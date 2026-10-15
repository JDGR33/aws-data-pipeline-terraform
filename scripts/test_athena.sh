#!/usr/bin/env bash
# ==============================================================================
# Script: test_athena.sh
# Purpose: Execute Athena SQL test queries and display clean execution metrics
#          and tabular query results without AWS CLI metadata noise.
# Usage:   ./scripts/test_athena.sh [AWS_PROFILE]
# ==============================================================================

set -euo pipefail

PROFILE="${1:-dev}"
WORKGROUP="${ATHENA_WORKGROUP:-texas-data-pipeline-prod}"
DATABASE="${ATHENA_DATABASE:-texas_data_pipeline_prod_db}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Verify AWS authentication
if ! aws sts get-caller-identity --profile "${PROFILE}" >/dev/null 2>&1; then
    echo "❌ Error: AWS credentials for profile '${PROFILE}' are expired or invalid."
    echo "Run 'aws sso login --profile ${PROFILE}' to authenticate."
    exit 1
fi

# Function: Run query and print clean execution time + clean table
run_query() {
    local title="$1"
    local sql="$2"

    echo "================================================================================"
    echo "▶ ${title}"
    echo "================================================================================"
    echo "SQL: ${sql}"
    echo ""

    # Start query execution
    local query_id
    query_id=$(aws athena start-query-execution \
        --query-string "${sql}" \
        --work-group "${WORKGROUP}" \
        --query-execution-context Database="${DATABASE}" \
        --profile "${PROFILE}" \
        --region "${REGION}" \
        --output text \
        --query 'QueryExecutionId')

    # Poll status
    local status="QUEUED"
    while [[ "${status}" == "QUEUED" || "${status}" == "RUNNING" ]]; do
        sleep 1
        status=$(aws athena get-query-execution \
            --query-execution-id "${query_id}" \
            --profile "${PROFILE}" \
            --region "${REGION}" \
            --output text \
            --query 'QueryExecution.Status.State')
    done

    if [[ "${status}" != "SUCCEEDED" ]]; then
        local reason
        reason=$(aws athena get-query-execution \
            --query-execution-id "${query_id}" \
            --profile "${PROFILE}" \
            --region "${REGION}" \
            --output text \
            --query 'QueryExecution.Status.StateChangeReason')
        echo "❌ Query Failed: ${reason}"
        echo ""
        return 1
    fi

    # Print clean execution stats
    aws athena get-query-execution \
        --query-execution-id "${query_id}" \
        --profile "${PROFILE}" \
        --region "${REGION}" \
        --output json | python3 -c '
import sys, json
info = json.load(sys.stdin)["QueryExecution"]["Statistics"]
exec_sec = info.get("EngineExecutionTimeInMillis", 0) / 1000.0
bytes_val = info.get("DataScannedInBytes", 0)
kb_val = bytes_val / 1024.0
print(f"⏱️  Execution Time: {exec_sec:.2f}s | 📊 Data Scanned: {kb_val:.2f} KB ({bytes_val} bytes)")
'
    echo ""

    # Fetch results and format as clean text table
    aws athena get-query-results \
        --query-execution-id "${query_id}" \
        --profile "${PROFILE}" \
        --region "${REGION}" \
        --output json | python3 -c '
import sys, json

data = json.load(sys.stdin)
rows = data.get("ResultSet", {}).get("Rows", [])
if not rows:
    print("(No rows returned)")
    sys.exit(0)

# Extract column values
table = []
for row in rows:
    row_vals = [col.get("VarCharValue", "NULL") for col in row.get("Data", [])]
    table.append(row_vals)

if not table or not table[0]:
    print("(Empty result)")
    sys.exit(0)

# Calculate column widths
num_cols = len(table[0])
col_widths = []
for c in range(num_cols):
    max_w = max(len(str(table[r][c])) if c < len(table[r]) else 0 for r in range(len(table)))
    col_widths.append(max(max_w, 4))

# Print header and data rows
header = " | ".join(f"{table[0][c]:<{col_widths[c]}}" for c in range(num_cols))
separator = "-+-".join("-" * col_widths[c] for c in range(num_cols))

print(header)
print(separator)
for row in table[1:]:
    vals = [row[c] if c < len(row) else "" for c in range(num_cols)]
    print(" | ".join(f"{vals[c]:<{col_widths[c]}}" for c in range(num_cols)))
'
    echo ""
}

# ------------------------------------------------------------------------------
# Test Queries
# ------------------------------------------------------------------------------

run_query \
    "Test 1: Texas Weather Latest Measurements" \
    "SELECT time, temperature_2m_c, direct_normal_irradiance_w_m2, wind_speed_10m_km_h FROM ${DATABASE}.texas_weather ORDER BY time DESC LIMIT 5;"

run_query \
    "Test 2: ERCOT Demand Forecast Aggregates (Partition Pruned: year=2026, month=10)" \
    "SELECT year, month, count(*) AS hourly_records, min(value_mwh) AS min_demand, max(value_mwh) AS max_demand, round(avg(value_mwh), 2) AS avg_demand FROM ${DATABASE}.ercot_demand_forecast WHERE year = 2026 AND month = 10 GROUP BY year, month;"

run_query \
    "Test 3: Power Grid Demand vs. Weather Metrics (Cross-Dataset Join)" \
    "SELECT d.period, d.value_mwh AS ercot_demand_mwh, w.temperature_2m_c AS temp_c, w.direct_normal_irradiance_w_m2 AS solar_w_m2, w.wind_speed_10m_km_h AS wind_km_h FROM ${DATABASE}.ercot_demand_forecast d INNER JOIN ${DATABASE}.texas_weather w ON d.period = w.time WHERE d.year = 2026 AND d.month = 10 ORDER BY d.period ASC LIMIT 8;"
