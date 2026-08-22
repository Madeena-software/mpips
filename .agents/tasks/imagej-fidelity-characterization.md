---
title: MPIPS ImageJ/Fiji Fidelity Characterization — I-4A
status: Validated/Published
---

# Executable Task

## Task identity

**Task title:** MPIPS ImageJ/Fiji Fidelity Characterization — I-4A

**Task path:** `.agents/tasks/imagej-fidelity-characterization.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** I-4A — ImageJ/Fiji Fidelity
Characterization, diagnostic prerequisite for later ImageJ fidelity remediation
and Threshold × CLAHE ablation.

**Owner / designated planning authority:** Repository Planner / designated
delivery authority.

## Delivery context

The accepted real-radiograph characterization found substantial structural
degradation in the legacy processing pipeline, but did not establish whether
thresholding, CLAHE, median filtering, or another ImageJ-style stage caused it.
This task establishes reproducible implementation fidelity evidence before any
later tuning or remediation.

This is characterization only. A mismatch is a valid result and MUST NOT be
fixed by this task.

## Baseline and task revision

**Implementation baseline:**
`dd13fc4dab512bbb59242bde7f5fb7cc6c5c370e`

**Task revision:** `.agents/tasks/imagej-fidelity-characterization.md @ the
immutable publication commit containing this file`.

The Planner publication report supplies the full publication SHA before
Executor handoff. The task revision and implementation baseline are separate.

## Objective

Build an evidence-backed characterization of the current
`ImageJReplicator` implementation against authoritative executable ImageJ/Fiji
behavior, answering per supported operation whether MPIPS reproduces the
reference.

Allowed classifications are:

- `PARITY CONFIRMED`
- `BOUNDED DEVIATION`
- `FIDELITY FAILURE`
- `NOT APPLICABLE`
- `NOT PRODUCTION-REACHABLE`
- `REFERENCE NOT RESOLVED`

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Accepted implementation baseline `dd13fc4dab512bbb59242bde7f5fb7cc6c5c370e`
- Roadmap objective I-4A and the approved publication directive for this task.

### Requirement traceability

- I-4A ImageJ/Fiji fidelity characterization → this task, the repository
  delivery contract, and the accepted baseline.
- Production-relevant call-surface analysis → `mpips/processing/imagej.py`,
  `mpips/processing/radiography.py`, `mpips/processing/filtering.py`,
  `mpips/processing/__init__.py`, and `tests/test_imagej_migration.py`.

### Required upstream references

Pin the exact source revision/version used for every reference execution.
Prefer upstream source repositories, official ImageJ source, official
Fiji/SciJava artifacts, and official plugin source. Do not use MPIPS comments or
random blog implementations as reference truth.

At minimum investigate:

1. ImageJ core `ij.plugin.ContrastEnhancer`, source
   `ij/plugin/ContrastEnhancer.java`, from `imagej/ImageJ`.
2. ImageJ core `ij.plugin.filter.RankFilters`, operation `MEDIAN`, from
   `imagej/ImageJ`, including circular-kernel construction and radius
   semantics.
3. Fiji CLAHE `mpicbg.ij.clahe.Flat`, `FastFlat`, and `Util`, resolving the
   authoritative repository and exact revision/version actually executed.
4. Official `Hybrid_2D_Median_Filter.java` by Christopher Philip Mauer,
   including its 3x3, 5x5, and 7x7 forms and edge behavior.
5. The authoritative source, if identifiable, for temporal median; also inspect
   whether MPIPS temporal median is production-reachable.

For each upstream implementation used, record project/repository, source
file/class, exact Git SHA where available, released artifact version where
applicable, retrieval URL/reference, and SHA256 of downloaded source/JAR where
practical. Record material source/artifact differences explicitly.

## Scope

### In scope

- Create lightweight deterministic characterization scripts, tests, fixtures,
  and Markdown/JSON/CSV evidence as necessary.
- Produce the mandatory evidence files
  `.agents/evidence/imagej-fidelity-characterization.md` and
  `.agents/evidence/imagej-fidelity-characterization.json`.
- Create a reusable deterministic characterization harness under an existing
  repository tooling location, preferably `scripts/`, plus only small textual
  fixtures/reference outputs required by that harness.
- Execute authoritative Java ImageJ/Fiji behavior wherever practical in a
  temporary isolated reference workspace and compare MPIPS results.
- Characterize grayscale radiography behavior for `uint8` and `uint16`.
- Perform reachability analysis for temporal median and RGB/composite behavior.
- Report per-operation classification, exact provenance, fixture identity,
  parameters, output values or hashes, dtype, shape, clipping, and known gaps.

The required operation matrix is:

#### A. ContrastEnhancer histogram stretch

Cover `uint8` and `uint16`; constant, two-level, ramp, sparse-histogram,
narrow-range, full-range, impulse/outlier, and asymmetric-tail fixtures;
saturation `0.0`, ImageJ default `0.35`, runtime-relevant `5.0` where
applicable, and boundary cases. Compare selected histogram bins, rounding or
truncation, output, dtype, shape, and clipping. Explicitly check MPIPS uint16
histogram/statistics semantics against ImageJ `ShortProcessor` behavior.

#### B. ContrastEnhancer equalization

Cover weighted/sqrt and classic equalization for `uint8` and `uint16`.
Investigate weighted values, cumulative integration, Java `Math.round` versus
Python rounding, endpoints, empty/sparse bins, dtype, and range.

#### C. Fiji CLAHE `Flat`

Cover supported `uint8` and `uint16`, including current radiography usage and
runtime-relevant `blocksize=127`, `histogram_bins=256`, `maximum_slope=0.6`,
`fast=False`, and `composite=True` where relevant. Check parameter mapping,
clipping, redistribution, interpolation, boundaries, scaling, masks,
composite behavior, and dtype conversion.

#### D. Fiji CLAHE `FastFlat`

Characterize separately from `Flat`; do not treat them as interchangeable. Use
a minimal deterministic subset when it is not production-relevant.

#### E. Hybrid 2D Median

Compare 3x3, 5x5, and 7x7 for `uint8` and `uint16`, exposing center, PLUS, X,
repeated-pass, edge, and corner behavior. Verify the authoritative unusual
semantics (top/bottom reflected outward and side edges wrapped) rather than
assuming SciPy padding behavior.

#### F. Circular ImageJ Median

Compare `ImageJReplicator.median_filter_imagej` with ImageJ `RankFilters`
`MEDIAN` for runtime-relevant integer radii and boundary cases, covering
circular membership, `makeLineRadii`, edges, median selection, uint8/uint16,
small images, and special radius handling. Do not substitute an OpenCV or
scikit-image disk approximation.

#### G. Temporal median

First inspect public wrappers, pipeline callers, tests, and production
configuration exposure. If reachable, characterize against its authoritative
source. If unreachable, classify `NOT PRODUCTION-REACHABLE`; if reachable but
no legitimate reference can be identified, classify `REFERENCE NOT RESOLVED`.

RGB/composite behavior is secondary. Inspect reachability, do not claim RGB
parity from grayscale evidence, and avoid excessive unrelated work when it is
not production-reachable.

### Out of scope

- Any production behavior change, tuning, default change, or image-quality
  recommendation.
- Changes to `ImageJReplicator`, ContrastEnhancer, CLAHE, hybrid/circular/
  temporal median, thresholding, wavelet denoise, inversion, calibration,
  contrast defaults, pipeline defaults, DAG/API/workers, or DICOM conversion.
- Threshold × CLAHE ablation or later ImageJ fidelity remediation.
- Java/Fiji dependencies in MPIPS runtime dependencies; changes to
  `pyproject.toml` or `uv.lock` merely for reference execution.
- Copying full third-party implementations into MPIPS or vendoring JARs.
- Large binary fixtures or generated TIFF/JPEG/PNG/DICOM/NPY/NPZ datasets.
- Licensing conclusions beyond the existing `THIRD_PARTY_NOTICES.md`.
- Repository-size regression, including third-party PDFs, JARs, TIFF datasets,
  generated image suites, or notebook output blobs.
- Deployment, release, main modification, history rewrite, force-push, tag
  manipulation, or external dataset mutation.

### Preserved behavior and boundaries

- MPIPS production algorithms, defaults, APIs, workers, dependencies, and
  DICOM behavior remain unchanged.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical with SHA256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Reference artifacts remain outside the tracked repository; no JAR or full
  third-party source is committed.
- Characterization evidence remains lightweight, deterministic, and human
  auditable.
- Large binary fixture artifacts MUST NOT be created or committed.

## Required evidence contract

The Markdown evidence MUST contain, at minimum:

1. exact upstream provenance;
2. production reachability;
3. fixture matrix;
4. parameter mapping;
5. per-case parity/deviation results;
6. boundary and rounding findings;
7. existing MPIPS test gaps;
8. per-operation final classifications;
9. an evidence-based ordering recommendation for later remediation families;
10. unresolved reference/licensing constraints.

The JSON evidence MUST contain machine-readable per-case measurements and
classifications. CSV MAY be emitted when useful, but Markdown and JSON are
mandatory.

### Exact comparison contract

For deterministic discrete integer ImageJ/Fiji operations, DEFAULT to exact
array equality. Do not weaken deterministic `uint8`/`uint16` operations to an
approximate tolerance merely to obtain a passing result.

A tolerance is permitted ONLY when exact equality is not a valid authoritative
contract, the reason is documented before evaluation, and an explicit numeric
tolerance is defined before examining the result. The comparison mode MUST be
recorded as `exact` or `tolerant`; tolerant cases MUST record the tolerance and
its rationale.

Every characterization case MUST record at minimum: operation, fixture
identifier, dtype, shape, authoritative project/version/commit, parameters,
comparison mode, tolerance and rationale when tolerant, equality/pass result,
mismatch pixel count, mismatch fraction, maximum absolute difference where
meaningful, first or representative differing coordinate/value where
meaningful, output/reference SHA256 where practical, and final classification.

For exact deterministic comparison, `mismatch_count == 0` is required for
`PARITY CONFIRMED`. Correlation, SSIM, PSNR, and visual similarity MUST NOT be
used as substitutes for exact algorithmic parity.

### Reusable harness contract

The harness MUST:

1. load deterministic fixture definitions;
2. execute current MPIPS `ImageJReplicator` behavior;
3. load authoritative reference outputs;
4. compare exact arrays where appropriate;
5. support explicitly justified tolerance only where valid;
6. compute mismatch count and fraction;
7. compute maximum absolute difference;
8. identify a representative or first mismatch;
9. verify shape and dtype; and
10. emit machine-readable results consumed by the evidence JSON.

This is implementation-fidelity tooling, not a clinical IQA metric.

## Baseline test preservation

`tests/test_imagej_migration.py` currently locks accepted MPIPS baseline
behavior. I-4A execution MUST NOT change its expected arrays or hashes merely
because authoritative ImageJ/Fiji output differs.

When an existing MPIPS baseline differs from the authoritative reference,
record `CURRENT MPIPS BASELINE != AUTHORITATIVE REFERENCE` and normally
classify the operation as `FIDELITY FAILURE`. Changing production behavior or
replacing accepted baseline expected values belongs to a later separately
governed fidelity-remediation task. New characterization tests MAY be added
separately.

## Required final classification table

The Markdown evidence MUST include an explicit final classification table with
at least these rows and only the allowed terminal values:

| Operation | Final classification |
|---|---|
| Contrast stretch uint8 | one allowed value |
| Contrast stretch uint16 | one allowed value |
| Equalize weighted uint8 | one allowed value |
| Equalize weighted uint16 | one allowed value |
| Equalize classic uint8 | one allowed value |
| Equalize classic uint16 | one allowed value |
| CLAHE Flat / precise | one allowed value |
| CLAHE FastFlat / fast | one allowed value |
| Hybrid Median 3x3 | one allowed value |
| Hybrid Median 5x5 | one allowed value |
| Hybrid Median 7x7 | one allowed value |
| Circular Median | one allowed value |
| Temporal Median | one allowed value |

Allowed values are `PARITY CONFIRMED`, `BOUNDED DEVIATION`, `FIDELITY
FAILURE`, `NOT APPLICABLE`, `NOT PRODUCTION-REACHABLE`, and `REFERENCE NOT
RESOLVED`. Do not introduce ad-hoc terminal classifications.

## Dependencies and assumptions

### Dependencies

- The accepted baseline and a clean branch state before execution.
- An already-installed compatible Java runtime, if authoritative executable
  reference generation requires Java.
- Public authoritative upstream sources/artifacts and network access when
  required.
- Existing MPIPS test and processing environment.

### Approved assumptions

- Grayscale `uint8`/`uint16` radiography is the primary acceptance scope.
- Existing MPIPS output-locking tests are migration evidence, not proof of
  ImageJ/Fiji parity.
- Temporary official source/JAR downloads may be used only for characterization
  and must not be committed or become runtime dependencies.
- Official version-pinned source/JAR artifacts MAY be downloaded temporarily
  outside Git. This does NOT authorize downloading or installing a JRE/JDK.

### Remaining approval requirements

- None for the bounded characterization and its normal commit/push to
  `refactor/package-boundaries`.
- Any privileged/system-wide install, MPIPS dependency change, licensing
  conclusion, production change, external mutation, or material scope change
  requires return to planning and fresh authorization.

## Required capabilities

- Repository read/write and local command execution.
- Test and static-check execution.
- Read-only network access to official upstream source/artifact locations.
- An already available compatible Java/reference runtime, if needed.

## Execution constraints

- Use exact pinned upstream provenance; never characterize floating “latest”.
- Prefer authoritative executable behavior over a manually translated Python
  equation compared with Python.
- A small Java harness invoking authoritative APIs is permitted.
- Use small deterministic numeric arrays, fixed seeds only when randomness is
  necessary, and targeted adversarial fixtures for borders, rounding,
  sparsity, clipping, dynamic range, geometry, and tiny images.
- Persist only lightweight inputs, expected arrays or hashes, output SHA256
  values, behavioral observations, and provenance.
- Reuse existing repository mechanisms before adding a helper. Do not introduce
  generic infrastructure.
- If a discrepancy is found, record it and do not fix it in this task.
- Do not install Java with `apt`, `sudo`, or any system-wide operation; do not
  silently download a user-local JRE/JDK; do not alter MPIPS dependencies to
  obtain Java. If no compatible Java runtime is already available and
  authoritative executable reference generation requires Java, STOP and return
  `PLANNING REQUIRED` for an explicit isolated-runtime decision.

## Acceptance criteria

- [ ] A reproducible provenance record exists for every authoritative reference
      actually used, including exact revision/version, retrieval reference, and
      hashes where practical.
- [ ] `.agents/evidence/imagej-fidelity-characterization.md` and
      `.agents/evidence/imagej-fidelity-characterization.json` exist, are
      deterministic, and satisfy the required evidence contract.
- [ ] A reusable deterministic harness and small textual fixtures/reference
      outputs exist under an appropriate existing tooling location, without
      large binary fixture artifacts.
- [ ] Each in-scope operation has a classification from the allowed set and
      evidence sufficient to reproduce the comparison.
- [ ] Every case records the required exact/tolerant comparison and mismatch
      measurements; exact deterministic parity requires zero mismatches.
- [ ] ContrastEnhancer stretch and equalization cover required uint8/uint16
      fixtures, parameters, and rounding/statistics questions.
- [ ] Flat and FastFlat CLAHE are characterized separately with required
      runtime-relevant parameter semantics.
- [ ] Hybrid 2D Median covers 3x3/5x5/7x7, both dtypes, and unusual edges;
      circular median covers ImageJ kernel/radius semantics and edges.
- [ ] Temporal median and RGB/composite reachability are explicitly recorded;
      no unsupported parity claim is made.
- [ ] Evidence is deterministic, lightweight, human-auditable, and excludes
      large binary datasets and vendored third-party artifacts.
- [ ] No production behavior, defaults, dependency, API, DICOM converter, or
      unrelated repository behavior changed.
- [ ] `tests/test_imagej_migration.py` expected arrays and hashes remain
      unchanged; any baseline/reference discrepancy is explicitly recorded.
- [ ] Findings are diagnostic only; any later remediation or ablation is
      identified as separately planned work.

## Verification requirements

### Required checks

- Verify branch, baseline ancestry, and clean starting state before execution.
- Run the characterization harness/tests and record exact commands and results.
- Verify reference provenance and hashes against the downloaded temporary
  artifacts where applicable.
- Verify the final diff contains only authorized characterization artifacts.
- Run `tests/test_imagej_migration.py`, relevant processing/filtering tests,
  `tests/test_converter_protection.py`, and the characterization harness/tests.
- Run Black, Flake8, mypy when practical, and the full pytest suite when
  practical. Local execution MUST NOT be called CI; report GitHub Actions
  separately only if it actually ran.
- Recompute the protected converter SHA256.

### Required evidence

The Executor MUST report the governing task revision, implementation baseline,
implementation revision, exact commands, observed results, fixture and
parameter inventory, reference provenance, per-operation classifications,
generated artifact paths, known gaps, deviations, and any stop condition.
The report MUST state whether each required check was run, skipped, or blocked;
skipped or terminated checks MUST NOT be reported as passed.

## Stop conditions

In addition to the standard task stop conditions, STOP and return
`PLANNING REQUIRED` if:

- authoritative provenance cannot be resolved for a primary
  production-relevant operation;
- reference execution requires privileged/system-wide installation;
- reference execution requires modifying MPIPS runtime dependencies;
- accurate characterization requires copying/licensing third-party code into
  MPIPS beyond lightweight reference evidence;
- a required production-relevant behavior cannot be isolated deterministically;
- repository state differs materially from the accepted baseline before
  execution; or
- unrelated work appears in the branch.

A fidelity mismatch is not a stop condition; it is a valid result. The Executor
MUST NOT silently substitute a Python approximation when authoritative execution
is required or reinterpret the task into remediation.

## Side-effect authorization

The task authorizes only bounded characterization work:

- create lightweight characterization scripts, tests, deterministic fixtures,
  and Markdown/JSON/CSV evidence;
- download official version-pinned source/JAR artifacts temporarily outside the
  repository;
- execute existing local Java tooling and repository checks;
- commit and push characterization-only changes to
  `refactor/package-boundaries`.

It does not authorize downloading or installing a JRE/JDK, production changes,
dependency changes, sudo/system-wide installs, deployment, main modification,
history rewrite, force-push, tag manipulation, external dataset mutation,
secret access, or unrelated changes.

## Expected terminal outcome

### Review Required

Use when the authorized characterization artifacts, exact immutable revision,
and truthful verification evidence are available for Planner/Reviewer
evaluation. After the normal characterization commit and push, stop and report
for review; the Executor does not self-accept the work.

### Planning Required

Use when any task stop condition prevents safe completion. Report the blocking
authority, dependency, environment, scope, or evidence issue and the repository
evidence supporting it.

## Review and remediation handling

Review against this exact task revision, the stated implementation baseline,
the implementation revision, and observed evidence. A fidelity failure is not a
remediation defect for this task. Any later fix, tuning, recommendation, or
ablation must be separately planned from the findings.
