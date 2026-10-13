locals {
  role_name     = var.role_name != null ? var.role_name : "${var.job_name}-role"
  script_s3_uri = "s3://${var.script_bucket_id}/${var.script_s3_key}"
}

# ---
# Upload PySpark Script to S3
# ---
resource "aws_s3_object" "script" {
  bucket      = var.script_bucket_id
  key         = var.script_s3_key
  source      = var.script_local_path
  source_hash = filemd5(var.script_local_path)
  kms_key_id  = var.kms_key_arn

  tags = var.tags
}

# ---
# IAM Execution Role for AWS Glue
# ---
resource "aws_iam_role" "glue" {
  name        = local.role_name
  description = "Execution role for Glue Job ${var.job_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_lake_access" {
  name = "${local.role_name}-policy"
  role = aws_iam_role.glue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BronzeReadOnlyAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.bronze_bucket_arn,
          "${var.bronze_bucket_arn}/*"
        ]
      },
      {
        Sid    = "S3ArtifactsScriptReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${var.script_bucket_arn}/*"
        ]
      },
      {
        Sid    = "S3SilverReadWriteAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:AbortMultipartUpload"
        ]
        Resource = [
          var.silver_bucket_arn,
          "${var.silver_bucket_arn}/*"
        ]
      },
      {
        Sid    = "KMSDataKeyDecryptionAndEncryption"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [
          var.kms_key_arn
        ]
      }
    ]
  })
}

# ---
# AWS Glue Job Definition
# ---
resource "aws_glue_job" "this" {
  name              = var.job_name
  description       = var.description
  role_arn          = aws_iam_role.glue.arn
  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  timeout           = var.timeout
  max_retries       = var.max_retries

  command {
    name            = "glueetl"
    script_location = local.script_s3_uri
    python_version  = "3"
  }

  default_arguments = merge(
    {
      "--job-language"                     = "python"
      "--job-bookmark-option"              = "job-bookmark-disable"
      "--enable-continuous-cloudwatch-log" = "true"
      "--enable-continuous-log-filter"     = "true"
      "--enable-metrics"                   = "true"
      "--enable-spark-ui"                  = "true"
      "--spark-event-logs-path"            = "s3://${var.silver_bucket_id}/spark-events/"
      "--BRONZE_BUCKET"                    = var.bronze_bucket_id
      "--SILVER_BUCKET"                    = var.silver_bucket_id
    },
    var.default_arguments
  )

  tags = var.tags

  depends_on = [
    aws_s3_object.script,
    aws_iam_role_policy.glue_lake_access
  ]
}
