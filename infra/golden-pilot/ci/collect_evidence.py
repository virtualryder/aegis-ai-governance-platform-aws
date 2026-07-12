#!/usr/bin/env python3
"""Reproducible deploy-evidence collector for the B3 MCP-gateway golden path.

Run AFTER `sam deploy` of `mcp-gateway.yaml`, with AWS credentials in the environment
(in CI these come from the GitHub OIDC role — no long-lived keys). It captures machine
evidence that the *deployed* governed controls actually fired, then writes sanitized
artifacts for an auditor. It never prints raw account IDs.

What it captures, all against the live stack:
  1. Live governed decisions over HTTPS — mints a Cognito token, POSTs MCP tools/call for
     ALLOW / ALLOW+masked / DENY(deny-by-default) / APPROVAL_REQUIRED(human gate).
  2. IAM policy simulation of the deployed Lambda role — proves dynamodb:PutItem is ALLOWED
     but UpdateItem/DeleteItem are DENIED on the audit table (append-only, enforced by IAM,
     not just app code).
  3. Append-only audit scan — confirms the sensitive record was stored MASKED.

Exit non-zero if any control does not behave as designed, so CI fails on a governance
regression rather than shipping a green check over a broken control.

Usage:
    python collect_evidence.py --stack aegis-mcp-gateway-ci --region us-east-1 --out ../evidence-ci
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import boto3

_SANITIZE = re.compile(r"\d{12}")  # redact any 12-digit AWS account id in captured text


def sanitize(obj):
    return json.loads(_SANITIZE.sub("<ACCOUNT>", json.dumps(obj, default=str)))


def stack_outputs(cfn, stack):
    outs = cfn.describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]
    return {o["OutputKey"]: o["OutputValue"] for o in outs}


def stack_resource(cfn, stack, logical_prefix):
    for r in cfn.list_stack_resources(StackName=stack)["StackResourceSummaries"]:
        if r["LogicalResourceId"].startswith(logical_prefix):
            return r["PhysicalResourceId"]
    return None


def mint_id_token(region, pool_id, client_id):
    idp = boto3.client("cognito-idp", region_name=region)
    user = "ci-verifier"
    pw = "Aegis-CI-Verify-2026!x"
    try:
        idp.admin_create_user(UserPoolId=pool_id, Username=user, MessageAction="SUPPRESS")
    except idp.exceptions.UsernameExistsException:
        pass
    idp.admin_set_user_password(UserPoolId=pool_id, Username=user, Password=pw, Permanent=True)
    r = idp.admin_initiate_auth(
        UserPoolId=pool_id, ClientId=client_id, AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": user, "PASSWORD": pw})
    return r["AuthenticationResult"]["IdToken"]


def mcp_call(url, token, rid, method, params=None):
    body = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def run_decisions(url, token):
    cases = [
        ("ALLOW", 1, "tools/call", {"name": "kb.search_policy", "arguments": {"query": "privacy policy"}}),
        ("ALLOW_MASKED", 2, "tools/call", {"name": "ticket.create_draft",
            "arguments": {"summary": "Resident SSN 123-45-6789 email jane@example.com needs help"}}),
        ("DENY_DEFAULT", 3, "tools/call", {"name": "db.drop", "arguments": {}}),
        ("HUMAN_GATE", 4, "tools/call", {"name": "ticket.submit", "arguments": {"ticket_id": "T1"}}),
    ]
    out = {}
    for label, rid, method, params in cases:
        out[label] = mcp_call(url, token, rid, method, params)
    return out


def assert_decisions(dec):
    problems = []
    if "result" not in dec["ALLOW"]:
        problems.append("kb.search_policy did not ALLOW")
    masked = json.dumps(dec["ALLOW_MASKED"])
    if "123-45-6789" in masked or "jane@example.com" in masked:
        problems.append("ticket.create_draft leaked raw PII (masker did not fire)")
    if "[SSN-REDACTED]" not in masked:
        problems.append("ticket.create_draft did not show the reviewed masker's redaction token")
    if "error" not in dec["DENY_DEFAULT"] or "no grant" not in json.dumps(dec["DENY_DEFAULT"]):
        problems.append("db.drop was not denied deny-by-default by the reviewed engine")
    if "consequential action withheld" not in json.dumps(dec["HUMAN_GATE"]):
        problems.append("ticket.submit did not hit the human gate")
    return problems


def iam_simulation(region, role_arn, table_arn):
    iam = boto3.client("iam", region_name=region)
    actions = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    res = iam.simulate_principal_policy(
        PolicySourceArn=role_arn, ActionNames=actions, ResourceArns=[table_arn])
    decisions = {r["EvalActionName"]: r["EvalDecision"] for r in res["EvaluationResults"]}
    problems = []
    if decisions.get("dynamodb:PutItem") != "allowed":
        problems.append("append (PutItem) is not allowed — the audit sink cannot write")
    for mut in ("dynamodb:UpdateItem", "dynamodb:DeleteItem"):
        if decisions.get(mut) == "allowed":
            problems.append(f"{mut} is ALLOWED — audit is not append-only")
    return decisions, problems


def audit_scan(region, table):
    ddb = boto3.client("dynamodb", region_name=region)
    items = ddb.scan(TableName=table).get("Items", [])
    rows = [{"tool": i.get("tool", {}).get("S"), "decision": i.get("decision", {}).get("S"),
             "detail": i.get("detail", {}).get("S", "")} for i in items]
    leaked = [r for r in rows if "123-45-6789" in r["detail"] or "jane@example.com" in r["detail"]]
    problems = ["audit stored raw PII (masking did not run before the write)"] if leaked else []
    return rows, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", required=True)
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--out", default="evidence-ci")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    cfn = boto3.client("cloudformation", region_name=args.region)
    outs = stack_outputs(cfn, args.stack)
    url = outs["McpEndpoint"]
    pool_id, client_id, table = outs["UserPoolId"], outs["ClientId"], outs["AuditTableName"]
    role_name = stack_resource(cfn, args.stack, "McpFunctionRole")
    acct = boto3.client("sts", region_name=args.region).get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{acct}:role/{role_name}"
    table_arn = f"arn:aws:dynamodb:{args.region}:{acct}:table/{table}"

    print("== 1. live governed decisions over HTTPS ==")
    token = mint_id_token(args.region, pool_id, client_id)
    decisions = run_decisions(url, token)
    dproblems = assert_decisions(decisions)

    print("== 2. IAM policy simulation of the deployed Lambda role ==")
    sim, iproblems = iam_simulation(args.region, role_arn, table_arn)
    print("   ", sim)

    print("== 3. append-only audit scan (masking before write) ==")
    time.sleep(2)
    rows, aproblems = audit_scan(args.region, table)

    problems = dproblems + iproblems + aproblems
    evidence = {
        "stack": args.stack, "region": args.region,
        "decisions": sanitize(decisions),
        "iam_simulation": sim,
        "audit_rows": sanitize(rows),
        "control_checks": {"passed": not problems, "problems": problems},
    }
    with open(os.path.join(args.out, "deploy-evidence.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    summary = [
        "# CI deploy-evidence — B3 MCP gateway (reviewed engine)", "",
        f"Stack `{args.stack}` in `{args.region}` (account redacted). Machine-captured; deploy → verify → teardown.",
        "",
        "| Control | Evidence | Result |",
        "|---|---|---|",
        f"| Deny-by-default authz | reviewed engine returned ALLOW / DENY / APPROVAL over HTTPS | {'PASS' if not dproblems else 'FAIL'} |",
        f"| Fail-closed masking | SSN/email redacted in response + audit row | {'PASS' if not aproblems else 'FAIL'} |",
        f"| Append-only audit (IAM) | PutItem allowed; Update/DeleteItem denied by IAM simulation | {'PASS' if not iproblems else 'FAIL'} |",
        "",
        "```json", json.dumps(sim, indent=2), "```",
    ]
    with open(os.path.join(args.out, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")

    if problems:
        print("FAIL: control problems detected:")
        for p in problems:
            print("  -", p)
        return 1
    print("PASS: all deployed controls behaved as designed. Evidence in", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
