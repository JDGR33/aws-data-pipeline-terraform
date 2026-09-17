variable "bucket_name" {
  description = "The s3 bucket name"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.bucket_name))
    error_message = "Bucket name must contain only lowercase letters, numbers, dots, and hyphens."
  }
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key to enforce SSE-KMS encryption"
  type        = string
  # No default - this is a required input
}

variable "versioning_status" {
  description = "Status of versioning of the bucket"
  type        = string
  default     = "Enabled"

  validation {
    condition     = contains(["Enabled", "Suspended", "Disabled"], var.versioning_status)
    error_message = "The versioning_status must be 'Enabled', 'Suspended', or 'Disabled'."
  }
}

variable "force_destroy" {
  description = "Whether to allow bucket deletion even if it contains objects"
  type        = bool
  default     = false
}

variable "tags" {
  description = "A mapping of tags to assign to the S3 buckeg resources."
  type        = map(string)
  default     = {}
}
