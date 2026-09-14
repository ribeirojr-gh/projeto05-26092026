# Step 02 — Structural Models

## Status

First validation gate only. The current branch contains one executable structural-model task: retrieve and independently validate elemental bcc Fe from the Materials Project.

No surfaces, oxides, hydroxides, silica models, or inhibitor structures are generated yet. Those will be added only after this first task is executed locally and reviewed.

## Scientific objective of this first task

Establish a traceable bulk alpha-Fe reference structure for later construction of Fe(110), Fe(100), and Fe(111) slabs. The Materials Project ID is not hard-coded. The script queries elemental Fe entries, selects an `Im-3m` candidate with the lowest reported energy above hull, and independently checks the space group using pymatgen.

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

The runner creates `.venv-step02`, installs the Python dependencies, queries Materials Project, writes the structure files, performs validation, and records the actual environment with `pip freeze`.

## Expected outputs

Generated locally under `outputs/`:

- `Fe_bulk_mp.cif`
- `POSCAR_Fe_bulk`
- `Fe_bulk_conventional.cif`
- `Fe_bulk_metadata.json`
- `Fe_query_candidates.json`
- `environment_freeze.txt`

A log is written to `logs/01_fetch_fe_bulk.log`.

## Validation criteria

The task must stop with an error unless:

1. the retrieved composition is elemental Fe;
2. a Materials Project candidate with `Im-3m` symmetry exists;
3. pymatgen independently identifies the selected structure as `Im-3m`;
4. all required output files are present and non-empty.

## Review gate

After execution, return the terminal output and:

```bash
cat outputs/Fe_bulk_metadata.json
```

Do not proceed to surface generation or oxide models until this result has been reviewed.
