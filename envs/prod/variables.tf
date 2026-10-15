variable "aws_region" {
  description = "The AWS region to deploy resources into."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "The AWS CLI profile to use for deployment. Defaults to null (uses standard environment credentials or default profile)."
  type        = string
  default     = "dev"
}

variable "environment" {
  description = "The deployment environment (e.g. dev, staging, prod)."
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "The name of the project, used in resource naming and tags."
  type        = string
  default     = "texas-data-pipeline"
}

variable "bucket_suffix" {
  description = "Optional unique suffix appended to S3 bucket names to avoid global namespace collisions on AWS."
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Whether to allow bucket deletion even if it contains objects (useful for testing and clean teardown)."
  type        = bool
  default     = true
}

variable "schedule_expression" {
  description = "Scheduling expression for EventBridge ingestion trigger."
  type        = string
  default     = "rate(1 day)"
}

variable "schedule_enabled" {
  description = "Whether the EventBridge ingestion rule is enabled."
  type        = bool
  default     = false
}

variable "eia_api_key" {
  description = "API key for EIA (U.S. Energy Information Administration). Optional if only collecting Open-Meteo weather."
  type        = string
  default     = ""
  sensitive   = true
}

variable "glue_timeout" {
  description = "Execution timeout for the Glue job in minutes (cost safety guardrail)."
  type        = number
  default     = 10
}

variable "glue_number_of_workers" {
  description = "Number of G.1X workers to allocate for the Glue job."
  type        = number
  default     = 2
}

variable "glue_schedule_expression" {
  description = "The cron schedule expression for the Glue PySpark ETL job (e.g. 06:30 UTC daily, 30 mins after collection)."
  type        = string
  default     = "cron(30 6 * * ? *)"
}

variable "glue_schedule_enabled" {
  description = "Whether the scheduled Glue trigger is enabled."
  type        = bool
  default     = true
}
