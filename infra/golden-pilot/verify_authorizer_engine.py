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
    os.environ["LEDGER"] = ""  # no ledger -> consequential must fail closed (re-enabled per check below)
    os.environ.pop("ALLOW_DEFAULT_ENTITLEMENTS", None)

    # Stub boto3 so the handler imports without AWS; capture audit writes. The stub
    # ledger evaluates the SAME binding the real ConditionExpression enforces
    # (COPILOT-2), so the consume path is exercised offline exactly as deployed.
    writes = []
    ledger = {}

    def _update_item(**kw):
        row = ledger.get(kw["Key"]["approval_id"]["S"])
        v = kw["ExpressionAttributeValues"]
        cond = (row is not None and "consumed_at" not in row and int(row["expires_at"]) > int(v[":now"]["N"])
                and row["requester"] == v[":sub"]["S"] and row["agent_id"] == v[":agent"]["S"]
                and row["tool_id"] == v[":tool"]["S"] and row["args_hash"] == v[":args"]["S"]
                and row["purpose"] == v[":purpose"]["S"])
        if not cond:
            raise Exception("ConditionalCheckFailedException")
        row["consumed_at"] = v[":now"]["N"]
    boto3 = types.ModuleType("boto3")
    boto3.client = lambda *a, **k: types.SimpleNamespace(put_item=lambda **kw: writes.append(kw), update_item=_update_item)
    sys.modules["boto3"] = boto3

    import handler as h
    from platform_core import masker, policy_engine
    from platform_core.approval_ledger import arguments_hash

    # 1) Decisions must come from the reviewed predicate.
    assert isinstance(h.POLICY, policy_engine.PolicyEngine), "authorizer must use platform_core.PolicyEngine"

    claims = {"sub": "alice", "custom:tools": "kb.search_policy ticket.create_draft ticket.submit"}
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

    # 1b) COPILOT-3: no / malformed entitlement claim => ZERO tools, never a default.
    assert h.ALLOW_DEFAULT_ENTITLEMENTS is False, "demo default must be OFF unless ALLOW_DEFAULT_ENTITLEMENTS=1"
    for bad in ({"sub": "bob"}, {"sub": "bob", "custom:tools": ""}, {"sub": "bob", "custom:tools": ["kb.search_policy"]},
                {"sub": "bob", "scope": 42}):
        assert h._entitlements(bad) == set(), f"claims {bad} must yield zero entitlements"
        eff, reason, _ = h._evaluate(bad, "kb.search_policy", {})
        assert eff.value == "DENY", f"no-claim caller must be denied: {reason}"
    ev = lambda body, c: h.handler({"requestContext": {"authorizer": {"jwt": {"claims": c}}}, "body": json.dumps(body)}, None)
    r = ev({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, {"sub": "bob"})
    assert r["statusCode"] == 403 and "zero tools" in r["body"], r
    r = ev({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "kb.search_policy", "arguments": {"query": "x"}}}, {"sub": "bob"})
    assert r["statusCode"] == 403 and "zero tools" in r["body"], r
    r = ev({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}, {"sub": "carol", "custom:tools": "kb.search_policy"})
    assert [t["name"] for t in json.loads(r["body"])["result"]["tools"]] == ["kb.search_policy"], "tools/list must be the entitlement intersection"
    print("  ok  no / malformed entitlement claim -> zero tools (403); tools/list = intersection")

    # 1c) COPILOT-2: the approval is bound to the FULL action at consumption.
    h.LEDGER = "verify-ledger"
    agent = h.MANIFEST["metadata"]["id"]
    good_args = {"ticket_id": "T1"}
    def mint(aid, **over):
        row = {"requester": "alice", "expires_at": str(int(__import__("time").time()) + 600), "agent_id": agent,
               "tool_id": "ticket.submit", "args_hash": arguments_hash(good_args), "purpose": "decision_support"}
        row.update(over); ledger[aid] = row
    mint("ap-args");  eff, reason, _ = h._evaluate(claims, "ticket.submit", {"ticket_id": "T2", "approval_id": "ap-args"})
    assert eff.value == "DENY" and "consumed_at" not in ledger["ap-args"], f"modified args must be refused: {reason}"
    mint("ap-tool", tool_id="ticket.create_draft"); eff, reason, _ = h._evaluate(claims, "ticket.submit", {"ticket_id": "T1", "approval_id": "ap-tool"})
    assert eff.value == "DENY" and "consumed_at" not in ledger["ap-tool"], f"wrong tool must be refused: {reason}"
    mint("ap-purpose", purpose="lookup"); eff, reason, _ = h._evaluate(claims, "ticket.submit", {"ticket_id": "T1", "approval_id": "ap-purpose"})
    assert eff.value == "DENY", f"wrong purpose must be refused: {reason}"
    mint("ap-other", requester="mallory"); eff, reason, _ = h._evaluate(claims, "ticket.submit", {"ticket_id": "T1", "approval_id": "ap-other"})
    assert eff.value == "DENY", f"another requester's approval must be refused: {reason}"
    mint("ap-good"); eff, reason, _ = h._evaluate(claims, "ticket.submit", {"ticket_id": "T1", "approval_id": "ap-good"})
    assert eff.value == "ALLOW" and "consumed_at" in ledger["ap-good"], f"the exact bound action must consume + ALLOW: {reason}"
    eff, reason, _ = h._evaluate(claims, "ticket.submit", {"ticket_id": "T1", "approval_id": "ap-good"})
    assert eff.value == "DENY", f"replay of the consumed approval must be refused: {reason}"
    h.LEDGER = ""
    print("  ok  approval bound at consumption: args / tool / purpose / requester mismatch -> DENY; exact -> ALLOW once")

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
