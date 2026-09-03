# Deployed & Validated on AWS

> This is a real deployment check, not a claim. The `infra/cloudformation/governance-core.yaml`
> stack was deployed to a live AWS account, verified at runtime, and torn down. It caught a real
> bug that `cfn-lint` did not — exactly the value of a live deploy.

**Run:** 2026-06-30 · Account `<VALIDATION-ACCOUNT-ID>` (real account ID redacted; evidence available on request) · Region `us-east-1` · Stack `aegis-governance-core-dev`
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

---

## Run 8 (2026-07-01) — Production components: KMS-signed manifests + atomic budget reservation

Two of the "offline approximations" (task #24) replaced with production AWS-backed components and
proven live:

- **KMS-asymmetric signed-manifest verification** (replaces signature-presence-only). Created an
  RSA_2048 SIGN_VERIFY KMS key, signed an agent manifest (`RSASSA_PSS_SHA_256`, 256-byte signature),
  then `kms verify` -> **valid-manifest: True**; a **tampered** manifest -> **REJECTED
  (KMSInvalidSignature)**. Key scheduled for deletion (7-day window).
- **Concurrency-safe token-budget reservation** (replaces in-memory budgets). A single conditional
  `UpdateItem` (`SET used = if_not_exists(used,:z)+:n` with `ConditionExpression used <= :room`) on a
  DynamoDB table: reserve 800 -> used **800**; a second 800 that would exceed cap 1000 ->
  **ConditionalCheckFailed (rejected)**; reserve 150 -> used **950**. Atomic conditional writes
  serialize, so concurrent reservations cannot oversell the cap. Table deleted.

Offline counterparts (real JSON-Schema validation, a manifest->Cedar compiler, local-RSA signing,
and the in-memory budget simulation) live in `platform_core/prod/` with unit tests
(`demo/test_prod_components.py`, 15 tests green). Negative-security suite
(`demo/test_negative_security.py`, 8 cases) and the extended CI (`.github/workflows/ci.yml`, cfn-lint
over all templates + all test suites) land task #25. Canonical IaC declared in `infra/CANONICAL-IAC.md`.

---

## Run 9 (2026-07-01) — Governed connector: idempotency + saga rollback

Deployed `infra/golden-pilot/connector-pilot.yaml` — a system of record (ticket store) reached only
through a governed connector Lambda with idempotency + append-only audit, wrapped in a Step Functions
saga with automatic compensation. Live:

- **Idempotency:** two `create_ticket` calls with the same `idempotency_key` -> the **same** ticket
  `TICK-e378e4fb22` (2nd `idempotent:true`), a single row in the tickets table (no duplicate write).
- **Happy saga (c1):** **SUCCEEDED**; ticket open (`create_ticket -> downstream_ok`).
- **Failure -> rollback saga (c2):** downstream failed -> saga `Catch` -> **Compensate**; execution
  **FAILED (CompensatedRollback)** and the ticket is **voided**. Audit:
  `create_ticket_before -> create_ticket_after -> downstream_failed -> compensated`.

Final system-of-record state: c1 open, b1 open (idempotent), c2 voided — no orphaned or duplicate
writes. Stands in for a real SaaS connector; swapping DynamoDB for a live API is a credentials change.
**Teardown:** connector-pi
---

## Run 10 (2026-07-07) — A real MCP-protocol gateway endpoint (portable pattern)

Deployed `infra/golden-pilot/mcp-gateway.yaml` (stack `aegis-mcp-gateway`, CREATE_COMPLETE) — the
control the platform is named for, now proven as a **live MCP JSON-RPC 2.0 endpoint** rather than
only as offline logic + individually proven controls (Runs 3/4/7). Architecture: API Gateway HTTP
API (`POST /mcp`) with a **Cognito JWT authorizer** in front of a Lambda MCP server
(`initialize`, `tools/list`, `tools/call`) with a deny-by-default tool allow-list, a
human-approval gate on consequential tools, fail-closed regex masking of tool arguments, and an
append-only DynamoDB audit sink.

Exercised live over HTTPS (all seven cases, in order):

| # | Case | Result |
|---|---|---|
| 1 | `tools/list` with **no token** | **HTTP 401** (rejected at the authorizer — never reaches the gateway) |
| 2 | `tools/list` with a **garbage token** | **HTTP 401** |
| 3 | `tools/list` with a valid Cognito ID token (JWT RS256) | allow-list returned: `kb.search_policy`, `ticket.create_draft`, `ticket.submit` |
| 4 | `tools/call kb.search_policy` with an SSN + email in the arguments | executed; audit + response show `SSN [MASKED] [MASKED]` — **masking fail-closed before audit write** |
| 5 | `tools/call payments.transfer` (**unregistered tool**) | JSON-RPC error `-32601` — "not in the allow-list (**deny-by-default**)" |
| 6 | `tools/call ticket.submit` (consequential) **without approval_id** | JSON-RPC error `-32003` — bound single-use approval required (reviewer service, Runs 5/7) |
| 7 | MCP `initialize` handshake | `aegis-mcp-gateway v0.1.0`, protocol `2025-03-26` |

> **Update (2026-07-10):** the deployed gateway template (`mcp-gateway.yaml`) no longer treats a
> *present* `approval_id` as sufficient. It now performs an **atomic single-use consume** of the
> `approval_id` against the reviewer-service ledger via a DynamoDB `ConditionExpression`
> (`attribute_exists(approval_id) AND attribute_not_exists(consumed_at) AND expires_at > now AND
> requester == sub`), so an arbitrary, replayed, expired, or unbound string is denied, and the gate
> **fails closed** if no ledger is wired. Case 6 above exercised the missing-approval deny path;
> the present-but-invalid path is now enforced by the same code.

Audit table after the run: **4 records** (2 allow, 2 deny), every record bound to the caller's
Cognito `sub`, args masked. IAM simulation on the gateway role against the audit table:
`PutItem = allowed`, `UpdateItem/DeleteItem = explicitDeny` — the audit sink is append-only at the
IAM layer, mirroring Run 1.

**What this does and does not prove.** It proves the portable MCP gateway pattern (API GW + JWT +
allow-list + HITL gate + masked append-only audit) end-to-end on a real MCP protocol surface.
The managed **AgentCore Gateway** deployment and live (non-fixture) connectors remain
customer-engagement work, per `docs/07-MCP-GATEWAY-AND-VALIDATION.md` §8.
**Teardown:** stack deleted after the run; zero `aegis-mcp-*` resources remain (verified via
CloudFormation, DynamoDB, Cognito, API Gateway list calls).

## Run 11 (2026-08-23) — CDK app live-validated: clean-account deploy of the synth output + Kill Switch enforced live

This is the run `infra/CANONICAL-IAC.md` and `infra/cdk/README.md` required before the CDK
path could claim live validation. The Python CDK app (`infra/cdk/`) was synthesized in-process
(`app.synth()`, 8 template assertions green), the emitted template was deployed **as plain
CloudFormation** (no CDK bootstrap — the `BootstrapVersion` parameter/rule stripped from the
synth output; the app has no file/image assets because the gateway handler is inline), and every
control was verified against the live account.

**Run:** 2026-08-23 · Account `111122223333` · Region `us-east-1` · Stack `aegis-governance-core`
(`dcb7b050-9f28-11f1-a9b2-1278cc123459`) · Pack `enterprise` · DataClass `pii` · 15 resources ·
`CREATE_COMPLETE` in ~80 seconds, followed by one `UPDATE_COMPLETE` (see Kill Switch note).

**Configuration proofs (live API reads):**
1. Audit table `aegis-audit-pii-dev`: keys `request_id`/`seq`, SSE-KMS on the platform CMK,
   PAY_PER_REQUEST, **PITR ENABLED** (35-day window).
2. Approvals table `aegis-approvals-pii-dev`: **TTL ENABLED** on `expires_at`.
3. WORM bucket `aegis-worm-pii-dev-<ACCOUNT_ID>`: `ObjectLockEnabled: Enabled`, all four
   public-access blocks true, default SSE-KMS with bucket key on the platform CMK.
4. Guardrail `aegis-guardrail-pii-dev` (`h02ji3st2lkd`): **READY**; PII EMAIL/PHONE → ANONYMIZE,
   US_SOCIAL_SECURITY_NUMBER → BLOCK; contextual grounding GROUNDING 0.80 / RELEVANCE 0.75;
   denied topic `UngroundedConsequentialAction`.
5. Gateway role: `AuditDenyMutations` **explicit Deny** on `dynamodb:UpdateItem`/`DeleteItem`
   against the audit table (read back from the live policy).
6. KMS CMK `4d0d3469-…`: rotation **enabled** (365-day period). Cognito pool
   `us-east-1_<REDACTED>` with the `aegis-operator` group. Kill-switch SSM parameter
   `/aegis/kill-switch` present, default disengaged.

**Runtime drills (all executed live, all audited — evidence object in the WORM bucket at
`evidence/go-live-drills/2026-08-23-governance-core-drills.json`, Object Lock GOVERNANCE
retention to 2026-09-22):**
| # | Drill | Result |
|---|---|---|
| 1 | Canary (benign prompt) | `allow`, guardrail `NONE`, audit row written |
| 2 | Prompt carrying an SSN | **HTTP 403 deny**, `GUARDRAIL_INTERVENED`, audited |
| 3 | Kill Switch engaged (`secops-oncall`) | canary → **403 deny**, `guardrail_action=KILL_SWITCH`, audited |
| 4 | Released by a **different identity** (`platform-lead`, SoD per runbook) | canary → `allow` again |
| 5 | Replay of an existing `request_id` | **refused** — `ConditionalCheckFailedException` from the append-only conditional put |
| 6 | Delete of the locked WORM evidence version | **AccessDenied** — "object protected by object lock" |

**Kill Switch is now enforced at the deployed gateway.** The live deploy surfaced that the
gateway stub wired `KILL_SWITCH_PARAM` into the environment but never read it — control 9 would
not actually deny. `infra/terraform/modules/governance_core/index.py` (the inline source the CDK
app ships) now checks the switch FIRST (short-TTL cache, 15s), denies with an audited
`KILL_SWITCH` row when engaged, and **fails closed** if the configured parameter is unreadable.
Deployments without `KILL_SWITCH_PARAM` set (the hand-written YAML, the frozen TF module as-is)
behave exactly as before; drills 3–4 above prove the live path. Exactly the class of gap only a
live deploy finds — same lesson as Run 1.

**Standing-still cost of what this run left running** (sources: aws.amazon.com/kms/pricing,
aws.amazon.com/cognito/pricing, service pricing pages): the only fixed line is the KMS CMK at
**$1.00/month** (prorated hourly). Both DynamoDB tables are on-demand and near-empty, the WORM
bucket holds kilobytes, Cognito has 0 MAU (free tier 10,000 MAU), the Lambda and Guardrail bill
only per use, and the standard-tier SSM parameter, IAM, and CloudFormation are free. Measured
platform-at-rest: **~$1/month** — under the $1–3/month figure the GTM materials quote.

**Status change:** the CDK app is now **live-validated**; `governance-core.yaml` remains
live-validated per Run 1. This stack was **left running** (not torn down) as the working
governance core for first-agent onboarding.

---

## Run 12 — 2026-08-29 · Full-observability wave + benefits agent hardening (live)

Account `111122223333` · `us-east-1` · stack `aegis-governance-core` (UPDATE_COMPLETE, 19 resources).
Layered observability deployed and verified end-to-end against the live benefits agent (`ben-demo`);
platform, benefits, PV and financial-aid templates brought to a single baseline.

**Platform (`aegis-governance-core`):**
- **Evidence trail** — one CloudTrail with advanced selectors: management-write events + DynamoDB
  data events for **all** tables + object-level events on the platform WORM bucket. Live check
  showed item-level `PutItem`/`TransactWriteItems`/`GetItem` attributed to each agent role.
- **X-Ray** on the control-plane gateway.
- **CloudWatch Logs KMS statement** added to the CMK key policy so log groups can associate the
  platform CMK — the generic ViaService statement never matches Logs (it calls KMS directly as
  `logs.<region>.amazonaws.com` under the log-group encryption context). Found live when
  `associate-kms-key` on the Bedrock invocation log group was denied. Fixed, redeployed, associated.

**Account baseline (platform runbook, one-time):** Bedrock **model-invocation logging** to a
CMK-encrypted 1-year log group (`/aegis/bedrock/model-invocations`) — full request/response bodies;
because masking runs before the model, logged prompts are de-identified.

**Agents (benefits first; PV + financial-aid ported):** X-Ray on every governed tool + a data-only
WORM-vault CloudTrail + Step Functions execution logging (`ALL`, payload-free) + unconditional 1-year
Lambda retention + the `AUDIT_BUCKET` alias the evidence writer needs.

**Governance hardening (governed-core 1.5.0):**
- **Guardrail-pinned drafting** — the drafter's direct Bedrock call now carries the platform
  guardrail. Proven live: a prompt-injection application was **intervened**
  (`AWS/Bedrock/Guardrails InvocationsIntervened=1`, guardrail version `1`), failed closed with no
  `notice_ref`, and routed to `ManualReview` — it never reached an approver.
- **Approval-path verification** — `finalize` verifies the approval was consumed by the
  identity-verifying `approve-signoff` (Cognito access-token, SoD, single-use). Proven live: a raw
  `send-task-success` bypass wrote **no `FINAL#` COMMITTED marker** and went to `ManualReview`; a
  token-verified approval committed; self-approval and a spoofed approver-string were both refused.

**One action, four independent captures (case `BEN-SYN-0002`):** a single X-Ray trace spanning the
state machine + 8 tool Lambdas; the SFN execution log (no case content); the Bedrock
invocation-log entry (`[REDACTED:NAME]`/`[REDACTED:SSN]`); and the ledger + WORM object with a
CloudTrail data event. Evidence: `benefits_eligibility_agent/evidence/OBSERVABILITY-VALIDATION-2026-08-29.md`.

**Cost delta:** roughly **+$4–5/month** at rest (platform trail S3 + DynamoDB data events at pilot
volume, data-only agent trails, X-Ray inside the free tier, invocation logging on small de-identified
payloads). The ~$1/month platform-at-rest story is unchanged.

## Run 13 — 2026-09-03 · Copilot-review hardening of the portable reference gateway (live)

Account `111122223333` · `us-east-1` · stacks `aegis-mcp-gateway-r13` (reviewed engine as a layer, ledger
attached) + `aegis-reviewer-r13` (the real reviewer service) — deployed, exercised over HTTPS, **torn down**.
Evidence: [`evidence/RUN13-BOUND-APPROVALS-ZERO-ENTITLEMENTS-2026-09-03.md`](evidence/RUN13-BOUND-APPROVALS-ZERO-ENTITLEMENTS-2026-09-03.md).

- **Zero tools without an entitlement claim (COPILOT-3).** A valid Cognito JWT with no `custom:tools` /
  `scope` claim gets `tools/list` **403** and `tools/call` **403** (before: the whole pilot tool set). The demo
  default is a template parameter (`DemoDefaultEntitlements`, default `"0"`) that is logged on every use and
  asserted OFF by the offline acceptance walk-through and by the deploy-evidence collector on the live function.
- **Approvals bound to the full action at consumption (COPILOT-2).** The reviewer stores `agent_id, tool_id,
  args_hash, purpose` on the ledger row; the gateway recomputes the binding from the actual call and checks it
  in the same atomic DynamoDB `ConditionExpression` as exists / unconsumed / unexpired / requester. Live:
  modified args → DENY, wrong tool → DENY, exact → ALLOW once (`consumed_by` = requester), replay → DENY;
  the wrong-tool approval stayed unconsumed.
- **Durable intent / outbox ordering (COPILOT-1)** landed in the reference engine the same day (offline:
  `demo/test_outbox.py`; ordering table in `GATEWAY-MODES.md`) — the portable gateway executes fixtures only, so
  there is no side effect to order live; the AgentCore packs' mirror (`AuditIntent` → `FINAL#` marker →
  `COMMITTED`) was already live in benefits.
- **Reproducible deploy-evidence pipeline (COPILOT-4).** The GitHub OIDC deploy role
  (`aegis-golden-pilot-ci-deploy`, trust scoped to `refs/heads/main` + `refs/tags/*` of this repo) is deployed and
  the repo secret set; the workflow now skips cleanly when the secret is absent instead of failing red, every
  tracked shell script is LF and `bash -n`-clean in CI, and the layer is staged + the authorizer verified on every
  push. **Green runs (OIDC, no stored keys, deploy → verify → teardown in ~3 min):** run
  [33797273003](https://github.com/virtualryder/aegis-ai-governance-platform-aws/actions/runs/33797273003)
  from `main` (`117e8ec`) and run
  [33799042751](https://github.com/virtualryder/aegis-ai-governance-platform-aws/actions/runs/33799042751)
  from the release tag **`v0.2.0`** (`4021492`) — both `control_checks.passed: true`: ALLOW / masked ALLOW /
  deny-by-default / human gate over HTTPS, zero tools without an entitlement claim (403/403, demo default `0`),
  IAM simulation `PutItem` allowed + `UpdateItem`/`DeleteItem` `explicitDeny`, audit stored masked. The evidence
  artifact of the tagged run is checked in at `infra/golden-pilot/evidence-ci/` (account redacted).
- **Release discipline (COPILOT-6).** `v0.2.0` is the first tagged release: CI built the wheel, installed it in a
  clean venv and imported it, then attached `aegis_platform_core-0.2.0-py3-none-any.whl` + `RELEASE-HASHES.txt`
  to the GitHub release.
