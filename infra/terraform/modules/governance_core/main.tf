# Aegis - Governed Agent Platform - governance_core module.
#
# Terraform parity for infra/cloudformation/governance-core.yaml. The CloudFormation
# core is the live-validated authoritative definition (DEPLOYED-AND-VALIDATED.md Run 1);
# this module reproduces it resource-for-resource so Terraform-standardized adopters can
# deploy the same governance boundary. Partition-aware so ARNs resolve in both the
# `aws` (commercial) and `aws-us-gov` (GovCloud) partitions.

# ---------------------------------------------------------------------------
# Data sources - partition-aware identity/region/account resolution.
# ---------------------------------------------------------------------------
data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# Locals - naming + the cost-allocation tag map applied to every taggable
# resource (mirrors the CFN dept/app/data_class/pack/environment tags).
# ---------------------------------------------------------------------------
locals {
  name_suffix = "${var.data_class}-${var.environment}"

  partition  = data.aws_partition.current.partition
  region     = data.aws_region.current.name
  account_id = data.aws_caller_identity.current.account_id

  # Scoped, no-wildcard foundation-model ARN (partition + region aware).
  bedrock_model_arn = "arn:${local.partition}:bedrock:${local.region}::foundation-model/${var.bedrock_model_id}"

  tags = {
    dept        = var.department
    app         = var.app_name
    data_class  = var.data_class
    pack        = var.pack
    environment = var.environment
  }
}

# ---------------------------------------------------------------------------
# KMS - customer-managed CMK per data class (+ rotation) and a friendly alias.
# ---------------------------------------------------------------------------
resource "aws_kms_key" "data_class" {
  description             = "Aegis CMK for data class ${var.data_class} (${var.app_name}/${var.environment})"
  enable_key_rotation     = true
  key_usage               = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  deletion_window_in_days = 7

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "aegis-cmk-policy"
    Statement = [
      {
        Sid       = "EnableRootAccountAdmin"
        Effect    = "Allow"
        Principal = { AWS = "arn:${local.partition}:iam::${local.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      # Confused-deputy guard: each service principal is constrained to this
      # account (aws:SourceAccount) and to requests made via that specific
      # service in this region (kms:ViaService).
      {
        Sid       = "AllowDynamoDbUseOfKey"
        Effect    = "Allow"
        Principal = { Service = "dynamodb.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = local.account_id
            "kms:ViaService"    = "dynamodb.${local.region}.amazonaws.com"
          }
        }
      },
      {
        Sid       = "AllowS3UseOfKey"
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = local.account_id
            "kms:ViaService"    = "s3.${local.region}.amazonaws.com"
          }
        }
      },
      {
        Sid       = "AllowLogsUseOfKey"
        Effect    = "Allow"
        Principal = { Service = "logs.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = local.account_id
            "kms:ViaService"    = "logs.${local.region}.amazonaws.com"
          }
        }
      },
    ]
  })

  tags = local.tags
}

resource "aws_kms_alias" "data_class" {
  name          = "alias/${var.app_name}-${var.data_class}-${var.environment}"
  target_key_id = aws_kms_key.data_class.key_id
}

# ---------------------------------------------------------------------------
# DynamoDB - append-only audit table (hash request_id + range seq).
# Append-only is enforced by the gateway IAM role's explicit deny (below),
# not by the table itself.
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "audit" {
  name         = "${var.app_name}-audit-${local.name_suffix}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "request_id"
  range_key    = "seq"

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "seq"
    type = "N"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.data_class.arn
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------
# DynamoDB - single-use approval ledger (hash approval_id, TTL expires_at).
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "approvals" {
  name         = "${var.app_name}-approvals-${local.name_suffix}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "approval_id"

  attribute {
    name = "approval_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.data_class.arn
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------
# S3 - WORM evidence bucket. Object Lock ENABLED with NO default retention so
# teardown stays clean (mirrors the CFN core exactly; the golden-pilot
# evidence-worm.yaml is the variant that applies a default retention rule).
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "worm_evidence" {
  bucket              = "${var.app_name}-worm-${local.name_suffix}-${local.account_id}"
  object_lock_enabled = true
  force_destroy       = false

  tags = local.tags
}

resource "aws_s3_bucket_versioning" "worm_evidence" {
  bucket = aws_s3_bucket.worm_evidence.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Object Lock ENABLED, but intentionally NO `rule { default_retention }` block -
# no default retention, so the bucket tears down cleanly. WORM is applied
# per-object (or via the COMPLIANCE-profile golden-pilot template) in production.
resource "aws_s3_bucket_object_lock_configuration" "worm_evidence" {
  bucket = aws_s3_bucket.worm_evidence.id

  object_lock_enabled = "Enabled"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "worm_evidence" {
  bucket = aws_s3_bucket.worm_evidence.id

  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_class.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "worm_evidence" {
  bucket = aws_s3_bucket.worm_evidence.id

  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# Bedrock Guardrail - PII sensitive-info filters, contextual grounding +
# relevance thresholds, and one DENY topic (definition kept short for the
# Bedrock 200-char topic-definition limit; mirrors the shortened CFN core).
# Provider version is pinned in versions.tf (~> 5.60) since this resource
# schema stabilized in recent provider releases.
# ---------------------------------------------------------------------------
resource "aws_bedrock_guardrail" "aegis" {
  name                      = "${var.app_name}-guardrail-${local.name_suffix}"
  blocked_input_messaging   = "This request was blocked by Aegis governance policy."
  blocked_outputs_messaging = "This response was blocked by Aegis governance policy."
  description               = "Aegis mandatory guardrail: PII filters, contextual grounding + relevance, and a denied topic. Applied on input and output by the control-plane gateway."

  sensitive_information_policy_config {
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "US_SOCIAL_SECURITY_NUMBER"
      action = "BLOCK"
    }
  }

  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = var.guardrail_grounding_threshold
    }
    filters_config {
      type      = "RELEVANCE"
      threshold = var.guardrail_relevance_threshold
    }
  }

  topic_policy_config {
    topics_config {
      name       = "UngroundedConsequentialAction"
      type       = "DENY"
      definition = "Taking a consequential action (issue, adjudicate, release, award, or transfer) without a valid bound human approval, instead of routing it to the human gate."
      examples = [
        "Go ahead and approve and release the payment now.",
        "Issue the permit without waiting for sign-off.",
      ]
    }
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------
# Cognito - user pool for federated JWT + an operator role group.
# NOTE on MFA: the CFN core ships MfaConfiguration OFF for a clean, low-cost
# teardown demo; the hardened golden-pilot cognito-identity.yaml requires
# software-token MFA. Set mfa_configuration = "ON" with a software_token_mfa
# block for any regulated deployment (CJIS v6.0 mandates MFA).
# ---------------------------------------------------------------------------
resource "aws_cognito_user_pool" "aegis" {
  name             = "${var.app_name}-pool-${local.name_suffix}"
  mfa_configuration = "OFF"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length    = 14
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  tags = local.tags
}

resource "aws_cognito_user_group" "operator" {
  name         = "${var.app_name}-operator"
  user_pool_id = aws_cognito_user_pool.aegis.id
  description  = "Role group whose JWT role claim the gateway evaluates for least-privilege."
  precedence   = 10
}

# ---------------------------------------------------------------------------
# CloudWatch Logs - the gateway Lambda's own log group.
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/aws/lambda/${var.app_name}-gateway-${local.name_suffix}"
  retention_in_days = var.log_retention_days

  tags = local.tags
}

# ---------------------------------------------------------------------------
# IAM - least-privilege gateway role. Allows append-only writes, an EXPLICIT
# DENY on audit mutations, guardrail apply, scoped Bedrock invoke (no wildcard
# Resource), CMK data-key use, and logs to its own group.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "gateway" {
  name = "${var.app_name}-gateway-role-${local.name_suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      },
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "gateway_least_privilege" {
  name = "aegis-gateway-least-privilege"
  role = aws_iam_role.gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AuditAppendOnly"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:ConditionCheckItem"]
        Resource = [aws_dynamodb_table.audit.arn]
      },
      {
        Sid      = "AuditDenyMutations"
        Effect   = "Deny"
        Action   = ["dynamodb:UpdateItem", "dynamodb:DeleteItem"]
        Resource = [aws_dynamodb_table.audit.arn]
      },
      {
        Sid      = "ApprovalLedgerBoundWrites"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:ConditionCheckItem"]
        Resource = [aws_dynamodb_table.approvals.arn]
      },
      {
        Sid      = "BedrockGuardrailApply"
        Effect   = "Allow"
        Action   = ["bedrock:ApplyGuardrail"]
        Resource = [aws_bedrock_guardrail.aegis.guardrail_arn]
      },
      {
        Sid      = "BedrockInvokeScoped"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = [local.bedrock_model_arn]
      },
      {
        Sid      = "KmsDataKeyOnCmk"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = [aws_kms_key.data_class.arn]
      },
      {
        Sid    = "LogsToOwnGroup"
        Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = [
          aws_cloudwatch_log_group.gateway.arn,
          "${aws_cloudwatch_log_group.gateway.arn}:*",
        ]
      },
    ]
  })
}

# ---------------------------------------------------------------------------
# Lambda - control-plane gateway (stub). Same fail-closed handler as the CFN
# core: applies the guardrail, allows ONLY on an explicit NONE, writes an
# append-only audit record with a conditional-put. Packaged from index.py via
# the archive_file data source.
# ---------------------------------------------------------------------------
data "archive_file" "gateway" {
  type        = "zip"
  source_file = "${path.module}/index.py"
  output_path = "${path.module}/build/gateway.zip"
}

resource "aws_lambda_function" "gateway" {
  function_name    = "${var.app_name}-gateway-${local.name_suffix}"
  description      = "Aegis control-plane gateway entrypoint (stub) - writes an audit record and applies the guardrail."
  role             = aws_iam_role.gateway.arn
  runtime          = "python3.12"
  handler          = "index.handler"
  timeout          = 30
  memory_size      = 128
  filename         = data.archive_file.gateway.output_path
  source_code_hash = data.archive_file.gateway.output_base64sha256

  environment {
    variables = {
      AUDIT_TABLE       = aws_dynamodb_table.audit.name
      APPROVAL_LEDGER   = aws_dynamodb_table.approvals.name
      GUARDRAIL_ID      = aws_bedrock_guardrail.aegis.guardrail_id
      GUARDRAIL_VERSION = aws_bedrock_guardrail.aegis.version
      DATA_CLASS        = var.data_class
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.gateway,
    aws_iam_role_policy.gateway_least_privilege,
  ]

  tags = local.tags
}
