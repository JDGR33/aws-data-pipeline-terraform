variable "aws_region" {
  description = "The AWS region to deploy resources into."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "The deployment environment (e.g. dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "The name of the project, used in resource naming and tags."
  type        = string
  default     = "texas-data-pipeline"
}

variable "localstack_endpoint" {
  description = "The endpoint URL for LocalStack services in local development."
  type        = string
  default     = "http://localhost:4566"
}
