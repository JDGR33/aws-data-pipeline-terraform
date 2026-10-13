"""AWS Glue PySpark ETL Job: Transform Bronze Raw Data into Silver Refined Parquet.

This job reads raw JSON payloads from the Bronze S3 zone, enforces schema
contracts, normalizes timestamps, casts numeric measurements, deduplicates
records by business keys, routes malformed rows to quarantine, and writes
optimized, partitioned Snappy Parquet files to the Silver S3 zone.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    StringType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("glue_transform_raw_to_refined")
logger.setLevel(logging.INFO)

# Detect AWS Glue runtime environment
try:
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions

    IS_GLUE = True
except ImportError:
    IS_GLUE = False

SUPPORTED_DATASETS = (
    "ercot_demand_forecast",
    "ercot_fuel_type",
    "tx_retail_sales",
    "texas_weather",
)


def parse_arguments() -> dict[str, str]:
    """Parse execution arguments from AWS Glue or CLI fallback."""
    required_args = ["JOB_NAME", "BRONZE_BUCKET", "SILVER_BUCKET"]
    optional_args = ["DATASET"]

    if IS_GLUE:
        # Resolve only arguments present in sys.argv to prevent KeyError
        args_to_resolve = list(required_args)
        for opt in optional_args:
            if f"--{opt}" in sys.argv:
                args_to_resolve.append(opt)

        resolved = getResolvedOptions(sys.argv, args_to_resolve)
        return {
            "JOB_NAME": resolved["JOB_NAME"],
            "BRONZE_BUCKET": resolved["BRONZE_BUCKET"],
            "SILVER_BUCKET": resolved["SILVER_BUCKET"],
            "DATASET": resolved.get("DATASET", "all"),
        }
    else:
        import argparse

        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--JOB_NAME", default="local_glue_job")
        parser.add_argument("--BRONZE_BUCKET", required=True)
        parser.add_argument("--SILVER_BUCKET", required=True)
        parser.add_argument("--DATASET", default="all", choices=["all", *SUPPORTED_DATASETS])
        parsed, _ = parser.parse_known_args()
        return vars(parsed)


def init_spark() -> tuple[SparkSession, Any]:
    """Initialize SparkSession and optional AWS Glue Job context."""
    if IS_GLUE:
        glue_context = GlueContext(SparkSession.builder.getOrCreate().sparkContext)
        spark = glue_context.spark_session
        job = Job(glue_context)
        return spark, job
    else:
        spark = (
            SparkSession.builder.appName("LocalGlueTransform")
            .config("spark.sql.session.timeZone", "UTC")
            .getOrCreate()
        )
        return spark, None


def write_partitioned_parquet(
    df: DataFrame,
    output_path: str,
    partition_cols: list[str],
    mode: str = "overwrite",
) -> None:
    """Write DataFrame to S3 using Snappy-compressed Parquet with dynamic partitions."""
    logger.info("Writing %d partitioned Parquet records to: %s", df.count(), output_path)
    df.write.mode(mode).partitionBy(*partition_cols).parquet(output_path)


def write_quarantine(df: DataFrame, quarantine_path: str) -> None:
    """Write invalid or malformed records to Silver quarantine prefix."""
    if df.take(1):
        logger.warning("Writing invalid records to quarantine: %s", quarantine_path)
        df.write.mode("append").parquet(quarantine_path)


def transform_ercot_demand_forecast(
    spark: SparkSession, bronze_bucket: str, silver_bucket: str
) -> None:
    """Transform ERCOT day-ahead demand forecast raw JSON into Silver Parquet."""
    input_path = f"s3://{bronze_bucket}/source=eia/dataset=ercot_demand_forecast/**/payload.json"
    logger.info("Processing ercot_demand_forecast from %s", input_path)

    raw_df = spark.read.json(input_path)
    if "response" not in raw_df.columns:
        logger.warning("Missing 'response' column in payload. Skipping ercot_demand_forecast.")
        return

    exploded_df = raw_df.select(F.explode("response.data").alias("record"))

    # Flexible timestamp parsing covering ISO 8601 variations
    period_ts = F.coalesce(
        F.to_timestamp(F.col("record.period"), "yyyy-MM-dd'T'HH:mm:ss"),
        F.to_timestamp(F.col("record.period"), "yyyy-MM-dd'T'HH:mm"),
        F.to_timestamp(F.col("record.period"), "yyyy-MM-dd'T'HH"),
        F.to_timestamp(F.col("record.period")),
    )

    parsed_df = exploded_df.select(
        period_ts.alias("period"),
        F.col("record.period").cast(StringType()).alias("period_raw"),
        F.col("record.respondent").cast(StringType()).alias("respondent"),
        F.col("record.`respondent-name`").cast(StringType()).alias("respondent_name"),
        F.col("record.type").cast(StringType()).alias("forecast_type"),
        F.col("record.`type-name`").cast(StringType()).alias("forecast_type_name"),
        F.col("record.value").cast(DoubleType()).alias("value_mwh"),
        F.col("record.`value-units`").cast(StringType()).alias("value_units"),
    )

    # Derive temporal partition keys
    partitioned_df = (
        parsed_df.withColumn("year", F.year("period"))
        .withColumn("month", F.month("period"))
    )

    # Deduplicate on primary key (period)
    deduped_df = partitioned_df.dropDuplicates(["period"])

    # Quality Gate
    is_valid = F.col("period").isNotNull() & F.col("value_mwh").isNotNull()
    clean_df = deduped_df.filter(is_valid)
    quarantine_df = deduped_df.filter(~is_valid)

    # Output to Silver and Quarantine
    silver_path = f"s3://{silver_bucket}/ercot_demand_forecast/"
    quarantine_path = f"s3://{silver_bucket}/quarantine/ercot_demand_forecast/"

    write_partitioned_parquet(clean_df, silver_path, ["year", "month"])
    write_quarantine(quarantine_df, quarantine_path)


def transform_ercot_fuel_type(
    spark: SparkSession, bronze_bucket: str, silver_bucket: str
) -> None:
    """Transform ERCOT generation by fuel type raw JSON into Silver Parquet."""
    input_path = f"s3://{bronze_bucket}/source=eia/dataset=ercot_fuel_type/**/payload.json"
    logger.info("Processing ercot_fuel_type from %s", input_path)

    raw_df = spark.read.json(input_path)
    if "response" not in raw_df.columns:
        logger.warning("Missing 'response' column in payload. Skipping ercot_fuel_type.")
        return

    exploded_df = raw_df.select(F.explode("response.data").alias("record"))

    period_ts = F.coalesce(
        F.to_timestamp(F.col("record.period"), "yyyy-MM-dd'T'HH:mm:ss"),
        F.to_timestamp(F.col("record.period"), "yyyy-MM-dd'T'HH:mm"),
        F.to_timestamp(F.col("record.period"), "yyyy-MM-dd'T'HH"),
        F.to_timestamp(F.col("record.period")),
    )

    parsed_df = exploded_df.select(
        period_ts.alias("period"),
        F.col("record.period").cast(StringType()).alias("period_raw"),
        F.col("record.respondent").cast(StringType()).alias("respondent"),
        F.col("record.`respondent-name`").cast(StringType()).alias("respondent_name"),
        F.col("record.fueltype").cast(StringType()).alias("fuel_type"),
        F.col("record.`type-name`").cast(StringType()).alias("fuel_type_name"),
        F.col("record.value").cast(DoubleType()).alias("generation_mwh"),
        F.col("record.`value-units`").cast(StringType()).alias("value_units"),
    )

    partitioned_df = (
        parsed_df.withColumn("year", F.year("period"))
        .withColumn("month", F.month("period"))
    )

    # Deduplicate on composite primary key
    deduped_df = partitioned_df.dropDuplicates(["period", "fuel_type", "fuel_type_name"])

    # Quality Gate (note: generation_mwh can be negative for battery storage charging)
    is_valid = (
        F.col("period").isNotNull()
        & F.col("fuel_type").isNotNull()
        & F.col("generation_mwh").isNotNull()
    )
    clean_df = deduped_df.filter(is_valid)
    quarantine_df = deduped_df.filter(~is_valid)

    silver_path = f"s3://{silver_bucket}/ercot_fuel_type/"
    quarantine_path = f"s3://{silver_bucket}/quarantine/ercot_fuel_type/"

    write_partitioned_parquet(clean_df, silver_path, ["year", "month"])
    write_quarantine(quarantine_df, quarantine_path)


def transform_tx_retail_sales(
    spark: SparkSession, bronze_bucket: str, silver_bucket: str
) -> None:
    """Transform Texas monthly electricity retail sales raw JSON into Silver Parquet."""
    input_path = f"s3://{bronze_bucket}/source=eia/dataset=tx_retail_sales/**/payload.json"
    logger.info("Processing tx_retail_sales from %s", input_path)

    raw_df = spark.read.json(input_path)
    if "response" not in raw_df.columns:
        logger.warning("Missing 'response' column in payload. Skipping tx_retail_sales.")
        return

    exploded_df = raw_df.select(F.explode("response.data").alias("record"))

    # Parse monthly period (e.g. '2026-06') to DateType (first of month)
    period_date = F.coalesce(
        F.to_date(F.concat(F.col("record.period"), F.lit("-01")), "yyyy-MM-dd"),
        F.to_date(F.col("record.period")),
    )

    parsed_df = exploded_df.select(
        F.col("record.period").cast(StringType()).alias("period"),
        period_date.alias("period_date"),
        F.col("record.stateid").cast(StringType()).alias("state_id"),
        F.col("record.stateDescription").cast(StringType()).alias("state_name"),
        F.col("record.sectorid").cast(StringType()).alias("sector_id"),
        F.col("record.sectorName").cast(StringType()).alias("sector_name"),
        F.col("record.price").cast(DoubleType()).alias("price_cents_per_kwh"),
        F.col("record.sales").cast(DoubleType()).alias("sales_million_kwh"),
        F.col("record.revenue").cast(DoubleType()).alias("revenue_million_dollars"),
        F.col("record.`price-units`").cast(StringType()).alias("price_units"),
        F.col("record.`sales-units`").cast(StringType()).alias("sales_units"),
        F.col("record.`revenue-units`").cast(StringType()).alias("revenue_units"),
    )

    partitioned_df = (
        parsed_df.withColumn("year", F.year("period_date"))
        .withColumn("month", F.month("period_date"))
    )

    # Deduplicate on composite primary key
    deduped_df = partitioned_df.dropDuplicates(["period", "sector_id", "sector_name"])

    # Quality Gate
    is_valid = F.col("period").isNotNull() & F.col("sector_id").isNotNull()
    clean_df = deduped_df.filter(is_valid)
    quarantine_df = deduped_df.filter(~is_valid)

    silver_path = f"s3://{silver_bucket}/tx_retail_sales/"
    quarantine_path = f"s3://{silver_bucket}/quarantine/tx_retail_sales/"

    write_partitioned_parquet(clean_df, silver_path, ["year", "month"])
    write_quarantine(quarantine_df, quarantine_path)


def transform_texas_weather(
    spark: SparkSession, bronze_bucket: str, silver_bucket: str
) -> None:
    """Transform Open-Meteo Texas weather raw JSON into Silver Parquet."""
    input_path = f"s3://{bronze_bucket}/source=open_meteo/dataset=texas_weather/**/payload.json"
    logger.info("Processing texas_weather from %s", input_path)

    raw_df = spark.read.json(input_path)
    if "hourly" not in raw_df.columns:
        logger.warning("Missing 'hourly' column in payload. Skipping texas_weather.")
        return

    # Zip columnar parallel arrays into a single array of structs, then explode
    zipped_df = raw_df.select(
        F.explode(
            F.arrays_zip(
                F.col("hourly.time"),
                F.col("hourly.temperature_2m"),
                F.col("hourly.direct_normal_irradiance"),
                F.col("hourly.wind_speed_10m"),
            )
        ).alias("z")
    )

    # Resolve struct fields supporting both named struct fields and positional indices
    time_raw = F.coalesce(F.col("z.time"), F.col("z.0"))
    temp_raw = F.coalesce(F.col("z.temperature_2m"), F.col("z.1"))
    dni_raw = F.coalesce(F.col("z.direct_normal_irradiance"), F.col("z.2"))
    wind_raw = F.coalesce(F.col("z.wind_speed_10m"), F.col("z.3"))

    time_ts = F.coalesce(
        F.to_timestamp(time_raw, "yyyy-MM-dd'T'HH:mm"),
        F.to_timestamp(time_raw, "yyyy-MM-dd'T'HH:mm:ss"),
        F.to_timestamp(time_raw),
    )

    parsed_df = zipped_df.select(
        time_ts.alias("time"),
        time_raw.cast(StringType()).alias("time_raw"),
        temp_raw.cast(DoubleType()).alias("temperature_2m_c"),
        dni_raw.cast(DoubleType()).alias("direct_normal_irradiance_w_m2"),
        wind_raw.cast(DoubleType()).alias("wind_speed_10m_km_h"),
    )

    partitioned_df = (
        parsed_df.withColumn("year", F.year("time"))
        .withColumn("month", F.month("time"))
    )

    # Deduplicate on primary key (time)
    deduped_df = partitioned_df.dropDuplicates(["time"])

    # Quality Gate
    is_valid = F.col("time").isNotNull() & F.col("temperature_2m_c").isNotNull()
    clean_df = deduped_df.filter(is_valid)
    quarantine_df = deduped_df.filter(~is_valid)

    silver_path = f"s3://{silver_bucket}/texas_weather/"
    quarantine_path = f"s3://{silver_bucket}/quarantine/texas_weather/"

    write_partitioned_parquet(clean_df, silver_path, ["year", "month"])
    write_quarantine(quarantine_df, quarantine_path)


def main() -> None:
    """Main execution flow for Glue PySpark transformation."""
    args = parse_arguments()
    job_name = args["JOB_NAME"]
    bronze_bucket = args["BRONZE_BUCKET"]
    silver_bucket = args["SILVER_BUCKET"]
    dataset = args["DATASET"]

    logger.info("Initializing Glue PySpark Job: %s", job_name)
    logger.info("Bronze Bucket: %s | Silver Bucket: %s | Dataset: %s", bronze_bucket, silver_bucket, dataset)

    spark, job = init_spark()
    if job:
        job.init(job_name, args)

    # Enable dynamic partition overwrite so reruns cleanly update touched partitions
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    transformation_map = {
        "ercot_demand_forecast": transform_ercot_demand_forecast,
        "ercot_fuel_type": transform_ercot_fuel_type,
        "tx_retail_sales": transform_tx_retail_sales,
        "texas_weather": transform_texas_weather,
    }

    datasets_to_process = (
        list(SUPPORTED_DATASETS) if dataset == "all" else [dataset]
    )

    for ds in datasets_to_process:
        transform_fn = transformation_map.get(ds)
        if transform_fn:
            logger.info(">>> Starting ETL for dataset: %s", ds)
            try:
                transform_fn(spark, bronze_bucket, silver_bucket)
                logger.info(">>> Completed ETL for dataset: %s", ds)
            except Exception as exc:
                logger.exception("Failed processing dataset %s: %s", ds, exc)
                raise
        else:
            logger.warning("Unrecognized dataset: %s. Skipping.", ds)

    if job:
        job.commit()
    logger.info("All ETL transformations completed successfully.")


if __name__ == "__main__":
    main()
