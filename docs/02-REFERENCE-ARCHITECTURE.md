# 02 — Reference Architecture (edge to data, on AWS)

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> Read alongside [`../SOURCES.md`](../SOURCES.md). Every AWS capability named here maps to a
> cited source. Controls are marked **[Impl]** = platform-implemented or **[Cfg]** =
> customer-configured under the AWS Shared Responsibility Model.

## 0. The one-line shape

```
Residents / staff / employees
  → CloudFront + AWS WAF (OWASP managed rules + rate limit) + AWS Shield        [edge]
  → API Gateway  ·  Amazon Cognito (federates the org IdP → short-lived JWT)     [identity]
  → Agent runtime (AgentCore Runtime, or Step Functions + Lambda) in a private subnet
  → MCP Authorization Gateway (AgentCore Gateway): re-validates JWT + role claim,
        deny-by-default policy, least-privilege intersection, scoped per-call token,
        token-budget check, human gate, append-only audit                       [control plane]
  → Amazon Bedrock (models) + Guardrails, reached over AWS PrivateLink           [reasoning]
        · Guardrails: PII filters + contextual grounding + automated reasoning
        · Governed RAG over a Bedrock Knowledge Base (retrieval is an audited read)
  → DynamoDB append-only audit · S3 Object Lock (WORM) · KMS CMK per data class  [data/evidence]
Cross-cutting: CloudTrail · GuardDuty · Security Hub · AWS Config · X-Ray
FinOps: application inference profiles + cost-allocation tags → Cost Explorer / CUR
Data-class isolation: CJI · FTI · PHI · EDU · public  (account/VPC/key separation)
```

## 1. Edge tier — CloudFront + WAF + Shield

**What it does.** Terminates TLS at the CDN edge, applies AWS WAF managed rule sets (OWASP Top 10,
known-bad inputs) and rate limiting, and absorbs L3/L4 DDoS with Shield. **[Impl]**

**Why it's there.** The first control a CISO asks about is the public attack surface. Putting WAF +
Shield in front of every agent means no agent ships its own bespoke edge security — it's inherited.

**Who cares & why.** *CISO:* documented, managed edge controls satisfy the perimeter section of a
security review. *Architect:* one edge pattern, not eight. *Regulator mapping:* NIST 800-53 SC-5,
SC-7; supports GovRAMP/FedRAMP boundary protection.

## 2. Identity tier — Cognito + federated IdP + API Gateway authorizer

**What it does.** Cognito federates the customer's existing IdP (Entra ID, Okta, PingFederate,
Login.gov) and issues a **short-lived JWT** carrying verified role claims; the API Gateway JWT
authorizer validates issuer/audience/expiry and an alg-confusion guard before any request reaches
an agent. **[Impl gateway logic / Cfg IdP integration]**

**Why it's there.** *Client-supplied roles are never trusted.* Identity is cryptographically
verified (RS256 over the IdP JWKS). This is the anchor for least-privilege.

**Who cares & why.** *CISO:* satisfies the MFA + identity-proofing demands of **CJIS v6.0** (MFA
mandatory for all CJI access, audited since 2025-10-01) and HIPAA access control. *Architect:* no
agent re-implements auth. NIST 800-53 IA-2, IA-5, AC-2.

## 3. Control plane — the MCP Authorization Gateway (this is the product)

**What it does.** Every model call, tool call, and retrieval an agent makes is brokered here. On
each call the gateway:

1. **Re-validates** the caller's JWT and role claim (defense in depth behind the API authorizer).
2. Evaluates the full authorization predicate — not just a grant∩entitlement intersection. A call is
   **ALLOWED iff** every clause holds:

   ```
   ALLOW iff:
     authenticated_user is valid
     AND agent grant permits the tool
     AND user entitlement permits the tool        # least-privilege as an intersection
     AND declared purpose is allowed              # purpose limitation
     AND data-class boundary is satisfied         # CJI/FTI/PHI/EDU/public isolation
     AND consent exists when required             # 42 CFR Pt 2 / COPPA / FERPA
     AND residency boundary is satisfied          # region / GovCloud vs commercial
     AND token/cost budget is available           # FinOps preflight
     AND a valid approval exists when required     # human gate for consequential actions
   ```

   The agent can never exceed the human it acts for, its declared purpose, its data class, its budget,
   or its human-authority boundary. **[Impl]**
3. Checks the **token budget** for the owning department/agent and rejects or throttles over-budget
   calls before they cost money (see [`05-FINOPS-…`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md)). **[Impl]**
4. For **consequential actions** (issue/adjudicate/release/award/transfer), refuses to execute and
   routes to a **human gate** — Step Functions `waitForTaskToken` or `interrupt_before`. The approval
   token is **bound** to the exact tool + arguments hash + purpose + requester + reviewer + expiry,
   single-use, separation-of-duties (approver ≠ requestor); the consumed token is recorded with a
   **DynamoDB conditional write** so a replay is rejected. **[Impl]**
5. Mints a **scoped, per-call token** for the downstream tool — never a long-lived credential. On AWS
   this is an **AgentCore Identity on-behalf-of (OBO) token exchange** / STS scoped credential so the
   agent acts *as the user* for that one call. **[Impl]**
6. Writes an **append-only audit** record (allow / deny / pending / error) with full lineage and
   masked sensitive fields. **[Impl]**

**On AWS this is AgentCore Gateway + Policy in AgentCore (Cedar).** AgentCore Gateway (GA 2025-10-13)
is a single secure endpoint connecting agents to **MCP servers** and APIs/Lambda-as-tools with **IAM
and OAuth** authorization. **Policy in Amazon Bedrock AgentCore** is the deterministic enforcement
layer that evaluates every agent-to-tool request against **Cedar** policies **outside the agent's
reasoning loop** — the same Cedar language behind **Amazon Verified Permissions**. The platform
compiles each agent manifest + tool contract into Cedar policies (default-deny), so authorization is
externalized and machine-analyzable, not hidden in agent code. The readable Python policy engine in
this repo is the **offline test analog**; production runs on AgentCore Policy / AVP so the real
enforcement path is what's tested.

**Why it's there.** *An AI agent that can touch a system of record is a governance, audit, and
least-privilege problem before it is a model problem.* Centralizing every system touch here is what
makes any agent — including third-party add-ons — safe to deploy.

**Who cares & why.** *CISO:* "Can the AI act on its own?" — No; consequential actions are withheld in
code and gated. *CIO:* build this once, inherit it forever. *Architect:* one broker, uniform policy.
NIST 800-53 AC-3, AC-6, AU-2, AU-10; NIST AI RMF **Manage**/**Human-AI Configuration**.

## 4. Reasoning tier — Model Gateway: Amazon Bedrock + Guardrails over PrivateLink

**What it does.** All Bedrock access is centralized in a **Model Gateway** so no agent calls a model
directly. The Model Gateway enforces: an **approved model-profile allowlist per agent**; **task-based
routing** (a small cheap model to classify/route, a stronger model only to draft); **prompt-version
pinning** (hash-pinned, drift-failing); **JSON-schema validation** of structured outputs;
**max_tokens** enforced by the budget manager; a **retry/fallback** model policy; and **model
invocation logging** to CloudWatch/S3 (which feeds the usage ledger for chargeback). Models are
reached over **AWS PrivateLink** so API traffic avoids the public internet. **Mandatory Guardrails**
apply on input *and* output: sensitive-information (PII) filters, denied topics, **contextual
grounding checks** (grounding + relevance scored 0–0.99 to filter hallucinations in RAG), and
**automated reasoning checks** (formal logic validating responses against defined policy).
**[Impl Model Gateway + Guardrail wiring / Cfg policy tuning]**

**Why it's there.** Inference stays in-account; the model never receives unmasked sensitive data;
and output that isn't grounded in retrieved source is blocked or flagged before a human ever sees it.
(Note: the model runs in the Bedrock regional service, not inside your VPC — data residency is
governed by region choice + your controls.)

**Who cares & why.** *CISO:* no PII egress, guardrails on every call. *CIO/CEO:* hallucination control
is a board-level trust question; contextual grounding + automated reasoning are the answer. *Regulator
mapping:* NIST AI RMF **Confabulation**, **Information Integrity**, **Data Privacy**; HIPAA minimum
necessary; FERPA disclosure limits.

## 5. Grounding — governed RAG over a Bedrock Knowledge Base

**What it does.** Retrieval is performed as an **audited read** through the gateway
(`kb.search_policy`) against a Bedrock Knowledge Base; retrieved passages become the grounding source
the contextual-grounding check scores the answer against. Security-trimmed so retrieval respects the
caller's entitlements. **[Impl]**

**Why it's there.** Grounding is the single biggest lever on hallucination and on auditability ("show
me the source for this answer"). Routing retrieval through the gateway means even reads are governed
and logged.

**Who cares & why.** *Architect:* one retrieval pattern. *CISO:* reads are entitlement-trimmed and
audited. *Regulator mapping:* FERPA/HIPAA need-to-know; NIST AI RMF Information Integrity.

## 6. Data & evidence tier — KMS, append-only audit, WORM, masking, isolation

**What it does.**
- **KMS customer-managed keys per data class** — separate CMKs for CJI / FTI / PHI / EDU / public. **[Impl/Cfg]**
- **Append-only audit (DynamoDB)** — PutItem-only IAM with explicit Update/Delete deny + conditional
  writes; every tool attempt recorded. **[Impl]**
- **WORM retention (S3 Object Lock)** — immutable evidence keyed to data classification + retention
  schedule. **[Impl/Cfg schedule]**
- **Masking that fails closed** — **Amazon Comprehend / Comprehend Medical** detect PII/PHI; **Amazon
  Macie** discovers and classifies sensitive data in S3; **S3 Object Lambda** redacts on read. If
  masking can't run, the boundary denies rather than leaks. **[Impl]**
- **Data-class isolation** — account/VPC/key separation per class (CJI and FTI in isolated accounts).

**Why it's there.** The audit trail is what survives a review board, a FOIA request, or an OIG audit.
WORM + append-only means it can't be quietly edited; masking means sensitive data never lands in a
prompt, a log, or the audit unmasked.

**Who cares & why.** *CISO:* "Will the audit hold up?" — append-only + WORM + fail-closed masking.
*Regulator mapping:* **IRS Pub 1075** (FTI isolation/masking/WORM), **CJIS v6.0**, **HIPAA** (PHI
masking, audit controls), **FERPA**, **PCI DSS** (card masking). NIST 800-53 AU-9, SC-12/13, MP-6.

## 7. FinOps tier — token budgets + per-department chargeback

**What it does.** Each agent/department reasons through a Bedrock **application inference profile**
tagged with cost-allocation tags (`dept`, `team`, `app`, `data_class`). Usage flows to **Cost
Explorer** and the **Cost and Usage Report**, giving accurate **showback/chargeback** — one
department's model usage is attributed and billed back to it, not spread arbitrarily. The gateway's
token-budget check enforces hard caps in real time before spend occurs. **[Impl]**

**Why it's there.** Uncontrolled token spend and the inability to charge it back is the #1 reason
finance kills AI programs. This makes spend visible, capped, and fair. Full design:
[`05-FINOPS-…`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md).

**Who cares & why.** *CFO:* per-department chargeback + hard caps. *CIO:* a fundable, defensible cost
model. *Architect:* tagging is declared in the agent manifest, not bolted on.

## 8. Observability & posture — CloudTrail, GuardDuty, Security Hub, Config, X-Ray

**What it does.** CloudTrail records the control plane; GuardDuty detects threats; Security Hub
aggregates findings against standards; AWS Config enforces/records resource compliance; X-Ray traces
agent execution end to end. **[Impl/Cfg]**

**Who cares & why.** *CISO:* continuous monitoring is now explicit in **CJIS v6.0**. *Architect:*
operational visibility for day-2. NIST 800-53 CA-7, SI-4, AU-6.

## 9. Control → regime mapping (summary)

| Control (platform) | GovRAMP/FedRAMP | CJIS v6.0 | IRS 1075 (FTI) | HIPAA/HITECH | 42 CFR Pt 2 | GxP/Part 11 | FERPA | COPPA | PCI | NIST AI RMF |
|---|---|---|---|---|---|---|---|---|---|---|
| Edge WAF/Shield | ✔ | ✔ | ✔ | ✔ |  |  |  |  | ✔ | — |
| Cryptographic identity + MFA | ✔ | ✔ (MFA) | ✔ | ✔ | ✔ |  | ✔ | ✔ |  | Human-AI Config |
| Deny-by-default gateway / least-priv intersection | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | Manage |
| Human gate (bound, single-use, SoD) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ (e-sig) | ✔ |  |  | Human-AI Config |
| In-account inference + Guardrails | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |  | Data Privacy |
| Contextual grounding + automated reasoning | — | — | — | ✔ |  | ✔ |  |  |  | Confabulation / Info Integrity |
| Append-only audit + WORM | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |  | ✔ | Measure |
| Masking (PII/PHI/FTI/CJI/card), fail-closed | ✔ | ✔ | ✔ | ✔ | ✔ | — | ✔ | ✔ (biometric) | ✔ | Data Privacy |
| KMS CMK + data-class isolation | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |  | ✔ | Info Security |
| Token budgets + chargeback | — | — | — | — |  |  |  |  |  | Value Chain |
| Continuous monitoring | ✔ | ✔ (new) | ✔ | ✔ |  | ✔ |  |  | ✔ | Manage |

Full, control-by-control machine-readable mapping:
[`../governance/controls/control_mappings.yaml`](../governance/controls/control_mappings.yaml) and
the per-regime narrative in [`03-COMPLIANCE-OVERLAY-PACKS.md`](03-COMPLIANCE-OVERLAY-PACKS.md).

## 10. Deployment topology

- **Multi-account landing zone (AWS Control Tower / Organizations).** A central **governance account**
  (registries, policy/Cedar, evidence ledger, FinOps) governs **isolated workload accounts per data
  class** — public/low-risk, PII/enterprise, PHI/HIPAA, CJI/CJIS, FTI/IRS-1075, EDU/FERPA — each its
  own VPC, KMS CMK, and WORM store. The control plane is central; the runtime/data planes are isolated
  by regulatory boundary. A shared security account holds CloudTrail, Security Hub, GuardDuty, Config,
  and Security Lake; a log-archive account holds immutable logs.
- **Standalone agent first.** One command stands up a complete isolated stack (own VPC, edge,
  Cognito, KMS, WORM audit, gateway, agent) with no platform dependency. Grow agent by agent.
- **Whole-of-Government / Enterprise orchestration when ready.** A coordination layer (durable saga
  with compensation, consent ledger, compliance event bus) composes governed agents across
  departments. The same agents become saga steps unchanged.
- **Regions.** Commercial (US Moderate) and **AWS GovCloud (US)** for High-impact / CJI / FTI; deploy
  CloudFront-scoped WAF in `us-east-1`. IaC parity across CloudFormation + Terraform.

## 11. What we deliberately do **not** claim

Not yet AWS-authorized, not ATO/GovRAMP/FedRAMP-certified, no live connectors, no third-party
security testing. "HIPAA-eligible" services ≠ a HIPAA-compliant deployment; that requires a BAA and
customer-implemented controls. See [`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
