provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    kms        = var.localstack_endpoint
    s3         = var.localstack_endpoint
    iam        = var.localstack_endpoint
    lambda     = var.localstack_endpoint
    cloudwatch = var.localstack_endpoint
    glue       = var.localstack_endpoint
    sts        = var.localstack_endpoint
  }
}
