#!/usr/bin/env python3
"""Fetch, diagnose, standardize, and validate elemental bcc alpha-Fe.

Materials Project reports symmetry using its production tolerance (symprec=0.1 A),
while a much tighter tolerance can classify a numerically relaxed structure in a
lower-symmetry setting. We therefore preserve the raw MP structure, record a
symmetry-tolerance diagnostic, and generate a standardized conventional Im-3m
cell only when the MP-consistent analysis confirms space group 229.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from mp_api.client import MPRester
from pymatgen.io.cif import CifWriter
from pymatgen.io.vasp import Poscar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

OUTDIR = Path("outputs")
OUTDIR.mkdir(parents=True, exist_ok=True)

MP_SYMPREC_A = 0.1
STRICT_SYMPREC_A = 1e-3
ANGLE_TOL_DEG = 5


def _symmetry_symbol(doc) -> str | None:
    sym = getattr(doc, "symmetry", None)
    if sym is None:
        return None
    if hasattr(sym, "symbol"):
        return getattr(sym, "symbol")
    if isinstance(sym, dict):
        return sym.get("symbol")
    return None


def _symmetry_number(doc) -> int | None:
    sym = getattr(doc, "symmetry", None)
    if sym is None:
        return None
    if hasattr(sym, "number"):
        return getattr(sym, "number")
    if isinstance(sym, dict):
        return sym.get("number")
    return None


def _energy_above_hull(doc) -> float:
    value = getattr(doc, "energy_above_hull", None)
    if value is None:
        return math.inf
    return float(value)


def _serialize_candidate(doc) -> dict:
    return {
        "material_id": str(getattr(doc, "material_id", "")),
        "formula_pretty": getattr(doc, "formula_pretty", None),
        "energy_above_hull": getattr(doc, "energy_above_hull", None),
        "is_stable": getattr(doc, "is_stable", None),
        "symmetry_symbol": _symmetry_symbol(doc),
        "symmetry_number": _symmetry_number(doc),
    }


def _analyze(structure, symprec: float) -> dict:
    analyzer = SpacegroupAnalyzer(
        structure,
        symprec=symprec,
        angle_tolerance=ANGLE_TOL_DEG,
    )
    return {
        "symprec_A": symprec,
        "space_group_symbol": analyzer.get_space_group_symbol(),
        "space_group_number": analyzer.get_space_group_number(),
    }


def _lattice_payload(structure) -> dict:
    lat = structure.lattice
    return {
        "a_A": lat.a,
        "b_A": lat.b,
        "c_A": lat.c,
        "alpha_deg": lat.alpha,
        "beta_deg": lat.beta,
        "gamma_deg": lat.gamma,
        "volume_A3": structure.volume,
        "num_sites": len(structure),
    }


def main() -> int:
    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        print("ERROR: MP_API_KEY is not set.", file=sys.stderr)
        return 2

    fields = [
        "material_id",
        "formula_pretty",
        "structure",
        "energy_above_hull",
        "is_stable",
        "symmetry",
    ]

    print("Querying Materials Project for elemental Fe entries...")
    with MPRester(api_key) as mpr:
        docs = list(mpr.materials.summary.search(chemsys="Fe", fields=fields))

    elemental_fe = [d for d in docs if getattr(d, "formula_pretty", None) == "Fe"]
    candidates_payload = [_serialize_candidate(d) for d in elemental_fe]
    (OUTDIR / "Fe_query_candidates.json").write_text(
        json.dumps(candidates_payload, indent=2, default=str) + "\n"
    )

    if not elemental_fe:
        print("ERROR: Materials Project query returned no elemental Fe entries.", file=sys.stderr)
        return 3

    bcc_candidates = [
        d
        for d in elemental_fe
        if _symmetry_symbol(d) == "Im-3m" and _symmetry_number(d) in (None, 229)
    ]
    if not bcc_candidates:
        print(
            "ERROR: elemental Fe entries were found, but none were reported by "
            "Materials Project as Im-3m. See outputs/Fe_query_candidates.json.",
            file=sys.stderr,
        )
        return 4

    # Prefer a stable entry, then the lowest energy above hull. No MP-ID is
    # hard-coded; the selected ID is recorded for provenance.
    selected = min(
        bcc_candidates,
        key=lambda d: (
            not bool(getattr(d, "is_stable", False)),
            _energy_above_hull(d),
            str(getattr(d, "material_id", "")),
        ),
    )
    raw_structure = selected.structure

    strict_diag = _analyze(raw_structure, STRICT_SYMPREC_A)
    mp_diag = _analyze(raw_structure, MP_SYMPREC_A)

    print(
        "Symmetry diagnostic: "
        f"symprec={STRICT_SYMPREC_A:g} A -> {strict_diag['space_group_symbol']} "
        f"({strict_diag['space_group_number']}); "
        f"symprec={MP_SYMPREC_A:g} A -> {mp_diag['space_group_symbol']} "
        f"({mp_diag['space_group_number']})."
    )

    if not (
        mp_diag["space_group_symbol"] == "Im-3m"
        and mp_diag["space_group_number"] == 229
    ):
        print(
            "ERROR: the selected MP structure does not recover Im-3m (229) at "
            f"the Materials Project-compatible symmetry tolerance ({MP_SYMPREC_A} A).",
            file=sys.stderr,
        )
        return 5

    mp_analyzer = SpacegroupAnalyzer(
        raw_structure,
        symprec=MP_SYMPREC_A,
        angle_tolerance=ANGLE_TOL_DEG,
    )
    conventional = mp_analyzer.get_conventional_standard_structure()

    # The standardized structure is the simulation reference. It must recover
    # the target symmetry even with the stricter local diagnostic.
    standardized_diag = _analyze(conventional, STRICT_SYMPREC_A)
    if not (
        standardized_diag["space_group_symbol"] == "Im-3m"
        and standardized_diag["space_group_number"] == 229
    ):
        print(
            "ERROR: standardized conventional structure failed strict Im-3m "
            "validation. No simulation reference was accepted.",
            file=sys.stderr,
        )
        return 6

    # Preserve the raw database structure separately from the standardized
    # simulation reference so provenance is never lost.
    CifWriter(raw_structure).write_file(OUTDIR / "Fe_bulk_mp_raw.cif")
    Poscar(raw_structure).write_file(OUTDIR / "POSCAR_Fe_bulk_mp_raw")
    CifWriter(conventional).write_file(OUTDIR / "Fe_bulk_conventional.cif")
    Poscar(conventional).write_file(OUTDIR / "POSCAR_Fe_bulk")

    metadata = {
        "source": "Materials Project",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "material_id": str(selected.material_id),
        "formula": selected.formula_pretty,
        "reported_symmetry": _symmetry_symbol(selected),
        "reported_space_group_number": _symmetry_number(selected),
        "energy_above_hull_eV_per_atom": getattr(selected, "energy_above_hull", None),
        "is_stable": getattr(selected, "is_stable", None),
        "raw_structure_symmetry_strict": strict_diag,
        "raw_structure_symmetry_mp_compatible": mp_diag,
        "standardized_structure_symmetry_strict": standardized_diag,
        "raw_structure_lattice": _lattice_payload(raw_structure),
        "standardized_conventional_lattice": _lattice_payload(conventional),
        "simulation_reference": "outputs/POSCAR_Fe_bulk",
        "provenance_reference": "outputs/POSCAR_Fe_bulk_mp_raw",
        "selection_rule": (
            "elemental Fe; Materials Project-reported Im-3m/229; prefer stable entry; "
            "then lowest energy_above_hull"
        ),
        "symmetry_policy": (
            "Preserve raw MP structure; diagnose at symprec=1e-3 A and at the "
            "MP-compatible symprec=0.1 A; accept only if the latter is Im-3m/229; "
            "standardize to a conventional Im-3m cell and revalidate that cell at "
            "symprec=1e-3 A."
        ),
    }

    (OUTDIR / "Fe_bulk_metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str) + "\n"
    )

    print("Selected Materials Project entry:")
    print(json.dumps(metadata, indent=2, default=str))
    print("Wrote:")
    print("  outputs/Fe_bulk_mp_raw.cif")
    print("  outputs/POSCAR_Fe_bulk_mp_raw")
    print("  outputs/Fe_bulk_conventional.cif")
    print("  outputs/POSCAR_Fe_bulk")
    print("  outputs/Fe_bulk_metadata.json")
    print("  outputs/Fe_query_candidates.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
