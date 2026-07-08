# 10 — Production Readiness & Shared-Responsibility (RACI)

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). **Updated 2026-07-08
> to reconcile with the ten-run evidence in [`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md).**
> **Deployed and live-validated on AWS:** append-only audit, WORM enablement, Bedrock Guardrail, human
> gate, fail-closed gateway (Run 1–2); **Cedar policy enforcement** (Verified Permissions, Run 3);
> **identity/MFA federation** (Cognito MFA + JWT verification, Run 4); **atomic token budgets** (Run 8);
> the reviewer service + API-Gateway JWT authorizer (Runs 5/7); and a **live MCP JSON-RPC endpoint**
> (Run 10). **Still offline reference / customer-engagement work:** ML-based runtime masking (the
> deployed masker is the deterministic regex analog), live (non-fixture) external-SaaS connectors, and
> enterprise IdP (SAML/OIDC) federation login. Per-control detail is in the README maturity matrix and
> `GAP-CLOSURE-BACKLOG.md`.

> The candid doc. Aegis is a **reference platform for architecture workshops, scoped pilots, and
> AWS/customer positioning** — not an AWS-authorized, ATO'd, production-certified system. This page
> states plainly what gives confidence today, what must still be built or authorized before go-live,
> and who owns each item across **AWS**, the **Delivery Partner**, and the **Customer**. The candor is
> a selling feature, not a disclaimer. Grounded in [`../SOURCES.md`](../SOURCES.md) §1, §5, §6.

## 1. What gives confidence today

The governance core is implemented and testable, not vaporware. Inherited from the proven SLG
accelerator (see [`09-REPO-REVIEW-slg-ai-agents.md`](09-REPO-REVIEW-slg-ai-agents.md)) and generalized
here:

- **Deny-by-default authorization gateway** with least-privilege as an intersection
  (`permitted ⇔ agent grant ∩ user entitlement`) — the agent can never exceed the human it acts for.
- **Consequential actions withheld in code** + a framework-enforced **human gate** (Step Functions
  `waitForTaskToken` / `interrupt_before`) with **bound, single-use, separation-of-duties** approvals.
- **Tamper-evident audit** — append-only DynamoDB (PutItem-only IAM, conditional writes) + S3 Object
  Lock WORM; **fail-closed masking** of PII/PHI/FTI/CJI.
- **In-account Bedrock + mandatory Guardrails over PrivateLink**, governed RAG, plus **contextual
  grounding** and **automated reasoning** checks (see [`06`](06-HALLUCINATION-AND-EVALUATION.md)).
- **Cryptographic identity** (RS256 over Cognito JWKS, issuer/audience/expiry + alg-confusion guard).
- **Agent manifest + minimum-bar CI gate** ([`04`](04-AGENT-ONBOARDING-STANDARD.md)) and a tool
  registry with validation/revocation ([`07`](07-MCP-GATEWAY-AND-VALIDATION.md)).
- **FinOps**: token budgets with hard caps + chargeback via application inference profiles and
  cost-allocation tags ([`05`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md)).
- **IaC parity** (CloudFormation + Terraform, commercial + GovCloud), and a no-API-key test suite with
  control-plane negative cases. The predecessor's stack was deployed and torn down on a live AWS
  account, which caught two real bugs the offline suite missed.

## 2. What must still be built or authorized before go-live

These are **not** platform-guaranteed and must be completed during a customer engagement:

- **Live connectors are fixtures.** Tool backends are simulated; at least one live connector (e.g.
  ServiceNow, a 311/CRM) must be built end-to-end to retire the "integrations are fixtures" gap. This
  is usually the largest line item.
- **No ATO / GovRAMP / FedRAMP.** AgentCore is **pursuing FedRAMP** and aligns with HITRUST, but the
  platform is not authorized. Authorization is a customer-owned process built from the control package.
- **No third-party security testing.** No independent penetration test or threat-model review has been
  commissioned.
- **Model-risk validation.** Eval gold sets, fairness baselines, and guardrail/red-team tuning are
  customer-owned and workflow-specific.
- **BAA for HIPAA.** AgentCore/Bedrock are **HIPAA-eligible**, which is **not** the same as
  HIPAA-compliant. A signed **AWS Business Associate Addendum (BAA)** plus customer-implemented
  controls are required before any PHI workload.
- **Production IdP integration.** Cognito federation to the customer's real IdP (Entra ID, Okta,
  PingFederate, Login.gov) and MFA enforcement are customer-configured.
- **Retention schedule.** WORM/Object-Lock durations must be set to the customer's records-retention
  and legal-hold schedule per regime.
- **HITL queue staffing.** The human gate is wired in code, but the people, SLAs, and rotation that
  staff the approval queue are an operational commitment the customer must make.

> **"HIPAA-eligible" ≠ "HIPAA-compliant."** The same logic applies to every regime: the platform
> implements the *technical* controls and maps them to the framework, but authorization,
> agreements (BAA), and operational ownership are customer responsibilities.

## 3. RACI matrix

**R** = Responsible (does the work) · **A** = Accountable (owns the outcome) · **C** = Consulted ·
**I** = Informed. "Delivery Partner" = the AWS Partner / SI standing up the engagement.

| # | Item | AWS | Delivery Partner | Customer |
|---|---|---|---|---|
| 1 | **Authorized cloud / region** (commercial, GovCloud) | A/R | C | I |
| 2 | **BAA for HIPAA** (signed before any PHI) | R (provides) | C | A |
| 3 | **Live connectors** to systems of record | I | R | A |
| 4 | **IdP integration + MFA** (Entra/Okta/Ping/Login.gov via Cognito) | I | R | A |
| 5 | **Data classification** (CJI/FTI/PHI/EDU/public) + class isolation | I | C | A/R |
| 6 | **ATO / GovRAMP / FedRAMP authorization** | C (FedRAMP path) | R (control package) | A |
| 7 | **Guardrail tuning** (grounding thresholds, automated-reasoning policy) | C | R | A |
| 8 | **Red-team / prompt-injection testing** | I | R | A |
| 9 | **Retention schedule** (WORM/Object-Lock durations, legal hold) | I | C | A/R |
| 10 | **Model-risk validation** (eval gold sets, fairness baselines) | I | C | A/R |
| 11 | **Accessibility testing** (axe-core + manual, ADA Title II) | I | R | A |
| 12 | **Third-party penetration test** | I | C | A/R |
| 13 | **Day-2 operations** (monitoring, drift checks, IR runbooks) | C | C | A/R |
| 14 | **Chargeback reconciliation** (gateway meter vs CUR truth) | I | C | A/R |
| 15 | **Compliance pack selection** (which regimes are active) | I | C | A/R |
| 16 | **Agent manifests** (scope, grants, budget, grounding, evals) | I | C | A/R |
| 17 | **Tool registration / revocation** (registry, scopes, provenance) | I | R | A |
| 18 | **HITL queue staffing** (approvers, SLAs, separation of duties) | I | I | A/R |
| 19 | **Encryption keys** (KMS CMK lifecycle per data class) | C (KMS service) | C | A/R |
| 20 | **Shared Responsibility boundary** (security *of* vs *in* the cloud) | A (of cloud) | C | A (in cloud) |

## 4. Gated go-live checklist

Go-live is **gated** — each item must be green before an agent touches production data. No item may be
waived silently; a waiver is itself an audited, accountable decision.

- [ ] **Authorized region** selected and provisioned (GovCloud for High-impact / CJI / FTI).
- [ ] **Signed BAA** in place (if any PHI) — *blocks all PHI workloads until done.*
- [ ] **Compliance pack(s)** selected and active for the target environment.
- [ ] **Production IdP** federated through Cognito; **MFA enforced** (mandatory for CJI under CJIS v6.0).
- [ ] **Data classification** completed; class isolation (account/VPC/key) verified.
- [ ] **At least one live connector** built, tested end-to-end, and registered in the tool registry.
- [ ] **Guardrail policy tuned**: grounding thresholds set per agent; automated-reasoning policy authored.
- [ ] **Eval suite passing** at the declared rate (accuracy, refusal, fairness, injection, a11y).
- [ ] **Red-team / prompt-injection** testing completed; findings remediated.
- [ ] **Accessibility testing** passed for any public-facing agent.
- [ ] **Third-party penetration test** completed; criticals/highs remediated.
- [ ] **Retention schedule** configured on WORM/Object-Lock per the customer's records policy.
- [ ] **Token budgets** set with hard caps + alert thresholds; **chargeback reconciliation** process agreed.
- [ ] **HITL queue staffed** with approvers, SLAs, and separation of duties.
- [ ] **Day-2 runbooks** in place (monitoring, drift checks, eval re-runs on model/prompt change, IR).
- [ ] **Authorization path** underway (ATO / GovRAMP / FedRAMP control package produced).

## 5. Who cares & why

- **CISO / Authorizing Official:** an honest gap list and an explicit RACI are exactly what a review
  board needs; nothing is hand-waved, and every customer-owned control is named.
- **CIO / Program owner:** the checklist is a fundable, sequenced path from reference platform to
  authorized production, not an open-ended research project.
- **CFO:** the boundary between platform-provided and customer-owned work is explicit, so engagement
  scope and cost are knowable up front.
- **CEO / Agency head:** the candor — "HIPAA-eligible ≠ HIPAA-compliant," "no ATO yet" — is what makes
  the rest of the platform's claims credible.
