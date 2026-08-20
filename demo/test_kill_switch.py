#!/usr/bin/env python3
"""Negative tests for the Kill Switch — the named platform containment control.

Proves the four design rules in platform_core/kill_switch.py:
  1. an engaged switch denies EVERYTHING at the gateway, first check, fail closed;
  2. release requires a different actor than engage (separation of duties);
  3. every state change is written to the append-only audit;
  4. disengaging restores normal authorization (containment is reversible).

Run:  PYTHONPATH=platform_core:. pytest demo/test_kill_switch.py -q
"""

from __future__ import annotations

import os
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from platform_core.approval_ledger import ApprovalLedger
from platform_core.audit_ledger import AuditLedger
from platform_core.chargeback import UsageLedger
from platform_core.gateway import AuthorizationGateway, ToolCall
from platform_core.kill_switch import KillSwitch, KillSwitchError
from platform_core.policy_engine import Effect, PolicyEngine
from platform_core.token_budget import BudgetRegistry

MANIFEST = {
    "apiVersion": "aegis/v1",
    "kind": "Agent",
    "metadata": {
        "id": "test-agent",
        "owner": "governance",
        "team": "governance",
        "packs": ["core"],
        "classification": ["public", "pii"],
    },
    "grants": {
        "tools": [
            {"id": "svc.read", "scope": "read", "data_classes": ["public", "pii"]},
        ],
        "consequential": [],
    },
    "human_gate": {"separation_of_duties": True, "approval_ttl_seconds": 3600},
    "budget": {"monthly_token_cap": 1_000_000, "cap_behavior": "hard"},
}

ENT = {"svc.read"}


def _fresh(ks: KillSwitch | None = None):
    audit = AuditLedger(jsonl_path=None)
    if ks is not None:
        ks.audit = audit
    gw = AuthorizationGateway(
        audit, BudgetRegistry(), ApprovalLedger(), UsageLedger(), PolicyEngine(),
        kill_switch=ks,
    )
    gw.register_agent(MANIFEST)
    gw.register_tool("svc.read", lambda a: {"ok": True})
    return gw, audit


def _tc(tool_id="svc.read", **overrides):
    base = dict(
        user="alice", authenticated=True, user_entitlements=ENT,
        agent_id="test-agent", tool_id=tool_id, scope="read", purpose="triage",
        data_classes=["public"], region="us-east-1", arguments={"x": 1},
        payload="hello", estimated_tokens=100,
    )
    base.update(overrides)
    return ToolCall(**base)


class KillSwitchTests(unittest.TestCase):
    def test_no_switch_configured_behaves_normally(self):
        """A gateway built without a switch is unchanged (backwards compatible)."""
        gw, _ = _fresh(None)
        self.assertEqual(gw.call(_tc()).effect, Effect.ALLOW)

    def test_engaged_switch_denies_everything_first(self):
        """Engaged switch -> DENY before policy/budget/masking, with audit."""
        ks = KillSwitch()
        gw, audit = _fresh(ks)
        self.assertEqual(gw.call(_tc()).effect, Effect.ALLOW)  # sanity: allowed
        ks.engage(actor="secops_oncall", reason="SEV-1 prompt-injection incident")
        res = gw.call(_tc())
        self.assertEqual(res.effect, Effect.DENY)
        self.assertIn("kill_switch_engaged", res.reason)
        # even a broken payload (masker would raise) is denied by the SWITCH,
        # proving containment precedes the masking boundary:
        res2 = gw.call(_tc(payload=None))
        self.assertIn("kill_switch_engaged", res2.reason)

    def test_engage_requires_actor_and_reason(self):
        ks = KillSwitch()
        with self.assertRaises(KillSwitchError):
            ks.engage(actor="", reason="x")
        with self.assertRaises(KillSwitchError):
            ks.engage(actor="a", reason="")

    def test_separation_of_duties_on_release(self):
        """The engaging actor cannot disengage; a second identity can."""
        ks = KillSwitch()
        gw, _ = _fresh(ks)
        ks.engage(actor="secops_oncall", reason="containment drill")
        with self.assertRaises(KillSwitchError):
            ks.disengage(actor="secops_oncall", reason="drill over")
        ks.disengage(actor="security_lead", reason="drill over, reviewed")
        self.assertFalse(ks.engaged)
        self.assertEqual(gw.call(_tc()).effect, Effect.ALLOW)  # reversible

    def test_state_changes_are_audited(self):
        ks = KillSwitch()
        gw, audit = _fresh(ks)
        ks.engage(actor="secops_oncall", reason="drill")
        ks.disengage(actor="security_lead", reason="drill over")
        reasons = [
            getattr(r, "decision_reason", "") or (r.get("decision_reason", "") if isinstance(r, dict) else "")
            for r in getattr(audit, "records", [])
        ]
        joined = " ".join(str(x) for x in reasons)
        self.assertIn("kill_switch_engage", joined)
        self.assertIn("kill_switch_disengage", joined)

    def test_disengage_when_not_engaged_raises(self):
        ks = KillSwitch()
        with self.assertRaises(KillSwitchError):
            ks.disengage(actor="anyone", reason="nothing to release")


if __name__ == "__main__":
    unittest.main(verbosity=2)
