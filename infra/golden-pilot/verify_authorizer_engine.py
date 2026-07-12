#!/usr/bin/env python3
"""Verify the deployed MCP authorizer runs the REVIEWED platform_core engine.

This is the B3 regression guard: it proves the Lambda handler in `gateway-src/`
makes its authorization decisions with `platform_core.policy_engine` and masks
with `platform_core.masker` (loaded exactly as the deployed Lambda loads them —
from the pre-staged layer), NOT an inline subset. It is deliberately NOT a
pytest-collected test (it lives outside demo/ and platform_core/tests/, and has
no test_ functions) so it does not perturb the canonical offline count in
MATURITY.yaml. Run it after ./prepare_layer.sh:

    ./prepare_layer.sh && python verify_authorizer_engine.py

Exit 0 = the deployed authorizer is the reviewed engine.
"""
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    layer = os.path.join(HERE, "layer", "python")
    if not os.path.isdir(os.path.join(layer, "platform_core")):
        print("FAIL: layer/python/platform_core missing — run ./prepare_layer.sh first")
        return 1
    # Load platform_core the way the Lambda does: from the staged layer only.
    sys.path.insert(0, layer)
    sys.path.insert(0, os.path.join(HERE, "gateway-src"))

    os.environ.setdefault("TABLE", "verify-table")
    os.environ["LEDGER"] = ""  # no ledger -> consequential must fail closed

    # Stub boto3 so the handler imports without AWS; capture audit writes.
    writes = []
    boto3 = types.ModuleType("boto3")
    boto3.client = lambda *a, **k: types.SimpleNamespace(
        put_item=lambda **kw: writes.append(kw),
        update_item=lambda **kw: (_ for _ in ()).throw(Exception("no ledger")),
    )
    sys.modules["boto3"] = boto3

    import handler as h
    from platform_core import masker, policy_engine

    # 1) Decisions must come from the reviewed predicate.
    assert isinstance(h.POLICY, policy_engine.PolicyEngine), "authorizer must use platform_core.PolicyEngine"

    claims = {"sub": "alice"}
    cases = {
        "kb.search_policy": "ALLOW",          # granted + entitled + purpose ok
        "db.drop": "DENY",                    # deny-by-default: no agent grant
        "ticket.submit": "APPROVAL_REQUIRED",  # consequential, withheld -> human gate
    }
    for tool, expected in cases.items():
        eff, reason, _ = h._evaluate(claims, tool, {})
        got = eff.value
        assert got == expected, f"{tool}: expected {expected}, got {got} ({reason})"
        print(f"  ok  {tool:20s} -> {got}")

    # 2) Masking must come from the reviewed fail-closed masker (not a one-liner).
    masked = h._mask("SSN 123-45-6789, card 4111 1111 1111 1111, email a@b.com", ["pii", "card"])
    assert "123-45-6789" not in masked and "a@b.com" not in masked, "masker must redact PII"
    assert "[SSN-REDACTED]" in masked and "[EMAIL-REDACTED]" in masked, "must be the reviewed masker's tokens"
    # The reviewed masker Luhn-validates cards; the inline subset never did.
    assert "[CARD-REDACTED]" in masked, "reviewed masker must Luhn-redact the card"
    print(f"  ok  masking via platform_core.masker -> {masked}")

    # 3) The inline subset must be gone from the template.
    tmpl = open(os.path.join(HERE, "mcp-gateway.yaml"), encoding="utf-8").read()
    assert "ZipFile:" not in tmpl, "inline ZipFile subset must be deleted"
    assert "PlatformCoreLayer" in tmpl and "gateway-src/" in tmpl, "template must ship the layer + external handler"
    print("  ok  inline subset deleted; template ships platform_core layer + gateway-src handler")

    print("PASS: the deployed MCP authorizer runs the reviewed platform_core engine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
