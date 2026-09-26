# 10 — Local replay of reviewed Step 03 gates and Drive mirroring (2026-09-26)

## Context

Work resumed on a different local workstation. None of the untracked
`outputs/` or `logs/` from the 2026-09-23 gates exist on this machine or
in Google Drive, so the current gate (script 09, k-point screening) cannot
consume the previously reviewed prerequisites.

## Machine provenance (this replay)

| Item | Value |
|---|---|
| CPU threads | 24 (README target: 32) |
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU (README target: RTX 3060) |
| RAM | ~30 GB |
| Kernel | Linux 7.0.0-28-generic |
| Python | 3.12.3, ASE 3.29.0 |
| MPI | Open MPI 4.1.6 |
| SIESTA | `siesta --version` → `71c860291` (differs from the build recorded in the handoff) |
| Fe.psml SHA-256 | `6b540d480fbdf34ef2058028ed6a6d47fc818f9ead7ea31e496720420ab44e12` (identical to handoff) |

## Decision

Because the SIESTA build differs, numbers from the previous machine must not
be mixed with numbers produced here. All reviewed gates of Step 03
(01 → 04 → 05 → 06 → 07 → 08) are therefore **replayed locally, unchanged**,
before script 09 runs. The replayed values are compared against the
2026-09-23 reviews (docs 05–09) as a cross-build reproducibility check; a
material discrepancy halts the workflow for review.

`run.sh` was changed only to make this replay automatic: a reviewed gate is
re-executed when its summary JSON is absent, and the run aborts if the
replay does not produce it. No physical or numerical parameter of any
script was changed. `MP_API_KEY` may be supplied through an optional,
never-committed file `~/.config/corrosao/secrets.env`.

## Drive mirroring

Project files are mirrored to the agent folder in Google Drive
(`CLAUDE…/CORROSAO/`) with `tools/drive_mirror.py`, which uses the local
GVFS Google Drive mount, updates files in place (no duplicates) and writes a
`DRIVE_MANIFEST.json` (path, size, SHA-256) for each mirrored tree:

- `CORROSAO/repository/<branch>@<commit>/` — snapshot of each branch;
- `CORROSAO/03_dft_baseline/<gate>/` — gate outputs and logs after each run.

The Drive folder path is read from `DRIVE_AGENT_DIR` and is not stored in
this public repository.
