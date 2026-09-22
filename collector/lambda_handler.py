"""AWS Lambda entry point for collecting Texas energy and weather raw data."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

# Support both flat Lambda package root and repository-level module imports
try:
    from collect_raw_data import SUPPORTED_DATASETS, collect_dataset
except ImportError:
    from collector.collect_raw_data import SUPPORTED_DATASETS, collect_dataset

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def lambda_handler(event: dict[str, Any] | None, context: Any = None) -> dict[str, Any]:
    """Execute raw data collection triggered by EventBridge or manual invocation.

    Event Parameters (all optional):
        dataset (str): Single dataset name to collect.
        datasets (list[str]): Multiple datasets to collect sequentially.
        mode (str): Collection mode, either 'incremental' (default) or 'backfill'.
        start (str): Start date/hour (ISO 8601).
        end (str): End date/hour (ISO 8601).
        destination (str): 's3' (default in Lambda) or 'local'.
        bucket (str): Target S3 bucket name (defaults to RAW_BUCKET env var).
        s3_endpoint_url (str): Optional S3 endpoint for LocalStack.
    """
    event = event or {}
    logger.info("Received event: %s", json.dumps(event))

    mode = event.get("mode", "incremental")
    start = event.get("start")
    end = event.get("end")
    destination = event.get("destination", os.getenv("DESTINATION", "s3"))
    bucket = event.get("bucket", os.getenv("RAW_BUCKET"))
    s3_endpoint_url = event.get("s3_endpoint_url", os.getenv("S3_ENDPOINT_URL"))
    local_output_dir = event.get(
        "local_output_dir", os.getenv("LOCAL_OUTPUT_DIR", "data/raw")
    )

    # Resolve target datasets:
    # 1. Single dataset specified
    # 2. Explicit list of datasets specified
    # 3. Default to all supported datasets (standard EventBridge schedule)
    if event.get("dataset"):
        target_datasets = [event["dataset"]]
    elif event.get("datasets"):
        target_datasets = list(event["datasets"])
    else:
        logger.info(
            "No specific dataset requested; defaulting to all supported datasets"
        )
        target_datasets = list(SUPPORTED_DATASETS)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for dataset in target_datasets:
        logger.info("Starting collection for dataset: %s (mode: %s)", dataset, mode)
        try:
            result = collect_dataset(
                dataset=dataset,
                mode=mode,
                start=start,
                end=end,
                destination=destination,
                local_output_dir=local_output_dir,
                bucket=bucket,
                s3_endpoint_url=s3_endpoint_url,
            )
            results.append(result)
            logger.info(
                "Successfully collected %s: %s bytes written to %s",
                dataset,
                result.get("bytes"),
                result.get("payload_key") or result.get("payload_path"),
            )
        except Exception as exc:
            logger.exception("Failed to collect dataset %s: %s", dataset, exc)
            errors.append({"dataset": dataset, "error": str(exc)})

    response_body = {
        "timestamp": datetime.now(UTC).isoformat(),
        "mode": mode,
        "processed_count": len(results),
        "results": results,
    }

    if errors:
        response_body["errors"] = errors
        logger.error("Lambda execution completed with %d error(s)", len(errors))
        # Raising an exception allows AWS Lambda / EventBridge metrics and DLQs
        # to record the invocation failure.
        raise RuntimeError(
            f"Collection finished with {len(errors)} error(s): {json.dumps(errors)}"
        )

    logger.info("Lambda execution succeeded for all %d dataset(s)", len(results))
    return {
        "statusCode": 200,
        "body": response_body,
    }


if __name__ == "__main__":
    # Local debugging convenience
    import sys

    logging.basicConfig(level=logging.INFO)
    test_event = {"dataset": "texas_weather", "destination": "local"}
    if len(sys.argv) > 1:
        test_event["dataset"] = sys.argv[1]
    res = lambda_handler(test_event)
    print(json.dumps(res, indent=2))
