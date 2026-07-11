# Portfolio Executive Summary — Aegis Governed-Agent Platform

*Read this first. It is the 10-minute front door to all five repositories — what the package is, what
it solves, how it works, how it stays secure and compliant, how it scales, and what is honestly true
today. Every claim here is backed by code and tests on `main`; where something is not done, it says so.*

---

## In one sentence
**Aegis is a governed-agent control-plane pattern for regulated industries on AWS, plus four vertical
agent packs (public sector, healthcare payer/provider, life sciences, and education) that prove the
pattern on real regulated workflows — so an enterprise can put AI agents next to sensitive systems
without giving them ungoverned access.**

## The problem it solves
Enterprises want to deploy AI agents against their highest-value, most-regulated workflows — claims,
prior auth, pharmacovigilance, benefits, records requests, student services. But an autonomous agent
with direct access to a system of record is a non-starter for a CISO or a regulator: no verified
identity, no least-privilege boundary, no human approval on consequential actions, no tamper-proof
audit, and a real risk of leaking PHI/PII to an external model. **The blocker to agentic AI in
regulated environments is governance, not model quality.**

## How it solves it — the governance pattern
Every agent action — model call, tool call, retrieval — flows through a **deny-by-default
authorization gateway** built on AWS-native, GA services:

> **verified identity → least-privilege intersection (agent ∩ human) → human gate for consequential
> actions → fail-closed PII/PHI masking → append-only + WORM audit → token budgets → grounded model
> gateway**

An agent never exceeds the authority of the human it acts for; consequential actions require a bound,
single-use, separation-of-duties approval consumed against a durable ledger; sensitive fields are
masked before any model call; and every decision is written to an immutable, hash-chained audit with
IAM-enforced no-delete. This is the **Aegis Governance Pattern (AGP) v1.0** — the versioned contract
each vertical pack conforms to.

## What's in the box
| Repo | Role | Lead hero (live reference connector) |
|---|---|---|
| **aegis-ai-governance-platform-aws** | The horizontal governed-agent **platform / pattern** | Governed IT service desk |
| **hcls-ai-agents** | Life sciences (pharma/biotech/CRO) — strongest vertical asset | Pharmacovigilance ICSR intake (openFDA/FAERS) |
| **slg-ai-agents** | State & local government | Resident Services / 311 (NYC 311) |
| **healthcare_ai_agents** (HPP) | Healthcare payer/provider | Revenue-Cycle Denials (X12 835 scaffold) |
| **edu-ai-agents** | K-12 & higher education | Student & Family Concierge (College Scorecard) |

## Security & regulatory posture (built-in, not bolted-on)
- **Identity:** RS256/JWKS JWT verified server-side; client-supplied roles are never trusted.
- **Authorization:** deny-by-default, least-privilege intersection; consequential tools withheld from every agent in code.
- **Human-in-the-loop:** bound, single-use, SoD approvals consumed against a durable ledger.
- **Data protection:** fail-closed masking (mandatory NER for real data); no silent PHI/PII egress; Bedrock reached over PrivateLink under the AWS BAA.
- **Auditability:** append-only, hash-chained audit; IAM denies delete; WORM S3 Object Lock; split signing keys.
- **Supply chain / CI:** pinned lockfiles, blocking `pip-audit`, cfn-lint, secret scanning.
- **Regulatory alignment (engineering, not certification):** HIPAA Security Rule, FERPA/COPPA, CJIS, GxP / 21 CFR Part 11 — mapped to implementing controls in each pack; authorization (ATO/HITRUST/FedRAMP) remains customer-owned under the AWS shared-responsibility model.

## How it scales to more agents
Adding an agent is a **manifest + conformance** operation, not a rebuild. Each agent declares its
identity, tool grants, consequential bright-lines, and data classes in a schema-validated
`agent.manifest.yaml`; a scaffolder refuses to emit a non-conformant agent; the platform mediates all
access through the same gateway. Today each vertical ships **one deep hero agent + governed workflow
scaffolds** — deliberately, so trust is proven on one low-blast-radius workflow before expanding.

## Positioning vs. Amazon Bedrock AgentCore
AgentCore now provides the managed **Gateway, Identity, Policy (Cedar), and Evaluations** primitives.
**Aegis is the regulated-industry governance *overlay and vertical packs* on top** — deny-by-default
intersection semantics, bound single-use SoD human approvals, WORM/immutable audit evidence, and the
compliance packs (GxP/Part 11, HIPAA, FERPA, CJIS) that horizontal primitives don't provide. Aegis
models both the managed-AgentCore path and a portable API-Gateway + Cognito path. (See the
AgentCore-overlay one-pager / slide.)

## What is honestly true today (and what isn't)
- ✅ **Real, tested governance:** ~1,324 offline tests green across the portfolio, incl. negative-control suites; golden-path SAM deploys are cfn-lint-clean with clean-account acceptance tests that demonstrate the controls firing; honest, machine-checked maturity.
- ◻ **The AI is deterministic-by-default:** the *governance* is the product; the agents are governed reference workflows with one real model path per hero. This is disclosed, not hidden.
- ◻ **Not production-certified:** no ATO/HITRUST/FedRAMP; tier-4 live systems-of-record connectors, IdP federation, pen test, DR/monitoring are customer-engagement work.

## The ask / go-to-market motion
Approve the package for **internal AWS enablement and customer architecture workshops now**, and for
**scoped, synthetic-data pilots** on the hero agents. Lead with one governed hero per vertical
(Pharmacovigilance → 311 → Denials → Concierge), prove the controls live, then expand. Do **not** open
with "40+ agents" — prove one governed workflow, earn trust, scale.

*Companion docs: [`AWS-INTERNAL-REVIEW-PACKET.md`](AWS-INTERNAL-REVIEW-PACKET.md) ·
[`CUSTOMER-SAFE-DEMO-SCRIPT.md`](CUSTOMER-SAFE-DEMO-SCRIPT.md) ·
[`PORTFOLIO-MATURITY-SCORECARD.md`](PORTFOLIO-MATURITY-SCORECARD.md) ·
[`DO-NOT-CLAIM.md`](DO-NOT-CLAIM.md)*
