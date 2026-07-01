# 12 — Commercial Packaging

> **Status & maturity (read first).** This document is **Designed**. It defines the offer,
> editions, and pricing *models* — not committed price points. **All currency figures below
> are illustrative placeholders to be set commercially**; they exist to show the shape of
> the model, not to quote a customer. The underlying platform maturity is tracked in
> [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md); the readiness scorecard there rates
> commercial packaging as "good narrative, missing offer/pricing/support" — this document
> closes the *structure* of that gap. It builds on the add-on model in
> [`08-GTM-AND-POSITIONING.md`](08-GTM-AND-POSITIONING.md) §8.

## 1. What is sold

Aegis is sold in three composable layers. The moat is the governance layer; agents are the
recurring, expandable revenue.

| Layer | What it is | Commercial motion |
|---|---|---|
| **Platform core** | The governed paved road: identity, authorization, audit, WORM evidence, guardrails, human gate, chargeback — deployed per environment in the customer's account | Per-environment license/subscription |
| **Compliance packs** | Overlay packs that map the core to a regime (enterprise, slg-core, healthcare, education, justice) — see [`03-COMPLIANCE-OVERLAY-PACKS.md`](03-COMPLIANCE-OVERLAY-PACKS.md) | Attach to the core; per pack |
| **Add-on agents** | Packaged, manifest-conformant agents that inherit the customer's governance on deploy | Per agent, priced per-agent / per-seat / usage-based |

## 2. Editions

| Edition | Includes | Intended buyer |
|---|---|---|
| **Aegis Platform — Standard** | Platform core + one compliance pack, one environment, commercial partition | A first regulated workload / single department |
| **Aegis Platform — Enterprise** | Platform core + multiple packs, multi-environment, multi-tenant (POOL/BRIDGE), GovCloud option | An organization standardizing many agents on one governed plane |
| **Aegis Platform — Government (GovCloud)** | Enterprise scope deployed in `aws-us-gov`, FedRAMP-High region, MFA-required identity, per the Terraform/GovCloud parity module | Public-sector / regulated buyers requiring GovCloud |

Editions differ by **scope** (packs, environments, tenancy model, partition), not by
withholding a security control — every edition ships the full governance boundary. That is
a deliberate trust decision: we do not sell "the audit trail" or "the human gate" as an
upsell.

## 3. Add-on agent pricing models

Each add-on agent picks one primary model; chargeback keeps all three transparent.

| Model | How it bills | Fits | Transparency mechanism |
|---|---|---|---|
| **Per-agent** | Flat recurring fee per deployed agent | Steady, always-on agents (service desk, intake) | Chargeback report shows the agent's tagged spend vs its fee |
| **Per-seat** | Per authorized human user/reviewer | Human-in-the-loop workflows with a defined user population | Cognito group membership → seat count |
| **Usage-based** | Per governed action / per token band | Spiky or high-volume decision-support | Bedrock application inference profile tags → Cost Explorer / CUR |

**Chargeback transparency is the differentiator.** Because 100% of model spend is tagged at
the source (see [`05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md)),
the customer can always reconcile what they are billed against what an agent actually
consumed, per department and (in multi-tenant deployments) per tenant. Illustrative only:
a per-agent fee of *~$X/agent/month* plus pass-through AWS consumption, or a usage tier at
*~$Y per 1M governed tokens* — **numbers to be set commercially.**

## 4. Support tiers

| Tier | Response targets (illustrative) | Scope |
|---|---|---|
| **Standard** | Business-hours support, next-business-day for standard issues | Break/fix, upgrade guidance, documentation access |
| **Premium** | 24×7 for severity-1, defined response SLOs, named contact | Standard plus priority incidents, upgrade assistance, architecture office-hours |

Response-time SLOs are **placeholders to be set commercially**; the tier *structure* is the
deliverable here.

## 5. Managed-operations boundary

Aegis can be delivered self-operated or with managed operations. The boundary must be
explicit so it survives a security review and the shared-responsibility model
([`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md)).

| Responsibility | Self-operated | Managed operations (optional add-on) |
|---|---|---|
| AWS account & org | Customer | Customer (vendor operates within customer accounts under least-privilege, auditable roles) |
| Platform deploy/upgrade | Customer | Vendor |
| Day-2 monitoring / incident response | Customer | Vendor (to the agreed boundary) |
| Data ownership & custody | **Customer, always** | **Customer, always** |
| Audit/evidence access | Customer | Customer (vendor never exclusively holds) |

The hard line: **the customer always owns the account, the data, the keys, and the audit
trail.** Managed operations means the vendor operates the platform *within* the customer's
boundary under auditable, least-privilege access — never that the vendor holds the
customer's data or evidence.

## 6. AWS Marketplace delivery motion

- **Platform + packs** list as a Marketplace offering (private offer for negotiated
  enterprise/government terms), deploying into the customer's own account.
- **Add-on agents** are Marketplace products that deploy onto the already-governed platform
  — the ISV/partner flywheel from [`08-GTM-AND-POSITIONING.md`](08-GTM-AND-POSITIONING.md):
  every governed customer is an addressable market for every new agent, with zero
  governance rework on the customer's side.
- Marketplace billing consolidates onto the customer's AWS bill and can draw down AWS
  committed spend (EDP), which is often the fastest procurement path in regulated buyers.
- GovCloud offers list against GovCloud accounts; confirm Marketplace + service
  availability in-partition (see the Terraform GovCloud notes).

## 7. Versioning, upgrade & rollback entitlements

- **Semantic versioning** for the platform core, packs, and each add-on agent
  (`MAJOR.MINOR.PATCH`). MAJOR = breaking control/interface change; MINOR = additive;
  PATCH = fix. Manifest schema and Cedar policy versions are tracked with the release.
- **Upgrade entitlement** by tier: Standard receives PATCH/MINOR within the licensed MAJOR
  line; Enterprise/Government add supported MAJOR-upgrade assistance and a longer support
  window per version.
- **Rollback entitlement.** Because the platform ships as versioned IaC (CloudFormation
  canonical; Terraform parity module), a customer can roll back to the prior released
  version. WORM evidence is immutable by design and is never rolled back — a rollback
  changes the control plane, not the historical audit record.
- **Deprecation policy:** advance notice before a MAJOR line goes end-of-support, with a
  documented migration path.

## 8. IP ownership: customer-owned vs vendor-owned

| Artifact | Owner | Notes |
|---|---|---|
| Customer data, prompts, outputs, audit/evidence | **Customer** | Stays in the customer's account and keys |
| Deployed IaC in the customer's account | **Customer** (licensed) | Readable, AWS-native; customer can inspect and operate it |
| Platform core, packs, agent source & manifests | **Vendor** (licensed to customer) | The licensed product |
| Customer-authored agents/manifests on the platform | **Customer** | Built to the onboarding standard; the customer's IP |

## 9. Positioning: "customer-owned," not "no lock-in"

The honest reframe (replacing the loose "no lock-in" line): **Aegis is a customer-owned,
readable, AWS-native implementation with no proprietary Aegis runtime dependency.**

- Everything Aegis deploys runs in the **customer's own AWS account** on **AWS GA services**
  (Bedrock, Cognito, DynamoDB, S3 Object Lock, KMS, IAM, Lambda, Step Functions).
- The control plane is **readable IaC** the customer owns and can operate — there is no
  hidden Aegis runtime the workload calls out to, and no black-box service in the request
  path that the customer cannot see or replace.
- If the commercial relationship ends, the customer keeps a functioning, AWS-native
  governance stack in their account and full custody of their data and evidence.

This is a stronger and more defensible claim than "no lock-in," because it is specific and
verifiable in a security review: the customer can point to every resource, in their own
account, built from IaC they hold.

---

*All pricing, SLO, and entitlement-window figures in this document are illustrative
placeholders to be set commercially.*
