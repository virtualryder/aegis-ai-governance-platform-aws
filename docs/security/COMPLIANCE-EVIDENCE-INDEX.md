# Compliance Evidence Index — Aegis Governed Agent Platform

> **Assessor-facing.** This index maps each platform control to its NIST 800-53 Rev.5 family and to
> **concrete evidence**: a live-validated run in [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md),
> an IaC file, a test, or an explicit "planned / customer-owned" note. Control ids and NIST families
> come from [`../../governance/controls/control_mappings.yaml`](../../governance/controls/control_mappings.yaml);
> maturity (**DA/IO/IT/CC/P**) from [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md).
>
> **What this is not.** This is an evidence *index*, not an authorization package and not an ATO.
> The platform is not AWS-authorized, GovRAMP/FedRAMP-certified, or third-party-pen-tested. Those
> are customer-owned processes built *from* this evidence (see
> [`../10-PRODUCTION-READINESS-RACI.md`](../10-PRODUCTION-READINESS-RACI.md)).

## 1. How to read this index

Each row is a control an auditor can follow end to end: the control name and id, the NIST 800-53
families it addresses, the NIST AI RMF function, the maturity, and a pointer to evidence an assessor
can independently inspect (a Run number, an IaC file path, or a test file). Where evidence is a Run,
the Run is reproducible via [`../../infra/DEPLOY-RUNBOOK.md`](../../infra/DEPLOY-RUNBOOK.md).

## 2. Control -> NIST 800-53 -> evidence

| Control (id) | NIST 800-53 | NIST AI RMF | Maturity | Evidence |
|---|---|---|---|---|
| Edge protection (`edge-waf-shield`) | SC-5, SC-7, SC-8 | Information Security | CC | Design: [`../02-REFERENCE-ARCHITECTURE.md`](../02-REFERENCE-ARCHITECTURE.md) §1; WAF/Shield customer-tuned |
| Cryptographic identity + MFA (`crypto-identity-mfa`) | IA-2, IA-5, AC-2 | Human-AI Configuration | DA | Runs 4, 7; IaC: [`../../infra/golden-pilot/cognito-identity.yaml`](../../infra/golden-pilot/cognito-identity.yaml), [`reviewer-api.yaml`](../../infra/golden-pilot/reviewer-api.yaml); test: [`verify_jwt.py`](../../infra/golden-pilot/verify_jwt.py) |
| Deny-by-default gateway (`deny-by-default-gateway`) | AC-3, AC-6, AC-4 | Manage | DA | Run 3; IaC: [`avp-cedar.yaml`](../../infra/golden-pilot/avp-cedar.yaml); analog: `platform_core/policy_engine.py`; test: `demo/test_negative_security.py` |
| Human gate (`human-gate`) | AC-3, AC-5, AC-6 | Human-AI Config, Manage | DA | Runs 2, 5, 7; IaC: [`reviewer-service.yaml`](../../infra/golden-pilot/reviewer-service.yaml), [`reviewer-api.yaml`](../../infra/golden-pilot/reviewer-api.yaml) |
| In-account inference + Guardrails (`in-account-inference-guardrails`) | SC-7, SC-8, AC-4 | Data Privacy, Information Security | DA | Run 1 (Guardrail READY, PII filters); IaC: [`../../infra/cloudformation/governance-core.yaml`](../../infra/cloudformation/governance-core.yaml) |
| Contextual grounding + automated reasoning (`contextual-grounding-automated-reasoning`) | SI-10 | Confabulation, Information Integrity | DA | Run 1 (grounding 0.80 / relevance 0.75; ungrounded-consequential denied topic) |
| Append-only audit + WORM (`append-only-audit-worm`) | AU-2, AU-9, AU-10, AU-11 | Measure | DA | Runs 1, 6; IaC: `governance-core.yaml`, [`evidence-worm.yaml`](../../infra/golden-pilot/evidence-worm.yaml); IAM simulation (Put=allow, Update/Delete=explicitDeny) |
| Boundary masking, fail-closed (`masking-fail-closed`) | MP-6, SC-28, SI-12 | Data Privacy | IO | Regex analog + `demo/test_fail_closed.py`; runtime Comprehend/Macie planned (P) |
| KMS CMK + data-class isolation (`kms-cmk-dataclass-isolation`) | SC-12, SC-13, SC-28, AC-4 | Information Security | DA (key) / P (multi-account) | Run 1 (per-class CMK, SSE-KMS); multi-account isolation documented, not deployed |
| Token budgets + chargeback (`token-budgets-chargeback`) | SA-2, PM-3 | Value Chain, Manage | DA | Run 8 (atomic reservation, over-cap rejected); Run 3 (inference-profile path) |
| Continuous monitoring (`continuous-monitoring`) | CA-7, SI-4, AU-6 | Manage, Measure | CC | CloudTrail/GuardDuty/Security Hub/Config/X-Ray; customer-enabled; see [`../ops/INCIDENT-RESPONSE.md`](../ops/INCIDENT-RESPONSE.md) |

## 3. Cross-cutting evidence artifacts

| Artifact | Location | Supports |
|---|---|---|
| Live-validation log (Runs 1-9) | [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md) | All DA controls above |
| Machine-readable control map | [`../../governance/controls/control_mappings.yaml`](../../governance/controls/control_mappings.yaml) | Control -> regime -> NIST |
| Maturity matrix (single source of truth) | [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md) | Honest DA/IO/IT/PE status |
| RACI + gated go-live checklist | [`../10-PRODUCTION-READINESS-RACI.md`](../10-PRODUCTION-READINESS-RACI.md) | Ownership of customer controls |
| Threat model (STRIDE + agentic) | [`THREAT-MODEL.md`](THREAT-MODEL.md) | RA-3, risk register |
| Signed-manifest onboarding gate | [`../../governance/onboarding/MINIMUM-BAR.md`](../../governance/onboarding/MINIMUM-BAR.md) | SA-4, CM-7 (supply chain) |
| Deploy/teardown runbook | [`../../infra/DEPLOY-RUNBOOK.md`](../../infra/DEPLOY-RUNBOOK.md) | Reproducibility of every Run |
| CI pipeline | [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | SA-11, SA-15 (dev security) |

## 4. Explicitly customer-owned or planned evidence

An assessor should expect the following to be produced during a customer engagement, not by the
reference platform:

- **Third-party penetration test report** — planned; scope in [`PENTEST-SCOPE.md`](PENTEST-SCOPE.md). (CA-8)
- **ATO / GovRAMP / FedRAMP authorization package** — customer-owned. (CA-6)
- **Signed BAA** (before any PHI) — customer-owned. (Contractual)
- **Runtime masking evidence** (Comprehend/Macie) — planned; currently regex analog. (SI-12)
- **Multi-account data-class isolation** — documented, not deployed. (SC-7, AC-4)
- **Model-risk validation** (eval gold sets, fairness baselines, guardrail/red-team tuning) — customer-owned. (SI-4, RA-3)
- **Accessibility testing** (axe-core + manual, ADA Title II) — customer-owned.
- **Production IdP federation + OBO delegation** — customer-configured / planned. (IA-2, AC-3)

## 5. Assessor note on honesty of claims

The maturity column is deliberately conservative: a control is marked **DA** only where a live AWS
run proves it, and controls with only an offline analog are marked **IO** and not represented as
production-enforced. This mirrors the guiding rule of the gap-closure review: stop calling a control
"implemented" when only an analog or stub exists. An assessor can therefore treat a **DA** row as
independently reproducible and an **IO/P/CC** row as work that is designed but not yet proven in the
target environment.
