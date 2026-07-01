# Gap-Closure Backlog — from Path to Customer-Deployable Pilot

> Source: a four-perspective review (CIO, CISO, Director of Architecture, AWS Solution
> Architect) of this repository, plus items surfaced by the live AWS deployment. This is the
> honest "interesting demo vs customer-deployable pilot" gap list, prioritized. It is the
> companion to [`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
>
> Guiding rule the review insisted on: **stop calling a control "implemented" when only an
> analog or stub exists.** Use the maturity matrix below as the single source of truth.

## Readiness scorecard (current)

| Area | Assessment | Decision |
|---|---|---|
| Executive positioning | Strong | Ready for customer conversations |
| CIO value proposition | Strong concept, limited financial proof | Ready for discovery |
| CISO control model | Strong design, enforcement now hardening (fail-closed fixed) | Not yet ready for production approval |
| Reference architecture | Coherent, well documented | Ready for architecture workshops |
| AWS deployment | Governance-core + sample-agent deploy & run live | Demonstrator, not the full platform |
| Compliance material | Good mapping + RACI | Not an authorization/evidence package |
| Agent onboarding | Good design + schema + CI gate | Not yet a secure software supply chain |
| Sample agents | Useful scaffolds | Not functioning products |
| Day-2 operations | Mostly absent | Blocks production pilot |
| Commercial packaging | Good narrative | Missing offer, pricing, support model |

Ratings: architecture-workshop 8/10 · GTM-conversation 7/10 · synthetic-PoC 6/10 ·
customer-production-pilot 3/10 · production 2/10.

## Control-status maturity matrix (the honesty fix — P0 item #1)

Legend: **D** Designed · **IO** Implemented offline (Python demo) · **DA** Deployed on AWS ·
**IT** Integration-tested · **PE** Production-enforced · **CC** Customer-configured · **P** Planned.

| Control | D | IO | DA | IT | PE | Notes |
|---|:--:|:--:|:--:|:--:|:--:|---|
| Append-only audit + explicit deny | ✓ | ✓ | ✓ | ✓ |  | Proven live via IAM simulation (Put=allow, Update/Delete=explicitDeny) |
| WORM evidence (S3 Object Lock) | ✓ | ✓ | ✓ | ✓ |  | **Retention APPLIED + deletion proven denied** (GOVERNANCE 1d; break-glass bypass for teardown), 2026-07-01. Prod profile = COMPLIANCE |
| Bedrock Guardrail (grounding+PII+topic) | ✓ | ✓ | ✓ | ✓ |  | READY live; contextual grounding + PII filters confirmed |
| Human gate + reviewer service | ✓ | ✓ | ✓ | ✓ |  | **Deployed & live-tested behind API Gateway + Cognito JWT authorizer**: 401 unauth; authenticated supervisor -> verified-role + SoD + bound single-use approval + audit + SendTaskSuccess -> SUCCEEDED (2026-07-01) |
| Fail-closed gateway | ✓ | ✓ | ✓ (template) |  |  | Fixed this session (guardrail error/intervention → deny); redeploy to prove |
| Deny-by-default policy (full predicate) | ✓ | ✓ | ✓ | ✓ |  | **Cedar on Amazon Verified Permissions — deployed & live-tested** (1 ALLOW + 2 DENY, 2026-06-30); AgentCore Policy is the next target |
| Real Bedrock invocation (Model Gateway) | ✓ | ✓ | ✓ | ✓ |  | Claude Haiku 4.5 via inference profile, live (2026-06-30) |
| Cryptographic identity + MFA | ✓ | ✓ | ✓ | ✓ |  | **MFA-required Cognito + advanced security deployed; real MFA login → RS256 JWT verified vs JWKS → verified group → Cedar decision** (2026-06-30). IdP federation + API GW authorizer + OBO still to wire |
| PII/PHI/FTI/CJI masking | ✓ | ✓ |  |  |  | Regex offline; Comprehend/Macie not wired at runtime |
| Token budgets + chargeback | ✓ | ✓ | ✓ | ✓ |  | **Atomic DynamoDB reservation deployed & live-tested** (over-cap rejected, no oversell), 2026-07-01; AIP chargeback path proven Run 3 |
| Signed agent manifests | ✓ | ✓ | ✓ | ✓ |  | **KMS-asymmetric sign/verify deployed & live-tested** (tamper rejected) + real JSON-Schema validation + manifest->Cedar compiler in platform_core/prod, 2026-07-01 |
| Single-use bound approval ledger | ✓ | ✓ | partial |  |  | Offline enforced; DynamoDB table deployed; reviewer service not built |
| Multi-account data-class isolation | ✓ |  |  |  |  | Control Tower topology documented, not deployed |
| Live connectors (system of record) | ✓ | ✓ | ✓ | ✓ |  | **Governed connector w/ idempotency + saga rollback deployed & live-tested** on a DynamoDB system-of-record (2026-07-01); real external SaaS (ServiceNow/CRM) is a credentials/endpoint change |

## P0 — before positioning it as pilot-ready

1. **Publish the maturity matrix above and reconcile every `[Impl]` claim** in docs 02/04/10 to
   one of D/IO/DA/IT/PE. Where a doc says "implemented," qualify it (offline vs deployed).
2. **Fix all fail-open paths** so every mandatory boundary fails closed: guardrail
   unavailable/error → deny; policy engine unavailable → deny; identity unverifiable → deny;
   manifest invalid/unsigned → deny; masking unavailable → deny; tool not registered → deny;
   approval ledger unavailable → deny consequential; audit-write failure → deny consequential/
   sensitive. *Status: DONE this session for the deployed gateway Lambda (guardrail error/
   intervention now denies) and the offline gateway (unregistered tool / policy / audit failure
   now deny), with `demo/test_fail_closed.py` added.*
3. **Build one complete "golden pilot"** end to end (recommend: enterprise IT service-desk,
   read-only KB retrieval + draft-ticket): real IdP login + MFA, authenticated API, AgentCore
   Gateway, real Cedar policies in AgentCore Policy, one real Bedrock invocation, one real KB,
   one sandbox connector (e.g. ServiceNow), prompt-injection defense, PII masking, token-budget
   enforcement, human approval for submission, single-use approval consumption, end-to-end audit,
   operator dashboard, automated deploy + teardown, evidence report.
4. **Real identity + delegated authorization**: IdP federation, MFA enforcement, app client/token
   issuer, issuer/audience/expiry/nonce/alg validation, group-role mapping, distinct agent vs
   human identity, OBO exchange, short-lived downstream creds, revocation, break-glass, and
   privilege-escalation / confused-deputy tests. *(Deployed template currently: Cognito pool +
   group, MFA off — placeholder only.)*
5. **Real human-approval system**: reviewer app/integration, authenticated approver, SoD, args-
   hash + purpose binding, expiry, single-use, approve/reject reasons, escalation, SLA/timeout,
   notifications, full approval audit (viewed/approved/rejected/expired/replayed), recovery.
6. **Genuinely immutable evidence**: apply Object Lock retention (governance/compliance profiles),
   prove deletion is denied; separate demo (no retention) / pilot (governance) / production
   (compliance + legal hold + cross-account log archive) profiles.
7. **Replace offline approximations** used as the "control plane": real JSON-Schema validation,
   KMS-asymmetric/Sigstore signed-manifest verification, durable budgets (concurrency-safe
   reservation), durable approval ledger, real Cedar compilation/deployment, real connector auth,
   runtime tool I/O schema enforcement, reconciled token usage.
8. **Complete canonical IaC + CI/CD** in one language first (recommend CDK/CloudFormation), then
   Terraform; deployment roles not human creds; change sets; rollback alarms; artifact signing;
   pinned deps. *(Started: GitHub Actions CI with cfn-lint + demo + bandit/checkov added this
   session; not yet full pipeline.)*
9. **End-to-end negative-security tests**: deny, wrong-data-class, prompt-injection, replay,
   masking-failure, audit-failure, budget-denial, retention, load, recovery, rollback.

## P1 — before any customer production data

- Threat model + security architecture (trust boundaries, data-flow, identity/tool-call/approval
  sequence diagrams). Supply-chain security + signed releases. Operational SLO/SLI, backup/
  restore, RTO/RPO, regional-failure and model-fallback plans, incident response. Independent
  **penetration test**. Compliance **evidence package** (not just mappings). Privacy,
  accessibility (axe-core + manual, ahead of ADA Title II 2027/2028), records-management, and
  model-risk validation. Fixed-scope **pilot SOW** + success metrics. 

  *Status (2026-07-01): security package authored — `docs/security/` (THREAT-MODEL, SECURITY-ARCHITECTURE with sequence diagrams, ENCRYPTION-AND-LOGGING-MATRIX, SUPPLY-CHAIN-SECURITY, PENTEST-SCOPE, COMPLIANCE-EVIDENCE-INDEX) and `docs/ops/` (OPS-READINESS with SLO/DR/RTO-RPO/fallback, INCIDENT-RESPONSE with key-compromise + prompt-injection playbooks). Grounded in Runs 1-9. Still customer/engagement-owned: the independent third-party pen test itself, a live DR game day, accessibility CI (axe-core), and the signed pilot SOW.*

## P2 — before commercial scale

- Multi-account / multi-tenant operating patterns. Terraform + GovCloud variants. Operator and
  customer dashboards. Licensing, pricing, support tiers, managed-service boundaries. Versioned
  releases + upgrade paths. Agents and compliance packs as independently versioned products.
  Secure a design partner and publish a reference outcome. 

  *Status (2026-07-01): delivered — a partition-aware **Terraform module** mirroring the live-proven governance core (`infra/terraform/modules/governance_core/`) with **commercial + GovCloud** root examples and a CFN<->Terraform parity table; **multi-tenancy** design (`docs/11-MULTI-TENANCY.md`, SILO/POOL/BRIDGE) and **commercial packaging** (`docs/12-COMMERCIAL-PACKAGING.md`, editions/pricing/support/Marketplace/versioning). HCL validated structurally (python-hcl2; terraform binary not available here). Still engagement-owned: a live `terraform apply`, a deployed multi-account/multi-tenant landing zone, operator/customer dashboards, finalized commercial pricing, and a named design partner.*

## Down-payment already made this session

- **Fail-closed** enforced in the deployed gateway Lambda and the offline gateway (+ tests).
- **Repo hygiene / DevSecOps**: `LICENSE` (Apache-2.0), `SECURITY.md`, `CONTRIBUTING.md`,
  `.github/CODEOWNERS`, `CHANGELOG.md`, and `.github/workflows/ci.yml` (python + cfn-lint +
  bandit/checkov).
- **Live AWS validation** of the governance core and the sample-agent human gate, which caught
  three real bugs (guardrail topic length; cross-stack KMS decrypt on the agent role; the
  fail-open gateway) — see [`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md).

## Recommended honest positioning (today)

> "Aegis is a well-developed AWS governance reference architecture and accelerator with a
> deployable, live-validated control-core demonstration and a working human-gate agent. It is
> being hardened into a repeatable production-pilot platform." Also soften "no lock-in" to:
> "customer-owned, readable, AWS-native implementation with no proprietary Aegis runtime dependency."
