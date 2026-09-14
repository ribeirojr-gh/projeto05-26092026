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
