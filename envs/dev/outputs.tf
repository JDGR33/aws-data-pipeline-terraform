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
