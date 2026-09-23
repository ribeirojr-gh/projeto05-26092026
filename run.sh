#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
export SIESTA_PS_PATH="${SIESTA_PS_PATH:-$HOME/Pacotes/PSEUDOS/DOJO-PSML}"

printf '\n[Step 03] SIESTA–ASE and Fe/O pseudopotential preflight\n'
printf "[Step 03] Repository: %s\n" "$ROOT_DIR"
printf "[Step 03] Pseudopotential directory: %s\n" "$SIESTA_PS_PATH"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf "ERROR: Python executable not found: %s\n" "$PYTHON_BIN" >&2
  exit 10
fi
if ! command -v siesta >/dev/null 2>&1; then
  echo 'ERROR: siesta executable not found in PATH.' >&2
  exit 11
fi

mkdir -p outputs logs
"$PYTHON_BIN" scripts/04_audit_siesta_pseudos.py 2>&1 | tee logs/04_siesta_preflight.log

for target in \
    outputs/siesta_preflight.json \
    outputs/siesta_preflight.txt \
    logs/04_siesta_preflight.log; do
  if [[ ! -s "$target" ]]; then
    echo "ERROR: expected diagnostic file missing or empty: $target" >&2
    exit 20
  fi
done

echo '[Step 03] Fe/O PSML metadata and ASE import preflight PASSED.'
echo '[Step 03] No DFT calculation was executed.'
echo '[Step 03] Please return outputs/siesta_preflight.txt and outputs/siesta_preflight.json.'
