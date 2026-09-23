#!/usr/bin/env python3
"""Audit actual local SIESTA/ASE availability and Fe/O PSML headers.

Preflight only: this script performs no DFT calculation, installs no packages,
and does not alter the pseudopotentials. It reads *full* local PSML files,
which is required before approving them for a production calculation.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
PSEUDO_DIR = Path(
    os.path.expanduser(os.environ.get(
        "SIESTA_PS_PATH", "~/Pacotes/PSEUDOS/DOJO-PSML"
    ))
).resolve()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def psml(element: str) -> dict:
    path = PSEUDO_DIR / (element + ".psml")
    item = {"element": element, "path": str(path), "exists": path.is_file()}
    if not path.is_file():
        item["error"] = "PSML file not found"
        return item
    item["size_bytes"] = path.stat().st_size
    item["sha256"] = sha256(path)
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        if root.tag.split("}")[-1] != "psml":
            raise ValueError("Root is not a PSML document")
        atom = root.find(".//{*}pseudo-atom-spec")
        provenance = root.find(".//{*}provenance")
        xc = root.find(".//{*}exchange-correlation")
        valence = root.find(".//{*}valence-configuration")
        if atom is None or xc is None or valence is None:
            raise ValueError("Missing pseudo-atom, XC, or valence metadata")
        xc_notes = [x.attrib for x in xc.iter() if x.tag.split("}")[-1] in ("annotation", "functional")]
        shells = [dict(x.attrib) for x in valence.findall(".//{*}shell")]
        item.update({
            "psml_version": root.attrib.get("version"),
            "generator": provenance.attrib.get("creator") if provenance is not None else None,
            "generation_date": provenance.attrib.get("date") if provenance is not None else None,
            "atomic_label": atom.attrib.get("atomic-label"),
            "z_pseudo": float(atom.attrib["z-pseudo"]),
            "relativity": atom.attrib.get("relativity"),
            "spin_dft_generation": atom.attrib.get("spin-dft"),
            "core_corrections": atom.attrib.get("core-corrections"),
            "xc_entries": xc_notes,
            "shells": shells,
            "total_valence_charge": float(valence.attrib["total-valence-charge"]),
        })
        xc_text = json.dumps(xc_notes).lower()
        item["xc_is_pbe"] = "perdew" in xc_text and "burke" in xc_text and "ernzerhof" in xc_text
        item["valid_xml"] = True
    except Exception as exc:
        item["valid_xml"] = False
        item["error"] = f"{type(exc).__name__}: {exc}"
    return item


def command_version(name: str) -> dict:
    path = shutil.which(name)
    obj = {"path": path, "present": path is not None}
    if path:
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True,
                timeout=15, check=False,
            )
            obj["exit_code"] = result.returncode
            obj["version_text"] = (result.stdout + result.stderr).strip()[:1800]
        except Exception as exc:
            obj["version_error"] = f"{type(exc).__name__}: {exc}"
    return obj


def main() -> int:
    issues = []
    fe, oxygen = psml("Fe"), psml("O")
    for element, item, expected_z in (("Fe", fe, 16), ("O", oxygen, 6)):
        if not item.get("valid_xml"):
            issues.append(f"{element}: {item.get('error', 'invalid or missing PSML')}")
            continue
        if item["atomic_label"] != element:
            issues.append(f"{element}: wrong atomic label: {item['atomic_label']}")
        if item["z_pseudo"] != expected_z or item["total_valence_charge"] != expected_z:
            issues.append(f"{element}: expected {expected_z} valence electrons; check pseudo")
        if item["relativity"] != "scalar":
            issues.append(f"{element}: expected scalar-relativistic pseudo")
        if not item["xc_is_pbe"]:
            issues.append(f"{element}: PBE was not confirmed by XC metadata")
    if fe.get("valid_xml"):
        shell_keys = {(s.get("n"), s.get("l")) for s in fe.get("shells", [])}
        if not {("3", "s"), ("3", "p")}.issubset(shell_keys):
            issues.append("Fe: 3s/3p semicore shells not found in valence metadata")

    try:
        from ase.calculators.siesta import Siesta  # noqa: F401
        ase_version = importlib.metadata.version("ase")
        ase_siesta = True
    except Exception as exc:
        ase_version = None
        ase_siesta = False
        issues.append(f"ASE–SIESTA calculator import failed: {type(exc).__name__}: {exc}")

    siesta = command_version("siesta")
    if not siesta["present"]:
        issues.append("SIESTA executable missing from PATH")
    report = {
        "purpose": "Fe/O PSML and ASE–SIESTA preflight; no DFT calculation",
        "pseudo_dir": str(PSEUDO_DIR),
        "siesta": siesta,
        "mpi_launcher": shutil.which("mpirun"),
        "ase": {"available": ase_siesta, "version": ase_version},
        "pseudos": {"Fe": fe, "O": oxygen},
        "issues": issues,
        "preflight_passed": not issues,
        "limitations": [
            "Full PSML metadata and hashes were checked, not transferability or numerical convergence.",
            "SIESTA compiled MPI, PSML runtime reading, and spin-polarized SCF still require a separate pilot.",
            "Pseudo spin-dft=no describes generation and is not proof that spin-polarized calculations are forbidden.",
        ],
    }
    (OUT / "siesta_preflight.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "Step 03 — SIESTA/ASE and PSML preflight",
        "=====================================",
        f"SIESTA path: {siesta['path'] or 'not found'}",
        f"ASE–SIESTA calculator: {'available' if ase_siesta else 'NOT available'}"
        + (f" (ASE {ase_version})" if ase_version else ""),
        f"PSML directory: {PSEUDO_DIR}",
    ]
    for item in (fe, oxygen):
        label = item["element"]
        if item.get("valid_xml"):
            lines += [
                f"{label}: PSML XML valid; PBE={item['xc_is_pbe']}; "
                f"relativity={item['relativity']}; z={item['z_pseudo']:g}; "
                f"core corrections={item['core_corrections']}",
                f"{label} SHA256: {item['sha256']}",
            ]
        else:
            lines.append(f"{label}: ERROR {item.get('error', 'invalid')}")
    lines += [f"Preflight {'PASSED' if not issues else 'FAILED'}"]
    lines += [f"ISSUE: {problem}" for problem in issues]
    lines.append("No DFT calculation executed; pilot and convergence remain pending.")
    (OUT / "siesta_preflight.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if not issues else 21


if __name__ == "__main__":
    sys.exit(main())
