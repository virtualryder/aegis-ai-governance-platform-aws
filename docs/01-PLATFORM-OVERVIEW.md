# 01 — Platform Overview (start here)

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> The "understand it in five minutes" doc. For the full edge-to-data design see
> [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md); for the candid go-live picture see
> [`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md). Every factual and compliance
> claim traces to [`../SOURCES.md`](../SOURCES.md).

## What Aegis is

Aegis is a **governance layer for AI agents** built on AWS-native, generally-available services. It
sits between your agents and your systems of record, so that **the governance — not the agent — is
the product**. You build one governed "paved road," and every future agent, model, and MCP tool
inherits identity, authorization, audit, data-class isolation, hallucination control, token budgets,
and departmental chargeback automatically.

The platform is two things stacked together: an **industry-agnostic governance core**, plus
**pluggable compliance overlay packs** (SLG, Education, Healthcare-Life-Sciences, Enterprise) that
switch on the right controls, regions, retention, and evidence for a given regime. Agents are
onboarded one at a time against a published **minimum bar**, and because governance is inherited, a
packaged agent becomes a **portable product** you can drop into any already-governed environment.

## The problem it solves: the pilot trap

Most AI-agent programs stall after the pilot. Each new agent becomes its own project — its own
auth, its own audit story, its own data-handling review, its own cost surprise — so scaling means
re-doing governance N times, and finance, security, and legal each have to re-approve every agent.
That is the pilot trap: working demos that never become a fundable, repeatable, review-survivable
program.

Aegis breaks it by making governance a **one-time, inherited platform investment** instead of a
per-agent tax. The CISO reviews the paved road once. The CFO gets per-department chargeback once.
The architect maintains one reference pattern instead of eight integrations. Every subsequent agent
arrives with an owner, a budget, a scope, and an audit trail already attached.

## The platform in five layers

Summarized from the [README](../README.md) and [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md):

| # | Layer | What it does | Key AWS services |
|---|---|---|---|
| 1 | **Edge & identity** | TLS, WAF/OWASP rules, DDoS absorption; federated IdP issuing short-lived JWTs with verified role claims | CloudFront, AWS WAF, Shield, Cognito, API Gateway |
| 2 | **Governed control plane (the core)** | Deny-by-default MCP authorization gateway: least-privilege *intersection*, scoped per-call tokens, human gate, token-budget check, append-only audit | AgentCore Gateway (or API Gateway + policy engine) |
| 3 | **Reasoning & grounding** | In-account inference with mandatory Guardrails (PII filters + contextual grounding + automated reasoning) and governed RAG | Bedrock over PrivateLink, Bedrock Guardrails, Bedrock Knowledge Base |
| 4 | **Data & evidence** | Per-data-class keys, immutable audit, WORM evidence, fail-closed masking, class isolation (CJI/FTI/PHI/EDU/public) | KMS CMK, DynamoDB, S3 Object Lock, Macie, Comprehend |
| 5 | **FinOps & observability** | Per-department cost attribution and chargeback; continuous monitoring and tracing | Application inference profiles + cost-allocation tags → Cost Explorer/CUR; CloudTrail, GuardDuty, Security Hub, Config, X-Ray |

The control plane (layer 2) is the load-bearing idea: **an AI agent that can touch a system of
record is a governance, audit, and least-privilege problem before it is a model problem.**

## Why each persona cares

| Persona | Their question | How Aegis answers it |
|---|---|---|
| **CIO / CDO** | "How do I escape the pilot trap and scale safely without a project per agent?" | One paved road; onboard agent-by-agent on a funded, repeatable pattern. |
| **CISO** | "Can the AI act on its own? Is identity trustworthy? Will the audit hold up? Where does data go?" | Consequential actions withheld in code + human gate; cryptographic identity; append-only WORM audit; in-account inference with Guardrails. |
| **Director / Chief Architect** | "Is this one maintainable pattern or eight integrations?" | A single reference architecture, IaC, and a standard agent manifest — no per-agent re-architecture. |
| **CFO / Budget owner** | "How do I control and allocate AI spend?" | Token budgets with hard caps + per-department showback/chargeback via application inference profiles and cost-allocation tags. |
| **CEO / Agency head** | "What's the business case and the risk story?" | Documented per-workflow outcomes + a candid shared-responsibility model that survives a review board. |

## Relationship to the predecessor repo

Aegis generalizes the SLG-focused accelerator
[`virtualryder/slg-ai-agents`](https://github.com/virtualryder/slg-ai-agents). The verdict of the
review was **generalize, do not rebuild**: the SLG accelerator is already a strong, honest,
controls-first reference, with a proven deny-by-default gateway, framework-enforced human gate,
tamper-evident audit, in-account Bedrock + Guardrails, and real deployment maturity (eight agents as
one-command golden paths, deployed and torn down on a live AWS account).

Aegis lifts that governance core out of the SLG framing and makes it industry-agnostic via overlay
packs, then adds the layers the predecessor lacked: a **FinOps layer** (token budgets + chargeback),
a **published agent-onboarding contract** (signed manifest + minimum-bar CI gate), **Education and
HCLS regimes**, **automated reasoning checks** on top of grounding, and an explicit target of
**AgentCore Gateway** as the production control plane. What carries forward verbatim, what is new,
and the remediation plan are in [`09-REPO-REVIEW-slg-ai-agents.md`](09-REPO-REVIEW-slg-ai-agents.md).

## Where to go next

- **Architecture** — [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md)
- **Compliance packs** — [`03-COMPLIANCE-OVERLAY-PACKS.md`](03-COMPLIANCE-OVERLAY-PACKS.md)
- **Onboarding an agent** — [`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md)
- **FinOps** — [`05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md)
- **Hallucination & evaluation** — [`06-HALLUCINATION-AND-EVALUATION.md`](06-HALLUCINATION-AND-EVALUATION.md)
- **MCP gateway & tool validation** — [`07-MCP-GATEWAY-AND-VALIDATION.md`](07-MCP-GATEWAY-AND-VALIDATION.md)
- **Go-to-market & positioning** — [`08-GTM-AND-POSITIONING.md`](08-GTM-AND-POSITIONING.md)
- **Honest readiness & RACI** — [`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md)

## What this is, and is not

Aegis is a **reference platform for architecture workshops, scoped pilots, and AWS/customer
positioning** — not an AWS-authorized, ATO'd, production-certified system. Live connectors,
production identity integration, third-party security testing, and authorization (ATO / GovRAMP /
FedRAMP) are customer-engagement work, captured honestly in
[`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
