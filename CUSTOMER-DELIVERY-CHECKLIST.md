# Customer Delivery Checklist

> The gate between "works in our account" and "handed to a customer." Every item is either
> **machine-enforced** (the delivery gate: `platform_core/prod/manifest_validator.delivery_check`,
> negative-tested in `platform_core/tests/test_delivery_check.py`) or **human-verified** with the
> evidence named. Run this per agent, per delivery — it is deliberately short.

## Machine-enforced (delivery gate fails the build)

| # | Check | Gate error |
|--:|---|---|
| 1 | **No placeholder credentials.** No string anywhere in the manifest contains a `ChangeMe` marker — all identities carry rotated, environment-injected secrets (`${VAR}` references pass; literals with markers fail). | `placeholder_credential` |
| 2 | **Production audit retention.** `audit.object_lock_mode: COMPLIANCE` and `retention_days` ≥ 30, set from the record-class table below — never the dev default (`GOVERNANCE` / 1 day). | `audit_retention` |
| 3 | **Signed manifest.** `signing.signature` present and non-empty; signed with `platform_core/prod/manifest_signing.py` (local RSA) or KMS asymmetric signing, and verifiable against the declared publisher key. | `unsigned_manifest` |

## Retention by record class (set `audit.retention_days` from this table)

| Record class (examples) | Mode | Retention | Basis |
|---|---|---|---|
| Demo / internal sandbox | GOVERNANCE | 1–30 d | Development only — never delivered |
| General business records | COMPLIANCE | 3 y (1095 d) | Customer records schedule |
| SLG benefits determinations / case records | COMPLIANCE | 5–7 y (1825–2555 d) | State records-retention schedules — confirm per state |
| EDU financial-aid records | COMPLIANCE | 5 y (1825 d) | Title IV program records guidance — confirm per institution |
| HCLS pharmacovigilance / GxP records | COMPLIANCE | ≥ 10 y (3650 d) | PV system master file / GxP retention — confirm per QA |
| Healthcare payer/provider (HIPAA) | COMPLIANCE | 6 y (2190 d) | HIPAA documentation retention |

*The table is the default posture; the customer's records counsel confirms the number. The point
is that retention is a **manifest parameter** — one line per agent — not an engineering change.*

## Human-verified (attach evidence to the release)

- [ ] **Suites green in a clean environment** — `PYTHONPATH=platform_core:. pytest demo platform_core/tests -q` plus the agent's own suite; record counts in `MATURITY.yaml`.
- [ ] **Kill Switch drill executed** in the target account (engage → canary denied → SoD disengage → audit shows all three events). See `docs/ops/KILL-SWITCH.md`.
- [ ] **Minimum Bar declarations present** — manifest carries `grounding`, `budget`, `evals`, `pack`, `signing` blocks (gates 4/5/8/9) and CI's static-scope diff passes (gate 1).
- [ ] **IAM/identity handoff** — Cognito pools or customer IdP federation configured; no shared credentials; reviewer/approver groups mapped to real people (SoD requires two humans).
- [ ] **NOT-CLAIMS reviewed with the customer** — the honesty boundary is part of the delivery, not an internal doc.
- [ ] **Operator handoff** — incident runbook walked through with the customer's on-call; Kill Switch engage/disengage roles assigned to two distinct identities in their IAM.

*Companion: `DEPLOY-EVERYTHING.md` (how to deploy) · `SA-DEPLOYMENT-RUNBOOK.md` (field runbook) ·
`docs/10-PRODUCTION-READINESS-RACI.md` (who owns what on day 2).*
