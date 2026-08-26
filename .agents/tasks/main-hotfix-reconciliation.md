---
title: Main Hotfix Reconciliation
document_id: TASK-MAIN-HOTFIX-RECONCILIATION-001
version: 1.1
status: Validated/Published
language: en-US
scope:
  - semantic reconciliation of the frozen main image-processing hotfix range
  - bounded canonical port of accepted image-processing hotfix semantics
authority_note: This task authorizes only the bounded Phase 2 canonical hotfix port described below. Acceptance is not release authorization.
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

**Implementation baseline:** `a4a5c16881e589154680f0606c849e2a4514041f`

**Frozen upstream main baseline:** `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`

**Known merge base:** `fec5695048acbc3ce95d0a658032ec3701b6e045`

**Task revision:** resolved by the immutable Git publication commit containing this file; the exact full SHA is supplied in the Planner handoff.

Do not merge `main`, rebase this branch onto `main`, or mechanically cherry-pick the hotfix chain.

## Objective

**Objective:** Execute the released Phase 2, `CANONICAL HOTFIX PORT`, by porting only the accepted Otsu scalar handling and TRX/BED threshold policy into canonical refactor ownership, with bounded regression protection. Phase 1 is accepted and closed; calibration, diagnostics, validation/promotion infrastructure, and later main changes remain excluded.

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

#### Phase 2 — Canonical Hotfix Port

- Correct OpenCV Otsu return-value handling in `mpips/processing/thresholding.py`.
- Apply detector-specific threshold policy in `mpips/pipelines/radiography.py`: TRX bypasses threshold separation by default; BED preserves configured threshold behavior.
- Add minimal deterministic regression coverage for scalar/range/determinism/Otsu semantics and TRX/BED policy behavior.
- Update only this future Phase 2 write surface:
  - `mpips/processing/thresholding.py`
  - `mpips/pipelines/radiography.py`
  - `tests/test_thresholding_processing.py`
  - `tests/test_radiography_pipeline.py`
  - `.agents/evidence/main-hotfix-reconciliation.md`

The accepted Phase 1 evidence is preserved as the evidence input for this
authorization. No Phase 2 implementation occurs in this publication.

The frozen upstream authority remains exactly
`203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`. The observed `origin/main` may be
newer; later calibration commits, including `ae41b1d5c11d99420aa195385cefa7e9b5b0a595`
and `80729162b50e92d99d45061c50ba0d875b2c4202`, are explicitly not absorbed.

Phase 2 regression coverage must establish that Otsu returns a deterministic
scalar, remains within the valid uint16 domain or normalized float32 `[0,1]`
domain, uses the OpenCV scalar rather than the thresholded array, and updates
the representative corrected Otsu golden. It must also establish TRX bypass,
BED configured-threshold behavior, BED skip behavior, config immutability, and
unchanged unrelated downstream stage configuration.


### Out of scope

- Any file outside the exact Phase 2 write surface above.
- Calibration, diagnostic or stage-observer plumbing, collapse-gate validation rules, validation/promotion/deployment infrastructure, and production API expansion.
- Git merge, rebase, mechanical cherry-pick, main promotion, deployment, release, or production mutation.
- Reopening accepted ImageJ/Fiji Contrast, Equalization, Hybrid Median, Circular Median, or CLAHE fidelity closure absent a direct contradiction; such a contradiction stops review.
- Broad Radiography Pipeline Optimization or a new experiment.
- Rewriting or deleting historical I-5B evidence.

### Preserved behavior

- The accepted ImageJ/Fiji closure remains protected at baseline `a4a5c16881e589154680f0606c849e2a4514041f`.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical; required SHA-256 is `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- TRX threshold separation is bypassed by default; BED retains its configured threshold method.
- Historical I-5B evidence remains intact. Otsu-affected threshold rows may require bounded revalidation; CLAHE and unaffected rows are not automatically invalidated.
- The later optimization primary source remains the preferred Drive folder; historical I-5B data is reused only for controlled impact comparability.

## Dependencies and assumptions

### Dependencies

- Exact branch and baseline state listed above.
- Frozen main commit and relevant history are locally resolvable.
- Accepted ImageJ/Fiji and I-5B artifacts remain available for comparison.

### Approved assumptions

- The canonical owners are under `mpips/processing/`, `mpips/pipelines/`, `mpips/workflows/imager_pipeline/`, and `mpips/calibration/`; removed `mpips/engine/` modules must not be resurrected.
- Phase 1 evidence is accepted and closed. Phase 2 ends at `Review Required`.

### Remaining approval requirements

- Reviewer acceptance is required after Phase 1 before any Phase 2 implementation.
- Every material phase must end `Review Required` and republish this same task path with a new immutable SHA before the next phase is executable.
- Acceptance does not authorize promotion, deployment, or release.

## Required capabilities

- Repository read/write access limited to the exact Phase 2 write surface
- Local command execution and focused test verification

## Execution constraints

- Use the frozen main SHA exactly; if main has advanced, do not include the new delta.
- Map semantics to canonical ownership, not legacy path names.
- Implement the OpenCV contract `threshold_value, thresholded_image = cv2.threshold(...)`; for float32 inputs retain uint16 conversion and normalize the returned scalar to `[0,1]`, and do not derive it from the output array.
- Keep low-level thresholding detector-agnostic. In radiography orchestration, bypass threshold separation for TRX by default and honor configured threshold behavior for BED, preserving global disable/skip semantics without mutating config.
- Distinguish runtime behavior from production-only diagnostics, carrier, promotion, deployment, and preflight infrastructure.
- Do not modify calibration or absorb later `origin/main` calibration commits.
- Do not run broad research or the later optimization experiment.

## Phase map

1. **PHASE 1 — UPSTREAM HOTFIX IMPACT MAPPING** — `ACCEPTED / CLOSED`.
2. **PHASE 2 — CANONICAL HOTFIX PORT** — `CURRENT RELEASED PHASE`.
3. **PHASE 3 — TARGETED HOTFIX REGRESSION VERIFICATION** — `UNAUTHORIZED`.
4. **PHASE 4 — I-5B IMPACT REVALIDATION** — `UNAUTHORIZED`.
5. **PHASE 5 — RECONCILIATION CLOSURE** — `UNAUTHORIZED`.

## Phase 2 execution contract

The Executor must:

- implement the bounded Otsu and TRX/BED changes;
- add the bounded regression coverage listed in the Phase 2 requirements;
- update the stable evidence file with implementation and verification evidence;
- leave the terminal state `Review Required`.

## Acceptance criteria

- [ ] The evidence names the exact frozen baselines and inventories the full merge-base-to-main range.
- [ ] Every relevant upstream change has a classification and canonical refactor disposition; no decision is based on filename similarity alone.
- [ ] Otsu, TRX, BED, calibration, validation, conversion, and production-infrastructure boundaries are explicitly analyzed.
- [ ] The implementation and evidence remain within the exact Phase 2 write surface.
- [ ] The I-5B impact and historical-cohort revalidation scope are bounded without rewriting historical evidence or starting a broad experiment.
- [ ] ImageJ/Fiji closure and protected converter invariants are verified and not reopened.
- [ ] The evidence records `Review Required`; Phase 3–5 remain unauthorized until republished after review.

## Verification requirements

### Required checks

- Verify the frozen main SHA remains `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd` and later main calibration deltas are excluded.
- Verify the focused canonical source/test surfaces, protected converter SHA, and Phase 2 behavior.
- Run `git diff --check` and inspect the final evidence diff.

### Required evidence

The Executor must report the exact working-tree or implementation state, commands actually run, observed outputs, source/test surfaces inspected, classification rationale, unresolved questions, and any stop condition. Local inspection must not be represented as CI or runtime production evidence.

## Stop conditions

Stop with `REVIEW BLOCKED` or `PLANNING REQUIRED` if the branch/HEAD does not match, the frozen main SHA cannot be resolved, the task path is unexpectedly changed, the converter hash differs, canonical ownership cannot be established, calibration scope cannot be bounded, a new main delta must be included, or a direct ImageJ contradiction is discovered.

Do not silently broaden scope, alter the frozen baseline, port a hotfix, or cross the production hold.

## Side-effect authorization

### Explicitly authorized side effects

- Create or update only the exact Phase 2 write surface during Phase 2 execution.
- No merge, rebase, cherry-pick, deployment, release, production mutation, dependency change, secret access, or external-system mutation is authorized by this task.

## Expected terminal outcome

### Review Required

Phase 2 ends with reviewable implementation and evidence. Reviewer acceptance is required before the same task path may be republished with Phase 3 authority. Acceptance remains separate from release authorization.
