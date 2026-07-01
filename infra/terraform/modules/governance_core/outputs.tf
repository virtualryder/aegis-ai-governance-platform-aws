# Aegis governance_core - outputs. Mirror the CloudFormation Outputs block.

output "audit_table_name" {
  description = "Append-only audit DynamoDB table name."
  value       = aws_dynamodb_table.audit.name
}

output "audit_table_arn" {
  description = "Append-only audit DynamoDB table ARN."
  value       = aws_dynamodb_table.audit.arn
}

output "approval_ledger_name" {
  description = "Single-use approval ledger DynamoDB table name."
  value       = aws_dynamodb_table.approvals.name
}

output "worm_bucket_name" {
  description = "WORM (Object Lock) evidence S3 bucket name."
  value       = aws_s3_bucket.worm_evidence.id
}

output "guardrail_id" {
  description = "Bedrock Guardrail id."
  value       = aws_bedrock_guardrail.aegis.guardrail_id
}

output "guardrail_arn" {
  description = "Bedrock Guardrail ARN."
  value       = aws_bedrock_guardrail.aegis.guardrail_arn
}

output "user_pool_id" {
  description = "Cognito user pool id (federated identity / JWT)."
  value       = aws_cognito_user_pool.aegis.id
}

output "gateway_fn_arn" {
  description = "Control-plane gateway Lambda ARN."
  value       = aws_lambda_function.gateway.arn
}

output "kms_key_arn" {
  description = "Customer-managed CMK ARN for this data class."
  value       = aws_kms_key.data_class.arn
}
