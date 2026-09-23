#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
export SIESTA_PS_PATH="${SIESTA_PS_PATH:-$HOME/Pacotes/PSEUDOS/DOJO-PSML}"
SIESTA_MPI_RANKS="${SIESTA_MPI_RANKS:-2}"

if ! [[ "$SIESTA_MPI_RANKS" =~ ^[1-4]$ ]]; then
  echo "ERROR: pilot allows SIESTA_MPI_RANKS=1, 2, 3 or 4 only." >&2
  exit 10
fi
export SIESTA_MPI_RANKS
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

if ! command -v siesta >/dev/null 2>&1 || ! command -v mpirun >/dev/null 2>&1; then
  echo "ERROR: siesta and mpirun must be available on PATH." >&2
  exit 11
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: Python not found: $PYTHON_BIN" >&2
  exit 12
fi
if ! "$PYTHON_BIN" -c "import ase, numpy" >/dev/null 2>&1; then
  if [[ -x .venv-step02/bin/python ]] && .venv-step02/bin/python -c "import ase, numpy" >/dev/null 2>&1; then
    PYTHON_BIN="$ROOT_DIR/.venv-step02/bin/python"
  else
    echo "ERROR: ASE and NumPy unavailable. Run Step 02 setup or set PYTHON_BIN to Python with ASE." >&2
    exit 13
  fi
fi

mkdir -p outputs logs
if [[ ! -s outputs/POSCAR_Fe_bulk || ! -s outputs/Fe_bulk_metadata.json ]]; then
  if [[ -z "${MP_API_KEY:-}" ]]; then
    echo "ERROR: validated bulk Fe prerequisite is missing; set MP_API_KEY for regeneration." >&2
    exit 14
  fi
  if ! "$PYTHON_BIN" -c "import mp_api, pymatgen, ase" >/dev/null 2>&1; then
    if [[ -x .venv-step02/bin/python ]] && .venv-step02/bin/python -c "import mp_api, pymatgen, ase" >/dev/null 2>&1; then
      PYTHON_BIN="$ROOT_DIR/.venv-step02/bin/python"
    else
      echo "ERROR: Materials Project dependencies unavailable. Run Step 02 setup first." >&2
      exit 15
    fi
  fi
  echo "[Step 03] Reconstructing the validated Fe reference from Materials Project."
  "$PYTHON_BIN" scripts/01_fetch_fe_bulk.py 2>&1 | tee logs/01_fetch_fe_bulk.log
else
  echo "[Step 03] Reusing validated local alpha-Fe bulk reference."
fi

if [[ ! -s outputs/siesta_preflight.json ]]; then
  echo "[Step 03] Performing SIESTA/PSML preflight."
  "$PYTHON_BIN" scripts/04_audit_siesta_pseudos.py 2>&1 | tee logs/04_siesta_preflight.log
fi

SIESTA_BIN="$(command -v siesta)"
export ASE_SIESTA_COMMAND="mpirun -np $SIESTA_MPI_RANKS $SIESTA_BIN < PREFIX.fdf > PREFIX.out"
echo "[Step 03] First electronic-structure pilot: alpha-Fe bulk PBE/DZP; MPI ranks=$SIESTA_MPI_RANKS."
echo "[Step 03] This is NOT a numerically converged production calculation."
"$PYTHON_BIN" scripts/05_siesta_fe_bulk_pilot.py 2>&1 | tee logs/05_siesta_fe_bulk_pilot.log
if [[ ! -s outputs/fe_bulk_siesta_pilot_summary.json ]]; then
  echo "ERROR: pilot summary was not produced." >&2
  exit 20
fi

echo "[Step 03] Pilot execution completed; return the files below for scientific review:"
echo "  outputs/fe_bulk_siesta_pilot_summary.json"
echo "  logs/05_siesta_fe_bulk_pilot.log"
echo "  SIESTA .out file within the run_directory given in the JSON summary"
