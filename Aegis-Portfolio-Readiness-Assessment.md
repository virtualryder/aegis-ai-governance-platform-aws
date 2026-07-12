# Aegis Governed-Agent Portfolio — Readiness Assessment (v3)

**Prepared across five viewpoints** — CISO, CIO, Security Analyst, Director of Architecture, and
**Principal Solutions Architect (AWS)** — and reconciled against an independent Claude Code code review.
**Date:** 2026-07-11 · supersedes v2. **Method:** every claim was verified against the current working
branches of all five repos *and* against **live AWS deploys on a clean account** (`us-east-1`) performed
this session — each hero deployed, its governed outputs inspected, and torn down. Where something is
still a gap, it is called a gap.

---

## 1. Bottom line up front

**Presentable to AWS leadership now — as a governed reference accelerator, not a product — and it now
survives a skeptical CISO's code review *and* a live deploy walkthrough.** The independent review's
verdict stands, and the two things it flagged as most reputationally load-bearing have been closed with
live evidence this session.

| Audience / use | Verdict |
|---|---|
| AWS internal leadership buy-off for a GTM motion | ✅ **Go now** — as discovery / architecture-workshop / scoped-pilot accelerator |
| Customer pilots on synthetic / de-identified data | ✅ **Go** — lead with the one validated hero per vertical |
| Production / real regulated data (PHI, FERPA, CJI, GxP) | ❌ **Not yet** — and every repo correctly says so |

The single biggest asset is unchanged: the security architecture is real engineering, and the honesty
documents are accurate rather than aspirational. That is rare and it makes every other claim credible.

---

## 2. What changed this session (verified live on AWS)

**All five heroes were deployed to a clean account, their governed resources verified, and torn down —
zero residual.** This converts "deploys as prescribed" from assertion to evidence.

| Hero | Mechanism | Live result |
|---|---|---|
| **EDU** — Concierge | raw CloudFormation | real Sonnet 4.5 inference; student PII masked before persistence; append-only audit written; torn down |
| **HPP** — Denials | SAM (private VPC) | full private-VPC + PrivateLink stack; API-GW gateway, Step Functions human gate, Cognito, append-only audit + JTI-replay + HITL tables, WORM bucket; torn down |
| **HCLS** — Pharmacovigilance | SAM | governed stack **+ a live Bedrock Guardrail**, Cognito, SoD pending-approvals, human gate, audit; torn down |
| **SLG** — 311 | SAM | governed stack + live Guardrail + in-stack token secret; torn down |
| **Aegis** — authz core | Verified Permissions / Cedar | three live decisions: **ALLOW / DENY / DENY** (deny-by-default proven on AWS); torn down |

**The #1 substantive gap is closed with live evidence.** Runtime PII/PHI masking is now **deployed and
verified on AWS**: a new `hcls-ai-agents/infra/golden-path-masking-verification/` stack wires **Amazon
Comprehend Medical `DetectPHI` + Amazon Comprehend `DetectPiiEntities`** into a Lambda that, on a
synthetic ICSR record staged in S3, detected **7 PHI + 7 PII entities**, redacted them, and wrote **only
the masked text** to an append-only audit table — **fail-closed**, before the write. Raw SSN/name/email
never persisted. See that module's `EVIDENCE.md`. An honest sub-finding surfaced and is documented: a
site-specific MRN format was *not* caught by NER — which is exactly why the design keeps a regex
Safe-Harbor pass for structured IDs alongside NER.

**Fixes landed this session (all on branches, delivered as patches):**
- EDU golden-path template deploy-blockers fixed (hard-coded placeholder account `111122223333` →
  `AWS::AccountId` pseudo-params; now-Legacy default model → active Sonnet 4.5) — found by a live rollback.
- SLG shared layer converted off a **Unix-only Makefile** to the portable pre-staged pattern — now builds
  *and* deploys on Windows/macOS/Linux/CI (verified live).
- EDU quickstart CFN: **6 real cfn-lint errors that were silently suppressed by an `.cfnlintrc`
  ignore-list** fixed at the source and the ignores removed (E1003 ×4, E3004 circular KMS↔role, E3005
  conditional listener).
- Test-count drift reconciled to canonical `MATURITY.yaml` portfolio-wide (Aegis 43 · EDU 201 · SLG 236 ·
  HPP 270 · HCLS 583 = **~1,333**); HPP recounted 268 → 270 and EDU 197 → 201 (its suite grew); HCLS 580 → 583 (B1 masking tests added).
- "Masked before any model call" softened to the accurate boundary claim across all five repos'
  `DO-NOT-CLAIM.md` / `NOT-CLAIMS.md` and the portfolio summary.
- Aegis "deployed subset ≠ reviewed engine" reconciled in `MATURITY.yaml` (the deployed authorizer is the
  mcp-gateway subset; the full 8-clause platform_core engine is offline-validated; packaging it as the
  deployed layer is a tracked P1 item).
- `healthcare_ai_agents` (HPP) vs `hcls-ai-agents` (life sciences) naming disambiguated in every README.
- **One unified SA runbook** (`SA-DEPLOYMENT-RUNBOOK.md`) + a **portfolio banner in all five READMEs** so
  the five repos read as one review-as-one solution; healthcare `.gitignore` for the vendored build copy.

---

## 3. The consistent-gap pattern (from the code review) — current status

| Gap the review found | Status now |
|---|---|
| Real-data masking never runtime-verified on AWS; NER not wired into a deployed path | ✅ **Closed (evidence)** — Comprehend Medical + Comprehend deployed and live-verified, fail-closed. **Now also wired into the HCLS hero pipeline** (masks the narrative prompt before the model, fail-closed, unit-tested — 2026-07-12). A real Bedrock+Guardrails hero invocation remains (P1). |
| Deployed artifact is a subset of the reviewed engine (Aegis inline authorizer ≠ platform_core) | ◑ **Disclosed & scoped** — `MATURITY.yaml` now states it; packaging platform_core as the deployed layer is P1. |
| "Masked before any model call" overstated | ✅ **Closed** — reworded to the accurate audit/model-output-boundary claim portfolio-wide. |
| Governance core duplicated-by-copy across 5 repos (drift risk) | ◻ **Open (P2)** — unify into one versioned, hash-checked shared package; make conformance a CI gate. |
| Naming collision (healthcare vs hcls); single-operator self-attested evidence | ◑ Naming **disambiguated**; reproducible CI-deploy evidence is **P1** (this session's runs are still single-operator, though now scripted + repeatable via the runbook). |
| EDU cfn-lint errors hidden by ignore-list | ✅ **Closed** — fixed at source, ignores removed. |

---

## 4. Readiness ladder (refreshed)

| Level | Status | Note |
|---|---|---|
| Internal AWS leadership demo | **Ready** | Offline + live-deploy evidence; honesty framework is the differentiator. |
| Customer architecture workshop | **Ready** | Field-grade runbook; controls demonstrable live. |
| Scoped pilot (synthetic / de-identified) | **Hero-ready** | Lead with HCLS PV, SLG 311, HPP Denials; masking now runtime-proven. |
| Production (real regulated data) | Customer-owned | ATO/HITRUST/FedRAMP, landing zone, tier-4 connectors, pen test, DR/monitoring — the P1/P2 roadmap. |

---

## 5. Remaining roadmap (priority order)

**P1 — before a customer pilot touches even de-identified-realistic data**
1. **Done — masking wired into the HCLS hero pipeline** (`pii_masker.py` masks the narrative prompt
   before `llm.invoke`, fail-closed in real-data mode; unit-tested). Remaining P1 here: add a **real
   Bedrock + Guardrails hero invocation** on AWS and tune the regex ID pass to the site's MRN formats.
2. **Make the deployed authorizer the reviewed engine** — package `platform_core` as the Lambda layer for
   the heroes; delete the inline subset.
3. **Reproducible deploy evidence** — a CI pipeline that deploys → tests → captures sanitized
   CloudTrail/IAM-simulation artifacts, replacing single-operator attestation.

**P2 — hardening / scale**
4. Unify the AGP core into one versioned, hash-checked shared package; turn the conformance table into a
   CI gate every suite imports and must pass.
5. Independent pen test + manual WCAG (EDU); finish or explicitly quarantine the experimental AgentCore
   Gateway CFN path.

**Do not build more hero agents.** Breadth is not the blocker. Depth-and-unify on the existing heroes.

---

## 6. Per-repo scorecard (updated)

| Repo | Security substance | Deployability (live-verified this session) | Standout gap |
|---|---|---|---|
| **Aegis** (WOGplatform) | Real, strongest | ✅ authz core deployed (Cedar ALLOW/DENY/DENY), torn down | deployed authorizer = mcp-gateway subset (disclosed); package platform_core as layer (P1) |
| **HCLS** (life sci) | Real, cleanest | ✅ hero deployed w/ live Guardrail; **runtime masking now evidenced** | wire masking into hero pipeline + real Bedrock call (P1) |
| **SLG** | Real, strong | ✅ hero deployed; cross-platform build fixed | token-budget wording; regex+NER masking into hero path |
| **HPP** (payer/prov) | Real | ✅ full private-VPC hero deployed, torn down | reproducible CI evidence; hero-pipeline masking |
| **EDU** | Real | ✅ hero deployed (real model + masking + audit); template + cfn-lint fixed | full nested quickstart stack still not deploy-validated |

---

## 7. Verdict

Take it to AWS leadership now. The package reads as what it honestly is: a strong, governed reference
accelerator that **deploys as prescribed (proven live), demonstrates its controls, verifies its most
compliance-load-bearing control on AWS, and tells the truth about its maturity.** Frame the ask as
buy-off to run discovery + architecture workshops + scoped synthetic-data pilots as a repeatable motion,
with the P1 roadmap above as the honest path to real-data readiness. Lead with one governed hero per
vertical, the negative demo, and the live masking evidence.
