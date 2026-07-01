#!/usr/bin/env python3
"""test_fail_closed - regression tests for the offline gateway's default-deny.

A ChatGPT review found the offline gateway could return a success ({"ok": true})
when NO tool handler was registered, instead of denying. These tests lock in the
fail-closed contract:

  * an unregistered tool  -> DENY  (reason "tool-not-registered")
  * masking failure       -> DENY  (reason contains "masking_fail_closed")
  * a normal registered tool with a satisfied policy -> ALLOW

Run from the repo root, stdlib only (no pytest):

    python3 demo/test_fail_closed.py
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
from platform_core.policy_engine import Effect, PolicyEngine
from platform_core.token_budget import BudgetRegistry


# A minimal, self-contained manifest so the tests never depend on demo state.
MANIFEST = {
    "metadata": {
        "id": "test-agent",
        "owner": "platform",
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


def _fresh_gateway():
    audit = AuditLedger(jsonl_path=None)
    gw = AuthorizationGateway(
        audit, BudgetRegistry(), ApprovalLedger(), UsageLedger(), PolicyEngine()
    )
    gw.register_agent(MANIFEST)
    return gw


def _tc(tool_id, **overrides):
    base = dict(
        user="alice", authenticated=True, user_entitlements=ENT,
        agent_id="test-agent", tool_id=tool_id, scope="read", purpose="triage",
        data_classes=["public"], region="us-east-1", arguments={"x": 1},
        payload="hello", estimated_tokens=100,
    )
    base.update(overrides)
    return ToolCall(**base)


class FailClosedTests(unittest.TestCase):
    def test_unregistered_tool_denies(self):
        """Policy would allow, but no handler is registered -> DENY."""
        gw = _fresh_gateway()
        # svc.read is granted+entitled, so policy ALLOWs; but we never
        # register_tool() it, so the gateway must fail closed.
        res = gw.call(_tc("svc.read"))
        self.assertEqual(res.effect, Effect.DENY)
        self.assertEqual(res.reason, "tool-not-registered")
        self.assertFalse(res.allowed)

    def test_masking_failure_denies(self):
        """A payload the masker cannot process -> boundary DENY."""
        gw = _fresh_gateway()
        gw.register_tool("svc.read", lambda a: {"ok": True})
        # payload=None models a masker that cannot run -> mask_report raises
        # MaskingError -> the boundary fails closed before anything executes.
        res = gw.call(_tc("svc.read", payload=None))
        self.assertEqual(res.effect, Effect.DENY)
        self.assertIn("masking_fail_closed", res.reason)

    def test_registered_tool_allows(self):
        """The happy path still works: registered + policy-satisfied -> ALLOW."""
        gw = _fresh_gateway()
        gw.register_tool("svc.read", lambda a: {"body": "ok", "x": a.get("x")})
        res = gw.call(_tc("svc.read"))
        self.assertEqual(res.effect, Effect.ALLOW)
        self.assertTrue(res.allowed)
        self.assertEqual(res.output, {"body": "ok", "x": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
