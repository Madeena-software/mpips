---
title: MPIPS Structural Preservation IQA Foundation
document_id: AGENT-TASK-MPIPS-IQA-STRUCTURAL-SAFETY-001
version: 1.1
status: Remediation Required
language: en-US
scope:
  - pure reference-based structural-preservation image-quality measurements
  - synthetic characterization fixtures and tests
  - truthful documentation of the existing BRISQUE-compatible metric
authority_note: This task authorizes only the bounded measurement foundation described below. It does not authorize production safety policy, radiography-pipeline changes, release, or deployment.
---

# Task: Add Structural Preservation IQA Measurements

## Task identity

**Task title:** MPIPS structural preservation IQA foundation  
**Task path:** `.agents/tasks/iqa-structural-safety.md`  
**Task contract state:** Validated/Published  
**Delivery objective / Work Package / MVP:** IQA Hardening — reference-based structural safety measurement foundation  
**Owner / designated planning authority:** Planner/Reviewer-approved repository delivery

This stable task path is the governing delivery contract. Its immutable task
revision is the full Git commit SHA containing this publication. Execution and
review MUST identify the task as:

`.agents/tasks/iqa-structural-safety.md @ <full publication commit SHA>`

## Delivery context

MPIPS needs trustworthy reference-based measurements to characterize whether
radiography processing preserves visible anatomy. The measurements are a pure
IQA capability only; they are not yet a production acceptance or rejection
policy and MUST NOT alter the existing radiography algorithm.

## Baseline and task revision

**Implementation baseline:** `4290a57f0fabd5c0f8a3b28e734d1aca17fead4a`  
**Task revision:** the full Git commit SHA containing this task publication

The implementation baseline and governing task revision are separate. The
Executor MUST stop if the baseline or governing task identity cannot be
resolved exactly before implementation begins.

## Objective

Create a pure, deterministic, mask-aware structural-preservation IQA API for
same-geometry grayscale NumPy arrays, expose it through the existing lazy
`mpips.iqa` boundary, characterize it with synthetic fixtures, and accurately
document the existing `calculate_brisque` implementation as an MSCN-based
proxy while preserving its public compatibility.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Planner/Reviewer-approved Phase 1 design in the governing user request

### Requirement traceability

- Structural-preservation measurements → approved IQA Hardening objective
- Pure package boundary and compatibility → repository architecture and
  existing `mpips.iqa` lazy-import convention
- No processing or release behavior change → approved task exclusions below

## Scope

### In scope

- Add a focused pure module at `mpips/iqa/safety.py`.
- Provide a deterministic typed ndarray result for structural-preservation
  analysis, including complementary measurements for:
  - reference-edge recall with bounded spatial tolerance;
  - gradient-energy retention;
  - bounded local/tile structure retention;
  - informative-region extreme clipping / near-flat loss; and
  - optional gradient-domain SSIM support only if it uses the already-present
    dependency closure without materially complicating the implementation.
- Require same-shape, grayscale 2D, finite-compatible inputs and finite output
  values; support uint16 and normalized floating-point inputs.
- Support an optional same-shape `valid_mask`; excluded pixels MUST NOT affect
  scores, invalid mask shapes MUST fail clearly, and an all-false mask MUST NOT
  report a perfect result.
- Export the new public helper(s) through `mpips.iqa` using the established
  lazy-import convention.
- Add synthetic characterization covering identity, brightness/contrast,
  inversion, benign smoothing, localized appendage deletion, large structural
  deletion, valid-mask padding, blank images, and near-blank images.
- Preserve existing IQA metrics and compatibility while documenting that
  `calculate_brisque` is an MSCN-based handcrafted proxy rather than the
  complete published BRISQUE model.

### Out of scope

- Any change to `RadiographyPipeline` processing behavior or output.
- Any change to thresholding, inversion, contrast, CLAHE, median filtering,
  denoising, FFC, calibration, crop, rotation, or normalization defaults.
- DAG schema changes, new DAG safety nodes, workflow integration, API/service
  integration, or production rejection behavior.
- Arbitrary PASS/WARN/FAIL thresholds or safety acceptance policy.
- Google Drive access, vendored TIFF fixtures, or external reference datasets.
- New dependencies, frameworks, model files, heavyweight IQA models, or the
  `metric-analyze` repository/package as a dependency.
- Docker, CI, deployment, worker, API, release, or production changes.
- Changes to `mpips/conversion/tiff_json_to_dcm.py` or its protected bytes.
- Any commit other than this task-publication commit in Phase 1.

### Preserved behavior

- Existing `mpips.iqa` public names, lazy loading, numerical contracts, and
  callers remain compatible.
- Existing DAG IQA nodes and schemas remain unchanged.
- `RadiographyPipeline` remains byte-for-byte behaviorally unchanged.
- The protected converter remains byte-identical to its recorded SHA-256:
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- No production output, threshold, deployment, or external system changes are
  authorized.

## Dependencies and assumptions

### Dependencies

- The Executor must use the existing NumPy/OpenCV/scikit-image dependency
  closure where appropriate; dependency metadata and lockfiles are not in
  scope for modification.
- The implementation must remain independent of workflows, pipelines, DAG
  engines, APIs, services, and file I/O.
- Phase 1 publication must be reviewed and authorized externally before Phase
  2 implementation begins.

### Approved assumptions

- `mpips.iqa.metrics` is the current canonical implementation for existing IQA
  helpers.
- `calculate_brisque` currently implements an MSCN-based proxy and must not be
  silently represented as validated published BRISQUE.
- `RadiographyPipeline` contains the future same-geometry pre-threshold
  reference point, but integration is deliberately deferred.

### Remaining approval requirements

- External Planner/Reviewer MUST verify this exact immutable task revision and
  explicitly authorize Phase 2 execution.
- No deployment, release, push, or external-system mutation is authorized by
  this task publication.

## Required capabilities

- repository read/write and local Git
- local test execution and static checks
- Codebase Memory MCP for implementation-impact verification

## Execution constraints

### Constraints

- Implement only the pure measurement foundation and its characterization.
- Use the smallest coherent implementation and existing repository patterns.
- Do not invent production safety thresholds; report measurements only.
- Do not add file I/O, workflow imports, pipeline imports, engine imports, API
  dependencies, or service dependencies to the pure module.
- Validate trust-boundary inputs and defensive blank/near-blank cases without
  producing NaN, infinity, or a false perfect-safety result.
- Do not modify this task file during execution. A materially changed contract
  requires republishing this stable path at a new immutable revision.

## Acceptance criteria

- [ ] `mpips/iqa/safety.py` provides a pure typed ndarray result and structural
      measurements for reference/candidate pairs with same-shape 2D inputs.
- [ ] Identity, retained structure under brightness/contrast and inversion,
      and benign smoothing characterize as preserved by the complementary
      measurements without relying on arbitrary production thresholds.
- [ ] Localized appendage deletion degrades the local/tile measurement while
      retaining the main body, and large structural deletion degrades global
      and local measurements.
- [ ] A substantially weaker connected appendage or other low-contrast,
      spatially coherent structure is characterized; deleting it measurably
      degrades at least one localized structural-preservation measurement.
- [ ] The measurement foundation does not define an informative region solely
      through a global relative-to-maximum cutoff that can systematically
      exclude faint coherent anatomy.
- [ ] Valid-mask padding is excluded from all structural scores; invalid and
      all-false masks fail safely and clearly.
- [ ] Blank and near-blank inputs return finite, explicit non-perfect-safe
      measurements rather than NaN, infinity, or silent perfect scores.
- [ ] New helper(s) are exposed through `mpips.iqa` lazily, without changing
      existing public names or DAG schemas.
- [ ] Existing `calculate_brisque` compatibility remains intact and its proxy
      semantics are documented accurately.
- [ ] RadiographyPipeline behavior, thresholds, defaults, protected converter,
      dependency metadata, Docker, CI, deployment, API, and worker files are
      unchanged.

## Remediation

**Review basis:** `1037fd28444f77d34b5c8b4a8f876e7ba7cf216a`

This is bounded remediation within the original structural-preservation IQA
objective. The prior implementation can ignore weak but spatially coherent
structures when informative selection is based only on a global relative-to-
maximum cutoff.

### Required corrections

- Add characterization for a substantially weaker connected appendage or
  low-contrast coherent structure, and show that deleting it measurably
  degrades at least one localized structural-preservation measurement.
- Revise the measurement foundation so informative selection is not defined
  solely by a global relative-to-maximum cutoff that can systematically exclude
  faint coherent anatomy. The implementation mechanism remains Executor
  technical discretion.
- Preserve robustness against blank and near-blank images, noise,
  brightness/contrast transforms, inversion, benign smoothing, and valid-mask
  padding.
- Do not introduce arbitrary production PASS/WARN/FAIL thresholds.

### Additional verification

- The weak-structure characterization must fail if deleting the weak connected
  structure does not measurably degrade a localized structural-preservation
  measurement.
- Verify that the weak-structure result and existing robustness
  characterizations remain finite, mask-aware, and compatible with the
  existing public IQA boundary.

### Remediation exclusions

- Do not broaden scope into pipeline integration, threshold changes, CLAHE
  changes, ImageJ hardening, `metric-analyze` integration, or new dependencies.
- Do not modify this task during remediation execution; any further material
  contract change requires another republished revision of this stable path.

## Verification requirements

### Required checks

- Run focused structural IQA characterization tests first.
- Run existing focused IQA ownership/public-boundary tests.
- Run relevant DAG and radiography-pipeline regression tests.
- Run Black, flake8, and mypy for the affected scope.
- Run the full pytest suite when practical and report any limitation.
- Verify the protected converter SHA-256 is unchanged.
- Inspect `git diff` and `git status` to prove excluded files and dependency
  metadata were not modified.

### Required evidence

The Executor MUST report the exact task revision, implementation revision or
working-tree state, changed files, Codebase Memory evidence, characterization
results for every required fixture, commands executed, observed outcomes,
verification gaps, and any material deviation.

## Stop conditions

The Executor MUST stop and return to Planner/Reviewer when:

- the exact task publication SHA or implementation baseline is unavailable;
- a requirement, architecture, dependency, or safety decision is missing or
  contradictory;
- implementation requires changing the radiography pipeline, DAG schema,
  dependency set, production policy, or any excluded file;
- arbitrary safety thresholds become necessary to satisfy acceptance;
- the existing public IQA compatibility cannot be preserved without a new
  authority decision;
- a security, privacy, data-integrity, clinical-safety, or operational risk
  requires scope or approval beyond this task; or
- unrelated working-tree changes overlap the authorized write surface.

## Expected terminal outcomes

- **Review Required:** the bounded implementation and required evidence exist
  and are ready for Planner/Reviewer assessment.
- **Planning Required:** a stop condition, missing authority, or invalid
  precondition prevents a reviewable implementation.

This task does not authorize acceptance, release, deployment, or production
execution.
