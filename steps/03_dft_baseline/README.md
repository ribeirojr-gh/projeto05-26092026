# Step 03 — DFT Baseline

## Current gate

The first task in this branch is a workstation environment audit. It does **not** run DFT and does not install a production DFT engine automatically.

The purpose is to determine, on the actual local workstation, whether SIESTA and/or GPAW are already available, whether an MPI launcher is present, and what CPU/RAM/GPU resources are visible. The next convergence script will be written only after this report is reviewed.

## Why this gate is required

The project targets a workstation with 32 CPU threads, 32 GB RAM, and an NVIDIA RTX 3060. For metallic alpha-Fe slabs, the production setup must be chosen deliberately because memory, spin polarization, k-point sampling, metallic smearing, pseudopotential provenance, and MPI/OpenMP balance can dominate both accuracy and runtime.

The project policy is therefore:

1. detect the real local software environment;
2. choose a backend explicitly;
3. verify pseudopotential/basis or plane-wave setup provenance;
4. converge bulk numerical parameters;
5. converge Fe(110) slab thickness and vacuum;
6. only then calculate adsorption/passivation chemistry.

## Run

```bash
chmod +x run.sh
./run.sh
```

## Expected outputs

- `outputs/dft_environment_report.txt`
- `outputs/dft_environment_report.json`
- `logs/03_dft_environment.log`

Return the two environment reports for review. No DFT production calculation should be started before the next gate is approved.

## Surface-library note carried from Step 02

The Step 02 geometric library passed overlap, vacuum, composition, and cell-normal checks for all 18 generated slabs. However, ASE's `layers` argument is a builder repeat count for the supplied conventional bcc cell; it does not equal the number of distinct atomic planes for every Miller orientation. In the validated output, Fe(110) had detected planes equal to the requested builder count, while Fe(100) and Fe(111) had twice as many detected atomic planes. This is not an overlap or vacuum failure, but it means cross-orientation convergence comparisons must use physical slab thickness and detected atomic-plane count rather than the raw ASE builder count. Fe(110), the primary surface for the first convergence study, is unaffected by this naming ambiguity.


## Current gate (after the environment audit): actual SIESTA/ASE + PSML preflight

Local user-provided PSML *header excerpts* indicate that Fe.psml was generated with
scalar-relativistic ONCVPSP and PBE, with 16 valence electrons including Fe 3s/3p
semicore. The O.psml header indicates a scalar-relativistic pseudo with
z-pseudo=6, but its truncated excerpt does **not** establish its XC functional.

The next runner uses the user's real local files, not the uploaded excerpts:
it XML-parses all of Fe.psml and O.psml, checks PBE, scalar relativity,
valence, Fe semicore, records SHA-256, finds the SIESTA executable, and
imports the ASE SIESTA calculator. It is a preflight and executes no DFT.

From the repository root:

```bash
git fetch origin
git switch step-03-dft-baseline
git pull --ff-only origin step-03-dft-baseline
SIESTA_PS_PATH="$HOME/Pacotes/PSEUDOS/DOJO-PSML" bash run.sh
```

If the user's Python with ASE differs from python3, run
`PYTHON_BIN=/path/to/python bash run.sh`.

Return `outputs/siesta_preflight.txt` and
`outputs/siesta_preflight.json` for review. A passed metadata
preflight does not prove SIESTA can read PSML at runtime, support a working
MPI launch, or converge a spin-polarized Fe SCF. Those are the subsequent
pilot/calibration gates.

## Gate 3: first local ASE–SIESTA electronic-structure pilot

The user's real PSML preflight passed: SIESTA 5.4.2 (MPI), ASE 3.29.0,
Fe.psml and O.psml both scalar-relativistic PBE; Fe has 16 valence electrons
including 3s/3p semicore. The exact local SHA-256 fingerprints are held in
`outputs/siesta_preflight.json` and checked again before the pilot.

Run from the repository root (only after reviewing local changes):

```bash
git fetch origin
git switch step-03-dft-baseline
git pull --ff-only origin step-03-dft-baseline
SIESTA_PS_PATH="$HOME/Pacotes/PSEUDOS/DOJO-PSML" bash run.sh
```

The runner reuses an existing validated `outputs/POSCAR_Fe_bulk`, or attempts
to reconstruct it from Materials Project when `MP_API_KEY` and the previous
Step 02 dependencies are available. It checks the preflight, then launches
ONE fixed-cell/fixed-position PBE/DZP spin-polarized bcc Fe test through ASE.
Default MPI ranks = 2, with OpenMP/BLAS threads = 1. The Fe initial moments
are +2.2 Bohr magnetons per atom. Pilot-only settings: 250 Ry mesh cutoff,
0.02 Ry PAO energy shift, 6×6×6 k-points, 300 K Fermi-Dirac electronic
temperature, DM tolerance 1e-4, mixing weight 0.05, 120 SCF iterations.

This is explicitly NOT a proof of numerical convergence, equilibrium
magnetization, optimized lattice, or a converged slab. A finite ASE energy
only establishes that this pilot calculation could be executed and parsed.
Output diagnostic spin-moment lines are retained for independent review.

Each run writes into a unique timestamped subdirectory under
`outputs/dft/fe_bulk_siesta_pilot/` to prevent accidental overwrites.
The run summary is `outputs/fe_bulk_siesta_pilot_summary.json`; the wrapper
log is `logs/05_siesta_fe_bulk_pilot.log`. If the pilot fails, collect the
timestamped `pilot_failure.json` and SIESTA `.out` file (if present).

Do not commit any MP API key, executable installations, or pseudopotential
libraries. Send the summary, wrapper log, and the native SIESTA `.out` for
review before any parameter sweep or surface DFT.

## Current task: MeshCutoff-only Fe bulk screening

The native `Fe_bulk_pilot.out` confirms that the spin-polarized pilot ended
after 60 SCF iterations with total spin ~4.5722 μB for two Fe atoms;
the total cell energy was −6888.008116 eV. The static pressure reported
−105.6167 kbar at the fixed imported lattice. The pilot execution passed,
but cutoff, basis, k-point and lattice convergence did not.

Run **one new script** `scripts/06_fe_bulk_mesh_cutoff_screen.py` via
the branch root `run.sh`, using the exact Fe PSML provenance of the pilot.
The single changed parameter is SIESTA `MeshCutoff` over 250, 350, 450,
and 550 Ry. Common settings: fixed validated two-atom alpha-Fe geometry,
PBE, DZP, PAO energy shift 0.02 Ry, 6×6×6 k mesh, 300 K electronic
temperature, +2.2 μB/Fe initial moments, SCF DM tolerance 1e−4,
SCF max 120, mixing 0.05, two MPI ranks and one OpenMP thread per rank.
Each point starts an independent SCF in a unique timestamped directory.

The runner refreshes the Fe/O PSML preflight each time, reuses the validated
Fe reference and pilot (or reconstructs those on a fresh clone if all
prerequisites including MP_API_KEY are available), then runs the screening.
Generated results stay untracked in `outputs/` and `logs/`.

```bash
cd ~/SIMULACOES/corrosao
git status --short
git fetch origin
git switch step-03-dft-baseline
git pull --ff-only origin step-03-dft-baseline
SIESTA_PS_PATH="$HOME/Pacotes/PSEUDOS/DOJO-PSML" bash run.sh
```

Return `outputs/fe_bulk_mesh_cutoff_summary.json`,
`outputs/fe_bulk_mesh_cutoff_report.txt`, and
`logs/06_fe_bulk_mesh_cutoff.log`. If a point fails, also return the
`screening_failure.json` from the timestamped run directory and the
native SIESTA `.out` for that point, if present.

All energies across the four points use **the same exact Fe pseudo** and
the same fixed atomic geometry, so within-series differences are meaningful.
Absolute energies must not be compared to different pseudopotential
families. Differences relative to 550 Ry are a screening diagnostic only:
**no converged cutoff is selected until after numerical review**.

## Current validation target: extension from 550 to 850 Ry (script 07)

The reviewed first MeshCutoff series has four successful SCF calculations at
250, 350, 450 and 550 Ry. The total-energy span is 1.432 meV/Fe; the Fe
moment span is 0.000085 μB/Fe, while the 450-to-550 Ry pressure changes
by ~1.405 kbar. The total energy is nonmonotonic; 550 Ry is not yet
designated numerically converged. See
`docs/06_mesh_cutoff_initial_review_2026-09-23.md`.

The next **single script** is `scripts/07_fe_bulk_mesh_cutoff_extension.py`.
It holds the Fe bulk structure, Fe PSML fingerprint, PBE, DZP, 0.02 Ry
PAO energy shift, 6×6×6 k-grid, 300 K electronic temperature,
+2.2 μB/Fe initial spin and two-MPI-rank configuration fixed,
while scanning `MeshCutoff = [550, 650, 750, 850] Ry`.
The repeated 550 Ry point is compared with the previous 550 Ry result
(automatic check ≤0.5 meV/Fe in energy and ≤0.005 μB/Fe in moment).
Each run receives a unique timestamped directory.

Run from the repository root after verifying there are no local
uncommitted changes:

```bash
cd ~/SIMULACOES/corrosao
git status --short
git fetch origin
git switch step-03-dft-baseline
git pull --ff-only origin step-03-dft-baseline
SIESTA_PS_PATH="$HOME/Pacotes/PSEUDOS/DOJO-PSML" bash run.sh
```

Return `outputs/fe_bulk_mesh_cutoff_extension_summary.json`,
`outputs/fe_bulk_mesh_cutoff_extension_report.txt`, and
`logs/07_fe_bulk_mesh_cutoff_extension.log`.
If the script reports a failure, also send the timestamped
`screening_failure.json` and native SIESTA `.out` for the failed point.

**Do not infer final numerical convergence from a finite total energy,
small net moment drift, or the highest screened cutoff alone.**
Pressure, k-mesh, PAO basis and equilibrium-lattice dependence must
be reviewed before production Fe(110) calculations.

## Current task: audit convergence across **realized** SIESTA FFT grids (script 08)

The native inputs and outputs for the previous cutoff extension were examined.
Requested 550, 650 and 750 Ry all selected the **same actual 48×48×48 FFT
grid**, with SIESTA reporting a used cutoff of **776.839 Ry**. Requesting
850 Ry selected **54×54×54** at used cutoff **983.187 Ry**. Therefore
identical energies and stresses at 550/650/750 Ry are expected: they are
not three independent real-space resolutions. The observed ~4.982 kbar
pressure change at 850 Ry coincides with the FFT-grid jump. There is no
evidence from these native files that the cutoff keyword was ignored.
See `docs/08_native_mesh_diagnostics_review_2026-09-23.md`.

The current `run.sh` executes only the next script,
`scripts/08_fe_bulk_realized_grid_screen.py`, after checking previous
prerequisites. The fixed two-Fe PBE/DZP/6×6×6, +2.2 μB/Fe,
300 K setup is held constant while requested cutoffs **850, 1000, 1250,
1500 Ry** are screened. Every `.out` is parsed for native SCF status,
energy, spin, pressure, and especially `InitMesh: MESH` and
`InitMesh: Mesh cutoff (required, used)`. The 850 Ry point is rerun
and compared with the prior result for energy, moment and pressure.

Run after checking that the working tree is clean:

```bash
cd ~/SIMULACOES/corrosao
git status --short
git fetch origin
git switch step-03-dft-baseline
git pull --ff-only origin step-03-dft-baseline
SIESTA_PS_PATH="$HOME/Pacotes/PSEUDOS/DOJO-PSML" bash run.sh
```

Send `outputs/fe_bulk_realized_grid_summary.json`,
`outputs/fe_bulk_realized_grid_report.txt`, and
`logs/08_fe_bulk_realized_grid.log`. If a run fails, include
`failure.json` under its timestamped run folder and the native SIESTA
`.out` for the failed point when present. No Fe(110) surface calculation
or numerical convergence claim is authorized by this screening task.

## Current numerical gate: Fe bulk k-point screening (script 09)

The previous realized-grid study (850, 1000, 1250, 1500 Ry) produced four
distinct SIESTA FFT grids and four converged SCF calculations. The
energy range was 0.4885 meV/Fe and the spin moment range was
0.000015 μB/Fe, but the static-pressure range remained 7.2747 kbar.
See `docs/09_realized_grid_review_2026-09-23.md`. This supports using
the **requested 1500 Ry cutoff provisionally for k-point screening**;
it does not prove stress convergence or the equilibrium lattice.

The current single script `scripts/09_fe_bulk_kpoint_screen.py` uses
five Monkhorst–Pack meshes: 6³, 8³, 10³, 12³, 14³. The validated
Fe semicore PSML, PBE/DZP, 0.02 Ry PAO shift, fixed two-Fe bulk geometry,
300 K electronic temperature, +2.2 μB/Fe initial moments and 1500 Ry
requested MeshCutoff remain fixed. The script verifies the generated FDF
k-grid, native SCF, actual SIESTA FFT grid, energy, magnetization and
pressure. The repeat 6³ calculation is compared against the previously
validated 1500 Ry calculation (energy, moment, pressure). The realized
FFT grid must stay unchanged when only k points vary.

From repository root, only when local changes are accounted for:

```bash
cd ~/SIMULACOES/corrosao
git status --short
git fetch origin
git switch step-03-dft-baseline
git pull --ff-only origin step-03-dft-baseline
SIESTA_PS_PATH="$HOME/Pacotes/PSEUDOS/DOJO-PSML" bash run.sh
```

Return `outputs/fe_bulk_kpoint_summary.json`,
`outputs/fe_bulk_kpoint_report.txt` and
`logs/09_fe_bulk_kpoint_screen.log`. If a calculation fails, send
the timestamped `failure.json` and native SIESTA `.out` file if present.
At this gate do not declare a production cutoff or k-mesh; do not
perform lattice optimization or Fe(110) slab/adsorption calculations.
