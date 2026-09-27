# 11 — Local replay of Step 03 and k-point screening review (2026-09-27)

Workstation, software and replay rationale are described in
`docs/10_local_replay_and_drive_mirror_2026-09-26.md`. Python dependencies
were installed in an isolated `.venv-step02` (host system pandas was
compiled against NumPy 1.x and broke `mp_api` under the user's NumPy 2.x).
Frozen versions are recorded in `logs/venv_step02_freeze_2026-09-27.txt`
(NumPy 2.5.3, ASE 3.29.0, pymatgen 2026.9.24, mp-api 0.46.5).
`run.sh` was fixed to check `from mp_api.client import MPRester` instead of
the bare `import mp_api`, which masked the broken environment.

Command: `PYTHON_BIN=.venv-step02/bin/python bash run.sh` (exit 0); wrapper
log `logs/run_sh_replay_2026-09-27.log`.

## 1. Cross-build reproducibility of reviewed gates

SIESTA build `71c860291` on this machine vs. the 2026-09-23 build.

| Gate | Quantity | 2026-09-23 | 2026-09-27 replay |
|---|---|---|---|
| 01 | MP entry / space group / a (Å) | mp-13 / Im-3m (229) / 2.8630355 | identical |
| 04 | Fe.psml, O.psml SHA-256 | 6b540d48…44e12, 224ded5c…87c35e | identical |
| 05 | E (eV/cell), SCF iter., M (μB/Fe) | −6888.008116, 60, 2.286102 | −6888.008116, 60, 2.2861 |
| 06 | E, M, P at 250/350/450/550 Ry | doc 06 table | identical to all printed digits |
| 07 | E, M, P at 550/650/750/850 Ry | doc 07 table | identical (550–750 Ry again share one 48³ grid) |
| 08 | E, M, P and realized grids 54³/60³/64³/72³ | doc 09 table | identical |

**Cross-build reproducibility gate: PASSED.** Every replayed energy, moment,
pressure, SCF iteration count and realized FFT grid matches the 2026-09-23
reviews to the precision printed by SIESTA. Earlier reviewed numbers and the
new k-point data are therefore directly comparable.

## 2. k-point screening (script 09, run `20260927T184249_729844Z`)

Fixed: two-Fe conventional alpha-Fe cell (mp-13, unrelaxed), approved Fe
PSML, PBE, DZP, PAO shift 0.02 Ry, requested MeshCutoff 1500 Ry (realized
72³ grid for all points), Fermi–Dirac 300 K, +2.2 μB/Fe initial moments,
DM tolerance 1e−4, 2 MPI ranks. Only the Monkhorst–Pack grid varies.

| k-grid | irreducible k | E (eV/Fe) | ΔE vs 14³ (meV/Fe) | M (μB/Fe) | ΔM vs 14³ (μB/Fe) | P (kbar) | ΔP vs 14³ (kbar) | SCF | wall time |
|---|---|---|---|---|---|---|---|---|---|
| 6³ | 132 | −3444.0031775 | +5.762 | 2.285995 | +0.0372 | −99.379 | +8.540 | 59 | ~3.6 min |
| 8³ | 296 | −3444.0069990 | +1.940 | 2.254645 | +0.0058 | −105.914 | +2.005 | 53 | ~4.7 min |
| 10³ | 560 | −3444.0088185 | +0.121 | 2.246045 | −0.0028 | −107.898 | +0.020 | 59 | ~7.7 min |
| 12³ | 948 | −3444.0076095 | +1.330 | 2.246215 | −0.0026 | −108.551 | −0.633 | 60 | ~11.5 min |
| 14³ | 1484 | −3444.0089390 | 0 | 2.248840 | 0 | −107.919 | 0 | 65 | ~17.3 min |

All five SCF cycles converged natively. The 6³ point reproduces the 1500 Ry
point of gate 08 exactly (reproducibility anchor).

### Interpretation

- **6³ is clearly under-sampled.** It overestimates the energy by 5.8 meV/Fe,
  the moment by 0.037 μB/Fe and the pressure by 8.5 kbar relative to 14³.
  Every earlier cutoff screen (gates 06–08) used 6³, so those absolute stress
  values carry a k-sampling error of this order. Their *relative* cutoff
  trends remain valid because k was held fixed.
- **From 10³ upward the moment and pressure plateau.** M varies by 0.0028 μB/Fe
  and P by 0.65 kbar across 10³–14³.
- **The energy is not monotonic.** 12³ lies 1.2 meV/Fe above 10³ and
  1.33 meV/Fe above 14³. This odd/even-type oscillation is typical of a
  ferromagnetic transition metal sampled with a small electronic
  temperature (300 K ≈ 26 meV). The 10³–14³ energy span of 1.33 meV/Fe
  exceeds a 1 meV/Fe tolerance, so **energy convergence to ≤1 meV/Fe is not
  demonstrated at 300 K**.

### Gate decision

**k-point screening gate: PASSED for execution and reproducibility;
numerical k-convergence NOT yet established.**

- Moment and pressure are converged within ~0.003 μB/Fe and ~0.7 kbar
  for k ≥ 10³.
- The total energy still oscillates by ~1.3 meV/Fe.
- 14³ is the densest screened grid and serves only as the current
  reference. It is not an approved production grid.

## 3. Proposed next single-variable gate (awaiting approval)

Two options. Both keep everything else fixed.

- **10A — denser k at 300 K:** 14³, 16³, 18³ and 20³, with 14³ repeated as
  the anchor. This tests whether the oscillation damps below 1 meV/Fe.
  Estimated cost at 2 ranks is ~2 h, or about half that with 4 ranks.
- **10B — electronic-temperature sensitivity at fixed 14³:** 300, 600, 1000
  and 1500 K, reporting the free-energy and energy extrapolation. This
  tests whether modest smearing removes the oscillation without biasing M
  or P.

Recommendation: **10A first**. It changes only k, which keeps the
single-variable protocol, and it defines a defensible grid before any
smearing change. 10B then becomes the basis for choosing the slab smearing.
The remaining gates, before any Fe(110) slab, are the PAO basis (DZP vs.
TZP / energy shift) and the equilibrium lattice.
