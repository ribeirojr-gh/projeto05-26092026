#!/usr/bin/env python3
"""Fetch and validate elemental bcc Fe from the Materials Project.

This is intentionally the first and only structural-model script in the
initial Step 02 branch. It does not assume a Materials Project ID in advance;
it queries the database and selects an elemental Fe entry with Im-3m symmetry.
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


def _symmetry_symbol(doc) -> str | None:
    sym = getattr(doc, "symmetry", None)
    if sym is None:
        return None
    if hasattr(sym, "symbol"):
        return getattr(sym, "symbol")
    if isinstance(sym, dict):
        return sym.get("symbol")
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

    bcc_candidates = [d for d in elemental_fe if _symmetry_symbol(d) == "Im-3m"]
    if not bcc_candidates:
        print(
            "ERROR: elemental Fe entries were found, but none had Im-3m symmetry. "
            "See outputs/Fe_query_candidates.json.",
            file=sys.stderr,
        )
        return 4

    selected = min(bcc_candidates, key=_energy_above_hull)
    structure = selected.structure

    analyzer = SpacegroupAnalyzer(structure, symprec=1e-3, angle_tolerance=5)
    verified_symbol = analyzer.get_space_group_symbol()
    verified_number = analyzer.get_space_group_number()

    if verified_symbol != "Im-3m":
        print(
            f"ERROR: pymatgen independently identified {verified_symbol} instead of Im-3m.",
            file=sys.stderr,
        )
        return 5

    conventional = analyzer.get_conventional_standard_structure()

    CifWriter(structure).write_file(OUTDIR / "Fe_bulk_mp.cif")
    Poscar(structure).write_file(OUTDIR / "POSCAR_Fe_bulk")
    CifWriter(conventional).write_file(OUTDIR / "Fe_bulk_conventional.cif")

    metadata = {
        "source": "Materials Project",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "material_id": str(selected.material_id),
        "formula": selected.formula_pretty,
        "reported_symmetry": _symmetry_symbol(selected),
        "verified_space_group": verified_symbol,
        "verified_space_group_number": verified_number,
        "energy_above_hull_eV_per_atom": getattr(selected, "energy_above_hull", None),
        "is_stable": getattr(selected, "is_stable", None),
        "num_sites": len(structure),
        "lattice_a_A": structure.lattice.a,
        "lattice_b_A": structure.lattice.b,
        "lattice_c_A": structure.lattice.c,
        "alpha_deg": structure.lattice.alpha,
        "beta_deg": structure.lattice.beta,
        "gamma_deg": structure.lattice.gamma,
        "volume_A3": structure.volume,
        "selection_rule": "elemental Fe; Im-3m symmetry; lowest energy_above_hull among matching Materials Project entries",
    }

    (OUTDIR / "Fe_bulk_metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str) + "\n"
    )

    print("Selected Materials Project entry:")
    print(json.dumps(metadata, indent=2, default=str))
    print("Wrote:")
    print("  outputs/Fe_bulk_mp.cif")
    print("  outputs/POSCAR_Fe_bulk")
    print("  outputs/Fe_bulk_conventional.cif")
    print("  outputs/Fe_bulk_metadata.json")
    print("  outputs/Fe_query_candidates.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
