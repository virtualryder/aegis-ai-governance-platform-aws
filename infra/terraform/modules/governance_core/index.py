"""Aegis control-plane gateway (stub).

Fail-closed governance boundary: applies the Bedrock guardrail on the input,
allows the request ONLY when the guardrail explicitly returns NONE (no
intervention), and writes an append-only audit record with a conditional put.
Byte-for-byte behavioural parity with the ZipFile handler in
infra/cloudformation/governance-core.yaml.
"""

import json
import os
import time
import uuid

import boto3

ddb = boto3.client("dynamodb")
bedrock = boto3.client("bedrock-runtime")

AUDIT_TABLE = os.environ["AUDIT_TABLE"]
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")
DATA_CLASS = os.environ.get("DATA_CLASS", "unknown")


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
