#!/usr/bin/env python3
"""Build and geometrically validate candidate alpha-Fe surface slabs.

This is the second auditable task of Step 02. It consumes the already validated
standardized bcc alpha-Fe reference in ``outputs/POSCAR_Fe_bulk`` and builds a
small, explicit candidate library for Fe(110), Fe(100), and Fe(111).

Important: this script performs *geometric* validation only. It does not claim
surface-energy, slab-thickness, or vacuum convergence. Final production slabs
must later be selected from electronic-structure convergence calculations.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from ase.build import surface
from ase.io import read, write

ROOT = Path(__file__).resolve().parents[1]
BULK_POSCAR = ROOT / "outputs" / "POSCAR_Fe_bulk"
BULK_METADATA = ROOT / "outputs" / "Fe_bulk_metadata.json"
OUTDIR = ROOT / "outputs" / "surfaces"

# Candidate library only. These values are deliberately not called converged.
LAYER_COUNTS = (7, 9, 11)
TOTAL_VACUUM_A = (15.0, 20.0)
SURFACES = {
    "Fe110": {"miller": (1, 1, 0), "role": "primary"},
    "Fe100": {"miller": (1, 0, 0), "role": "sensitivity"},
    "Fe111": {"miller": (1, 1, 1), "role": "sensitivity"},
}

# Purely geometric sanity thresholds; not convergence criteria.
MIN_ALLOWED_DISTANCE_A = 1.80
MIN_REALIZED_VACUUM_A = 14.0
NORMAL_ALIGNMENT_MIN = 0.999


def _load_and_validate_bulk():
    if not BULK_POSCAR.is_file():
        raise FileNotFoundError(f"Missing validated bulk reference: {BULK_POSCAR}")
    if not BULK_METADATA.is_file():
        raise FileNotFoundError(f"Missing bulk metadata: {BULK_METADATA}")

    meta = json.loads(BULK_METADATA.read_text())
    if meta.get("formula") != "Fe":
        raise RuntimeError(f"Bulk metadata formula is not Fe: {meta.get('formula')!r}")

    std = meta.get("standardized_structure_symmetry_strict", {})
    if std.get("space_group_symbol") != "Im-3m" or std.get("space_group_number") != 229:
        raise RuntimeError(
            "Bulk reference has not passed strict standardized Im-3m (229) validation."
        )

    atoms = read(BULK_POSCAR, format="vasp")
    if set(atoms.get_chemical_symbols()) != {"Fe"}:
        raise RuntimeError("Bulk POSCAR contains species other than Fe.")

    lengths = np.asarray(atoms.cell.lengths(), dtype=float)
    angles = np.asarray(atoms.cell.angles(), dtype=float)
    if not np.allclose(lengths, lengths[0], rtol=1e-5, atol=1e-5):
        raise RuntimeError(f"Validated bulk reference is not cubic in length: {lengths}")
    if not np.allclose(angles, [90.0, 90.0, 90.0], rtol=0.0, atol=1e-5):
        raise RuntimeError(f"Validated bulk reference is not cubic in angle: {angles}")

    return atoms, meta


def _layer_count_from_projection(projections: np.ndarray, tol_a: float = 0.20) -> int:
    values = sorted(float(x) for x in projections)
    if not values:
        return 0
    layers = 1
    anchor = values[0]
    for value in values[1:]:
        if abs(value - anchor) > tol_a:
            layers += 1
            anchor = value
    return layers


def _minimum_distance(atoms) -> float:
    distances = np.asarray(atoms.get_all_distances(mic=True), dtype=float)
    np.fill_diagonal(distances, np.inf)
    value = float(np.min(distances))
    return value


def _geometry_metrics(atoms) -> dict:
    cell = np.asarray(atoms.cell.array, dtype=float)
    a_vec, b_vec, c_vec = cell
    cross = np.cross(a_vec, b_vec)
    area = float(np.linalg.norm(cross))
    if area <= 0.0:
        raise RuntimeError("Degenerate slab surface area.")
    normal = cross / area
    c_norm = float(np.linalg.norm(c_vec))
    if c_norm <= 0.0:
        raise RuntimeError("Degenerate slab c vector.")

    alignment = float(abs(np.dot(c_vec / c_norm, normal)))
    height = float(abs(np.dot(c_vec, normal)))
    projections = np.dot(np.asarray(atoms.positions, dtype=float), normal)
    thickness = float(np.max(projections) - np.min(projections))
    realized_vacuum = float(height - thickness)

    return {
        "n_atoms": int(len(atoms)),
        "surface_area_A2": area,
        "cell_height_normal_A": height,
        "slab_thickness_A": thickness,
        "realized_total_vacuum_A": realized_vacuum,
        "normal_c_alignment": alignment,
        "detected_atomic_layers": _layer_count_from_projection(projections),
        "minimum_pair_distance_A": _minimum_distance(atoms),
        "cell_lengths_A": [float(x) for x in atoms.cell.lengths()],
        "cell_angles_deg": [float(x) for x in atoms.cell.angles()],
    }


def _safe_tag(vacuum_a: float) -> str:
    return str(int(round(vacuum_a))) if math.isclose(vacuum_a, round(vacuum_a)) else str(vacuum_a).replace(".", "p")


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    bulk, bulk_meta = _load_and_validate_bulk()

    print("Validated bulk reference:")
    print(f"  Materials Project ID: {bulk_meta.get('material_id')}")
    print(f"  standardized a = {bulk.cell.lengths()[0]:.8f} A")
    print("Building geometric candidate library (not a DFT convergence claim).")

    records: list[dict] = []

    for label, spec in SURFACES.items():
        miller = tuple(int(x) for x in spec["miller"])
        for layers in LAYER_COUNTS:
            for total_vac in TOTAL_VACUUM_A:
                # ASE's center(vacuum=x) adds x on each side. We therefore use
                # total_vac/2 so the periodic slab-to-slab gap is ~total_vac.
                slab = surface(bulk, miller, layers, vacuum=None, periodic=True)
                slab.center(vacuum=total_vac / 2.0, axis=2)
                slab.wrap()

                metrics = _geometry_metrics(slab)
                checks = {
                    "composition_is_pure_Fe": set(slab.get_chemical_symbols()) == {"Fe"},
                    "no_unphysical_overlap": metrics["minimum_pair_distance_A"] >= MIN_ALLOWED_DISTANCE_A,
                    "vacuum_meets_geometric_minimum": metrics["realized_total_vacuum_A"] >= MIN_REALIZED_VACUUM_A,
                    "c_axis_aligned_with_surface_normal": metrics["normal_c_alignment"] >= NORMAL_ALIGNMENT_MIN,
                    "pbc_xyz_enabled": bool(np.all(slab.pbc)),
                }
                passed = all(checks.values())

                vac_tag = _safe_tag(total_vac)
                stem = f"{label}_L{layers:02d}_V{vac_tag}A"
                poscar_path = OUTDIR / f"POSCAR_{stem}"
                cif_path = OUTDIR / f"{stem}.cif"

                write(poscar_path, slab, format="vasp", direct=True, sort=True, vasp5=True)
                write(cif_path, slab, format="cif")

                record = {
                    "label": label,
                    "role": spec["role"],
                    "miller_index": list(miller),
                    "layers_requested": int(layers),
                    "total_vacuum_requested_A": float(total_vac),
                    **metrics,
                    "checks": checks,
                    "validation_passed": passed,
                    "poscar": str(poscar_path.relative_to(ROOT)),
                    "cif": str(cif_path.relative_to(ROOT)),
                }
                records.append(record)

                status = "PASS" if passed else "FAIL"
                print(
                    f"[{status}] {stem}: atoms={metrics['n_atoms']}, "
                    f"detected_layers={metrics['detected_atomic_layers']}, "
                    f"thickness={metrics['slab_thickness_A']:.3f} A, "
                    f"vacuum={metrics['realized_total_vacuum_A']:.3f} A, "
                    f"dmin={metrics['minimum_pair_distance_A']:.3f} A"
                )

    failures = [r for r in records if not r["validation_passed"]]

    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "bulk_reference": str(BULK_POSCAR.relative_to(ROOT)),
        "bulk_material_id": bulk_meta.get("material_id"),
        "purpose": "geometric candidate library for later DFT slab/vacuum convergence tests",
        "not_a_convergence_claim": True,
        "primary_surface": "Fe110",
        "candidate_layer_counts": list(LAYER_COUNTS),
        "candidate_total_vacuum_A": list(TOTAL_VACUUM_A),
        "validation_thresholds": {
            "minimum_pair_distance_A": MIN_ALLOWED_DISTANCE_A,
            "minimum_realized_total_vacuum_A": MIN_REALIZED_VACUUM_A,
            "minimum_normal_c_alignment": NORMAL_ALIGNMENT_MIN,
        },
        "n_candidates": len(records),
        "n_failed": len(failures),
        "candidates": records,
    }
    (OUTDIR / "surface_library.json").write_text(json.dumps(payload, indent=2) + "\n")

    csv_fields = [
        "label",
        "role",
        "miller_index",
        "layers_requested",
        "total_vacuum_requested_A",
        "n_atoms",
        "detected_atomic_layers",
        "surface_area_A2",
        "slab_thickness_A",
        "realized_total_vacuum_A",
        "minimum_pair_distance_A",
        "normal_c_alignment",
        "validation_passed",
        "poscar",
        "cif",
    ]
    with (OUTDIR / "surface_library.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for r in records:
            row = {k: r.get(k) for k in csv_fields}
            row["miller_index"] = "".join(str(x) for x in r["miller_index"])
            writer.writerow(row)

    lines = [
        "Alpha-Fe geometric slab candidate library",
        "=========================================",
        f"Bulk source: {bulk_meta.get('material_id')}",
        "Primary orientation for later DFT: Fe(110)",
        "Fe(100) and Fe(111) are sensitivity/comparison orientations.",
        "",
        "This stage validates geometry only. No candidate is declared DFT-converged.",
        "",
    ]
    for r in records:
        lines.append(
            f"{r['label']:5s} L={r['layers_requested']:2d} V={r['total_vacuum_requested_A']:4.0f} A "
            f"atoms={r['n_atoms']:3d} thickness={r['slab_thickness_A']:7.3f} A "
            f"vacuum={r['realized_total_vacuum_A']:7.3f} A "
            f"dmin={r['minimum_pair_distance_A']:6.3f} A "
            f"{'PASS' if r['validation_passed'] else 'FAIL'}"
        )
    (OUTDIR / "surface_library_report.txt").write_text("\n".join(lines) + "\n")

    if failures:
        print(f"ERROR: {len(failures)} slab candidate(s) failed geometric validation.", file=sys.stderr)
        print("See outputs/surfaces/surface_library.json for diagnostics.", file=sys.stderr)
        return 20

    expected = len(SURFACES) * len(LAYER_COUNTS) * len(TOTAL_VACUUM_A)
    if len(records) != expected:
        print(f"ERROR: expected {expected} candidates, generated {len(records)}.", file=sys.stderr)
        return 21

    print(f"Geometric validation PASSED for all {len(records)} candidate slabs.")
    print("Wrote outputs/surfaces/surface_library.json")
    print("Wrote outputs/surfaces/surface_library.csv")
    print("Wrote outputs/surfaces/surface_library_report.txt")
    print("No final production slab has been selected yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
