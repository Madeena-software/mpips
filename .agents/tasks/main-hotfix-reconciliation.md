---
title: Main Hotfix Reconciliation
document_id: TASK-MAIN-HOTFIX-RECONCILIATION-001
version: 1.9
status: Validated/Published
language: en-US
scope:
  - semantic reconciliation of the frozen main image-processing hotfix range
  - bounded canonical port of accepted image-processing hotfix semantics
  - newer-main radiography semantic-drift mapping
  - bounded canonical TRX orientation port
  - BED threshold policy reference grounding
authority_note: This task authorizes only the bounded Phase 6 BED threshold policy reference grounding described below. It does not authorize BED runtime-policy changes, calibration changes, production activity, optimization, or release activity.
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

**Objective:** Maintain the accepted Phase 1–5 reconciliation history, then determine whether trustworthy exact-same-acquisition BED reference material can be associated with the Phase-5 cases for an engineering comparison baseline. BED runtime-policy reconciliation, calibration, revalidation, optimization, and production work remain unauthorized.

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


### Historical Phase 5 — BED Threshold Policy Evidence Characterization (accepted)

Phase 5 is accepted and closed at `80d815c191766798bf0a6977f7abcbe24977cfbd`.
Its classification is **BED THRESHOLD POLICY UNRESOLVED**. The 12-case
characterization established that configured AUTO thresholding materially
changes the pre-threshold image relative to bypass, but did not establish a
trustworthy exact-same-acquisition engineering reference. Preserve its JSON,
CSV, and Markdown artifacts as historical evidence; do not rewrite them during
this publication.

### Phase 6 write surface

The future Phase-6 execution write surface is exactly:

- `scripts/bed_threshold_reference_grounding.py`
- `artifacts/real-data-regression/bed-threshold-reference-grounding.md`
- `artifacts/real-data-regression/bed-threshold-reference-grounding.json`
- `artifacts/real-data-regression/bed-threshold-reference-grounding.csv`
- `.agents/evidence/main-hotfix-reconciliation.md`

The helper must use the same authorized BED Drive source read-only, inventory
processed/reference artifacts separately from raw acquisition NPZ, gain NPZ,
calibration artifacts, and generated outputs, and orchestrate existing
canonical components. It must duplicate no production algorithm, become no
production dependency, and modify no canonical runtime semantics. No external
radiograph, NPZ, TIFF, thumbnail, generated image, NumPy array, calibration
carrier, or other patient/subject binary may be committed.

### Phase 6 execution contract

Phase 6 is provenance/reference grounding first. It must determine whether
trustworthy exact-same-acquisition reference material can be losslessly
associated with Phase-5 acquisition radiographs and used as an engineering
comparison baseline. It is not a new threshold-method search. Do not change
BED runtime policy or mechanically copy `dd7c21eead66a2c5396522a2310f5dd9cbd85b85`.

Use only the authorized read-only BED source:
`https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8`.
Recursively inventory it and record Drive file ID, path, filename, file type,
SHA-256 when materialized, acquisition ID, subject, session,
derivation/provenance, and dimensions/orientation where applicable. Do not
infer same-acquisition identity from subject or folder proximity.

Classify every possible reference relationship as exactly one of:
`EXACT_SAME_ACQUISITION_LOSSLESS`, `SAME_ACQUISITION_PROVENANCE_INSUFFICIENT`,
`SAME_SUBJECT_DIFFERENT_OR_UNKNOWN_ACQUISITION`, `DERIVED_PROVENANCE_UNKNOWN`,
or `NON-COMPARABLE`. The first category requires positive provenance evidence.

Use the exact accepted 12-case Phase-5 acquisition identities and provenance
from `80d815c191766798bf0a6977f7abcbe24977cfbd` as the immutable Phase-6
reference-grounding target set. Phase 6 does not select a new radiograph
cohort. Reference inventory may contain material for other acquisitions, but
it must not silently create a replacement experimental cohort.

For each accepted Phase-5 case, attempt to establish an evidence-backed
relationship to processed/reference material and record the mapping,
acquisition identity evidence, dimensions/orientation, transform parameters,
losslessness, reference SHA-256, corresponding Phase-5 raw acquisition, and
corresponding AUTO/NONE identities. Only when a trustworthy exact-same-
acquisition reference is established may Phase 6 compare reference ↔
`BED_AUTO` and reference ↔ `BED_NONE` using existing canonical
IQA/measurement components. Record conflicts and limitations; do not create a
new weighted quality score or make clinical/diagnostic claims.

Phase 6 may regenerate AUTO/NONE arrays only for a corresponding accepted
Phase-5 case and only when required for an established reference comparison.
Use the exact accepted Phase-5 acquisition and gain provenance, preserve
canonical Phase-5 semantics, verify source/input identity against accepted
Phase-5 hashes, and where applicable verify regenerated AUTO/NONE outputs
against accepted Phase-5 hashes. Any discrepancy is a stop condition; do not
silently replace Phase-5 evidence. If inventory establishes that no accepted
Phase-5 case has a trustworthy `EXACT_SAME_ACQUISITION_LOSSLESS` reference,
short-circuit without rerunning AUTO/NONE characterization and retain
`BED THRESHOLD POLICY UNRESOLVED`.

Use only lossless geometry reconciliation: known orientation transform, crop,
pad, integer translation, and valid-mask intersection. Resize, interpolation,
resampling, warp, or non-rigid registration makes the comparison
`NON-COMPARABLE`.

End with exactly one classification: `BED BYPASS SUPPORTED`, `BED CONFIGURED
THRESHOLD SUPPORTED`, or `BED THRESHOLD POLICY UNRESOLVED`. This is decision
support only and does not change production or canonical defaults.

Do not modify `mpips/conversion/tiff_json_to_dcm.py`; required SHA-256 is
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`. Preserve
ImageJ/Fiji closure, accepted TRX orientation/bypass, current BED configured
threshold behavior, and `NPZ → processing → DICOM` boundaries. Historical
threshold results affected by corrected Otsu semantics are context only.

### Out of scope

- Any file outside the Phase-6 evidence write surface above.
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
- Historical Phase-5 characterization used the deferred detector-specific BED and TRX Drive sources only as bounded evidence inputs; no current Phase-6 cohort or optimization scope is implied.

## Dependencies and assumptions

### Dependencies

- Exact branch and baseline state listed above.
- Frozen main commit and relevant history are locally resolvable.
- Accepted ImageJ/Fiji and I-5B artifacts remain available for comparison.

### Approved assumptions

- The canonical owners are under `mpips/processing/`, `mpips/pipelines/`, `mpips/workflows/imager_pipeline/`, and `mpips/calibration/`; removed `mpips/engine/` modules must not be resurrected.
- Phases 1–5 are accepted and closed. Phase 6 ends at `Review Required`.

### Remaining approval requirements

- Reviewer acceptance is recorded for Phases 2–5. Planner/Reviewer review is required after Phase 6 evidence execution.
- Every material phase must end `Review Required` and republish this same task path with a new immutable SHA before the next phase is executable.
- Acceptance does not authorize promotion, deployment, or release.

## Required capabilities

- Repository read/write access limited to the exact Phase 6 evidence write surface
- Local command execution and bounded reference-grounding verification

## Execution constraints

- Preserve accepted Phase-1–5 provenance.
- Change only the Phase-6 write surface; do not modify BED runtime thresholding, calibration, conversion, ImageJ, filtering, config, API, deployment, or production behavior.
- Do not run Phase 6 during task republication. Do not merge, rebase, cherry-pick, run production workflows, deploy, release, or mutate external systems.

## Phase map

1. **PHASE 1 — UPSTREAM HOTFIX IMPACT MAPPING** — `ACCEPTED / CLOSED`.
2. **PHASE 2 — CANONICAL HOTFIX PORT** — `ACCEPTED / CLOSED` at `e0ff8a5c093f5ad265bf65326b40663cb4454943`.
3. **PHASE 3 — NEWER-MAIN RADIOGRAPHY SEMANTIC DRIFT MAPPING** — `ACCEPTED / CLOSED` at `b9093b0aec5dd66cf2a5afcd5028c2876cf889bd`.
4. **PHASE 4 — CANONICAL TRX ORIENTATION PORT** — `ACCEPTED / CLOSED` at `820948734e8b598b851135cc82c2210ead934963`.
5. **PHASE 5 — BED THRESHOLD POLICY EVIDENCE CHARACTERIZATION** — `ACCEPTED / CLOSED` at `80d815c191766798bf0a6977f7abcbe24977cfbd`.
6. **PHASE 6 — BED THRESHOLD POLICY REFERENCE GROUNDING** — `CURRENT RELEASED PHASE`.
7. **BED RUNTIME-POLICY IMPLEMENTATION** — `UNAUTHORIZED`.
8. **CALIBRATION RECONCILIATION** — `UNAUTHORIZED`.
9. **BROADER REVALIDATION / OPTIMIZATION / PRODUCTION PHASES** — `UNAUTHORIZED`.

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

The following requirements were satisfied by the accepted Phase-4
implementation; they are historical facts, not current execution authority:

- TRX rotation changed from 90° CCW to 90° CW in canonical `crop_and_rotate()`.
- Documentation was updated to say clockwise.
- Exact asymmetric pixel assertions were added for TRX CW output and BED
  crop-only behavior.
- Crop-before-rotation, dtype, swapped dimensions, and workflow-wrapper
  behavior were preserved.
- The stable evidence file was updated with observed implementation and
  verification.
- BED policy, calibration, conversion, ImageJ, deployment, and production
  behavior remained unchanged.
- The terminal state was left `Review Required`.

## Historical Phase 3 acceptance criteria — satisfied

- [x] The evidence names the exact frozen baselines and inventories the full merge-base-to-main range.
- [x] Every relevant upstream change has a classification and canonical refactor disposition; no decision is based on filename similarity alone.
- [x] Otsu, TRX, BED, calibration, validation, conversion, and production-infrastructure boundaries are explicitly analyzed.
- [x] The Phase-3 task and evidence remained within the exact Phase 3 documentation/evidence write surface.
- [x] The I-5B impact and historical-cohort revalidation scope are bounded without rewriting historical evidence or starting a broad experiment.
- [x] ImageJ/Fiji closure and protected converter invariants are verified and not reopened.
- [x] The evidence records Phase 2 acceptance and Phase 3 `Review Required`; subsequent implementation remains unauthorized.

## Historical Phase 4 acceptance criteria — satisfied

- [x] TRX uses one 90° clockwise rotation at canonical `crop_and_rotate()`.
- [x] Exact asymmetric pixel tests prove TRX CW output, BED preservation, supported dtype, and swapped dimensions.
- [x] No threshold, calibration, conversion, ImageJ, filtering, config, API, deployment, or production behavior changes.

## Verification requirements

### Required checks for Phase 6

- `./.venv/bin/python -m pytest -q tests/test_iqa_safety.py`
- `./.venv/bin/python -m pytest -q tests/test_imager_pipeline_workflow.py`
- `./.venv/bin/python -m pytest -q tests/test_radiography_pipeline.py`
- `./.venv/bin/python -m pytest -q tests/test_converter_protection.py`
- When the Phase-6 helper exists, run applicable quality checks:
  `./.venv/bin/python -m black --check scripts/bed_threshold_reference_grounding.py`
  and `./.venv/bin/python -m flake8 scripts/bed_threshold_reference_grounding.py`.
- Run repository-authorized mypy, syntax, and import checks where applicable.

### Phase-6 evidence checks

- Verify processed/reference material is inventoried separately from acquisition, gain, calibration, and generated-output artifacts.
- Verify each reference classification has evidence; exact-same-acquisition requires positive provenance.
- Verify JSON parses, CSV and JSON rows agree, and Markdown conclusions are traceable to machine-readable evidence.
- Verify only lossless geometry reconciliation is used; otherwise classify `NON-COMPARABLE`.
- Verify the exact Phase-6 write surface is respected.
- Verify no NPZ, TIFF, image, NumPy, calibration, or other binary is committed.
- Verify no runtime, default, or configuration source changes occur.
- Verify the protected converter SHA remains
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Run `git diff --check`.

### Required evidence

The Executor must report the exact working-tree or implementation state, commands actually run, observed outputs, source/test surfaces inspected, classification rationale, unresolved questions, and any stop condition. Local inspection must not be represented as CI or runtime production evidence.

## Stop conditions

Stop with `REVIEW BLOCKED` or `PLANNING REQUIRED` if the branch/HEAD does not match, the frozen main SHA cannot be resolved, the task path is unexpectedly changed, the converter hash differs, canonical ownership cannot be established, calibration scope cannot be bounded, a new main delta must be included, or a direct ImageJ contradiction is discovered.

Do not silently broaden scope, alter the frozen baseline, port a hotfix, or cross the production hold.

## Side-effect authorization

### Explicitly authorized side effects

- Read-only access to the designated BED Drive source.
- Local bounded Phase-6 reference-grounding execution.
- Create or update only the exact Phase-6 write surface above.

### Explicitly prohibited side effects

- Drive mutation; BED runtime/default/config changes; threshold algorithm
  modification; calibration generation, mutation, or promotion; converter or
  ImageJ/Fiji modification; deployment; production mutation; merge; rebase;
  cherry-pick; release; or main promotion.
- Push is not authorized by this corrective remediation.

## Expected terminal outcome

### Review Required

`PHASE 6 TASK REPUBLICATION CANDIDATE — PLANNER REVIEW REQUIRED`

Phase-6 execution outcomes are `PHASE 6 EVIDENCE CANDIDATE — PLANNER REVIEW
REQUIRED` on successful completion or `PHASE 6 EVIDENCE BLOCKED — PLANNER
REVIEW REQUIRED` when a stop condition prevents trustworthy completion.
Planner/Reviewer acceptance remains separate from release authorization.
