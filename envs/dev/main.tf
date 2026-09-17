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

module "s3_bronze" {
  source = "../../modules/s3"

  bucket_name   = "${var.project_name}-${var.environment}-bronze"
  kms_key_arn   = module.kms.key_arn
  force_destroy = true # This is to easily delete things in Dev

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Layer       = "bronze"
    ManagedBy   = "Terraform"
  }
}


module "s3_silver" {
  source = "../../modules/s3"

  bucket_name   = "${var.project_name}-${var.environment}-silver"
  kms_key_arn   = module.kms.key_arn
  force_destroy = true # This is to easily delete things in Dev

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Layer       = "silver"
    ManagedBy   = "Terraform"
  }
}
