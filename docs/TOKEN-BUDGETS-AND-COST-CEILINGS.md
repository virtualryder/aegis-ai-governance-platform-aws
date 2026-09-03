# Token budgets and cost ceilings — what is enforced today, what is only tracked, and how a customer sets "never exceed $X"

*Written 2026-09-02 against the deployed + live-validated tree (benefits `v0.3.0-pilot-rc1`, governed-core
1.7.1, platform `aegis-governance-core` stack). Every claim below is labelled **LIVE** (deployed and exercised
with real requests), **OFFLINE** (implemented and unit-tested in `platform_core`, not wired into a deployed
path), or **NOT BUILT**. The diagram (`docs/ARCHITECTURE-DEPLOYED.drawio`) uses the same labels.*

## 1. The short version a buyer needs

| Question | Today's honest answer |
|---|---|
| Can you tell me, per tenant, per case, per session, how many tokens the model used and on which calls? | **LIVE.** Every Bedrock invocation is logged with `inputTokenCount` / `outputTokenCount`, tagged `tenant` / `session_id` / `case_id` / `requester` (`requestMetadata`), and every Strands model span carries `gen_ai.usage.*` with the same keys. Proven on two tenants: `benefits evidence/AGENTCORE-OBSERVABILITY-2026-09-02.md`, `AGENTCORE-111-GATE-2026-09-02.md`. |
| Can you stop a tenant or agent that is about to blow its budget **before** the spend happens? | **OFFLINE only.** `platform_core/token_budget.py` is a real fail-closed meter (`preflight()` denies when a hard cap would be exceeded; 60/85/100 % alerts; `commit()` after spend) and the benefits manifest declares its budget line (`budget: monthly_token_cap 5,000,000, cap_behavior hard`) — but **no deployed component reads that block or runs that meter**. In the deployed AgentCore path nothing denies a call for budget reasons today. |
| Can you put a hard dollar ceiling on the account? | **NOT BUILT in the stacks.** AWS Budgets (with an action) is the account-level mechanism the FinOps doc names; no stack creates one. It is a ~10-line CDK addition, listed in §4. |
| Can you charge a department/tenant back? | **Tracked LIVE, allocated OFFLINE.** The per-tenant token counts above are the meter; `platform_core/chargeback.py` turns them into a bill offline. Cost-allocation tags on the stacks (`app`, `env`, `cost-center`, tenant stacks tagged) feed Cost Explorer / CUR with the usual ≤24 h lag. |

So: **tracking is live and per-tenant; capping is designed, tested and declared, but not enforced live.**
Say that sentence to a customer; do not say "we enforce token budgets" until §4 lands.

## 2. What exists, exactly

### 2.1 LIVE — measurement

- **Bedrock model-invocation logging** (`-c model_logging=1`, `ObservabilityStack`): every `Converse` /
  `ConverseStream` row with the exact request/response bodies, `modelId`, `inputTokenCount`,
  `outputTokenCount`, and `requestMetadata` = `{tenant, session_id, case_id, requester, governed_by}`
  injected by the runtime (`lib/runtime/agent.py::_bedrock_session`). Filterable per tenant without reading
  bodies. Account+region level; opt-in because it is a singleton.
- **Runtime spans** (ADOT + Strands): `chat <model>` spans with `gen_ai.usage.input_tokens` /
  `output_tokens`, `session.id`, `tenant`, `case_id`; joined to the log rows by `aws.request_id` =
  `requestId` (`scripts/trace_case.py`, `model_invocations_joined_to_spans` 5–7/5–7 on both tenants).
- **Per-tenant physical isolation of the evidence** so the meter's inputs cannot be cross-attributed:
  the WORM record for each governed action carries the same keys (`correlation` block, hashed).

### 2.2 OFFLINE — enforcement logic that exists but is not wired

- `platform_core/token_budget.py` — `BudgetMeter(monthly_token_cap, cap_behavior='hard'|'soft', alert_thresholds)`
  with `preflight(requested_tokens) -> BudgetDecision(allowed, throttled, fired_alerts)` and `commit(actual)`;
  `BudgetRegistry` for many lines. Fail-closed on budget. Unit-tested.
- `platform_core/kill_switch.py` — engaging the switch **zeroes every registered budget meter** (belt and
  suspenders). Unit-tested (`demo/test_kill_switch.py`).
- `platform_core/chargeback.py` — department/tenant allocation from usage records. Unit-tested.
- Benefits manifest `budget:` block — a *declaration* the delivery checklist requires; `render.py` ignores it,
  the CDK ignores it, the runtime ignores it. It documents intent, it enforces nothing.

### 2.3 NOT BUILT

- A live per-tenant meter (durable counter) in the AgentCore path.
- AWS Budgets (cost) with a budget action.
- A dollar conversion of tokens (a pinned price table per model) inside the platform.

## 3. Where a live cap has to sit in the deployed architecture

Two hops make model spend: the **runtime** (Strands → Bedrock, every model call) and the **gateway**
(every tool call; tools such as `draft_notice` call Bedrock server-side). The enforcement points that
already exist on every request are therefore:

1. **The runtime agent, before each model call** — it already owns the per-invocation correlation set and
   the boto session that tags every call; a `preflight` there can deny a session that would exceed the
   tenant's remaining budget and can `commit` the real `usage` from each Converse response.
2. **The gateway REQUEST interceptor, before each tool call** — it already derives the tenant and injects the
   signed pair; a budget/kill-switch check there denies (403, audited) before the target Lambda runs.
3. **The durable meter** — a small DynamoDB table `<prefix>-budgets` keyed `tenant#YYYY-MM` with
   `tokens_in`, `tokens_out`, `usd_estimate`, `cap_tokens`, `cap_usd`, `behavior`; written from the
   model-invocation log (authoritative, async) and from the runtime (real-time, optimistic).
4. **The account backstop** — AWS Budgets on the tagged resources with an action that **engages the Kill
   Switch** (SSM parameter) at 100 %, so the dollar ceiling is enforced even if a meter is bypassed.

Dollars: `usd = tokens_in × price_in(model) + tokens_out × price_out(model)` from a **pinned price table**
committed with the release (prices change; the table's date is part of the evidence), reconciled monthly
against the CUR (the financial truth) exactly as `05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md` §6 says.

## 4. The build to make "never exceed $X" true (tracked as tasks)

| # | Item | Effect for the customer | Proof required |
|---|---|---|---|
| B1 | `BudgetsTable` per deployment + pinned model price table; runtime `commit()` after every model call; model-log → meter reconciler Lambda | per-tenant running total in tokens **and USD**, visible on the dashboard | two tenants, counts match the model-invocation log |
| B2 | Runtime `preflight()` before each model call; interceptor budget check before each tool call; `cap_behavior: hard` ⇒ **403 / refused, WORM-recorded** ("budget exceeded") | a tenant that hits its cap is stopped before the next model call | live: set a 1,000-token cap on tenant B, run the agent, observe the refusal + WORM record; tenant A unaffected |
| B3 | 60 / 85 / 100 % CloudWatch alarms per tenant → SNS (existing ops topic) | early warning before the hard stop | alarms fire in the live run |
| B4 | AWS Budgets (USD) for the account/tag with an action → engage `/aegis/kill-switch` | the dollar ceiling holds even if a meter is bypassed | budget action wired (Budgets fires on real billing data; simulate via `describe-budget-action`) |
| B5 | Manifest `budget:` block becomes the source of the caps the CDK deploys (`-c tenants=` → per-tenant caps) | one place to set the number | synth test |

Until B2 lands the Kill Switch (`docs/ops/KILL-SWITCH.md`) is the only *hard* stop, and it stops everything,
not one tenant.
