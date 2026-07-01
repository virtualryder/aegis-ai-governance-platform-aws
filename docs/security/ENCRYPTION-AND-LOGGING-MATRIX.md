# Encryption & Logging Matrix — Aegis Governed Agent Platform

> **Status & maturity (read first).** Encryption-at-rest, WORM, and append-only audit are
> **deployed and live-validated** (see [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md)
> Runs 1 and 6); retention *durations* and multi-account log archive are **customer-configured**
> per the records-retention and legal-hold schedule. Maturity labels (**DA/IO/IT/CC/P**) follow
> [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md). Sources for every AWS capability are in
> [`../../SOURCES.md`](../../SOURCES.md).

## 1. Encryption at rest

Every data class (CJI / FTI / PHI / EDU / public) uses a **separate KMS customer-managed key
(CMK)**; CJI and FTI additionally run in isolated accounts (multi-account isolation is documented,
not yet deployed — see residual risk RR-3 in [`THREAT-MODEL.md`](THREAT-MODEL.md)).

| Store | Mechanism | Key | Maturity |
|---|---|---|---|
| DynamoDB audit table (`aegis-audit-<class>-*`) | SSE-KMS + PITR | Per-class CMK | DA (Run 1) |
| DynamoDB approval ledger (`aegis-approvals-<class>-*`) | SSE-KMS + TTL | Per-class CMK | DA (Run 1, Run 5) |
| DynamoDB budget reservation table | SSE-KMS, atomic conditional write | Per-class CMK | DA (Run 8) |
| S3 evidence bucket (`aegis-worm-<class>-*`) | SSE-KMS + Object Lock + public access blocked | Per-class CMK | DA (Run 1, Run 6) |
| Bedrock Knowledge Base backing store | SSE-KMS | Per-class CMK | CC |
| CloudWatch Logs / model-invocation logs (S3) | SSE-KMS | Per-class CMK | CC |

KMS lifecycle (rotation, disable/rotate on compromise) is covered in
[`../ops/INCIDENT-RESPONSE.md`](../ops/INCIDENT-RESPONSE.md). KMS enforces a mandatory 7-30 day
`PendingDeletion` window on key deletion (observed in every teardown).

## 2. Encryption in transit

| Path | Mechanism | Maturity |
|---|---|---|
| Client -> edge | TLS terminated at CloudFront | CC |
| Edge -> API Gateway -> Lambda | TLS in-transit | DA |
| Gateway -> Bedrock (models + Guardrails) | AWS PrivateLink (VPC interface endpoints); traffic avoids the public internet | DA (Run 1 invocation path); CC (endpoint provisioning) |
| Gateway -> DynamoDB / S3 / KMS | TLS to AWS service endpoints (VPC endpoints where configured) | DA |
| Gateway -> connector (system of record) | TLS; scoped OBO/STS credential per call | DA (Run 9, DynamoDB SoR); CC (real SaaS TLS + creds) |

The model runs in the Bedrock regional service, not inside the customer VPC; PrivateLink governs
the API path, and data residency is governed by region choice plus customer controls (see
[`../02-REFERENCE-ARCHITECTURE.md`](../02-REFERENCE-ARCHITECTURE.md) §4).

## 3. Logging sources, data class, and retention

Retention is expressed as three profiles that mirror the WORM profiles proven in Run 6:
**demo** (no retention / short), **pilot** (GOVERNANCE mode, bypassable by an authorized
break-glass principal), **production** (COMPLIANCE mode, no deletion before expiry even by root,
plus legal hold and cross-account log archive).

| Source | What it captures | Data class handling | Integrity | Demo | Pilot | Production |
|---|---|---|---|---|---|---|
| CloudTrail | Control-plane API calls | Masked identifiers only; management + data events | Log file validation; log-archive account | 90 days | 1 year | 7 years, cross-account archive |
| Bedrock model-invocation logging | Request/response + token metrics (feeds usage ledger) | Prompts masked at boundary before model; PII filters on output | S3 SSE-KMS | 30 days | 1 year | Per records schedule |
| Gateway audit table (DynamoDB) | Every tool attempt (allow/deny/pending/error) + lineage | Sensitive fields masked; class tagged per record | Append-only (PutItem-only, Update/Delete explicitDeny), PITR | Retain | Retain | Retain + export to WORM |
| Reviewer/approval audit table | viewed/approved/denied/expired/replayed + reviewer id | Reviewer identity from verified claims only | Append-only + conditional write | Retain | Retain | Retain + WORM |
| Connector audit table | create/compensate lineage + idempotency key | Masked payload fields | Append-only | Retain | Retain | Retain + WORM |
| S3 WORM evidence | Approval + decision evidence objects | Keyed by data classification | Object Lock (none / GOVERNANCE / COMPLIANCE) | none | GOVERNANCE 1d+ | COMPLIANCE + legal hold |
| CloudWatch Logs (Lambda) | Operational logs, X-Ray traces | No unmasked sensitive fields | SSE-KMS | 14 days | 90 days | Per policy |
| GuardDuty / Security Hub / Config | Threat findings, posture, resource compliance | Metadata | Security account aggregation | On | On | On + Security Lake |

Retention durations shown for pilot and production are illustrative starting points; the customer
sets them to their actual records-retention and legal-hold schedule per regime (RACI item 9 in
[`../10-PRODUCTION-READINESS-RACI.md`](../10-PRODUCTION-READINESS-RACI.md)). Regulatory drivers per
source map through [`../../governance/controls/control_mappings.yaml`](../../governance/controls/control_mappings.yaml)
(`append-only-audit-worm`: AU-2/AU-9/AU-10/AU-11; `kms-cmk-dataclass-isolation`: SC-12/SC-13/SC-28;
`continuous-monitoring`: CA-7/SI-4/AU-6).

## 4. What is proven vs configured

- **Proven live (DA):** SSE-KMS on DynamoDB and S3, per-class CMK, Object Lock enablement and
  applied GOVERNANCE retention with deletion denied, append-only audit via IAM policy simulation,
  Guardrail PII filters, atomic budget reservation.
- **Customer-configured (CC):** retention durations, legal hold, cross-account log archive,
  CloudTrail data-event scope, PrivateLink endpoint provisioning, CloudWatch retention windows,
  Security Lake.
- **Planned (P):** multi-account data-class isolation; runtime Comprehend/Macie masking (currently
  the regex analog).
