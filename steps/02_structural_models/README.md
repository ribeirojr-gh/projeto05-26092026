# Step 02 — Structural Models

## Status

Task 01 (bulk alpha-Fe reference) has passed local validation. The current executable gate is Task 02: build and geometrically validate a candidate slab library for Fe(110), Fe(100), and Fe(111).

No surface is yet claimed to be DFT-converged. Oxides, hydroxides, silica models, inhibitor structures, and adsorption calculations remain outside the present gate.

## Task 01 — validated bulk alpha-Fe reference

The Materials Project query selected `mp-13`, elemental Fe, reported as `Im-3m` (space group 229), stable, with `energy_above_hull = 0.0 eV/atom`.

The raw relaxed database structure was intentionally preserved for provenance. It was classified as `Fmmm` (69) at the very strict local tolerance `symprec = 1e-3 Å`, but recovered `Im-3m` (229) at the Materials Project-compatible `symprec = 0.1 Å`. A conventional standardized cell was then generated and recovered `Im-3m` (229) again at `symprec = 1e-3 Å`.

The accepted simulation reference is `outputs/POSCAR_Fe_bulk`, with standardized conventional lattice parameter approximately `a = 2.8630355 Å`.

### Symmetry policy

The raw Materials Project structure is never silently overwritten. Both the raw database structure and the standardized simulation reference are retained. The strict raw-cell lower-symmetry diagnostic is preserved in `Fe_bulk_metadata.json`.

## Task 02 — geometric Fe surface candidate library

### Scientific objective

Construct a controlled candidate library from the validated bulk reference for:

- Fe(110) — primary orientation for the first corrosion-interface calculations;
- Fe(100) — sensitivity/comparison orientation;
- Fe(111) — sensitivity/comparison orientation.

The present task is geometric only. It generates candidate slabs at three requested layer counts (`7`, `9`, `11`) and two total periodic vacuum gaps (`15 Å`, `20 Å`) for each orientation, for a total of 18 candidates.

These candidates are *not* called converged. Final slab thickness and vacuum will later be selected from explicit electronic-structure convergence calculations.

### Structural checks

For every candidate the script records and checks:

- pure Fe composition;
- Miller orientation requested;
- number of atoms;
- detected atomic layers;
- slab thickness;
- surface area;
- periodic cell height normal to the surface;
- realized total vacuum gap;
- minimum pair distance;
- alignment of the cell c-axis with the surface normal;
- periodic boundary conditions in all directions;
- absence of unphysical atomic overlap.

The script stops if any candidate fails the defined geometric sanity checks.

## Requirements

- Linux shell
- Python 3 with `venv` support
- `mp-api`, `pymatgen`, and `ase` from `requirements-step02.txt`
- Materials Project API key only if the validated Task 01 outputs are absent

Never commit the Materials Project API key.

## Local execution

Synchronize the branch first:

```bash
git fetch origin
git switch step-02-structural-models
git pull origin step-02-structural-models
chmod +x run.sh
./run.sh
```

If the validated bulk outputs already exist locally, `run.sh` reuses them and does not repeat the Materials Project query. On a fresh clone, export `MP_API_KEY` before running so Task 01 can be reconstructed automatically.

## Task 02 expected outputs

Generated under `outputs/surfaces/`:

- POSCAR and CIF files for all 18 candidate slabs;
- `surface_library.json` — complete machine-readable provenance and validation record;
- `surface_library.csv` — compact tabular summary;
- `surface_library_report.txt` — human-readable review report.

The run log is written to:

- `logs/02_build_fe_surfaces.log`

## Task 02 validation gate

The task passes only if all 18 candidates are generated and all geometric checks pass. Passing this gate means only that the slab geometries are internally valid candidate models. It does not establish DFT convergence.

After execution, return:

```bash
cat outputs/surfaces/surface_library_report.txt
```

and the file:

```text
logs/02_build_fe_surfaces.log
```

Do not proceed to DFT surface-energy convergence or oxide models until this gate has been reviewed.
