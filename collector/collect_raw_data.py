"""Collect EIA and Open-Meteo responses and upload immutable raw files to S3."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import boto3
import requests
from botocore.config import Config
from dotenv import load_dotenv

EIA_FUEL_TYPE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
EIA_REGION_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
EIA_RETAIL_SALES_URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        required=True,
        choices=(
            "ercot_fuel_type",
            "ercot_demand_forecast",
            "tx_retail_sales",
            "texas_weather",
        ),
    )
    parser.add_argument("--mode", required=True, choices=("backfill", "incremental"))
    parser.add_argument(
        "--start", help="Inclusive date or timestamp in ISO 8601 format."
    )
    parser.add_argument("--end", help="Inclusive date or timestamp in ISO 8601 format.")
    parser.add_argument("--destination", choices=("local", "s3"), default="local")
    parser.add_argument("--local-output-dir", default="data/raw")
    parser.add_argument("--bucket", default=os.getenv("RAW_BUCKET"))
    parser.add_argument("--s3-endpoint-url", default=os.getenv("S3_ENDPOINT_URL"))
    return parser.parse_args()


def resolve_date_range(arguments: argparse.Namespace) -> tuple[str, str]:
    if arguments.start and arguments.end:
        return arguments.start, arguments.end

    if arguments.mode == "backfill":
        raise ValueError("--start and --end are required when --mode is backfill")

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return (
        (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H"),
        (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H"),
    )


def build_request(
    dataset: str, mode: str, start: str, end: str
) -> tuple[str, dict[str, str]]:
    if dataset == "ercot_fuel_type":
        return EIA_FUEL_TYPE_URL, {
            "api_key": required_environment("EIA_API_KEY"),
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": "ERCO",
            "start": start,
            "end": end,
            "length": "5000",
        }
    if dataset == "ercot_demand_forecast":
        return EIA_REGION_URL, {
            "api_key": required_environment("EIA_API_KEY"),
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": "ERCO",
            "facets[type][]": "DF",
            "start": start,
            "end": end,
            "length": "5000",
        }
    if dataset == "tx_retail_sales":
        return EIA_RETAIL_SALES_URL, {
            "api_key": required_environment("EIA_API_KEY"),
            "frequency": "monthly",
            "data[0]": "price",
            "data[1]": "sales",
            "data[2]": "revenue",
            "facets[stateid][]": "TX",
            "start": start[:7],
            "end": end[:7],
            "length": "5000",
        }

    weather_url = (
        OPEN_METEO_ARCHIVE_URL if mode == "backfill" else OPEN_METEO_FORECAST_URL
    )
    return weather_url, {
        "latitude": "29.7604",
        "longitude": "-95.3698",
        "hourly": "temperature_2m,direct_normal_irradiance,wind_speed_10m",
        "timezone": "America/Chicago",
        "start_date": start[:10],
        "end_date": end[:10],
    }


def required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set in the environment or .env file")
    return value


def fetch_response(url: str, parameters: dict[str, str]) -> requests.Response:
    response = requests.get(url, params=parameters, timeout=60)
    response.raise_for_status()
    return response


def s3_client(endpoint_url: str | None) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        config=Config(s3={"addressing_style": "path"}),
    )


def response_paths(
    dataset: str,
    mode: str,
    collected_at: datetime,
    request_id: str,
) -> tuple[str, str]:
    prefix = (
        f"source={'eia' if dataset.startswith(('ercot', 'tx_')) else 'open_meteo'}/"
        f"dataset={dataset}/delivery_type={mode}/"
        f"ingested_date={collected_at:%Y-%m-%d}/request_id={request_id}"
    )
    return f"{prefix}/payload.json", f"{prefix}/metadata.json"


def response_metadata(
    url: str,
    parameters: dict[str, str],
    response: requests.Response,
    collected_at: datetime,
    payload_key: str,
) -> dict[str, str | dict[str, str] | int]:
    payload_hash = hashlib.sha256(response.content).hexdigest()
    return {
        "source_url": url,
        "request_parameters": {
            key: value for key, value in parameters.items() if key != "api_key"
        },
        "collected_at_utc": collected_at.isoformat(),
        "http_status": response.status_code,
        "payload_sha256": payload_hash,
        "payload_s3_key": payload_key,
    }


def upload_raw_response(
    client: Any,
    bucket: str,
    payload_key: str,
    metadata_key: str,
    metadata: dict[str, str | dict[str, str] | int],
    response: requests.Response,
) -> None:
    client.put_object(
        Bucket=bucket,
        Key=payload_key,
        Body=response.content,
        ContentType=response.headers.get("Content-Type", "application/json"),
    )
    client.put_object(
        Bucket=bucket,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def write_local_response(
    output_directory: str,
    payload_key: str,
    metadata_key: str,
    metadata: dict[str, str | dict[str, str] | int],
    response: requests.Response,
) -> tuple[Path, Path]:
    root = Path(output_directory)
    payload_path = root / payload_key
    metadata_path = root / metadata_key
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_bytes(response.content)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return payload_path, metadata_path


def main() -> None:
    load_dotenv()
    arguments = parse_arguments()
    if arguments.destination == "s3" and not arguments.bucket:
        raise RuntimeError("--bucket or RAW_BUCKET is required")

    start, end = resolve_date_range(arguments)
    url, parameters = build_request(arguments.dataset, arguments.mode, start, end)
    response = fetch_response(url, parameters)
    collected_at = datetime.now(UTC)
    payload_key, metadata_key = response_paths(
        arguments.dataset,
        arguments.mode,
        collected_at,
        str(uuid.uuid4()),
    )
    metadata = response_metadata(
        url,
        parameters,
        response,
        collected_at,
        payload_key,
    )
    if arguments.destination == "local":
        payload_path, metadata_path = write_local_response(
            arguments.local_output_dir, payload_key, metadata_key, metadata, response
        )
        print(f"Wrote {payload_path}")
        print(f"Wrote {metadata_path}")
        return

    upload_raw_response(
        s3_client(arguments.s3_endpoint_url),
        arguments.bucket,
        payload_key,
        metadata_key,
        metadata,
        response,
    )
    print(f"Uploaded s3://{arguments.bucket}/{payload_key}")
    print(f"Uploaded s3://{arguments.bucket}/{metadata_key}")


if __name__ == "__main__":
    main()
