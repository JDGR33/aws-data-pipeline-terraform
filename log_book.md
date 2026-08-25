# AWS-DATA-PIPELINE-TERRAFORM

## 2026-07-28
* Installed AWS CLI
* Terraform is blcoked in Venezuela, should use VPN for all of this

## 2026-07-29
* Installed Terraform using a VPN and the Binary
* Installed npm to installed LocalStack
* Login with my LocalStack basic account in my  local pc 

## 2026-07-30
* Create Python .ven for pip installing terraform-local 
* I needed to use VPN for Terraform init. It makes calles to a registry
* Manage to run "tflocal apply" and got the all good prompt

## 2026-07-31
* Set Up AWS CLI for LocalStack
* Test AWS CLI and LocalStack S3

## 2026-08-01
* Research about posible data Sources

## 2026-06-03
* Testing the API Micro-Mobility & Spatial Feeds APIs

## 2026-08-05
* Testing the US Energy Information Administration (EIA v2 API) and OpenMeteo API

## 2026-08-22
* Objective: Give Shape to Data that can be extracted from the APIs

## Raw Data Collector

The pipeline begins when an upstream collector uploads data to the raw S3 bucket. The collector is deliberately independent from the ETL infrastructure: it calls public APIs, uploads each API response unchanged as `payload.json`, and writes a sibling `metadata.json` with non-secret request details and a SHA-256 checksum.

Install the collector dependencies in the active Python environment:

```bash
pip install -r collector/requirements.txt
```

Copy `.env.example` to `.env` and set `EIA_API_KEY`. The collector writes locally by default, preserving the same raw path layout it uses in S3. Use `--destination s3` to upload to the configured bucket.

```bash
.venv/bin/python collector/collect_raw_data.py --dataset texas_weather --mode backfill --start 2025-01-01 --end 2025-01-31
.venv/bin/python collector/collect_raw_data.py --dataset ercot_fuel_type --mode backfill --start 2025-01-01T00 --end 2025-01-31T23 --destination s3
.venv/bin/python collector/collect_raw_data.py --dataset ercot_demand_forecast --mode incremental --destination s3
.venv/bin/python collector/collect_raw_data.py --dataset tx_retail_sales --mode backfill --start 2024-01 --end 2025-12 --destination s3
```

For AWS, omit `S3_ENDPOINT_URL`, set `RAW_BUCKET` to the deployed bucket name, and authenticate Boto3 using the standard AWS credential chain. The ETL pipeline processes only these S3 objects; it never calls a live source API.

## 2026-08-24 - Texas Raw Data Collection

Defined Texas as the project data domain and implemented the upstream raw-data collector in `collector/collect_raw_data.py`. Collection remains outside the ETL pipeline: the collector is responsible for live public API requests, while the pipeline is responsible only for files delivered to the raw S3 bucket.

The collector supports these datasets:

* EIA hourly ERCOT generation by fuel type (`ercot_fuel_type`)
* EIA hourly ERCOT day-ahead demand forecast (`ercot_demand_forecast`)
* EIA monthly Texas retail electricity price, sales, and revenue (`tx_retail_sales`)
* Open-Meteo hourly Houston weather, including temperature, solar irradiance, and wind speed (`texas_weather`)

Both `backfill` and `incremental` deliveries are supported. A backfill requires an explicit start and end range; an incremental collection defaults to the previous 24 completed hours. Each delivery uses an immutable, partition-style path:

```text
source=<eia|open_meteo>/dataset=<dataset>/delivery_type=<backfill|incremental>/ingested_date=YYYY-MM-DD/request_id=<uuid>/
```

Every delivery contains the unmodified API response in `payload.json` and a `metadata.json` sidecar. Metadata records the source URL, non-secret request parameters, UTC collection time, HTTP status, payload SHA-256 checksum, and the intended raw S3 key. API keys are excluded from metadata.

Local output is the default development mode and writes to `data/raw/`, which is ignored by Git. This was validated using real Open-Meteo archive data and a real EIA ERCOT fuel-type response. When LocalStack or AWS is available, pass `--destination s3` to use the same object layout in the raw bucket.

Validation completed with the repository Python environment:

```bash
.venv/bin/python -m py_compile collector/collect_raw_data.py
.venv/bin/python collector/collect_raw_data.py --dataset texas_weather --mode backfill --start 2025-01-01 --end 2025-01-02
```

The next project stage is the raw-zone processing contract: read these objects from S3, validate and normalize each source schema, quarantine failures, and write refined Parquet datasets for analytical querying.