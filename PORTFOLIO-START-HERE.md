# Governed Agent Platform — portfolio start-here

**One sentence.** Aegis is the **governed agent platform pattern**; SLG, HPP, HCLS, and EDU are
**vertical agent packs** that prove how the pattern applies to regulated public-sector, healthcare
payer/provider, life-sciences, and education workflows on AWS.

> 🚀 **Want to deploy it?** [`DEPLOY-EVERYTHING.md`](DEPLOY-EVERYTHING.md) is the single, copy-paste-able
> end-to-end guide: how the packs fit together, the recommended sequence, local-first testing, and the
> per-pack SAM golden-path deploy → verify → teardown.

> **What this is / is not.** A **reference field accelerator** for internal AWS enablement, customer
> architecture workshops, and scoped, synthetic-data pilots. **Not** a turnkey production solution,
> an official AWS solution, or a compliance-certified product. Every repo states its own honest
> maturity; nothing here is production-certified without customer-specific engineering, testing,
> authorization, and operational ownership. *Independent reference accelerator; not an AWS service or
> AWS-supported software; not affiliated with or endorsed by Amazon Web Services.*

## The five repositories

| # | Repo | Role | Lead with (hero pilot) |
|---|---|---|---|
| — | **aegis-ai-governance-platform-aws** | The horizontal governed-agent **platform** (the pattern all packs conform to) | Governed IT service desk / ticketing |
| 1 | **hcls-ai-agents** | Life-sciences vertical pack (pharma / biotech / medtech / CRO) — **strongest vertical asset** | Pharmacovigilance (Agent 02) or Regulatory Writing |
| 2 | **slg-ai-agents** | State & local government pack — **cleanest workshop/pilot story** | 311 resident services or IT service desk |
| 3 | **healthcare_ai_agents** (HPP) | Healthcare payer/provider pack | Patient Access, Member Services, or Revenue-Cycle Denials |
| 4 | **edu-ai-agents** | Education pack — **most candid; strongest GTM/assurance** | Student/Family Concierge or Document Accessibility |

**Do not lead with** utilization management, clinical administration, care management (HPP), benefits
or public safety (SLG) as *first* pilots — start low-blast-radius, expand once trust is established.

## Portfolio maturity (one table)

| Repo | Internal AWS pitch | Customer workshop | Scoped pilot | Production | Deployment evidence |
|---|:--:|:--:|:--:|:--:|---|
| Aegis | Strong | Strong | Medium | Not yet | 10 live AWS runs (governance core → MCP endpoint), deployed & torn down |
| HCLS | Strongest | Strong | Medium (GxP/CSV care) | Not yet | 9 golden paths deployed, run end-to-end, torn down |
| SLG | Strong | Strong | Medium-high (synthetic) | Not yet | 8 golden paths + a secure variant, deployed/validated/torn down |
| HPP | Medium-high | Medium-high | Medium (after cleanup) | Not yet | Agent 01 golden path acceptance-gated; 02–08 share templates, not individually gated |
| EDU | Medium-high | Strong | Medium | Not yet | Resource-level provisioning validated; no clean-account CFN stack stood up yet (its documented gap) |

Each repo's README carries a per-control **capability maturity matrix** (Designed / Implemented-offline
/ Deployed-on-AWS / Integration-tested / Production-ready / Owner) and a dated validation note. The
**machine-readable source of truth** for every maturity claim is each repo's **`MATURITY.yaml`**
(per-agent maturity, clean-account evidence, connector tier, test count); prose defers to it, and
`tools/check_maturity.py` flags drift. Deploy evidence is in each repo's
`evidence/CLEAN-ACCOUNT-ACCEPTANCE.md`.

## Do not pitch all agents as equally validated

This is the single most important honesty rule for the portfolio. Clean-account deploy evidence differs
sharply by pack — **lead only with what is actually validated**:

| Pack | Clean-account deploy evidence | Pitch as |
|---|---|---|
| **HCLS** | **All 9 golden paths** deployed, run end-to-end, torn down | Deploy-validated — strongest proof point |
| **SLG** | **All 8 golden paths** (+ a hardened secure variant) deployed/validated/torn down | Deploy-validated |
| **HPP** | **Only Agent 01** (Revenue-Cycle Denials) is clean-account-gated; 02–08 share templates, **not** individually gated | **Lead only with Agent 01** |
| **EDU** | **No clean-account CFN stack stood up yet** (resource-level provisioning validated; documented gap) | Workshops/envisioning — **not** deploy-validated |
| **Aegis** | Platform controls validated (10 live runs); live external SaaS connectors, monitoring, DR, prod cert **outside the repo** | Strong pattern; needs operating proof |

## Hero sequencing (lead in this order)

Do **not** open with "we have 40+ agents." Prove one governed workflow, then expand. The customer-facing
sequence, strongest evidence first:

1. **Aegis** — the governed-agent platform pattern (identity → authorization → tool access → human approval → audit → data protection → grounding → cost).
2. **HCLS Agent 02 — Pharmacovigilance ICSR intake** — the best HCLS proof point (live openFDA reference connector + scored eval + the auth walkthrough).
3. **SLG Agent 01 — Resident Services / 311** — the best public-sector proof point (live NYC 311 reference connector).
4. **HPP Agent 01 — Revenue-Cycle Denials** — the best payer/provider proof point (the only clean-account-gated HPP agent).
5. **EDU Agent 01 — Student & Family Concierge** — **only after** a clean-account deployment is completed and evidenced.

**Strongest first customer motion:** *a governed pharmacovigilance ICSR-intake pilot on AWS — Aegis controls, synthetic or de-identified adverse-event data, one live connector path, human medical review, immutable evidence.* Specific enough to move on; small enough to avoid a platform science project.

## Connector maturity — say it precisely

Everything in these repos is at connector **tiers 1–3**; **tier 4 (a customer's production system of
record — Veeva, Argus, Epic, ServiceNow, PowerSchool/Banner/Canvas, a real X12 835 feed) is NOT done
in any repo** and is engagement work. The four terms and per-agent status are in each repo's
[`docs/CONNECTOR-MATURITY.md`](CONNECTOR-MATURITY.md); the portfolio's tier-3 **live reference
connectors** (real, public, read-only) are:

| Pack | Hero agent | Live reference connector (tier 3, public) |
|---|---|---|
| HCLS | 02 Pharmacovigilance | openFDA / FAERS |
| SLG | 01 Resident Services / 311 | NYC 311 Socrata |
| EDU | 01 Student & Family Concierge | College Scorecard |
| HPP | 01 Revenue-Cycle Denials | documented X12 835 scaffold (no public denial API) |

## The governance pattern (why this belongs on AWS)

Every agent action — model call, tool call, retrieval — flows through a **deny-by-default authorization
gateway**: verified identity → least-privilege intersection (an agent never exceeds the human it acts
for) → human gate for consequential actions → fail-closed PII/PHI masking → append-only + WORM audit →
token budgets. Built on AWS-native, GA services (Bedrock + Guardrails, Cognito, Step Functions,
DynamoDB, S3 Object Lock, KMS, API Gateway, PrivateLink). The **Aegis Governance Pattern (AGP) v1.0**
is the versioned contract each pack conforms to — see
`aegis-ai-governance-platform-aws/docs/14-GOVERNANCE-PATTERN-VERSIONING.md`.

### MCP / secure gateway (state it precisely)
All tool calls pass through an **authenticated gateway** with **inbound authorization (JWT or IAM;
"no auth" is development-only, never production)**, **scoped outbound authorization** (IAM / OAuth /
token-exchange, mapping to "the agent acts only within the human's authority"), **deny-by-default
policy evaluation**, **tool registration/allow-list**, **short-lived scoped credentials**, **human
approval for consequential actions**, and **append-only audit**. In deployment this is Amazon Bedrock
AgentCore Gateway (managed) or the portable API-Gateway-+-Cognito-JWT path; the portable path is the
supported default and the one live-validated (Aegis Run 10).

## How to pitch it

**Internal (AWS):** "Customers are stuck in AI pilot sprawl. The blocker isn't the model — it's
governance: identity, tool authorization, human approval, audit, data protection, grounding, cost
control. This accelerator shows how to build a governed agent platform on AWS, then onboard agents one
at a time through the same security/compliance pattern — a repeatable regulated-industry motion that
drives Bedrock, AgentCore, Guardrails, Knowledge Bases, Step Functions, KMS, CloudTrail, Security Hub,
WAF, and PrivateLink consumption." Lead with Aegis + HCLS (aligns to the HCLS SA role).

**Customer (by persona):**
- **CIO:** a governed paved road, so every AI use case isn't a separate security review.
- **CISO:** the agent cannot take consequential action alone — authenticated gateway, deny-by-default,
  bound single-use approvals, every action audited.
- **Director of Architecture:** one repeatable AWS pattern — identity, gateway, policy,
  Bedrock/Guardrails, Step Functions, audit, WORM, IaC.

**The first pilot motion (make it painfully clear):** synthetic/de-identified data · customer AWS
account · one connector · one workflow · one approval path · one evidence report.

## Where to go next in each repo
- **Honest status (start here):** each repo's `MATURITY.yaml` (machine-readable truth) + `docs/CONNECTOR-MATURITY.md` (connector tiers) + `NOT-CLAIMS.md` (boundaries). Run `python tools/check_maturity.py` to confirm prose matches.
- **Sellers/SAs:** the per-repo `gtm/SELLER-SA-FIELD-GUIDE.md` + the demo script in the internal pitch
  kit (deny-path demo is the money shot).
- **CISO/architecture reviewers:** each repo's `assurance/README.md` (auditor packet) + `evidence/`.
- **Cost:** each repo's `offerings/TCO-MODEL.md` (run cost) + `offerings/ROI-CASE-STUDY.md` (value).
- **Deploy:** each repo's **Canonical deployment path** section (CloudFormation/SAM is canonical;
  Terraform status is documented per repo).

## Standing caveats (keep these true everywhere)
- Residency: private connectivity to **regional** AWS services via PrivateLink; no egress to external
  AI APIs. Not "data never leaves the VPC."
- Compliance: **HIPAA-eligible services under a signed BAA with customer-owned controls** — not
  "HIPAA-compliant." FedRAMP/IL authorizations belong to the **AWS services** in GovCloud, not to this
  accelerator.
- Regions: **supported AWS Regions** where the required services are available — not "any Region."
- Brand: "Built on AWS" text only; use official internal templates for internal decks and get field
  approval before any external use; do not imply an official AWS solution.
