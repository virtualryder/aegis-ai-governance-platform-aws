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
| PERIM-2 | **Bedrock + AgentCore data-event capture** in the account trail (advanced selectors; docstring corrected) | Detective | **FIXED** (IaC) | `test_capture_trail_selects_bedrock_and_agentcore_data_events`; `org/cloudtrail-advanced-event-selectors.json` pinned equal | Next `capture_all=1` gate: `lineage_proof` + an `ApplyGuardrail` call from a test role appears in the WORM capture |
| PERIM-3 | **Bypass alarm** `<prefix>-bedrock-perimeter-bypass` from the capture log (issuing-role allowlist + IAM-user/root) on the ops topic | Detective | **FIXED** (IaC) | `test_bedrock_perimeter_bypass_alarm_from_capture_trail` | Same gate: an operator-role `converse` → ALARM within 5 min; the drafter's own calls do not trip it |
| PERIM-4 | **Invocation-log store as regulated data**: CMK (log group + payload bucket, bedrock service granted the key), Object-Lock COMPLIANCE + versioned + RETAIN + no auto-empty under `-c model_log_lock_days>0`; **production gate requires it** | Data protection | **FIXED** (IaC + gate) | `test_invocation_log_store_is_regulated_data_under_production_settings`; `app.py` `_require_production_controls` | Next `model_logging=1` + `kms=customer-managed` gate: Bedrock delivers to the SSE-KMS bucket + CMK log group (the cross-service key grant is the risk to verify) |
| PERIM-5 | **In-VPC endpoint policy** on `bedrock-runtime` (drafter role pattern + `approved_bedrock_principals`) | Network | **FIXED** (IaC) | `test_bedrock_runtime_endpoint_policy_admits_only_the_governed_drafter` | Next `network_mode=private` gate (`network_waf_proof`): drafter still drafts through the endpoint |
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

