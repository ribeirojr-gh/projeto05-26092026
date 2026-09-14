# 01 — Simulation Proposal (Draft)

Status: **awaiting user approval; no simulation code or simulation branches created yet**.

## System

ABNT 1020 carbon steel protected by epoxy coatings containing cerium-loaded silica microcapsules and natural-oil / organic-inhibitor formulations, exposed primarily to 3.5 wt% NaCl.

## Primary scientific questions

1. Why do microcapsules reduce the measured corrosion rate and alter OCP/EIS/polarization behavior?
2. What roles are played by barrier transport, Ce-mediated passivation, organic inhibitor adsorption, and healing-agent release?
3. Why is an intermediate capsule loading (experimentally around 10 wt% in the mass-loss dataset) apparently better than lower/higher loadings?
4. Which inhibitor/carrier/coating combinations should be prioritized for improved protection and sustainable formulation?
5. Can a calibrated transport/electrochemical model predict coating degradation and EIS evolution beyond the experimental window?

## Input gaps

- [STRUCT-GAP] Atomic structure and oxidation/hydroxylation state of the steel/corrosion-product interface.
- [STRUCT-GAP] Exact microcapsule shell/core chemistry and geometry.
- [ELEC-GAP] Adsorption, charge transfer and passivation energetics of Ce species and organic inhibitors on Fe/oxide surfaces.
- [DYN-GAP] Water/Cl− transport through epoxy; inhibitor release and diffusion; interfacial residence and competition with water/chloride.
- [STAT-GAP] Raw replicates, uncertainty and consistency of mass-loss versus electrochemical metrics.
- [ML-GAP] Optional later-stage screening of a larger sustainable-inhibitor candidate space.

## Recommended multiscale strategy

### Step 01 — Experimental data QA and electrochemical model extraction

**Purpose:** establish a trustworthy experimental target before atomistic fitting.

Tools: Python, NumPy, pandas, SciPy, matplotlib, impedance.py / custom equivalent-circuit fitting.

Tasks:

- reproduce corrosion-rate calculations from raw masses
- detect causes of negative apparent rates
- fit OCP/EIS/polarization datasets per replicate
- compare candidate circuits (e.g. Rs-(Qcoat||Rpores)-(Qdl||Rct), only when statistically justified)
- estimate Rpo, Rct, CPE/Q, n, characteristic times and uncertainty
- generate a harmonized dataset for subsequent calibration

Runtime: seconds to minutes per dataset; <1 h total for typical project-scale data.

Hardware: CPU only.

**Gate:** cannot be completed from figure images; raw electrochemical and mass-loss files are required.

### Step 02 — Structural models and reference-state preparation

Tools: Materials Project API, COD where needed, pymatgen, ASE, spglib, Packmol/RDKit.

Initial structures:

- bcc Fe (baseline carbon-steel proxy)
- Fe(110) primary metallic surface; Fe(100)/(111) sensitivity checks if needed
- representative corrosion/passive products: magnetite Fe3O4, hematite α-Fe2O3 and iron oxyhydroxide phases when relevant
- amorphous/hydroxylated SiO2 surface or pore model for carrier interactions
- confirmed inhibitor molecules from the experimental recipe (8-HQ and others only after identity is verified)
- Ce(III)/Ce-containing reference species consistent with the formulation

Runtime: minutes to hours for structure generation; MLIP prerelaxation where valid.

Hardware: CPU/GPU.

Important limitation: CHGNet/MACE may be useful for inorganic structural prerelaxation, but they will **not** be assumed reliable for Fe/Ce/organic/water corrosion chemistry without DFT validation.

### Step 03 — Baseline DFT mechanism: inhibitor and chloride competition at steel interfaces

Primary tools: SIESTA for cost-efficient screening on the local workstation; GPAW for selected higher-confidence calculations and electronic-structure analysis.

Calculations:

- spin-polarized slab convergence
- water/Cl− adsorption baselines
- inhibitor adsorption energies in several orientations/sites
- Ce-related species interaction with metallic/oxidized/hydroxylated surfaces
- coadsorption: inhibitor + Cl−, inhibitor + water, Ce species + Cl−
- charge-density difference, Bader/Hirshfeld-compatible charge analysis where feasible, DOS/PDOS and work-function shifts

Outputs:

- adsorption-energy hierarchy
- displacement/competition mechanism against Cl−/water
- preferred binding atoms and orientations
- predicted electronic passivation signatures

Runtime on 32 threads / 32 GB RAM: approximately 4–24 h per converged slab geometry for moderate cells; selected calculations may require 1–3 days. Full screening is expected to span days to a few weeks locally.

Hardware: primarily CPU; RTX 3060 is not assumed to accelerate the DFT production path unless the selected code/version is explicitly validated for GPU use.

### Step 04 — Sustainable inhibitor screening

Purpose: propose improved formulations rather than only explain the current one.

Candidate families will be finalized after exact current formulation is known. Priority should be given to sustainable molecules and experimentally realistic combinations, for example:

- 8-hydroxyquinoline as a strong reference/benchmark if confirmed in the formulation
- tannic/gallic/caffeic-acid-type polyphenols
- phytic-acid derivatives or other benign chelating species
- amino-acid-derived inhibitors
- Ce + organic-ligand dual-inhibitor concepts
- pH-responsive mesoporous-silica carriers

Workflow:

1. molecular conformer generation (RDKit)
2. inexpensive molecular prescreening/descriptors
3. DFT refinement of top candidates
4. surface adsorption calculations for top 5–10 candidates
5. rank by adsorption/passivation, solubility/release compatibility, sustainability and experimental feasibility

Runtime: hours for prescreening; days to ~2 weeks for selected surface DFT depending candidate count.

### Step 05 — Epoxy/water/NaCl transport MD

Purpose: quantify the barrier component separately from active inhibition.

Tools: LAMMPS or OpenMM; Packmol/RDKit; validated all-atom force field for the actual epoxy/cure chemistry.

Tasks:

- construct cured epoxy models at the experimental formulation/crosslink density
- calculate water uptake, diffusion coefficients and free-volume descriptors
- compare Cl−/Na+ penetration tendencies
- assess how microcapsule/silica-like inclusions perturb local free volume and transport in simplified representative cells

Runtime: approximately hours to days per 10–50 ns trajectory on RTX 3060 depending atom count and force field.

Hardware: GPU preferred, CPU fallback.

### Step 06 — Release and carrier-interface modeling

Purpose: understand why different oils/inhibitors and shell chemistries produce different protection despite different organic loadings.

Model level will depend on the actual microcapsule recipe. Candidate approaches:

- inhibitor adsorption/desorption from hydroxylated silica
- diffusion through mesoporous/hydroxylated silica models
- oil/inhibitor partitioning using molecular MD
- pH/speciation-informed thermodynamic calculations

A full 35–50 µm capsule is not modeled atomistically. Atomistic results provide transport/binding parameters for a reduced continuum model.

Runtime: hours to days per representative MD system.

### Step 07 — Continuum coating-degradation + EIS model (SimCorrosao concept)

The project deck already proposes a physically interpretable chain:

water/species diffusion → absorption → property degradation → equivalent-circuit response → calibration → lifetime prediction.

We recommend formalizing this as a reproducible Python model and treating it as a separate, fast scale of the project.

State variables/parameters may include:

- water concentration C(x,t)
- absorbed-water fraction φ(t)
- coating conductivity σ(t)
- coating capacitance Cc(t)
- pore resistance Rp/Rpo(t)
- charge-transfer resistance Rct(t)
- corrosion current density icorr(t)

Calibration must use raw EIS data and uncertainty-aware fitting. Atomistic/MD results should constrain trends/priors rather than be forced into a direct one-to-one mapping.

Runtime: seconds to minutes per calibration/prediction.

Hardware: CPU.

### Step 08 — Capsule-loading and microstructure optimization

Purpose: explain the apparent optimum near 10 wt% and deterioration above/below it.

Approach:

- statistical/continuum representation of capsules in coating volume
- competing terms for inhibitor reservoir, tortuosity/barrier enhancement, agglomeration/defect probability and adhesion penalty
- calibrate against 4/10/14 wt% experimental series
- use uncertainty intervals rather than a single deterministic optimum

Runtime: minutes to hours.

### Step 09 — Validation and uncertainty quantification

Validation hierarchy:

1. reproduce measured corrosion-rate trends after QA
2. reproduce OCP/EIS/polarization trends and circuit parameters
3. test DFT/MD ranking against experimental inhibitor/oil ranking
4. predict at least one new formulation or loading condition before experimental validation
5. update model after blind validation

Recommended additional experiments for decisive mechanism testing:

- scratched-coating EIS with replicates
- Ce release versus time and pH (ICP-OES/ICP-MS if available)
- inhibitor release kinetics (UV–Vis/HPLC when applicable)
- XPS/Raman/EDS at defect sites to verify Ce/Fe passivation products
- adhesion and pull-off testing versus capsule loading
- coating thickness and water uptake
- contact angle / hydrophobicity
- salt-spray and wet/dry cyclic exposure

### Step 10 — Technical report

The technical report should contain:

1. executive summary
2. experimental input audit
3. QA/corrected experimental dataset
4. mechanistic model
5. multiscale computational methods
6. DFT adsorption/passivation results
7. MD transport/release results
8. continuum/EIS calibration and lifetime predictions
9. ranked candidate materials/formulations
10. experimentally actionable recommendations
11. limitations and uncertainty
12. reproducibility appendix with GitHub branch/commit hashes

### Step 11 — Scientific article

Proposed article concept:

**Multiscale Mechanistic Design of Cerium-Loaded Self-Healing Epoxy Coatings for Carbon-Steel Corrosion Protection in Chloride Media**

Core narrative:

experimental corrosion/EIS evidence → data QA → atomistic mechanism → transport/release physics → calibrated EIS-degradation model → new formulation predictions → experimental validation.

Potential journals after results mature:

- Corrosion Science
- Progress in Organic Coatings
- Surface & Coatings Technology
- npj Materials Degradation

The final target should be selected only after the depth of atomistic and validation results is known.

## Databases to query

- Materials Project — Fe and oxide bulk structures; API access through `MP_API_KEY`
- COD — supplementary crystal structures
- NOMAD / AFLOW / OQMD as cross-checks if needed
- PubChem or curated molecular sources for confirmed organic inhibitors

## Planned GitHub branch policy after approval

Each executable step gets a numbered branch, for example:

- `step-01-experimental-qa`
- `step-02-structural-models`
- `step-03-dft-baseline`
- `step-04-inhibitor-screening`
- `step-05-epoxy-md`
- `step-06-release-model`
- `step-07-eis-continuum`
- `step-08-loading-optimization`
- `step-09-validation-uq`

Every branch must contain a self-contained `run.sh` and a branch-specific README describing expected inputs/outputs and validation checks.

## Estimated project compute fit to local hardware

The available workstation (32 CPU threads, 32 GB RAM, RTX 3060) is sufficient for the proposed workflow if DFT cells are kept moderate and screening is staged. The GPU is especially useful for classical MD. The main bottleneck will be production DFT and possibly large cured-epoxy models; these will be designed around memory constraints and run sequentially/with limited parallelism.

## Approval gate

Before Step 01/02 code is created, approve or revise this proposal and provide/confirm the raw experimental data and exact active-agent chemistry.
