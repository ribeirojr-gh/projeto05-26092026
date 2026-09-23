# Step 03 — Native SIESTA grid audit, 550–850 Ry extension

Source: user-provided `fe_mesh_extension_diagnostics.tar.gz`, containing four generated `.fdf` files, four native SIESTA `.out` files, plus extension JSON/TXT. The earlier upload `fe_bulk_mesh_cutoff_report(1).txt` belonged to the previous 250–550 Ry series; the archive contained the correct extension report.

## Root cause of the identical 550/650/750 Ry outputs

Inspection of all four FDFs confirms that the only scientific input changing is `MeshCutoff`; run labels change as expected. Native outputs independently confirm that SIESTA received the requested values, read `Fe.1.psml`, and completed SCF. **SIESTA quantizes the mesh to permissible integer grid dimensions, so different requested cutoff values can select the same realized grid.** The identical results are not evidence of the cutoff keyword being ignored.

| Requested cutoff (Ry) | Native required / used cutoff (Ry) | Actual mesh | E (eV/Fe) | Spin (μB/Fe) | Static P (kbar) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 550 | 550 / 776.839 | 48 × 48 × 48 | −3444.0037165 | 2.286015 | −94.43440007 |
| 650 | 650 / 776.839 | 48 × 48 × 48 | −3444.0037165 | 2.286015 | −94.43440007 |
| 750 | 750 / 776.839 | 48 × 48 × 48 | −3444.0037165 | 2.286015 | −94.43440007 |
| 850 | 850 / 983.187 | 54 × 54 × 54 | −3444.0036010 | 2.286010 | −99.41620132 |

The 850 Ry request crosses an integer-grid threshold, changing the realized mesh from 48³ to 54³. Energy changes by +0.1155 meV/Fe; static pressure changes by about −4.982 kbar. These are valid calculations on **two different realized grids** (not four independent grid resolutions). The pressure sensitivity remains material for subsequent lattice and surface studies.

## Gate decision

**Diagnostic hold resolved**: the flat plateau is caused by the discrete actual grid, not by a missing MeshCutoff setting or automatically reused output. **Numerical convergence is still NOT demonstrated.** The reference cell was held fixed at a lattice parameter obtained from Materials Project, while PAO basis and k-points are not converged. Large residual static pressure cannot be interpreted as a relaxed-lattice result.

## Next one-script task

Run the same two-Fe PBE/DZP spin-polarized fixed-cell setup at requested MeshCutoff **850, 1000, 1250, 1500 Ry**. Repeat 850 Ry as an energy/moment/pressure reproducibility anchor. The script must explicitly parse native `InitMesh: MESH` and `InitMesh: Mesh cutoff (required, used)` and record the **realized FFT grid**, not just the requested cutoff. Compare energy, magnetization and pressure across **distinct realized grids**; do not claim final convergence merely because adjacent requests produce the same mesh. Do not run surface/adsorbate DFT until the bulk gates are complete.
