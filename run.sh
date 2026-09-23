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

echo "[Step 03] Previous 550–850 Ry study completed and native FFT-grid diagnostic reviewed."
for source in outputs/fe_bulk_mesh_cutoff_extension_summary.json outputs/fe_bulk_mesh_cutoff_extension_report.txt; do
  if [[ ! -s "$source" ]]; then
    echo "ERROR: reviewed extension output missing: $source" >&2
    exit 16
  fi
done
echo "[Step 03] Screening distinct realized SIESTA grids: requests 850, 1000, 1250, 1500 Ry."
echo "[Step 03] Repeating 850 Ry as a physical-grid reproducibility anchor."
echo "[Step 03] MPI ranks: $SIESTA_MPI_RANKS, one OpenMP/BLAS thread per rank."
"$PYTHON_BIN" scripts/08_fe_bulk_realized_grid_screen.py 2>&1 | tee logs/08_fe_bulk_realized_grid.log
for output in outputs/fe_bulk_realized_grid_summary.json outputs/fe_bulk_realized_grid_summary.csv outputs/fe_bulk_realized_grid_report.txt logs/08_fe_bulk_realized_grid.log; do
  if [[ ! -s "$output" ]]; then
    echo "ERROR: requested grid-screening output missing or empty: $output" >&2
    exit 20
  fi
done
echo "[Step 03] Realized-grid screening complete. No final numerical convergence is claimed."
echo "[Step 03] Send outputs/fe_bulk_realized_grid_summary.json, outputs/fe_bulk_realized_grid_report.txt and logs/08_fe_bulk_realized_grid.log."
