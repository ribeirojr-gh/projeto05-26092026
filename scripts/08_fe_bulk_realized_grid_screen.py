#!/usr/bin/env python3
"""One-variable MeshCutoff study of alpha-Fe using the *realized* SIESTA FFT grid.

All calculations keep the same Fe PSML, fixed two-atom geometry, PBE/DZP,
spin initialization, k-mesh, smearing and SCF settings. Not a convergence claim.
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

from ase.calculators.siesta import Siesta
from ase.io import read
from ase.units import Ry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
CUTS = (850, 1000, 1250, 1500)
KPTS = (6, 6, 6)
PAO_SHIFT_RY = 0.02
SCF_MAX = 120
INIT_MAG = 2.2

SCF_RE = re.compile(r"SCF cycle converged after\s+(\d+)\s+iterations", re.I)
ETOT_RE = re.compile(r"(?m)^\s*siesta:\s+Etot\s*=\s*([-+0-9.eEdD]+)")
SPIN_RE = re.compile(r"spin moment:.*?([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$", re.I)
PRESSURE_RE = re.compile(
    r"(?m)^\s*siesta:\s+([-+0-9.eEdD]+)\s+[-+0-9.eEdD]+\s+kBar\s*$"
)
MESH_RE = re.compile(
    r"InitMesh:\s*MESH\s*=\s*(\d+)\s*x\s*(\d+)\s*x\s*(\d+)\s*=\s*(\d+)"
)
ACTUAL_RE = re.compile(
    r"InitMesh:\s*Mesh cutoff \(required, used\)\s*=\s*"
    r"([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)\s+Ry"
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_number(text: str) -> float:
    n = float(text.replace("D", "E").replace("d", "e"))
    if not math.isfinite(n):
        raise ValueError("Non-finite native SIESTA observable")
    return n


def validated_inputs(pseudos: Path):
    required = {
        "bulk": OUT / "POSCAR_Fe_bulk",
        "bulk_metadata": OUT / "Fe_bulk_metadata.json",
        "psml_audit": OUT / "siesta_preflight.json",
        "pilot": OUT / "fe_bulk_siesta_pilot_summary.json",
        "extension": OUT / "fe_bulk_mesh_cutoff_extension_summary.json",
    }
    for name, path in required.items():
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite {name}: {path}")
    meta = json.loads(required["bulk_metadata"].read_text())
    audit = json.loads(required["psml_audit"].read_text())
    pilot = json.loads(required["pilot"].read_text())
    previous = json.loads(required["extension"].read_text())
    fe_hash = audit["pseudos"]["Fe"]["sha256"]
    if meta.get("formula") != "Fe" or meta.get(
        "standardized_structure_symmetry_strict", {}
    ).get("space_group_number") != 229:
        raise RuntimeError("Validated alpha-Fe bulk symmetry not confirmed.")
    if not audit.get("preflight_passed") or not pilot.get("ase_returned_finite_energy"):
        raise RuntimeError("SIESTA PSML preflight or initial pilot was not validated.")
    if digest(pseudos / "Fe.psml") != fe_hash or pilot.get("Fe_psml_sha256") != fe_hash:
        raise RuntimeError("Fe.psml differs from the preflight or previous pilot.")
    if (
        previous.get("mesh_cutoff_grid_Ry") != [550, 650, 750, 850]
        or previous.get("n_completed") != 4
        or previous.get("all_scf_converged") is not True
        or previous.get("Fe_psml_sha256") != fe_hash
        or previous.get("geometry") != "outputs/POSCAR_Fe_bulk"
        or previous.get("basis") != "DZP"
        or previous.get("k_points") != list(KPTS)
        or previous.get("energy_shift_Ry") != PAO_SHIFT_RY
        or previous.get("electronic_temperature_K") != 300
        or [r.get("cutoff_Ry") for r in previous.get("results", [])] != [550, 650, 750, 850]
    ):
        raise RuntimeError("Previous 550–850 Ry screening summary is incomplete/incompatible.")
    atoms = read(required["bulk"], format="vasp")
    if len(atoms) != 2 or set(atoms.get_chemical_symbols()) != {"Fe"} or not all(atoms.pbc):
        raise RuntimeError("Expected periodic two-atom alpha-Fe conventional cell.")
    return atoms, meta, audit, previous, fe_hash


def parse_native(out_file: Path, requested: int) -> dict:
    if not out_file.is_file():
        raise RuntimeError(f"Missing native SIESTA output: {out_file}")
    native = out_file.read_text(errors="replace")
    if "Job completed" not in native or "Fe.1.psml" not in native:
        raise RuntimeError("SIESTA did not finish or document the Fe PSML.")
    grids = MESH_RE.findall(native)
    cutoffs = ACTUAL_RE.findall(native)
    scfs = SCF_RE.findall(native)
    etots = ETOT_RE.findall(native)
    spin = [m for line in native.splitlines() if "spin moment:" in line.lower()
            for m in [SPIN_RE.search(line)] if m is not None]
    pressure_part = native.rsplit("Pressure (static):", 1)
    pressures = PRESSURE_RE.findall(pressure_part[-1]) if len(pressure_part) == 2 else []
    if not all((grids, cutoffs, scfs, etots, spin, pressures)):
        raise RuntimeError("Native output missing realized grid, cutoff, SCF, energy, spin or pressure.")
    dims = tuple(map(int, grids[-1][:3]))
    points = int(grids[-1][3])
    if math.prod(dims) != points:
        raise RuntimeError("SIESTA FFT-grid dimensions and total-point count disagree.")
    required, used = map(finite_number, cutoffs[-1])
    if abs(required - requested) > 0.01 or used + 0.01 < required:
        raise RuntimeError("Native SIESTA requested/used cutoff inconsistent with ASE input.")
    return {
        "realized_fft_mesh": list(dims),
        "realized_fft_mesh_points": points,
        "native_required_cutoff_Ry": required,
        "native_used_cutoff_Ry": used,
        "native_energy_eV_cell": finite_number(etots[-1]),
        "spin_moment_muB_cell": finite_number(spin[-1].group(1)),
        "pressure_static_kbar": finite_number(pressures[0]),
        "scf_iterations": int(scfs[-1]),
        "scf_converged": True,
        "native_job_completed": True,
    }


def run_point(atoms, cutoff: int, root: Path, command: str, pseudos: Path) -> dict:
    label = f"Fe_bulk_mesh_{cutoff}Ry"
    directory = root / f"mesh_{cutoff}Ry"
    directory.mkdir(parents=True, exist_ok=False)
    calc = Siesta(
        label=label,
        directory=str(directory),
        command=command,
        pseudo_path=str(pseudos),
        pseudo_qualifier="",
        symlink_pseudos=True,
        xc="PBE",
        mesh_cutoff=cutoff * Ry,
        energy_shift=PAO_SHIFT_RY * Ry,
        basis_set="DZP",
        kpts=list(KPTS),
        spin="collinear",
        fdf_arguments={
            "ElectronicTemperature": "300 K",
            "SCF.DM.Tolerance": 1.0e-4,
            "MaxSCFIterations": SCF_MAX,
            "DM.MixingWeight": 0.05,
            "SCFMustConverge": True,
            "Charge.Mulliken": "end",
            "DM.UseSaveDM": False,
        },
    )
    crystal = atoms.copy()
    crystal.set_initial_magnetic_moments([INIT_MAG] * len(crystal))
    crystal.calc = calc
    ase_energy = float(crystal.get_potential_energy())
    fdf = directory / f"{label}.fdf"
    native_out = directory / f"{label}.out"
    if not fdf.is_file():
        raise RuntimeError(f"{label}: missing generated FDF.")
    fdf_text = fdf.read_text(errors="replace")
    if not re.search(r"(?im)^\s*Spin\s+collinear\b", fdf_text) or not re.search(
        r"(?im)^\s*%block\s+DM\.InitSpin\b", fdf_text
    ):
        raise RuntimeError(f"{label}: missing collinear spin or initial moments.")
    native = parse_native(native_out, cutoff)
    if abs(ase_energy - native["native_energy_eV_cell"]) > 1e-3:
        raise RuntimeError(f"{label}: ASE/native energies disagree by >1 meV/cell.")
    return {
        "cutoff_Ry": cutoff,
        "energy_eV_cell": ase_energy,
        "energy_eV_per_atom": ase_energy / len(crystal),
        "moment_muB_per_Fe": native["spin_moment_muB_cell"] / len(crystal),
        **native,
        "run_dir": str(directory.relative_to(ROOT)),
        "input_FDF": str(fdf.relative_to(ROOT)),
        "native_output": str(native_out.relative_to(ROOT)),
    }


def main() -> int:
    command = os.environ.get("ASE_SIESTA_COMMAND", "")
    if "PREFIX.fdf" not in command or "PREFIX.out" not in command:
        raise RuntimeError("ASE_SIESTA_COMMAND lacks PREFIX.fdf and PREFIX.out.")
    pseudos = Path(os.path.expanduser(
        os.environ.get("SIESTA_PS_PATH", "~/Pacotes/PSEUDOS/DOJO-PSML")
    )).resolve()
    atoms, meta, audit, previous, fe_hash = validated_inputs(pseudos)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    root = OUT / "dft" / "fe_bulk_realized_grid" / stamp
    root.mkdir(parents=True, exist_ok=False)
    settings = {
        "purpose": "Fe bulk SIESTA single-variable MeshCutoff study with realized FFT grids",
        "run_id": stamp,
        "source_material_id": meta["material_id"],
        "Fe_psml_sha256": fe_hash,
        "geometry": "outputs/POSCAR_Fe_bulk",
        "functional": "PBE",
        "basis": "DZP",
        "energy_shift_Ry": PAO_SHIFT_RY,
        "k_points": list(KPTS),
        "initial_moments_muB_per_Fe": INIT_MAG,
        "electronic_temperature_K": 300,
        "SCF_DM_tolerance": 1e-4,
        "SCF_max_iterations": SCF_MAX,
        "MPI_ranks": int(os.environ.get("SIESTA_MPI_RANKS", "2")),
        "cutoff_requests_Ry": list(CUTS),
        "previous_extension_run_id": previous.get("run_id"),
        "not_a_final_convergence_claim": True,
    }
    (root / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    rows = []
    for cutoff in CUTS:
        print(f"[Real grid] Running fixed Fe bulk at requested {cutoff} Ry", flush=True)
        try:
            row = run_point(atoms, cutoff, root, command, pseudos)
            if cutoff == 850:
                old = previous["results"][-1]
                de = 1000 * (row["energy_eV_per_atom"] - old["energy_eV_per_atom"])
                dm = row["moment_muB_per_Fe"] - old["moment_muB_per_Fe"]
                dp = row["pressure_static_kbar"] - old["pressure_static_kbar"]
                row["anchor_delta_E_meV_per_Fe"] = de
                row["anchor_delta_M_muB_per_Fe"] = dm
                row["anchor_delta_P_kbar"] = dp
                if abs(de) > 0.5 or abs(dm) > 0.005 or abs(dp) > 0.5:
                    raise RuntimeError(
                        f"850 Ry repeat mismatch: dE={de:+.4f} meV/Fe, "
                        f"dM={dm:+.6f} muB/Fe, dP={dp:+.4f} kbar."
                    )
                print(
                    f"[Real grid] 850 Ry reproducibility anchor: dE={de:+.4f} meV/Fe, "
                    f"dM={dm:+.6f} muB/Fe, dP={dp:+.4f} kbar",
                    flush=True,
                )
            rows.append(row)
            (root / "partial_results.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(
                f"[Real grid] {cutoff} Ry -> {row['realized_fft_mesh']} "
                f"(used {row['native_used_cutoff_Ry']:.3f} Ry); "
                f"E={row['energy_eV_per_atom']:.8f} eV/Fe; "
                f"M={row['moment_muB_per_Fe']:.6f} muB/Fe; "
                f"P={row['pressure_static_kbar']:.3f} kbar",
                flush=True,
            )
        except Exception:
            (root / "failure.json").write_text(
                json.dumps({**settings, "completed": rows, "failed_cutoff_Ry": cutoff,
                            "traceback": traceback.format_exc()}, indent=2) + "\n"
            )
            print(f"[Real grid] FAILED; inspect {root / 'failure.json'}", file=sys.stderr)
            raise

    ref = rows[-1]
    for row in rows:
        row["delta_E_vs_1500_meV_per_Fe"] = (
            row["energy_eV_per_atom"] - ref["energy_eV_per_atom"]
        ) * 1000.0
        row["delta_M_vs_1500_muB_per_Fe"] = (
            row["moment_muB_per_Fe"] - ref["moment_muB_per_Fe"]
        )
        row["delta_P_vs_1500_kbar"] = (
            row["pressure_static_kbar"] - ref["pressure_static_kbar"]
        )
    distinct = len({tuple(row["realized_fft_mesh"]) for row in rows})
    result = {
        **settings, "n_expected": len(CUTS), "n_completed": len(rows),
        "all_scf_converged": all(row["scf_converged"] for row in rows),
        "n_distinct_realized_fft_grids": distinct, "results": rows,
        "interpretation": (
            "Identical requested cutoffs may map to identical FFT grids. "
            "Only distinct realized meshes provide independent grid-resolution evidence. "
            "1500 Ry is a screening endpoint, NOT an approved production cutoff. "
            "Basis, k-point and lattice convergence remain pending."
        ),
    }
    (OUT / "fe_bulk_realized_grid_summary.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    columns = [
        "cutoff_Ry", "native_used_cutoff_Ry", "realized_fft_mesh",
        "energy_eV_per_atom", "delta_E_vs_1500_meV_per_Fe",
        "moment_muB_per_Fe", "delta_M_vs_1500_muB_per_Fe",
        "pressure_static_kbar", "delta_P_vs_1500_kbar",
        "scf_iterations", "native_output",
    ]
    with (OUT / "fe_bulk_realized_grid_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{key: row.get(key) for key in columns} for row in rows])
    lines = [
        "Alpha-Fe SIESTA MeshCutoff screening: requested versus realized FFT grids",
        "======================================================================",
        "Fixed cell, PBE/DZP, approved Fe semicore PSML, 6x6x6 k-mesh, 300 K.",
        " Ry     FFT grid     Used Ry    E(eV/Fe)       dE(meV/Fe)  M(muB/Fe) P(kbar)",
    ]
    for row in rows:
        dims = "x".join(map(str, row["realized_fft_mesh"]))
        lines.append(
            f"{row['cutoff_Ry']:4d} {dims:>12} {row['native_used_cutoff_Ry']:10.3f} "
            f"{row['energy_eV_per_atom']:14.7f} "
            f"{row['delta_E_vs_1500_meV_per_Fe']:11.4f} "
            f"{row['moment_muB_per_Fe']:10.6f} "
            f"{row['pressure_static_kbar']:8.3f}"
        )
    lines += [
        f"Distinct realized FFT meshes: {distinct} out of {len(CUTS)} requested cutoffs.",
        "No final MeshCutoff, basis, k-point or equilibrium lattice selected.",
    ]
    (OUT / "fe_bulk_realized_grid_report.txt").write_text("\n".join(lines) + "\n")
    print(f"[Real grid] All points finished; distinct realized FFT grids: {distinct}", flush=True)
    print("[Real grid] Return summary JSON, report TXT and wrapper log for review.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
