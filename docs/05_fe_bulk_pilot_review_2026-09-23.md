# Step 03 — First alpha-Fe ASE–SIESTA pilot review

## Execution and provenance

- Local pilot run ID: `20260923T154129_596106Z`.
- SIESTA 5.4.2, ASE 3.29.0, two MPI ranks, scalar-relativistic PBE Fe ONCVPSP PSML with 16 valence electrons including 3s/3p semicore.
- Validated bulk reference: Materials Project `mp-13`, standardized two-atom cubic alpha-Fe cell, lattice parameter ~2.8630355 Å.
- Fixed cell and positions; collinear spin polarization initialized to +2.2 μB on each Fe.
- Pilot-only settings: DZP automatically generated basis, PAO energy shift 0.02 Ry, mesh cutoff 250 Ry, 6 × 6 × 6 k-points, 300 K electronic temperature, DM tolerance 1e-4.

## Observed result (from uploaded native Fe_bulk_pilot.out)

- Native output confirms the Fe.1 PSML was read, with PBE exchange-correlation, scalar-relativistic projectors, and eight Fe semicore electrons in valence.
- SIESTA reports SCF convergence by DM+H after **60 iterations**: final max |DM_out−DM_in| = 1.30807e-5; max |H_out−H_in| = 9.684788e-4 eV.
- Final SIESTA total energy **Etot = −6888.008116 eV for the two-atom cell**. This very negative absolute number contains semicore valence and pseudopotential reference contributions; it is not compared to other pseudopotentials.
- Final cell spin moment 4.572203 μB; Mulliken reports two equivalent Fe atoms each at **2.286102 μB**. The difference between initialized and final moments is not a convergence failure.
- Native SIESTA output shows a 105.62 kbar diagonal stress magnitude (reported static pressure −105.6167 kbar). This is a large **fixed-cell residual stress**, not proof of a relaxed or equilibrium lattice.
- Native output ends with `Job completed`. The only explicit runtime warning is about deprecated BASIS_ENTHALPY filenames; the separate basis text notes possible incompleteness of a printed input excerpt.

## Gate decision

**Execution/SCF/PSML/MPI pilot gate PASSED** for this fixed-geometry calculation.
**Scientific convergence gate NOT PASSED**: basis, mesh cutoff, k-point sampling, magnetic ground state, lattice parameter and slab thickness/vacuum remain unconverged. A single total moment close to the expected ferromagnetic state is reassuring but cannot establish a physical benchmark independently.

## Next single scripted task: mesh cutoff sensitivity

Use the identical validated Fe pseudo, spin initialization, geometry, PBE/DZP, smearing, mixing and 6×6×6 k mesh, changing only MeshCutoff over **250, 350, 450, 550 Ry**. Use two MPI ranks and one OpenMP thread by default. Record Etot per atom, final spin moment per Fe, SCF iterations and residual stress for each cutoff, plus differences relative to the 550 Ry point.

These are **screening data**, not a final converged cutoff: 550 Ry is only the highest tested value, k-mesh and PAO basis are not yet converged, and the residual stress signals that an equilibrium-lattice study will be needed. After reviewing the screening curve, extend the cutoff grid if required; then perform k-point convergence and basis/lattice checks, with a final cross-check for coupled numerical dependence.

Do not start slab DFT until bulk numerical accuracy has been reviewed. Never commit locally generated pseudopotentials, private API credentials, or unreviewed raw outputs.
