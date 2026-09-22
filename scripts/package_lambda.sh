#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"

if [[ ! -x "${PYTHON}" ]]; then
    PYTHON="python3"
fi

exec "${PYTHON}" "${PROJECT_ROOT}/scripts/package_lambda.py" "$@"
