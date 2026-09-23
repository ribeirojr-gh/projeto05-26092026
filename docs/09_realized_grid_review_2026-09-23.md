# Step 03 — 850–1500 Ry realized-grid screening review (2026-09-23)

## Provenance and outcomes
Reviewed user-uploaded `fe_bulk_realized_grid_summary.json`, `fe_bulk_realized_grid_report.txt`, and `08_fe_bulk_realized_grid.log` for run `20260923T181410_514058Z`. All four fixed-geometry, collinear-ferromagnetic alpha-Fe SIESTA/ASE calculations completed, with the same validated Fe PBE semicore PSML (SHA-256 `6b540d480fbdf34ef2058028ed6a6d47fc818f9ead7ea31e496720420ab44e12`), DZP basis, 0.02 Ry PAO energy shift, 6×6×6 k-grid, 300 K electronic temperature and two MPI ranks. The repeated 850 Ry point matched the previous independent run in energy, moment and pressure to the reported precision.

| Request (Ry) | Realized FFT grid | Used cutoff (Ry) | Energy (eV/Fe) | Moment (μB/Fe) | Static pressure (kbar) | SCF iterations |
| ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| 850 | 54×54×54 | 983.187 | −3444.0036010 | 2.286010 | −99.416201 | 59 |
| 1000 | 60×60×60 | 1213.811 | −3444.0033855 | 2.286005 | −101.969417 | 59 |
| 1250 | 64×64×64 | 1381.047 | −3444.0031125 | 2.286000 | −94.694700 | 59 |
| 1500 | 72×72×72 | 1747.888 | −3444.0031775 | 2.285995 | −99.378729 | 59 |

All four requested cutoffs produced **distinct realized grids**, so these are independent grid-resolution tests. The energy span of these four points is **0.4885 meV/Fe**; the moment span is **0.000015 μB/Fe**. The pressure span is **7.2747 kbar** and is nonmonotonic.

## Scientific gate decision
The **execution, reproducibility and energy/magnetic-moment sensitivity gates passed for this specific fixed-cell, 6×6×6, DZP setup**. Use requested `MeshCutoff=1500 Ry` as a **provisional fixed parameter for k-point screening only**; SIESTA's realized grid is 72³ and actual used cutoff is 1747.888 Ry for the validated fixed cell.

**Do not assert general mesh convergence, stress convergence or a production cutoff.** The static stress changes by several kbar across realized grids, the fixed cell has large residual pressure of order −100 kbar, and the PAO basis, metallic Brillouin-zone sampling, and equilibrium lattice are not yet converged. High cutoff and consistent spin alone do not resolve the stress. Before lattice optimization and Fe(110) slab production, revisit mesh/stress convergence at the final k-mesh and basis and investigate Pulay stress or grid effects if they persist.

## Next single-script task
Hold geometry, spin initialization, Fe PSML, PBE, DZP, PAO shift 0.02 Ry, 300 K, two MPI ranks and requested `MeshCutoff=1500 Ry` fixed. Screen Monkhorst–Pack k-grids **6×6×6, 8×8×8, 10×10×10, 12×12×12, and 14×14×14**; repeat 6³ as an energy/moment/pressure and realized-grid anchor against the previous 1500 Ry calculation. Parse the native SIESTA outputs and generated FDFs to confirm the intended k-grid, SCF, Fe PSML, realized FFT mesh, energy, magnetic moment and pressure. Report energy/moment/pressure sensitivity versus 14³ but do not select a final k-grid until the results have been reviewed. Only one script, with an auditable local `run.sh`; no slabs or adsorbates.
