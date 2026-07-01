# 03 — Compliance Overlay Packs

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> The governance core is industry-agnostic. A **pack** is a declarative bundle
> (`packs/<pack>/pack.yaml`) that, when applied, switches on the right controls, AWS regions,
> retention, masking entity sets, guardrail policy, and evidence artifacts for a regime — and
> marks each control **[Impl]** platform-implemented vs **[Cfg]** customer-configured.
> All packs inherit the core controls in [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md)
> and map to **NIST 800-53** and the **NIST AI RMF Generative AI Profile (NIST AI 600-1)**.

## How a pack works

A pack is applied at deploy time and at runtime:
- **Deploy time** — selects region (commercial vs GovCloud), CMK topology, retention schedule on
  S3 Object Lock, the Macie/Comprehend entity sets to detect, and the Guardrail policy to attach.
- **Runtime** — the gateway loads the pack's control profile so authorization, masking, grounding
  thresholds, and audit fields match the regime. Multiple packs compose (e.g. a county hospital may
  apply `healthcare-lifesciences` + `slg`).

Every pack ships an **evidence map**: for each control, the artifact an assessor can inspect (a test,
an IaC resource, a config, or a named owner). This is what makes a pack survive a review board.

---

## `packs/slg` — State, Local & Public Sector

**Regimes:** GovRAMP (formerly StateRAMP) / FedRAMP, CJIS Security Policy v6.0, IRS Pub 1075 (FTI),
NIST AI RMF, ADA Title II / WCAG 2.1 AA.

| Regime | What the pack does | Tier |
|---|---|---|
| **GovRAMP / FedRAMP** | Deploy on AWS authorized regions (GovCloud High / US Moderate); inherit boundary, identity, audit controls; produce a control matrix for the package. *Authorization itself (ATO) is customer-owned.* | [Cfg] |
| **CJIS v6.0** | CJI account/VPC isolation; **MFA mandatory** (v6.0, audited since 2025-10-01); deny-by-default gateway; scoped tokens; masked, append-only audit; continuous monitoring (new in v6.0). | [Impl]/[Cfg IdP] |
| **IRS Pub 1075 (FTI)** | FTI isolation account; FTI masking; dedicated KMS CMK; access logging; WORM retention. | [Impl]/[Cfg] |
| **NIST AI RMF** | Grounding + prompt registry + evals + red-team + fairness + HITL gates wired to Govern/Map/Measure/Manage. | [Impl] |
| **ADA Title II / WCAG 2.1 AA** | Accessibility checks on AI output in CI (Title II deadlines Apr 2026/2027 by entity size). | [Impl] |

**Why a public-sector buyer cares.** GovRAMP's 2025 rebrand explicitly expanded its scope to local
governments, K-12, higher ed, and hospitals — so a single GovRAMP-aligned posture now travels across
the whole public sector. CJIS v6.0 audits are live *now*; an agent that touches anything near CJI must
prove MFA, isolation, and continuous monitoring on day one.

---

## `packs/education` — K-12, Higher Ed & EdTech

**Regimes:** FERPA, amended COPPA (2025), state student-data-privacy laws (e.g. SOPIPA), ADA/Section 508.

| Regime | What the pack does | Tier |
|---|---|---|
| **FERPA** | Treats student records as a protected data class (EDU); security-trimmed retrieval (need-to-know); masking of identifiers; school-official-exception controls (direct control + use limits); no student data to a model without an in-account, BAA-equivalent path. | [Impl]/[Cfg agreement] |
| **COPPA (amended, eff. 2025-06-23; compliance 2026-04-22)** | Expands masking entity set to **biometric identifiers** (voiceprints, facial patterns) now in scope; enforces **opt-in** consent capture in the consent ledger; requires a written security program (this pack's evidence map *is* that program's technical core). | [Impl]/[Cfg consent] |
| **State laws (SOPIPA etc.)** | No targeted advertising / no profiling data classes; retention limits on EDU data. | [Cfg] |
| **ADA / Section 508** | WCAG checks on student-facing AI output. | [Impl] |

**Why an education buyer cares.** The most common real-world FERPA violation is staff pasting student
data into general-purpose AI with no agreement. Aegis makes that structurally impossible: EDU-class
data is masked at the boundary and can only reach an in-account, guardrailed model with logged,
entitlement-trimmed retrieval. The amended COPPA biometric expansion is handled by switching on the
biometric entity set in the masker — a config flag, not a re-architecture.

---

## `packs/healthcare-lifesciences` — Providers, Payers, Pharma & MedTech

**Regimes:** HIPAA/HITECH, 42 CFR Part 2 (SUD records), GxP / 21 CFR Part 11 & EU Annex 11, HITRUST,
MARS-E (for state Medicaid).

| Regime | What the pack does | Tier |
|---|---|---|
| **HIPAA / HITECH** | PHI data class; **Comprehend Medical** detection + masking; minimum-necessary retrieval; deterministic eligibility/clinical-rule engines kept **outside** the LLM; audit controls. Requires an **AWS BAA** + customer controls — "HIPAA-eligible" (Bedrock & AgentCore are, per the HIPAA Eligible Services Reference) ≠ "HIPAA-compliant." | [Impl masking]/[Cfg BAA] |
| **42 CFR Part 2** | SUD-record data class with stricter consent + redisclosure controls in the consent ledger; segregated audit. | [Impl]/[Cfg] |
| **GxP / 21 CFR Part 11 & Annex 11** | Electronic-records integrity (append-only + WORM); **electronic-signature**-grade human gate (bound, attributable, non-repudiable); Computer Software Assurance (risk-based) validation hooks; immutable audit for regulated activities. | [Impl]/[Cfg validation] |
| **HITRUST** | Maps platform controls to HITRUST CSF; rides AWS's HITRUST-certified service inheritance. | [Cfg] |

**Why an HCLS buyer cares.** The board-level fear is an LLM fabricating a clinical or eligibility
fact. This pack keeps decisioning deterministic and outside the model, masks PHI before any prompt,
applies **contextual grounding + automated reasoning** checks to every generated statement, and gives
the human gate the attributability that 21 CFR Part 11 e-signatures require.

---

## `packs/enterprise` — Cross-Industry / Whole-of-Enterprise

**Regimes:** SOC 2, PCI DSS, ISO 27001/27701, GLBA (financial), plus a sector-agnostic data-governance
baseline.

| Regime | What the pack does | Tier |
|---|---|---|
| **SOC 2 / ISO 27001** | Maps platform controls to Trust Services Criteria / Annex A; evidence map = audit artifacts. | [Cfg] |
| **PCI DSS** | Card data class; **Luhn-aware** card masking; no PAN in prompts/audit; tokenized payment connector. | [Impl] |
| **GLBA** | NPI data class; safeguards-rule controls. | [Cfg] |
| **Baseline** | Default deny, encryption everywhere, least-privilege, audit on by default. | [Impl] |

**Why an enterprise buyer cares.** The same governance that satisfies a government review board is
exactly what an enterprise CISO needs for SOC 2 and PCI — so one platform serves the regulated public
sector *and* the regulated enterprise, which is the whole-of-enterprise thesis.

---

## Composition & precedence

When multiple packs apply, controls combine by **strictest-wins**: the most restrictive retention,
the union of masking entity sets, the highest guardrail thresholds, and the narrowest data-class
isolation. The gateway records which pack(s) authorized each decision in the audit lineage.

## What no pack can do for you

A pack configures controls; it does not grant an authorization. ATO / GovRAMP / FedRAMP authorization,
the AWS BAA, IdP integration, connector validation, retention-schedule sign-off, model-risk
validation, and Computer Software Assurance for the intended use remain customer-owned. See
[`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
