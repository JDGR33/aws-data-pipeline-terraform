"""Create four source-specific historical CSV tables from raw API payloads."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

DEFAULT_DATA_ROOT = Path("data/raw")
DEFAULT_OUTPUT_DIR = Path("data")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def payloads(data_root: Path, dataset: str) -> list[Path]:
    return sorted(data_root.glob(f"source=*/dataset={dataset}/**/payload.json"))


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def unique_eia_rows(
    data_root: Path, dataset: str, key_fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    rows: dict[tuple[str, ...], dict[str, Any]] = {}
    for path in payloads(data_root, dataset):
        for row in read_json(path).get("response", {}).get("data", []):
            key = tuple(str(row.get(field, "")) for field in key_fields)
            rows.setdefault(key, row)
    return list(rows.values())


def forecast_rows(data_root: Path) -> list[dict[str, Any]]:
    rows = unique_eia_rows(data_root, "ercot_demand_forecast", ("period",))
    return [
        {
            "period": row.get("period", ""),
            "respondent": row.get("respondent", ""),
            "respondent_name": row.get("respondent-name", ""),
            "forecast_type": row.get("type", ""),
            "forecast_type_name": row.get("type-name", ""),
            "value_mwh": row.get("value", ""),
            "value_units": row.get("value-units", ""),
        }
        for row in rows
    ]


def fuel_type_rows(data_root: Path) -> list[dict[str, Any]]:
    rows = unique_eia_rows(
        data_root, "ercot_fuel_type", ("period", "fueltype", "type-name")
    )
    return [
        {
            "period": row.get("period", ""),
            "respondent": row.get("respondent", ""),
            "respondent_name": row.get("respondent-name", ""),
            "fuel_type": row.get("fueltype", ""),
            "fuel_type_name": row.get("type-name", ""),
            "generation_mwh": row.get("value", ""),
            "value_units": row.get("value-units", ""),
        }
        for row in rows
    ]


def retail_rows(data_root: Path) -> list[dict[str, Any]]:
    rows = unique_eia_rows(
        data_root, "tx_retail_sales", ("period", "sectorid", "sectorName")
    )
    return [
        {
            "period": row.get("period", ""),
            "state_id": row.get("stateid", ""),
            "state_name": row.get("stateDescription", ""),
            "sector_id": row.get("sectorid", ""),
            "sector_name": row.get("sectorName", ""),
            "price_cents_per_kwh": row.get("price", ""),
            "sales_million_kwh": row.get("sales", ""),
            "revenue_million_dollars": row.get("revenue", ""),
            "price_units": row.get("price-units", ""),
            "sales_units": row.get("sales-units", ""),
            "revenue_units": row.get("revenue-units", ""),
        }
        for row in rows
    ]


def value_at(data: dict[str, list[Any]], field: str, index: int) -> Any:
    values = data.get(field, [])
    return values[index] if index < len(values) else ""


def weather_rows(data_root: Path) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in payloads(data_root, "texas_weather"):
        hourly = read_json(path).get("hourly", {})
        for index, time in enumerate(hourly.get("time", [])):
            rows.setdefault(
                time,
                {
                    "time": time,
                    "temperature_2m_c": value_at(hourly, "temperature_2m", index),
                    "direct_normal_irradiance_w_m2": value_at(
                        hourly, "direct_normal_irradiance", index
                    ),
                    "wind_speed_10m_km_h": value_at(hourly, "wind_speed_10m", index),
                },
            )
    return list(rows.values())


def write_table(
    output_dir: Path,
    filename: str,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / filename
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output}")


def main() -> None:
    arguments = parse_arguments()
    tables = [
        (
            "historical_ercot_demand_forecast.csv",
            forecast_rows(arguments.data_root),
            [
                "period",
                "respondent",
                "respondent_name",
                "forecast_type",
                "forecast_type_name",
                "value_mwh",
                "value_units",
            ],
        ),
        (
            "historical_ercot_fuel_type.csv",
            fuel_type_rows(arguments.data_root),
            [
                "period",
                "respondent",
                "respondent_name",
                "fuel_type",
                "fuel_type_name",
                "generation_mwh",
                "value_units",
            ],
        ),
        (
            "historical_tx_retail_sales.csv",
            retail_rows(arguments.data_root),
            [
                "period",
                "state_id",
                "state_name",
                "sector_id",
                "sector_name",
                "price_cents_per_kwh",
                "sales_million_kwh",
                "revenue_million_dollars",
                "price_units",
                "sales_units",
                "revenue_units",
            ],
        ),
        (
            "historical_texas_weather.csv",
            weather_rows(arguments.data_root),
            [
                "time",
                "temperature_2m_c",
                "direct_normal_irradiance_w_m2",
                "wind_speed_10m_km_h",
            ],
        ),
    ]
    for filename, rows, columns in tables:
        write_table(arguments.output_dir, filename, rows, columns)


if __name__ == "__main__":
    main()
