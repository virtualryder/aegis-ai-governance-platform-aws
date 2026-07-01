# Aegis — Terraform parity module (`governance_core`)

CloudFormation is the **canonical, live-validated** IaC for Aegis (see
[`../CANONICAL-IAC.md`](../CANONICAL-IAC.md)). This Terraform module is the **P2
parity deliverable**: a resource-for-resource port of
[`../cloudformation/governance-core.yaml`](../cloudformation/governance-core.yaml)
for adopters who standardize on Terraform, with partition awareness so it deploys
in both the commercial (`aws`) and GovCloud (`aws-us-gov`) partitions.

## Maturity — read first

- The **CloudFormation governance core was deployed to a real AWS account and torn
  down cleanly** (DEPLOYED-AND-VALIDATED.md **Run 1**, account `864217980669`,
  region `us-east-1`). It is the authoritative definition.
- This **Terraform module is validated structurally** here — every `.tf` parses and
  the resource graph mirrors the proven stack. A live `terraform apply` is a
  **customer step** in the customer's own account; it is not part of this
  deliverable. Nothing in this directory claims a Terraform live-deploy that has
  not happened.

## Layout

```
infra/terraform/
  modules/governance_core/     # the reusable module (parity target)
    versions.tf                # required_providers aws ~> 5.60, terraform >= 1.5
    variables.tf               # one-for-one with the CFN Parameters
    main.tf                    # resources + partition-aware data sources + tags
    outputs.tf                 # mirrors the CFN Outputs
    index.py                   # fail-closed gateway handler (packaged via archive_file)
  environments/
    dev-commercial/main.tf     # aws partition, us-east-1, pack=enterprise data_class=pii
    dev-govcloud/main.tf       # aws-us-gov partition, us-gov-west-1, GovCloud notes inline
```

## Usage

```bash
# Commercial
cd infra/terraform/environments/dev-commercial
terraform init
terraform plan
terraform apply     # customer step, in the customer's account

# GovCloud (requires a GovCloud account + GovCloud credentials)
cd infra/terraform/environments/dev-govcloud
terraform init
terraform plan
terraform apply
```

Structural validation without cloud credentials or the Terraform binary:

```bash
pip install python-hcl2 --break-system-packages
python3 -c "import hcl2,glob; [hcl2.load(open(f)) for f in glob.glob('infra/terraform/**/*.tf',recursive=True)]"
```

## Partition / GovCloud notes

The module resolves the partition, region, and account at plan time via
`aws_partition`, `aws_region`, and `aws_caller_identity` data sources and builds
**every ARN from those values**. Consequences:

- The CMK key policy, the scoped Bedrock foundation-model ARN, and the guardrail
  ARN all resolve as `arn:aws-us-gov:...` automatically in GovCloud — no module
  edits. Never hardcode `arn:aws:...`.
- **No cross-partition ARNs.** A GovCloud deployment references only GovCloud
  resources; a commercial deployment references only commercial resources.
- `us-gov-west-1` is a **FedRAMP High** region. Keep data, keys, and logs
  in-partition/in-region for residency.
- **Confirm Bedrock + Guardrail + your foundation model are available in your
  GovCloud region before apply** — GovCloud Bedrock/model coverage lags commercial
  and changes over time. Set `bedrock_model_id` to a model actually enabled
  in-partition.
- For regulated GovCloud workloads, require MFA on the Cognito pool (the module
  ships `mfa_configuration = "OFF"` for a clean demo teardown, matching the CFN
  core; CJIS v6.0 mandates MFA).

## CloudFormation ↔ Terraform parity table

Every governance-core resource is reproduced. The Terraform module is a faithful
port of the live-proven CloudFormation stack.

| Governance control | `governance-core.yaml` (CFN) | `governance_core` (Terraform) | Parity notes |
|---|---|---|---|
| CMK per data class (+ rotation) | `AWS::KMS::Key` | `aws_kms_key.data_class` | Rotation on; key policy partition-aware via `aws_partition` |
| CMK alias | `AWS::KMS::Alias` | `aws_kms_alias.data_class` | `alias/${app}-${data_class}-${env}` |
| Append-only audit table | `AWS::DynamoDB::Table AuditTable` | `aws_dynamodb_table.audit` | PAY_PER_REQUEST, KMS SSE, PITR, hash `request_id` + range `seq` |
| Approval ledger | `AWS::DynamoDB::Table ApprovalLedger` | `aws_dynamodb_table.approvals` | hash `approval_id`, TTL `expires_at`, KMS SSE |
| WORM evidence bucket | `AWS::S3::Bucket` | `aws_s3_bucket.worm_evidence` + `_versioning` + `_object_lock_configuration` + `_server_side_encryption_configuration` + `_public_access_block` | Object Lock **enabled, NO default retention** (clean teardown); versioning on; KMS default encryption; all public access blocked |
| Bedrock Guardrail | `AWS::Bedrock::Guardrail` | `aws_bedrock_guardrail.aegis` | PII (EMAIL/PHONE anonymize, SSN block) + grounding/relevance thresholds + one DENY topic (short <200-char definition) |
| Cognito user pool | `AWS::Cognito::UserPool` | `aws_cognito_user_pool.aegis` | Admin-create-only, 14-char password policy; MFA OFF in demo (note to enable) |
| Cognito operator group | `AWS::Cognito::UserPoolGroup` | `aws_cognito_user_group.operator` | `${app}-operator`, precedence 10 |
| Gateway log group | `AWS::Logs::LogGroup` | `aws_cloudwatch_log_group.gateway` | Retention = `log_retention_days` |
| Gateway IAM role | `AWS::IAM::Role GatewayLambdaRole` | `aws_iam_role.gateway` + `aws_iam_role_policy.gateway_least_privilege` | Allow PutItem/ConditionCheckItem on both tables; **explicit DENY UpdateItem/DeleteItem on audit**; `bedrock:ApplyGuardrail` on guardrail ARN; `bedrock:InvokeModel` on scoped model ARN (no `*`); `kms:Decrypt`/`GenerateDataKey` on CMK; logs to own group |
| Gateway Lambda | `AWS::Lambda::Function` (inline ZipFile) | `aws_lambda_function.gateway` + `archive_file` over `index.py` | python3.12, same fail-closed handler (allow only on guardrail `NONE`, conditional-put audit) |
| Cost-allocation tags | per-resource `Tags` | `locals.tags` map + `default_tags` in the env providers | `dept`/`app`/`data_class`/`pack`/`environment` on every taggable resource |
| Outputs | `Outputs` (with Exports) | `outputs.tf` | audit table name/arn, approval ledger, WORM bucket, guardrail id/arn, user pool id, gateway fn arn, kms key arn |

### Intentional, documented differences

- **No `Export`/cross-stack outputs.** Terraform composes via module outputs and
  remote state, not CloudFormation Exports. The same values are exposed as module
  `output`s.
- **Object Lock retention.** The core mirrors the CFN core exactly: Object Lock
  **enabled, no default retention** so the bucket tears down cleanly. The
  COMPLIANCE-profile default-retention variant lives in the golden-pilot
  (`infra/golden-pilot/evidence-worm.yaml`), matching the CFN split.
- **Lambda packaging.** CFN uses an inline `ZipFile`; Terraform packages the same
  handler from `index.py` via the `archive_file` data source (idiomatic Terraform).
  Handler logic is behaviourally identical.
