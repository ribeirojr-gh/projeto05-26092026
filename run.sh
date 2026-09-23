#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
export SIESTA_PS_PATH="${SIESTA_PS_PATH:-$HOME/Pacotes/PSEUDOS/DOJO-PSML}"
SIESTA_MPI_RANKS="${SIESTA_MPI_RANKS:-2}"
if ! [[ "$SIESTA_MPI_RANKS" =~ ^[1-4]$ ]]; then
  echo "ERROR: this screening permits 1–4 MPI ranks (default 2)." >&2
  exit 10
fi
export SIESTA_MPI_RANKS OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

if ! command -v siesta >/dev/null 2>&1 || ! command -v mpirun >/dev/null 2>&1; then
  echo "ERROR: siesta and mpirun must be available in PATH." >&2
  exit 11
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: Python interpreter not found: $PYTHON_BIN" >&2
  exit 12
fi

if ! "$PYTHON_BIN" -c "from ase.calculators.siesta import Siesta; import numpy" >/dev/null 2>&1; then
  if [[ -x .venv-step02/bin/python ]] && .venv-step02/bin/python -c "from ase.calculators.siesta import Siesta; import numpy" >/dev/null 2>&1; then
    PYTHON_BIN="$ROOT_DIR/.venv-step02/bin/python"
  else
    echo "[Step 03] Installing prerequisites in a project-local Python virtual environment."
    python3 -m venv .venv-step02
    "$ROOT_DIR/.venv-step02/bin/python" -m pip install --upgrade pip setuptools wheel
    "$ROOT_DIR/.venv-step02/bin/python" -m pip install -r requirements-step02.txt
    PYTHON_BIN="$ROOT_DIR/.venv-step02/bin/python"
  fi
fi

mkdir -p outputs logs
if [[ ! -s outputs/POSCAR_Fe_bulk || ! -s outputs/Fe_bulk_metadata.json ]]; then
  if [[ -z "${MP_API_KEY:-}" ]]; then
    echo "ERROR: validated bulk Fe prerequisite missing; export MP_API_KEY for Materials Project retrieval." >&2
    exit 13
  fi
  if ! "$PYTHON_BIN" -c "import mp_api, pymatgen, ase" >/dev/null 2>&1; then
    if [[ ! -x .venv-step02/bin/python ]] || ! .venv-step02/bin/python -c "import mp_api, pymatgen, ase" >/dev/null 2>&1; then
      python3 -m venv .venv-step02
      .venv-step02/bin/python -m pip install --upgrade pip setuptools wheel
      .venv-step02/bin/python -m pip install -r requirements-step02.txt
    fi
    PYTHON_BIN="$ROOT_DIR/.venv-step02/bin/python"
  fi
  echo "[Step 03] Reconstructing the Materials Project alpha-Fe bulk prerequisite."
  "$PYTHON_BIN" scripts/01_fetch_fe_bulk.py 2>&1 | tee logs/01_fetch_fe_bulk.log
else
  echo "[Step 03] Reusing the validated local bulk alpha-Fe reference."
fi

echo "[Step 03] Refreshing actual local Fe/O PSML + ASE preflight."
"$PYTHON_BIN" scripts/04_audit_siesta_pseudos.py 2>&1 | tee logs/04_siesta_preflight.log

SIESTA_BIN="$(command -v siesta)"
export ASE_SIESTA_COMMAND="mpirun -np $SIESTA_MPI_RANKS $SIESTA_BIN < PREFIX.fdf > PREFIX.out"
if [[ ! -s outputs/fe_bulk_siesta_pilot_summary.json ]]; then
  echo "[Step 03] Initial validated pilot absent; running it once before numerical screening."
  "$PYTHON_BIN" scripts/05_siesta_fe_bulk_pilot.py 2>&1 | tee logs/05_siesta_fe_bulk_pilot.log
else
  echo "[Step 03] Reusing previously completed alpha-Fe bulk pilot."
fi

echo "[Step 03] Prior 250–550 Ry sensitivity gate has been reviewed."
for prior in outputs/fe_bulk_mesh_cutoff_summary.json outputs/fe_bulk_mesh_cutoff_report.txt; do
  if [[ ! -s "$prior" ]]; then
    echo "ERROR: prior validated MeshCutoff screening result missing: $prior" >&2
    echo "Run the previous screening gate before this extension; no numerical result will be invented." >&2
    exit 16
  fi
done
echo "[Step 03] Extended MeshCutoff screening: 550, 650, 750, 850 Ry."
echo "[Step 03] Repeating 550 Ry to validate reproducibility against the prior run."
echo "[Step 03] Two MPI ranks and one thread per rank by default; no slab DFT."
"$PYTHON_BIN" scripts/07_fe_bulk_mesh_cutoff_extension.py 2>&1 | tee logs/07_fe_bulk_mesh_cutoff_extension.log

for path in outputs/fe_bulk_mesh_cutoff_extension_summary.json outputs/fe_bulk_mesh_cutoff_extension_summary.csv outputs/fe_bulk_mesh_cutoff_extension_report.txt logs/07_fe_bulk_mesh_cutoff_extension.log; do
  if [[ ! -s "$path" ]]; then
    echo "ERROR: expected screening output missing or empty: $path" >&2
    exit 20
  fi
done
echo "[Step 03] Extended cutoff screening completed; no final numerical convergence was claimed."
echo "[Step 03] Return extension summary JSON, extension report TXT and logs/07_fe_bulk_mesh_cutoff_extension.log."
