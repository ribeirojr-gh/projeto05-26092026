#!/usr/bin/env python3
"""Single-parameter alpha-Fe extended mesh-cutoff screening (NOT final convergence).

Four independent fixed-cell/fixed-position ferromagnetic bulk calculations,
with only MeshCutoff varied. No slab DFT or adsorbate calculations are started.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import traceback

import numpy as np
from ase.calculators.siesta import Siesta
from ase.io import read
from ase.units import Ry

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
BULK = OUTPUTS / "POSCAR_Fe_bulk"
BULK_META = OUTPUTS / "Fe_bulk_metadata.json"
PREFLIGHT = OUTPUTS / "siesta_preflight.json"
PILOT = OUTPUTS / "fe_bulk_siesta_pilot_summary.json"

# The sole numerical variable in this screening task.
CUTOFF_GRID_RY = (550, 650, 750, 850)
ENERGY_SHIFT_RY = 0.02
KPTS = (6, 6, 6)
INIT_MOMENT = 2.2
TEMP_K = 300
DM_TOL = 1.0e-4
SCF_MAX = 120
MIX = 0.05

SCF_RE = re.compile(r"SCF cycle converged after\s+(\d+)\s+iterations", re.I)
ETOT_RE = re.compile(r"(?m)^\s*siesta:\s+Etot\s*=\s*([-+0-9.eEdD]+)")
SPIN_RE = re.compile(r"spin moment:.*?([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$", re.I)
PRESSURE_RE = re.compile(
    r"(?m)^\s*siesta:\s+([-+0-9.eEdD]+)\s+[-+0-9.eEdD]+\s+kBar\s*$"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def native_diagnostics(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Native SIESTA output not found: {path}")
    native = path.read_text(errors="replace")
    if "Job completed" not in native:
        raise RuntimeError(f"SIESTA did not report 'Job completed': {path}")
    scf = SCF_RE.findall(native)
    etot = ETOT_RE.findall(native)
    spin = [SPIN_RE.search(s) for s in native.splitlines() if "spin moment:" in s.lower()]
    spin = [m for m in spin if m is not None]
    if not scf or not etot or not spin:
        raise RuntimeError(
            f"Missing SCF convergence, final Etot, or spin moment in {path}; inspect full output."
        )
    if "Reading pseudopotential information in PSML from:" not in native or "Fe.1.psml" not in native:
        raise RuntimeError(f"Approved Fe PSML provenance missing from SIESTA output: {path}")
    pressure_section = native.rsplit("Pressure (static):", 1)
    pressures = PRESSURE_RE.findall(pressure_section[-1]) if len(pressure_section) == 2 else []
    return {
        "scf_converged": True,
        "scf_iterations": int(scf[-1]),
        "etot_native_eV_cell": _to_float(etot[-1]),
        "spin_moment_native_muB_cell": _to_float(spin[-1].group(1)),
        "pressure_static_kbar": _to_float(pressures[0]) if pressures else None,
        "native_output_completed": True,
        "Fe_psml_read": True,
    }


def load_prerequisites(pseudo_dir: Path):
    for source in (BULK, BULK_META, PREFLIGHT, PILOT):
        if not source.is_file():
            raise RuntimeError(f"Required validated local prerequisite missing: {source}")
    meta = json.loads(BULK_META.read_text())
    preflight = json.loads(PREFLIGHT.read_text())
    pilot = json.loads(PILOT.read_text())
    std = meta.get("standardized_structure_symmetry_strict", {})
    if meta.get("formula") != "Fe" or std.get("space_group_number") != 229:
        raise RuntimeError("Bulk Fe structural gate is missing or invalid.")
    if not preflight.get("preflight_passed") or not pilot.get("ase_returned_finite_energy"):
        raise RuntimeError("SIESTA preflight or initial Fe bulk pilot gate is not valid.")
    approved = preflight["pseudos"]["Fe"]["sha256"]
    actual = pseudo_dir / "Fe.psml"
    if not actual.is_file() or sha256(actual) != approved:
        raise RuntimeError("Fe.psml hash differs from the approved PSML preflight.")
    if pilot.get("Fe_psml_sha256") != approved:
        raise RuntimeError("Initial pilot and current preflight used different Fe.psml files.")
    atoms = read(BULK, format="vasp")
    if len(atoms) != 2 or set(atoms.get_chemical_symbols()) != {"Fe"} or not all(atoms.pbc):
        raise RuntimeError("Expected the validated two-atom periodic alpha-Fe reference.")
    if pilot.get("bulk_structure") != "outputs/POSCAR_Fe_bulk":
        raise RuntimeError("Pilot bulk-structure provenance differs from the current reference.")
    previous_path = OUTPUTS / "fe_bulk_mesh_cutoff_summary.json"
    if not previous_path.is_file():
        raise RuntimeError("Previous 250/350/450/550 Ry mesh screening missing; cannot proceed.")
    previous = json.loads(previous_path.read_text())
    previous_grid = previous.get("mesh_cutoff_grid_Ry")
    previous_rows = previous.get("results", [])
    if (
        previous_grid != [250, 350, 450, 550]
        or previous.get("n_completed") != 4
        or not previous.get("all_scf_converged")
        or previous.get("Fe_psml_sha256") != approved
        or previous.get("geometry") != "outputs/POSCAR_Fe_bulk"
        or previous.get("k_points") != list(KPTS)
        or previous.get("basis") != "DZP"
        or previous.get("energy_shift_Ry") != ENERGY_SHIFT_RY
        or previous.get("electronic_temperature_K") != TEMP_K
        or len(previous_rows) != 4
        or [r.get("cutoff_Ry") for r in previous_rows] != previous_grid
        or not all(r.get("scf_converged") for r in previous_rows)
    ):
        raise RuntimeError("Previous mesh-cutoff gate is incomplete or incompatible.")
    return atoms, meta, preflight, pilot, approved, previous


def run_one(atoms, cutoff_ry: int, directory: Path, command: str, pseudo_dir: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    label = f"Fe_bulk_mesh_{cutoff_ry}Ry"
    calc = Siesta(
        label=label,
        directory=str(directory),
        command=command,
        pseudo_path=str(pseudo_dir),
        pseudo_qualifier="",
        symlink_pseudos=True,
        xc="PBE",
        mesh_cutoff=cutoff_ry * Ry,
        energy_shift=ENERGY_SHIFT_RY * Ry,
        basis_set="DZP",
        kpts=list(KPTS),
        spin="collinear",
        fdf_arguments={
            "ElectronicTemperature": f"{TEMP_K} K",
            "SCF.DM.Tolerance": DM_TOL,
            "MaxSCFIterations": SCF_MAX,
            "DM.MixingWeight": MIX,
            "SCFMustConverge": True,
            "Charge.Mulliken": "end",
            "DM.UseSaveDM": False,
        },
    )
    independent_atoms = atoms.copy()
    independent_atoms.set_initial_magnetic_moments([INIT_MOMENT] * len(independent_atoms))
    independent_atoms.calc = calc
    energy_ev = float(independent_atoms.get_potential_energy())
    if not math.isfinite(energy_ev):
        raise RuntimeError(f"{label}: ASE returned non-finite energy.")
    output = directory / f"{label}.out"
    fdf = directory / f"{label}.fdf"
    if not fdf.is_file():
        raise RuntimeError(f"{label}: generated FDF not found.")
    fdf_text = fdf.read_text(errors="replace")
    if not re.search(r"(?im)^\s*Spin\s+collinear\b", fdf_text) or not re.search(
        r"(?im)^\s*%block\s+DM\.InitSpin\b", fdf_text
    ):
        raise RuntimeError(f"{label}: missing collinear spin or initial moments in FDF.")
    extracted = native_diagnostics(output)
    if abs(extracted["etot_native_eV_cell"] - energy_ev) > 1.0e-3:
        raise RuntimeError(
            f"{label}: ASE and native SIESTA energies disagree by >1 meV/cell."
        )
    n_atoms = len(independent_atoms)
    return {
        "cutoff_Ry": cutoff_ry,
        "energy_eV_cell": energy_ev,
        "energy_eV_per_atom": energy_ev / n_atoms,
        "moment_muB_per_Fe": extracted["spin_moment_native_muB_cell"] / n_atoms,
        **extracted,
        "run_dir": str(directory.relative_to(ROOT)),
        "native_output": str(output.relative_to(ROOT)),
        "input_FDF": str(fdf.relative_to(ROOT)),
    }


def main() -> int:
    command = os.environ.get("ASE_SIESTA_COMMAND", "")
    if not all(s in command for s in ("PREFIX.fdf", "PREFIX.out")):
        raise RuntimeError("ASE_SIESTA_COMMAND must include PREFIX.fdf and PREFIX.out.")
    pseudo_dir = Path(os.path.expanduser(
        os.environ.get("SIESTA_PS_PATH", "~/Pacotes/PSEUDOS/DOJO-PSML")
    )).resolve()
    atoms, meta, preflight, pilot, fe_hash, previous = load_prerequisites(pseudo_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    root = OUTPUTS / "dft" / "fe_bulk_mesh_cutoff_extension" / run_id
    root.mkdir(parents=True, exist_ok=False)

    setup = {
        "purpose": "single-variable extended alpha-Fe MeshCutoff sensitivity; NOT final numerical convergence",
        "run_id": run_id,
        "source_material_id": meta["material_id"],
        "Fe_psml_sha256": fe_hash,
        "geometry": str(BULK.relative_to(ROOT)),
        "spin": "collinear; two initial Fe moments +2.2 muB",
        "functional": "PBE",
        "basis": "DZP",
        "energy_shift_Ry": ENERGY_SHIFT_RY,
        "k_points": list(KPTS),
        "electronic_temperature_K": TEMP_K,
        "dm_tolerance": DM_TOL,
        "max_scf_iterations": SCF_MAX,
        "mixing_weight": MIX,
        "mesh_cutoff_grid_Ry": list(CUTOFF_GRID_RY),
        "MPI_ranks": int(os.environ.get("SIESTA_MPI_RANKS", "2")),
        "ase_siesta_command": command,
        "reference_pilot_energy_eV_cell": pilot["energy_eV_cell"],
        "previous_550_Ry_energy_eV_per_atom": previous["results"][-1]["energy_eV_per_atom"],
        "previous_550_Ry_moment_muB_per_Fe": previous["results"][-1]["moment_muB_per_Fe"],
        "original_screening_run_id": previous.get("run_id"),
        "not_a_final_convergence_claim": True,
    }
    (root / "screening_setup.json").write_text(json.dumps(setup, indent=2) + "\n")
    records = []
    for cutoff in CUTOFF_GRID_RY:
        directory = root / f"mesh_{cutoff}Ry"
        print(f"[Mesh] Starting Fe bulk calculation at MeshCutoff={cutoff} Ry", flush=True)
        try:
            row = run_one(atoms, cutoff, directory, command, pseudo_dir)
            if cutoff == 550:
                prior_anchor = previous["results"][-1]
                delta_energy_mev = (
                    row["energy_eV_per_atom"] - prior_anchor["energy_eV_per_atom"]
                ) * 1000.0
                delta_moment = (
                    row["moment_muB_per_Fe"] - prior_anchor["moment_muB_per_Fe"]
                )
                row["repeat_550_delta_energy_meV_per_atom"] = delta_energy_mev
                row["repeat_550_delta_moment_muB_per_Fe"] = delta_moment
                if abs(delta_energy_mev) > 0.5 or abs(delta_moment) > 0.005:
                    raise RuntimeError(
                        "Repeated 550 Ry anchor disagrees with original screening: "
                        f"deltaE={delta_energy_mev:+.4f} meV/Fe, "
                        f"deltaM={delta_moment:+.6f} muB/Fe. "
                        "Investigate environment before interpreting the extension."
                    )
                print(
                    f"[Mesh] 550 Ry repeat anchor: deltaE={delta_energy_mev:+.4f} "
                    f"meV/Fe, deltaM={delta_moment:+.6f} muB/Fe",
                    flush=True,
                )
            records.append(row)
            (root / "partial_results.json").write_text(json.dumps(records, indent=2) + "\n")
            print(
                f"[Mesh] {cutoff} Ry: SCF in {row['scf_iterations']} iterations, "
                f"E={row['energy_eV_per_atom']:.8f} eV/atom, "
                f"M={row['moment_muB_per_Fe']:.6f} muB/Fe",
                flush=True,
            )
        except Exception:
            failure = {
                **setup, "completed": records, "failed_cutoff_Ry": cutoff,
                "failure_traceback": traceback.format_exc(),
            }
            (root / "screening_failure.json").write_text(json.dumps(failure, indent=2) + "\n")
            print(
                f"[Mesh] FAILED at {cutoff} Ry. Diagnostics: {root / 'screening_failure.json'}",
                file=sys.stderr,
            )
            raise

    highest = records[-1]
    for row in records:
        row["delta_E_vs_850_meV_per_atom"] = (
            row["energy_eV_per_atom"] - highest["energy_eV_per_atom"]
        ) * 1000.0
        row["delta_M_vs_850_muB_per_Fe"] = (
            row["moment_muB_per_Fe"] - highest["moment_muB_per_Fe"]
        )
    outcome = {
        **setup,
        "n_completed": len(records),
        "n_expected": len(CUTOFF_GRID_RY),
        "all_scf_converged": all(r["scf_converged"] for r in records),
        "results": records,
        "warning": (
            "850 Ry is merely the highest screened cutoff, not a converged reference. "
            "The PAO basis, k-points, lattice parameter, and magnetic state also require "
            "independent/coupled convergence checks. Fixed-cell residual stress can be substantial."
        ),
    }
    screening_json = OUTPUTS / "fe_bulk_mesh_cutoff_extension_summary.json"
    screening_json.write_text(json.dumps(outcome, indent=2) + "\n")

    columns = [
        "cutoff_Ry", "energy_eV_per_atom", "delta_E_vs_850_meV_per_atom",
        "moment_muB_per_Fe", "delta_M_vs_850_muB_per_Fe",
        "scf_iterations", "pressure_static_kbar", "run_dir", "native_output",
    ]
    with (OUTPUTS / "fe_bulk_mesh_cutoff_extension_summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{field: row.get(field) for field in columns} for row in records])

    lines = [
        "Alpha-Fe bulk SIESTA extended MeshCutoff screening (not final convergence)",
        "==============================================================",
        "PBE, validated Fe semicore PSML, DZP, 6x6x6 k-mesh, 300 K, fixed mp-13 geometry.",
        "All calculations started from identical +2.2 muB/Fe initial moments.",
        "  Ry        eV/Fe    deltaE(meV/Fe)  moment(muB/Fe)  SCF iter  P(kbar)",
    ]
    for r in records:
        pressure = r["pressure_static_kbar"]
        lines.append(
            f"{r['cutoff_Ry']:4d}  {r['energy_eV_per_atom']:13.6f} "
            f"{r['delta_E_vs_850_meV_per_atom']:14.4f} "
            f"{r['moment_muB_per_Fe']:14.6f} "
            f"{r['scf_iterations']:8d} "
            f"{pressure:9.2f}" if pressure is not None else
            f"{r['cutoff_Ry']:4d}  {r['energy_eV_per_atom']:13.6f} "
            f"{r['delta_E_vs_850_meV_per_atom']:14.4f} "
            f"{r['moment_muB_per_Fe']:14.6f} "
            f"{r['scf_iterations']:8d} {'N/A':>9}"
        )
    lines += [
        "",
        f"Native run folder: {root.relative_to(ROOT)}",
        "Screening completed. Numerical convergence is NOT established.",
    ]
    (OUTPUTS / "fe_bulk_mesh_cutoff_extension_report.txt").write_text("\n".join(lines) + "\n")
    print("[Mesh] Completed all four fixed-geometry calculations.", flush=True)
    print(f"[Mesh] Summary: {screening_json}", flush=True)
    print("[Mesh] Return summary JSON, report TXT and full wrapper log.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
