# 09 — Review of `virtualryder/slg-ai-agents` and the Path to This Platform

> Source reviewed: the public README and repository map of
> [`github.com/virtualryder/slg-ai-agents`](https://github.com/virtualryder/slg-ai-agents)
> (reviewed 2026-06-30). Verdict up front: **do not rebuild — generalize.** The SLG accelerator is
> already a strong, honest, controls-first reference. Aegis lifts its governance core out of the SLG
> framing, makes it industry-agnostic via overlay packs, and adds the layers it doesn't yet have.

## 1. What the existing repo already does well (carry forward)

- **Deny-by-default MCP authorization gateway** with least-privilege as an intersection
  (`permitted ⇔ agent grant ∩ user entitlement`). This is the right core and is reused verbatim.
- **Consequential actions withheld in code** + a **framework-enforced human gate** (Step Functions
  `waitForTaskToken` / `interrupt_before`), with **bound, single-use, separation-of-duties** approvals.
- **Tamper-evident audit** — append-only DynamoDB (PutItem-only IAM, conditional writes) + S3 Object
  Lock WORM; **fail-closed masking** of PII/CJI/FTI.
- **In-account Bedrock + mandatory Guardrails over PrivateLink**, governed RAG over a Bedrock
  Knowledge Base (retrieval as an audited read).
- **Cryptographic identity** (RS256 over Cognito JWKS, issuer/audience/expiry + alg-confusion guard).
- **Real engineering maturity** — 8 agents as one-command SAM golden paths, **deployed and torn down
  on a live AWS account** (caught two real bugs the offline suite missed), a no-API-key test suite
  with control-plane negative cases, IaC parity (CloudFormation + Terraform, commercial + GovCloud).
- **Security & compliance package** — threat model, NIST 800-53 control matrix, OWASP-LLM/ATLAS
  mapping, incident-response/key-management docs, machine-readable control mappings.
- **Intellectual honesty** — an explicit production-readiness + RACI doc and a remediation plan;
  it never claims to be ATO'd or production-certified. *Keep this candor; it's a selling feature.*

## 2. Honest gaps in the existing repo (what Aegis adds)

| Gap | Evidence in the repo | What Aegis adds |
|---|---|---|
| **SLG-only framing** | Everything is named/scoped to State & Local Gov; compliance is SLG regimes. | Industry-agnostic **governance core** + **overlay packs** (SLG, Education, HCLS, Enterprise). |
| **No FinOps / token budgets / chargeback** | README control set and architecture do not mention token caps or per-department cost attribution. | **Token budgets with hard caps** in the gateway + **chargeback via Bedrock application inference profiles + cost-allocation tags** ([`05`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md)). |
| **No published agent-onboarding contract** | Agents are hand-built to a shared pattern; no formal manifest/minimum-bar that a third party builds toward. | **Signed agent manifest + minimum-bar CI gate** ([`04`](04-AGENT-ONBOARDING-STANDARD.md)) — the unlock for the add-on/marketplace model. |
| **No Education or Life-Sciences regimes** | FERPA appears; COPPA(2025), 42 CFR Part 2, GxP/21 CFR Part 11 do not. | **Education** and **Healthcare-Life-Sciences** packs ([`03`](03-COMPLIANCE-OVERLAY-PACKS.md)). |
| **Gateway is a reference model, not AgentCore** | README states the production AgentCore/API GW + Cedar authorizer "must be tested, not just the analog." | Targets **AgentCore Gateway** (GA 2025-10-13; MCP + IAM/OAuth) as the production control plane, with the readable engine kept for offline test. |
| **Hallucination control = grounding only** | Governed RAG + Guardrails present; no mention of **automated reasoning** checks. | Adds Bedrock **automated reasoning checks** (formal logic) on top of contextual grounding ([`06`](06-HALLUCINATION-AND-EVALUATION.md)). |
| **No live connectors / ATO** (acknowledged) | README lists these as tracked engagement work. | Unchanged — these remain customer-engagement work; Aegis keeps the same honest RACI ([`10`](10-PRODUCTION-READINESS-RACI.md)). |

## 3. Concrete remediation/improvement plan to make it deployment-ready

Prioritized; each item is independently shippable.

**P0 — Generalize the core (this repo)**
1. Extract `platform_core` + `governance` + `gov_platform` into the industry-agnostic Aegis core;
   move SLG specifics into `packs/slg`.
2. Introduce the **agent manifest schema** + CI minimum-bar gate; retrofit the 8 SLG agents to ship
   manifests (proves the contract against real agents).

**P1 — Close the named gaps**
3. Add the **FinOps layer**: provision application inference profiles per agent/dept, route all
   inference through profile ARNs, add the gateway token-budget check + AWS Budgets actions.
4. Add **automated reasoning checks** to the guardrail policy alongside contextual grounding.
5. Build the **Education** and **HCLS** packs; switch the masker entity sets (COPPA biometric,
   Comprehend Medical for PHI) by pack.

**P2 — Production hardening (was already on their backlog)**
6. Replace the reference gateway with **AgentCore Gateway** (or API GW + Cedar) and test *that*,
   keeping the Python engine as the offline analog.
7. Build **at least one live connector** end-to-end (e.g. ServiceNow or a 311/CRM) to retire the
   "integrations are fixtures" gap — usually the largest line item.
8. Commission **third-party security testing** (pen test, threat-model review) and stand up the
   accessibility CI (axe-core + manual) ahead of the ADA Title II deadlines.

**P3 — Authorization path**
9. Produce the **GovRAMP/FedRAMP control package** from the control matrix; begin the customer-owned
   ATO process. Pursue the AWS BAA for HCLS deployments.

## 4. Recommendation

Stand up this repository as the platform, port the SLG accelerator's proven core into it as the
governance core + `packs/slg`, and treat the SLG agents as the first set of manifest-conformant
agents that validate the onboarding standard. This preserves all the existing engineering value and
honesty while delivering the horizontal, multi-industry, FinOps-aware, add-on-ready platform the
business case requires.
