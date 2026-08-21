# MPIPS real-radiograph structural characterization

Governing task revision: `deaf1430f62c90ce02cd4cefc8b58ab380d2aad8`  
Accepted IQA implementation baseline: `c09012a1d20a72d3ce3cccaa7bb1ea4d38a82f20`

Execution was read-only against the three supplied Google Drive locations.
The reference inventory contains 28 identities per anatomy. After exact-name
matching, lossless geometry reconciliation, and alignment sanity checks:

| Anatomy | Comparable | Non-comparable |
|---|---:|---:|
| Kepala | 19 | 9 |
| Tulang Belakang | 19 | 9 |

Coverage: goats 1–6; acquisitions 1–6 where supplied. The reference set
contained goats 1–6 for acquisitions 1–2 and goats 1–3,6 for acquisitions
3–6. Candidate folders supplied 29 files per anatomy, including a duplicate
`I-2-6`; the deterministic intersection produced 28 logical identities per
anatomy.

The complete per-pair inventory, metadata, geometry, valid overlap, alignment
correlation, and all six IQA outputs are in
`radiograph-structural-characterization.json` and
`radiograph-structural-characterization.csv` beside this report.

## Method

- References: processed images under `Ambil Data N / processed / kambing M`.
- Candidates: supplied legacy/main `Kepala` and `Tulang Belakang` TIFFs.
- All images were grayscale integer TIFF page 0, 16-bit.
- 3000×4096 references were reconciled to 3028×4136 candidates by centered
  integer crop, or to 3056×4066 candidates by centered row crop plus centered
  integer column pad. No resize, interpolation, warp, or resampling was used.
- Alignment sanity was Pearson correlation over every 16th valid pixel after
  reconciliation. `I-3-1 Tulang Belakang` was rejected as non-comparable
  (correlation -0.0078); `I-2-6` was rejected because the candidate identity
  is duplicated and ambiguous. Other missing/ambiguous identities are listed
  in the machine-readable inventory.

NON-COMPARABLE records are excluded from IQA scoring when the identity is
missing or ambiguous, or when alignment sanity is not trustworthy. The
inventory records the exact affected identity and reason for every exclusion;
`I-3-1 Tulang Belakang` is excluded for near-zero post-reconciliation
correlation rather than silently treated as valid.

## Results

Across comparable pairs, mean metrics were:

| Anatomy | Pearson | Edge recall | Gradient retention | Lost informative tile fraction | Informative extreme fraction |
|---|---:|---:|---:|---:|---:|
| Kepala | 0.9658 | 0.1729 | 0.1304 | 0.8440 | 0.2307 |
| Tulang Belakang | 0.9396 | 0.5114 | 0.3232 | 0.8651 | 0.0769 |

Representative full six-metric rows (edge recall, gradient retention,
informative tile count, lost informative tile fraction, low-percentile tile
retention, informative-extreme fraction) are `Kepala I-1-1` =
`0.2223, 0.1808, 665, 0.8376, 0.0, 0.1479`, `Kepala I-2-1` =
`0.1616, 0.1222, 587, 0.7836, 0.0, 0.1873`, `Tulang Belakang I-1-1` =
`0.5787, 0.3322, 821, 0.8575, 0.0, 0.0365`, and `Tulang Belakang I-2-1` =
`0.5831, 0.3181, 924, 0.8712, 0.0, 0.0485`.

The direct matched-image inspection reproduces the prior `Kepala` pattern:
the reference shows a faint peripheral ear/soft-tissue flap, while the
legacy candidate presents a hard foreground/background separation and the
corresponding weak structure is strongly suppressed. This is a structural
observation, not a clinical finding.

Conclusion: faint-ear/peripheral-soft-tissue suppression was **reproduced**
across multiple comparable examples, not refuted.

`Tulang Belakang` candidates similarly show stronger hard separation/clipping
and changed weak local structure. The quantitative retention is higher than
`Kepala` for edge recall and gradient energy, but remains substantially below
identity preservation. These observations do not establish whether threshold,
inversion, contrast enhancement, CLAHE, denoising, or another stage caused
the differences.

### Evidence status

- **OBSERVED:** dimensions, ranges, correlations, IQA values, hard background
  separation, and changed weak structures in matched images.
- **HYPOTHESIS / INFERRED:** the pattern is consistent with structural
  suppression and clipping in legacy outputs.
- **NOT ESTABLISHED:** clinical significance, the responsible pipeline stage,
  or causality by threshold, inversion, contrast enhancement, CLAHE,
  denoising, or filtering.

## Pipeline context and next step

The current main `ImagerPipelineConfig` defaults enable initial wavelet
denoising, automatic thresholding, inversion, contrast enhancement, CLAHE,
and median filtering; optional final denoising is disabled. These current
source defaults do not prove that every legacy candidate image was generated
using exactly those effective runtime values. This is observational context,
not a causal claim and does not select a processing default.

The evidence-backed next delivery order is:

1. ImageJReplicator fidelity and hardening, including the fidelity and
   semantics of the relevant ImageJ-derived operations.
2. Only after that work is accepted, a controlled Threshold × CLAHE ablation
   on the same matched pairs, retaining the no-resampling and alignment checks.

Threshold × CLAHE remains a later planned experiment; this characterization
does not prescribe it as the immediate task.

Commands used included read-only Drive TIFF downloads, Pillow TIFF metadata and
array loading, the inline deterministic inventory/alignment workflow, and
`mpips.iqa.analyze_structural_preservation`. Verification used report
consistency checks, `python -m pytest tests/test_iqa_safety.py -q`, Git status,
and the protected-converter SHA-256 check. No new dependency was installed.

Limitations: Drive filenames were the only identity authority; ambiguous
duplicates were not guessed. `lost_informative_tile_fraction` is a structural
metric, not a literal percentage of anatomy removed. The comparison is not a
clinical diagnosis. Future ImageJReplicator hardening should test the observed
hard-separation/weak-structure pattern, first establish fidelity and semantics
of the relevant ImageJ-derived operations, preserve the lossless geometry
rules, and treat rejected alignments as data-quality cases rather than
optimizing correlation blindly.

No repository production code, dependency, converter, Google Drive content,
or radiograph binary was modified or committed.
