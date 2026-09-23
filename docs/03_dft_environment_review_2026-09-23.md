# Step 03 — DFT Workstation Audit Review (2026-09-23)

## Status
Environment audit reviewed from locally generated `dft_environment_report.json`, `dft_environment_report.txt`, and `03_dft_environment.log`. This is an environment **inventory**, not a successful DFT or MPI run.

## Observed workstation
- Linux; Python 3.12.3.
- 32 **logical** CPUs; 31.03 GiB RAM.
- NVIDIA GeForce RTX 4070 **Laptop** GPU, 8188 MiB. This supersedes the original assumed RTX 3060 specification; do not assume GPU acceleration in GPAW.
- GPAW command and Python package: 25.7.0; CLI path `/home/luiz/.local/bin/gpaw`.
- `mpirun` and `mpiexec` available: Open MPI 4.1.6.
- SIESTA executable not detected on `PATH`; no SIESTA production job may be assumed.
- Current `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` — suitable starting point for pure MPI benchmarking.

## Preliminary backend decision
Use **CPU GPAW** as the first backend to test for spin-polarized bulk alpha-Fe. This is conditional on successful GPAW/PAW-data preflight and a small actual SCF test. Presence of the CLI and Python package alone does **not** establish that PAW setups or MPI support are functional.

Do not attempt an RTX 4070 GPAW production job without separately verifying a supported GPU build. Do not launch 32 MPI ranks by default on 31 GiB RAM.

## Next non-DFT preflight
From the repository root:
```bash
mkdir -p logs
gpaw info 2>&1 | tee logs/04_gpaw_info.log
```
Review GPAW installation, compiled MPI support, PAW setup paths and available datasets. If preflight succeeds, draft an explicitly approved Fe-bulk spin-polarized PBE/PAW numerical convergence protocol (PAW provenance, plane-wave cutoff, k-point mesh, smearing, magnetic initialization, SCF convergence, MPI/RAM limits), then implement a single local pilot script and update the branch `run.sh`.

## Scientific safeguards
- Fe bulk `mp-13` / standardized `Im-3m` structure passed the structural-model gate.
- The geometric slab library contains 18 candidates but **no slab is DFT converged**.
- The first physical test should be **ferromagnetic bulk alpha-Fe**, not a large slab or adsorbate.
- A working spin-polarized SCF is not yet evidence of k-point, cutoff, lattice, magnetic-moment, or slab convergence.
- Preserve actual local environment reports as provenance; do not commit API keys or unreviewed numerical results.
