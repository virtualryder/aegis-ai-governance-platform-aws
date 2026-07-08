# Clean-Account Acceptance Report — Aegis Governed Agent Platform

Sanitized deployment evidence for the ten live runs claimed in
[`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md). Validation account ID and IAM
user are redacted; raw CLI JSON is available on request. All verification queries were read-only.

**Account:** `<VALIDATION-ACCOUNT-ID>` · **Region:** us-east-1 · **Verified:** 2026-07-07/08 via AWS CLI.

## 1. CloudFormation stack lifecycle (from the stack API + CloudTrail)

Every stack reached CREATE_COMPLETE, was exercised, and reached DELETE_COMPLETE:

| Stack | Created (UTC) | Deleted (UTC) | Run |
|---|---|---|---|
| aegis-governance-core-dev | Jun 30 20:06 / 20:13; Jul 1 02:44 | Jun 30 20:09; Jul 1 02:16 / 02:54 | 1, 2 |
| aegis-sample-agent-dev | Jul 1 02:46 | Jul 1 02:53 | 2 |
| aegis-golden-pilot-avp | Jul 1 03:44 / 04:11 | Jul 1 03:50 / 04:12 | 3 |
| aegis-golden-pilot-identity | Jul 1 04:05 | Jul 1 04:12 | 4 |
| aegis-reviewer-service | Jul 1 04:25 | Jul 1 04:30 | 5 |
| aegis-evidence-worm | Jul 1 13:14 | Jul 1 13:16 | 6 |
| aegis-reviewer-api | Jul 1 13:18 | Jul 1 13:26 | 7 |
| aegis-connector-pilot | Jul 1 14:23 | Jul 1 14:27 | 9 |
| aegis-mcp-gateway | Jul 8 00:26 | Jul 8 00:31 | 10 |

CloudTrail management events corroborate: 11 `CreateStack` + matching `DeleteStack` events, all
issued by the validation IAM user; 6 Step Functions `StartExecution` events during the Run 2/9
windows (workflows were *run*, not just provisioned). Run 8 used ad-hoc KMS + DynamoDB resources
(no stack), confirmed via KMS key history.

## 2. KMS deletion markers (observed live, 2026-07-07)

Four Aegis CMKs were still visible in `PendingDeletion` on verification day — AWS's own record
that the keys existed and were torn down with a deletion window as designed:
three "Aegis CMK for data class pii (aegis/dev)" keys (scheduled deletion Jul 7–8) and one
"Aegis manifest signing (demo)" RSA key from Run 8 (scheduled Jul 8).

## 3. Run 10 — live MCP-protocol gateway (2026-07-07)

`infra/golden-pilot/mcp-gateway.yaml`: API Gateway HTTP API (`POST /mcp`) + Cognito JWT authorizer
→ Lambda MCP JSON-RPC 2.0 server. Exercised live over HTTPS:

| Case | Result |
|---|---|
| No token / garbage token | HTTP 401 (rejected at the authorizer) |
| `tools/list` (valid JWT) | 3-tool allow-list returned |
| `tools/call kb.search_policy` with SSN+email in args | executed; `[MASKED]` in response and audit |
| `tools/call payments.transfer` (unregistered) | JSON-RPC −32601 deny-by-default |
| `tools/call ticket.submit` without approval | JSON-RPC −32003 bound-approval required |
| `initialize` | `aegis-mcp-gateway v0.1.0`, protocol 2025-03-26 |

Audit table: 4 records (2 allow / 2 deny), each bound to the caller's Cognito `sub`.
IAM simulation on the gateway role vs the audit table: `PutItem = allowed`,
`UpdateItem/DeleteItem = explicitDeny` (append-only at the IAM layer).

## 4. Residual state after all runs

Zero application stacks, DynamoDB tables, API Gateway APIs, or Aegis Cognito pools remain.
Only tooling artifacts persist (SAM-managed artifact bucket, CloudTrail logs bucket).

## 5. Method

Read-only CLI: `cloudformation list-stacks/describe-stacks`, `cloudtrail lookup-events`
(CreateStack / ExecuteChangeSet / DeleteStack / StartExecution), `kms list-keys/describe-key`,
`dynamodb list-tables/scan`, `cognito-idp list-user-pools`, `apigatewayv2 get-apis`,
`iam simulate-principal-policy`. Portfolio-level export:
`Projects-DR/evidence/AWS-CLEAN-ACCOUNT-EVIDENCE-2026-07-07.md` (kept outside the repo).
