# Control mappings — CJIS v6.0 · IRS Pub 1075 · 42 CFR Part 2 · GxP/21 CFR Part 11 · FERPA

*Human-readable companion to the machine-readable `control_mappings.yaml`. This is an **engineering
description** of how the platform's controls address each regime's control families — **not** a
certification, attestation, or legal determination. `NOT-CLAIMS.md` governs. Authorizations attach to
the underlying **AWS services** under the shared-responsibility model, not to this accelerator.*

## Why this exists

AWS will not write your CJIS / IRS-1075 / 42-CFR-Part-2 / GxP / FERPA control narrative — that mapping
is the customer-facing differentiator. AgentCore gives you the managed control *plane*; this document
shows which regime control families each AGP control (on AgentCore + Aegis) speaks to.

## Enforcement split (who provides each control)

| AGP control | AgentCore component | Aegis adds (what AgentCore does not do) |
|---|---|---|
| Identity | Identity + Gateway CUSTOM_JWT | verified-claim-only identity |
| Deny-by-default gateway | Gateway + Cedar Policy **ENFORCE** | least-privilege intersection; parity oracle |
| **Human gate (single-use SoD)** | — (Cedar can't express it) | **bound single-use SoD approval; commit routed to human gate** |
| **Fail-closed masking** | Guardrails (input filter) | **mask-before-audit-and-model; deny on masker failure** |
| **WORM audit (tamper-evident)** | Observability = telemetry only | **hash-chained ledger + S3 Object Lock; IAM-denied mutate** |
| Token budgets | ~ Payments (spend limits) | atomic per-agent hard cap |
| Model gateway + grounding | Bedrock + Guardrails; Runtime | guardrail-pinned drafting; grounding checks |
| Observability / transparency | OTEL spans + Bedrock invocation logs | correlated OTEL + invocation-log + WORM evidence |

## Regime highlights

**CJIS Security Policy v6.0** — MFA is mandatory for CJI access (audited since 2025-10-01): met by
AgentCore Identity + Gateway CUSTOM_JWT. Deny-by-default access to CJI with scoped tokens: Cedar Policy
in ENFORCE. Separation of duties on CJI actions: the Aegis single-use human gate. Tamper-evident audit
of who touched CJI: the WORM ledger. No CJI egress to a public model: in-account Bedrock + Guardrails.

**IRS Publication 1075 (FTI)** — need-to-know / least privilege for FTI: Cedar default-deny + intersection.
Authorized human decision on FTI-affecting actions: the SoD gate. No FTI egress to a public model surface:
in-account inference. Immutable audit of FTI access: WORM ledger + AgentCore Observability. Data masking of
FTI before logging/model: fail-closed masker.

**42 CFR Part 2 (SUD records)** — strict access limitation and authenticated access: Identity + Cedar.
Human authorization on disclosure/redisclosure: the SoD gate. No SUD-record egress to a public model:
in-account inference. Masking before any log/model boundary: fail-closed masker.

**GxP / 21 CFR Part 11** — electronic-signature-grade, attributable, non-repudiable approvals: the bound
single-use SoD approval, recorded in the WORM ledger. Authority checks limiting system access: Cedar.
Controlled, in-account processing of regulated activity: Bedrock over PrivateLink + Guardrails.

**FERPA** — need-to-know / school-official-exception access: Identity + Cedar. Human authorization on
disclosure of education records: the SoD gate. No education-record egress to a general-purpose model:
in-account inference. Auditable access trail: WORM ledger.

*Every regime claim above is backed by a citation in `SOURCES.md`; the per-control matrix is in
`control_mappings.yaml` (NIST 800-53 Rev.5 + NIST AI RMF ids per control).*
