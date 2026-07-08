# Aegis — Canonical Infrastructure-as-Code

**CloudFormation is the canonical IaC language for Aegis.** Every deployable
control-plane resource ships as a CloudFormation template under
`infra/cloudformation/` (the platform baseline) or `infra/golden-pilot/` (the
end-to-end golden-pilot slices). CI (`.github/workflows/ci.yml`, `iac` job)
lints **both** directories with `cfn-lint` on every push and pull request.

Terraform parity is deliberately **out of scope for now and tracked as P2**
(see task #27). We do not maintain two source-of-truth IaC dialects: adopters
who standardize on Terraform can wrap these templates
(`aws_cloudformation_stack`) or port them, but CloudFormation remains the
authoritative, live-validated definition.

## Live-validation status

Every template below has been deployed to a real AWS account and torn down
cleanly. Evidence is recorded in `DEPLOYED-AND-VALIDATED.md` (Runs 1–7,
account `<VALIDATION-ACCOUNT-ID>` — real account ID redacted; evidence available
on request — region `us-east-1`). This document only cross-references
those runs; it does not restate the evidence.

### `infra/cloudformation/` — platform baseline

| Template | Purpose | Live-validation |
| --- | --- | --- |
| `governance-core.yaml` | Governance core: security + data + gateway tiers (KMS CMK, append-only audit table, guardrails, budget/usage plumbing) — the minimal deployable subset of `STACKS.md`. | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 1** (governance-core) |
| `sample-agent.yaml` | Low-blast-radius sample agent: a Standard Step Functions state machine (Classify → Retrieve → Draft → Check → HumanGate via `waitForTaskToken`) wired to the governance core. | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 2** (sample-agent + human gate) |

### `infra/golden-pilot/` — end-to-end golden-pilot slices

| Template | Purpose | Live-validation |
| --- | --- | --- |
| `avp-cedar.yaml` | Real Cedar authorization on Amazon Verified Permissions: STRICT-validated policy store, schema (Agent principal / Tool resource / InvokeTool action) and the least-privilege intersection permit. Production analog of `platform_core/policy_engine.py` and the target of `platform_core/prod/cedar_compiler.py`. | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 3** (avp-cedar) |
| `cognito-identity.yaml` | Real identity: hardened Amazon Cognito user pool with software-token MFA required, advanced security, an app client, and verified-role claims feeding Cedar. | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 4** (cognito-identity) |
| `reviewer-service.yaml` | Real human-approval reviewer service: pending/ledger/audit tables + a gate-opener Lambda enforcing verified-supervisor role, separation-of-duties, single-use, bound, expiring approvals. | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 5** (reviewer-service) |
| `evidence-worm.yaml` | Immutable evidence: S3 bucket with Object Lock and a DEFAULT retention rule so every evidence object is written WORM (S3 Object Lock analog of `audit_ledger.export_worm`). | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 6** (evidence-worm) |
| `reviewer-api.yaml` | Reviewer front door: API Gateway HTTP API + Cognito JWT authorizer in front of the reviewer Lambda; the authorizer verifies the supervisor JWT before any approval action. | Deployed & torn down — DEPLOYED-AND-VALIDATED.md **Run 7** (reviewer-api) |

## Linting locally

```bash
pip install cfn-lint
cfn-lint infra/cloudformation/*.yaml infra/golden-pilot/*.yaml
```

A clean exit (no findings) is the CI gate for the `iac` job.
