# 08 — Go-to-Market & Positioning

> The narrative for taking Aegis to a customer's leadership **and** to AWS leadership. Grounded
> figures are cited in [`../SOURCES.md`](../SOURCES.md); SLG outcome figures carry their evidence
> tier from the predecessor accelerator.

## 1. The one-sentence positioning

> **Aegis is the governance layer that makes any AI agent deployable in a regulated environment —
> build the paved road once on AWS, and every agent, model, and tool inherits identity,
> authorization, audit, compliance, hallucination control, and chargeback automatically.**

## 2. The problem we sell against

Organizations are stuck in the **pilot trap**: a chatbot per department, each its own integration,
security review, and audit; spend nobody can attribute; and no governed path from pilot to production.
The blocker is **not the model** — it's identity, authorization, audit, data-class isolation,
hallucination risk, cost control, and *who has authority to act*. Every regulated buyer — government,
education, healthcare, enterprise — has the same shape of problem with a different regime on top.

## 3. The "why now"

- **AgentCore went GA (Oct 2025)** — the AWS-native primitives for a governed agent control plane
  (Gateway with MCP + IAM/OAuth, Identity, VPC/PrivateLink) now exist; this is buildable today.
- **Bedrock & AgentCore are HIPAA-eligible**, AgentCore is **pursuing FedRAMP** and aligns with
  HITRUST — the compliance substrate is moving fast.
- **Regulatory clocks are ticking:** CJIS v6.0 audits began Oct 2025; amended COPPA compliance is due
  Apr 2026; ADA Title II accessibility deadlines are 2026–2027. Buyers need governed AI *now*.
- **GovRAMP's 2025 rebrand** explicitly widened scope to local gov, K-12, higher ed, and hospitals —
  one posture now travels across the whole public sector.

## 4. The master deck structure (modular: exec core + audience appendices)

A single deck with a shared executive core and swappable appendices. Build target:
[`05-...build the deck...`] → produced as `Aegis-Master-Deck.pptx`.

**Executive core (everyone):**
1. Title — Aegis: the governed agent platform on AWS.
2. The pilot trap (the problem, with the "90% piloting / 25% funded" framing).
3. The insight — the agent isn't the product; governance is.
4. What Aegis is — the five layers, one diagram.
5. The AWS reference architecture (edge→data) — the money slide.
6. How it solves the five hard problems — authorization, hallucination, audit, cost, onboarding.
7. Compliance overlay packs — one platform, every regime.
8. The add-on model — package once, deploy anywhere governed.
9. Proof & honesty — what's real, what's customer-owned (the RACI in one slide).
10. The ask / next step.

**Appendix A — Customer CIO/CISO/Architect:** the security-review walkthrough, control→regime matrix,
the four CISO questions and their answers, first-90-days plan.

**Appendix B — AWS field/leadership:** consumption (ACR) story, Marketplace add-on motion, where it
pulls Bedrock/AgentCore/GovCloud, co-sell and differentiation.

## 5. Talking points by persona (use verbatim)

**CISO — "Can the AI act on its own?"**
> "No. Every consequential action — issue, adjudicate, release, award, transfer — is withheld from the
> agent in code and proven absent by a test. It executes only after a bound, single-use,
> separation-of-duties human approval. Identity is cryptographically verified; client-supplied roles
> are never trusted. The audit is append-only and WORM, and PII/PHI/FTI is masked fail-closed. Bedrock
> inference stays in-account over PrivateLink with mandatory guardrails."

**CIO — "How do I get out of the pilot trap?"**
> "You build the governance once and every future agent inherits it. Start with one low-blast-radius
> agent, prove it against a documented outcome, and scale on a paved road that's already funded and
> compliant. No re-architecture per agent; no re-doing security review per agent."

**Director of Architecture — "Is this maintainable?"**
> "One reference pattern reused across every agent: edge → Cognito JWT → MCP gateway (deny-by-default +
> scoped token) → Bedrock + guardrails → human gate → append-only WORM audit. IaC in CloudFormation
> and Terraform, commercial and GovCloud. Readable, AWS-native, no black box, no lock-in."

**CFO — "How do I control and allocate the spend?"**
> "Every agent runs through a tagged Bedrock application inference profile, so 100% of model spend is
> attributed to the owning department and charged back from Cost Explorer / the CUR. The gateway
> enforces hard token caps in real time, so one runaway agent can't blow the quarter."

**CEO / Agency head — "What's the business case and the risk story?"**
> "Documented outcomes per workflow, a candid shared-responsibility model that survives a review
> board, and a platform that turns AI from a pile of risky pilots into a governed, fundable program."

## 6. First-customer playbook

1. **Qualify for a low-blast-radius first agent** — IT service desk or resident/customer services,
   *not* benefits or public safety first. Decision-support, reversible, high volume, clear ROI.
2. **Run a discovery + architecture workshop** — map their IdP, data classes, regimes → select packs.
3. **Stand up the standalone golden path** in their account (own VPC, edge, Cognito, KMS, WORM, gateway,
   agent) with synthetic data; demo the human gate, the audit, the masking, the budget cap live.
4. **Prove against a documented outcome** (e.g. self-service deflection economics; cycle-time cut).
5. **Sign the shared-responsibility plan** (RACI) so security review has no surprises.
6. **Land-and-expand** — add agents one at a time on the same paved road; turn on chargeback;
   introduce the orchestration layer when ≥2 agents are live.

## 7. Positioning to AWS (why AWS leadership should co-sell)

- **It pulls the right services:** Bedrock + Guardrails, **AgentCore** (Gateway/Identity/Runtime),
  GovCloud, KMS, Macie/Comprehend, the cost/FinOps stack — durable, consumption-generating workloads.
- **It accelerates regulated-industry adoption** — the exact segments (gov, HCLS, education) where AWS
  wins on compliance breadth (HIPAA-eligible, HITRUST, GovCloud, FedRAMP path).
- **It's a Marketplace motion** — packaged add-on agents become Marketplace listings that deploy onto
  the governed platform, an ISV/partner flywheel.
- **It de-risks the customer's security review**, which is the real blocker to Bedrock consumption in
  regulated accounts — so it converts stalled pilots into funded production.

## 8. The add-on / marketplace commercial model

- **Platform** (Aegis core + packs) — the governed paved road; sold/deployed per environment.
- **Add-on agents** — packaged, manifest-conformant agents sold as products; each inherits the
  customer's governance on deploy (see [`04`](04-AGENT-ONBOARDING-STANDARD.md)). Priced per agent /
  per seat / per usage; chargeback makes consumption transparent.
- **Why it compounds:** every new pack opens an industry; every new agent is sellable into every
  existing governed customer with zero governance rework. The moat is the governance, not the agent.

## 9. Objection handling (short)

- *"Is this production-ready?"* — "It's a production-shaped accelerator with the hard controls built
  and tested; live connectors, ATO/GovRAMP, and third-party security testing are scoped engagement
  work. That candor is why the rest is credible." (See [`10`](10-PRODUCTION-READINESS-RACI.md).)
- *"Why not just use a model vendor's console?"* — "A console doesn't give you least-privilege
  intersection, a human gate withheld in code, WORM audit, per-department chargeback, or a compliance
  pack that survives a review board."
- *"Lock-in?"* — "Readable code, AWS-native GA services, IaC you own in your account."
