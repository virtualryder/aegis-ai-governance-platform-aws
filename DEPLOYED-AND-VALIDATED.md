# Deployed & Validated on AWS

> This is a real deployment check, not a claim. The `infra/cloudformation/governance-core.yaml`
> stack was deployed to a live AWS account, verified at runtime, and torn down. It caught a real
> bug that `cfn-lint` did not — exactly the value of a live deploy.

**Run:** 2026-06-30 · Account `864217980669` · Region `us-east-1` · Stack `aegis-governance-core-dev`
· Pack `enterprise` · DataClass `pii`.

## Result: CREATE_COMPLETE, all controls verified, clean teardown

**Resources stood up (all serverless / pay-per-use):**
- KMS customer-managed CMK (per data class) + alias
- DynamoDB append-only audit table (`aegis-audit-pii-dev`, SSE-KMS, PITR)
- DynamoDB single-use approval ledger (`aegis-approvals-pii-dev`, TTL)
- S3 WORM evidence bucket (`aegis-worm-pii-dev-...`, Object Lock enabled, SSE-KMS, public access blocked)
- Bedrock Guardrail (`aegis-guardrail-pii-dev`) — status **READY**
- Cognito user pool + operator group
- Gateway Lambda (`aegis-gateway-pii-dev`) + least-privilege role + log group

**Runtime proofs (live API calls):**
1. **Guardrail READY** with contextual grounding (GROUNDING 0.80 / RELEVANCE 0.75), PII filters
   (EMAIL, PHONE, US_SOCIAL_SECURITY_NUMBER), and the `UngroundedConsequentialAction` denied topic.
2. **End-to-end control loop** — invoking the gateway Lambda applied the guardrail (returned
   `action: NONE` for benign input, proving the scoped `bedrock:ApplyGuardrail` permission works) and
   wrote exactly one append-only audit record (`decision=allow`, `data_class=pii`, `purpose=smoke-test`).
3. **Append-only audit proven by IAM policy simulation** on the gateway role against the audit table:
   `dynamodb:PutItem = allowed`, `dynamodb:UpdateItem = explicitDeny`, `dynamodb:DeleteItem =
   explicitDeny`. The agent cannot alter or delete audit history.
4. **WORM confirmed** — S3 `get-object-lock-configuration` returns `ObjectLockEnabled: Enabled`.

**Teardown verified:** stack deleted; `head-bucket` → 404, `list-tables` → none, `list-guardrails`
→ none; the KMS CMK entered the mandatory `PendingDeletion` window (scheduled 2026-07-07 — KMS
enforces a 7–30 day minimum; negligible cost). Zero `aegis-*` runtime resources remain.

## Real bug found and fixed (now in the repo)

**Bedrock Guardrail topic definition exceeded the 200-character service limit.** `cfn-lint` passed
the template (this is a service-side constraint, not a schema error), but the first `CREATE` rolled
back with `InvalidRequest: One or more of your guardrail topic definitions exceeds the maximum
allowed length`. The `UngroundedConsequentialAction` topic `Definition` was shortened to 157
characters in `infra/cloudformation/governance-core.yaml`, and the redeploy reached
`CREATE_COMPLETE`. This is the kind of finding only a live deploy surfaces.

## How to reproduce

See [`infra/DEPLOY-RUNBOOK.md`](infra/DEPLOY-RUNBOOK.md): `deploy.sh` → `smoke_test.sh` →
`teardown.sh`. Prerequisites: AWS credentials, `us-east-1` (CloudFront-scoped WAF variants must live
there), and Bedrock model access enabled for the account. Cost is pennies; tear down immediately.
