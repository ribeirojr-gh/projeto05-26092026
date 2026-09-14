# 00 — Input Audit

Status: **completed for the currently available project inputs; simulation code not started**.

## Source-of-truth inputs

Google Drive: `CORROSAO/INPUTS`

- `Projeto Corrosão UnB.PDF`
- `reunião acompanhamento 1109.pptx` (11 Sep 2026 project update)

## Experimental system identified from the inputs

- Substrate: carbon steel; the project-update deck identifies ABNT 1020 steel for the immersion study.
- Corrosive medium: 3.5 wt% NaCl for the main immersion/electrochemical tests.
- Baseline coating: epoxy resin/epoxy paint.
- Smart additive: silica-based microcapsules described as cerium-loaded; formulations use natural oils including linseed, soybean, palm/dendê and waste soybean oil.
- A separate 8-HQ microcapsule condition appears in the direct-immersion comparison.
- Microcapsule contents tested in epoxy include at least 4, 10 and 14 wt%.
- Main experimental methods: SEM, TGA/dTG, FTIR-ATR, pH monitoring, ASTM G31 / NACE TM0169 immersion, mass loss, optical microscopy, OCP, EIS, potentiodynamic polarization and salt-spray development (ASTM B117).

## Main experimental observations

### Microcapsule morphology and composition proxies

Scaled microcapsule syntheses show characteristic particle sizes around 35–54 µm in the presented SEM data, with a broad distribution and visible agglomeration/irregular particles.

TGA-based estimated organic content varies strongly with oil:

- soybean: ~18–22%
- palm/dendê: ~35–40%
- waste soybean: ~15–18%
- linseed: ~60–65%

Therefore, payload/organic fraction alone cannot be assumed to control corrosion protection.

### Direct microcapsule exposure in 3.5 wt% NaCl

After 168 h, the chart reports approximate corrosion rates (mm/year):

- no microcapsules: 0.186
- 8-HQ microcapsules: 0.027
- waste-soy microcapsules: 0.013
- palm/dendê microcapsules: 0.133
- soybean microcapsules: 0.133
- linseed microcapsules: 0.119

This ranking suggests that chemical inhibition/release/interfacial affinity may dominate over total organic loading.

### Coated-steel immersion

Presented mean corrosion rates (mm/year):

- bare steel, 168 h: 0.676
- epoxy, 168 h: 0.102
- epoxy + 4% microcapsules, 168 h: 0.062
- epoxy + 10% microcapsules, 168 h: -0.061
- epoxy + 14% microcapsules, 168 h: 0.046
- epoxy, 400 h: 0.097
- epoxy + 4% microcapsules, 672 h: 0.027
- epoxy + 10% microcapsules, 400 h: -0.008
- epoxy + 14% microcapsules, 400 h: 0.035

The nominal optimum is centered near 10 wt% in the mass-loss table, but negative corrosion rates are not physically interpretable as material dissolution and require a raw-data/cleaning/protocol audit.

### Electrochemistry

At 0 h, OCP and impedance trends indicate a nobler/more protective response for microcapsule-containing coatings, with the 10 wt% condition showing a relatively stable and less negative OCP and high initial impedance.

However, the time-dependent EIS plots at 168–336 h do not preserve a simple monotonic ranking with microcapsule fraction; neat epoxy can show larger low-frequency |Z| than 10 wt% in the displayed curves. The mass-loss and EIS rankings therefore cannot yet be treated as mutually validated.

The 0 h phase-angle curves suggest multiple characteristic time scales for coated systems, consistent with contributions from coating/barrier and metal/coating interfacial processes. Quantitative equivalent-circuit fitting is not shown in the inputs.

## Mechanistic hypotheses to test — not yet conclusions

1. **Barrier contribution** — epoxy and silica/microcapsule filling delay water/Cl− transport.
2. **Ce-mediated active inhibition** — released Ce(III) may precipitate as cerium hydroxide/oxide species at locally alkaline cathodic sites, suppressing cathodic activity and forming a protective interfacial deposit.
3. **Organic/self-healing contribution** — oil/healing-agent release may seal damage and modify hydrophobicity/transport.
4. **Specific organic inhibitor adsorption** — 8-HQ or related ligand chemistry may adsorb/chelate strongly at Fe/oxide interfaces and may act synergistically with Ce.
5. **Loading trade-off** — increasing microcapsule content increases active-agent availability but can introduce agglomeration, porosity, coating heterogeneity or adhesion loss; the experimental 10–14 wt% range may lie near this trade-off.

These hypotheses are consistent with the project observations but cannot be distinguished quantitatively from the current figures alone.

## Critical QA flags before model calibration

1. **Negative mass-loss-derived corrosion rates** at 10 wt% must be traced to initial/final masses, cleaning procedure, retained coating/corrosion products, and the exact ASTM/NACE equation implementation.
2. **EIS versus mass-loss ranking mismatch** must be checked against raw spectra, replicate IDs, sample history and labeling.
3. Several plots use magnitude-only EIS; raw Zreal/Zimag/phase data are required for defensible equivalent-circuit fitting.
4. Replicate counts, error bars and uncertainty propagation are not present in the current source files.
5. The exact chemistry/topology of the microcapsule (shell precursor, Ce salt/speciation/loading, oil/inhibitor core, surfactant, shell thickness, 8-HQ location/loading) is not specified in the inputs.

## Required additional experimental/raw inputs

Before atomistic production calculations or EIS lifetime-model calibration, request:

- raw EIS files for every sample/time/replicate (frequency, Zreal, Zimag; phase/magnitude if available)
- raw OCP and polarization data
- raw mass-loss table with specimen dimensions/area, density, exposure time, initial/final/cleaned mass and replicate IDs
- exact ABNT 1020 composition used
- exact epoxy formulation, curing agent, cure schedule and coating thickness
- exact microcapsule synthesis recipe and Ce/8-HQ/oil loading
- particle-size distribution and shell thickness if available
- release-kinetics measurements if available (Ce and/or organic inhibitor)
- post-corrosion surface chemistry if available (XPS/Raman/EDS/ICP)

## External literature cross-check

The experimental concept is strongly supported by peer-reviewed work on Ce-loaded silica/nanocontainers, Ce-containing microcapsules, and combined Ce + organic inhibitor systems in epoxy. Particularly close literature reports increased coating/polarization resistance with SiO2@Ce, precipitation of Ce hydroxide/oxide in damaged regions, strong performance near ~10 wt% capsule loading in some systems, and beneficial combinations of Ce with organic inhibitors such as 8-hydroxyquinoline.

Relevant DOIs for the project bibliography:

- 10.1108/ACMM-03-2022-2629
- 10.1016/j.porgcoat.2019.105339
- 10.1021/acsomega.1c04597
- 10.1016/j.surfcoat.2015.11.035

## Decision gate

No simulation scripts are to be written until the Simulation Proposal is approved and the identity of the first modeled inhibitor/capsule chemistry is confirmed.
