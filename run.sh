#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv-step02}"

printf '\n[Step 02] Structural models — second validation target: alpha-Fe surface library\n'
printf '[Step 02] Repository: %s\n' "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN was not found in PATH." >&2
  exit 10
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

# A fresh clone of this branch can reconstruct the prerequisite bulk reference.
# On a workstation where Task 01 has already passed, the validated local files
# are reused and no Materials Project query is repeated.
if [[ ! -s outputs/POSCAR_Fe_bulk || ! -s outputs/Fe_bulk_metadata.json ]]; then
  if [[ -z "${MP_API_KEY:-}" ]]; then
    cat >&2 <<'EOF'
ERROR: validated bulk Fe outputs are missing and MP_API_KEY is not set.
For a fresh clone, export the Materials Project key first:

  export MP_API_KEY="YOUR_KEY_HERE"
  ./run.sh

The key must never be committed to Git.
EOF
    exit 11
  fi

  echo "[Step 02] Bulk prerequisite missing; reconstructing Task 01 first."
  python scripts/01_fetch_fe_bulk.py 2>&1 | tee logs/01_fetch_fe_bulk.log
else
  echo "[Step 02] Reusing existing validated bulk Fe outputs."
fi

python - <<'PY'
import json
from pathlib import Path

p = Path('outputs/Fe_bulk_metadata.json')
if not p.is_file():
    raise SystemExit('ERROR: outputs/Fe_bulk_metadata.json is missing.')
meta = json.loads(p.read_text())
if meta.get('formula') != 'Fe':
    raise SystemExit(f"ERROR: expected formula Fe, got {meta.get('formula')!r}")
std = meta.get('standardized_structure_symmetry_strict', {})
if std.get('space_group_symbol') != 'Im-3m' or std.get('space_group_number') != 229:
    raise SystemExit(f"ERROR: bulk prerequisite failed strict Im-3m/229 validation: {std}")
if not Path('outputs/POSCAR_Fe_bulk').is_file():
    raise SystemExit('ERROR: outputs/POSCAR_Fe_bulk is missing.')
print('[Step 02] Bulk prerequisite PASSED: standardized alpha-Fe Im-3m (229).')
print(f"[Step 02] Bulk source: {meta.get('material_id')}")
PY

LOG_FILE="logs/02_build_fe_surfaces.log"
echo "[Step 02] Building Fe(110), Fe(100), and Fe(111) geometric slab candidates."
python scripts/02_build_fe_surfaces.py 2>&1 | tee "$LOG_FILE"

for required in \
  outputs/surfaces/surface_library.json \
  outputs/surfaces/surface_library.csv \
  outputs/surfaces/surface_library_report.txt; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: expected output missing or empty: $required" >&2
    exit 20
  fi
done

python - <<'PY'
import json
from pathlib import Path

p = Path('outputs/surfaces/surface_library.json')
data = json.loads(p.read_text())
if data.get('not_a_convergence_claim') is not True:
    raise SystemExit('ERROR: surface-library metadata lost the non-convergence disclaimer.')
if data.get('n_candidates') != 18:
    raise SystemExit(f"ERROR: expected 18 slab candidates, got {data.get('n_candidates')!r}")
if data.get('n_failed') != 0:
    raise SystemExit(f"ERROR: {data.get('n_failed')} slab candidates failed geometry validation.")
labels = {row.get('label') for row in data.get('candidates', [])}
if labels != {'Fe110', 'Fe100', 'Fe111'}:
    raise SystemExit(f"ERROR: unexpected surface labels: {sorted(labels)}")
if not all(row.get('validation_passed') for row in data.get('candidates', [])):
    raise SystemExit('ERROR: at least one candidate did not pass geometric validation.')
print('[Step 02] Validation PASSED: 18 alpha-Fe slab candidates passed geometric checks.')
print('[Step 02] Fe(110) remains the primary orientation; no slab is yet DFT-converged.')
PY

python -m pip freeze > outputs/environment_freeze.txt

echo
printf '[Step 02] Surface-library task finished successfully.\n'
printf '[Step 02] Please send back:\n'
printf '  1) outputs/surfaces/surface_library_report.txt, and\n'
printf '  2) logs/02_build_fe_surfaces.log\n'
printf '[Step 02] Do not proceed to DFT or oxide models until this gate is reviewed.\n'
