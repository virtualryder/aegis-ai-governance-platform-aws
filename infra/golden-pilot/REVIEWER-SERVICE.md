# Human-Approval Reviewer Service (task #22)

> Replaces the Run 2 placeholder human gate with a real authenticated reviewer service.
> Deployed + live-tested on AWS account 864217980669 (us-east-1) on 2026-07-01, then torn down.

## What is real now (`reviewer-service.yaml`)

A gate-opener Lambda writes the Step Functions **task token** + request context to a
`pending-approvals` table when a `waitForTaskToken` gate opens. The **reviewer Lambda** then, on an
approval request, enforces in order:

1. **Verified-supervisor role** — the reviewer's groups (delivered as VERIFIED claims by an API
   Gateway Cognito JWT authorizer in production; see `verify_jwt.py`) must contain
   `service-desk-supervisor`, else 403.
2. **Separation of duties** — approver != requester, else 403.
3. **Bound, single-use approval** — `approval_id = sha256(request_id|agent|tool|args_hash|purpose|
   requester)` written to the `approval-ledger` with a DynamoDB conditional write; a replay fails the
   condition and is rejected (409), and once the gate is consumed a repeat is 404.
4. **Append-only audit** of every outcome (denied / approved).
5. **`states:SendTaskSuccess`** with the approval evidence — releasing the gate so `Finalize` runs.

## Live results (2026-07-01)

| Attempt | Reviewer | Result |
|---|---|---|
| Wrong role (operator group) | supervisor1 w/ operator group | **403 DENY** (lacks supervisor role) |
| Separation-of-duties | operator1 (== requester) | **403 DENY** (approver == requester) |
| Valid approval | supervisor1 w/ supervisor group | **200 APPROVE** → gate released → execution **SUCCEEDED** |
| Replay | supervisor1 (again) | **404** (already consumed) — single-use |

Audit trail for the request: `classify` (seq 0) → `approval_denied: not supervisor` (90) →
`approval_denied: SoD` (91) → `approved: reviewer=supervisor1` (seq 1) → `finalize` (seq 2).
The consequential `Finalize` step executed **only** after a valid, bound, single-use, SoD approval.

## Not yet included (tracked in ../../docs/GAP-CLOSURE-BACKLOG.md)

The API Gateway HTTP API + Cognito JWT authorizer front door (tested here via direct Lambda invoke
with the verified claims the authorizer would inject), a reviewer web UI, approve/reject reasons +
escalation + SLA/timeout notifications, and recovery when the approval service or Step Functions is
unavailable.
