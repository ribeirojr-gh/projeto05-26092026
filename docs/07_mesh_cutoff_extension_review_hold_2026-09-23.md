# Step 03 — Extended Fe bulk MeshCutoff screening: review hold

User-provided diagnostics: `07_fe_bulk_mesh_cutoff_extension.log`,
`fe_bulk_mesh_cutoff_extension_summary.csv` and a TXT upload named
`fe_bulk_mesh_cutoff_report(1).txt` (2026-09-23). The TXT contains the
**previous 250/350/450/550 Ry series**, not the extended 550/650/750/850
Ry report. Extension JSON and native FDF/out files were not uploaded.

## Extension observations (same Fe PBE semicore PSML, DZP, 6x6x6 k mesh, fixed bulk)

| MeshCutoff (Ry) | E (eV/Fe) | moment (μB/Fe) | pressure (kbar) | SCF iter |
|---:|---:|---:|---:|---:|
| 550 | -3444.0037165 | 2.286015 | -94.43440007 | 59 |
| 650 | -3444.0037165 | 2.286015 | -94.43440007 | 59 |
| 750 | -3444.0037165 | 2.286015 | -94.43440007 | 59 |
| 850 | -3444.0036010 | 2.286010 | -99.41620132 | 59 |

The 550 Ry repeat matches its previous value to the precision reported
by the automated script. All four executions ended successfully.
However, the 550/650/750 Ry energies, moments, iteration counts, **and
pressure** are identical to all exported decimal places, whereas
850 Ry shifts pressure by about 4.982 kbar despite changing energy
by only +0.1155 meV/Fe. This is not sufficient evidence of cutoff
convergence. It may reflect discrete FFT mesh selection or another
input/runtime issue; distinguish these using native SIESTA outputs.

## Validation hold: do NOT launch k-point sweep or surface DFT yet

Request the four FDF and four native OUT files under
`outputs/dft/fe_bulk_mesh_cutoff_extension/20260923T160457_911092Z/mesh_{550,650,750,850}Ry/`,
plus `outputs/fe_bulk_mesh_cutoff_extension_summary.json` and
`outputs/fe_bulk_mesh_cutoff_extension_report.txt` if available.
Audit, for each cutoff: FDF MeshCutoff actually differs, native
`redata: Mesh Cutoff` agrees, FFT mesh dimensions and grid-origin
settings when printed, Fe PSML provenance is the same, SCF reached
the requested criterion, and pressure and magnetization are read
from the correct native files. Once the anomaly is explained,
decide whether a denser cutoff grid and/or stricter stress criterion
are needed before selecting a provisional MeshCutoff.

No new DFT script has been released pending this diagnostics gate.
