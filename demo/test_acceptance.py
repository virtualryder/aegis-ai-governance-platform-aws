"""Optional pytest entry point (bonus path; pytest is NOT required).

The canonical demo is `python3 demo/clean_account_acceptance.py`. This wrapper
lets a CI/pytest user assert the same thing:

    pytest demo/test_acceptance.py

It runs the full acceptance scenario in-process and asserts it returns 0
(every step PASS). It also adds a few focused unit assertions on the core
controls so a failure points at the right module.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def test_full_acceptance_returns_zero():
    from demo import clean_account_acceptance as demo
    # reset module-level results so repeated runs are clean
    demo._results.clear()
    assert demo.main() == 0


def test_masker_fails_closed_on_bad_input():
    from platform_core import masker
    import pytest  # type: ignore

    # Luhn-aware: a real PAN is masked, a random 16-digit run is not.
    assert "[CARD-REDACTED]" in masker.mask("pay 4111111111111111 now", ["card"])
    assert "1234567812345678" in masker.mask("ref 1234567812345678", ["card"])
    with pytest.raises(masker.MaskingFailClosed):
        masker.mask(None, ["pii"])


def test_policy_engine_is_default_deny():
    from platform_core.policy_engine import AuthContext, Effect, PolicyEngine

    manifest = {
        "metadata": {"id": "a", "classification": ["public"]},
        "grants": {"tools": [{"id": "t.read", "scope": "read"}], "consequential": []},
    }
    ctx = AuthContext(
        user="u", authenticated=True, user_entitlements={"t.read"}, agent_id="a",
        tool_id="other.tool", scope="read", purpose="triage",
        data_classes=["public"], region="us-east-1",
    )
    assert PolicyEngine().evaluate(ctx, manifest).effect is Effect.DENY


def test_approval_replay_rejected():
    from platform_core.approval_ledger import ApprovalError, ApprovalLedger
    import pytest  # type: ignore

    led = ApprovalLedger()
    ap = led.request_approval("a", "t.do", {"x": 1}, "p", "alice")
    with pytest.raises(ApprovalError):
        led.approve(ap.approval_id, reviewer="alice")  # self-approval blocked
    led.approve(ap.approval_id, reviewer="bob")
    led.consume(ap.approval_id, "a", "t.do", {"x": 1}, "p")  # ok once
    with pytest.raises(ApprovalError):
        led.consume(ap.approval_id, "a", "t.do", {"x": 1}, "p")  # replay rejected


def test_audit_is_immutable():
    from platform_core.audit_ledger import AuditLedger, ImmutabilityError
    import pytest  # type: ignore

    led = AuditLedger()
    led.append(request_id="r", user="u", agent_id="a", tool_id="t", purpose="p",
               data_class=["public"], policy_decision="ALLOW", decision_reason="ok")
    assert led.verify_chain()
    with pytest.raises(ImmutabilityError):
        led.try_mutate(0, policy_decision="DENY")
