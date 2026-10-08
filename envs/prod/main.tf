locals {
  name_suffix = var.bucket_suffix != "" ? "-${var.bucket_suffix}" : ""
}

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

  bucket_name   = "${var.project_name}-${var.environment}${local.name_suffix}-bronze"
  kms_key_arn   = module.kms.key_arn
  force_destroy = var.force_destroy

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Layer       = "bronze"
    ManagedBy   = "Terraform"
  }
}

module "s3_silver" {
  source = "../../modules/s3"

  bucket_name   = "${var.project_name}-${var.environment}${local.name_suffix}-silver"
  kms_key_arn   = module.kms.key_arn
  force_destroy = var.force_destroy

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
  environment_variables = merge(
    {
      RAW_BUCKET  = module.s3_bronze.bucket_id
      DESTINATION = "s3"
    },
    var.eia_api_key != "" ? { EIA_API_KEY = var.eia_api_key } : {}
  )

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

module "eventbridge" {
  source = "../../modules/eventbridge"

  rule_name   = "${var.project_name}-${var.environment}"
  description = "Daily scheduled trigger for Texas Energy and Weather raw collection (${var.environment})"

  schedule_expression = var.schedule_expression
  is_enabled          = var.schedule_enabled

  target_arn    = module.lambda.function_arn
  function_name = module.lambda.function_name

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}
