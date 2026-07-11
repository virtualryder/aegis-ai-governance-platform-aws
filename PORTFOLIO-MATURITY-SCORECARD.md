# Portfolio Maturity Scorecard

*The single-glance honesty table. Green = evidence in-repo (code + tests, or documented clean-account
validation). Not every agent is equally validated — lead only with what is proven. The machine-readable
source of truth for each repo is its `MATURITY.yaml`; `tools/check_maturity.py` fails CI on drift.*

**Verified on `main` (2026-07-10): ~1,324 offline tests green** — Aegis 43 · EDU 197 · SLG 236 · HPP 268 · HCLS 580.

## Portfolio readiness

| Repo | Internal AWS demo | Customer workshop | Scoped pilot (synthetic) | Production | Clean-account deploy evidence |
|---|:--:|:--:|:--:|:--:|---|
| **Aegis** (platform) | ✅ Ready | ✅ Ready | ◑ Medium | ◻ Not yet | Governance core → MCP endpoint runs, deployed & torn down |
| **HCLS** (life sciences) | ✅ Strongest | ✅ Ready | ◑ Medium (GxP/CSV care) | ◻ Not yet | 9 golden paths deployed, run end-to-end, torn down |
| **SLG** (state/local gov) | ✅ Ready | ✅ Ready | ◑ Medium-high (synthetic) | ◻ Not yet | 8 golden paths + a hardened secure variant, validated & torn down |
| **HPP** (payer/provider) | ✅ Ready | ✅ Ready | ◑ Medium (Agent 01) | ◻ Not yet | Agent 01 golden path acceptance-gated; 02–08 share templates |
| **EDU** (education) | ✅ Ready | ✅ Ready | ◑ Medium | ◻ Not yet | Resource-level provisioning validated; full-stack CFN deploy is a documented next step |

## Control maturity (AGP v1.0) — portfolio view

| Control | Designed | Implemented + tested (offline) | Deployed on AWS (golden path) | Notes |
|---|:--:|:--:|:--:|---|
| Verified identity (RS256/JWKS) | ✅ | ✅ | ✅ | Server-side verification on request paths; body claims never trusted |
| Deny-by-default gateway | ✅ | ✅ | ✅ | Least-privilege intersection (agent ∩ human) |
| Bound SoD human approval | ✅ | ✅ | ✅ | Single-use, consumed against a durable ledger |
| Fail-closed PII/PHI masking | ✅ | ✅ | ◑ | Regex Safe-Harbor always-on; NER mandatory for real data (`ALLOW_REAL_DATA`) |
| Append-only + WORM audit | ✅ | ✅ | ✅ | Conditional PutItem; IAM denies delete; split signing keys; S3 Object Lock |
| Token budgets | ✅ | ✅ | ◑ | Enforced before spend in Aegis; metering in packs |
| Model gateway + grounding | ✅ | ✅ | ◑ | Bedrock default; external API gated; Guardrails config |
| Fail-closed output guardrail | ✅ | ✅ | ◑ | Configured-guardrail error → block + alarm |

## Connector maturity (say it precisely)
Everything is at connector **tiers 1–3**. **Tier 4** (a customer's production system of record — Veeva/Argus,
Epic/Availity, a real X12 835 feed, ServiceNow, PowerSchool/Banner/Canvas) **is engagement work, not done in any repo.**

| Pack | Hero | Live tier-3 reference connector (real, public, read-only) |
|---|---|---|
| HCLS | Pharmacovigilance (02) | openFDA / FAERS |
| SLG | Resident Services / 311 (01) | NYC 311 Socrata |
| HPP | Revenue-Cycle Denials (01) | X12 835 scaffold (no public denial API) |
| EDU | Student & Family Concierge (01) | College Scorecard |

## Depth honesty
Each vertical has **one deep hero agent + governed reference scaffolds** (same governed chassis, swapped
domain logic/fixtures). This is deliberate low-blast-radius sequencing — not a claim of 40 production agents.

## What remediation closed (2026-07-10)
All CRITICAL and HIGH findings, and the actionable MEDIUM findings, from the independent readiness review
are resolved on `main`: approval-gate enforcement, audit immutability, server-side identity, secure-by-
default container, per-deploy secrets, fail-closed guardrail, Bedrock-default provider, real release
evidence, pinned deps + blocking CI, network/edge stacks, IAM wildcard scoping, durable approval registry,
real prompt change-control, and a working drift-checker. See `Aegis-Portfolio-Readiness-Assessment-v2` /
each repo `CHANGELOG.md`.
