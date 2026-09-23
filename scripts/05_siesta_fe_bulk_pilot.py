#!/usr/bin/env python3
"""One small, non-production ferromagnetic alpha-Fe ASE/SIESTA pilot.

The first executable electronic-structure task after the completed PSML preflight.
It runs one fixed-cell, fixed-position calculation only; no convergence claims.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import traceback

import numpy as np
from ase.calculators.siesta import Siesta
from ase.io import read
from ase.units import Ry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
PILOT_ROOT = OUT / "dft" / "fe_bulk_siesta_pilot"
BULK = OUT / "POSCAR_Fe_bulk"
BULK_META = OUT / "Fe_bulk_metadata.json"
PREFLIGHT = OUT / "siesta_preflight.json"

# Pilot parameters, deliberately not declared numerically converged.
MESH_CUTOFF_RY = 250.0
ENERGY_SHIFT_RY = 0.02
KPTS = (6, 6, 6)
INITIAL_MAGMOM_MUB_PER_FE = 2.2
ELECTRONIC_TEMPERATURE_K = 300
SCF_DM_TOLERANCE = 1.0e-4
SCF_MAX_ITERATIONS = 120
MIXING_WEIGHT = 0.05


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_previous_gates(pseudo_dir: Path) -> tuple:
    if not BULK.is_file() or not BULK_META.is_file():
        raise RuntimeError("Validated bulk Fe files missing. Run the structural-model prerequisite.")
    bulk_meta = json.loads(BULK_META.read_text())
    symmetry = bulk_meta.get("standardized_structure_symmetry_strict", {})
    if bulk_meta.get("formula") != "Fe" or symmetry.get("space_group_number") != 229:
        raise RuntimeError("Bulk metadata does not document validated alpha-Fe Im-3m/229.")
    if not PREFLIGHT.is_file():
        raise RuntimeError("SIESTA/Fe/O PSML preflight missing. First run script 04.")
    check = json.loads(PREFLIGHT.read_text())
    if not check.get("preflight_passed"):
        raise RuntimeError("SIESTA/PSML preflight did not pass.")
    for element in ("Fe", "O"):
        record = check["pseudos"][element]
        current = pseudo_dir / f"{element}.psml"
        if not current.is_file() or sha256(current) != record.get("sha256"):
            raise RuntimeError(
                f"{element}.psml differs from the validated preflight file. "
                "Repeat the PSML audit before running DFT."
            )
    atoms = read(BULK, format="vasp")
    if len(atoms) != 2 or set(atoms.get_chemical_symbols()) != {"Fe"} or not bool(np.all(atoms.pbc)):
        raise RuntimeError("Expected the validated two-atom, periodic alpha-Fe conventional cell.")
    lengths = np.asarray(atoms.cell.lengths(), dtype=float)
    angles = np.asarray(atoms.cell.angles(), dtype=float)
    if not np.allclose(lengths, lengths[0], rtol=0, atol=1e-4) or not np.allclose(
        angles, [90.0] * 3, rtol=0, atol=1e-4
    ):
        raise RuntimeError("Fe bulk structure is not the validated conventional cubic cell.")
    return atoms, bulk_meta, check


def moment_diagnostic(output: Path) -> list[str]:
    if not output.is_file():
        return []
    return [
        line.strip()
        for line in output.read_text(errors="replace").splitlines()
        if "spin moment:" in line.lower()
    ][-8:]


def main() -> int:
    pseudo_dir = Path(os.path.expanduser(
        os.environ.get("SIESTA_PS_PATH", "~/Pacotes/PSEUDOS/DOJO-PSML")
    )).resolve()
    command = os.environ.get("ASE_SIESTA_COMMAND")
    if not command or "PREFIX.fdf" not in command or "PREFIX.out" not in command:
        raise RuntimeError("ASE_SIESTA_COMMAND must include PREFIX.fdf and PREFIX.out.")
    atoms, bulk_meta, check = require_previous_gates(pseudo_dir)
    atoms.set_initial_magnetic_moments(
        [INITIAL_MAGMOM_MUB_PER_FE] * len(atoms)
    )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    run_dir = PILOT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    label = "Fe_bulk_pilot"
    output = run_dir / f"{label}.out"
    fdf = run_dir / f"{label}.fdf"
    summary_path = run_dir / "pilot_summary.json"

    settings = {
        "purpose": "first ASE-SIESTA fixed-geometry alpha-Fe pilot, not a convergence result",
        "run_id": run_id,
        "source_material_id": bulk_meta.get("material_id"),
        "bulk_structure": str(BULK.relative_to(ROOT)),
        "siesta_version": check.get("siesta", {}).get("version_text", "").split("\n")[1:2],
        "ase_version": check.get("ase", {}).get("version"),
        "Fe_psml_sha256": check["pseudos"]["Fe"]["sha256"],
        "O_psml_sha256_provenance_only": check["pseudos"]["O"]["sha256"],
        "Fe_psml_valence_electrons": check["pseudos"]["Fe"].get("z_pseudo"),
        "spin": "collinear (ferromagnetic initialization)",
        "initial_magnetic_moment_muB_per_Fe": INITIAL_MAGMOM_MUB_PER_FE,
        "xc": "PBE",
        "basis": "DZP (automatic PAO generation)",
        "mesh_cutoff_Ry": MESH_CUTOFF_RY,
        "PAO_energy_shift_Ry": ENERGY_SHIFT_RY,
        "k_points": list(KPTS),
        "electronic_temperature_K": ELECTRONIC_TEMPERATURE_K,
        "SCF_DM_tolerance": SCF_DM_TOLERANCE,
        "SCF_max_iterations": SCF_MAX_ITERATIONS,
        "DM_mixing_weight": MIXING_WEIGHT,
        "MPI_ranks": int(os.environ.get("SIESTA_MPI_RANKS", "2")),
        "ASE_SIESTA_COMMAND": command,
        "positions_relaxed": False,
        "cell_relaxed": False,
        "parameter_convergence_demonstrated": False,
        "magnetic_ground_state_verified": False,
        "run_directory": str(run_dir.relative_to(ROOT)),
    }
    (run_dir / "pilot_settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    print(f"[Pilot] Inputs and parameters recorded: {run_dir / 'pilot_settings.json'}", flush=True)
    print("[Pilot] Running single spin-polarized alpha-Fe bulk calculation.", flush=True)

    calc = Siesta(
        label=label,
        directory=str(run_dir),
        command=command,
        pseudo_path=str(pseudo_dir),
        pseudo_qualifier="",
        symlink_pseudos=True,
        xc="PBE",
        mesh_cutoff=MESH_CUTOFF_RY * Ry,
        energy_shift=ENERGY_SHIFT_RY * Ry,
        basis_set="DZP",
        kpts=list(KPTS),
        spin="collinear",
        fdf_arguments={
            "ElectronicTemperature": f"{ELECTRONIC_TEMPERATURE_K} K",
            "SCF.DM.Tolerance": SCF_DM_TOLERANCE,
            "MaxSCFIterations": SCF_MAX_ITERATIONS,
            "DM.MixingWeight": MIXING_WEIGHT,
            "SCFMustConverge": True,
            "Charge.Mulliken": "end",
            "DM.UseSaveDM": False,
        },
    )
    atoms.calc = calc
    try:
        energy_ev = float(atoms.get_potential_energy())
        if not math.isfinite(energy_ev):
            raise RuntimeError(f"Non-finite total energy: {energy_ev!r}")
        if not fdf.is_file() or not output.is_file():
            raise RuntimeError("SIESTA FDF/output files missing after ASE returned energy.")
        fdf_text = fdf.read_text(errors="replace")
        if not re.search(r"(?im)^\s*Spin\s+(?:collinear|polarized)\b", fdf_text):
            raise RuntimeError("Generated FDF does not enable collinear spin polarization.")
        if not re.search(r"(?im)^\s*%block\s+DM\.InitSpin\b", fdf_text):
            raise RuntimeError("Generated FDF is missing the magnetic initialization block.")
        pseudo_links = list(run_dir.glob("Fe*.psml"))
        if not pseudo_links or all(sha256(p) != settings["Fe_psml_sha256"] for p in pseudo_links):
            raise RuntimeError("ASE did not link/copy the approved Fe.psml into the run directory.")
        moment_lines = moment_diagnostic(output)
        summary = {
            **settings,
            "ase_returned_finite_energy": True,
            "energy_eV_cell": energy_ev,
            "energy_eV_per_atom": energy_ev / len(atoms),
            "FDF_present": True,
            "SIESTA_stdout_present": True,
            "spin_initialization_FDF_present": True,
            "approved_Fe_psml_used": True,
            "reported_spin_moment_lines_last_8": moment_lines,
            "magnetism_check_pending_review": True,
            "pilot_gate": "ASE/SIESTA execution completed; scientific review pending",
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        (OUT / "fe_bulk_siesta_pilot_summary.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
        print(f"[Pilot] ASE returned finite energy: {energy_ev:.8f} eV/cell", flush=True)
        print(f"[Pilot] Spin-moment diagnostic lines in output: {len(moment_lines)}", flush=True)
        print(f"[Pilot] Summary: {OUT / 'fe_bulk_siesta_pilot_summary.json'}", flush=True)
        print(f"[Pilot] SIESTA output: {output}", flush=True)
        print("[Pilot] Numerical convergence and magnetic state still require review.", flush=True)
        return 0
    except Exception:
        failure = {
            **settings,
            "pilot_gate": "FAILED",
            "error": traceback.format_exc(),
            "SIESTA_stdout_present": output.is_file(),
            "SIESTA_FDF_present": fdf.is_file(),
        }
        (run_dir / "pilot_failure.json").write_text(json.dumps(failure, indent=2) + "\n")
        print(f"[Pilot] Failed; detailed diagnostics: {run_dir / 'pilot_failure.json'}", file=sys.stderr)
        print(f"[Pilot] If present, review {output}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
