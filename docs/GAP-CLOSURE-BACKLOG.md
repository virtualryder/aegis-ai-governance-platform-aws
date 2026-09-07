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
| PII/PHI/FTI/CJI masking | ✓ | ✓ |  |  |  | Deterministic Safe Harbor regex covers **structured** identifiers; **free-text names need the NER engine**, which is **mandatory and fail-closed in real-data mode** (`ALLOW_REAL_DATA`). Comprehend/Macie not wired at runtime (customer work) |
| Token budgets + chargeback | ✓ | ✓ | ✓ | ✓ |  | **Atomic DynamoDB reservation deployed & live-tested** (over-cap rejected, no oversell), 2026-07-01; AIP chargeback path proven Run 3 |
| Signed agent manifests | ✓ | ✓ | ✓ | ✓ |  | **KMS-asymmetric sign/verify deployed & live-tested** (tamper rejected) + real JSON-Schema validation + manifest->Cedar compiler in platform_core/prod, 2026-07-01 |
| Single-use bound approval ledger | ✓ | ✓ | ✓ | ✓ |  | Offline enforced; reviewer service deployed (Runs 5/7); the **deployed MCP gateway** (`infra/golden-pilot/mcp-gateway.yaml`) now validates a consequential-tool `approval_id` against the ledger with an **atomic single-use consume bound to the calling identity** (`requester == sub`) — arbitrary/replayed/expired/unbound denied, fail-closed if no ledger wired (no longer presence-only) |
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
  *Status (2026-09-02): the **hybrid multi-tenant control plane is BUILT and LIVE-VALIDATED** in the benefits pack (shared AgentCore control plane, per-tenant data stacks incl. each tenant's own audit ledger / WORM vault, tenant derived from the verified identity, cross-tenant deny proven, full per-case transparency through the real AgentCore Runtime) — `docs/MULTI-TENANT-SAAS-DESIGN.md`, `docs/OBSERVABILITY-CORRELATION.md`, benefits `evidence/AGENTCORE-*-2026-09-02.md`. Multi-account tenancy, onboarding automation, metering and an operator console remain open.*

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


---

# 2026-09-05 — Production-readiness refresh & Well-Architected gap register

The scorecard and P0/P1/P2 lists above are the **2026-07 review** and are kept for provenance. This
section is the **current** state and the honest remaining-work list, framed against the six AWS
Well-Architected pillars plus the governance-specific concern an auditor actually opens the platform for:
**can I reconstruct, for any one case, every decision, every API call, every model input/output, who
approved what, and what it cost — and prove none of it was tampered with?** On the AgentCore path that
question is now answerable end-to-end (pillar-by-pillar below).

Everything marked **LIVE** was proven on a from-zero AWS deploy in `111122223333`/us-east-1 and torn down
to zero residue, with the account model-invocation logging restored. Account ids in committed evidence are
redacted to `111122223333`.

## A. What has CLOSED since the 2026-07 review (correcting the scorecard above)

| Capability | 2026-07 state | Now (2026-09) | Evidence |
|---|---|---|---|
| Managed policy enforcement | Cedar on Verified Permissions (demo) | **AgentCore Gateway (MCP, CUSTOM_JWT) + GA Cedar Policy engine in ENFORCE, deny-by-default, stood up as IaC by a CFN custom resource** — LIVE | benefits `evidence/AGENTCORE-LIVE-2026-09-02.md` |
| Zero-trust entitlement | Group→role claim | **Zero-default entitlement — no `custom:tools` claim ⇒ zero tools (list+call denied); action-scoped Cedar perimeter (#160/#161)** — LIVE | `evidence/AGENTCORE-CEDAR-PERIMETER-2026-09-05.md` |
| Output guardrail | READY, hand-created | **Bedrock Guardrail created from the manifest as IaC (PROMPT_ATTACK + PII ANONYMIZE + pinned published version), wired into the drafter fail-closed (#166)** — LIVE | `evidence/AGENTCORE-GUARDRAIL-2026-09-05.md` |
| Contextual grounding | Filter present | **Enforced end-to-end on the drafter — grounded factual core is grounding-scored, boilerplate appended deterministically; a hallucinated determination is blocked, a legitimate notice is not (#150/#190)** — LIVE | `evidence/AGENTCORE-GROUNDING-DRAFTER-190-2026-09-05.md` |
| Multi-tenant isolation | Documented topology | **Hybrid multi-tenant LIVE — shared control plane, per-tenant data incl. each tenant's own audit ledger / WORM vault / approvals; cross-tenant deny proven; tenant derived from verified identity** | `evidence/AGENTCORE-MULTITENANT-{E2E,AUDIT}-2026-09-02.md` |
| Full traceability | Audit rows | **One correlation set joins agent reasoning spans + every gateway request + each tool's `aegis.call` + every Bedrock model body + the hash-chained WORM record, per tenant — LIVE; plus capture-every-API-call lineage via account CloudTrail→WORM with a zero-orphan coverage proof (#168)** | `evidence/AGENTCORE-OBSERVABILITY-2026-09-02.md`; `GOVERNED-CORE-1.10.0-LIVE-GATE-2026-09-05.md` |
| Containment | — | **Kill switch on the AgentCore path — interceptor + every tool Lambda + the Runtime read an SSM flag first, fail-closed, 13.9 s to effect, IAM SoD on engage/disengage (#)** — LIVE | `evidence/AGENTCORE-KILL-SWITCH-2026-09-03.md` |
| Cost governance | Reservation demo | **Per-tenant token + USD meter on every model call (reserve-before/commit-after), AWS Budgets USD ceiling whose breach engages the kill switch, meter == the Bedrock invocation log to the token; USD reconciled against Cost Explorer (#169)** — LIVE | `evidence/AGENTCORE-BUDGET-2026-09-03.md` |
| Audit fail-closed | Fail-open found | **Finalize writes COMMITTED WORM/hash-chained evidence BEFORE the exactly-once marker; args-hash-bound approvals cannot be reused for another action (#159/#162)** — LIVE | `GOVERNED-CORE-1.10.0-LIVE-GATE-2026-09-05.md` |
| Network posture | network.yaml not wired | **Tool + drafter Lambdas in private subnets w/ VPC endpoints; live sweep measured 0 NAT / 0 IGW (#170)** — LIVE | `evidence/AGENTCORE-NETWORK-WAF-2026-09-05.md` |

The single most important upgrade for an auditor: **capture-every-API-call lineage (#168) + token
chargeback (#169)** — one query now returns, for a case, every governed API call, model body, Cedar
decision, approval, and reconciled cost, in a tamper-evident WORM record.

## B. Remaining items to production-ready — by Well-Architected pillar

Status key: **[P]** product/platform work we own and can do now · **[A]** blocked on a real
(non-sandbox / AWS Organizations) account · **[E]** engagement / customer-owned by design.

### Security
- **[P] Enterprise IdP federation** — SAML/OIDC into Cognito, MFA policy, SCIM provisioning, and the
  group→`custom:tools`/scope entitlement mapping the gateway already consumes. Today every validated run
  uses a portable Cognito pool with admin-created users; the entitlement *contract* is proven, the
  federation is not built. This is the single biggest "demo vs production identity" gap.
- **[P] Delegated authorization / OBO** — distinct agent vs human identity, on-behalf-of token exchange,
  short-lived downstream credentials, revocation, and explicit confused-deputy / privilege-escalation
  tests. Partially present (bound approvals, IAM-verified kill-switch actor); the OBO exchange is not wired.
- **[A] WAF↔Cognito association (#189)** — the REGIONAL Web ACL is built as IaC; the association is blocked
  at the account level in the sandbox (native association hangs for Cognito; `AssociateWebACL` →
  `WAFUnavailableEntityException`; the account is not in an Organization). One-liner in a normal account.
- **[A] Organizations SCP/RCP guardrails (#172)** — preventative org-level controls (deny regions, deny
  disabling CloudTrail/guardrails, data-perimeter RCPs) need real AWS Organizations connectivity.
- **[P] Customer-managed KMS per data class** + rotation, and a **cross-account log/evidence archive**
  (the WORM vault + CloudTrail bucket should replicate to a separate security account).
- **[E] Independent third-party penetration test** and the **ATO / HITRUST / FedRAMP / IL** authorization.
- **[E] Real connector secrets** — Secrets Manager under the env path + a controlled egress path for any
  tier-4 system of record (Veeva/Argus, Epic/Availity, X12 835, SIS/LMS).

### Reliability
- **[P] DR for the evidence plane** — backup/restore and cross-region strategy for the audit ledger + WORM
  vault + approvals register, with stated RTO/RPO, plus a **DR game day**. WORM + retention is proven;
  regional failure recovery is not.
- **[P] Model fallback tested** — cross-region inference profiles / alternate model on Bedrock throttle or
  regional outage, exercised (the budget meter + kill switch must behave under fallback).
- **[P] Exactly-once + isolation under production-scale load** — the exactly-once finalize and per-tenant
  routing are unit- and gate-proven; a concurrency/replay storm at pilot scale (Gate-B exit) is not yet run.
- **[P] Quotas / throttling / DLQ operations** — document AgentCore Gateway + Runtime + Bedrock quotas,
  and the DLQ inspect/replay runbook for the workflow hop.

### Operational Excellence
- **[P] Day-2 operator console** — kill-switch status, per-tenant budget burn + alarm state, the pending-
  approval queue, and the per-case lineage viewer, in one pane. Today these are CLI/evidence-script driven.
- **[P] Full CI/CD** — deployment roles (not human creds), change sets, canary + rollback alarms, artifact
  signing (KMS/Sigstore), pinned deps + SBOM. A CI-evidence workflow exists; the release pipeline does not.
- **[P] Propagate governed-core 1.10.0 across all packs and re-gate LIVE** — benefits is live-gated at
  1.10.0; pharmacovigilance + edu are re-pinned offline (suites green) but need a live re-gate; **Housing
  shows a 1.10.0 pin in its requirements while `MATURITY.yaml` still records it at 1.4.0 "pending" —
  reconcile this drift**, then update the pharma/edu/housing pack READMEs to state the current pin.
- **[P] Platform-repo AgentCore reference deploy** — the packs deploy on AgentCore; the platform repo's
  own CDK/TF stack is still a primitive-validation stub (network_edge/identity_federation not wired there).

### Performance Efficiency
- **[P] Governed-hop latency budget** — measure and publish p50/p99 for a full case with all controls on
  (guardrail + Cedar + interceptor + masking add hops); set a latency SLO and right-size Lambda memory /
  provisioned concurrency for the drafter.
- **[P] Model right-sizing** — task-appropriate model selection (e.g. Haiku for classification, Sonnet for
  drafting) bound to the budget meter, with the choice recorded on the invocation.

### Cost Optimization
- **[P] Continuous CUR/Cost-Explorer reconciliation** — chargeback is proven once (#169); schedule it as a
  recurring job and surface per-tenant / per-case **showback** in the operator console.
- **[P] Cost of the controls themselves** — model and document the added cost of capture-every-API-call
  (CloudTrail data events), Comprehend, guardrail, and WORM storage, so the governance overhead is a known
  line item, and add evidence-lifecycle tiering (aged WORM evidence → cheaper storage class within the
  retention policy).

### Sustainability
- **[P] Region + model efficiency guidance** — prefer the smallest model that passes grounding; evidence/
  log lifecycle tiering; document region selection. Low urgency, but name it so it isn't a silent gap.

### Governance & audit-defensibility (the cross-cutting pillar this product exists for)
- **[E/P] Compliance EVIDENCE package per framework** — the CJIS / IRS-1075 / 42-CFR-Part-2 / GxP / FERPA /
  HIPAA control *mappings* exist; the auditor-ready binder (each control → its test → the live evidence
  artifact, indexed) is the gap. This is what converts "mapped" into "would pass an audit."
- **[P] Model-risk / evaluation gate** — a grounding/refusal/bias/prompt-injection eval harness run as a
  release gate (AgentCore Evaluations is in preview; wire it or a portable analog).
- **[P] Accessibility (WCAG 2.2 / Section 508, ahead of ADA Title II)** for any human-facing reviewer UI.
- **[P] Records management + legal hold** — COMPLIANCE Object-Lock profile + legal-hold workflow on the
  WORM vault for a real deployment (demo runs use GOVERNANCE/short retention).
- **[E] A named design partner + scoped pilot SOW** with success metrics — the commercial precondition to
  a production pilot.

## C. Ownership summary — what "finished" depends on

- **We can finish now (product/platform, [P]):** IdP-federation wiring, OBO exchange, the day-2 operator
  console, full CI/CD + signing, propagate + live-re-gate governed-core 1.10.0 across all packs (and fix
  the Housing version drift), the platform-repo AgentCore reference deploy, latency/cost SLOs, the
  compliance evidence binder, and the model-eval gate. These are the backlog we control.
- **Needs a real account ([A]):** the WAF↔Cognito association (#189) and Organizations SCP/RCP (#172).
  Code + IaC are in place and tested to the account boundary; they finish in a customer/non-sandbox account.
- **Customer / engagement-owned ([E]):** third-party pen test, ATO/HITRUST/FedRAMP authorization, live
  tier-4 connector credentials, and the signed pilot SOW + design partner.

## D. Highest-leverage next five (recommendation)

1. **Enterprise IdP federation + MFA + OBO** — closes the biggest identity gap and unblocks a real pilot.
2. **Propagate + live-re-gate governed-core 1.10.0 across all packs; reconcile the Housing 1.4.0↔1.10.0
   drift** — makes the whole portfolio consistent at the current control bar (an auditor checks consistency).
3. **Compliance evidence binder** (control → test → live artifact) for one framework end-to-end — turns the
   proven controls into something an auditor signs.
4. **Day-2 operator console** — kill-switch / budget / approvals / per-case lineage in one pane; this is
   what a CISO asks to see on day one.
5. **DR game day for the evidence plane + model-fallback test** — the reliability story behind the audit
   claims.

> Positioning that matches the evidence (2026-09-05): *"Aegis is an AWS-native governed-agent control plane
> whose core controls — deny-by-default Cedar authorization, fail-closed PII masking, tamper-evident WORM
> audit with capture-every-API-call lineage, per-tenant cost metering with a hard USD ceiling, one-command
> containment, and contextual-grounding enforcement — are live-validated end-to-end on Amazon Bedrock
> AgentCore in the vertical packs. It is being hardened from live-validated control core to a
> production-pilot platform: enterprise IdP federation, day-2 operations, a per-framework evidence binder,
> and DR are the remaining path."*


---

# 2026-09-05 — External deep-dive review: validation + action status

An external technical review (assessed at platform commit `211bbe7`, governed-core 1.10.0, all four
packs) reproduced several defects where "the strongest guarantees fail in exactly the fault conditions
those guarantees are supposed to cover." **Every finding below was re-validated against the actual code
(and AWS docs) — not taken on faith — then acted on.** Status key: **FIXED** (code changed + tests) ·
**CORRECTED** (claim/doc fixed) · **STAGED** (implemented, live re-gate pending) · **OPEN** (tracked).

## Critical blockers

**#1 WORM failure still permitted a commit — CONFIRMED → FIXED (governed-core 1.10.1).**
Verified: `evidence.record_event()` returned `stored=True, worm=False` on an S3 Object-Lock failure, and
`finalize_signoff` gated on `stored` alone (`committed = bool(res.get("stored")) or ...`) — so a commit
proceeded with `worm=False`. Fix: a single `evidence.is_durable()` predicate now requires the
hash-chained ledger write **and** the WORM copy; finalize/request/approve gate every side effect on it.
`record_event` REPAIRS a missing WORM copy on replay from the authoritative stored item, so a transient
S3 failure heals on retry instead of committing. Explicit `EVIDENCE_WORM_REQUIRED=false` opt-out for a
WORM-less sandbox (secure by default). Tests: `tests/test_finalize_failclosed.py` (stored=True/worm=False
must NOT commit; WORM-repair-on-replay commits; replay-without-WORM refuses).

**#2 request/approve audit-before-side-effect fail-open — CONFIRMED → FIXED (governed-core 1.10.1).**
Verified: `request_signoff` ignored its INTENT `record_event` result and started Step Functions anyway;
`approve_signoff` consumed the approval, released the task token, THEN wrote (and ignored) APPROVED
evidence — strandable. Fix: `request_signoff` refuses to start the execution unless the INTENT is durable.
`approve_signoff` is now an un-strandable idempotent saga: reserve (a retry by the same approver that has
not released re-enters) → **durable** APPROVED evidence → idempotent token release (already-released /
timed-out counts as released) → mark released. Evidence precedes the side effect; nothing strands.
Tests: `tests/test_signoff_saga_failclosed.py`.

**#3 nine-condition Cedar trusted caller assertions — CONFIRMED → FIXED (governed-core 1.10.1).**
Verified: the interceptor injected the signed tenant but forwarded `consent`/`purpose`/`budget_ok`/
`within_service_window` unchanged from the caller. Fix: the interceptor now STRIPS any caller-supplied
copy of those fields and injects only server-authoritative values — the server clock
(`within_service_window` from `SERVICE_WINDOW_*`), the live meter (`budget_ok`), and an optional pack
`authoritative_context` resolver for `consent`/`purpose`; without a resolver those stay UNSET so Cedar
denies (fail-closed). Tests: `tests/test_interceptor_authoritative.py` (caller values stripped/overwritten).
**CLOSED END-TO-END + LIVE-PROVEN (2026-09-05):** the benefits pack now ships
`lib/controls/authoritative_context.py` — the interceptor's resolver reads the authoritative consent
record and the case's authorized purpose from a server-side authz store (DynamoDB, case_id key, CMK/TTL,
`GetItem`-only for the interceptor). A from-zero `ben-perim` deploy proved it live: a case with a real
authz record → ALLOWED (returned an ELIGIBLE determination); a caller that FORGED consent/purpose on a
case with NO record → DENIED by `consent_purpose_before_assess`. That also proves the interceptor's
injection reaches the Cedar decision (the pattern would have inverted otherwise). Evidence:
`benefits_eligibility_agent/evidence/AGENTCORE-PERIMETER-AUTHZ-3-2026-09-05.md`. Torn down to zero residue.

**#4 supported release tag lacked the fixes — CONFIRMED → FIXED.**
Verified: `v0.4.0-pilot-rc1 = be39f1c` (2026-09-03, governed-core 1.9.0) predates the Sept-5 work, yet
RELEASE-MANIFEST claimed it was "cut from this tree and matches this count." Fix: RELEASE-MANIFEST
corrected (the false claim retracted); `RELEASE` + deploy guide + anchor docs moved to
**`v0.5.1-pilot-rc1`** (v0.5.0 → v0.5.1 after the #3 resolver landed), cut from current main
(governed-core 1.10.1 + all Sept-5 work + the 1.10.1 fixes + the #3 resolver), release-consistency gate
green. **LIVE re-gate DONE for the perimeter + #3 path** (from-zero `ben-perim` deploy, PASS, torn down —
see #3 above and `AGENTCORE-PERIMETER-AUTHZ-3-2026-09-05.md`). **STAGED:** re-running the heavier
full-portfolio gates (111 / kill-switch / budget / lineage — last green at 1.10.0) against this exact tag
is the remaining live step; they exercise the audit/approval paths the 1.10.1 offline fault-injection
tests already cover.

**#5 zero-egress breaks cold-start JWT verification — CONFIRMED → FIXED (IaC) / STAGED (live).**
Verified: the private NetworkStack created endpoints for Secrets/SFN/Comprehend/Bedrock/Logs/KMS/STS but
**no cognito-idp endpoint**, while the verifier fetches Cognito JWKS at cold start over a VPC with no
NAT/IGW. Fix: added the `cognito-idp` interface VPC endpoint (private DNS on). **STAGED:** a live
cold-start + key-rotation test in the zero-egress profile is the remaining verification.

**#6 no enforced production profile — CONFIRMED → FIXED.**
Verified: `env=prod` synthesized with dev defaults. Fix: `cdk/app.py` now REFUSES to synthesize
`env=prod` (or `-c profile=production`) unless every production control is explicitly on — customer KMS,
production/compliance retention, private network, non-sandbox identity + OIDC federation, WAF, Cedar
perimeter, model logging, account capture, COMPLIANCE Object-Lock — with an audited `-c
allow_insecure_prod=1` override. Proven live to refuse; regression test in `tests/test_cdk_context_flags.py`.

## Claims corrected (honesty)

- **"WAF association blocked at the account/Organizations level" (#189) — RETRACTED / CORRECTED.** AWS
  documents WAF↔Cognito association as **supported** and `WAFUnavailableEntityException` as a
  **propagation delay** (seconds to minutes); the repro retried only ~60 s, inside that window. The
  association harness now retries with backoff across ~6 min; a live re-run is pending. Evidence file and
  MATURITY corrected.
- **"AgentCore Gateway is not WAF-associable" — RETRACTED.** AWS now documents `GatewayAssociateWebACL`
  (<https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-waf.html>); the MCP runtime
  front door can be WAF-fronted directly. Corrected in the evidence + MATURITY.
- **"Every agent/model/tool/API call flows through Aegis" — SCOPED.** Only calls through the governed
  gateway or instrumented workflow are governed; direct Bedrock/Lambda/other-AWS calls are possible
  unless IAM/Organizations forbid them. See OPEN item below (IAM/org guardrails). Docs should say
  "every *governed-path* call," not "every call."
- **"Full nine-condition authorization" — now TRUE at the enforcement point** after #3 (fields
  authoritative); previously the predicates existed but four were caller-supplied. The authoritative
  consent/purpose *source* (consent record + workflow-bound purpose) remains a pack follow-up (#3 OPEN).
- **"Capture every API call" (#168) — SCOPED.** The trail captures management events + S3/Lambda data
  events; it is not literally every AWS data-event type (AgentCore Gateway data events need explicit
  advanced selectors). Describe as "every governed API call in the captured event set," and add selectors
  where a data-event type matters. (OPEN.)
- **"Every model body captured" — CONDITIONAL.** Only when Bedrock model-invocation logging is enabled
  (`-c model_logging=1`; AWS default off). The production profile (#6) now REQUIRES it for prod. Wording
  corrected to "when model logging is enabled (required by the production profile)."
- **"Signed agent manifests" — CONDITIONAL.** The capability exists; the benefits manifest ships
  `signature: null` and direct CDK deploy does not enforce verification. OPEN: sign the manifest and make
  the deploy/delivery gate refuse an unsigned/`null` manifest in the production profile.
- **"Independently verified" — CORRECTED to "internally reproduced."** The evidence is author-produced;
  there is no external signed attestation. RELEASE-MANIFEST already says "author-produced, synthetic data
  only — not independently audited or pen-tested"; keep that wording everywhere.

## Other production gaps (tracked)

- **OPEN — burn down the Checkov/Bandit baselines** (PITR, API access logging, Lambda DLQ/reserved
  concurrency, log-group KMS, bucket access logging, broad IAM). A baseline is a debt register, not
  "hardened"; start with the approval/evidence-durability, logging and IAM findings.
- **FIXED (Tier-1, 2026-09-05) — restrict direct Bedrock/Lambda bypass + protect ENFORCE config.** The
  AgentCore attachment provider's `bedrock-agentcore:*` is replaced by the enumerated control-plane CRUD it
  performs, and the drafter's `bedrock:InvokeModel` carries the **mandatory-guardrail** IAM condition
  (`Null: bedrock:GuardrailIdentifier=false`) — 2 CDK tests. The account/org half is the
  enforcement-perimeter section below (PERIM-1).
- **NOTED — AWS Budgets is a backstop, not a real-time breaker** (updates ~8–12 h). The real-time control
  is the per-call meter + kill switch; Budgets is the belt-and-suspenders ceiling. Docs already frame it
  this way; keep it.
- **OPEN — production-scale concurrency/replay test, DR game day, regional recovery, external pen test**
  before real customer data (also in the pillar register above).
- **OPEN — real system-of-record connector, enterprise OBO/delegation, full IdP-federation lifecycle**
  (the entitlement claim contract is proven; the lifecycle is not deployed).

## Net effect on the review's verdict

The review's headline blocker — *"a consequential action cannot occur without durable, immutable
evidence" is not currently true* — is now addressed in code (governed-core 1.10.1: #1, #2) with
fault-injection tests, released and re-pinned across all four packs, and the enforcement point no longer
trusts caller assertions (#3). The remaining path to a design-partner pilot is the **live re-gate against
`v0.5.0-pilot-rc1`** (including the private-network JWKS path and the WAF association with the corrected
retry window), the authoritative consent/purpose source, and the burn-down items above — none of which
re-open the durable-evidence guarantee.

---

# 2026-09-05 — Enforcement-perimeter review (second external teardown): validation + action plan

A second external review argued that a customer-account governance layer *"cannot guarantee capture of
every API call"* without organization-level SCPs and VPC-endpoint policies, that Bedrock model-invocation
logging creates an *unredacted secondary PII store*, that inline proxies degrade streaming/TTFT, and that
single-account designs lack multi-account aggregation; it proposed an SCP, a VPC-endpoint policy, a
CloudTrail configuration and a bypass alarm. **Every claim was validated against AWS documentation and the
code before anything was changed**, and every proposed artefact was linted rather than adopted. Status key
as above: **FIXED** · **CORRECTED** · **STAGED** · **OPEN** · **N/A**.

## Validation, claim by claim

| # | Review claim | Verdict | Evidence |
|---|---|---|---|
| 1 | "Captures every API call" cannot hold without SCPs / endpoint policies | **Partly valid → CORRECTED + FIXED** | Aegis's *proven* scope is the governed path (preventive) plus an account-wide capture trail (#168). The label "capture-every-API-call" invited the account-boundary reading and **no SCP / endpoint-policy artefact was shipped** (prose only in `docs/16` and the pack's network-hardening doc). Wording fixed; artefacts shipped (PERIM-1). |
| 2 | Full capture "requires CloudTrail **data** events for InvokeModel / Converse" | **Wrong per AWS docs → CORRECTED (in our favour)** | CloudTrail records `InvokeModel`, `InvokeModelWithResponseStream`, `Converse`, `ConverseStream` as **management** events ([Monitor Amazon Bedrock API calls using CloudTrail](https://docs.aws.amazon.com/bedrock/latest/userguide/logging-using-cloudtrail.html)); the #168 trail (management ALL, multi-region, WORM, file-validated) already records every direct invocation by any principal. **But** `ApplyGuardrail`, `InvokeAgent`/`InvokeInlineAgent`/`InvokeFlow`, `Retrieve`/`RetrieveAndGenerate`, async + bidirectional invokes and the AgentCore Gateway *are* data events we did not select — a real selector gap (PERIM-2). The lineage docstring also leaned on invocation logging for Bedrock coverage, which is mutable, per-region and non-WORM — corrected. |
| 3 | Invocation logging = unredacted PII store | **Mitigated on the governed path; store under-protected → FIXED** | The drafter refuses to draft unless the content carries a mask_pii-signed `sanitized_ref` bound to the signed digest (P0-1), so *its* invocations are de-identified before Bedrock. The account-level log also records **bypass callers'** raw prompts — precisely what the new alarm catches — and the store itself was `S3_MANAGED`, `DESTROY` + auto-delete, no Object Lock, no CMK **while the production gate now requires `model_logging=1`**. Fixed (PERIM-4). |
| 4 | Inline proxy doubles TTFT / breaks SSE streaming | **N/A → documented** | The drafter is a synchronous `converse()` inside a Step Functions workflow; there is no inline token proxy anywhere in the design. Agent-runtime streaming is AgentCore-native. Recorded as a design boundary in `org/README.md`. |
| 5 | Custom Lambdas + DynamoDB "lockouts" add cold starts / rate limits / quota pressure | **Valid ops item → OPEN (PERIM-7)** | True of the reserve-before meter and the idempotency writes; the design already documents Budgets as non-real-time. Needs a capacity/quota model and a reserved-concurrency decision — not a correctness defect. |
| 6 | Single-account; no cross-account aggregation | **Valid enterprise item → OPEN (PERIM-6)** | Landing-zone design exists (`docs/16-MULTI-ACCOUNT-LANDING-ZONE.md`); no IaC or two-account proof. |
| 7 | Proposed SCP (two statements, `aws:userId`, `aws:PrincipalType`, `bedrock:Converse`, SLR exemption) | **Unsafe as written → REJECTED, replaced** | Statement 1 ANDs `PrincipalType != AssumedRole` into the Deny, so **no role session is ever denied** — the EC2/ECS/Lambda bypass it targets passes. Statement 2 keys on `aws:userId` = `<role-id>:<caller-chosen session name>` ([global condition keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)) — defeated by `--role-session-name AegisGovernanceProxy-x`. `bedrock:Converse*` are not IAM actions (Converse authorizes as `bedrock:InvokeModel`, [Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)). SCPs never apply to service-linked roles or the management account ([SCPs](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)), so the SLR carve-out is noise. It is kept as a **regression fixture that must fail the lint**. |
| 8 | Proposed CloudTrail selectors (`Model`, `Guardrail`, `KnowledgeBase`, `AgentAlias`) + metric filter on `userIdentity.arn != "*Proxy*"` | **Directionally right; incomplete / unsafe → replaced** | Missing `AsyncInvoke`, `InlineAgent`, `FlowAlias`, `Prompt` and `AWS::BedrockAgentCore::Gateway`; the filter keys on the session-bearing ARN. Ours selects every documented type and keys on `sessionContext.sessionIssuer.arn` (the role) plus a second filter for IAM-user/root callers. |
| 9 | Console / playground needs `aws:UserAgent` denial | **Unnecessary → documented** | A playground call is the console principal calling `InvokeModel`; outside the allowlist it is denied by the inference statement. `aws:UserAgent` is spoofable and adds nothing. |

## Action plan — PERIM-1 … PERIM-8

| ID | Item | Layer | Status | Proof | Live gate |
|---|---|---|---|---|---|
| PERIM-1 | **Preventive account boundary**: corrected org SCP (11 real inference actions incl. agents/KB/async/batch; `ArnNotLike aws:PrincipalArn` allowlist; allowlisted-role protection; telemetry protection; control-plane changes only by the deployer) + standalone VPC-endpoint policy + renderer + lint | Org / network | **STAGED** (templates shipped, statically validated) | `benefits org/*`, `scripts/render_org_perimeter.py --lint`, `tests/test_org_perimeter.py` (4, incl. the proposed-SCP fixture) | Needs an Organization (#172): sandbox OU → `guardrail_proof` + `cedar_perimeter_proof` still pass while an operator-role `converse` is refused. Step 1 of the landing-zone runbook. |
| PERIM-2 | **Bedrock + AgentCore data-event capture** in the account trail (advanced selectors; docstring corrected) | Detective | **LIVE-PROVEN** (ben-t1 2026-09-06: management + 12 data-event types on the running trail; `ApplyGuardrail` data events captured) | `test_capture_trail_selects_bedrock_and_agentcore_data_events`; `org/cloudtrail-advanced-event-selectors.json` pinned equal | Next `capture_all=1` gate: `lineage_proof` + an `ApplyGuardrail` call from a test role appears in the WORM capture |
| PERIM-3 | **Bypass alarm** `<prefix>-bedrock-perimeter-bypass` from the capture log (issuing-role allowlist + IAM-user/root) on the ops topic | Detective | **LIVE-PROVEN** (ben-t1 2026-09-06: a real direct `Converse` by an IAM user → ALARM; metric = exactly the non-allowlisted inference events (1); the drafter's 2 calls excluded) | `test_bedrock_perimeter_bypass_alarm_from_capture_trail` | Same gate: an operator-role `converse` → ALARM within 5 min; the drafter's own calls do not trip it |
| PERIM-4 | **Invocation-log store as regulated data**: CMK (log group + payload bucket, bedrock service granted the key), Object-Lock COMPLIANCE + versioned + RETAIN + no auto-empty under `-c model_log_lock_days>0`; **production gate requires it** | Data protection | **LIVE-PROVEN** (ben-t1 2026-09-06: CMK log group + Bedrock delivered the drafter's rows through the cross-service key grant; lock mode exercised at `lock_days=0` for the disposable env — the COMPLIANCE-lock variant is IaC-asserted) | `test_invocation_log_store_is_regulated_data_under_production_settings`; `app.py` `_require_production_controls` | Next `model_logging=1` + `kms=customer-managed` gate: Bedrock delivers to the SSE-KMS bucket + CMK log group (the cross-service key grant is the risk to verify) |
| PERIM-5 | **In-VPC endpoint policy** on `bedrock-runtime` (EXACT pinned drafter role + `approved_bedrock_principals`) | Network | **LIVE-PROVEN** (ben-t1 2026-09-06: the drafter drafted twice through the policied endpoint in private mode; L12 fixed the wrong-case pattern first) | `test_bedrock_runtime_endpoint_policy_admits_only_the_governed_drafter` | Next `network_mode=private` gate (`network_waf_proof`): drafter still drafts through the endpoint |
| PERIM-6 | **Multi-account aggregation**: org trail → log-archive account, cross-account EventBridge for the bypass alarm, central Security Hub | Landing zone | **OPEN (P1)** | design in `docs/16` | Two-account live proof; deliver as IaC in `org/` |
| PERIM-7 | **Egress / non-Bedrock model surfaces** (SageMaker endpoints, third-party APIs): optional no-IGW/NAT SCP + Network Firewall pattern for workload OUs; pack already asserts 0 NAT / 0 IGW in private mode | Org / network | **OPEN (P1)** | `test_network_zero_public_egress` (pack) | Template + lint, then the same sandbox-OU gate as PERIM-1 |
| PERIM-8 | **Capacity & quota model**: Lambda reserved concurrency for the drafter/interceptor, DynamoDB on-demand vs provisioned for the meter/ledger, Bedrock TPM/RPM quotas and model units, cold-start budget | Ops | **OPEN (P2)** | — | Load test at pilot volume; record in DEPLOYMENT-GUIDE |
| — | **Claim precision**: "capture-every-API-call" = account-wide *capture*; *prevention* of direct calls = org boundary (PERIM-1) | Docs | **CORRECTED** | governed-core README, platform README/MATURITY, benefits README | — |
| — | Streaming / TTFT | — | **N/A** | `org/README.md` | — |

## Net effect

The review's verdict — *"an opt-in proxy rather than an enterprise governance framework"* — was right
about one thing and wrong about two. Right: prevention of *direct* Bedrock calls is an organization-level
control, and we had not shipped it. Wrong: CloudTrail *already* records every model invocation in the
account as a management event into our WORM trail, and the design has no inline token proxy to degrade
streaming. With PERIM-1..5 the pack now ships **prevention (SCP + endpoint policy), capture (every Bedrock
surface, WORM) and detection (bypass alarm)** as one tested set — with the honest caveat that the SCP is
validated statically until a customer Organization is available (#172), which is why it sits first in
the landing-zone runbook rather than in the pack's own from-zero gate.

---

# 2026-09-05 — Third external review (re-run against HEAD `bcf8d7a`): release integrity + runtime path

The reviewer re-ran against current HEAD and separated *what is fixed in code* from *what a customer can
actually deploy*. Verdict: the `governed-core` 1.10.1 fixes are real, but **release integrity was broken** —
the packs' supported tags predate the fixes, their integrity verifiers failed, and two AWS-documented
production blockers sat in the live runtime path. **Every finding was reproduced before it was acted on.**
Status key as above.

## Validation, finding by finding

| # | Finding | Reproduced? | What was actually wrong | Status |
|---|---|---|---|---|
| R1 | Pack integrity verifiers fail (Benefits, PV, EDU); "mirrored control files drift from the declared lock/version" | **Yes** — `lib/verify_core.py` rc=1 in all three; Housing clean but declared 1.10.0 vs pin 1.10.1 | `lib/CORE_VERSION`/`core.lock` still said 1.9.0 while `requirements-core.txt` pins 1.10.1; `lib/controls/mask_pii.py` (PV/EDU, #164 propagation) and benefits' new `lib/controls/verify_manifest.py` + `authoritative_context.py` were added **without a relock**. CI runs the verifier, so all three mains were red. | **FIXED** — relocked at 1.10.1 in all four packs (`regen_core_lock.py --set 1.10.1`), verifiers OK, suites green (benefits 278/279, PV 191, EDU 189, Housing 186), pushed. **Closure test:** the verifier is already a CI gate; the miss was procedural (relock is not automatic). Added to the release checklist below (REL-4). |
| R2 | Supported tags older than the fixes; benefits tag ~1,700 lines behind HEAD; some release docs still describe 1.9.0 | **Yes** — benefits `RELEASE`=v0.5.1 (pre-Tier-1), PV v0.3.0 (1.9.0 gate), EDU `RELEASE`=v0.1.3 while its docs/tags say v0.3.0, Housing `RELEASE`=v0.9.6 while v0.10.0 exists | The "1.9.0" sentences are accurate history of *older* tags, but the **supported tag ≠ the fixed core** in every pack, and two `RELEASE` files disagree with their own tags/docs. | **DONE** (REL-1 2026-09-06, REL-2 2026-09-05) — benefits: `v0.5.2-pilot-rc1` cut after the Tier-1 live gate (REL-1). Siblings: cut `v0.4.0-pilot-rc1` (PV, EDU) and `v0.11.0` (Housing) from the relocked mains with release docs stating exactly what is live-gated vs offline-gated on 1.10.1 (REL-2). |
| R3 | Pack tests "pass only when `governed-core` source is injected into PYTHONPATH" | **Partly** — with the pinned wheel installed (`pip install --require-hashes -r requirements-core.txt`, which each pack's CI does) the suites pass with no PYTHONPATH; without it `conftest.py` fails at `import governed_core` | A documentation gap: the test-run instruction was not next to the suite. | **FIXED** — README/START-HERE test instructions state the install step (REL-3). |
| R4 | Checkov blocks new findings but baselines existing failures (reviewer counted 86) | **Yes** — `WOGplatform/infra/.checkov.baseline`: 10 templates, **93 check-instances**: CKV_AWS_28 (DynamoDB PITR) ×13, 115/116/117 (Lambda reserved concurrency / DLQ / VPC) ×13 each, 173 (Lambda env-var KMS) ×12, 119 (DynamoDB CMK) ×10, 158 (log-group KMS) ×6, 18 (S3 access logging) ×4, 111/107/109/110/95 (IAM) ×9 | A baseline is a debt register; the count is the debt. | **OPEN (P1)** — CHK-1 burn-down below, phased by cost. |
| R5 | Runtime accepts an unvalidated `prompt` (AWS: structured input can cause direct tool dispatch) | **Yes** — `lib/runtime/agent.py` took `payload["prompt"]` verbatim, any type, unbounded | A list/dict prompt would reach Strands as content blocks. Tool calls would still hit the Cedar gateway, but the entrypoint had no input contract at all. | **FIXED** — `validate_input()`: prompt must be a plain string ≤ 4000 chars (no NUL), `case_id`/`requester` short identifiers; refused **before** the kill-switch read, tenant derivation, gateway and model; `access_token` type-checked. 5 tests incl. an I/O-ordering proof (RT-1). |
| R6 | Deployment relies on the AgentCore CLI-generated execution role (AWS: development/testing only) | **Yes** — `_configure.sh` ran `agentcore configure … -ecr auto` with no `--execution-role`; `_obs_setup.sh` then patched the CLI role with an inline SSM/budget policy; a generated `ssm-pol.json` carrying the raw account id was committed | Also: the runtime's own Strands model carried **no guardrail**, so the mandatory-guardrail IAM condition could not be applied to the runtime role. | **FIXED (IaC + tests; live gate staged)** — compute stack exports `RuntimeExecutionRole` (`<prefix>-agentcore-runtime`): the AWS-documented runtime policy scoped to region/account/runtime name + SSM, budget meter, ApplyGuardrail, SourceAccount/SourceArn trust; with a guardrail deployed, model invocations carry `Null{bedrock:GuardrailIdentifier:false}`. `_configure.sh` **refuses** to run without the role ARN; `_launch.sh` passes `GUARDRAIL_ID/VERSION` so `agent.py` sets Strands `guardrail_id/version`; `_obs_setup.sh` never patches an IaC role; `ssm-pol.json` removed + gitignored. The deterministic role name feeds the org SCP allowlist and the bypass alarm automatically. 2 CDK tests + 1 runtime test (RT-2). |
| R7 | SCP/VPC boundary staged + statically tested, not live-proven; multi-account + non-Bedrock egress open | **Agreed** — matches PERIM-1/6/7 status | — | as recorded (PERIM-*) |

## Action items — REL-1 … REL-4, RT-1 … RT-3, CHK-1

| ID | Item | Status | Closure | Validation |
|---|---|---|---|---|
| REL-1 | **Benefits supported tag = fixed core**: cut `v0.5.2-pilot-rc1` from the Tier-1 + perimeter + runtime-hardening tree | **DONE 2026-09-06** | tagged from the exact tree the `ben-t1` gate passed on (attempt 11) | `tests/test_release_consistency.py` (RELEASE ↔ anchors), `tests/test_doc_counts.py`, evidence `TIER1-REGATE-2026-09-06.*` |
| REL-2 | **Sibling supported tags = fixed core**: PV/EDU `v0.4.0-pilot-rc1`, Housing `v0.11.0`; `RELEASE` files reconciled with tags and docs | **DONE 2026-09-05** (tags cut; every anchor re-audited 2026-09-06 to say offline-gated on 1.10.1 + the exact last live gate) — the live re-gates on 1.10.1 are tracked as **REL-5** | cut from relocked mains; release docs say "offline-gated on 1.10.1; last live gate on 1.9.0 (date/env)" until each pack's live re-gate | each pack's release-consistency test; `git describe` == `RELEASE` |
| REL-5 | **Live re-gates on governed-core 1.10.1 for PV / EDU / Housing** (111 + kill switch + budget + lineage, from zero, two tenants, real Runtime) — Housing has NEVER had an AgentCore-era live gate (only the 2026-07-24 Gate-B run) | **OPEN (P1)** | run the benefits gate harness (`scripts/tier1_regate.py` pattern + the 111/kill-switch/budget drivers) per pack; Housing first needs its multi-tenant / runtime wiring parity checked against benefits | each pack's `evidence/AGENTCORE-*-2026-09-*.md` on the 1.10.1 tag |
| PAR-1 | **PV / EDU parity with the 2026-09-05 controls**: capture-all trail + lineage (#168), enforcement perimeter (endpoint policy, bypass alarm, CMK invocation store), output guardrail as IaC + grounded drafter (#166/#190), WAFv2 on Cognito (#170), authoritative Cedar context resolver (#3) | **DONE 2026-09-06 — all 5 steps** (PV `6381f23`+`288bba1`+`54133e7`+`c6bf80c`, EDU `403ca20`+`339fd71`+`3d9b365`+`6cb762a`): capture-all lineage, enforcement perimeter, regulated invocation store, L6 restore-aware logging, L9 endpoints, L12 pinned drafter, L3 CMK families, output guardrail as IaC + grounded drafter (L14 shape), WAFv2, L11 entitlement grant as IaC, authoritative Cedar context resolver (#3) + authz store + L18 ingest attestation, the perimeter Cedar profile (#160/#161) behind `-c perimeter=1`, and the fourth-review ports R4-3 (exact-guardrail IAM + explicit deny) / R4-8 (deny the *ForUser paths) / R4-5 (runtime pins 1.10.1). **PACK-PARITY 15/15 for both.** Quantitative (#161) is N/A on PV (no numeric decision field) and recorded as such. Offline-gated only: CDK assertions + cedar lint + unit + a full-switch synth per pack — **live-proven only on benefits**; the live re-gate here is REL-5 | port the benefits stacks (lineage/observability/network/identity/compute) construct by construct with the benefits CDK tests; `docs/PACK-PARITY.md` flips ❌→✅ only from the code | `tools/check_pack_parity.py --check`; each pack's CDK tests; then REL-5 live |
| PAR-2 | **Housing full uplift**: hybrid multi-tenant, kill switch, budget + USD ceiling, model-invocation logging, runtime port (benefits template + input contract + IaC execution role), then the PAR-1 set | **OPEN (P1, 2026-09-06)** — Housing's CDK is at the July Gate-B level (private network + MFA only) | port in the same order the controls landed on benefits (1.6 → 1.8 → 1.9 → 110 → RT → 09-05); `ssm-pol.json` with a raw account id removed | parity matrix ✅ across the row; Housing unit + CDK suites; then REL-5 live (first AgentCore-era live gate for Housing) |
| REL-3 | **Test-run instructions** next to the suite (install the hash-pinned core first) | **FIXED** | README/START-HERE "Run the tests" | reviewer reproduction without PYTHONPATH |
| REL-4 | **Relock is part of the change, not a follow-up**: any edit under `lib/` must regenerate `core.lock` in the same commit | **DONE 2026-09-06** | CI already ran `lib/verify_core.py`; every pack now ships a versioned pre-commit hook (`tools/hooks/pre-commit`, `bash tools/install_hooks.sh`) that refuses a `lib/` commit whose lock does not verify — it caught its first real case the same hour (benefits runtime edit without a relock) | `lib/verify_core.py` in CI + the hook locally |
| RT-1 | Runtime **input contract** | **FIXED** | `agent.validate_input` | `tests/test_runtime_input_contract.py` (5) |
| RT-2 | Runtime **execution role as IaC** + guardrail on the runtime model | **FIXED in IaC; live gate staged** | compute `RuntimeExecutionRole`; `_configure.sh --execution-role` | CDK tests (2) + runtime test; **next runtime gate** (`gate_111` / `obs_two_tenant_proof`) launched on the IaC role must pass, and a runtime model call must appear guardrail-assessed in the invocation log |
| RT-3 | Propagate RT-1/RT-2 to PV / EDU / Housing runtimes (same `lib/runtime` template) | **DONE for PV + EDU 2026-09-06 (IaC-asserted); Housing folded into PAR-2** — Housing's runtime is the pre-1.9.0 template and needs the full benefits runtime port first (REL-5 prerequisite) | PV `2020cdd`, EDU `5a2a33d`: `validate_input`, guardrail on the runtime model, IaC execution role + drafter mandatory-guardrail condition, `_configure.sh` refusal | PV/EDU: 5 runtime tests + 2 CDK tests each (206 / 204 collected); live runtime gate on the IaC role per pack is REL-5 |
| CHK-1 | **Checkov baseline burn-down** (93 → 0 with justified skips) | **OPEN (P1)** | Phase A (IaC flags, cheap): PITR ×13, DynamoDB CMK ×10, log-group KMS ×6, Lambda env KMS ×12, DLQ ×13 → ~54. Phase B (design): reserved concurrency ×13 (capacity model, PERIM-8), Lambda-in-VPC ×13 (private mode), S3 access logging ×4. Phase C: IAM 111/107/109/110/95 ×9 (scope the writes). Every remaining item carries an inline `checkov:skip` with the rationale. | `checkov` with an **empty** baseline in CI; the baseline file deleted |

## Net effect

The reviewer's distinction — *fixed on `main` ≠ deployable by a customer* — was correct and is now the
release rule: a pack's supported tag must be cut from a tree whose integrity lock, pinned core, and live
gate all agree, and the docs must say which of those three the tag actually has. Benefits reaches that
state with `v0.5.2-pilot-rc1`; the siblings get honest 1.10.1 tags now and their live re-gates as the next
cross-pack milestone.

---

# 2026-09-05 — Live-found register: what the Tier-1 from-zero gate caught that the unit suite could not

Every item below passed CDK synthesis assertions and the offline suite, and **failed on the first real deploy
of that path**. Each is now fixed *and* pinned by a test that encodes the live fact, so the class cannot
recur silently. Recorded because a reviewer should weigh "IaC-asserted" against "live-proven" with exactly
this list in mind.

| # | Surface | What the live deploy said | Why the suite was blind | Fix + pin |
|---|---|---|---|---|
| L1 | `cognito-idp` interface endpoint (deep-dive #5 zero-egress JWKS) | "does not support the availability zone of the subnet" — offered only in us-east-1b/1c/1d; VPC pinned to 1a+1b | AZ availability of an endpoint service is account/region data, invisible to synth | VPC pinned to AZs every endpoint service offers (`describe-vpc-endpoint-services`-verified), `-c vpc_azs` override; CDK test asserts subnets/endpoints stay in the vetted set |
| L2 | CloudTrail advanced selectors (PERIM-2) | "resources.type field value is not valid" — `AWS::Bedrock::Prompt` is rejected | CloudFormation validates the type only at PutEventSelectors time; a docs summary had listed it | Probed every type on a throwaway trail; Prompt removed, `BedrockAgentCore::Runtime`/`RuntimeEndpoint` added; test pins Prompt out; org selector file regenerated |
| L3 | CMK key policy (customer-managed KMS) | Step Functions log group refused the key: grant covered `/aws/lambda/<prefix>-*` only | Key-policy conditions are opaque strings to synth; no test enumerated the log-group families | Grant lists every family the pack encrypts; CDK test enumerates them |
| L4 | AgentCore attachment provider (Tier-1 least-privilege) | Gateway went FAILED: `CreateGateway` needs `bedrock-agentcore:CreateWorkloadIdentity` (a dependency the wildcard had hidden) | The enumerated list was derived from what the provider *calls*, not what the service *does on its behalf* | Workload-identity Create/Get/Delete/List enumerated; CDK test pins them |
| L5 | Teardown helper | `BypassGovernanceRetention` on plain buckets (InvalidRequest); AgentCore sweep silently failing on an old host boto3 — an engine from the morning's gate survived | Errors swallowed; residue report omitted buckets, log groups and AgentCore | Per-bucket lock check, gateways swept before engines with retry on the async conflict, errors printed, residue report complete |
| L6 | Account model-invocation logging | The stack's `on_delete` deletes the account's pre-existing (platform runbook) config | Account singleton; nothing in the pack owns the prior state | **CLOSED 2026-09-06** (benefits `24b6895`): Lambda-backed provider snapshots the prior config to a stack-owned SSM parameter on create and RESTORES it on delete (5 unit tests with fakes + a CDK test); the gate driver's own snapshot/restore stays as belt-and-braces |
| L7 | AgentCore attachment provider (policy attach) | Cedar policy "did not reach ACTIVE" with no reason; the provider had polled one target, then created the policy while the gateway's other targets were still settling | The provider's state machine was written against one target; status reasons were discarded | Every target waited to READY + a settle window; `_create_policy_active` retries only the transient "unrecognized action" and surfaces `statusReasons`; `_wait` fails fast on terminal states naming the resource; provider unit tests (4) |
| L8 | AgentCore attachment provider (least privilege, 2nd pass) | Policy creation refused: "Insufficient permissions to call gateway" — policy validation reads the gateway's tool list *as the caller* | `InvokeGateway` is a data-plane action the docs' control-plane CRUD list does not mention | Separate `AgentCorePolicyValidationReadsGateway` statement scoped to the account's gateways; CDK test pins the provider's action set incl. it |
| L9 | Private-mode VPC endpoints (network_mode=private) | Deploy PASSED, then every gateway `tools/call` returned 500 — even the zero-entitlement caller got a 500, not a Cedar deny. Direct invoke of a tool Lambda: `Sandbox.Timedout` after 30 s. Every governed tool reads the kill switch from SSM first and the budget meter writes CloudWatch metrics; the VPC had no `ssm` or `monitoring` endpoint | The endpoint list was hand-maintained; nothing derived it from what the deployed code actually calls | `SsmEp` + `MonitoringEp` added; CDK test derives the required endpoint set from the boto3 clients reachable (transitive imports in the staged bundle) from the DEPLOYED handler modules and asserts one exists for each — the next missing service fails at synth |
| L10 | Gate driver P3 accounting | `metric_sum == 1` failed with 3: the guardrail proof's direct `ApplyGuardrail` calls by the deployer user are real, correctly-counted bypasses (and proved the data-event selectors live) | The assertion encoded the driver's own call count, not the perimeter's definition | Assertion is now exactness against the capture log: metric = IAMUser/Root Bedrock events; the drafter's allowlisted calls exist and are excluded |
| L11 | Zero-default entitlement (#160) | Attempt 9: every tool ran (L9 held) and the Cedar proof passed, but the guardrail proof's caseworker was denied every tool — `require_entitlement` admits only a non-empty `custom:tools` claim or the `tools_granted` group, and NEITHER was IaC (a proof script had been creating them by hand) | The policy was tested with users a script provisioned, never with what the stacks alone provide | Identity stack provisions the `custom:tools` attribute and the `tools_granted` group; the guardrail proof grants the entitlement; CDK test ties the manifest policy to the provisioned grant |
| L12 | Bedrock VPC-endpoint policy + org SCP/VPCE principal | The policies named the drafter by a guessed CDK role-name pattern (`<prefix>-compute-coretoolsServiceRole*`); the real physical name is `<prefix>-compute-CoreToolsServiceRole<hash>-<rand>` and `ArnLike` is case-sensitive — the drafter would have been refused at the endpoint the first time it ran through it | A pattern written from the construct id, never compared to a deployed role name | Drafter role name pinned (`<prefix>-compute-coretools`), endpoint policy and org templates name the EXACT ARN (no wildcard), `DrafterRoleArn` output; CDK test asserts the pinned role is the one the core-tools function assumes |
| L13 | Gate teardown | CloudTrail keeps delivering for minutes after `StopLogging`; the capture bucket was non-empty again when CloudFormation deleted it, `cdk destroy` aborted on lineage and left the lower stacks standing | The 20 s post-stop wait was a guess | Driver re-empties the bucket and deletes remaining stacks dependents-first with waits/retries; the teardown verdict is the cleanup's own residue report; P3 capture counts use the metric filter's exact inference event set |
| L14 | Grounded drafter in the PRODUCTION path (#190) | Full-portfolio gate attempt 3 (2026-09-06): every workflow run ended `DraftNotice -> ManualReview` and every runtime draft was blocked — the contextual-grounding filter refused the notice because the determination it stated was not in the grounding source. The workflow's `DraftNotice` passed only the masked application; the earlier guardrail proof had pre-baked the determination INTO the masked text (a proof artifact, not the production path) | The proof exercised the drafter with an input shape the workflow never produces; no test asserted that the workflow's payload carries what the grounded drafter needs | **CLOSED 2026-09-06** (benefits main): the deterministic engine's output is a REQUIRED, allowlisted drafter input (`determination`, rendered into the grounding source from fixed fields — never caller free text); the workflow passes `$.assessment.out`, the gateway schema requires it, the manifest is re-signed; without it the drafter refuses fail-closed BEFORE any model spend. Test pins the workflow payload + schema + refusal |
| L15 | Runtime prompt path under the output guardrail (RT-2) | The observability proof's operator prompt ("NEVER ask for or restate raw applicant details … If a tool is denied, stop and report the control") was flagged `PROMPT_ATTACK` at LOW confidence and BLOCKED at HIGH filter strength — a false positive on an imperative caseworker instruction, first seen because RT-2 made every runtime model call guardrail-assessed | Prompt-attack scoring is a model judgement; no offline test can predict it, and the runtime had not been guardrail-assessed in earlier gates | Proof wording changed to plain operator language (verified with `ApplyGuardrail` before the re-run); the guardrail strength is deliberately UNCHANGED (fail-closed). **Product note for pilots:** imperative/negation-heavy operator prompts can be refused at HIGH strength; the refusal is visible and audited, and `-c` guardrail strength is the customer's manifest decision |
| L16 | Proof scripts vs #160 zero-default entitlement | Attempt 2: gate_111 / kill-switch / budget / lineage proofs created caseworkers WITHOUT the `tools_granted` grant (the same class as L11, in six more scripts) and were denied every tool | Each proof provisioned its own users by hand | Every proof grants `tools_granted`; the MT proof's tenant-less identity carries it too, so its denial is provably for the ABSENT TENANT, not the absent entitlement |
| L17 | Contextual grounding on the notice drafter (#190) | Attempt 4: with the determination now IN the grounding source, GROUNDING scored 0.99 on faithful factual cores but RELEVANCE scored 0.32–0.56 at threshold 0.55 — every legitimate notice was still blocked, on relevance alone (the earlier Tier-1 pass was one answer landing at 0.56). Measured with `ApplyGuardrail` against the deployed guardrail | Relevance is a model judgement on a terse structured answer; no offline test can score it, and the drafter requested no guardrail trace so the blocked reason was invisible | GROUNDING stays BLOCKING; RELEVANCE is DETECTIVE by default (`grounding.relevance_action: NONE`, scored + traced; `BLOCK` re-arms it once PQ has a threshold that holds); the pinned version's signature carries the action; the drafter requests the trace so a blocked draft's filter + score land in the invocation log. CDK test pins both actions |
| L18 | Authoritative consent / purpose (#3, #163) with `-c perimeter=1` | Attempt 4: every real runtime flow was denied at `assess_eligibility` (`consent_purpose_before_assess`) — NOTHING in the production path wrote the authz record the interceptor's resolver reads; only the Cedar proof had seeded it | The resolver was proven with a proof-seeded record; no test asked who writes it in production | Ingest (the one door raw content enters, by a verified caseworker in MT mode) records the caseworker's explicit attestation of the applicant's consent + the case's authorized purpose (`consent_attested: true`, `purpose` in the Cedar-allowed set), server-side; nothing else may write it (the interceptor keeps GetItem only); a caller-supplied consent/purpose is still stripped. Fail-closed without it. Unit + CDK tests; every proof attests as the caseworker's client would |
| L19 | Runtime mid-session stop (kill switch / budget) | Attempt 4: the BUDGET stop was computed correctly inside the session, but leaving the MCP client re-raised its teardown error ("Connection to the MCP server was closed" — the gateway had refused the in-flight tool call under the same cap) and the caller saw HTTP 424, not the governed refusal. The EDU runtime had carried a teardown guard since its 2026-09-04 gate; the benefits template never received it — **runtime drift in the wrong direction** (see R4-5) | The unit fakes never raised on `__exit__`; the fix lived in one pack's copy of the template | The session records its outcome first; a teardown error after an outcome is logged, never surfaced; the containment-cause walk descends into ExceptionGroups. Ported to PV + EDU the same day. Unit test raises on teardown in all three packs |
| L20 | Negation-blind eligibility extraction (`intake_application`) | Attempt 6: the extractor matched the bare token `tanf` in an application reading "... **no TANF**." and set `categorical_eligibility=True`. Categorical eligibility SKIPS the income/resource test, so a negation-blind match silently converts an income-tested case into an automatic approval - a materially wrong legal determination drawn from text that says the opposite. **What caught it was the contextual-grounding guardrail, not a test**: the drafter's model wrote that the case facts and the engine's determination contradicted each other, GROUNDING scored 0.31 against a 0.55 threshold, the draft was blocked fail-closed and the case went `DraftNotice -> ManualReview` instead of to sign-off. No unit test found it because every fixture asserted the positive case. | Negation-aware scan (`_categorical_from_text`): a benefit token counts only when no negation cue appears in the clause around it, with a clause boundary ending the negation window ("no TANF. Receives SSI" is still categorical). 12 regression cases in `tests/test_tools.py` - 7 negated, 4 granted, 1 explicit-field-wins. The same class exists in Housing (`elderly`/`disabled`) - carried into PAR-2 - and in PV's `_SERIOUS` flags, where it over-flags seriousness (fail-safe for PV, still wrong; tracked as L20b). |
| L20b | The L20 class swept across the portfolio | The benefits negation bug was not one bug. Every pack pulls decision-relevant flags out of free text the same way, and three more instances were found: **edu_financial_aid** decided dependency status with a bare SUBSTRING check (`"independent" in low`), so "the student is not independent" set `dependency="independent"` - and dependency decides whether PARENTAL income counts toward the SAI, so it changes the aid determination itself (the worst of the four); **housing** granted the elderly/disabled preference from "is not disabled", assigning a household to a preference category its own application denies; **pharmacovigilance** flagged ICH E2B seriousness from "no hospitalization required" and "not life-threatening". | ONE shared `lib/controls/negation.py` in every pack, staged flat into the Lambda bundle - a copy per pack is how this class returns. Fail-closed for ASSERTIONS: an ambiguous or negated mention never counts, so errors fall on "not asserted", which routes to a human rather than to an automatic grant. PV's direction is called out at the call site: over-flagging seriousness is the SAFE error there (it escalates, at worst filing an unneeded report), so this was never a patient-safety bug - but an ICSR that records a criterion the narrative rules OUT still misstates the reporter's account. A KNOWN LIMITATION is asserted by a test rather than described: a mixed clause ("Unexpected reaction, not in the RSI") is a human reader's UNLISTED but degrades to `unknown`, because the negation cue sits in the window. The window is deliberately NOT widened to guess - a wrong `listed` suppresses an expedited report, `unknown` only costs a human look. Real clause parsing is the actual fix, and the test says so. |
| L21 | Lineage proof read log-delivered sources with no settle window | Attempt 6: `lineage_proof.py` read CloudTrail / model-invocation / gateway logs ONCE, immediately after the case ran. On a from-zero deployment the capture-all trail is minutes old and CloudTrail's delivery into CloudWatch Logs lags the API call it records, so the proof saw `cloudtrail_lambda_invokes=0`, `model_invocations=0`, `gateway_requests=0` while DynamoDB (11 aegis calls) and Step Functions (17 events) - read directly, not through log delivery - were fully populated. Every governed tool was reported as an orphan. Every previous PASS was on stacks that had been delivering for hours; proving the platform from zero is exactly what surfaced this. | Bounded settle (`--settle-max-sec`, default 900): re-read the three delivered sources until CloudTrail shows at least one governed Lambda invoke in the window, or the deadline passes. The wait is RECORDED in the evidence and an expired deadline still FAILS - "we waited 15 minutes and CloudTrail delivered nothing" can never be confused with "we did not wait". |
| L21c | CloudTrail `eventTime` is second-granular; the proof window was milliseconds | The L21 settle worked, but the lineage proof still reported orphans on some runs. CloudTrail stamps `eventTime` to **one-second** resolution, while the proof's window came from millisecond timestamps taken around the case. An invoke that really happened at `12:00:03.critical` is recorded as `12:00:03.000`, which falls OUTSIDE a window starting at `12:00:03.412`. The proof was rejecting evidence it had correctly retrieved. | The window is snapped outward to whole seconds ONCE, in `main()`, before any source is read: `start = (start // 1000) * 1000` and `end = -(-end // 1000) * 1000`. Doing it in one place matters - see L21e. |
| L21d | A tool alias defeated by a stale default prefix - dead code that had never fired live | `tool_of()` maps a Lambda's log-group stem to the governed tool name via an alias table, one entry of which was keyed on the deployment prefix (`ben-gate-coretools` -> `benefits_core`). The `fp` environment uses the prefix `ben-fp-`, so the key never matched and the alias silently did nothing. It had **never once fired against a live deployment** - the table was written against an older environment's names and no test covered it, because the aliases only matter when real log groups exist. | The alias is now matched prefix-independently: any alias key that appears anywhere in the stem resolves, so the mapping survives a change of environment name. The lesson recorded is about the class: a lookup table keyed on a deployment-specific string is untested code until it runs against that exact deployment. |
| L21e | Self-inflicted: widening one side of a two-sided comparison | Applying the L21c second-snap to the CloudTrail side only turned a genuine orphan into an `invoked_not_audited` disagreement - the trail side now admitted an event the audit side's narrower window still excluded. I had made the proof WORSE while fixing it, and the failure mode changed shape rather than disappearing, which is what made it look like a new bug. | The window is computed once and applied to every source (L21c). Recorded verbatim as self-inflicted, because the honest register is the point: a fix that alters only one arm of a comparison is not a fix. |
| L21g | The audit side was read once, before the thing it was waiting for arrived | The settle loop re-read CloudTrail every poll but read the DynamoDB `aegis.call` audit rows ONCE, before the loop. So the proof could wait fifteen minutes for CloudTrail and still compare it against a stale audit snapshot. `signoff_register`'s audit line was verified by hand to be present and 6.5 seconds inside the window - it simply had not been ingested at the moment of the single read. | `_read_lagging()` now returns all four delivered sources `(aegis, model, gateway, cloudtrail)` and is called on EVERY poll, and `_unsettled()` reports disagreements in **both** directions - invoked-not-audited and audited-not-invoked. The settle ends only when the two sides agree, and an expired deadline still fails. |
| L22 | Regression sweep knew only the Lambda-side view of a deliberate refusal | Attempt 6: a correct fail-closed run reported 17 "unexpected" errors. (a) A **Cedar DENY at the gateway** logs `Policy evaluation denied request` / `Tool Execution Denied` with `"decision":"DENY"`; the classifier matched only uppercase `DENIED`, so the platform's headline control read as an incident. (b) The gateway wraps a tool Lambda's refusal in a generic line ("An error occurred while executing tool: mask-pii___mask_pii from target X") that carries no reason - no content pattern can tell a kill-switch refusal from a genuinely broken tool. | (a) explicit Cedar-deny patterns. (b) **correlation, not a wider pattern**: a gateway tool-execution wrapper is expected only when that tool's own Lambda log carries an already-classified-EXPECTED refusal within 15s. Widening the pattern to match the wrapper text would have blinded the gate to real tool failures; a wrapper with no matching Lambda refusal stays UNEXPECTED. Offline-tested in both directions. |
| L22b-g | Six more ways a correct refusal looked like an incident | Beyond L22's Cedar-deny and gateway-wrapper cases: (b) runtime session teardown echoes a tool error back up to 300s later, outside any per-call window; (c) the echo signature was being read from the 260-character excerpt rather than the full message, so long lines lost their own evidence; (d) `ConditionalCheckFailedException` is the idempotency guard doing its job; (e) the Strands MCP client logs `Connection to the MCP server was closed` on normal shutdown; (f) P0-5 refuses in PROSE ("requester identity not verified"), matching no exception pattern; (g) genuine transient AWS faults (`ServiceUnavailableException`, `ThrottlingException`, `An internal error occurred. Please retry later`) are neither expected nor incidents. | (b) `_RUNTIME_ECHO_WINDOW_MS = 300000` with `correlate_runtime_echoes()`; (c) `row["_echo"]` computed at row-build time from the FULL message; (d)(e) added to `_RUNTIME_OPAQUE`; (f) an explicit prose pattern; (g) a WARN_ONLY class that is reported and counted but does not fail the sweep. Each correlation still requires a matching classified refusal - none of them widens the net by text alone. |
| L23 | Teardown blocked by an execution parked at the sign-off wait | Attempt 7 teardown: `ben-fp-workflow` sat in `DELETE_IN_PROGRESS` for 30 minutes on the Step Functions state machine. The PII-canary probe starts an execution that PARKS at the human sign-off wait **by design** and is never resumed, so it was still RUNNING when teardown began and CloudFormation waited on it. Any proof that leaves an execution at a wait state does the same - and the teardown-to-zero-residue claim depends on this completing. | `full_portfolio_gate.py` stops every RUNNING execution for the prefix before `cdk destroy`, and again between destroy rounds (an execution can park during the destroy itself). Verified live: the workflow stack deleted within seconds of the parked execution being stopped. The fix lands for the NEXT run - the in-flight attempt 7 had already loaded the old script and was unblocked by hand. |
| L24 | A hung CDK CLI read as a failed deployment | Attempt 5 stalled and was attributed to the device link dropping. That was **wrong**. The `cdk deploy` CLI can stop producing output and never exit while CloudFormation completes the deployment perfectly normally underneath it. The gate was trusting a subprocess exit code to describe the state of a distributed system. | `--deploy-timeout` (default 1800) bounds the CLI, and on a hang or a non-zero rc **CloudFormation decides**: if every expected stack is CREATE/UPDATE_COMPLETE the run continues with `steps["deploy_cli_hung"]` and the full stack-state map RECORDED in the evidence; if the stacks are not complete it still fails. The exit code was never the thing being claimed. The earlier device-link attribution is corrected here on the record. |
| L25 | The gate manufactured a false negative on 14 green checks | The lineage proof prints a JSON object; the gate checked its verdict by grepping stdout for the string `"0 orphan"`. The proof had never printed that string. So a run in which the lineage proof genuinely passed - and 14 other checks passed - was reported as a FAILED gate. A proof that succeeds and is then misread is worse than one that fails: it destroys trust in the passes too. | `_lineage_verdict(out)` parses the object with `json.JSONDecoder().raw_decode` (not `json.loads` - the proof prints a trailing "wrote coverage evidence" line) and asserts `covered is True and not orphans`, surfacing the counts in the check detail. Structured output is now read as structure, never as text. |
| L26 | A stray scheduled task tearing the environment down mid-run | Attempt 12's deploy "failed" in 2.4 seconds with completely empty stdout and stderr, and four stacks (`sp-a-data`, `sp-b-data`, `workflow`, `observability`) were reported ABSENT. Nothing in the run deletes stacks. CloudFormation said `ben-fp-workflow` was deleted at **04:01:39Z - ninety seconds BEFORE the run was launched**. The cause was a leftover Windows scheduled task, `AegisFpTeardown`, still registered from an earlier cycle and **still Running**: it had fired at 03:59Z and begun destroying the environment underneath the gate. | Task stopped, unregistered, and its python process killed; a clean from-zero cycle relaunched. Recorded because it is a HARNESS NONDETERMINISM finding, not a platform one, and because it bounds what can be trusted: any run overlapping 03:59-04:03Z is suspect. The earlier diagnoses do NOT rest on it - L21g, L22f/g, L24 and L25 were each verified against raw CloudWatch/CloudTrail/CloudFormation data at the time, and attempts 9-11 all completed before this task fired. The lesson is the same one L24 taught: when a step reports failure, check what the authoritative system says happened before believing the harness. |
| L27 | Two CDK CLIs sharing one cloud-assembly directory | Attempt 13's deploy exited 1 after **2.7 seconds** with `Other CLIs (PID=14484) are currently reading from cdk.out. Invoke the CLI in sequence, or use '--output' to synth into different directories.` All nine stacks read ABSENT and the gate correctly recorded "deploy failed" - a verdict about the local toolchain, not the platform. The preceding `--teardown-only` run had returned rc=0 and written its sentinel while a grandchild `cdk` process was still exiting and still holding the default `cdk.out`; the chained launcher started the deploy one second later. Fourteen checks never ran; the result is a NULL, not a red. | Every gate process now synths into its own `cdk/cdk.out-<pid>`, stale directories swept on startup and the run's own removed on exit (`.gitignore`d). Chosen over waiting for the lock, which would only be a guess about how long another process takes to die - separate directories remove the contention by construction, so two gate runs can overlap safely. Verified before relaunch: `cdk --output DIR ls` rc=0 enumerating all nine stacks. Same family as L23/L24/L26 - harness nondeterminism, recorded because a gate whose failures are not attributable is not evidence. |
| L28 | `subprocess.run`'s timeout is unenforceable when a grandchild holds the inherited pipes | Attempt 14 hung: `cdk deploy` parked on a dead HTTPS socket to CloudFormation after the fifth stack - 2.4 CPU-seconds over 2h20m, one ESTABLISHED connection that never returned, `ben-fp-compute` never submitted. The L24 `--deploy-timeout` **fired on schedule at 1800s and changed nothing**; the run stayed stuck for a further 110 minutes and ended only when the orphans were killed by hand. The mechanism was read off the live process tree, not guessed: `python 19192 -> cmd.exe 18340 (GONE - killed at the timeout)` while `node/npx 33888 (ALIVE, orphaned) -> cmd 42832 -> node cdk 9396 (ALIVE)` survived. `subprocess.run(capture_output=True, shell=True)` pipes stdout/stderr and on timeout kills only its DIRECT child, then re-enters `communicate()` to drain those pipes; the orphaned grandchildren still held the write handles so the drain never reached EOF. Killing 9396/42832/33888 unblocked python instantly and it exited rc=1 with the correct verdict already computed. **So L24's "the deploy is now bounded" was FALSE on Windows** - the bound existed in the argument list and nowhere in the behaviour, and had never been exercised because no deploy had previously hung past it. | `sh()` now (a) captures through FILES rather than pipes, so there is no drain to deadlock on and no 8KB pipe-buffer stall for a chatty CLI, and (b) kills the whole process TREE on timeout (`taskkill /T /F`, `killpg` elsewhere). It still raises `subprocess.TimeoutExpired`, so no call site changed. Pinned by `tests/test_sh_timeout.py` - three tests written against the shape that actually hung (a command whose grandchild outlives it holding the inherited handles): normal capture intact, `TimeoutExpired` raised at 8.2s against an 8s bound (previously: never), zero survivors. The general lesson is the sharpest of the campaign: **a bound you have never seen fire is not a bound.** |
| L28b | One recorded resume after a bounded hang | Attempt 14's hang was a transient dead socket, and `cdk deploy --all` is idempotent, so failing a 15-check gate on it wastes a full cycle. But a blanket retry would hide a genuinely broken deploy. | Exactly ONE resume, attempted only when the CLI hung or errored AND the stacks are still incomplete, and RECORDED as `deploy_resumed` plus a separate `deploy_2` step. Two attempts can never be read as one clean deploy, and a second hang still fails the gate. |
| L29 | Residue sweep raced DynamoDB's asynchronous `DeleteTable` | The teardown that cleared attempt 14 reported `clean=False`, listing two "residual" tables that the same run had deleted three lines earlier (`deleted table ben-fp-audit-ledger` is in its own stdout). `DeleteTable` is asynchronous: the table remains in `ListTables` with `TableStatus=DELETING` after the call returns, so re-listing immediately reports a false residue. Verified after the fact - both tables were gone with no further action, along with every stack and bucket. Same class as L25: a check misreading a genuinely good outcome, which is worse than one that fails, because it teaches you to distrust the passes. | The sweep waits out tables in `DELETING` (bounded, 180s) and reports anything else as genuine residue. |
| L30 | `DeleteAgentRuntime` is denied to the operator user, so teardown leaves the runtime behind | Recorded, NOT fixed. The 2026-09-07 teardown logged `AccessDeniedException ... DeleteAgentRuntime ... user/dryder is not authorized`. The AgentCore runtime therefore survives a "zero-residue" teardown, and the prefix residue sweep does not catch it because the runtime sits outside the prefix scan (its ECR repo already shows up under `toolkit_residue`). Two things are wrong: the permission, and a residue check whose scope does not cover everything the run creates. | Open. Needs the operator policy widened (or a dedicated teardown role) AND the residue sweep extended to AgentCore runtimes, so the zero-residue claim covers what the gate actually deploys. |
| L31 | A three-term Insights OR-chain returned zero rows while every disjunct matched alone | Attempt 15 reached 13/15 and failed `LIN_zero_orphans` on `invoked_not_audited:write_audit` after a full 906-second settle: 11 CloudTrail invokes, 10 audit lines, and the one missing was **`write_audit` - the evidence writer itself**, the single worst tool to appear unaudited. The line was never missing. It sits in `/aws/lambda/ben-fp-write-audit` at 11:02:37.666, inside the window, carrying the case_id, the run's trace_id AND its execution_arn, with a `request_id` matching the WORM ledger row - read out of the log stream by hand. Re-running the proof 80 minutes later against the still-standing environment reproduced the failure exactly, so this was not an ingestion race. Probing that one log group with the reader's own filter shape: `case` alone -> 1 row; `case or trace` -> 1; `case or exec` -> 1; `trace` alone -> 1; `exec` alone -> 1; **`case or trace or exec` (what the reader built) -> 0**, three runs running. Every disjunct matches, the union does not. So the proof got WEAKER the more correlation keys it had, and it failed SILENTLY. | The reader now asks the server only for the cheap invariant every audit line carries (`aegis` + `args_sha256`) and does correlation-key matching in Python, where it is deterministic and unit-testable - rather than hunting for the Insights query shape that happens to work today. Verified live against the failing case BEFORE committing: 10 rows -> 11, `write_audit` restored, 11 aegis calls against 11 CloudTrail invokes - exact parity, zero orphans. Pinned by `tests/test_trace_correlation.py` (5 tests), including the exact three-key shape that returned zero and a guard that client-side correlation has not quietly become "accept everything in the window". Third FALSE failure of the campaign (L25, L29, L31): the platform's audit coverage was complete the whole time, and a proof that cries wolf costs more than one that stays silent. |
| L32 | Background work launched through the MCP bridge was never actually detached | Gate attempt 16 passed 8 checks including G111 and then simply stopped at 12:51:55: the gate python AND its wrapper PowerShell both gone, no sentinel, no traceback, a log ending cleanly mid-step, and nine stacks left standing. Not a crash - an external kill of the whole tree, in the same minutes the bridge was dropping. `Start-Process` from the MCP shell inherits the MCP host's job object, so when the host dies every "detached" descendant dies with it. Attempts 13-15 survived bridge drops by luck, not design. **This also corrects something I told the user repeatedly across the day - that these runs were "detached and unaffected by the link". That was wrong, and stated with more confidence than it deserved.** | Long runs are now started with `Invoke-CimMethod Win32_Process Create`, whose parent is the WMI provider host: verified chain `WmiPrvSE.exe -> powershell -> python`, outside the MCP job object. Harness-nondeterminism finding, recorded because a gate whose runs can vanish is not evidence. |
| L33 | Insights silently drops rows for `like` filters - and L31 was only half the fix | Attempt 17 failed `LIN_zero_orphans` on `write_audit` AGAIN with the L31 fix already committed. L31 removed a three-term OR-chain after proving each disjunct matched alone; with the chain gone, the remaining two-term `@message like "aegis" and @message like "args_sha256"` filter ALSO returned nothing. Same log group, same window: filtered -> 0 rows; filtered +120s -> 0 rows; **unfiltered -> the line is right there at 13:46:51.712**; `filter_log_events` -> 11 rows including `write_audit`. So the window was never wrong and the audit line was never missing. I had declared L31 fixed on evidence that only showed one query shape working at one moment. | `read_lambda_calls` no longer uses the query engine at all: `filter_log_events` is a plain paginated scan and every predicate is applied in Python. Verified live against the failing case before committing - covered=true, 11 invokes vs 11 audit lines, orphans [], settle 0.0s (agreement on the FIRST poll, down from 906s). Tests assert the reader never calls `start_query`. |
| L33b | A swallowed throttle is a silent truncation | The L33 scan caught throttling with a bare `except Exception: break`. A rate limit therefore became a short read - and a short read of audit lines is indistinguishable from a governed tool that never audited itself. Attempt 18: the transparency proof reads that function over 21 log groups right after the heaviest part of the run, hit throttling, and reported `lambda_calls_logged: false` on BOTH tenants, turning **G111 red after it had passed in attempts 15, 16 and 17**. A regression I introduced, in code written to fix a proof. | Throttles retried with backoff; everything else RAISES. Failing loudly beats reporting a clean-looking absence - the same lesson as L25, L29, L31 and L33, this time in an hour-old change of my own. |
| L34 | The CloudTrail arm was exposed to the same L33 defect - and the first fix fabricated invokes | With the audit arm fixed, attempt 18's lineage failure moved to the other side: 11 audit lines against 10 invokes, `audited_not_invoked:assess_eligibility`. `read_cloudtrail_capture` builds its query from four `like` predicates, exactly what L33 proved unreliable. **The first fix made it worse**: re-reading the window unfiltered and merging on `(eventTime, eventName, fn, bkt)` took invokes from 10 to 21 and flipped seven tools, because CloudTrail's eventTime is second-granular (L21c) and distinct invokes legitimately share a second. Merging on a non-unique key does not deduplicate, it FABRICATES. That is L21e's lesson walked into a second time in one session; it was reverted and left OPEN rather than half-fixed. | Closed with `eventID` as the only identity - CloudTrail guarantees it unique per event, so a merge can neither invent an invoke nor collapse two real ones. The unfiltered re-read is reached ONLY when a tool would otherwise be reported audited-but-never-invoked (the expensive scan happens when the answer would otherwise be an accusation) and the recovery is recorded as `settle.cloudtrail_unfiltered_reread.recovered_events`, so a run that needed it can never read as one that did not. Developed against SYNTHETIC FIXTURES, not live AWS: `tests/test_cloudtrail_capture.py` pins the shapes that caused the damage - two distinct invokes in one second both kept, a repeated eventID counted once, a dropped row recovered, a recovery that never double-counts. The last three iterations of this proof each cost ~90 minutes and real spend to learn what a unit test teaches in milliseconds; the next live gate is the first EVIDENCE for this fix rather than the third iteration of it. |
| PAR-4 | **OPEN** - the proof harness is FORKED across packs, so a fix in one never reaches the others | Found while preparing REL-5, the first live gate on a second pack. Every pack carries its own copy of `scripts/trace_case.py`, and PV and EDU were three fixes behind: neither had L31, L33 or L33b, so both still contained the Insights silent-drop defect and the swallowed throttle that produced today's false failures. Running REL-5 as planned would have reproduced the benefits failures exactly and spent a ~90-minute live cycle rediscovering findings already in this register. It also QUALIFIES the parity claim: `PACK-PARITY` measures controls, not the proof code that verifies them, so '17/17 by parity' said nothing about whether the verifier worked. Worse, benefits alone has `full_portfolio_gate.py` and `lineage_proof.py` - the orchestrator and the lineage proof do not exist in the other packs at all, so 'portfolio gate' has always been a benefits-only harness. | Stopgap applied: L31/L33/L33b and `tests/test_trace_correlation.py` ported into PV and EDU (their suites pass, 275 and 276). That is a stopgap and is labelled one - copying a fix four ways is how the fork happened. The real answer is ONE shared proof library (a `governed_core.proofs` module versioned with the wheel, as PAR-3 already proposes for the runtime) with the packs supplying only prefix, tenants and tool names. Until that exists, every proof fix has to be applied four times and any pack can silently drift behind. |

Each of L1–L19 is closed with a test or an exact live assertion (L6 closed 2026-09-06; L14–L34 found by the full-portfolio gate on 2026-09-06/07 — attempts 2–18. Of the eighteen cycles run on 2026-09-07, THIRTEEN were derailed by the harness or the proof rather than by the platform, and five findings (L25, L29, L31, L33, L33b) were cases where the platform was right and the check was wrong. That ratio is itself a finding: the proof machinery needs the same scrutiny as the thing it proves; L23–L27 are harness-nondeterminism findings, not platform ones, and each is recorded with what it invalidated — and closed on benefits main; attempt 5 is the from-zero re-run of the closed tree). The gate itself (`scripts/tier1_regate.py`) is now the
pack's standing from-zero acceptance harness.


---

# 2026-09-06 — Fourth external review (commits: platform `02eb9f4`, governed-core `2c8466e`, Benefits `43fcbc3`, PV `2020cdd`, EDU `5a2a33d`, Housing `910b58f`)

Reviewer's verdict: a credible, sophisticated reference implementation and a viable supervised sandbox;
**not** a customer production platform, and **not** non-bypassable governance over every API call or
model use in an account. Recommendation table accepted as written (architecture demo: yes; workshop /
technical evaluation: yes; supervised synthetic sandbox: conditional; pilot on real or regulated data:
not yet; production: no; account-wide non-bypassable governance: no). **Every finding was checked against
the code before it was accepted**; where the reviewer was wrong or only partly right, that is recorded too.
Note the review predates the same-day work on `main` (L14–L19, PAR-1 steps 1–4); items already moved by
that work are marked.

## Validation, finding by finding

| # | Finding (reviewer) | Verified? | What the code actually shows | Status |
|---|---|---|---|---|
| R4-1 | **Account-wide model governance is bypassable** — the SCP is staged, not org-tested; a direct `Converse` succeeded and only alarmed; no Organizations Bedrock policy / account-level enforced guardrail | **Confirmed** | `org/scp-bedrock-runtime-perimeter.json` is a template (PERIM-1: no Organization in the dev account); the capture-trail bypass alarm is DETECTIVE by design and the Tier-1 evidence says so. Bedrock **Organizations policies (enforced guardrail)** are the right preventive control and are not implemented | **OPEN → PERIM-1b** (needs an Organization / test OU; owner: David — account structure) |
| R4-2 | **Runtime can bypass the gateway**: runtimes are not Gateway runtime targets; no `allowedWorkloadConfiguration` / `aws:SourceArn` restriction; "every model call flows through the gateway" is false | **Partly** | Correct that the runtime's OWN model calls are governed by IAM + the mandatory guardrail, not by the Gateway (the Gateway governs tool/retrieval calls); the platform README's sentence overclaims → corrected (R4-12). The runtime IS the designed direct entry for a JWT holder (`allowedClients`); restricting inbound to a Gateway target / SourceArn is a real hardening option, not yet evaluated live | **Claim fixed; hardening OPEN → RT-4** |
| R4-3 | **IAM requires *a* guardrail, not *the* guardrail** (`Null` condition); model/inference-profile ARNs too broad; no explicit deny | **Confirmed** | drafter + runtime roles: `{"Null": {"bedrock:GuardrailIdentifier": "false"}}`; resources `foundation-model/*` + `arn:aws:bedrock:<region>:<acct>:*` | **FIXED on benefits main 2026-09-06 (R4-3)**: `StringEquals bedrock:GuardrailIdentifier = <exact guardrail ARN>` (+ version) on the allow and an explicit `Deny` with `StringNotEquals`; resources scoped to the manifest model + inference profile. PV/EDU: PAR-1 step 5 |
| R4-4 | **No immutable release with all fixes**; branches ahead of tags; benefits' full gate not run on the exact tree | **Confirmed** | benefits `main` was 7 commits ahead of `v0.5.2-pilot-rc1` at review time (now more: L14–L19); the full-portfolio gate (attempts 2–4) found and fixed L14–L19; attempt 5 runs from zero on the fixed tree | **IN PROGRESS → REL-6**: on a green attempt 5, tag that exact commit `v0.6.0-pilot-rc1`; the evidence records the sha; siblings re-tag after PAR-1 step 5 |
| R4-5 | **Parity checker is weaker than its name**: five runtime hashes; runtime `requirements.txt` still pins governed-core **1.9.0** (root pins 1.10.1); Housing unpinned | **Confirmed — and worse than stated** | `lib/runtime/requirements.txt` in benefits/PV/EDU pins the **1.9.0** wheel (the runtime image's budget meter is one core behind the Lambdas); the L19 teardown guard existed in EDU's runtime copy since 2026-09-04 and never reached the benefits template — per-pack runtime copies drift both ways | **FIXED (pin) 2026-09-06**: runtime requirements pin 1.10.1 + CI test that runtime/root/lock agree. **OPEN → PAR-3**: one versioned runtime package (`governed_core.runtime`) consumed by every pack; packs carry manifest-only differences; image provenance asserted in the gate |
| R4-6 | **MMDSv2 not configured or proven** (`metadataConfiguration.requireMMDSV2`) | **Confirmed absent** | nothing in `_configure.sh` / `_launch.sh` / the CDK sets it; the gate never asserts it | **FIXED 2026-09-06**: the full-portfolio gate asserts `requireMMDSV2` on the deployed runtime (`get_agent_runtime`); `_launch.sh` sets it explicitly when the toolkit supports the flag — recorded as live evidence in attempt 5+ |
| R4-7 | **"Every API call in the account" is false** — management events + selected data events only; no SageMaker / self-hosted / Q / external APIs / every DynamoDB-S3 data event | **Confirmed (wording)** | `lineage_stack.py` docstring and START-HERE said "EVERY API call in the account"; the actual selectors are management-all + Bedrock/AgentCore/Lambda/S3 data events | **FIXED (wording) 2026-09-06**; coverage of non-Bedrock model surfaces stays PERIM-7 |
| R4-8 | Inbound JWT config incomplete (no audience/scope/claim requirements); runtime role grants `GetWorkloadAccessTokenForUserId` | **Confirmed** | `_configure.sh`: `discoveryUrl` + `allowedClients` only; role statement `GetAgentAccessToken` includes `…ForUserId` | **FIXED (deny) 2026-09-06**: explicit Deny on `GetWorkloadAccessTokenForUserId` + `InvokeAgentRuntimeForUser` (identity always from the verified JWT); audience/scope pinning **OPEN → RT-5** (Cognito access tokens carry `client_id`/`scope`, not `aud` — needs the authorizer's `allowedAudience` semantics checked live) |
| R4-9 | `requester` / `case_id` in request metadata are caller-controlled | **Confirmed (as correlation)** | they ARE labelled correlation keys in `requestMetadata`; tenancy comes from the verified JWT (`custom:tenant`) and the interceptor's signed binding — never from the payload | **FIXED (labelling) 2026-09-06**: `requester`→`caller_requester`, `case_id`→`caller_case_id` in runtime metadata; the verified `sub` is added as `subject`; docs say which fields are authoritative |
| R4-10 | Production durability (Object Lock COMPLIANCE) not live-tested | **Confirmed** | gates run `GOVERNANCE`, 1-day retention so they can tear down | **OPEN → EV-1**: one COMPLIANCE-mode deployment in a disposable account (a locked bucket cannot be deleted for the retention period) |
| R4-11 | Multi-account / Organizations governance is a design, not a deployment | **Confirmed** | PERIM-1/6 | **OPEN** (needs an Organization) |
| R4-12 | Marketing claims to correct: "every model call flows through the gateway", "every API call", "KMS-signed manifests", "agent reasoning spans", "independently re-verified" | **Confirmed, all five** | platform README §"one gateway"; benefits README/START-HERE; MATURITY bar 8 | **FIXED 2026-09-06** in WOGplatform README + MATURITY and the benefits docs (see R4-12 commit) |
| R4-13 | Security pipeline inconsistent (SAST / IaC scan / secrets / CodeQL / image scan / attestations); Checkov baseline debt | **Confirmed** | benefits/PV/EDU CI: pip-audit + SBOM + Checkov (baselined); no CodeQL / trivy / gitleaks; no image attestation | **OPEN → SEC-1** (one reusable workflow: CodeQL + gitleaks + Checkov hard-fail + trivy on the runtime image + SLSA provenance) + CHK-1 |
| R4-14 | Artifact signing inconsistent (benefits Ed25519; PV/EDU null; Housing none; KMS a reference path) | **Confirmed** | as stated | **OPEN → SIG-1**: sign PV/EDU/Housing manifests; KMS-asymmetric signer exercised in CI |
| R4-15 | No customer IdP / connector / concurrency / quota / DR / IR / pen-test evidence | **Confirmed** | as recorded (out_of_repo, PERIM-8, #173, #174) | **OPEN** (needs a design partner / external party) |

## Action plan — order of attack (2026-09-06 evening onward)

| ID | Item | Why this order | Status |
|---|---|---|---|
| REL-6 | Green attempt 7 → tag `v0.6.0-pilot-rc1` on that exact commit; evidence + teardown from the same sha | the reviewer's #4 and the honesty anchor for everything below | attempt 6 found L20/L21/L22 (all fixed); attempt 7 from zero next |
| R4-3 | Exact-guardrail IAM (allow `StringEquals` + explicit `Deny StringNotEquals`; scoped model/profile ARNs) — benefits, then PV/EDU | cheapest P0, pure IaC, CDK-testable | benefits DONE (pending gate re-run on the tagged tree) |
| R4-6 | MMDSv2 explicit + asserted in the gate | AWS hard requirement since 2026-06-30 | DONE (asserted from attempt 5) |
| R4-5 | Runtime pins 1.10.1 + agreement test | the image was one core behind | DONE; PAR-3 (single runtime package) next |
| R4-8/9 | JWT-path denies + honest correlation labels | small, closes two P1s | DONE |
| R4-7/12 | Claim corrections | honesty | DONE |
| PAR-1 step 5 | authoritative Cedar context resolver + the perimeter Cedar set + R4-3 for PV/EDU | parity 13/13 | next |
| PAR-3 | `governed_core.runtime` — one versioned runtime, packs consume it | R4-5 root cause | after PAR-1 |
| RT-4 | Gateway-only runtime invocation (Gateway runtime target / `aws:SourceArn`) evaluated live | R4-2 hardening | after PAR-3 |
| SEC-1 | reusable security workflow (bandit / detect-secrets / checkov / CodeQL / trivy, all blocking) in benefits + PV + EDU | R4-13 | **DONE 2026-09-06** |
| CHK-1 | Checkov burn-down: hardened the evidence-trail log bucket, Log4j WAF rule group, reviewed baselines committed | R4-14 | **DONE 2026-09-06** (baseline gate live; residual items are design positions, recorded) |
| SIG-1 | sign PV/EDU/Housing manifests; exercise the KMS signer | R4-14 | next |
| EV-1 | COMPLIANCE-mode live deployment in a disposable account | R4-10 | needs a throwaway account |
| PERIM-1b | Organizations Bedrock policy (enforced guardrail) + SCP tested in a real OU | R4-1 — the only path to "non-bypassable" | blocked on an Organization (David) |


## 2026-09-06 - SEC-1 / CHK-1 landed (fourth review R4-13, R4-14)

**SEC-1 - one security workflow, every pack, every gate blocking.** Before this the packs ran only
pip-audit + SBOM while the platform repo alone ran static analysis, secret detection and IaC
scanning, so a finding could land in a pack and never be seen. `.github/workflows/security.yml` now
runs the same five gates in benefits, PV and EDU, and none of them is report-only:

| Gate | Tool | Blocking on |
|---|---|---|
| static analysis | bandit 1.9.4 (`-ll -ii`, B101 skipped) | any medium+/medium+ finding - benefits scanned clean, so this starts at zero with no baseline |
| secret detection | detect-secrets 1.5.0 | any string not already in the reviewed `.secrets.baseline` |
| IaC | checkov 3.2.489 over the **synthesized** CloudFormation | any finding not in `.checkov.baseline` (checkov cannot see through CDK Python - the app must be synthesized first or the scan silently passes over an empty tree) |
| code scanning | CodeQL `security-extended` | its own findings |
| container | trivy on the runtime image built from `lib/runtime` | HIGH/CRITICAL, `ignore-unfixed` - pip-audit sees requirements.txt; only an image scan sees the base image's OS packages |

`.secrets.baseline` per pack was reviewed line by line, not accepted blind: 18/13/17 files, every
finding an env-var NAME, a URL, an example ARN (already redacted), a Docker digest pin, a test
fixture JWT, or the documented `ChangeMe-Approver1!` demo seed the manifest ships for the sandbox
profile (a pilot must change it; the CDK "no default passwords" assertion covers the deployed pool).

**CHK-1 first real finding - the evidence trail's own log bucket was unhardened.** The data-events
trail on the WORM vault (the control that proves nobody but the gateway touched the evidence) was
delivering into a CDK auto-created bucket that synthesized with **no properties at all**: no
block-public-access, no TLS enforcement, no versioning, no declared encryption
(CKV_AWS_53/54/55/56/21/35). It is now an explicitly declared bucket with the same shape as the rest
of the regulated-data estate, and the same locked/unlocked retention behaviour (RETAIN and never
auto-emptied under the production profile; destroy/auto-delete in sandbox, which is what the
portfolio gate's zero-residue teardown asserts). Also added `AWSManagedRulesKnownBadInputsRuleSet`
to the auth Web ACL (CKV_AWS_192 - the Common Rule Set alone does not inspect for a Log4j2 JNDI
lookup). Both are covered by new CDK assertions in all three packs.

Honest note on the checkov numbers: the 481 raw findings from the first sizing scan are inflated -
the same 3-4 stacks are synthesized once per deployment profile (demo/dev/mt/synth/val1-3), so the
distinct finding set is far smaller. The residual baseline is dominated by Lambda DLQ/concurrency/
in-VPC and log-group-KMS checks that are deliberate design positions, not debt; the CI gate fails
on anything NEW.
