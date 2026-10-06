# Schedule Rules
resource "aws_cloudwatch_event_rule" "this" {
  name                = var.rule_name
  description         = var.description
  schedule_expression = var.schedule_expression
  state               = var.is_enabled ? "ENABLED" : "DISABLED"

  tags = var.tags
}

# Target Mapping
resource "aws_cloudwatch_event_target" "this" {
  rule      = aws_cloudwatch_event_rule.this.name
  target_id = "${var.rule_name}-target"
  arn       = var.target_arn
  input     = var.target_input
}

# invocation Rights on the Lambda Function
resource "aws_lambda_permission" "this" {
  statement_id  = "AllowExecutionFromEventBridge-${var.rule_name}"
  action        = "lambda:InvokeFunction"
  function_name = var.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.this.arn
}
