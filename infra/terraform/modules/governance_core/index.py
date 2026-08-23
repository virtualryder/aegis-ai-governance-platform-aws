"""Aegis control-plane gateway (stub).

Fail-closed governance boundary: checks the platform Kill Switch FIRST
(containment precedes evaluation — platform_core/kill_switch.py), applies the
Bedrock guardrail on the input, allows the request ONLY when the guardrail
explicitly returns NONE (no intervention), and writes an append-only audit
record with a conditional put. Behavioural parity with the ZipFile handler in
infra/cloudformation/governance-core.yaml, except the Kill Switch check, which
activates only when the KILL_SWITCH_PARAM environment variable is set (the
CDK app sets it; deployments without the parameter behave as before).
"""

import json
import os
import time
import uuid

import boto3

ddb = boto3.client("dynamodb")
bedrock = boto3.client("bedrock-runtime")
ssm = boto3.client("ssm")

AUDIT_TABLE = os.environ["AUDIT_TABLE"]
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")
DATA_CLASS = os.environ.get("DATA_CLASS", "unknown")
KILL_SWITCH_PARAM = os.environ.get("KILL_SWITCH_PARAM", "")
KILL_SWITCH_TTL_SECONDS = int(os.environ.get("KILL_SWITCH_TTL_SECONDS", "15"))

_kill_switch_cache = {"at": 0.0, "engaged": False, "reason": ""}


def _kill_switch_state():
    """Read the platform Kill Switch (short-TTL cache). Fail closed: if the
    parameter is configured but cannot be read or parsed, treat it as ENGAGED
    — an unreadable containment control cannot vouch for anything."""
    if not KILL_SWITCH_PARAM:
        return {"engaged": False, "reason": "not-configured"}
    now = time.time()
    if now - _kill_switch_cache["at"] < KILL_SWITCH_TTL_SECONDS:
        return {"engaged": _kill_switch_cache["engaged"],
                "reason": _kill_switch_cache["reason"]}
    try:
        raw = ssm.get_parameter(Name=KILL_SWITCH_PARAM)["Parameter"]["Value"]
        state = json.loads(raw)
        engaged = bool(state.get("engaged", False))
        reason = str(state.get("reason", ""))
    except Exception as exc:  # noqa: BLE001 — fail closed on unreadable switch
        engaged, reason = True, "kill-switch-unreadable: " + str(exc)
    _kill_switch_cache.update({"at": now, "engaged": engaged, "reason": reason})
    return {"engaged": engaged, "reason": reason}


def _apply_guardrail(text):
    """Apply the Bedrock guardrail on input text. Best-effort: never block
    the audit write if guardrail access is not yet enabled."""
    if not GUARDRAIL_ID:
        # Fail closed: no guardrail configured means we cannot vouch for the request.
        return {"action": "UNAVAILABLE", "reason": "no-guardrail-configured"}
    try:
        resp = bedrock.apply_guardrail(
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion=str(GUARDRAIL_VERSION),
            source="INPUT",
            content=[{"text": {"text": text}}],
        )
        return {"action": resp.get("action", "NONE")}
    except Exception as exc:  # noqa: BLE001
        return {"action": "ERROR", "reason": str(exc)}


def handler(event, context):
    request_id = (event or {}).get("request_id") or str(uuid.uuid4())
    prompt = (event or {}).get("prompt", "hello from aegis gateway")

    # KILL SWITCH FIRST: an engaged switch denies every request — before the
    # guardrail, before anything. The denial is still audited.
    ks = _kill_switch_state()
    if ks["engaged"]:
        ddb.put_item(
            TableName=AUDIT_TABLE,
            Item={
                "request_id": {"S": request_id},
                "seq": {"N": "0"},
                "ts": {"N": str(int(time.time()))},
                "data_class": {"S": DATA_CLASS},
                "decision": {"S": "deny"},
                "guardrail_action": {"S": "KILL_SWITCH"},
                "purpose": {"S": (event or {}).get("purpose", "demo")},
            },
            ConditionExpression="attribute_not_exists(request_id) AND attribute_not_exists(seq)",
        )
        return {
            "statusCode": 403,
            "decision": "deny",
            "request_id": request_id,
            "seq": 0,
            "kill_switch": ks,
            "body": json.dumps({"status": "audited", "decision": "deny",
                                "reason": "kill-switch-engaged",
                                "request_id": request_id}),
        }

    guardrail_result = _apply_guardrail(prompt)
    action = str(guardrail_result.get("action"))

    # FAIL CLOSED: allow only when the guardrail explicitly returned NONE
    # (no intervention). Any intervention, error, or inability to evaluate
    # denies the request. Mandatory governance boundary.
    allowed = action == "NONE"
    decision = "allow" if allowed else "deny"

    item = {
        "request_id": {"S": request_id},
        "seq": {"N": "0"},
        "ts": {"N": str(int(time.time()))},
        "data_class": {"S": DATA_CLASS},
        "decision": {"S": decision},
        "guardrail_action": {"S": action},
        "purpose": {"S": (event or {}).get("purpose", "demo")},
    }
    ddb.put_item(
        TableName=AUDIT_TABLE,
        Item=item,
        ConditionExpression="attribute_not_exists(request_id) AND attribute_not_exists(seq)",
    )

    return {
        "statusCode": 200 if allowed else 403,
        "decision": decision,
        "request_id": request_id,
        "seq": 0,
        "guardrail": guardrail_result,
        "body": json.dumps({"status": "audited", "decision": decision, "request_id": request_id}),
    }
