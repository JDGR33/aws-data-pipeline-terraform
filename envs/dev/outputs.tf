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
