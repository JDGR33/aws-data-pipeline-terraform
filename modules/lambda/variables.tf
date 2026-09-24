variable "function_name" {
  description = "The Function's name."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-_]+$", var.function_name))
    error_message = "The function_name can only contain letters, numbers, hyphens, and underscores."

  }
}

variable "description" {
  description = "Description of the lambda function."
  type        = string
  default     = "Lambda function for data pipeline ingestion."
}

variable "role_arn" {
  description = "The ARN of the IAM role for this Lambda function."
  type        = string
}

variable "handler" {
  description = "The function entrypoint in the code"
  type        = string
  default     = "lambda_handler.lambda_handler"
}

variable "runtime" {
  description = "The runtime environment for this Lambda function."
  type        = string
  default     = "python3.12"
}

variable "timeout" {
  description = "Amount of time the Lambda function has to run in seconds."
  type        = number
  default     = 300

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "The timeout must be between 1 and 900 seconds."
  }
}

variable "memory_size" {
  description = "Amount of memory in MB."
  type        = number
  default     = 256

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "The memory_size must be between 128 MB and 10,240 MB."
  }
}

variable "package_path" {
  description = "Local file path to the Lambda zip file."
  type        = string
}

variable "environment_variables" {
  description = "Key-value map of environment variables to pass to the Lambda function."
  type        = map(string)
  default     = {}
}

variable "log_retention_in_days" {
  description = "The number of days to retain logs."
  type        = number
  default     = 14

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120], var.log_retention_in_days)
    error_message = "log_retention_in_days must be a valid CloudWatch retention period less than 120."
  }
}

variable "tags" {
  description = "A mapping of tags for the resources."
  type        = map(string)
  default     = {}
}

