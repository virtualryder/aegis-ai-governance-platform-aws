# 04 — Agent Onboarding Standard

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> The contract every agent — first-party or third-party add-on — must satisfy to run on Aegis.
> The goal: a department or vendor knows *exactly what to build toward as a minimum*, and the
> platform can refuse anything that doesn't meet the bar. Machine-readable schema:
> [`../governance/onboarding/agent-manifest.schema.json`](../governance/onboarding/agent-manifest.schema.json).
> The bar itself: [`../governance/onboarding/MINIMUM-BAR.md`](../governance/onboarding/MINIMUM-BAR.md).

## 1. The agent manifest (the single source of truth)

Every agent ships a signed `agent.manifest.yaml`. It is the contract the gateway enforces and the
artifact CI validates. It declares:

```yaml
apiVersion: aegis/v1
kind: Agent
metadata:
  id: permitting-precheck
  owner: dept-planning            # cost-allocation + chargeback owner
  packs: [slg]                    # compliance overlay packs that must be active
  classification: [public, pii]   # data classes this agent may touch
grants:                            # least-privilege; intersected with the human's entitlement
  tools:
    - id: accela.read_permit       # MCP tool id (registered in the gateway tool registry)
      scope: read
    - id: kb.search_policy
      scope: read
  consequential:                   # actions WITHHELD from the agent; human-gated only
    - accela.issue_permit
grounding:
  knowledge_base: kb-zoning-code   # required grounding source(s) for RAG
  grounding_threshold: 0.85        # contextual-grounding minimum (0–0.99)
budget:
  monthly_token_cap: 50_000_000    # hard cap; gateway rejects over-budget calls
  inference_profile: aip-planning-precheck   # Bedrock application inference profile (chargeback)
  alert_thresholds: [0.6, 0.85, 1.0]
evals:
  suite: evals/permitting-precheck/   # required pass before promotion
  min_pass_rate: 0.95
human_gate:
  mode: step_functions_wait_for_task_token
  separation_of_duties: true
signing:
  publisher: planning-dept
  signature: <cosign/JWS>
```

## 2. The minimum bar (what CI enforces before an agent can touch a system of record)

An agent is **rejected** unless every item is true. These are gates, not guidelines.

1. **Declared scope, nothing more.** The manifest enumerates every tool/MCP server and data class.
   CI fails the build if the code attempts any tool or class not in the manifest.
2. **Consequential actions withheld in code.** Any issue/adjudicate/release/award/transfer action is
   absent from the agent's grants and only reachable via the human gate. A test proves it.
3. **A bound, single-use, separation-of-duties human gate** is wired for every consequential action.
4. **A grounding source is declared** and the contextual-grounding threshold is set; no
   ungrounded free-generation against systems of record.
5. **A token budget with a hard cap and an inference profile** is declared (no unbounded spend; spend
   is attributable — see [`05-FINOPS-…`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md)).
6. **An eval suite passes** at the declared rate (accuracy, refusal, fairness/four-fifths,
   prompt-injection resistance, accessibility for user-facing output).
7. **Masking is on for every declared data class** and fails closed.
8. **The manifest is signed** by a known publisher; the gateway verifies the signature at load.
9. **Pack compatibility** — the agent declares which compliance packs it requires; deploy fails if a
   required pack is not active in the target environment.

> The bar is deliberately the *floor*. It is the minimum a department or ISV builds toward; clearing
> it is what makes an agent portable across every Aegis environment.

## 3. Onboarding flow — one agent at a time

```
Author manifest  →  Register tools/MCP servers in the gateway registry  →  Wire grounding KB
   →  Write evals  →  CI gate (the minimum bar)  →  Deploy to a sandbox env (synthetic data)
   →  Shadow / canary against documented outcomes  →  Promote with budget + pack bound
   →  Day-2: drift checks, budget alerts, eval re-runs on model/prompt change
```

New **models** onboard the same way: a model is registered, its inference profile + guardrail policy
attached, and agents reference it by profile ARN — so swapping or adding a model is a config change,
not a re-architecture. New **MCP servers/tools** are registered in the gateway tool registry with
their scopes and validation rules before any agent may reference them (see
[`07-MCP-GATEWAY-AND-VALIDATION.md`](07-MCP-GATEWAY-AND-VALIDATION.md)).

## 4. Why this is the unlock for the add-on / marketplace model

Because the manifest + minimum bar are uniform, an agent built by any team or vendor is a **portable
product**. Dropping a packaged agent into a customer's Aegis environment automatically inherits that
customer's identity, data classes, guardrails, budgets, packs, and audit — there is no per-customer
governance re-build. That is what lets you *package and sell agents as add-ons across industries*
with governance already in place. The commercial model is in
[`08-GTM-AND-POSITIONING.md`](08-GTM-AND-POSITIONING.md).

## 5. Who cares & why

- **Architect / platform team:** a published contract means departments self-serve onboarding without
  bespoke review each time.
- **CISO:** nothing reaches a system of record without clearing the bar; scope is enforced, not trusted.
- **CIO / CFO:** every agent arrives with a budget and an owner attached — no ungoverned, unfunded sprawl.
- **ISV / department building an agent:** a single, testable target to build toward.
