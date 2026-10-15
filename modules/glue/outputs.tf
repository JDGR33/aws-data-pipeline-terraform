output "job_name" {
  description = "The name of the AWS Glue ETL Job."
  value       = aws_glue_job.this.name
}

output "job_arn" {
  description = "The Amazon Resource Name (ARN) of the Glue Job."
  value       = aws_glue_job.this.arn
}

output "job_id" {
  description = "The ID of the Glue Job."
  value       = aws_glue_job.this.id
}

output "role_arn" {
  description = "The ARN of the IAM execution role used by the Glue Job."
  value       = aws_iam_role.glue.arn
}

output "role_name" {
  description = "The name of the IAM execution role used by the Glue Job."
  value       = aws_iam_role.glue.name
}

output "script_s3_uri" {
  description = "The S3 URI of the uploaded PySpark script."
  value       = local.script_s3_uri
}

output "trigger_name" {
  description = "The name of the scheduled Glue trigger (null if no schedule was defined)."
  value       = try(aws_glue_trigger.scheduled[0].name, null)
}

output "trigger_arn" {
  description = "The ARN of the scheduled Glue trigger (null if no schedule was defined)."
  value       = try(aws_glue_trigger.scheduled[0].arn, null)
}
