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

module "iam" {
  source = "../../modules/iam"

  role_name     = "${var.project_name}-${var.environment}-collector-role"
  s3_bucket_arn = module.s3_bronze.bucket_arn
  kms_key_arn   = module.kms.key_arn

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

module "lambda" {
  source = "../../modules/lambda"

  function_name = "${var.project_name}-${var.environment}-collector"
  role_arn      = module.iam.role_arn
  package_path  = "${path.module}/../../dist/collector_lambda.zip"
  environment_variables = {
    RAW_BUCKET  = module.s3_bronze.bucket_id
    DESTINATION = "s3"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

module "evenbridge" {
  source = "../../modules/eventbridge"

  rule_name   = "${var.project_name}-${var.environment}"
  description = "Daily scheduled trigger for Texas Energy and Weather raw collection"

  schedule_expression = "rate(1 day)"
  is_enabled          = true

  target_arn    = module.lambda.function_arn
  function_name = module.lambda.function_name

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}
