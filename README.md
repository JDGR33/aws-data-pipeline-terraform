# AWS Data Pipeline with Terraform

An evolving data-engineering project focused on collecting and preparing Texas energy and weather data with AWS-compatible infrastructure.

## Vision

Build a reliable, serverless data pipeline that turns public Texas energy and environmental APIs into well-structured, queryable datasets. The project is also a transparent record of learning how to design, provision, test, and document data infrastructure with Terraform.

## Abilities I Want to Show

- Infrastructure as Code with Terraform, developed locally with LocalStack and designed for AWS.
- Python data collection from public APIs, including EIA ERCOT data and Open-Meteo weather data.
- Data engineering practices such as schema validation, quality checks, partitioning, and Parquet-based analytical storage.
- Clear engineering documentation and a public record of the project's progress in [`log_book.md`](log_book.md).

## What This Project Is Not

- It is not a finished production platform.
- It is not a general-purpose data ingestion service.
- It does not yet provide a complete transformation, serving, or CI/CD layer.
- It does not store API secrets in the repository or treat local development as a substitute for production security and operations.

## Current State and Next Steps

The repository has its initial Terraform and LocalStack foundation, and the raw-data collector is working for Texas energy and weather datasets. It supports backfill and incremental deliveries, keeps source payloads unchanged, and records collection metadata separately.

## Collector Scripts

The collector uses the Python entry point [`collector/collect_raw_data.py`](collector/collect_raw_data.py) for one API request at a time. The Bash scripts provide repeatable workflows around that entry point.

### June Backfill

[`collector/backfill_june_2026.sh`](collector/backfill_june_2026.sh) is a fixed, reproducible backfill for June 2026. It invokes the Python collector once for each dataset:

- `ercot_fuel_type`: hourly EIA data from June 1 at 00:00 through June 30 at 23:00.
- `ercot_demand_forecast`: hourly EIA data over the same range.
- `texas_weather`: hourly Open-Meteo archive data for June 1 through June 30.
- `tx_retail_sales`: monthly EIA data for June 2026.

Run it locally with:

```bash
./collector/backfill_june_2026.sh
```

### Year Backfill

[`collector/backfill_year_2026.sh`](collector/backfill_year_2026.sh) loops over months and runs the same four requests for each month. Monthly batching keeps hourly EIA responses below the request limit and makes a large backfill restartable at a month boundary. When `YEAR` is the current year, it defaults to the last completed month; otherwise it defaults to December.

```bash
# January through the last completed month, written to data/raw/
./collector/backfill_year_2026.sh

# Collect a selected range of months
START_MONTH=03 END_MONTH=06 ./collector/backfill_year_2026.sh

# Upload the selected range to S3 or LocalStack
DESTINATION=s3 RAW_BUCKET=my-raw-bucket ./collector/backfill_year_2026.sh
```

Both scripts accept `PYTHON` to select the Python executable and `LOCAL_OUTPUT_DIR` to change the local destination. The year script also accepts `YEAR`, `START_MONTH`, `END_MONTH`, and `REQUEST_PAUSE_SECONDS`. The Python collector reads `EIA_API_KEY`, `RAW_BUCKET`, and `S3_ENDPOINT_URL` from the environment or `.env` as appropriate. Set `END_MONTH=12` once the complete calendar year is available; future dates cannot be collected from the archive APIs before then.

## How the Main Collector Works

[`collector/collect_raw_data.py`](collector/collect_raw_data.py) handles one dataset and one date range per process:

1. It loads `.env` values and validates the required `--dataset`, `--mode`, and optional date, destination, and storage arguments.
2. It resolves the date range. Backfills require explicit `--start` and `--end` values. Incremental runs default to the previous 24 completed UTC hours.
3. It builds the source-specific request. EIA requests select the ERCOT or Texas facets and use a maximum response length of 5,000 records. Open-Meteo uses the archive endpoint for backfills and the forecast endpoint for incremental collection.
4. It sends the request with a `requests` session that retries connection, read, rate-limit, and server failures. Responses use a 60-second timeout and retry HTTP 429, 500, 502, 503, and 504 errors.
5. It preserves the response body unchanged and creates metadata containing the source URL, non-secret request parameters, collection time, HTTP status, payload checksum, and payload path. The EIA API key is excluded from metadata.
6. It writes `payload.json` and `metadata.json` either below `data/raw/` or to the configured S3 bucket. Each request gets a UUID directory under a partition-style path, so later runs do not overwrite earlier raw deliveries.

The Python script does not combine pages or merge multiple responses. That is why the year backfill script batches by month; downstream processing can later read the individual immutable deliveries as a raw zone.

### First Historical Base CSV Tables

After collecting raw files locally, create the first combined historical base with:

```bash
.venv/bin/python collector/create_historical_base.py
```

This writes four independent CSV tables in `data/`:

- [`historical_ercot_demand_forecast.csv`](data/historical_ercot_demand_forecast.csv)
- [`historical_ercot_fuel_type.csv`](data/historical_ercot_fuel_type.csv)
- [`historical_tx_retail_sales.csv`](data/historical_tx_retail_sales.csv)
- [`historical_texas_weather.csv`](data/historical_texas_weather.csv)

The script follows the notebook’s normalization approach, preserves each source schema as its own table, and deduplicates overlapping raw deliveries. It does not join the sources together at this stage. This is an initial analytical base, not yet a production-grade refined dataset.

The next step is to define the raw-zone processing contract: read delivered objects from S3, validate and normalize each source schema, quarantine failures, and write refined Parquet datasets for analytical querying. Later stages will add quality gates, a serving layer, CI/CD, and deployment documentation.
