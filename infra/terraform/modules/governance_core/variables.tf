# Aegis governance_core - input variables.
# One-for-one with the CloudFormation Parameters in governance-core.yaml.

variable "data_class" {
  description = "Data classification this module governs (drives the CMK + guardrail)."
  type        = string
  default     = "pii"

  validation {
    condition     = contains(["public", "pii", "phi", "cji", "fti", "edu"], var.data_class)
    error_message = "data_class must be one of: public, pii, phi, cji, fti, edu."
  }
}

variable "pack" {
  description = "Compliance overlay pack name (e.g. enterprise, slg-core)."
  type        = string
  default     = "enterprise"
}

variable "department" {
  description = "Owning department for cost allocation / chargeback."
  type        = string
  default     = "shared-services"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, test, staging, prod."
  }
}

variable "app_name" {
  description = "Application / agent platform short name used in tags and naming."
  type        = string
  default     = "aegis"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days (keep low for cost)."
  type        = number
  default     = 7

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90], var.log_retention_days)
    error_message = "log_retention_days must be one of: 1, 3, 5, 7, 14, 30, 60, 90."
  }
}

variable "bedrock_model_id" {
  description = <<-EOT
    Bedrock model id the gateway Lambda is permitted to invoke (scoped, no wildcard
    Resource). Must be enabled for your account/region under Bedrock model access.
    Confirm availability in your target partition/region (commercial vs GovCloud).
  EOT
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "guardrail_grounding_threshold" {
  description = "Contextual grounding threshold (0.00-0.99). Higher is stricter."
  type        = number
  default     = 0.80

  validation {
    condition     = var.guardrail_grounding_threshold >= 0 && var.guardrail_grounding_threshold <= 0.99
    error_message = "guardrail_grounding_threshold must be between 0 and 0.99."
  }
}

variable "guardrail_relevance_threshold" {
  description = "Contextual relevance threshold (0.00-0.99). Higher is stricter."
  type        = number
  default     = 0.75

  validation {
    condition     = var.guardrail_relevance_threshold >= 0 && var.guardrail_relevance_threshold <= 0.99
    error_message = "guardrail_relevance_threshold must be between 0 and 0.99."
  }
}
