# 05 — FinOps: Token Budgets, Caps & Departmental Chargeback

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> The #1 reason finance kills an AI program is that spend is unbounded and can't be attributed.
> Aegis makes token spend **visible, capped, and fairly charged back**. This is built on AWS-native
> cost primitives — see [`../SOURCES.md`](../SOURCES.md) §2.

## 1. The two problems and the two mechanisms

| Problem | Mechanism | AWS primitive |
|---|---|---|
| **"Token maxing"** — one runaway agent/prompt burns the budget | **Token budgets with hard caps**, enforced in the gateway *before* spend | Gateway budget check + per-agent inference profile |
| **Chargeback** — one department uses a model, another foots the bill | **Per-department cost attribution → showback/chargeback** | **Application inference profiles** + **cost-allocation tags** → Cost Explorer / CUR |

## 2. Chargeback: how a department gets billed for its own usage

Amazon Bedrock **application inference profiles (AIPs)** let you attribute `InvokeModel`/`Converse`
costs by application, team, or workload. Each AIP is model-specific and carries **cost-allocation
tags** that flow to **AWS Cost Explorer** and the **Cost and Usage Report (CUR / CUR 2.0)**. You call
the model using the **profile ARN in place of the model ID**, and the profile's tags are attached to
the billing record for every request.

**In Aegis:**
- Each agent declares an `inference_profile` and an `owner` in its manifest (see
  [`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md)).
- The platform provisions one AIP per owning department/agent with tags:
  `dept`, `team`, `app`, `data_class`, `pack`.
- All inference is routed through the AIP ARN — never a raw model ID — so **100% of model spend is
  tagged at the source**.
- Cost Explorer (filter/group by tag) and CUR line items produce the **monthly chargeback report**
  per department. (Tags can take up to 24h to appear after activation.)
- For finer attribution, **IAM principal-based cost allocation** attributes Bedrock cost by caller
  identity as a cross-check.

```
agent call → gateway (budget check) → AIP ARN (tagged dept/team/app) → Bedrock
                                              │
                                              └─ billing record carries tags
                                                     → Cost Explorer / CUR → chargeback report
```

## 3. Token budgets & caps: stopping spend before it happens

Cost attribution is *after the fact*; budgets must act *before*. The gateway enforces a real-time
budget check on every call:

- Each agent/department has a `monthly_token_cap` and `alert_thresholds` in its manifest.
- The gateway maintains a running token meter (input+output tokens, by agent/dept) and **rejects or
  throttles** calls that would breach the cap — *fail-closed on budget*, with a clear denial reason in
  the audit record.
- Threshold alerts (e.g. 60% / 85% / 100%) fire to the owner via the event bus / SNS, and (optionally)
  **AWS Budgets** actions provide a second, account-level guardrail on actual dollar spend.
- Soft vs hard caps are policy: a soft cap warns and continues; a hard cap denies. Departments can
  request a temporary lift through an audited approval — same human-gate machinery.

Example policy: [`../governance/finops/budget-policy.example.yaml`](../governance/finops/budget-policy.example.yaml).

## 4. Cost-control levers the platform also gives you

- **Model right-sizing per task** — cheap model for classify/route, premium model only where it earns
  its keep; the inference profile makes the cost of each choice visible.
- **Prompt-caching and retrieval discipline** — governed RAG limits context bloat (fewer tokens).
- **Caps per data class** — high-sensitivity classes can carry tighter budgets and stricter review.
- **Showback before chargeback** — start by showing departments their usage (behavior changes fast),
  then enforce chargeback once the data is trusted.

## 5. Who cares & why

- **CFO / budget owner:** a defensible, usage-based cost model — departments pay for what they use,
  with hard caps so a single agent can't blow the quarter.
- **CIO:** turns "AI spend is a black hole" into a line-item-attributable, fundable program — the
  argument that gets the next agent funded.
- **Department head:** transparency — you see your own consumption and can plan against your cap.
- **CISO:** budget denials and lift-approvals are audited like any other gateway decision.

## 6. Honest limits

AIP cost-allocation tags can lag up to 24h in Cost Explorer/CUR, so the *real-time* control is the
gateway token meter; the *financial truth* is the CUR. Reconciliation between the two is a standard
day-2 FinOps practice. Mapping AIP coverage across every Bedrock API surface is a customer validation
item per [`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
