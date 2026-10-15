# ==============================================================================
# AWS Glue Catalog Database
# ==============================================================================
resource "aws_glue_catalog_database" "this" {
  name        = var.database_name
  description = var.description
  tags        = var.tags
}

# ==============================================================================
# Amazon Athena Workgroup
# ==============================================================================
resource "aws_athena_workgroup" "this" {
  name        = var.workgroup_name
  description = "Athena workgroup for ${var.database_name} analytics queries."
  state       = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.artifacts_bucket_id}/${var.athena_results_prefix}"

      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = var.kms_key_arn
      }
    }
  }

  tags = var.tags
}

# ==============================================================================
# External Table: ERCOT Hourly Demand Forecast
# ==============================================================================
resource "aws_glue_catalog_table" "ercot_demand_forecast" {
  name          = "ercot_demand_forecast"
  database_name = aws_glue_catalog_database.this.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "typeOfData"                = "file"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "storage.location.template" = "s3://${var.silver_bucket_id}/ercot_demand_forecast/year=$${year}/month=$${month}"
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${var.silver_bucket_id}/ercot_demand_forecast/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "period"
      type = "timestamp"
    }
    columns {
      name = "period_raw"
      type = "string"
    }
    columns {
      name = "respondent"
      type = "string"
    }
    columns {
      name = "respondent_name"
      type = "string"
    }
    columns {
      name = "forecast_type"
      type = "string"
    }
    columns {
      name = "forecast_type_name"
      type = "string"
    }
    columns {
      name = "value_mwh"
      type = "double"
    }
    columns {
      name = "value_units"
      type = "string"
    }
  }
}

# ==============================================================================
# External Table: ERCOT Generation by Fuel Type
# ==============================================================================
resource "aws_glue_catalog_table" "ercot_fuel_type" {
  name          = "ercot_fuel_type"
  database_name = aws_glue_catalog_database.this.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "typeOfData"                = "file"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "storage.location.template" = "s3://${var.silver_bucket_id}/ercot_fuel_type/year=$${year}/month=$${month}"
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${var.silver_bucket_id}/ercot_fuel_type/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "period"
      type = "timestamp"
    }
    columns {
      name = "period_raw"
      type = "string"
    }
    columns {
      name = "respondent"
      type = "string"
    }
    columns {
      name = "respondent_name"
      type = "string"
    }
    columns {
      name = "fuel_type"
      type = "string"
    }
    columns {
      name = "fuel_type_name"
      type = "string"
    }
    columns {
      name = "generation_mwh"
      type = "double"
    }
    columns {
      name = "value_units"
      type = "string"
    }
  }
}

# ==============================================================================
# External Table: Texas Monthly Retail Electricity Sales
# ==============================================================================
resource "aws_glue_catalog_table" "tx_retail_sales" {
  name          = "tx_retail_sales"
  database_name = aws_glue_catalog_database.this.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "typeOfData"                = "file"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "storage.location.template" = "s3://${var.silver_bucket_id}/tx_retail_sales/year=$${year}/month=$${month}"
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${var.silver_bucket_id}/tx_retail_sales/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "period"
      type = "string"
    }
    columns {
      name = "period_date"
      type = "date"
    }
    columns {
      name = "state_id"
      type = "string"
    }
    columns {
      name = "state_name"
      type = "string"
    }
    columns {
      name = "sector_id"
      type = "string"
    }
    columns {
      name = "sector_name"
      type = "string"
    }
    columns {
      name = "price_cents_per_kwh"
      type = "double"
    }
    columns {
      name = "sales_million_kwh"
      type = "double"
    }
    columns {
      name = "revenue_million_dollars"
      type = "double"
    }
    columns {
      name = "price_units"
      type = "string"
    }
    columns {
      name = "sales_units"
      type = "string"
    }
    columns {
      name = "revenue_units"
      type = "string"
    }
  }
}

# ==============================================================================
# External Table: Open-Meteo Texas Weather
# ==============================================================================
resource "aws_glue_catalog_table" "texas_weather" {
  name          = "texas_weather"
  database_name = aws_glue_catalog_database.this.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "parquet"
    "typeOfData"                = "file"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "storage.location.template" = "s3://${var.silver_bucket_id}/texas_weather/year=$${year}/month=$${month}"
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${var.silver_bucket_id}/texas_weather/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "time"
      type = "timestamp"
    }

    columns {
      name = "time_raw"
      type = "string"
    }

    columns {
      name = "temperature_2m_c"
      type = "double"
    }

    columns {
      name = "direct_normal_irradiance_w_m2"
      type = "double"
    }

    columns {
      name = "wind_speed_10m_km_h"
      type = "double"
    }
  }
}
