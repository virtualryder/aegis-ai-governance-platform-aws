# Token budgets and cost ceilings — what is enforced live, what is estimated, and how a customer sets "never exceed $X"

*Rewritten 2026-09-03 after task 128 landed (governed-core 1.9.0, benefits main). Every claim is labelled **LIVE**
(deployed and exercised with real requests; evidence cited), **OFFLINE** or **NOT BUILT**. The diagram
(`docs/ARCHITECTURE-DEPLOYED.drawio`) uses the same labels. The 2026-09-02 version of this document — when
capping was OFFLINE — is in git history; §4 below is the build list it promised, with each item's status.*

## 1. The short version a buyer needs

| Question | Today's honest answer |
|---|---|
| Can you tell me, per tenant, per case, per session, how many tokens the model used and on which calls? | **LIVE.** Every Bedrock invocation is logged with `inputTokenCount` / `outputTokenCount` tagged per tenant / session / case (`requestMetadata`), every Strands model span carries `gen_ai.usage.*`, and — since 2026-09-03 — a **per-tenant meter** (`<prefix>-budgets`, DynamoDB) holds the running `tokens_in / tokens_out / usd_micro / calls` per tenant per month, written from the real Converse `usage` of every model call. Proven: the meter's totals **equal** the model-invocation log's totals for the same session (`benefits evidence/AGENTCORE-BUDGET-2026-09-03.md`). |
| Can you stop a tenant that is about to blow its budget **before** the spend happens? | **LIVE.** Before every model call the Runtime makes ONE conditional DynamoDB reservation against the tenant's cap; a call that would breach a **hard** cap is refused — including **mid-session** (proven: a capped tenant's session stops at the first model call that no longer fits). A tenant at/over its cap is also refused at the gateway REQUEST interceptor (403 + DENIED WORM record) and on the workflow hop (the drafter refuses → `ManualReview`). Cap 0 switches a tenant off with one PutItem. |
| Can you put a hard dollar ceiling on the account? | **LIVE (as the AWS mechanism allows).** `-c budget_usd=<dollars>` creates an AWS Budgets monthly COST budget on Amazon Bedrock with an **APPLY_IAM_POLICY action** (automatic) that attaches a `Deny bedrock:InvokeModel*` policy to the Bedrock-calling roles at 100 % actual, and a notification whose subscriber (the budget-breach function) **engages the kill switch** (WORM-audited, IAM-verified actor — proven with a synthetic notification). **Honest limit:** AWS Budgets is *not* real-time — AWS: budgets are "updated up to three times a day … 8–12 hours after the previous update" — so the dollar ceiling is the backstop; the real-time guard is the meter's USD cap (`cap_usd_micro`, from the pinned price table), which refuses before the spend. |
| What price does the meter use? | An **estimate** from a **pinned price table** committed with the release (`benefits/lib/model_prices.json`), whose `price_version` is recorded on every commit. Provenance stated in the file: Anthropic models are not in the AWS Price List API and the Bedrock pricing page is not machine-readable, so the table is pinned from Anthropic's published pricing and marked *UNCONFIRMED-ON-BEDROCK* until confirmed against the Bedrock pricing page for the customer's region. The financial truth is the Cost and Usage Report. |
| Can you charge a department/tenant back? | **Metered LIVE, allocated OFFLINE.** The meter is per tenant per month in tokens and estimated USD; `platform_core/chargeback.py` turns usage into a bill offline; cost-allocation tags feed Cost Explorer / CUR (≤24 h lag). |

So: **tracking, capping and alerting are live and per-tenant; the dollar figure is a pinned estimate; the account
backstop is AWS Budgets with its documented delay.** Say exactly that to a customer.

## 2. What exists, exactly (2026-09-03)

### 2.1 LIVE — measurement (unchanged from 2026-09-02)

- Bedrock model-invocation logging with `requestMetadata` per tenant / session / case; runtime spans with
  `gen_ai.usage.*`; per-tenant physically separate evidence (`correlation` block in every WORM record).

### 2.2 LIVE — the meter and the caps (governed-core 1.9.0 `budget.py`, benefits main)

- **Table** `<prefix>-budgets`, key `<tenant>#<YYYY-MM>`: `used`, `reserved`, `tokens_in`, `tokens_out`,
  `usd_micro`, `calls`, `price_version`, `model_id`; optional overrides `cap_tokens`, `cap_usd_micro`, `behavior`.
- **Runtime** (`lib/runtime/agent.py`, governed-core installed in the image): `reserve(tenant, 4000)` before every
  model call (one conditional `ADD used :n` with `used <= cap - :n` — DynamoDB serialises conditional writes per
  item, so concurrent sessions cannot oversell); `commit(tenant, usage)` after every call with the real Converse
  `usage` (`streaming=False` so the parsed response carries it); the meter converges to the truth.
- **Gateway REQUEST interceptor**: `check(tenant)` on every `tools/call` — at/over cap ⇒ 403 + `DENIED
  budget.deny` record in that tenant's ledger; `tools/list` stays free.
- **Drafter** (`draft_notice`, the server-side Bedrock call): `reserve` before / `commit` after; a refusal returns
  `guardrail_action: BUDGET` and the controller routes to `ManualReview`.
- **Defaults** from the manifest `budget:` block through the CDK (`BUDGET_CAP_TOKENS`, `BUDGET_BEHAVIOR`),
  `-c budget_usd` for the USD cap, `lib/model_prices.json` for prices — B5 done: one place to set the number.
- **Alarms**: `Aegis/Budget` `TokensUsedPct` / `UsdUsedPct` per Tenant+Deployment → 60 / 85 / 100 % alarms on
  the ops topic (B3).
- **Rules**: hard = fail-closed (an unreadable meter denies); soft = flag + alert only; the reservation
  estimate is the only over-count and it is corrected by the commit.

### 2.3 LIVE — the account backstop (B4)

`-c budget_usd` ⇒ AWS Budgets COST budget (Amazon Bedrock) + `APPLY_IAM_POLICY` action (automatic) targeting the
drafter role and the Runtime exec role (`-c runtime_role`) + notification → ops topic → `budget-breach` function →
kill-switch engage (IAM-verified actor, WORM row). Not real-time by AWS design (see §1).

### 2.4 OFFLINE / NOT BUILT

- `platform_core/token_budget.py` and `chargeback.py` remain the offline analogs (unit-tested; not deployed).
- A **scheduled reconciler** that re-derives the meter from the model-invocation log is NOT BUILT — the proof
  reconciles them by script (`scripts/budget_proof.py`, `meter_equals_model_invocation_log`).
- **Bedrock-confirmed prices**: the price table is pinned from Anthropic's published pricing; confirming it
  against the Bedrock pricing page per region is a release step, not code.
- Executing the AWS Budgets action outside a real breach: `ExecuteBudgetAction` is refused while the action is in
  STANDBY (`ResourceLockedException`, seen live), so the IAM-attach path is proven by configuration
  (`describe-budget-action`) and the notification path by a synthetic message, not by real billing data.

## 3. Where the cap sits (as deployed)

Runtime (before every model call) → gateway interceptor (before every tool call) → drafter (before its own
model call) → durable meter (`<prefix>-budgets`) → AWS Budgets backstop → kill switch. Dollars =
`tokens_in × price_in + tokens_out × price_out` from the pinned table, reconciled monthly against the CUR.

## 4. The build list from 2026-09-02, with status

| # | Item | Status 2026-09-03 | Proof |
|---|---|---|---|
| B1 | `<prefix>-budgets` + pinned price table; runtime `commit()` after every model call; reconciliation with the model log | **LIVE** (reconciler = script, not scheduled) | meter == model-invocation log (rows, tokens_in, tokens_out); USD == pinned table |
| B2 | Runtime `reserve()` before each model call; interceptor check; drafter check; hard ⇒ refused + WORM DENIED | **LIVE** | tenant B cap 0: gateway 403, runtime refused, workflow → ManualReview; tenant A stopped mid-session at the call that no longer fits |
| B3 | 60 / 85 / 100 % alarms per tenant → ops topic | **LIVE** | alarms fire in the live run |
| B4 | AWS Budgets USD ceiling with an action → kill switch | **LIVE (configuration + synthetic notification)** | action wired (APPLY_IAM_POLICY, AUTOMATIC); breach → kill switch engaged → 403 → released by a second identity |
| B5 | Manifest `budget:` block is the source of the caps the CDK deploys | **LIVE** | synth test + live env (`BUDGET_CAP_TOKENS` = manifest value) |

Evidence: `benefits/evidence/AGENTCORE-BUDGET-2026-09-03.md`. The kill switch (`docs/ops/KILL-SWITCH.md`) remains
the deployment-wide stop; the budget is the per-tenant one.

### 4.1 Two findings the gate surfaced (closed the same day)

1. **The drafter's refusal on the workflow hop was not landing in the ledger.** The Step Functions `DraftNotice`
   task has no gateway interceptor in front of it, so the drafter Lambda refuses a capped tenant itself and writes
   the DENIED record — but the drafter's role only had Bedrock + case-store grants (by design: it is not one of the
   ledger writers). The refusal worked (fail-closed, `ManualReview`), the record silently did not (`stored: false`,
   `AccessDenied` on `GetItem` — visible only in the 0-unexpected-errors sweep, which is why the sweep exists).
   Fix: the drafter gets the same *append-only* grant the interceptor has (`PutItem` + `GetItem` + `TransactWriteItems`,
   mirrored per tenant; `UpdateItem` / `DeleteItem` stay implicit-deny — verified with `SimulatePrincipalPolicy`).
   The gate now asserts the drafter's DENIED row (joined by the execution ARN in its correlation block — R3-2: the
   drafter never sees a case id).
2. **The drafter's model-invocation rows were not per-tenant filterable.** The Runtime tags every `Converse` with
   `requestMetadata` (tenant, session, case); the drafter's server-side `Converse` did not, so a run that used
   `draft_notice` could not be reconciled from the log by tenant (the meter counted 7 calls, the session-tagged log
   rows summed 6). Fix: the drafter tags its call with `{tenant, component=draft_notice, trace_id, execution_arn,
   request_id}` — correlation keys only, never content, never a case id — and the gate sums the log by
   `requestMetadata.tenant` (Runtime + drafter rows) after the delivery lag has settled.
