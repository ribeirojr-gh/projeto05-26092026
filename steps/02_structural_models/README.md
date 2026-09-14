# Step 02 — Structural Models

## Status

First validation gate only. The current branch contains one executable structural-model task: retrieve, diagnose, standardize, and validate elemental bcc alpha-Fe from the Materials Project.

No surfaces, oxides, hydroxides, silica models, or inhibitor structures are generated yet. Those will be added only after this first task is executed locally and reviewed.

## Scientific objective of this first task

Establish a traceable bulk alpha-Fe reference structure for later construction of Fe(110), Fe(100), and Fe(111) slabs.

The script queries elemental Fe entries and selects a Materials Project entry reported as `Im-3m` (space group 229), preferring a stable entry and then the lowest energy above hull. The MP-ID is not hard-coded.

### Symmetry policy

The raw Materials Project structure is preserved exactly as retrieved for provenance. A very strict local symmetry analysis (`symprec = 1e-3 Å`) is recorded as a diagnostic but is not used alone to reject the structure because relaxed database cells can be represented in non-standard or slightly distorted settings.

The Materials Project production pipeline uses a looser symmetry tolerance (`symprec = 0.1 Å`) for reported space-group assignments. The script therefore requires the raw structure to recover `Im-3m`/229 at `symprec = 0.1 Å`, then constructs a conventional standardized cell and requires that standardized cell to recover `Im-3m`/229 again at the stricter `symprec = 1e-3 Å`.

This preserves both provenance and a clean simulation reference without silently overwriting the raw database structure.

## Requirements

- Linux shell
- Python 3 with `venv` support
- Internet access
- Materials Project API key available as the environment variable `MP_API_KEY`

Do not commit the API key.

## Local execution

```bash
export MP_API_KEY="YOUR_KEY_HERE"
chmod +x run.sh
./run.sh
```

The runner creates `.venv-step02`, installs the Python dependencies, queries Materials Project, writes both raw and standardized structure files, performs validation, and records the actual environment with `pip freeze`.

## Expected outputs

Generated locally under `outputs/`:

- `Fe_bulk_mp_raw.cif` — raw database structure for provenance
- `POSCAR_Fe_bulk_mp_raw` — raw database structure in POSCAR format
- `Fe_bulk_conventional.cif` — standardized conventional bcc cell
- `POSCAR_Fe_bulk` — standardized simulation reference
- `Fe_bulk_metadata.json` — provenance, lattice, selection rule, and symmetry diagnostics
- `Fe_query_candidates.json` — all elemental Fe query candidates returned
- `environment_freeze.txt`

A log is written to `logs/01_fetch_fe_bulk.log`.

## Validation criteria

The task must stop with an error unless:

1. the retrieved composition is elemental Fe;
2. a Materials Project candidate reported as `Im-3m`/229 exists;
3. the raw candidate recovers `Im-3m`/229 at the Materials Project-compatible `symprec = 0.1 Å`;
4. the standardized conventional structure recovers `Im-3m`/229 at `symprec = 1e-3 Å`;
5. all required output files are present and non-empty.

A lower symmetry detected for the raw relaxed cell at `symprec = 1e-3 Å` is retained in the metadata as a diagnostic and is not hidden.

## Review gate

After execution, return the terminal output and:

```bash
cat outputs/Fe_bulk_metadata.json
```

Do not proceed to surface generation or oxide models until this result has been reviewed.
