# Aegis — Leadership Status Brief

*Governed Agent Platform on AWS · status as of 2026-07-01 · account 864217980669 (us-east-1)*

## Bottom line up front

Aegis is the **governance layer that makes any AI agent deployable in a regulated environment**:
build the paved road once on AWS, and every agent, model, and tool inherits identity, authorization,
audit, compliance, hallucination control, and departmental chargeback. Over the past cycle we took it
from a documented reference to a **live-validated control platform**: the hard controls a CISO and an
auditor ask about have each been **deployed to AWS, exercised with real requests, and torn down** —
**nine documented runs** — and the security/operations review package is written. It is **not yet an
authorized (ATO'd) product**; the remaining work is scoped and customer/engagement-owned.

The full deck is `Aegis-Master-Deck.pptx`; the GTM narrative is `docs/08-GTM-AND-POSITIONING.md`; the
evidence log is `DEPLOYED-AND-VALIDATED.md`; the honest gap plan is `docs/GAP-CLOSURE-BACKLOG.md`.

## What is proven on AWS (9 live runs)

| # | Capability | Result (live, then torn down) |
|---|---|---|
| 1 | Governance core (KMS CMK, append-only audit, WORM, Guardrail, Cognito, gateway) | `CREATE_COMPLETE`; caught a real Guardrail-limit bug cfn-lint missed |
| 2 | Human gate (Step Functions `waitForTaskToken`) | Paused before the consequential step; ran only after approval |
| 3 | Cedar authorization on Amazon Verified Permissions + real Bedrock (Haiku 4.5) | ALLOW for a legit read; DENY for unpermitted tool and wrong data class |
| 4 | Identity: hardened Cognito (MFA required) + cryptographic JWT verification | Real MFA login; tampered/ wrong-audience tokens rejected; verified group → Cedar |
| 5 | Human-approval reviewer service | Wrong role & self-approval denied; valid supervisor approval; replay rejected |
| 6 | Immutable evidence (S3 Object Lock retention) | Locked-object delete denied; break-glass bypass for clean teardown |
| 7 | Reviewer front door (API Gateway + Cognito JWT authorizer) | 401 unauthenticated; authenticated supervisor approval → workflow SUCCEEDED |
| 8 | Production components: KMS-signed manifests + atomic token-budget reservation | Tamper rejected; over-cap reservation rejected (no oversell) |
| 9 | Governed connector: idempotency + saga rollback | Duplicate write prevented; downstream failure auto-compensated (ticket voided) |

Every run is reproducible from `infra/` (CloudFormation) with deploy/smoke/teardown scripts; a
Terraform module mirrors the core with a GovCloud variant (`infra/terraform/`). A laptop-only demo
(`demo/clean_account_acceptance.py`, no AWS/API key) exercises the same control plane, 18/18 green.

## Security & operations package (review-ready)

`docs/security/` — threat model (STRIDE + agentic abuse cases), security architecture with sequence
diagrams, encryption/logging matrix, supply-chain security, pen-test scope with an OWASP-LLM / MITRE
ATLAS self-assessment, and a compliance-evidence index mapping controls → NIST 800-53 → the run that
proves them. `docs/ops/` — SLOs/DR/RTO-RPO/model-fallback and an incident-response runbook with
key-compromise and prompt-injection playbooks. CI (`.github/workflows/ci.yml`) re-runs the tests and
lints every template on each push.

## Honest status — what is NOT done

This is a **live-validated reference platform, not an authorized product.** Still required and
customer/engagement-owned: **ATO / GovRAMP / FedRAMP authorization**, an **independent third-party
pen test**, a **live connector to a real external SaaS** (the connector pattern is proven against a
DynamoDB stand-in), a deployed **multi-account / multi-tenant** landing zone, **operator dashboards**,
accessibility CI, a signed **pilot SOW**, and finalized commercial pricing. Full detail:
`docs/10-PRODUCTION-READINESS-RACI.md` and `docs/GAP-CLOSURE-BACKLOG.md`.

## The ask

Fund a **scoped, low-blast-radius pilot** (IT service desk or resident/customer services — reversible,
high-volume, clear ROI) in a customer AWS account: run the discovery + architecture workshop, select
the compliance pack(s), stand up the governed golden path with synthetic data plus one real connector,
prove it against a documented outcome, and sign the shared-responsibility plan so security review has
no surprises. Then land-and-expand: add agents one at a time on the same paved road, turn on
chargeback, and open the add-on/marketplace motion.
