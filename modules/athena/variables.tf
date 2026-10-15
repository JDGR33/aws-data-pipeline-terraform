variable "database_name" {
  description = "The name of the AWS Glue Data Catalog database."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9_]+$", var.database_name))
    error_message = "Glue database names can only contain lowercase letters, numbers, and underscores."
  }
}

variable "description" {
  description = "Description of the Glue Catalog database."
  type        = string
  default     = "Glue Data Catalog for Texas Energy and Weather data lake."
}

variable "workgroup_name" {
  description = "The name of the AWS Athena Workgroup."
  type        = string
}

variable "silver_bucket_id" {
  description = "The Silver S3 bucket ID containing the partitioned Parquet tables."
  type        = string
}

variable "artifacts_bucket_id" {
  description = "The S3 bucket ID used for storing Athena query execution results."
  type        = string
}

variable "athena_results_prefix" {
  description = "S3 prefix/directory within the artifacts bucket for query results."
  type        = string
  default     = "athena-results/"
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN used to encrypt Athena query results and decrypt S3 data."
  type        = string
}

variable "tags" {
  description = "Resource tags to apply to Athena and Glue resources."
  type        = map(string)
  default     = {}
}
