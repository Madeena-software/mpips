---
title: MPIPS Real Radiograph Structural Characterization
status: Validated/Published
---

# Executable Task

## Task identity

**Task title:** MPIPS Real Radiograph Structural Characterization

**Task path:** `.agents/tasks/real-radiograph-characterization.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** IQA Hardening — real-data
characterization before ImageJReplicator hardening and Threshold × CLAHE
ablation.

**Owner / designated planning authority:** Repository Planner / designated
delivery authority.

## Delivery context

Characterize structural-preservation differences between matched reference-
quality images from `6 Kambing Radiografi` and corresponding legacy/main
processed `Kepala` and `Tulang Belakang` outputs before any processing
hardening or causal ablation.

This is characterization only. It must not modify radiography processing
behavior.

## Baseline and task revision

**Implementation baseline:**
`c09012a1d20a72d3ce3cccaa7bb1ea4d38a82f20`

**Task revision:** The immutable governing revision is the publication commit
containing this file; it is reported by the Planner after publication.

## Objective

Produce a reproducible, evidence-backed characterization using lossless
geometry reconciliation and the accepted
`mpips.iqa.analyze_structural_preservation` measurement foundation.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Accepted structural-IQA implementation at
  `c09012a1d20a72d3ce3cccaa7bb1ea4d38a82f20`
- External reference dataset — `6 Kambing Radiografi`:
  <https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8>
- External legacy/main processed `Tulang Belakang` data:
  <https://drive.google.com/drive/folders/1tjkz_sSi63u9M5GuCGEFJD-8WF_wXTcr>
- External legacy/main processed `Kepala` data:
  <https://drive.google.com/drive/folders/1diBR6vitRnrQO1J_vq60cynFr9_2Wo_C>

### Requirement traceability

- Real-data structural characterization → this approved delivery directive,
  the governing repository contract, and the accepted structural-IQA task
  outcome.

Images under `Ambil Data N / processed / kambing M` in `6 Kambing Radiografi`
are the reference-quality comparison baseline. They are not raw detector
images. The separate `Kepala` and `Tulang Belakang` folders contain outputs
from the legacy/main MPIPS processing path.

Prior planner evidence includes matched `I-1-1` and `I-1-2` `Kepala` and
`Tulang Belakang` examples. A recurring faint goat-ear/peripheral soft-tissue
suppression pattern was observed in `Kepala`; `Tulang Belakang` outputs may
show stronger contrast while changing weak/local structure. These are prior
observations to reproduce or refute, not execution evidence.

## Scope

### In scope

- Build a deterministic matched-pair inventory for `Kepala` and `Tulang
  Belakang` using `I-<goat>-<acquisition> + anatomy` identity, ignoring
  wrappers such as `Copy of`.
- Characterize multiple goats and acquisitions where unambiguous matches are
  available, with more than one goat, more than one acquisition, and both
  anatomies when available.
- Inspect TIFF dimensions, dtype/bit depth, orientation, intensity range, and
  geometry.
- Reconcile geometry only with justified lossless integer operations: crop,
  pad, integer translation, orientation correction, and valid-mask overlap.
- Report for every comparable pair: logical ID, anatomy, reference/candidate
  paths, shapes and dtypes, exact transform, valid-overlap fraction,
  alignment sanity evidence such as correlation, `edge_recall`,
  `gradient_energy_retention`, `informative_tile_count`,
  `lost_informative_tile_fraction`, `low_percentile_tile_retention`, and
  `informative_extreme_fraction`.
- Record qualitative observations visible in matched images, including faint
  ear/peripheral suppression, weak vertebral/rib/local-structure changes,
  clipping or hard foreground/background separation, and contrast gain without
  equivalent structural preservation.
- Inspect current main-branch processing defaults/order as explanatory
  context only. Potentially relevant stages are threshold enabled/auto,
  inversion, contrast enhancement, CLAHE, and median filtering.
- Produce a concise repository characterization report using an existing
  diagnostic/evidence convention where available.
- Add a narrowly scoped deterministic helper only if genuinely necessary for
  reproducible mapping, alignment, or measurement; do not create generic
  infrastructure.

### Out of scope

- Modifying `RadiographyPipeline`, `mpips.processing`, `mpips.pipelines`,
  threshold behavior/defaults, CLAHE, contrast defaults, ImageJReplicator,
  median filtering, denoising, FFC, calibration, DAG, API, workers,
  dependencies, lockfiles, Docker, CI, deployment, or release configuration.
- Threshold × CLAHE ablation, production default selection, production
  PASS/WARN/FAIL IQA policy, and ImageJReplicator hardening.
- Resizing, interpolation, warping, or resampling to force same-shape IQA.
  For an individual matched pair, use only justified lossless integer
  crop/pad/translation/orientation operations when they provide trustworthy
  alignment. If that pair would require resizing, interpolation, warping, or
  other resampling, classify only that pair as `NON-COMPARABLE`, record the
  reason, and continue with the remaining pairs.
- Causal claims that threshold or CLAHE caused an observed loss.
- Google Drive mutation, committing external radiograph binaries, or modifying
  `.agents/tasks/iqa-structural-safety.md`.
- Characterization scripts or reports in this publication turn.

### Preserved behavior

- Radiography processing behavior remains unchanged.
- Google Drive access is read-only: no upload, rename, move, delete, or
  modification.
- No external radiograph binary is committed to Git.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical with SHA-256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- `lost_informative_tile_fraction` is not interpreted as a literal percentage
  of anatomical tissue removed. Structural IQA is not a clinical diagnostic
  verdict, and the reference dataset is not asserted absolute clinical ground
  truth.

## Dependencies and assumptions

### Dependencies

- Read-only access to the three supplied Google Drive data locations.
- Accepted structural-IQA implementation at the stated baseline.
- Existing repository diagnostic/evidence conventions, if applicable.

### Approved assumptions

- The supplied `6 Kambing Radiografi` processed images are the comparison
  reference baseline as stated above.
- The supplied `Kepala` and `Tulang Belakang` folders contain legacy/main
  processed outputs.
- Pair identity is used only when logical ID and anatomy are unambiguous.

### Remaining approval requirements

- None beyond the task's existing authority. Any new processing behavior,
  resampling requirement, dependency, data-handling concern, or material
  scope/architecture change requires return to planning.

## Required capabilities

- Repository read/write and local command execution.
- Read-only Google Drive/browser access to the supplied data.
- TIFF/image metadata and visualization/measurement capability already
  available in the repository environment.

## Execution constraints

- Reuse `mpips.iqa.analyze_structural_preservation` and existing repository
  conventions before adding code.
- Use only lossless integer geometry operations when justified.
- Do not claim causality from observational comparisons.
- Keep quantitative measurement separate from clinical judgment.
- Do not add dependencies, generic infrastructure, processing behavior, or
  external data binaries.

## Acceptance criteria

- [ ] Deterministic matched-pair inventory is produced for both anatomies where
      unambiguous data exists.
- [ ] Multiple goats and acquisitions are characterized where available.
- [ ] TIFF metadata, orientation, intensity range, and geometry are recorded.
- [ ] Scored pairs use trustworthy lossless reconciliation only; all pairs that
      require resampling are explicitly `NON-COMPARABLE`.
- [ ] Numerical alignment sanity evidence and all six structural-IQA outputs
      are reported for every comparable pair.
- [ ] Recurring `Kepala` behavior is established or refuted from multiple
      examples, and `Tulang Belakang` behavior is characterized.
- [ ] Qualitative observations are grounded in the actual matched images and
      are not presented as clinical judgments or unsupported causal claims.
- [ ] No processing/default behavior, dependency, or unrelated repository
      behavior is changed; Google Drive remains read-only; no radiograph binary
      is committed; and the protected converter remains unchanged.
- [ ] Evidence-backed questions or recommendations for the next
      ImageJReplicator-hardening task are recorded.

## Verification requirements

### Required checks

- Run the deterministic inventory/alignment/measurement workflow over all
  available unambiguous pairs.
- Inspect the generated report and matched-image evidence for both anatomies.
- Verify the worktree diff contains only characterization artifacts authorized
  by this task and verify the protected converter hash.

### Required evidence

The Executor must report the exact implementation revision or working-tree
state, commands run, observed results, inventory and comparable/non-comparable
pair counts, generated report/artifact paths, matched-image observations,
verification gaps, and any stop condition encountered.

## Stop conditions

For an individual matched pair, classify it as `NON-COMPARABLE`, record the
reason, and continue characterization when trustworthy comparison would require
resizing, interpolation, warping, or other resampling. Do not weaken the
prohibition on resampling for scored IQA pairs.

Stop and return to planning only when a systematic geometry, identity, access,
data-handling, dependency, or authority problem prevents the acceptance
criteria from being meaningfully satisfied. Examples include essentially no
trustworthy comparable pairs remaining, systematically ambiguous matching,
inability to obtain read-only dataset access, a required new dependency or
processing change, or a material privacy/licensing concern.

The Executor must not silently reinterpret the task into a materially different
objective.

## Side-effect authorization

The future execution authorizes creation of only the bounded characterization
artifacts permitted by this task, an optional narrowly scoped deterministic
helper when genuinely required, and the commit and push of those authorized
changes to `refactor/package-boundaries`. It does not authorize touching
`main`, merging, opening or merging a release PR unless separately authorized,
deployment, release, production-configuration changes, Google Drive mutation,
committing radiograph binaries, dependency changes, processing-behavior
changes, dependency installation/replacement, permission expansion, or secret
access.

After pushing the bounded immutable characterization implementation revision,
the Executor must stop and report it for Reviewer inspection.

### Explicitly authorized side effects

- Read-only access to the supplied Google Drive data.
- Local creation of the deterministic characterization report and any narrowly
  scoped helper genuinely required by the acceptance criteria.
- Commit only those authorized characterization changes.
- Push the resulting characterization commit to
  `refactor/package-boundaries`.

## Expected terminal outcome

### Review Required

Use when the characterization artifacts and truthful evidence are available
for review, with exact working-tree/implementation identity and verification
results.

### Planning Required

Use when a stop condition prevents safe completion within this contract.

The Executor must report the blocking issue and the affected authority, scope,
dependency, data boundary, or acceptance condition.
