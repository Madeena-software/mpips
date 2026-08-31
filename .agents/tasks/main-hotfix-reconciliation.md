---
title: Main Hotfix Reconciliation
document_id: TASK-MAIN-HOTFIX-RECONCILIATION-001
version: 1.6
status: Validated/Published
language: en-US
scope:
  - semantic reconciliation of the frozen main image-processing hotfix range
  - bounded canonical port of accepted image-processing hotfix semantics
  - newer-main radiography semantic-drift mapping
  - bounded canonical TRX orientation port
  - BED threshold policy evidence characterization
authority_note: This task authorizes only the bounded Phase 5 BED threshold policy evidence characterization described below. It does not authorize BED runtime-policy changes, calibration changes, production activity, optimization, or release activity.
---

# Executable Task

## Task identity

**Task title:** Main Image-Processing Hotfix Reconciliation

**Task path:** `.agents/tasks/main-hotfix-reconciliation.md`

**Task contract state:** `Validated/Published`

**Delivery objective / Work Package / MVP:** Main hotfix reconciliation before Radiography Pipeline Optimization

**Owner / designated planning authority:** Repository Planner/Reviewer under the `.agents/` delivery contract

## Delivery context

The production `main` line contains material image-processing and calibration hotfixes added after `refactor/package-boundaries` diverged. Reconcile accepted semantics into the canonical refactor architecture without synchronizing Git history, reopening accepted ImageJ/Fiji fidelity work, or porting production-only infrastructure.

## Baseline and task revision

**Implementation baseline:** `820948734e8b598b851135cc82c2210ead934963`

**Frozen upstream main baseline:** `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`

**Accepted Phase-2 implementation:** `e0ff8a5c093f5ad265bf65326b40663cb4454943`

**Phase-3 observed upstream main baseline:** `e94784db65bb134d43e87a2046037ab4d1cbfe02`

**Known merge base:** `fec5695048acbc3ce95d0a658032ec3701b6e045`

**Task revision:** resolved by the immutable Git publication commit containing this file; the exact full SHA is supplied in the Planner handoff.

Do not merge `main`, rebase this branch onto `main`, or mechanically cherry-pick the hotfix chain.

## Objective

**Objective:** Maintain the accepted Phase 1–4 reconciliation history, then characterize BED configured thresholding versus threshold bypass using bounded, provenance-controlled evidence. BED runtime-policy reconciliation, calibration, revalidation, optimization, and production work remain unauthorized.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Frozen branch and hotfix requirements in the initial reconciliation directive
- Accepted ImageJ/Fiji closure baseline `a4a5c16881e589154680f0606c849e2a4514041f`
- Accepted I-5B publication `82cf2187b2efd6146de790021c1ba5e4e307b9d7` and corrected baseline `8396fbc768285cc68ed3bbe572561cd664b70e8b`

### Requirement traceability

- Reconciliation objective → frozen main baseline, canonical refactor baseline, and phase requirements in the initial reconciliation directive
- Phase 2 port contract → `PHASE 2 — CANONICAL HOTFIX PORT` in the initial reconciliation directive and accepted Phase 1 evidence
- Protected ImageJ/converter and production-hold boundaries → protection and hold requirements in the initial reconciliation directive

## Scope

### In scope

#### Historical Phase 2 — Canonical Hotfix Port (accepted)

- Correct OpenCV Otsu return-value handling in `mpips/processing/thresholding.py`.
- Apply detector-specific threshold policy in `mpips/pipelines/radiography.py`: TRX bypasses threshold separation by default; BED preserves configured threshold behavior.
- Add minimal deterministic regression coverage for scalar/range/determinism/Otsu semantics and TRX/BED policy behavior.
- Historical Phase-2 write surface (satisfied; not current authorization):
  - `mpips/processing/thresholding.py`
  - `mpips/pipelines/radiography.py`
  - `tests/test_thresholding_processing.py`
  - `tests/test_radiography_pipeline.py`
  - `.agents/evidence/main-hotfix-reconciliation.md`

The accepted Phase 1 and Phase 2 evidence is preserved as historical provenance.
Phase 2 implementation is accepted at `e0ff8a5c093f5ad265bf65326b40663cb4454943`.

#### Historical Phase 3 — Newer-Main Radiography Semantic Drift Mapping (accepted)

- Compare accepted refactor state `e0ff8a5c093f5ad265bf65326b40663cb4454943` with observed `origin/main` `e94784db65bb134d43e87a2046037ab4d1cbfe02`.
- Classify BED threshold defaults, TRX orientation, calibration/canvas behavior, production validation infrastructure, and other material newer-main changes.
- Record exact commits, ownership, tests, evidence, gaps, and deferred BED/TRX dataset inputs in the stable evidence file.
- Modify only this remediation write surface:
  - `.agents/tasks/main-hotfix-reconciliation.md`
  - `.agents/evidence/main-hotfix-reconciliation.md`

Do not change runtime code, tests, configuration, calibration, conversion,
deployment, production state, or experiment inputs during Phase 3.

#### Historical Phase 4 — Canonical TRX Orientation Port (accepted)

- Change only `mpips/processing/geometry.py` so TRX uses `cv2.ROTATE_90_CLOCKWISE` in `crop_and_rotate()`.
- Update only `tests/test_geometry_processing.py` for exact asymmetric CW pixel regressions and `.agents/evidence/main-hotfix-reconciliation.md` for evidence.
- Preserve crop-before-rotation, BED crop-only behavior, supported dtype, and swapped TRX dimensions.
- Do not introduce a second transform or resurrect `mpips/engine/`.

The Phase-4 implementation write surface is exactly:

- `mpips/processing/geometry.py`
- `tests/test_geometry_processing.py`
- `.agents/evidence/main-hotfix-reconciliation.md`

The frozen upstream authority remains exactly
`203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`. The observed `origin/main` may be
newer; later calibration commits, including `ae41b1d5c11d99420aa195385cefa7e9b5b0a595`
and `80729162b50e92d99d45061c50ba0d875b2c4202`, are explicitly not absorbed.

Historical Phase-2 regression coverage established that Otsu returns a deterministic
scalar, remains within the valid uint16 domain or normalized float32 `[0,1]`
domain, uses the OpenCV scalar rather than the thresholded array, and updates
the representative corrected Otsu golden. That coverage also established TRX
bypass, BED configured-threshold behavior, BED skip behavior, config
immutability, and unchanged unrelated downstream stage configuration.


### Phase 5 write surface

The future Phase-5 execution write surface is exactly:

- `scripts/bed_threshold_policy_characterization.py`
- `artifacts/real-data-regression/bed-threshold-policy-characterization.md`
- `artifacts/real-data-regression/bed-threshold-policy-characterization.json`
- `artifacts/real-data-regression/bed-threshold-policy-characterization.csv`
- `.agents/evidence/main-hotfix-reconciliation.md`

The helper must orchestrate existing canonical components, duplicate no
production algorithm, become no production dependency, and modify no
canonical runtime semantics. No external radiograph, NPZ, TIFF, thumbnail,
generated image, NumPy array, calibration carrier, or other patient/subject
binary may be committed.

### Phase 5 execution contract

Phase 5 is evidence/experiment only. It must determine whether available BED
acquisition evidence supports retaining canonical configured threshold
separation or supports default threshold bypass as later implemented on
`main`. Do not change BED runtime policy or mechanically copy
`dd7c21eead66a2c5396522a2310f5dd9cbd85b85`; TRX bypass is accepted, BED bypass
is not evidence-accepted.

Use only the authorized read-only BED source:
`https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8`.
Recursively inventory it and separate acquisition radiographs, gain NPZ,
processed/reference images, calibration artifacts, and generated outputs.
Do not treat the heterogeneous folder or processed tree as one dataset or
ground truth.

Use trusted repository NPZ semantics from
`mpips/workflows/imager_pipeline/npz_io.py`, including `allow_pickle=True`
where required. A primary case must establish SHA-256, `id`, `gainid`,
`rawimage`, `xrayparams`, `cameraparams`, detector mode `BED`, shape, dtype,
and finite numeric range. Its gain must have matching identity and usable
dark, flat/raw gain, detector metadata, and camera metadata. Exclude and
record malformed, non-BED, duplicate, ambiguous, inconsistent, or
unresolvable cases.

Freeze a deterministic cohort before inspecting threshold or IQA outcomes:
maximum 12 radiographs, with at least 3 sessions and 3 subject folders when
available. Group by session/subject, sort groups lexicographically, sort
within groups by stable acquisition ID/filename, select first and last
distinct acquisitions where available, then round-robin to the cap. Record
the algorithm and selected IDs. Selection must not use quality, appearance,
threshold results, IQA, or final-output quality.

Run exactly two paired states through identical accepted Phase-4 semantics:
`BED_AUTO` (`use_threshold=True`, `threshold_method="auto"`) and `BED_NONE`
(the canonical `threshold_method="none"` bypass). Freeze raw/gain inputs,
detector mode, denoise, FFC, calibration if legitimately resolved, crop/BED
geometry, normalization, inversion, contrast/equalization, CLAHE, final
denoise/filtering, dtype, dimensions, stage order, and unrelated config.
Calibration must not be invented, regenerated, promoted, mutated, or silently
substituted from TRX; exclude cases requiring a new calibration decision or
stop if systematic.

Record the normalized pre-threshold image and stage-local metrics. AUTO must
include requested/effective branch, numeric threshold when applicable,
fallback, mask/output SHA-256, foreground/background fractions, min/max/mean/
median, p01/p50/p99, dynamic range, and nonzero count. NONE must explicitly
record disabled separation, no invented numeric threshold, output SHA-256,
and equivalent statistics. Record paired final outputs with shape, dtype,
ndarray SHA-256, intensity/clipping statistics, and AUTO-vs-NONE differences.

Reuse `mpips.iqa.analyze_structural_preservation` against the same-geometry
normalized pre-threshold reference for both threshold-stage outputs, recording
`edge_recall`, `gradient_energy_retention`, `informative_tile_count`,
`lost_informative_tile_fraction`, `low_percentile_tile_retention`, and
`informative_extreme_fraction`. Require lossless geometry; comparisons needing
resize, interpolation, warp, or resampling are `NON-COMPARABLE`. Analyze each
case and session/subject/cohort groups where possible; report median, range,
sign consistency, worst-case degradation, and outliers without a weighted
aggregate or clinical/diagnostic claim.

End with exactly one classification: `BED BYPASS SUPPORTED`,
`BED CONFIGURED THRESHOLD SUPPORTED`, or `BED THRESHOLD POLICY UNRESOLVED`,
citing case-level evidence and conflicts. This is decision support only and
does not change production or canonical defaults.

Do not modify `mpips/conversion/tiff_json_to_dcm.py`; required SHA-256 is
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`. Preserve
ImageJ/Fiji closure, accepted TRX orientation/bypass, current BED configured
threshold behavior, and `NPZ → processing → DICOM` boundaries. Historical
threshold results affected by corrected Otsu semantics are context only.

### Out of scope

- Any file outside the Phase-5 evidence write surface above.
- Calibration, diagnostic or stage-observer plumbing, collapse-gate validation rules, validation/promotion/deployment infrastructure, and production API expansion.
- Git merge, rebase, mechanical cherry-pick, main promotion, deployment, release, or production mutation.
- Reopening accepted ImageJ/Fiji Contrast, Equalization, Hybrid Median, Circular Median, or CLAHE fidelity closure absent a direct contradiction; such a contradiction stops review.
- Broad Radiography Pipeline Optimization or a new experiment.
- Rewriting or deleting historical I-5B evidence.

### Preserved behavior

- The accepted ImageJ/Fiji closure remains protected at baseline `a4a5c16881e589154680f0606c849e2a4514041f`.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical; required SHA-256 is `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Accepted Phase 2 behavior remains historical: TRX threshold separation is bypassed by default; BED retains its configured threshold method.
- Historical I-5B evidence remains intact. Otsu-affected threshold rows may require bounded revalidation; CLAHE and unaffected rows are not automatically invalidated.
- The deferred detector-specific BED and TRX Drive sources are characterization/optimization inputs only; historical I-5B data is reused only for controlled impact comparability.

## Dependencies and assumptions

### Dependencies

- Exact branch and baseline state listed above.
- Frozen main commit and relevant history are locally resolvable.
- Accepted ImageJ/Fiji and I-5B artifacts remain available for comparison.

### Approved assumptions

- The canonical owners are under `mpips/processing/`, `mpips/pipelines/`, `mpips/workflows/imager_pipeline/`, and `mpips/calibration/`; removed `mpips/engine/` modules must not be resurrected.
- Phases 1–4 are accepted and closed. Phase 5 ends at `Review Required`.

### Remaining approval requirements

- Reviewer acceptance is recorded for Phases 2–4. Planner/Reviewer review is required after Phase 5 evidence execution.
- Every material phase must end `Review Required` and republish this same task path with a new immutable SHA before the next phase is executable.
- Acceptance does not authorize promotion, deployment, or release.

## Required capabilities

- Repository read/write access limited to the exact Phase 5 evidence write surface
- Local command execution and bounded experiment verification

## Execution constraints

- Preserve accepted Phase-1–4 provenance.
- Change only the Phase-5 write surface; do not modify BED runtime thresholding, calibration, conversion, ImageJ, filtering, config, API, deployment, or production behavior.
- Do not merge, rebase, cherry-pick, run production workflows, deploy, release, or mutate external systems.

## Phase map

1. **PHASE 1 — UPSTREAM HOTFIX IMPACT MAPPING** — `ACCEPTED / CLOSED`.
2. **PHASE 2 — CANONICAL HOTFIX PORT** — `ACCEPTED / CLOSED` at `e0ff8a5c093f5ad265bf65326b40663cb4454943`.
3. **PHASE 3 — NEWER-MAIN RADIOGRAPHY SEMANTIC DRIFT MAPPING** — `ACCEPTED / CLOSED` at `b9093b0aec5dd66cf2a5afcd5028c2876cf889bd`.
4. **PHASE 4 — CANONICAL TRX ORIENTATION PORT** — `ACCEPTED / CLOSED` at `820948734e8b598b851135cc82c2210ead934963`.
5. **PHASE 5 — BED THRESHOLD POLICY EVIDENCE CHARACTERIZATION** — `CURRENT RELEASED PHASE`.
6. **BED RUNTIME-POLICY IMPLEMENTATION** — `UNAUTHORIZED`.
7. **CALIBRATION RECONCILIATION** — `UNAUTHORIZED`.
8. **BROADER REVALIDATION / OPTIMIZATION / PRODUCTION PHASES** — `UNAUTHORIZED`.

## Historical Phase 3 execution contract — satisfied

The following requirements were satisfied by the Phase-3 mapping and evidence
recorded in `bc093e66c590367b663a6e95073e7e0fd86d210e`; they are historical
provenance, not current execution authority:

- the task and evidence were updated with exact provenance;
- newer-main semantic drift and evidence boundaries were inspected and classified;
- deferred dataset inputs were recorded;
- runtime implementation and experiments remained unauthorized;
- the terminal state was left `Review Required`.

## Historical Phase 4 execution contract — satisfied

The Executor must:

- change TRX rotation from 90° CCW to 90° CW in canonical `crop_and_rotate()`;
- update its documentation to say clockwise;
- add exact asymmetric pixel assertions for TRX CW output and BED crop-only behavior;
- preserve crop-before-rotation, dtype, swapped dimensions, and workflow-wrapper behavior;
- update the stable evidence file with observed implementation and verification;
- leave BED policy, calibration, conversion, ImageJ, deployment, and production behavior unchanged;
- leave the terminal state `Review Required`.

## Historical Phase 3 acceptance criteria

- [ ] The evidence names the exact frozen baselines and inventories the full merge-base-to-main range.
- [ ] Every relevant upstream change has a classification and canonical refactor disposition; no decision is based on filename similarity alone.
- [ ] Otsu, TRX, BED, calibration, validation, conversion, and production-infrastructure boundaries are explicitly analyzed.
- [x] The Phase-3 task and evidence remained within the exact Phase 3 documentation/evidence write surface.
- [ ] The I-5B impact and historical-cohort revalidation scope are bounded without rewriting historical evidence or starting a broad experiment.
- [ ] ImageJ/Fiji closure and protected converter invariants are verified and not reopened.
- [x] The evidence records Phase 2 acceptance and Phase 3 `Review Required`; subsequent implementation remains unauthorized.

## Phase 4 acceptance criteria

- [ ] TRX uses one 90° clockwise rotation at canonical `crop_and_rotate()`.
- [ ] Exact asymmetric pixel tests prove TRX CW output, BED preservation, supported dtype, and swapped dimensions.
- [ ] No threshold, calibration, conversion, ImageJ, filtering, config, API, deployment, or production behavior changes.

## Verification requirements

### Required checks

- `./.venv/bin/python -m pytest -q tests/test_geometry_processing.py`
- `./.venv/bin/python -m pytest -q tests/test_imager_pipeline_workflow.py`
- `./.venv/bin/python -m pytest -q tests/test_radiography_pipeline.py`
- `./.venv/bin/python -m pytest -q tests/test_converter_protection.py`
- Verify the protected converter SHA and unchanged unrelated boundaries.
- Run `git diff --check` and inspect the final evidence diff.

### Required evidence

The Executor must report the exact working-tree or implementation state, commands actually run, observed outputs, source/test surfaces inspected, classification rationale, unresolved questions, and any stop condition. Local inspection must not be represented as CI or runtime production evidence.

## Stop conditions

Stop with `REVIEW BLOCKED` or `PLANNING REQUIRED` if the branch/HEAD does not match, the frozen main SHA cannot be resolved, the task path is unexpectedly changed, the converter hash differs, canonical ownership cannot be established, calibration scope cannot be bounded, a new main delta must be included, or a direct ImageJ contradiction is discovered.

Do not silently broaden scope, alter the frozen baseline, port a hotfix, or cross the production hold.

## Side-effect authorization

### Explicitly authorized side effects

- Create or update only the exact Phase 4 implementation write surface during this phase.
- No merge, rebase, cherry-pick, deployment, release, production mutation, dependency change, secret access, or external-system mutation is authorized by this task.

## Expected terminal outcome

### Review Required

Phase 4 ends with reviewable implementation and evidence. Planner/Reviewer
acceptance remains separate from release authorization.
