# Corrosao — Computational Modeling and Simulation

Computational arm of the corrosion-protection project based on self-healing anticorrosive microcapsules developed at UnB/LMCNano.

## Scientific goals

1. Rationalize the experimental corrosion, immersion and electrochemical results.
2. Identify the atomistic/molecular mechanisms governing inhibition, adhesion, release and interfacial protection.
3. Propose and computationally screen improved inhibitor/capsule/coating concepts.
4. Generate reproducible computational evidence for a technical report and a scientific article.

## Experimental input

The authoritative experimental source files are maintained in Google Drive under `CORROSAO/INPUTS`.

## Local compute target

- CPU: 32 threads
- RAM: 32 GB
- GPU: NVIDIA RTX 3060
- Simulations are executed locally, not through GitHub Actions.

## Reproducibility rules

- Every simulation step is developed in a dedicated numbered branch.
- Every branch containing executable simulation code **must include a self-contained `run.sh`** with all commands required to install/activate the expected environment and execute the step locally.
- No API keys, tokens or credentials are committed. Materials Project access is read from the environment variable `MP_API_KEY`.
- Raw results are never invented or manually back-filled. Figures/tables must trace to output files.
- Each step records software versions, inputs, parameters, convergence criteria, outputs and validation checks.
- Heavy trajectory/checkpoint files should not be committed unless explicitly required; reproducible scripts and compact derived data are versioned.

## Workflow gate

No simulation scripts are started until the project input audit and the Simulation Proposal have been reviewed and approved. The modeling workflow follows the LCCMat `Expert Materials Modeler & Simulator v1.0` protocol.

## Planned stages

- `00` Input audit and experimental interpretation
- `01` Experimental data QA and electrochemical consistency checks
- `02` Structural models: steel/iron oxide/silica/inhibitor candidates
- `03` Mechanism-oriented baseline calculations
- `04` Inhibitor adsorption and electronic-structure calculations
- `05` Aqueous chloride interface molecular simulations
- `06` Microcapsule/coating and release-model abstractions
- `07` Screening of improved inhibitor/material concepts
- `08` Validation, sensitivity analysis and uncertainty quantification
- `09` Technical report
- `10` Scientific article

The exact toolchain and branch names will be frozen only after approval of the Simulation Proposal.
