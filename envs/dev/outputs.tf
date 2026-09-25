output "kms_key_arn" {
  description = "The Amazon Resource Name (ARN) of the customer-managed KMS key."
  value       = module.kms.key_arn
}

output "kms_key_id" {
  description = "The globally unique identifier for the KMS key."
  value       = module.kms.key_id
}

output "kms_alias_arn" {
  description = "The Amazon Resource Name (ARN) of the KMS key alias."
  value       = module.kms.alias_arn
}

output "kms_alias_name" {
  description = "The display name of the KMS key alias."
  value       = module.kms.alias_name
}


# ---
# S3 Bronze
# ---

output "s3_bronze_bucket_id" {
  description = "ID of the bronze s3 bucket."
  value       = module.s3_bronze.bucket_id
}

output "s3_bronze_bucket_arn" {
  description = "The ARN of the bronze s3 bucket."
  value       = module.s3_bronze.bucket_arn
}

# ---
# S3 Silver
# ---

output "s3_silver_bucket_id" {
  description = "ID of the silver s3 bucket."
  value       = module.s3_silver.bucket_id
}

output "s3_silver_bucket_arn" {
  description = "The ARN of the silver s3 bucket."
  value       = module.s3_silver.bucket_arn
}

# ---
# IAM (Collector)
# ---

output "iam_collector_role_arn" {
  description = "The ARN of the collector Lambda IAM execution role."
  value       = module.iam.role_arn
}

output "iam_collector_role_name" {
  description = "The name of the collector Lambda IAM execution role."
  value       = module.iam.role_name
}

# ---
# Lambda (Collector)
# ---

output "lambda_collector_function_arn" {
  description = "The ARN of the collector Lambda function."
  value       = module.lambda.function_arn
}

output "lambda_collector_function_name" {
  description = "The name of the collector Lambda function."
  value       = module.lambda.function_name
}

output "lambda_collector_invoke_arn" {
  description = "The invocation ARN used by EventBridge / API Gateway to trigger the Lambda."
  value       = module.lambda.invoke_arn
}

output "lambda_collector_log_group_name" {
  description = "The CloudWatch Log Group name for the collector Lambda."
  value       = module.lambda.log_group_name
}

output "lambda_collector_log_group_arn" {
  description = "The CloudWatch Log Group ARN for the collector Lambda."
  value       = module.lambda.log_group_arn
}

