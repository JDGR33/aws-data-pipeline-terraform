# ---
# KMS
# ---

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
  description = "ID of the bronze S3 bucket."
  value       = module.s3_bronze.bucket_id
}

output "s3_bronze_bucket_arn" {
  description = "The ARN of the bronze S3 bucket."
  value       = module.s3_bronze.bucket_arn
}

# ---
# S3 Silver
# ---

output "s3_silver_bucket_id" {
  description = "ID of the silver S3 bucket."
  value       = module.s3_silver.bucket_id
}

output "s3_silver_bucket_arn" {
  description = "The ARN of the silver S3 bucket."
  value       = module.s3_silver.bucket_arn
}

# ---
# S3 Artifacts
# ---

output "s3_artifacts_bucket_id" {
  description = "ID of the artifacts S3 bucket."
  value       = module.s3_artifacts.bucket_id
}

output "s3_artifacts_bucket_arn" {
  description = "The ARN of the artifacts S3 bucket."
  value       = module.s3_artifacts.bucket_arn
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

# ---
# EventBridge
# ---

output "event_rule_arn" {
  description = "The EventBridge rule ARN for raw collection."
  value       = module.eventbridge.rule_arn
}

output "event_rule_name" {
  description = "The EventBridge rule name for raw collection."
  value       = module.eventbridge.rule_name
}

# ---
# AWS Glue
# ---

output "glue_job_name" {
  description = "The name of the AWS Glue PySpark ETL job."
  value       = module.glue.job_name
}

output "glue_job_arn" {
  description = "The ARN of the AWS Glue PySpark ETL job."
  value       = module.glue.job_arn
}

output "glue_role_arn" {
  description = "The ARN of the IAM execution role used by the Glue job."
  value       = module.glue.role_arn
}

output "glue_script_s3_uri" {
  description = "The S3 URI of the PySpark ETL script."
  value       = module.glue.script_s3_uri
}

# ---
# Amazon Athena & Glue Data Catalog
# ---

output "athena_database_name" {
  description = "The name of the AWS Glue Catalog database."
  value       = module.athena.database_name
}

output "athena_workgroup_name" {
  description = "The name of the Amazon Athena workgroup."
  value       = module.athena.workgroup_name
}

output "athena_results_s3_uri" {
  description = "The S3 URI where Athena stores query execution results."
  value       = module.athena.query_results_s3_uri
}

output "athena_table_names" {
  description = "The list of external table names registered in the Glue Catalog."
  value       = module.athena.table_names
}
