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

---

## Run 2 (2026-06-30) — Sample agent + human gate, end to end

Deployed `governance-core.yaml` + `sample-agent.yaml` (Step Functions Classify → Retrieve →
Draft → Check → **HumanGate (waitForTaskToken)** → Finalize) and drove one execution to completion.

**Proof the human gate holds a consequential action:**
- Execution reached `HumanGate` and **paused** (status RUNNING). Audit table showed **4** records
  (classify, retrieve, draft, check) — **Finalize did not run**.
- Acting as approver, sent the bound task token via `states:SendTaskSuccess`. Execution resumed →
  **SUCCEEDED**. Audit table then showed **5** records (finalize added).
- This demonstrates the core thesis on live infrastructure: the consequential step cannot execute
  without an explicit human approval carrying the task token.

**Two more real bugs caught by the live run (cfn-lint could not):**
1. **Cross-stack KMS access** — the agent's worker role could `PutItem` to the audit table but
   lacked `kms:Decrypt`/`GenerateDataKey` on the core CMK, so writes to the SSE-KMS table failed
   `AccessDenied`. Fixed by importing `${CoreStackName}-KmsKeyArn` into the step role.
2. **Fail-open gateway** (flagged by external review) — the control-plane Lambda wrote
   `decision=allow` and returned 200 even when the guardrail errored. Corrected to **fail closed**:
   allow only on guardrail `NONE`; any intervention/error/unavailable → `deny` (403). The offline
   gateway was hardened the same way (unregistered tool / policy / audit failure now deny), with
   `demo/test_fail_closed.py`.

**Teardown:** sample-agent then core deleted; `list-tables` → none, S3 bucket → 404, guardrails →
none; CMK in the mandatory 7-day `PendingDeletion` window. Zero `aegis-*` runtime resources remain.

> Full gap list from the four-perspective review: [`docs/GAP-CLOSURE-BACKLOG.md`](docs/GAP-CLOSURE-BACKLOG.md).

---

## Run 3 (2026-06-30) — Golden-pilot slice: real Cedar authz + real Bedrock

**Real Cedar authorization on Amazon Verified Permissions.** Deployed `infra/golden-pilot/avp-cedar.yaml`
(STRICT-validated policy store + schema + a default-deny permit implementing least-privilege
intersection + purpose + data-class boundary). Three live `is-authorized` decisions:
- Legit read (agent-granted, user-entitled, right purpose, `public`) -> **ALLOW**.
- Unpermitted consequential tool (`ticket.issue` not in agent grants, though user entitled) -> **DENY**.
- Wrong data class (`kb.search` tagged `phi`, user cleared only for `public`) -> **DENY**.
This is the production analog of `platform_core/policy_engine.py`, enforced by a live AWS service.

**Real Bedrock invocation.** `bedrock-runtime converse` on **Claude Haiku 4.5** via the
`us.anthropic.claude-haiku-4-5-20251001-v1:0` inference profile returned a real completion
(16 input / 31 output tokens) — exercising the inference-profile path that underpins chargeback.
(Claude 3 Haiku is now a Legacy model and returns access-denied; use an active model + inference profile.)

**Debugging note (real finding):** the CLI proxy drops `--cli-input-json` for `is-authorized`,
producing a false DENY with no determining policy and no errors. Passing the request as explicit
`--principal/--action/--resource/--context/--entities` `file://` flags resolved it. Captured in the
runbook so a customer SA doesn't lose an hour to it.

**Teardown:** AVP policy-store stack deleted. See `infra/golden-pilot/GOLDEN-PILOT.md` for what this
slice does and does not yet cover.

---

## Run 4 (2026-06-30) — Real identity: hardened Cognito + MFA + verified JWT -> Cedar

Deployed `infra/golden-pilot/cognito-identity.yaml` — a Cognito pool with **software-token MFA
REQUIRED** and **AdvancedSecurityMode ENFORCED** (verified live), an app client, and role groups.

- **Real MFA login end to end.** Admin auth returned an `MFA_SETUP` challenge (proving enforcement);
  associated a software token, computed a TOTP from the secret, `verify-software-token`=SUCCESS; a
  fresh login returned `SOFTWARE_TOKEN_MFA` and, on responding with a live TOTP, issued a real signed
  **ID token** with `cognito:groups=["service-desk-operator"]`.
- **Cryptographic JWT verification** (`verify_jwt.py`, RS256 against the pool JWKS + iss/aud/exp/
  token_use + alg-confusion guard): real token -> **VERIFY OK** (group extracted); tampered signature
  -> **rejected**; wrong audience -> **rejected**.
- **Identity -> authorization loop closed on AWS.** The verified `service-desk-operator` group mapped
  (`role_map.json`) to Cedar context and evaluated on Amazon Verified Permissions: read `kb.search`
  -> **ALLOW**; consequential `ticket.issue` (supervisor-only) -> **DENY**. Client-supplied roles are
  never trusted — only the cryptographically verified `cognito:groups` claim.

**Teardown:** identity + AVP stacks deleted. Details: `infra/golden-pilot/IDENTITY.md`.

---

## Run 5 (2026-07-01) — Real human-approval reviewer service

Deployed `infra/golden-pilot/reviewer-service.yaml` (pending/ledger/audit tables, a gate-opener
Lambda, a reviewer Lambda, and a `waitForTaskToken` state machine). Started an execution (requester
`operator1`) that paused at the gate, then drove the reviewer service:

- **Wrong role** (reviewer with only the operator group) -> **403 DENY**.
- **Separation of duties** (reviewer == requester) -> **403 DENY**.
- **Valid supervisor approval** (`supervisor1`, supervisor group) -> **200 APPROVE**: bound
  single-use approval written via DynamoDB conditional write, audited, `SendTaskSuccess` released the
  gate -> execution **SUCCEEDED**.
- **Replay** of the same approval -> **404** (already consumed) — single-use enforced.

Audit trail: `classify` -> `approval_denied (not supervisor)` -> `approval_denied (SoD)` ->
`approved (supervisor1, bound approval_id)` -> `finalize`. The consequential step ran only after a
valid, bound, single-use, separation-of-duties approval — the Run 2 placeholder is now a real service.

**Teardown:** reviewer-service stack deleted. Details: `infra/golden-pilot/REVIEWER-SERVICE.md`.

---

## Run 6 (2026-07-01) — Immutable evidence retention (WORM proven)

Deployed `infra/golden-pilot/evidence-worm.yaml` — an S3 bucket with Object Lock and a **default
GOVERNANCE retention rule (1 day)** so every evidence object is written WORM automatically.

- Wrote `evidence/appr-001.json`; `get-object-retention` -> **Mode GOVERNANCE, RetainUntilDate
  2026-07-02** (retention was applied, not merely enabled).
- `delete-object` on the locked version (no bypass) -> **AccessDenied: "object protected by object
  lock"** — deletion is genuinely blocked.
- Break-glass teardown: `delete-object --bypass-governance-retention` (requires
  s3:BypassGovernanceRetention) succeeded (204), then the stack was deleted cleanly.

This closes the "Object Lock enabled but no retention applied" gap. Profiles: **demo** = none;
**pilot** = GOVERNANCE (bypassable by an authorized break-glass principal, as shown); **production**
= COMPLIANCE (no deletion before expiry, even root) + legal hold + cross-account log archive.

---

## Run 7 (2026-07-01) — Reviewer front door: API Gateway + Cognito JWT authorizer

Deployed `infra/golden-pilot/reviewer-api.yaml` — the reviewer service behind an **API Gateway HTTP
API with a Cognito JWT authorizer** (hardened pool: MFA required + advanced security). The authorizer
verifies the RS256 token (issuer + audience) before the Lambda runs; the Lambda reads the **verified**
`cognito:username` / `cognito:groups` claims from `requestContext.authorizer`.

- **Unauthenticated** `POST /approvals` (no token) -> **401**; garbage bearer token -> **401**.
- **Authenticated** `POST /approvals` with a real `supervisor2` ID token (obtained via full MFA login)
  and body `{request_id}` -> **200 APPROVE** (bound approval_id, reviewer=supervisor2); the gate was
  released and the execution reached **SUCCEEDED**. Requester was `operator9`, so separation of duties
  held. Identity is taken only from the authorizer's verified claims — never from the request body.

This closes #22's front door: the reviewer service is now reachable only through an authenticated,
JWT-verified API. **Teardown:** reviewer-api stack deleted.
