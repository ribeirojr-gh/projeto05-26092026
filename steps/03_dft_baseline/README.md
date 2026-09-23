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
