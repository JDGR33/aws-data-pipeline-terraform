variable "rule_name" {
  description = "EventBridge rule name."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-_]+$", var.rule_name))
    error_message = "The rule_name can only have alphanumeric characters, hyphens, and underscores."
  }
}

variable "description" {
  description = "EventBridge rule description."
  type        = string
  default     = "Scheduled trigger for data ingestion pipeline."
}

variable "schedule_expression" {
  description = "Scheduling expression."
  type        = string
}

variable "is_enabled" {
  description = "Whether the rule is enabled or not."
  type        = bool
  default     = true
}

variable "target_arn" {
  description = "ARN of the target to invoke"
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function to invoke."
  type        = string
  default     = null
}

variable "target_input" {
  description = "Optional JSON payload to pass to the target"
  type        = string
  default     = null
}

variable "tags" {
  description = "Resource tags to attach to the EventBridge rule."
  type        = map(string)
  default     = {}
}
