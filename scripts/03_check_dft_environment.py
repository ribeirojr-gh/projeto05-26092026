#!/usr/bin/env python3
"""Audit the local workstation before any DFT production calculation.

This script does not install or run a DFT engine. It records the executable and
Python-package environment, basic CPU/RAM information, and NVIDIA GPU visibility
so the next calculation can be configured reproducibly for this workstation.
"""

from __future__ import annotations

import importlib.metadata as md
import importlib.util
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "outputs"
OUTDIR.mkdir(parents=True, exist_ok=True)


def run_version(cmd: list[str]) -> str | None:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=15, check=False)
        text = (p.stdout or "").strip()
        return text[:4000] if text else None
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def pkg(name: str) -> dict:
    present = importlib.util.find_spec(name) is not None
    version = None
    if present:
        for candidate in (name, name.replace("_", "-")):
            try:
                version = md.version(candidate)
                break
            except md.PackageNotFoundError:
                pass
    return {"present": present, "version": version}


def memory_gib() -> float | None:
    p = Path("/proc/meminfo")
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.startswith("MemTotal:"):
            kb = float(line.split()[1])
            return kb / 1024.0 / 1024.0
    return None


def exe(name: str) -> dict:
    path = shutil.which(name)
    return {"present": path is not None, "path": path}


def main() -> int:
    commands = {name: exe(name) for name in [
        "siesta", "gpaw", "mpirun", "mpiexec", "srun", "nvidia-smi", "gcc", "gfortran"
    ]}

    siesta_ver = run_version([commands["siesta"]["path"], "--version"]) if commands["siesta"]["present"] else None
    gpaw_ver = run_version([commands["gpaw"]["path"], "--version"]) if commands["gpaw"]["present"] else None
    mpi_ver = None
    if commands["mpirun"]["present"]:
        mpi_ver = run_version([commands["mpirun"]["path"], "--version"])
    elif commands["mpiexec"]["present"]:
        mpi_ver = run_version([commands["mpiexec"]["path"], "--version"])

    gpu_query = None
    if commands["nvidia-smi"]["present"]:
        gpu_query = run_version([
            commands["nvidia-smi"]["path"],
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader"
        ])

    packages = {name: pkg(name) for name in ["ase", "pymatgen", "numpy", "scipy", "mpi4py", "gpaw"]}

    siesta_ready = commands["siesta"]["present"] and (commands["mpirun"]["present"] or commands["mpiexec"]["present"])
    gpaw_ready = commands["gpaw"]["present"] or packages["gpaw"]["present"]

    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "pre-DFT workstation audit; no DFT calculation executed",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_logical_count": os.cpu_count(),
        "memory_total_GiB": memory_gib(),
        "commands": commands,
        "versions": {
            "siesta": siesta_ver,
            "gpaw": gpaw_ver,
            "mpi": mpi_ver,
        },
        "gpu": gpu_query,
        "python_packages": packages,
        "environment_variables": {
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
            "SIESTA_PP_PATH": os.environ.get("SIESTA_PP_PATH"),
            "SIESTA_PS_PATH": os.environ.get("SIESTA_PS_PATH"),
        },
        "backend_readiness": {
            "siesta_executable_plus_mpi_detected": bool(siesta_ready),
            "gpaw_detected": bool(gpaw_ready),
            "production_backend_selected": False,
        },
        "policy": (
            "This audit does not auto-install or auto-select a DFT backend. "
            "Pseudopotential provenance, basis/cutoff strategy, spin treatment, "
            "k-point convergence, smearing, and slab/vacuum convergence must be "
            "approved explicitly before production calculations."
        ),
    }

    (OUTDIR / "dft_environment_report.json").write_text(json.dumps(report, indent=2) + "\n")

    lines = [
        "Step 03 — DFT environment audit",
        "===============================",
        f"Platform: {report['platform']}",
        f"Python: {report['python']}",
        f"Logical CPUs: {report['cpu_logical_count']}",
        f"RAM: {report['memory_total_GiB']:.2f} GiB" if report['memory_total_GiB'] is not None else "RAM: unknown",
        f"SIESTA executable: {commands['siesta']['path'] or 'not found'}",
        f"MPI launcher: {(commands['mpirun']['path'] or commands['mpiexec']['path'] or 'not found')}",
        f"GPAW command: {commands['gpaw']['path'] or 'not found'}",
        f"GPAW Python package: {packages['gpaw']['version'] or ('present' if packages['gpaw']['present'] else 'not found')}",
        f"NVIDIA GPU: {gpu_query or 'not detected'}",
        "",
        f"SIESTA+MPI detected: {siesta_ready}",
        f"GPAW detected: {gpaw_ready}",
        "Production backend selected: False",
        "",
        "No DFT calculation was executed by this task.",
    ]
    (OUTDIR / "dft_environment_report.txt").write_text("\n".join(lines) + "\n")

    print("\n".join(lines))
    print("\nWrote outputs/dft_environment_report.json")
    print("Wrote outputs/dft_environment_report.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
