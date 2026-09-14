#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

printf '\n[Step 03] DFT baseline — workstation environment audit\n'
printf '[Step 03] Repository: %s\n' "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN was not found in PATH." >&2
  exit 10
fi

mkdir -p outputs logs

LOG_FILE="logs/03_dft_environment.log"
echo "[Step 03] Auditing available DFT executables, MPI, CPU/RAM, and GPU visibility."
"$PYTHON_BIN" scripts/03_check_dft_environment.py 2>&1 | tee "$LOG_FILE"

for required in \
  outputs/dft_environment_report.json \
  outputs/dft_environment_report.txt \
  logs/03_dft_environment.log; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: expected output missing or empty: $required" >&2
    exit 20
  fi
done

echo
printf '[Step 03] Environment audit finished successfully.\n'
printf '[Step 03] No DFT calculation has been executed.\n'
printf '[Step 03] Please send back:\n'
printf '  1) outputs/dft_environment_report.txt, and\n'
printf '  2) outputs/dft_environment_report.json\n'
printf '[Step 03] The production backend and convergence protocol will be selected only after review.\n'
