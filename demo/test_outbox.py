"""Durable intent / outbox ordering in the reference gateway (COPILOT-1, 2026-09-03).

The failure this guards against: the gateway executed a consequential side effect, THEN tried to
write the audit record, and when that write failed it answered DENY - the approval was consumed,
the real-world action had happened, and the caller was told "no", i.e. invited to retry and do it
twice. Copilot's review found it in platform_core/gateway.py (consume -> execute -> audit -> DENY).

The order is now: AUTHORIZED-INTENT (durable) -> consume -> execute(idempotency_key) ->
COMPLETED/FAILED. The tests below pin every consequence of that order:

  1. INTENT write fails       => DENY, handler NOT called, approval NOT consumed (retry is safe)
  2. COMPLETED write fails    => INDETERMINATE (reconciliation_required), the side effect ran once,
                                 the INTENT record is the anchor, and a retry with the same key is
                                 refused from the outbox (already_completed) - never executed twice
  3. the connector receives the gateway's idempotency key; the key is on INTENT and COMPLETED rows
  4. an unregistered consequential tool no longer burns the approval
  5. INDETERMINATE is never produced by the policy predicate itself

Run:  PYTHONPATH=platform_core:. python -m pytest demo/test_outbox.py -q
"""
from __future__ import annotations

import os
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from platform_core.approval_ledger import ApprovalLedger  # noqa: E402
from platform_core.audit_ledger import AuditLedger  # noqa: E402
from platform_core.chargeback import UsageLedger  # noqa: E402
from platform_core.gateway import AuthorizationGateway, ToolCall  # noqa: E402
from platform_core.policy_engine import Effect, PolicyEngine  # noqa: E402
from platform_core.token_budget import BudgetRegistry  # noqa: E402

MANIFEST = {
    "metadata": {"id": "permit-triage", "owner": "dept-permitting", "team": "intake",
                 "packs": ["slg"], "classification": ["public", "pii"]},
    "grants": {
        "tools": [{"id": "kb.read", "scope": "read", "data_classes": ["public", "pii"]}],
        "consequential": ["accela.issue_permit"],
    },
    "human_gate": {"separation_of_duties": True, "approval_ttl_seconds": 3600},
    "budget": {"monthly_token_cap": 1_000_000, "cap_behavior": "hard"},
}
AGENT = "permit-triage"
ENT = {"kb.read", "accela.issue_permit"}


class _AuditFailingAt(AuditLedger):
    """Append-only ledger that fails on the Nth append (1-based) - models a backend outage at one
    exact point of the sequence. `policy_decision` of the failing call is recorded for assertions."""

    def __init__(self, fail_on_decision):
        super().__init__(jsonl_path=None)
        self.fail_on_decision = fail_on_decision
        self.failed = []

    def append(self, **fields):  # type: ignore[override]
        if fields.get("policy_decision") == self.fail_on_decision:
            self.failed.append(fields)
            raise RuntimeError("audit backend unavailable")
        return super().append(**fields)


def _gateway(audit=None):
    audit = AuditLedger(jsonl_path=None) if audit is None else audit
    gw = AuthorizationGateway(audit, BudgetRegistry(), ApprovalLedger(), UsageLedger(), PolicyEngine())
    gw.register_agent(MANIFEST)
    return gw


def _approved(gw, args):
    ap = gw.approvals.request_approval(AGENT, "accela.issue_permit", args, "decision_support",
                                       requester="clerk-alice")
    gw.approvals.approve(ap.approval_id, reviewer="supervisor-bob")
    return ap


def _call(tool, **over):
    base = dict(user="clerk-alice", authenticated=True, user_entitlements=ENT, agent_id=AGENT,
                tool_id=tool, scope="execute", purpose="decision_support", data_classes=["public"],
                region="us-east-1", arguments={"case": "CASE-1"}, payload="hello", estimated_tokens=100)
    base.update(over)
    return ToolCall(**base)


class OutboxOrderingTests(unittest.TestCase):
    # 1 ------------------------------------------------------------------
    def test_intent_write_failure_denies_before_any_side_effect(self):
        audit = _AuditFailingAt("INTENT")
        gw = _gateway(audit)
        calls = []
        gw.register_tool("accela.issue_permit", lambda a, idempotency_key=None: calls.append(a) or {"issued": True})
        ap = _approved(gw, {"case": "CASE-1"})
        res = gw.call(_call("accela.issue_permit", approval_id=ap.approval_id))
        self.assertIs(res.effect, Effect.DENY)
        self.assertIn("intent not durable", res.reason)
        self.assertEqual(calls, [], "the connector must not run without a durable INTENT")
        self.assertEqual(gw.approvals.get(ap.approval_id).status, "approved",
                         "the approval must not be consumed when nothing executed")
        self.assertEqual(len(audit.failed), 1)
        # A retry once the ledger is back succeeds exactly once.
        audit.fail_on_decision = None
        res2 = gw.call(_call("accela.issue_permit", approval_id=ap.approval_id))
        self.assertIs(res2.effect, Effect.ALLOW)
        self.assertEqual(len(calls), 1)

    # 2 ------------------------------------------------------------------
    def test_completion_write_failure_is_indeterminate_not_deny_and_never_reexecutes(self):
        audit = _AuditFailingAt("ALLOW")
        gw = _gateway(audit)
        calls = []
        gw.register_tool("accela.issue_permit", lambda a, idempotency_key=None: calls.append(idempotency_key) or {"issued": True})
        ap = _approved(gw, {"case": "CASE-1"})
        res = gw.call(_call("accela.issue_permit", approval_id=ap.approval_id))
        self.assertIs(res.effect, Effect.INDETERMINATE)
        self.assertTrue(res.reconciliation_required)
        self.assertIn("reconciliation_required", res.reason)
        self.assertEqual(len(calls), 1, "the side effect ran exactly once")
        self.assertEqual(res.output, {"issued": True})
        # The INTENT row is durable and carries the same idempotency key as the (failed) completion.
        self.assertIsNotNone(res.intent_record)
        self.assertEqual(res.intent_record.policy_decision, "INTENT")
        self.assertEqual(res.intent_record.idempotency_key, res.idempotency_key)
        self.assertEqual(res.intent_record.approval_id, ap.approval_id)
        self.assertEqual(audit.records[-1].policy_decision, "INTENT",
                         "the last durable row is the INTENT - the reconciliation anchor")
        # A retry with the same authorized action (same approval => same key) must NOT execute
        # again - it is refused from the outbox even though the ledger is still down...
        res2 = gw.call(_call("accela.issue_permit", approval_id=ap.approval_id))
        self.assertEqual(len(calls), 1, "never executed twice")
        self.assertIs(res2.effect, Effect.DENY)
        self.assertTrue(res2.already_completed)
        self.assertIsNone(res2.output, "single-use means single response: output is not re-served")
        # ...and once the ledger is back the same replay is still refused, audited, one execution.
        audit.fail_on_decision = None
        res3 = gw.call(_call("accela.issue_permit", approval_id=ap.approval_id))
        self.assertIs(res3.effect, Effect.DENY)
        self.assertTrue(res3.already_completed)
        self.assertIn("already_completed", res3.reason)
        self.assertEqual(res3.audit_record.idempotency_key, res.idempotency_key)
        self.assertEqual(len(calls), 1)

    # 3 ------------------------------------------------------------------
    def test_idempotency_key_reaches_connector_and_both_records(self):
        gw = _gateway()
        seen = {}
        gw.register_tool("accela.issue_permit", lambda a, idempotency_key: seen.setdefault("key", idempotency_key) or {"issued": True})
        ap = _approved(gw, {"case": "CASE-9"})
        res = gw.call(_call("accela.issue_permit", arguments={"case": "CASE-9"}, approval_id=ap.approval_id))
        self.assertIs(res.effect, Effect.ALLOW)
        self.assertTrue(res.idempotency_key and seen["key"] == res.idempotency_key)
        kinds = [(r.policy_decision, r.idempotency_key) for r in gw.audit.records[-2:]]
        self.assertEqual(kinds, [("INTENT", res.idempotency_key), ("ALLOW", res.idempotency_key)])
        # Keyed by the single-use approval: the same action under the same approval is one key;
        # a different approval (a second authorized action) is a different key.
        self.assertEqual(res.idempotency_key, AuthorizationGateway.idempotency_key(
            AGENT, "accela.issue_permit", {"case": "CASE-9"}, ap.approval_id, "ignored-when-approved"))
        # A legacy connector without the keyword still works (gateway-level de-dup protects it).
        gw.register_tool("kb.read", lambda a: {"ok": True})
        r = gw.call(_call("kb.read", scope="read", purpose="triage"))
        self.assertIs(r.effect, Effect.ALLOW)
        self.assertTrue(r.idempotency_key)

    # 4 ------------------------------------------------------------------
    def test_unregistered_consequential_tool_does_not_burn_the_approval(self):
        gw = _gateway()
        ap = _approved(gw, {"case": "CASE-1"})
        res = gw.call(_call("accela.issue_permit", approval_id=ap.approval_id))
        self.assertIs(res.effect, Effect.DENY)
        self.assertEqual(res.reason, "tool-not-registered")
        self.assertEqual(gw.approvals.get(ap.approval_id).status, "approved")
        self.assertNotIn("INTENT", [r.policy_decision for r in gw.audit.records])

    # 5 ------------------------------------------------------------------
    def test_policy_engine_never_returns_indeterminate(self):
        import inspect
        from platform_core import policy_engine
        src = inspect.getsource(policy_engine.PolicyEngine)
        self.assertNotIn("INDETERMINATE", src)
        # The chain stays verifiable with the new INTENT rows in it.
        gw = _gateway()
        gw.register_tool("kb.read", lambda a: {"ok": True})
        gw.call(_call("kb.read", scope="read", purpose="triage"))
        self.assertTrue(gw.audit.verify_chain())


if __name__ == "__main__":
    unittest.main(verbosity=2)
