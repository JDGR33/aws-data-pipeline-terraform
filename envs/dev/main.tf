module "kms" {
  source = "../../modules/kms"

  alias_name  = "alias/${var.project_name}-${var.environment}"
  description = "Customer managed KMS key for ${var.project_name} (${var.environment}) S3 buckets"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}
