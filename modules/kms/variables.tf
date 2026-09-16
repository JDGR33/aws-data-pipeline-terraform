variable "description" {
  description = "The description of the KMS key as it appears in the AWS console."
  type        = string
  default     = "Customer managed KMS key for data pipeline S3 buckets encryption"
}

variable "deletion_window_in_days" {
  description = "The waiting period, specified in number of days, before the key is deleted permanently (7 to 30 days)."
  type        = number
  default     = 7

  validation {
    condition     = var.deletion_window_in_days >= 7 && var.deletion_window_in_days <= 30
    error_message = "The deletion_window_in_days must be between 7 and 30 days."
  }
}

variable "enable_key_rotation" {
  description = "Specifies whether key rotation is enabled. Defaults to true for security best practices."
  type        = bool
  default     = true
}

variable "alias_name" {
  description = "The display name of the alias. Must begin with 'alias/'."
  type        = string

  validation {
    condition     = startswith(var.alias_name, "alias/")
    error_message = "The alias_name must start with 'alias/' prefix."
  }
}

variable "tags" {
  description = "A mapping of tags to assign to the KMS resources."
  type        = map(string)
  default     = {}
}
