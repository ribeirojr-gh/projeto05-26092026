# Step 03: ASE–SIESTA PSML preflight review

Reviewed from the workstation-generated siesta_preflight.json and siesta_preflight.txt
(2026-09-23). No DFT calculation was executed in this preflight.

## Passed checks

- SIESTA /usr/local/bin/siesta, version 5.4.2; binary reports MPI, NetCDF, ELSI/ELPA, DFT-D3 support.
- MPI launcher /usr/bin/mpirun; ASE SIESTA calculator import passes, ASE 3.29.0.
- PSML directory: /home/luiz/Pacotes/PSEUDOS/DOJO-PSML.
- Fe.psml: valid PSML 1.1, ONCVPSP 3.3, PBE, scalar relativistic, nonlinear core corrections, 16-valence electrons with Fe 3s/3p/3d/4s explicitly recorded.
- O.psml: valid PSML 1.1, ONCVPSP 3.3, PBE, scalar relativistic, nonlinear core corrections, six-valence electrons (2s/2p).
- Fe SHA-256: 6b540d480fbdf34ef2058028ed6a6d47fc818f9ead7ea31e496720420ab44e12.
- O SHA-256: 224ded5c59176d9bcb76d19b7a4a68a48d5dffabf8b262f64d5760250e87c35e.
- No preflight issues were reported.

## Limitations and next gate

The PSML metadata and SHA hashes verify internal consistency and local provenance;
they do not demonstrate pseudo transferability, SCF convergence, actual MPI execution,
or the equilibrium magnetic state. The next task is a single fixed-geometry,
spin-polarized alpha-Fe bulk pilot using ASE–SIESTA with two MPI ranks by default.
Any numeric parameters in this pilot are provisional and must be converged before
production surface or corrosion calculations. GPAW remains available for independent
cross-checks. No Ce pseudo has yet been approved.
