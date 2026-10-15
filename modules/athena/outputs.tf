output "database_name" {
  description = "The name of the AWS Glue Catalog database."
  value       = aws_glue_catalog_database.this.name
}

output "database_arn" {
  description = "The ARN of the AWS Glue Catalog database."
  value       = aws_glue_catalog_database.this.arn
}

output "workgroup_name" {
  description = "The name of the AWS Athena Workgroup."
  value       = aws_athena_workgroup.this.name
}

output "workgroup_arn" {
  description = "The ARN of the AWS Athena Workgroup."
  value       = aws_athena_workgroup.this.arn
}

output "query_results_s3_uri" {
  description = "The S3 URI where Athena query results are stored."
  value       = "s3://${var.artifacts_bucket_id}/${var.athena_results_prefix}"
}

output "table_names" {
  description = "List of external tables registered in the Glue Data Catalog."
  value = [
    aws_glue_catalog_table.ercot_demand_forecast.name,
    aws_glue_catalog_table.ercot_fuel_type.name,
    aws_glue_catalog_table.tx_retail_sales.name,
    aws_glue_catalog_table.texas_weather.name,
  ]
}
