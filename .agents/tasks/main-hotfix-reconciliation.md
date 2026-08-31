---
title: Main Hotfix Reconciliation
document_id: TASK-MAIN-HOTFIX-RECONCILIATION-001
version: 1.4
status: Validated/Published
language: en-US
scope:
  - semantic reconciliation of the frozen main image-processing hotfix range
  - bounded canonical port of accepted image-processing hotfix semantics
  - newer-main radiography semantic-drift mapping
authority_note: This task authorizes only the bounded Phase 3 semantic-drift mapping and evidence work described below. It does not authorize runtime implementation, experiments, or release activity.
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

**Accepted Phase-2 implementation:** `e0ff8a5c093f5ad265bf65326b40663cb4454943`

**Phase-3 observed upstream main baseline:** `e94784db65bb134d43e87a2046037ab4d1cbfe02`

**Known merge base:** `fec5695048acbc3ce95d0a658032ec3701b6e045`

**Task revision:** resolved by the immutable Git publication commit containing this file; the exact full SHA is supplied in the Planner handoff.

Do not merge `main`, rebase this branch onto `main`, or mechanically cherry-pick the hotfix chain.

## Objective

**Objective:** Maintain the accepted Phase 1 and Phase 2 reconciliation history, then map the newer-main radiography semantic drift from the accepted refactor state to the observed `origin/main` baseline. Phase 3 is evidence/mapping only; implementation of newer-main semantics remains unauthorized until Planner review and republication.

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

#### Phase 3 — Newer-Main Radiography Semantic Drift Mapping

- Compare accepted refactor state `e0ff8a5c093f5ad265bf65326b40663cb4454943` with observed `origin/main` `e94784db65bb134d43e87a2046037ab4d1cbfe02`.
- Classify BED threshold defaults, TRX orientation, calibration/canvas behavior, production validation infrastructure, and other material newer-main changes.
- Record exact commits, ownership, tests, evidence, gaps, and deferred BED/TRX dataset inputs in the stable evidence file.
- Modify only this remediation write surface:
  - `.agents/tasks/main-hotfix-reconciliation.md`
  - `.agents/evidence/main-hotfix-reconciliation.md`

Do not change runtime code, tests, configuration, calibration, conversion,
deployment, production state, or experiment inputs during Phase 3.

The frozen upstream authority remains exactly
`203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`. The observed `origin/main` may be
newer; later calibration commits, including `ae41b1d5c11d99420aa195385cefa7e9b5b0a595`
and `80729162b50e92d99d45061c50ba0d875b2c4202`, are explicitly not absorbed.

Historical Phase-2 regression coverage established that Otsu returns a deterministic
scalar, remains within the valid uint16 domain or normalized float32 `[0,1]`
domain, uses the OpenCV scalar rather than the thresholded array, and updates
the representative corrected Otsu golden. It must also establish TRX bypass,
BED configured-threshold behavior, BED skip behavior, config immutability, and
unchanged unrelated downstream stage configuration.


### Out of scope

- Any file outside the exact Phase 3 documentation/evidence write surface above.
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
- Phase 1 and Phase 2 are accepted and closed. Phase 3 ends at `Review Required`.

### Remaining approval requirements

- Reviewer acceptance is recorded for Phase 2. Planner/Reviewer republication is required before any newer-main runtime implementation.
- Every material phase must end `Review Required` and republish this same task path with a new immutable SHA before the next phase is executable.
- Acceptance does not authorize promotion, deployment, or release.

## Required capabilities

- Repository read/write access limited to the exact Phase 3 documentation/evidence write surface
- Local command execution and repository history inspection

## Execution constraints

- Preserve the frozen Phase-2 baseline as historical provenance and observe newer `origin/main` separately.
- Map semantics to canonical ownership, not legacy path names.
- Distinguish implementation intent, tests, observed validation, production infrastructure, and evidence gaps.
- Do not implement BED bypass, TRX orientation, calibration/canvas changes, or any other newer-main runtime semantic.
- Do not merge, rebase, cherry-pick, modify calibration/conversion/deployment, run production workflows, or run broad research or optimization.

## Phase map

1. **PHASE 1 — UPSTREAM HOTFIX IMPACT MAPPING** — `ACCEPTED / CLOSED`.
2. **PHASE 2 — CANONICAL HOTFIX PORT** — `ACCEPTED / CLOSED` at `e0ff8a5c093f5ad265bf65326b40663cb4454943`.
3. **PHASE 3 — NEWER-MAIN RADIOGRAPHY SEMANTIC DRIFT MAPPING** — `COMPLETED / REVIEW REQUIRED`.
4. **SUBSEQUENT RUNTIME RECONCILIATION / REVALIDATION / OPTIMIZATION PHASES** — `UNAUTHORIZED`.

## Historical Phase 3 execution contract — satisfied

The following requirements were satisfied by the Phase-3 mapping and evidence
recorded in `bc093e66c590367b663a6e95073e7e0fd86d210e`; they are historical
provenance, not current execution authority:

- the task and evidence were updated with exact provenance;
- newer-main semantic drift and evidence boundaries were inspected and classified;
- deferred dataset inputs were recorded;
- runtime implementation and experiments remained unauthorized;
- the terminal state was left `Review Required`.

## Acceptance criteria

- [ ] The evidence names the exact frozen baselines and inventories the full merge-base-to-main range.
- [ ] Every relevant upstream change has a classification and canonical refactor disposition; no decision is based on filename similarity alone.
- [ ] Otsu, TRX, BED, calibration, validation, conversion, and production-infrastructure boundaries are explicitly analyzed.
- [ ] The Phase-3 task and evidence remain within the exact Phase 3 documentation/evidence write surface.
- [ ] The I-5B impact and historical-cohort revalidation scope are bounded without rewriting historical evidence or starting a broad experiment.
- [ ] ImageJ/Fiji closure and protected converter invariants are verified and not reopened.
- [ ] The evidence records Phase 2 acceptance and Phase 3 `Review Required`; subsequent implementation remains unauthorized.

## Verification requirements

### Required checks

- Verify the frozen main SHA remains historical provenance and record observed `origin/main` separately.
- Verify the relevant newer-main history, source ownership, tests, task/evidence, and validation gaps.
- Run `git diff --check` and inspect the final evidence diff.

### Required evidence

The Executor must report the exact working-tree or implementation state, commands actually run, observed outputs, source/test surfaces inspected, classification rationale, unresolved questions, and any stop condition. Local inspection must not be represented as CI or runtime production evidence.

## Stop conditions

Stop with `REVIEW BLOCKED` or `PLANNING REQUIRED` if the branch/HEAD does not match, the frozen main SHA cannot be resolved, the task path is unexpectedly changed, the converter hash differs, canonical ownership cannot be established, calibration scope cannot be bounded, a new main delta must be included, or a direct ImageJ contradiction is discovered.

Do not silently broaden scope, alter the frozen baseline, port a hotfix, or cross the production hold.

## Side-effect authorization

### Explicitly authorized side effects

- Create or update only the exact Phase 3 documentation/evidence write surface during this phase.
- No merge, rebase, cherry-pick, deployment, release, production mutation, dependency change, secret access, or external-system mutation is authorized by this task.

## Expected terminal outcome

### Review Required

Phase 3 ends with reviewable mapping and evidence. Planner/Reviewer acceptance and republication are required before any newer-main runtime implementation. Acceptance remains separate from release authorization.
