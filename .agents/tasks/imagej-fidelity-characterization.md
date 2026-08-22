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

## Dependencies and assumptions

### Dependencies

- The accepted baseline and a clean branch state before execution.
- Existing compatible Java/reference tooling, or an unprivileged temporary
  runtime that does not require system installation.
- Public authoritative upstream sources/artifacts and network access when
  required.
- Existing MPIPS test and processing environment.

### Approved assumptions

- Grayscale `uint8`/`uint16` radiography is the primary acceptance scope.
- Existing MPIPS output-locking tests are migration evidence, not proof of
  ImageJ/Fiji parity.
- Temporary official source/JAR downloads may be used only for characterization
  and must not be committed or become runtime dependencies.

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

## Acceptance criteria

- [ ] A reproducible provenance record exists for every authoritative reference
      actually used, including exact revision/version, retrieval reference, and
      hashes where practical.
- [ ] Each in-scope operation has a classification from the allowed set and
      evidence sufficient to reproduce the comparison.
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
- [ ] Findings are diagnostic only; any later remediation or ablation is
      identified as separately planned work.

## Verification requirements

### Required checks

- Verify branch, baseline ancestry, and clean starting state before execution.
- Run the characterization harness/tests and record exact commands and results.
- Verify reference provenance and hashes against the downloaded temporary
  artifacts where applicable.
- Verify the final diff contains only authorized characterization artifacts.
- Run relevant focused tests and available repository quality checks without
  changing production dependencies.
- Recompute the protected converter SHA256.

### Required evidence

The Executor MUST report the governing task revision, implementation baseline,
implementation revision, exact commands, observed results, fixture and
parameter inventory, reference provenance, per-operation classifications,
generated artifact paths, known gaps, deviations, and any stop condition.

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

It does not authorize production changes, dependency changes, sudo/system-wide
installs, deployment, main modification, history rewrite, force-push, tag
manipulation, external dataset mutation, secret access, or unrelated changes.

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

