resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_in_days
  tags              = var.tags
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  description   = var.description
  role          = var.role_arn
  handler       = var.handler
  runtime       = var.runtime
  timeout       = var.timeout
  memory_size   = var.memory_size

  # Code and drift detection
  filename         = var.package_path
  source_code_hash = filebase64sha256(var.package_path)


  # Only if variables are supplied
  dynamic "environment" {
    for_each = length(keys(var.environment_variables)) > 0 ? [var.environment_variables] : []
    content {
      variables = environment.value
    }

  }

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.this]
}



