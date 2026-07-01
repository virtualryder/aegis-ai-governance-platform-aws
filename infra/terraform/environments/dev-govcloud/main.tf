# Aegis governance_core - dev example, GOVCLOUD partition (aws-us-gov), us-gov-west-1.
#
# GovCloud differences vs the commercial example (all handled by the module's
# partition-aware data sources - no module code changes needed):
#
#   * PARTITION: resources land in the `aws-us-gov` partition. The module builds
#     every ARN from data.aws_partition.current, so the CMK key policy, the
#     scoped Bedrock model ARN, and the guardrail ARN all resolve as
#     arn:aws-us-gov:... automatically. Never hardcode arn:aws:... and never
#     reference a resource across partitions (no cross-partition ARNs).
#   * REGION: us-gov-west-1 is a FedRAMP High authorized region. Keep all data,
#     keys, and logs in-partition/in-region for the residency boundary.
#   * SERVICE AVAILABILITY: confirm Amazon Bedrock, Bedrock Guardrails, and the
#     specific foundation model are available in your GovCloud region before
#     apply - Bedrock service and model coverage in GovCloud lags commercial and
#     changes over time. Validate against the AWS GovCloud service/region matrix
#     and your account's Bedrock model access, then set bedrock_model_id to a
#     model actually enabled in-partition.
#   * IDENTITY: for regulated GovCloud workloads set the Cognito pool to require
#     MFA (see the module's mfa_configuration note); CJIS v6.0 mandates MFA.
#
# A GovCloud AWS account and GovCloud-scoped credentials are required to plan or
# apply this configuration.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = "us-gov-west-1"

  default_tags {
    tags = {
      managed_by = "terraform"
      module     = "aegis-governance-core"
      partition  = "aws-us-gov"
    }
  }
}

module "governance_core" {
  source = "../../modules/governance_core"

  app_name    = "aegis"
  pack        = "slg-core"
  data_class  = "cji"
  department  = "public-safety"
  environment = "dev"

  # IMPORTANT: confirm this model id is available/enabled in us-gov-west-1
  # Bedrock model access before apply. GovCloud model coverage differs from
  # commercial; substitute a model that is actually enabled in-partition.
  bedrock_model_id = "anthropic.claude-3-haiku-20240307-v1:0"

  log_retention_days = 30
}

output "audit_table_name" {
  value = module.governance_core.audit_table_name
}

output "worm_bucket_name" {
  value = module.governance_core.worm_bucket_name
}

output "kms_key_arn" {
  value = module.governance_core.kms_key_arn
}
