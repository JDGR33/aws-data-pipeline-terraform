output "function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "function_name" {
  description = "The unique name of the Lambda function."
  value       = aws_lambda_function.this.function_name
}

output "invoke_arn" {
  description = "The ARN to invoke the function."
  value       = aws_lambda_function.this.invoke_arn
}

output "log_group_name" {
  description = "Name of the CloudWatch Log Group for the function."
  value       = aws_cloudwatch_log_group.this.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch Log group for the function."
  value       = aws_cloudwatch_log_group.this.arn
}
