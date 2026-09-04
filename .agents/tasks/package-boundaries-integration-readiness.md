---
title: Package Boundaries Integration Readiness
document_id: TASK-PACKAGE-BOUNDARIES-INTEGRATION-READINESS-001
version: 1.2
status: Validated/Published
language: en-US
last_updated: 2026-09-04
authority_note: >-
  This task authorizes bounded non-destructive synchronization of origin/main
  into refactor/package-boundaries, branch reconciliation verification (especially
  NPZ-to-DICOM correctness), push/update of refactor/package-boundaries, and
  creation of an integration pull request to main. It does not authorize PR merge,
  deployment, release, or production mutation.
---

# Executable Task

## Task identity

**Task title:**
`Package Boundaries Integration Readiness`

**Task path:**
`.agents/tasks/package-boundaries-integration-readiness.md`

**Task contract state:**
`Validated/Published`

**Delivery objective / Work Package / MVP:**
`Safely integrate origin/main into refactor/package-boundaries, verify reconciled branch and NPZ-to-DICOM correctness, and create integration PR to main`

**Owner / designated planning authority:**
`Repository Planner/Reviewer under the .agents/ delivery contract`

## Delivery context

The accepted `refactor/package-boundaries` implementation is substantially
diverged from `main` (144 commits ahead and 78 commits behind `main`, with merge
base `fec5695048acbc3ce95d0a658032ec3701b6e045`).

Prior task version v1.1 authorized only non-persistent, read-only integration
analysis and strictly prohibited branch mutation, merge, push, and PR creation.
The latest Human Request explicitly authorizes bounded synchronization of
`origin/main` into `refactor/package-boundaries`, remote branch update of that
same branch, and creation of an integration pull request from
`refactor/package-boundaries` to `main`, provided reconciliation and verification
succeed.

This remediated task (v1.2) replaces the v1.1 contract. It establishes the
validated delivery contract for executing a non-destructive merge of `origin/main`
into `refactor/package-boundaries`, performing rigorous verification of the
reconciled branch—with mandatory observed evidence of NPZ-to-DICOM conversion
integrity, clinical invariants, and package boundary health—and creating the
integration pull request for human/team review.

Exposing NPZ-to-DICOM as a supported Python import surface is explicitly
separated as a distinct, dependent successor objective and is not part of this task.

## Baseline and comparison identity

**Validated feature implementation baseline (pre-synchronization):**
`ccbb2a5707741903d5eaa75c72e789405d6e055f`

**Relevant `main` comparison baseline:**
`f1ef9604e06f98119de73f6e4df1e5ea619ae278`

**Known merge base:**
`fec5695048acbc3ce95d0a658032ec3701b6e045`

**Branch relationship:**
`refactor/package-boundaries` is currently observed as 144 commits ahead and
78 commits behind `main`.

**Task revision:**
The exact immutable Git revision containing this published task is established
upon task publication:
`.agents/tasks/package-boundaries-integration-readiness.md @ <commit SHA>`
The implementation baseline and governing task revision are separate identities.

## Authoritative inputs

### Governing authority

- applicable higher-priority Human Request explicitly authorizing bounded
  synchronization of `origin/main` into `refactor/package-boundaries`, remote
  branch update, and integration PR creation;
- `AGENTS.md`;
- `.agents/AGENTS.md`;
- `.agents/software-workflow.md`;
- accepted repository delivery state and decisions legitimately governing this work;
- this task once accepted as the governing delivery contract.

### Supporting context and procedure

- `.agents/context/project.md`;
- `.agents/prompts/plan-create-task.md`;
- `.agents/tasks/_template.md`.

These materials support planning, execution, and review but do not independently
govern the delivery objective.

### Accepted prior decisions and traceability

- accepted/closed `.agents/tasks/main-hotfix-reconciliation.md` v1.14;
- accepted/closed `.agents/tasks/radiography-pipeline-optimization.md` v1.1;
- accepted feature implementation baseline `ccbb2a5707741903d5eaa75c72e789405d6e055f`;
- accepted `main` baseline `f1ef9604e06f98119de73f6e4df1e5ea619ae278` (including
  emergency batch hotfixes, CI workflow improvements, and ops maintenance merged to `main`);
- accepted package boundaries, internal module reorganization, and import structure
  established on `refactor/package-boundaries`.

### Observed implementation and verification evidence

- source code, configuration, and tests on both `refactor/package-boundaries` and `main`;
- Git history, branch refs, and the merge base `fec5695048acbc3ce95d0a658032ec3701b6e045`;
- `.github/workflows/ci.yml` and related GitHub Actions workflows representing the
  configured repository CI verification surface;
- available local and CI verification results.

Observed evidence describes repository reality and does not become governing
authority merely because it is useful for verification.

### Relevant accepted decisions and observed invariants

- **Protected canonical DICOM converter:** SHA-256 is strictly
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` at
  `mpips/conversion/tiff_json_to_dcm.py`. The legacy location
  `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` must remain absent.
- **Accepted TRX behavior:** Canonical clockwise orientation and threshold bypass
  are accepted; expected golden characterization output hash is
  `5b9af36adc670ed1d93d650179d60b9cb2688cc53fa21f64fb4049de33e88d56`.
- **BED threshold behavior:** Configured threshold semantics remain preserved.
- **ImageJ/Fiji fidelity:** Accepted fidelity decisions remain preserved.
- **Calibration policy:** Fixed-canvas output is the canonical default; expanded-canvas
  remains opt-in; unapproved numeric calibration thresholds remain unadopted.
- **Package boundaries:** Reorganized domain modules under `mpips/` and supported
  public import surfaces are preserved.
- **Main-branch hotfixes:** Unrelated operational changes and hotfixes from `main`
  must be cleanly preserved during reconciliation.

## Objective

Safely synchronize `origin/main` into `refactor/package-boundaries` using a
non-destructive, non-history-rewriting merge; resolve any integration conflicts
with semantic review; rigorously verify the reconciled branch—with mandatory
observed proof of NPZ-to-DICOM conversion correctness, converter integrity, pixel
semantics, orientation, and metadata invariants; update
`origin/refactor/package-boundaries`; and create exactly one integration pull
request to `main`.

## Scope

### In scope

- Non-destructive synchronization of `origin/main` (`f1ef9604e06f98119de73f6e4df1e5ea619ae278`)
  into `refactor/package-boundaries` (`ccbb2a5707741903d5eaa75c72e789405d6e055f`).
- Semantic review and resolution of integration conflicts.
- Verification of the reconciled branch against the full test suite, linting,
  formatting, type checking, build/smoke checks, and converter protection.
- Thorough NPZ-to-DICOM acceptance verification, including synthetic and fixture-based
  radiograph + gain + manifest conversions to valid DICOM.
- Pushing the reconciled `refactor/package-boundaries` branch to origin without force.
- Creating exactly one pull request from `refactor/package-boundaries` to `main`
  with detailed traceability, verification evidence, and explicit NPZ-to-DICOM
  validation results.

### Out of scope

- Merging the pull request into `main` (requires separate review/merge authorization).
- Deployment, release, production mutation, or external infrastructure operations.
- History rewriting, rebase, squash, or force-pushing either branch.
- Silent or purely textual conflict resolution that glosses over semantic divergence.
- Designing or implementing the importable Python NPZ-to-DICOM module API surface
  (governed as a distinct successor task).
- Reopening accepted BED, TRX, ImageJ/Fiji, calibration, or radiography pipeline decisions.
- Using real-patient data, committing credentials, or introducing external sensitive artifacts.
- Unrelated feature work, refactoring outside integration necessity, or speculative
  dependency additions.

### Preserved invariants

All accepted behavior and invariants already recorded by the repository must be
strictly preserved:

1. **Existing API functionality:** `POST /v1/radiographs/dicom` and `GET /health`,
   API-key authentication, schemas, idempotency controls, and synchronous conversion.
2. **NPZ upload and NPZ-to-DICOM conversion:** NPZ gain and radiograph array
   validation, metadata parsing, enrichment, and DICOM serialization.
3. **Protected canonical DICOM converter integrity:** Exact SHA-256
   `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` at
   `mpips/conversion/tiff_json_to_dcm.py`.
4. **Accepted TRX behavior:** Clockwise orientation, threshold bypass, and canonical
   hash `5b9af36adc670ed1d93d650179d60b9cb2688cc53fa21f64fb4049de33e88d56`.
5. **BED threshold behavior:** Configured threshold semantics preserved.
6. **ImageJ/Fiji fidelity decisions:** Preserved per prior accepted closures.
7. **Calibration policy and defaults:** Fixed-canvas default preserved; expanded-canvas
   opt-in; unapproved numeric thresholds remain unadopted.
8. **Package boundaries and public behavior:** Clean architecture boundaries,
   supported import paths, and unrelated `main` hotfixes preserved.

Decisions must not be reopened merely to simplify integration.

## Integration strategy boundary

- Synchronization must be non-destructive and non-history-rewriting.
- An ordinary merge of `origin/main` into the feature branch (`git merge origin/main`)
  is the preferred and authorized method, unless verified repository policy
  requires another non-rewriting method.
- Force-push, destructive reset (`git reset --hard`), published-history rewriting,
  deletion of unrelated work, and silent conflict resolution are strictly prohibited.
- Conflicts must be reviewed semantically rather than treating textual mergeability
  as sufficient evidence of safety.
- If conflict resolution requires a new product, clinical, data-integrity,
  architecture, security, or accepted behavior decision, execution MUST stop and
  return to Planner/Reviewer.

## NPZ-to-DICOM acceptance obligations

Observed verification of the reconciled state must be performed and recorded,
including at minimum:

1. **Protected converter hash and path integrity:**
   - verify `tests/test_converter_protection.py` passes;
   - verify SHA-256 is `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`
     at `mpips/conversion/tiff_json_to_dcm.py`.
2. **Focused DICOM conversion test suite:**
   - `tests/api/test_dicom_conversion.py` passes.
3. **Pipeline workflow and imager tests:**
   - relevant NPZ validation, imager workflow, metadata, enrichment, clinical/temporal
     semantics, and TRX conversion tests present after reconciliation
     (`tests/test_imager_pipeline_workflow.py`, `tests/test_radiography_pipeline.py`,
     `tests/test_config_characterization.py`, `tests/test_geometry_processing.py`).
4. **Package boundary and import tests:**
   - import and boundary tests affected by the refactor
     (`tests/test_public_boundaries.py`, `tests/test_package_import.py`,
     `tests/test_processing_boundary.py`, `tests/api/test_api_surface.py`).
5. **Representative end-to-end conversion verification:**
   - execute representative successful NPZ radiograph + gain + manifest to valid
     DICOM conversion using repository-safe fixtures or synthetic data;
   - validate output is readable as DICOM (e.g. via `pydicom`);
   - validate pixel array invariants: expected pixel shape, bit depth (16-bit),
     `PixelRepresentation == 0`, preserved pixel data;
   - validate clinical/geometry semantics: clockwise TRX orientation where applicable,
     required patient/study/series identifiers, metadata invariants, and absence
     of unauthorized private tags.
6. **Configured repository quality checks:**
   - full pytest suite (`pytest -v`);
   - formatting check (`black --check mpips tests`);
   - linting (`flake8 mpips tests`);
   - type checking (`mypy mpips tests`);
   - dependency and lockfile consistency (`uv.lock` / `pyproject.toml`);
   - package build and install smoke checks where configured (`python -m build --wheel`).
7. **Remote CI checks:**
   - observe CI workflow execution results on GitHub after push to
     `origin/refactor/package-boundaries`.

**Privacy and Safety Boundary:** Real-patient data, production credentials,
production mutation, or externally supplied sensitive artifacts must not be
required, used, or persisted.

## Defect and readiness standard

- Do not promise absolute "bug-free" status.
- Define readiness as:
  1. No known in-scope regressions on the reconciled branch.
  2. All required focused and configured verification checks pass, except clearly
     evidenced pre-existing or environment-only limitations permitted by repository policy.
  3. Any failure affecting NPZ-to-DICOM, converter integrity, pixel semantics,
     orientation, metadata correctness, packaging/imports, security, or data
     integrity is a blocking defect that prohibits PR readiness.
  4. Failures may not be hidden through test removal, weakened assertions,
     skipped verification, or unjustified golden-value changes.

## PR boundary

After reconciliation and all required verification succeed, the following actions
are authorized:

1. Ordinary bounded commits on `refactor/package-boundaries` required for merge
   reconciliation and verified integration fixes.
2. Push / update of `refactor/package-boundaries` to `origin` without force.
3. Creation of exactly one pull request:
   - **Head:** `refactor/package-boundaries`
   - **Base:** `main`
   - **PR description:** must include the exact reconciled commit revision,
     summary of reconciled changes, conflict resolution details, verification
     commands and observed results, known limitations, and explicit NPZ-to-DICOM
     verification evidence.

**Strict PR boundaries (prohibitions):**
- Do not merge the pull request.
- Do not deploy or release.
- Do not mutate production or shared external infrastructure.
- Do not force-push.
- Do not write to unrelated issues or pull requests.
- Do not introduce unrelated refactoring or new product features.

## Importable-module successor boundary

Exposing NPZ-to-DICOM conversion through a supported Python import surface
(library interface) is a distinct, dependent delivery objective.

It is **not** part of this integration task.

The successor work must:
1. Wait until the integration PR is merged into `main` and the resulting `main`
   revision is established as the applicable baseline.
2. Use a new branch created from that then-current `main`.
3. Receive its own validated task before implementation begins.
4. Preserve the existing HTTP API rather than replace or disrupt it.

No design or implementation of that import API is authorized under this task.

## Dependencies and assumptions

### Dependencies

- Feature baseline `ccbb2a5707741903d5eaa75c72e789405d6e055f` and `main` baseline
  `f1ef9604e06f98119de73f6e4df1e5ea619ae278` remain resolvable.
- GitHub CLI (`gh`) or repository platform access is available for PR creation.
- Python 3.12 environment with declared dependencies is available for running tests.

### Approved assumptions

- Bounded synchronization and PR creation are explicitly authorized by the Human Request.
- Ordinary merge of `origin/main` into `refactor/package-boundaries` is the approved
  non-rewriting integration strategy.
- If `main` advances before execution, the Executor must re-evaluate drift; if
  conflicts or architectural assumptions change materially, return to Planner.

### Remaining approval requirements

- Planner/Reviewer review of execution outcome.
- Designated human/team review and approval of the pull request prior to merge.
- No merge, deployment, or release is authorized without separate approval.

## Required capabilities

- repository read and local write;
- Git history, branch inspection, and merge operations;
- local shell, test, static-check, and build execution;
- remote push to `origin/refactor/package-boundaries`;
- GitHub CLI / API for pull request creation;
- evidence capture without committing credentials or sensitive data.

## Execution constraints

- Preserve unrelated working-tree and branch state; do not reset, clean, stash,
  rebase, or cherry-pick.
- Ordinary merge only; no history rewriting or force-push.
- Use established repository checks and patterns; do not add unnecessary frameworks
  or dependencies.
- Treat observed implementation as evidence of current reality, not authority to
  change accepted behavior.
- Distinguish branch-quality failures, semantic conflicts, environment limitations,
  and pre-existing failures.
- Do not treat mergeability as proof of semantic safety.

## Acceptance criteria

- [ ] Baseline identities (`ccbb2a5707741903d5eaa75c72e789405d6e055f` and `f1ef9604e06f98119de73f6e4df1e5ea619ae278`) and merge base (`fec5695048acbc3ce95d0a658032ec3701b6e045`) are recorded and verified.
- [ ] `origin/main` is merged into `refactor/package-boundaries` non-destructively without history rewriting or force-push.
- [ ] Any integration conflicts are resolved semantically with recorded rationale and zero unmade architectural/clinical decisions.
- [ ] Protected canonical DICOM converter SHA-256 remains `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` at `mpips/conversion/tiff_json_to_dcm.py` (`tests/test_converter_protection.py` passes).
- [ ] NPZ-to-DICOM conversion passes all focused tests (`tests/api/test_dicom_conversion.py`) and representative synthetic/fixture end-to-end conversions.
- [ ] Output DICOM is validated: readable with `pydicom`, correct pixel array shape, 16-bit depth, orientation preserved, metadata invariants intact.
- [ ] TRX, BED, ImageJ/Fiji, calibration, and optimization invariants are preserved (`tests/test_config_characterization.py`, etc.).
- [ ] Package boundaries and public import surfaces pass verification (`tests/test_public_boundaries.py`, `tests/test_package_import.py`, `tests/api/test_api_surface.py`).
- [ ] Branch-wide quality gates pass: full pytest suite, Black, Flake8, mypy, and build checks (subject to documented pre-existing limitations).
- [ ] Reconciled branch is pushed to `origin/refactor/package-boundaries` without force.
- [ ] Exactly one pull request (head: `refactor/package-boundaries`, base: `main`) is created with complete verification evidence, limitations, and NPZ-to-DICOM proof.
- [ ] Pull request remains open for review; no merge, deployment, or release is performed.

## Verification requirements

### Required checks

- `git merge origin/main` cleanly resolved and committed;
- `pytest tests/test_converter_protection.py -v`;
- `pytest tests/api/test_dicom_conversion.py -v`;
- `pytest tests/test_imager_pipeline_workflow.py tests/test_radiography_pipeline.py -v`;
- `pytest tests/test_config_characterization.py -v`;
- `pytest tests/test_public_boundaries.py tests/test_package_import.py tests/api/test_api_surface.py -v`;
- Representative end-to-end NPZ-to-DICOM conversion execution and DICOM validation;
- `pytest -v` (full suite);
- `black --check mpips tests`;
- `flake8 mpips tests`;
- `mypy mpips tests`;
- `git push origin refactor/package-boundaries`;
- GitHub CI run observation;
- Pull request creation (`gh pr create`).

### Required evidence

The Executor must report:
- Pre-merge and post-merge commit SHAs;
- Merge conflict files, semantic analysis, and resolution details;
- Test execution outputs and pass/fail counts;
- Protected converter SHA verification;
- NPZ-to-DICOM validation evidence (dimensions, bit depth, tags);
- Static check outputs (Black, Flake8, mypy);
- Remote branch push confirmation;
- PR URL, number, head SHA, base SHA, and PR description summary;
- Known limitations and unverified items.

## Stop and escalation conditions

The Executor MUST stop and return to Planner/Reviewer if:

- actual ref drift on `main` or `refactor/package-boundaries` materially invalidates
  the task premises;
- synchronization requires history rewriting, rebase, or force-push;
- integration conflicts require an unmade product, clinical, data-integrity,
  architecture, or security decision;
- protected converter integrity or location deviates unexpectedly;
- NPZ-to-DICOM correctness cannot be verified or shows regressions;
- required checks reveal defects that cannot be boundedly corrected under this
  integration objective;
- repository policy requires additional approval;
- pre-existing or unrelated work cannot be safely preserved;
- remote push or PR creation fails due to missing permissions or branch protection blocks.

## Authorized side effects

After Planner accepts the immutable task revision, the Executor is authorized to:
- execute an ordinary merge of `origin/main` into `refactor/package-boundaries`;
- make ordinary bounded commits required for merge conflict resolution and verified fixes;
- push `refactor/package-boundaries` to `origin` without force;
- create exactly one integration pull request (head `refactor/package-boundaries` -> base `main`);
- execute non-destructive local checks and temporary test scripts using repository-safe fixtures.

**Prohibited side effects:**
- Merging the pull request into `main`.
- Force-pushing to any branch.
- Rebase, squash, or destructive Git reset.
- Modifying `main` directly.
- Deployment, release, or production mutation.
- Modifying production infrastructure or external services.
- Committing secrets or patient data.
- Unrelated feature changes or refactoring outside integration necessity.

## Expected terminal outcome

`PACKAGE BOUNDARIES INTEGRATION CANDIDATE — PLANNER REVIEW REQUIRED`

The Executor does not self-declare final acceptance or merge authorization.
