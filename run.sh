#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv-step02}"

printf '\n[Step 02] Structural models — first validation target: bulk bcc Fe\n'
printf '[Step 02] Repository: %s\n' "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN was not found in PATH." >&2
  exit 10
fi

if [[ -z "${MP_API_KEY:-}" ]]; then
  cat >&2 <<'EOF'
ERROR: MP_API_KEY is not set.
Export your Materials Project API key before running, for example:

  export MP_API_KEY="YOUR_KEY_HERE"
  ./run.sh

The key must never be committed to Git.
EOF
  exit 11
fi

mkdir -p outputs logs

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[Step 02] Creating Python virtual environment: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-step02.txt

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-32}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-32}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-32}"

LOG_FILE="logs/01_fetch_fe_bulk.log"
echo "[Step 02] Querying Materials Project for elemental bcc Fe (Im-3m)."
python scripts/01_fetch_fe_bulk.py 2>&1 | tee "$LOG_FILE"

for required in \
  outputs/Fe_bulk_mp_raw.cif \
  outputs/POSCAR_Fe_bulk_mp_raw \
  outputs/POSCAR_Fe_bulk \
  outputs/Fe_bulk_conventional.cif \
  outputs/Fe_bulk_metadata.json \
  outputs/Fe_query_candidates.json; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: expected output missing or empty: $required" >&2
    exit 20
  fi
done

python - <<'PY'
import json
from pathlib import Path
p = Path('outputs/Fe_bulk_metadata.json')
meta = json.loads(p.read_text())
if meta.get('formula') != 'Fe':
    raise SystemExit(f"ERROR: expected formula Fe, got {meta.get('formula')!r}")
reported = meta.get('reported_symmetry')
if reported != 'Im-3m':
    raise SystemExit(f"ERROR: expected MP-reported Im-3m, got {reported!r}")
mp_diag = meta.get('raw_structure_symmetry_mp_compatible', {})
if mp_diag.get('space_group_symbol') != 'Im-3m' or mp_diag.get('space_group_number') != 229:
    raise SystemExit(f"ERROR: MP-compatible symmetry validation failed: {mp_diag}")
std_diag = meta.get('standardized_structure_symmetry_strict', {})
if std_diag.get('space_group_symbol') != 'Im-3m' or std_diag.get('space_group_number') != 229:
    raise SystemExit(f"ERROR: standardized strict symmetry validation failed: {std_diag}")
print('[Step 02] Validation PASSED: elemental alpha-Fe reference standardized as bcc Im-3m (229).')
print(f"[Step 02] Materials Project ID: {meta.get('material_id')}")
strict = meta.get('raw_structure_symmetry_strict', {})
print(
    '[Step 02] Raw MP structure diagnostic at symprec=1e-3 A: '
    f"{strict.get('space_group_symbol')} ({strict.get('space_group_number')})"
)
print('[Step 02] Simulation reference: outputs/POSCAR_Fe_bulk')
PY

python -m pip freeze > outputs/environment_freeze.txt

echo
printf '[Step 02] Finished successfully.\n'
printf '[Step 02] Please send back:\n'
printf '  1) the terminal output, and\n'
printf '  2) cat outputs/Fe_bulk_metadata.json\n'
printf '[Step 02] Do not proceed to the next structural model until this validation is reviewed.\n'
