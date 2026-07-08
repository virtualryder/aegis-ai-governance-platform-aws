# Terraform & GovCloud status — Aegis platform

**Honest status.** CloudFormation is the **canonical, live-validated** IaC (the governance core and
golden pilots were deployed across ten runs — see
[`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md) and
[`../evidence/CLEAN-ACCOUNT-ACCEPTANCE.md`](../evidence/CLEAN-ACCOUNT-ACCEPTANCE.md)). The Terraform
module (`infra/terraform/modules/governance_core/`) is a **partition-aware reference of the governance
core**, with commercial and GovCloud root examples. It is **structurally validated (python-hcl2), not
`terraform apply`-validated.** "Parity" refers to the governance-core module, not the full golden-
pilot set.

## Coverage: Terraform module vs the CloudFormation governance core

The Terraform reproduces ~15 AWS resource *types*; it mirrors `governance-core.yaml` closely:

| Control / resource | CloudFormation | Terraform `governance_core` |
|---|---|---|
| KMS CMK + alias | ✅ | ✅ |
| DynamoDB audit (append-only) + approvals | ✅ | ✅ |
| S3 WORM (Object Lock + encryption + versioning + PAB) | ✅ | ✅ |
| Bedrock Guardrail | ✅ | ✅ |
| Cognito user pool + group | ✅ | ✅ |
| Gateway Lambda + IAM role/policy | ✅ | ✅ |
| CloudWatch log group | ✅ | ✅ |

Not in the Terraform module (CloudFormation golden-pilot-only): the AVP/Cedar policy store, the
reviewer service + API-Gateway JWT authorizer, the Run-10 MCP endpoint, the WORM evidence pilot, and
the connector saga — these are the separate golden-pilot templates, deliberately CFN-only.

## GovCloud posture

- `infra/terraform/environments/dev-govcloud/main.tf` is a **partition-aware root example** for
  `aws-us-gov` (FedRAMP High region, MFA-required identity), parameterized off the same module as the
  commercial root. It is a **design-time example — no `terraform apply` in GovCloud has been run.**
- Same service caveat as the verticals: AgentCore Gateway GovCloud availability was pending as of
  2026-05, so a GovCloud deployment uses the portable gateway path.

## What "done" would require (engagement-owned)

A live `terraform apply` of the governance-core module in a commercial account, then in GovCloud;
extending the module set to cover the golden-pilot templates if Terraform is to reach full parity with
CloudFormation. Until then CloudFormation is canonical; the Terraform module is a validated-by-
structure reference. Tracked in [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md).
