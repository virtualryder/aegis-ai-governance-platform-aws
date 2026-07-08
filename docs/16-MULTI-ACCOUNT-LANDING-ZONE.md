# Multi-account landing zone — deploying Aegis at scale

**What this is.** A reference design for deploying the Aegis governed-agent platform across **multiple
AWS accounts** using AWS Organizations / Control Tower, so a customer can separate data classes,
environments, and blast radius the way regulated enterprises and governments require. It complements
[`11-MULTI-TENANCY.md`](11-MULTI-TENANCY.md) (SILO/POOL/BRIDGE tenant isolation *within* a deployment)
— this doc is about the **account topology around** it. It is a design reference, not a deployed
landing zone; a real landing zone is customer/engagement work.

## Why multi-account (not one big account)

A single account can't cleanly give a CISO or auditor what they need: hard data-class isolation, a
blast-radius boundary, separate audit custody, and environment separation. AWS's own guidance is to
use an account as the unit of isolation. For a governed-agent platform the natural cuts are **by
environment, by data class, and by governance function.**

## Reference organizational-unit (OU) structure

```
Root (AWS Organizations)
├── Security OU
│   ├── Log Archive account         — centralized CloudTrail + the WORM audit archive (Object Lock)
│   └── Audit/Security Tooling acct  — GuardDuty, Security Hub, Config aggregator, IAM Access Analyzer
├── Infrastructure OU
│   ├── Network account              — Transit Gateway, shared VPC endpoints (Bedrock PrivateLink), DNS
│   └── Shared Services account      — CI/CD, artifact/registry, the reviewer service (if shared)
├── Governance-Platform OU
│   ├── Aegis-Platform-Prod          — the governance control plane (gateway, policy store, budgets)
│   └── Aegis-Platform-NonProd       — dev/test of the control plane
└── Workload OU  (one account per data class × environment)
    ├── Public / low-sensitivity     — 311, permitting  (prod + nonprod)
    ├── FTI (IRS 1075)               — benefits/tax      (prod + nonprod)
    ├── CJI (CJIS)                   — public safety     (prod + nonprod)
    └── PHI (HIPAA/BAA)              — health workflows  (prod + nonprod)
```

The **data-class-per-account** cut is what makes the SLG regime-overlay separation
([regime overlays](../../slg-ai-agents/docs/REGIME-OVERLAY-SEPARATION.md)) enforceable at the account
boundary, not just in policy: CJIS controls live in the CJI account; 1075 controls in the FTI account;
a 311 agent never runs where CJI lives.

## How the platform maps onto it

| Platform element | Account | Notes |
|---|---|---|
| Governance control plane (gateway, AVP/Cedar policy store, token budgets) | Governance-Platform-Prod | One paved road; agents in workload accounts call it |
| Agents + their systems-of-record connectors | Workload account (by data class) | Blast radius contained to that data class |
| Append-only audit + WORM archive | Log Archive account | Cross-account log delivery; audit custody separated from operators (SoD at the account level) |
| Identity / IdP federation | Shared/Identity | Cognito + customer IdP; short-lived cross-account roles |
| Bedrock + Guardrails via PrivateLink | Network + workload | Interface endpoints centralized or per-account; traffic stays on AWS private networking |
| Security tooling (GuardDuty/Config/Security Hub) | Audit/Security account | Org-wide, delegated administrator |

## Guardrails at the org level

- **Service Control Policies (SCPs):** deny disabling CloudTrail/Config, deny public S3, restrict
  Regions (e.g., only the customer's chosen Region / GovCloud), deny use of non-approved services.
- **Delegated administration** for Security Hub / GuardDuty / IAM Access Analyzer to the audit account.
- **Centralized CloudTrail (organization trail)** → Log Archive account WORM bucket; operators in
  workload accounts cannot alter the audit custody account (separation of duties at the account level).
- **Cross-account roles** are short-lived and scoped; the gateway's least-privilege-intersection model
  extends across the account boundary.

## GovCloud note

For public-sector customers the same topology deploys in the **AWS GovCloud (US) partition**
(`aws-us-gov`), with the portable gateway path (AgentCore Gateway GovCloud availability was pending as
of 2026-05). Commercial and GovCloud are separate Organizations; the landing-zone structure is
mirrored.

## What "done" would require (engagement-owned)

Stand up Control Tower (or a Landing Zone Accelerator), create the OUs/accounts, apply the SCPs, wire
centralized logging to the Log Archive WORM bucket, deploy the control plane to the Governance-Platform
account and agents to the workload accounts, and validate cross-account audit delivery. This repo
provides the single-account golden paths and this topology reference; the multi-account landing zone
itself is a customer deployment. See [`12-COMMERCIAL-PACKAGING.md`](12-COMMERCIAL-PACKAGING.md) and
[`11-MULTI-TENANCY.md`](11-MULTI-TENANCY.md).
