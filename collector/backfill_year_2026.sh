#!/usr/bin/env bash

# Collect completed 2026 months for all four project datasets.
#
# Usage:
#   ./collector/backfill_year_2026.sh
#   END_MONTH=12 DESTINATION=s3 RAW_BUCKET=mybucket ./collector/backfill_year_2026.sh
#
# The default end month is the last completed month when YEAR is the current
# year, which avoids requesting future data from the archive APIs.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"
YEAR="${YEAR:-2026}"
START_MONTH="${START_MONTH:-01}"
DESTINATION="${DESTINATION:-local}"
LOCAL_OUTPUT_DIR="${LOCAL_OUTPUT_DIR:-${PROJECT_ROOT}/data/raw}"
REQUEST_PAUSE_SECONDS="${REQUEST_PAUSE_SECONDS:-1}"

if [[ "${YEAR}" == "$(date -u +%Y)" ]]; then
    END_MONTH="${END_MONTH:-$(date -u -d 'last month' +%m)}"
else
    END_MONTH="${END_MONTH:-12}"
fi

if [[ ! -x "${PYTHON}" ]]; then
    echo "Python executable not found or not executable: ${PYTHON}" >&2
    echo "Set PYTHON=/path/to/python or create the project virtual environment." >&2
    exit 1
fi

if [[ "${DESTINATION}" != "local" && "${DESTINATION}" != "s3" ]]; then
    echo "DESTINATION must be either local or s3; got: ${DESTINATION}" >&2
    exit 1
fi

if (( 10#${START_MONTH} < 1 || 10#${START_MONTH} > 12 )); then
    echo "START_MONTH must be between 01 and 12; got: ${START_MONTH}" >&2
    exit 1
fi

if (( 10#${END_MONTH} < 1 || 10#${END_MONTH} > 12 )); then
    echo "END_MONTH must be between 01 and 12; got: ${END_MONTH}" >&2
    exit 1
fi

if (( 10#${START_MONTH} > 10#${END_MONTH} )); then
    echo "START_MONTH must not be after END_MONTH" >&2
    exit 1
fi

start_month_number=$((10#${START_MONTH}))
end_month_number=$((10#${END_MONTH}))

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
    sleep "${REQUEST_PAUSE_SECONDS}"
}

for month_number in $(seq "${start_month_number}" "${end_month_number}"); do
    month="$(printf '%02d' "${month_number}")"
    month_start="${YEAR}-${month}-01"
    month_end="$(date -u -d "${month_start} +1 month -1 day" +%Y-%m-%d)"

    run_backfill "ercot_fuel_type" "${month_start}T00" "${month_end}T23"
    run_backfill "ercot_demand_forecast" "${month_start}T00" "${month_end}T23"
    run_backfill "texas_weather" "${month_start}" "${month_end}"
    run_backfill "tx_retail_sales" "${YEAR}-${month}" "${YEAR}-${month}"
done

echo "${YEAR} backfill completed through ${YEAR}-${END_MONTH}."