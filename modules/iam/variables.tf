variable "role_name" {
  description = "The name of the IAM role."
  type        = string
}

variable "description" {
  description = "Description of the IAM rol"
  type        = string
  default     = "IAM execution role for ingestion lambda."
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket where the lambda function is writes it's data."
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key used to encrypt raw data in S3."
  type        = string
}

variable "tags" {
  description = "A mapping of tags to assign to the IAM resources."
  type        = map(string)
  default     = {}
}
