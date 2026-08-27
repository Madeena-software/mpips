---
title: MPIPS TRX output orientation hotfix
document_id: TASK-MPIPS-TRX-OUTPUT-ORIENTATION-HOTFIX
version: 1.0
status: Validated/Published
language: en-US
scope:
  - canonical TRX crop/rotate orientation correction and regression coverage
authority_note: This task authorizes only the bounded TRX output-orientation correction and associated tests. It does not authorize production mutation, deployment, release, or external-system changes.
---

# Executable Task

## Task identity

**Task title:** MPIPS TRX output orientation hotfix

**Task path:** `.agents/tasks/mpips-trx-output-orientation-hotfix.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Correct the accepted production MPIPS TRX DICOM orientation at the canonical detector-specific crop/rotate boundary.

**Owner / designated planning authority:** Human operator / Planner-Reviewer handoff.

## Delivery context

The accepted production MPIPS pipeline produces real THORAX/TRX DICOM images upside-down in the MHCS viewer. The observed cause is the canonical TRX crop/rotate step using a 90-degree counterclockwise rotation. A clockwise rotation provides the required 180-degree change relative to the current output while preserving dimensions.

## Baseline and task revision

**Implementation baseline:** `e8122ad7b1ac38614b4c18f5d36875c478feb6c5`

**Task revision:** resolved as the immutable Git publication revision before implementation handoff.

## Objective

Change the canonical TRX crop/rotate operation from 90° counterclockwise to 90° clockwise, update its informational output, and add deterministic source-level and pipeline-level regressions proving TRX pixel orientation and preserving BED behavior and output geometry.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Planner-reviewed hotfix request supplied with this task

### Requirement traceability

- TRX orientation correction → Planner-reviewed hotfix request
- Preserve calibration, dimensions, BED behavior, and DICOM contract → Planner-reviewed hotfix request and repository context
- Deterministic orientation regression coverage → Planner-reviewed hotfix request

## Scope

### In scope

- `mpips/engine/imager_pipeline/complete_pipeline.py`
- `tests/test_imager_pipeline_workflow.py`
- Directly affected existing TRX expectation only if required by the new orientation semantics

### Out of scope

- calibration generation, fingerprints, metadata, `map_x`, `map_y`, remap geometry, or calibration carriers
- FFC, thresholding, ImageJ, CLAHE, median filtering, DICOM conversion, API schemas, MHCS integration, Docker/runtime configuration, secrets, production calibration layout, deployment, production verification, or Stage C dispatch
- any second rotation, flip, DICOM metadata workaround, heuristic, or clinical validation
- archived implementation copies under `artifacts/`

### Preserved behavior

- TRX calibration fingerprint: `1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492`
- expanded remap geometry: source `3000x4096`, remap `3045x4114`, origin `[42,-73]`
- final TRX DICOM geometry: Rows `4114`, Columns `3045`
- BED remains cropped and unrotated
- DICOM converter semantics and all unrelated pipeline stages remain unchanged

## Dependencies and assumptions

### Dependencies

- The implementation baseline remains unchanged after task publication.
- Existing OpenCV/NumPy/pytest test dependencies are available.

### Remaining approval requirements

- Human review is required before implementation acceptance.
- No production deployment, workflow dispatch, or release authorization is granted.

## Required capabilities

- repository read/write
- shell and focused test execution
- Codebase Memory MCP for implementation discovery where useful
- Git publication for the task, followed by implementation

## Execution constraints

- Keep the correction at `crop_and_rotate_by_detector()`; do not add a later transform.
- Use `cv2.ROTATE_90_CLOCKWISE` for TRX and update the corresponding informational text from `rotated 90° CCW` to `rotated 90° CW`.
- Use asymmetric deterministic sentinel data and assert exact pixel positions, not only shape.
- Add/retain a BED regression proving the sentinel is unchanged.
- Add pipeline-level asymmetric coverage with unrelated optional processing disabled where practical; prove TRX clockwise orientation and swapped dimensions while preserving BED behavior.
- Do not use `np.flip`, `np.fliplr`, `np.flipud`, a 180-degree post-process, or DICOM metadata tricks.
- Do not include real patient pixels in output, logs, or commits.

## Acceptance criteria

- [ ] Canonical TRX crop/rotate uses 90° clockwise and its informational output says `rotated 90° CW`.
- [ ] Direct canonical regression maps `[[1,2,3],[4,5,6]]` to `[[4,1],[5,2],[6,3]]` for TRX.
- [ ] BED regression returns the asymmetric sentinel unchanged.
- [ ] Pipeline-level regression proves TRX pixel orientation and swapped output shape, and BED behavior remains unchanged.
- [ ] No calibration, DICOM, API, runtime, or production files outside scope are changed.

## Verification requirements

### Required checks

- `pytest tests/test_imager_pipeline_workflow.py -q`
- `pytest tests/api/test_dicom_conversion.py -q`
- `pytest tests/test_verify_production_real_trx.py -q`
- directly affected TRX tests, if any
- `black --check` on affected Python files
- `flake8` on affected Python files
- `python -m compileall` on affected Python files
- `git diff --check`
- broader relevant suite if practical

### Required evidence

Report the exact implementation revision or working-tree state, observed command results, changed files, old and new TRX sentinel output, expected clockwise output, equality proof, swapped-shape proof, unchanged BED output, and explicit `NO` results for calibration fingerprint changes, DICOM converter changes, production deployment, and production workflow dispatch.

## Stop conditions

Stop and return to planning if the baseline changes, the canonical boundary is not the active production path, any calibration/DICOM/API/runtime change is required, acceptance requires clinical validation, or any production/external mutation is needed.

## Side-effect authorization

This task authorizes task publication and repository implementation only. It does not authorize deployment, production workflow dispatch, production mutation, calibration mutation, external-system mutation, or release.

### Explicitly authorized side effects

- Publish this task as its own Git commit.
- Publish the implementation as a separate Git commit after verification.
- Push the two commits, if the configured repository remote is available.

## Expected terminal outcome

**Review Required**
