# Aegis - Governed Agent Platform - governance_core module: provider + version pins.
# Mirrors infra/cloudformation/governance-core.yaml (the live-proven core, Run 1).
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}
