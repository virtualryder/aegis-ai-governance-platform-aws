# Aegis governance_core - dev example, COMMERCIAL partition (aws), us-east-1.
# This is the same region/account family that live-validated the CloudFormation
# core (DEPLOYED-AND-VALIDATED.md Run 1, account 864217980669, us-east-1).

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
  region = "us-east-1"

  # default_tags flow onto every taggable resource in addition to the module's
  # own locals.tags map, so account-wide tagging policy is honored too.
  default_tags {
    tags = {
      managed_by = "terraform"
      module     = "aegis-governance-core"
    }
  }
}

module "governance_core" {
  source = "../../modules/governance_core"

  app_name    = "aegis"
  pack        = "enterprise"
  data_class  = "pii"
  department  = "shared-services"
  environment = "dev"

  # Commercial-partition Bedrock model (confirm enabled under model access).
  bedrock_model_id = "anthropic.claude-3-haiku-20240307-v1:0"

  log_retention_days = 7
}

output "audit_table_name" {
  value = module.governance_core.audit_table_name
}

output "worm_bucket_name" {
  value = module.governance_core.worm_bucket_name
}

output "guardrail_id" {
  value = module.governance_core.guardrail_id
}

output "gateway_fn_arn" {
  value = module.governance_core.gateway_fn_arn
}
