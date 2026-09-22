"""Unit tests for the raw data collector and Lambda handler."""

import argparse
import unittest
from unittest.mock import MagicMock, patch

from collector.collect_raw_data import (
    SUPPORTED_DATASETS,
    collect_dataset,
    resolve_date_range,
)
from collector.lambda_handler import lambda_handler


class TestCollector(unittest.TestCase):
    def test_resolve_date_range_explicit(self) -> None:
        start, end = resolve_date_range("incremental", "2026-06-01T00", "2026-06-01T23")
        self.assertEqual(start, "2026-06-01T00")
        self.assertEqual(end, "2026-06-01T23")

    def test_resolve_date_range_namespace(self) -> None:
        args = argparse.Namespace(mode="backfill", start="2026-01-01", end="2026-01-31")
        start, end = resolve_date_range(args)
        self.assertEqual(start, "2026-01-01")
        self.assertEqual(end, "2026-01-31")

    def test_resolve_date_range_backfill_missing_dates(self) -> None:
        with self.assertRaises(ValueError):
            resolve_date_range("backfill")

    def test_resolve_date_range_incremental_default(self) -> None:
        start, end = resolve_date_range("incremental")
        self.assertRegex(start, r"^\d{4}-\d{2}-\d{2}T\d{2}$")
        self.assertRegex(end, r"^\d{4}-\d{2}-\d{2}T\d{2}$")

    def test_collect_dataset_invalid_dataset(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            collect_dataset("unknown_dataset", "incremental")
        self.assertIn("Unsupported dataset", str(ctx.exception))

    def test_collect_dataset_invalid_destination(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            collect_dataset("ercot_fuel_type", "incremental", destination="ftp")
        self.assertIn("Destination must be 'local' or 's3'", str(ctx.exception))

    def test_collect_dataset_s3_missing_bucket(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                collect_dataset("ercot_fuel_type", "incremental", destination="s3")
            self.assertIn("RAW_BUCKET is required", str(ctx.exception))


class TestLambdaHandler(unittest.TestCase):
    @patch("collector.lambda_handler.collect_dataset")
    def test_lambda_handler_single_dataset(self, mock_collect: MagicMock) -> None:
        mock_collect.return_value = {
            "dataset": "ercot_demand_forecast",
            "status": "success",
            "destination": "s3",
            "bucket": "test-bucket",
            "payload_key": "raw/payload.json",
            "metadata_key": "raw/metadata.json",
            "bytes": 500,
        }

        event = {"dataset": "ercot_demand_forecast", "mode": "incremental"}
        response = lambda_handler(event)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["processed_count"], 1)
        self.assertEqual(response["body"]["results"][0]["dataset"], "ercot_demand_forecast")
        mock_collect.assert_called_once()

    @patch("collector.lambda_handler.collect_dataset")
    def test_lambda_handler_default_all_datasets(self, mock_collect: MagicMock) -> None:
        mock_collect.return_value = {"status": "success"}

        response = lambda_handler({})

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["processed_count"], len(SUPPORTED_DATASETS))
        self.assertEqual(mock_collect.call_count, len(SUPPORTED_DATASETS))

    @patch("collector.lambda_handler.collect_dataset")
    def test_lambda_handler_error_raises_runtime_error(self, mock_collect: MagicMock) -> None:
        mock_collect.side_effect = Exception("API connection timed out")

        with self.assertRaises(RuntimeError) as ctx:
            lambda_handler({"dataset": "texas_weather"})
        self.assertIn("Collection finished with 1 error(s)", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
