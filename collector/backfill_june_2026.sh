#!/usr/bin/env bash

# Collect the four project datasets for June 2026.
#
# Usage:
#   ./collector/backfill_june_2026.sh
#   DESTINATION=s3 RAW_BUCKET=mybucket ./collector/backfill_june_2026.sh
#
# Local collection is the default. For S3 or LocalStack, set DESTINATION=s3
# and provide the same environment variables used by collect_raw_data.py.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"
DESTINATION="${DESTINATION:-local}"
LOCAL_OUTPUT_DIR="${LOCAL_OUTPUT_DIR:-${PROJECT_ROOT}/data/raw}"

if [[ ! -x "${PYTHON}" ]]; then
    echo "Python executable not found or not executable: ${PYTHON}" >&2
    echo "Set PYTHON=/path/to/python or create the project virtual environment." >&2
    exit 1
fi

if [[ "${DESTINATION}" != "local" && "${DESTINATION}" != "s3" ]]; then
    echo "DESTINATION must be either local or s3; got: ${DESTINATION}" >&2
    exit 1
fi

collector=(
    "${PYTHON}"
    "${PROJECT_ROOT}/collector/collect_raw_data.py"
)

run_backfill() {
    local dataset="$1"
    local start="$2"
    local end="$3"

    echo "Collecting ${dataset}: ${start} through ${end} (${DESTINATION})"
    "${collector[@]}" \
        --dataset "${dataset}" \
        --mode backfill \
        --start "${start}" \
        --end "${end}" \
        --destination "${DESTINATION}" \
        --local-output-dir "${LOCAL_OUTPUT_DIR}"
}

# Hourly datasets use an inclusive timestamp range covering the complete month.
run_backfill "ercot_fuel_type" "2026-06-01T00" "2026-06-30T23"
run_backfill "ercot_demand_forecast" "2026-06-01T00" "2026-06-30T23"
run_backfill "texas_weather" "2026-06-01" "2026-06-30"

# Retail sales is a monthly EIA dataset, so month precision is sufficient.
run_backfill "tx_retail_sales" "2026-06" "2026-06"

echo "June 2026 backfill completed successfully."