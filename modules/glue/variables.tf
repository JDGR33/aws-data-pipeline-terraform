variable "job_name" {
  description = "The name of the AWS Glue ETL Job."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-_]+$", var.job_name))
    error_message = "The job_name can only contain letters, numbers, hyphens, and underscores."
  }
}

variable "description" {
  description = "Description of the AWS Glue job."
  type        = string
  default     = "PySpark ETL job to transform Bronze JSON to Silver Parquet."
}

variable "glue_version" {
  description = "The Glue version to use (e.g. 4.0 for Apache Spark 3.3.0 and Python 3.10)."
  type        = string
  default     = "4.0"
}

variable "role_name" {
  description = "Optional custom name for the IAM execution role. If omitted, defaults to <job_name>-role."
  type        = string
  default     = null
}

variable "script_local_path" {
  description = "Local filesystem path to the PySpark script to upload."
  type        = string
}

variable "script_bucket_id" {
  description = "S3 bucket ID where the Glue ETL script will be uploaded."
  type        = string
}

variable "script_bucket_arn" {
  description = "The ARN of the S3 bucket where the Glue ETL script will be uploaded."
  type        = string
}

variable "script_s3_key" {
  description = "S3 object key under which the Glue ETL script will be placed."
  type        = string
  default     = "scripts/transform_raw_to_refined.py"
}

variable "bronze_bucket_id" {
  description = "The Bronze S3 bucket ID containing raw JSON payloads."
  type        = string
}

variable "bronze_bucket_arn" {
  description = "The ARN of the Bronze S3 bucket."
  type        = string
}

variable "silver_bucket_id" {
  description = "The Silver S3 bucket ID where refined Parquet files will be stored."
  type        = string
}

variable "silver_bucket_arn" {
  description = "The ARN of the Silver S3 bucket."
  type        = string
}

variable "kms_key_arn" {
  description = "The customer-managed KMS key ARN for decrypting Bronze and encrypting Silver."
  type        = string
}

variable "worker_type" {
  description = "The type of predefined worker that is allocated (Standard, G.1X, G.2X)."
  type        = string
  default     = "G.1X"

  validation {
    condition     = contains(["G.1X", "G.2X", "Standard"], var.worker_type)
    error_message = "The worker_type must be one of: 'G.1X', 'G.2X', or 'Standard'."
  }
}

variable "number_of_workers" {
  description = "The number of workers allocated when the Glue job runs (minimum 2 for G.1X/G.2X)."
  type        = number
  default     = 2

  validation {
    condition     = var.number_of_workers >= 2 && var.number_of_workers <= 10
    error_message = "The number_of_workers must be between 2 and 10 to ensure strict cost control."
  }
}

variable "timeout" {
  description = "The job execution timeout in minutes. Set conservatively to prevent runaway costs."
  type        = number
  default     = 10

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 60
    error_message = "The timeout must be between 1 and 60 minutes."
  }
}

variable "max_retries" {
  description = "The maximum number of times to retry this job if it fails. Default 0 for dev/cost control."
  type        = number
  default     = 0

  validation {
    condition     = var.max_retries >= 0 && var.max_retries <= 3
    error_message = "The max_retries must be between 0 and 3."
  }
}

variable "default_arguments" {
  description = "Additional or overriding default arguments passed to the Glue job."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Key-value mapping of resource tags."
  type        = map(string)
  default     = {}
}
