---
title: Main Hotfix Reconciliation
document_id: TASK-MAIN-HOTFIX-RECONCILIATION-001
version: 1.0
status: Validated/Published
language: en-US
scope:
  - semantic reconciliation of the frozen main image-processing hotfix range
  - bounded impact mapping before radiography optimization
authority_note: This task authorizes only the bounded Phase 1 evidence work described below. Acceptance is not release authorization.
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

**Objective:** Publish and execute Phase 1, `UPSTREAM HOTFIX IMPACT MAPPING`, to freeze and classify the main-only hotfix range, map relevant semantics to canonical refactor owners, identify conflicts and missing behavior, define the smallest Phase 2 write surface, and bound later I-5B impact revalidation.

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
- Phase 1 evidence contract → `PHASE 1 — UPSTREAM HOTFIX IMPACT MAPPING` in the initial reconciliation directive
- Protected ImageJ/converter and production-hold boundaries → protection and hold requirements in the initial reconciliation directive

## Scope

### In scope

- Inspect commits in `fec5695048acbc3ce95d0a658032ec3701b6e045..203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`.
- Inventory and classify every relevant main-only change as image-processing, calibration, production validation, workflow/promotion infrastructure, test-only, or unrelated.
- Explicitly inspect Otsu return-value correction, TRX bypass, BED threshold preservation, diagnostic override, collapse/stage-observer validation, final image/DICOM structural validation, calibration lattice/remap safety, carrier/promotion changes, conversion worker/service changes, and NPZ → processing → DICOM semantics.
- Compare each relevant behavior with the canonical refactor owner and determine whether it is already present, partial, missing, conflicting, or not applicable.
- Define the smallest Phase 2 source/test write surface and the exact bounded Phase 4 I-5B revalidation subset.
- Record evidence only in `.agents/evidence/main-hotfix-reconciliation.md` during Phase 1.

### Out of scope

- Any production source, test, script, workflow, dependency, configuration, schema, API, worker, artifact, or converter modification during Phase 1.
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
- Phase 1 is evidence/planning only and ends at `Review Required`.

### Remaining approval requirements

- Reviewer acceptance is required after Phase 1 before any Phase 2 implementation.
- Every material phase must end `Review Required` and republish this same task path with a new immutable SHA before the next phase is executable.
- Acceptance does not authorize promotion, deployment, or release.

## Required capabilities

- Repository read and write access limited to the Phase 1 evidence file
- Git history inspection and local command execution
- Test/source inspection as read-only evidence gathering

## Execution constraints

- Use the frozen main SHA exactly; if main has advanced, do not include the new delta.
- Map semantics to canonical ownership, not legacy path names.
- Do not implement the known Otsu fix or TRX policy in Phase 1.
- Treat the correct OpenCV contract as `threshold_value, thresholded_image = cv2.threshold(...)`; document the current canonical bug, corrected semantics, dtype/range implications, and missing regressions.
- Distinguish runtime behavior from production-only diagnostics, carrier, promotion, deployment, and preflight infrastructure.
- Do not run broad research or the later optimization experiment.

## Phase map

1. **PHASE 1 — UPSTREAM HOTFIX IMPACT MAPPING** — CURRENT RELEASED PHASE; evidence/planning only; ends `Review Required`.
2. **PHASE 2 — CANONICAL HOTFIX PORT** — UNAUTHORIZED until Phase 1 review acceptance and republished task revision.
3. **PHASE 3 — TARGETED HOTFIX REGRESSION VERIFICATION** — UNAUTHORIZED until Phase 2 review acceptance and republished task revision.
4. **PHASE 4 — I-5B IMPACT REVALIDATION** — UNAUTHORIZED until Phase 3 review acceptance and republished task revision.
5. **PHASE 5 — RECONCILIATION CLOSURE** — UNAUTHORIZED until Phase 4 review acceptance and republished task revision.

## Phase 1 execution contract

The Executor must produce `.agents/evidence/main-hotfix-reconciliation.md` containing:

- frozen branch, HEAD, origin, main baseline, and merge-base evidence;
- the complete commit/behavior mapping table with upstream SHA, subject, path, behavior, category, refactor relevance, canonical owner, presence, conflict, disposition, and rationale;
- explicit analysis of all high-priority items listed in Scope;
- exact current Otsu bug and corrected semantic mapping, including uint16/float32 expectations and test gaps;
- deliberate TRX/BED policy ownership and diagnostic-override disposition;
- calibration scope decision, including whether it remains safely bounded or requires a separate task;
- explicit ImageJ result: expected `NO REOPENING REQUIRED` unless a direct contradiction is evidenced;
- exact smallest Phase 2 source/test write surface and items not to port;
- affected I-5B rows/conclusions and the smallest Phase 4 revalidation subset, preserving the original cohort and experiment identity where technically possible;
- a truthful verification record and terminal state `Review Required`.

## Acceptance criteria

- [ ] The evidence names the exact frozen baselines and inventories the full merge-base-to-main range.
- [ ] Every relevant upstream change has a classification and canonical refactor disposition; no decision is based on filename similarity alone.
- [ ] Otsu, TRX, BED, calibration, validation, conversion, and production-infrastructure boundaries are explicitly analyzed.
- [ ] The evidence identifies the Phase 2 write surface without modifying production source or tests.
- [ ] The I-5B impact and historical-cohort revalidation scope are bounded without rewriting historical evidence or starting a broad experiment.
- [ ] ImageJ/Fiji closure and protected converter invariants are verified and not reopened.
- [ ] The evidence records `Review Required`; Phase 2–5 remain unauthorized until republished after review.

## Verification requirements

### Required checks

- Verify branch, local HEAD, origin HEAD, frozen main commit, merge base, clean starting state, task path, and protected converter SHA.
- Inspect the full frozen commit range and relevant canonical source/test surfaces.
- Run `git diff --check` and inspect the final evidence diff.

### Required evidence

The Executor must report the exact working-tree or implementation state, commands actually run, observed outputs, source/test surfaces inspected, classification rationale, unresolved questions, and any stop condition. Local inspection must not be represented as CI or runtime production evidence.

## Stop conditions

Stop with `REVIEW BLOCKED` or `PLANNING REQUIRED` if the branch/HEAD does not match, the frozen main SHA cannot be resolved, the task path is unexpectedly changed, the converter hash differs, canonical ownership cannot be established, calibration scope cannot be bounded, a new main delta must be included, or a direct ImageJ contradiction is discovered.

Do not silently broaden scope, alter the frozen baseline, port a hotfix, or cross the production hold.

## Side-effect authorization

### Explicitly authorized side effects

- Create or update only `.agents/evidence/main-hotfix-reconciliation.md` during Phase 1 execution.
- No Git commit, push, merge, rebase, deployment, release, production mutation, dependency change, secret access, or external-system mutation is authorized by Phase 1 execution.

## Expected terminal outcome

### Review Required

Phase 1 ends with a reviewable evidence file and truthful verification record. Reviewer acceptance is required before the same task path may be republished with Phase 2 authority. Acceptance remains separate from release authorization.
