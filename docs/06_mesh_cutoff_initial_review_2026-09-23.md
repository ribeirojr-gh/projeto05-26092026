# Step 03 — Fe bulk MeshCutoff screening review (2026-09-23)

## Source and task
Reviewed user-generated `fe_bulk_mesh_cutoff_summary.json`, `fe_bulk_mesh_cutoff_report.txt`, and `06_fe_bulk_mesh_cutoff.log` for run `20260923T155429_360060Z`. The validated source was alpha-Fe `mp-13`, fixed two-atom conventional cell. The same Fe ONCVPSP PBE 16-valence PSML (SHA-256 `6b540d480fbdf34ef2058028ed6a6d47fc818f9ead7ea31e496720420ab44e12`) was used throughout. All points used PBE/DZP, 0.02 Ry energy shift, 6×6×6 k-mesh, 300 K smearing, +2.2 μB/Fe initial moments, and two MPI ranks. Only `MeshCutoff` varied.

| MeshCutoff (Ry) | E (eV/Fe) | ΔE relative to 550 (meV/Fe) | Moment (μB/Fe) | SCF iterations | Static pressure (kbar) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | −3444.0040580 | −0.3415 | 2.286100 | 60 | −105.6167 |
| 350 | −3444.0027895 | +0.9270 | 2.286045 | 59 | −94.8059 |
| 450 | −3444.0042215 | −0.5050 | 2.286020 | 60 | −95.8389 |
| 550 | −3444.0037165 | 0 | 2.286015 | 59 | −94.4344 |

All four runs completed and passed the native SIESTA SCF gate. The energy spread is 1.432 meV/Fe. Magnetic moments vary by only 0.000085 μB/Fe across this grid. However, the 450→550 Ry pressure difference is ~1.405 kbar and the 250→550 Ry pressure difference is ~11.18 kbar; no zero-stress/equilibrium-lattice claim is justified. Energies are nonmonotonic as a function of the real-space grid cutoff, so 550 Ry is **not yet a defensible converged reference**. The 6×6×6 k-mesh and DZP basis remain unconverged.

## Decision and next one-script task
The **four-point SCF/parameter-sensitivity gate passed**, but the **numerical MeshCutoff convergence gate remains open**. Extend the same fixed-geometry, fixed-pseudopotential, fixed-basis, fixed-k-point test over 550, 650, 750, 850 Ry. Rerun 550 Ry within this extension as a reproducibility anchor and explicitly compare it with the previous 550 Ry result. Record energy, spin moment, pressure and SCF iterations for each point and differences relative to 850 Ry. A successful extension is not automatically the final converged cutoff; inspect the energy and stress trends and, if needed, extend further or revisit SCF, basis, k-mesh, and lattice sensitivity. Do not run Fe(110) slab production calculations at this gate.
