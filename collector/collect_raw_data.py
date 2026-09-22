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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

EIA_FUEL_TYPE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
EIA_REGION_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
EIA_RETAIL_SALES_URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

SUPPORTED_DATASETS = (
    "ercot_fuel_type",
    "ercot_demand_forecast",
    "tx_retail_sales",
    "texas_weather",
)


def parse_arguments() -> argparse.Namespace:
    """Parse the command-line options used to collect one dataset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        required=True,
        choices=SUPPORTED_DATASETS,
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


def resolve_date_range(
    mode_or_arguments: str | argparse.Namespace,
    start: str | None = None,
    end: str | None = None,
) -> tuple[str, str]:
    """Return the requested inclusive range, or the latest completed 23 hours.

    Backfills must be explicit so a large historical request cannot happen by
    accident. Incremental runs default to the period from 24 hours ago through
    the last completed hour.
    """
    if isinstance(mode_or_arguments, argparse.Namespace):
        mode = mode_or_arguments.mode
        start = mode_or_arguments.start
        end = mode_or_arguments.end
    else:
        mode = mode_or_arguments

    if start and end:
        return start, end

    if mode == "backfill":
        raise ValueError("start and end are required when mode is backfill")

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return (
        (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H"),
        (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H"),
    )


def build_request(
    dataset: str, mode: str, start: str, end: str
) -> tuple[str, dict[str, str]]:
    """Build the API URL and query parameters for a supported dataset."""
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

    # Open-Meteo uses its archive endpoint for historical backfills and its
    # forecast endpoint for recent incremental data.
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
    """Read a required environment variable and fail with a useful message."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set in the environment or .env file")
    return value


def fetch_response(url: str, parameters: dict[str, str]) -> requests.Response:
    """Fetch an API response, retrying transient network and server errors."""
    retry_policy = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_policy))
    session.mount("http://", HTTPAdapter(max_retries=retry_policy))
    response = session.get(url, params=parameters, timeout=60)
    response.raise_for_status()
    return response


def s3_client(endpoint_url: str | None) -> Any:
    """Create an S3 client, optionally targeting a local S3-compatible service."""
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
    """Create partitioned object keys for the payload and its metadata.

    Every request gets a UUID directory, so a later collection never
    overwrites an earlier raw response.
    """
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
    """Build provenance metadata without storing the EIA API key."""
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
    """Upload the response bytes and JSON provenance record to S3."""
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
    """Write the response bytes and JSON provenance record under a local root."""
    root = Path(output_directory)
    payload_path = root / payload_key
    metadata_path = root / metadata_key
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_bytes(response.content)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return payload_path, metadata_path


def collect_dataset(
    dataset: str,
    mode: str,
    start: str | None = None,
    end: str | None = None,
    destination: str = "local",
    local_output_dir: str = "data/raw",
    bucket: str | None = None,
    s3_endpoint_url: str | None = None,
) -> dict[str, Any]:
    """Run one collection request and persist its immutable raw result.

    Returns execution summary and paths/keys of written artifacts.
    """
    if dataset not in SUPPORTED_DATASETS:
        raise ValueError(
            f"Unsupported dataset '{dataset}'. Must be one of {SUPPORTED_DATASETS}"
        )
    if destination not in ("local", "s3"):
        raise ValueError(f"Destination must be 'local' or 's3'; got '{destination}'")

    if destination == "s3":
        bucket = bucket or os.getenv("RAW_BUCKET")
        if not bucket:
            raise RuntimeError("bucket or RAW_BUCKET is required when destination is s3")
        s3_endpoint_url = s3_endpoint_url or os.getenv("S3_ENDPOINT_URL")

    resolved_start, resolved_end = resolve_date_range(mode, start, end)
    url, parameters = build_request(dataset, mode, resolved_start, resolved_end)

    # Keep the original response bytes so the stored payload matches exactly
    # what the upstream service returned; metadata is generated alongside it.
    response = fetch_response(url, parameters)
    collected_at = datetime.now(UTC)
    request_id = str(uuid.uuid4())
    payload_key, metadata_key = response_paths(
        dataset,
        mode,
        collected_at,
        request_id,
    )
    metadata = response_metadata(
        url,
        parameters,
        response,
        collected_at,
        payload_key,
    )

    if destination == "local":
        payload_path, metadata_path = write_local_response(
            local_output_dir, payload_key, metadata_key, metadata, response
        )
        return {
            "dataset": dataset,
            "mode": mode,
            "status": "success",
            "destination": "local",
            "start": resolved_start,
            "end": resolved_end,
            "request_id": request_id,
            "payload_path": str(payload_path),
            "metadata_path": str(metadata_path),
            "bytes": len(response.content),
            "http_status": response.status_code,
        }

    client = s3_client(s3_endpoint_url)
    upload_raw_response(
        client,
        bucket,
        payload_key,
        metadata_key,
        metadata,
        response,
    )
    return {
        "dataset": dataset,
        "mode": mode,
        "status": "success",
        "destination": "s3",
        "start": resolved_start,
        "end": resolved_end,
        "request_id": request_id,
        "bucket": bucket,
        "payload_key": payload_key,
        "metadata_key": metadata_key,
        "bytes": len(response.content),
        "http_status": response.status_code,
    }


def main() -> None:
    """Run one collection request and persist its immutable raw result."""
    load_dotenv()
    arguments = parse_arguments()
    result = collect_dataset(
        dataset=arguments.dataset,
        mode=arguments.mode,
        start=arguments.start,
        end=arguments.end,
        destination=arguments.destination,
        local_output_dir=arguments.local_output_dir,
        bucket=arguments.bucket,
        s3_endpoint_url=arguments.s3_endpoint_url,
    )
    if result["destination"] == "local":
        print(f"Wrote {result['payload_path']}")
        print(f"Wrote {result['metadata_path']}")
    else:
        print(f"Uploaded s3://{result['bucket']}/{result['payload_key']}")
        print(f"Uploaded s3://{result['bucket']}/{result['metadata_key']}")


if __name__ == "__main__":
    main()
