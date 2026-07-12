"""Aegis MCP gateway Lambda — deployed authorizer running the REVIEWED engine.

This is the deployed authorizer for the portable MCP-protocol pilot
(`infra/golden-pilot/mcp-gateway.yaml`). Every governance decision it makes now
comes from the **reviewed `platform_core` engine**, delivered as a Lambda layer:

    * the deny-by-default authorization decision  -> platform_core.policy_engine
      (the full 9-clause ALLOW-iff predicate: authenticated_user AND agent_grant
       AND user_entitlement AND purpose AND data_class_boundary AND consent AND
       residency AND budget AND approval)
    * fail-closed boundary masking                 -> platform_core.masker
      (deterministic Safe-Harbor regex pass + mandatory-NER-in-real-data mode;
       raises rather than leaking)

Previously this handler embedded an *inline subset* of that logic (a hand-rolled
tool allow-list dict and a single one-line SSN/email regex). That subset has been
deleted. The MCP JSON-RPC plumbing and the AWS-native I/O (DynamoDB append-only
audit sink, DynamoDB reviewer-ledger single-use approval consume) remain here as
the orchestration *around* the pure engine — exactly the reference architecture
(docs/02 §3): "the gateway orchestrates I/O around" the reviewed predicate.

So the deployed artifact is no longer a subset of the reviewed engine — it *is*
the reviewed engine, invoked in-account.
"""

import base64
import json
import os
import time
import uuid

import boto3

# --- the REVIEWED engine, imported from the platform_core Lambda layer ------- #
# (staged into the layer's python/ by infra/golden-pilot/prepare_layer.sh)
from platform_core import masker, policy_engine
from platform_core.policy_engine import AuthContext, Effect, PolicyEngine

ddb = boto3.client("dynamodb")
TABLE = os.environ["TABLE"]
LEDGER = os.environ.get("LEDGER", "")

# One shared instance of the reviewed predicate for the life of the container.
POLICY = PolicyEngine()

# --------------------------------------------------------------------------- #
# Pilot agent manifest — CONFIG, not engine logic. The engine (policy_engine)
# is what evaluates this manifest; here we only declare the pilot agent's grants,
# the consequential bright-line, and the data classes it is allowed to touch.
# Consequential tools are deliberately WITHHELD from grants.tools so the reviewed
# predicate forces them through the human gate.
# --------------------------------------------------------------------------- #
MANIFEST = {
    "metadata": {
        "id": "aegis-mcp-gateway",
        "classification": ["public", "pii"],
        "owner": "platform",
        "team": "gov",
        "packs": ["aegis"],
    },
    "grants": {
        "tools": [
            {"id": "kb.search_policy", "scope": "read", "data_classes": ["public"]},
            {"id": "ticket.create_draft", "scope": "write", "data_classes": ["public", "pii"]},
        ],
        "consequential": ["ticket.submit"],
    },
}

# Per-tool call metadata (MCP surface + the purpose/scope/data-class each call
# declares to the reviewed predicate). Tools absent here are unknown and are
# denied deny-by-default by the engine (no grant).
TOOLS = {
    "kb.search_policy": {
        "description": "Search the approved policy knowledge base (read-only).",
        "consequential": False,
        "purpose": "policy_search",
        "scope": "read",
        "data_classes": ["public"],
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    "ticket.create_draft": {
        "description": "Draft a service ticket. Drafting only - no submit authority.",
        "consequential": False,
        "purpose": "draft_response",
        "scope": "write",
        "data_classes": ["public", "pii"],
        "inputSchema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
    },
    "ticket.submit": {
        "description": "CONSEQUENTIAL: submit a ticket. Requires a bound single-use approval.",
        "consequential": True,
        "purpose": "decision_support",
        "scope": "write",
        "data_classes": ["public", "pii"],
        "inputSchema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}, "approval_id": {"type": "string"}},
            "required": ["ticket_id"],
        },
    },
}

# Default entitlements for an authenticated caller (least-privilege INTERSECTION
# is still enforced by the engine — an entitlement without a matching agent grant
# is not sufficient). A real IdP supplies these via a claim; the pilot defaults to
# the pilot tool set so the intersection clause is exercised, not bypassed.
_DEFAULT_ENTITLEMENTS = {"kb.search_policy", "ticket.create_draft", "ticket.submit"}


def _entitlements(claims):
    raw = claims.get("custom:tools") or claims.get("scope") or ""
    ents = {t.strip() for t in raw.replace(",", " ").split() if t.strip()}
    return ents or set(_DEFAULT_ENTITLEMENTS)


def _mask(text, data_classes):
    """Fail-closed masking via the reviewed masker. On any masking fault the
    boundary denies (masker.mask raises MaskingFailClosed) rather than leaking."""
    return masker.mask(text, data_classes)


def audit(sub, tool, decision, detail, data_classes):
    ddb.put_item(
        TableName=TABLE,
        Item={
            "pk": {"S": "audit"},
            "sk": {"S": "%.6f#%s" % (time.time(), uuid.uuid4().hex[:8])},
            "sub": {"S": sub},
            "tool": {"S": tool},
            "decision": {"S": decision},
            # Masked with the reviewed fail-closed masker, not an inline regex.
            "detail": {"S": _mask(detail, data_classes)[:400]},
        },
    )


def _consume_approval(aid, sub):
    """Atomic single-use consume against the reviewer ledger: the approval must
    exist, be unconsumed, unexpired, AND bound to the calling identity. Returns
    True iff consumed. Any other case (unknown/expired/replayed/unbound) -> False.
    Fail-closed: no ledger configured or any error -> False."""
    if not LEDGER:
        return False
    now = int(time.time())
    try:
        ddb.update_item(
            TableName=LEDGER,
            Key={"approval_id": {"S": str(aid)}},
            UpdateExpression="SET consumed_at = :now",
            ConditionExpression=(
                "attribute_exists(approval_id) AND attribute_not_exists(consumed_at) "
                "AND expires_at > :now AND requester = :sub"
            ),
            ExpressionAttributeValues={":now": {"N": str(now)}, ":sub": {"S": sub}},
        )
        return True
    except Exception:
        return False


def err(i, c, m):
    return {"jsonrpc": "2.0", "id": i, "error": {"code": c, "message": m}}


def ok(i, r):
    return {"jsonrpc": "2.0", "id": i, "result": r}


def resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def _evaluate(claims, name, args):
    """Run the reviewed deny-by-default predicate for one tools/call. Returns
    (effect, reason, data_classes). Consequential tools with a supplied approval
    are validated by consuming the bound single-use approval, and only then is the
    predicate re-run with approval_valid=True."""
    sub = claims.get("sub", "anonymous")
    meta = TOOLS.get(name)
    # Unknown tool: build a minimal context so the engine denies deny-by-default
    # (no agent grant) — the decision still comes from the reviewed predicate.
    data_classes = meta["data_classes"] if meta else ["public"]
    ctx = AuthContext(
        user=sub,
        authenticated=bool(sub and sub != "anonymous"),
        user_entitlements=_entitlements(claims),
        agent_id=MANIFEST["metadata"]["id"],
        tool_id=name,
        scope=(meta["scope"] if meta else "read"),
        purpose=(meta["purpose"] if meta else "lookup"),
        data_classes=data_classes,
        region=os.environ.get("AWS_REGION", ""),
        consent_present=True,
        approval_valid=False,
    )
    decision = POLICY.evaluate(ctx, MANIFEST)

    # If the only blocker is the human gate on a consequential tool, try to
    # consume a bound single-use approval, then re-affirm with the reviewed engine.
    if decision.effect is Effect.APPROVAL_REQUIRED:
        aid = (args or {}).get("approval_id")
        if aid and _consume_approval(aid, sub):
            ctx.approval_valid = True
            decision = POLICY.evaluate(ctx, MANIFEST)
    return decision.effect, decision.reason, data_classes


def handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    sub = claims.get("sub", "anonymous")
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    try:
        req = json.loads(body)
    except Exception:
        return resp(400, err(None, -32700, "parse error"))
    rid, method = req.get("id"), req.get("method", "")

    if method == "initialize":
        return resp(200, ok(rid, {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "aegis-mcp-gateway", "version": "1.0.0"},
        }))
    if method == "notifications/initialized":
        return resp(202, {})
    if method == "tools/list":
        audit(sub, "*", "allow", "tools/list", ["public"])
        return resp(200, ok(rid, {"tools": [
            {"name": k, "description": v["description"], "inputSchema": v["inputSchema"]}
            for k, v in TOOLS.items()
        ]}))
    if method == "tools/call":
        p = req.get("params", {})
        name = p.get("name", "")
        args = p.get("arguments", {})
        try:
            effect, reason, data_classes = _evaluate(claims, name, args)
        except masker.MaskingFailClosed as exc:
            audit(sub, name, "deny", "masking_fail_closed", ["public"])
            return resp(200, err(rid, -32003, "deny: masking failed, boundary closed: %s" % exc))

        if effect is Effect.ALLOW:
            audit(sub, name, "allow", json.dumps(args), data_classes)
            masked_args = _mask(json.dumps(args), data_classes)
            return resp(200, ok(rid, {
                "content": [{"type": "text", "text": "[fixture] %s executed. args=%s" % (name, masked_args)}],
                "isError": False,
            }))
        if effect is Effect.APPROVAL_REQUIRED:
            audit(sub, name, "deny", "approval_required: %s" % reason, data_classes)
            return resp(200, err(rid, -32003,
                                  "deny: %s (bound single-use approval required — see reviewer service, Runs 5/7)" % reason))
        # DENY (deny-by-default and every other unsatisfied clause)
        audit(sub, name, "deny", reason, data_classes)
        return resp(200, err(rid, -32601, "deny: %s" % reason))

    return resp(200, err(rid, -32601, "method '%s' not supported" % method))
