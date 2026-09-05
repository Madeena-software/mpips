---
title: MPIPS Hybrid Median Fidelity Remediation — I-4D-Hybrid
document_id: AGENT-TASK-MPIPS-I4D-HYBRID
version: 1.0
status: Validated/Published
language: en-US
scope:
  - production Hybrid Median ImageJ fidelity remediation
  - bounded implementation and verification
---

# Executable Task

## Task identity

**Task title:** MPIPS Hybrid Median Fidelity Remediation — I-4D-Hybrid
**Task path:** `.agents/tasks/hybrid-median-fidelity-remediation.md`
**Task contract state:** Validated/Published
**Delivery objective / Work Package / MVP:** I-4D-Hybrid — Hybrid Median fidelity remediation
**Owner / designated planning authority:** MPIPS Planner/Reviewer

## Delivery context

Accepted I-4A ImageJ/Fiji Fidelity Characterization established exact parity for
ContrastEnhancer stretch, weighted equalization, and classic equalization on
uint8/uint16. It established fidelity failures for Hybrid Median 3×3, 5×5,
and 7×7, CLAHE Flat/FastFlat, and Circular Median; Temporal Median is not
production-reachable. ContrastEnhancer remediation is therefore not required.

This task addresses only the Hybrid Median family. Current production uses
`median_filter_type = "hybrid_imagej"` and `median_filter_radius = 2`; the
wrapper maps radius 2 to a 5×5 kernel, making 5×5 parity acceptance-critical.
The exposed 3×3 and 7×7 variants are also in scope.

## Baseline and task revision

**Implementation baseline:** `6c5e7772c93e8b498b47bedcaa2b4261f42e9420`
**Task revision:** this stable task path at the immutable publication commit
created for this publication. The containing commit is the governing task
revision; it must be resolved before execution.

## Objective

Correct `ImageJReplicator.hybrid_median_filter_2d()` so observable grayscale
uint8/uint16 output exactly matches the pinned authoritative ImageJ Hybrid 2D
Median plugin for supported 3×3, 5×5, and 7×7 kernels, including boundary
semantics and repeated passes, while preserving public MPIPS interfaces,
runtime configuration, unrelated processing, and repository boundaries.

This is a production fidelity correction, not image-quality tuning.

## Authoritative inputs

- `.agents/evidence/imagej-fidelity-characterization.md`
- `.agents/evidence/imagej-fidelity-characterization.json`
- `scripts/imagej_fidelity_characterization.py`
- `scripts/imagej_reference/ReferenceHarness.java`
- `scripts/imagej_reference/README.md`
- `mpips/processing/imagej.py`
- `mpips/processing/filtering.py`
- `mpips/processing/radiography.py`
- `mpips/pipelines/config.py`
- `tests/test_imagej_migration.py`

The parity oracle is the executable authoritative behavior already pinned by
I-4A: Christopher Philip Mauer, `Hybrid_2D_Median_Filter.java`. Use its pinned
retrieval and SHA256 from `scripts/imagej_reference/README.md` and the accepted
evidence. The implementation must independently reproduce observable behavior
in Python; do not copy substantial Java, mechanically translate it, vendor the
source or binary, weaken third-party notices, or make a new broad licensing
conclusion. Preserve the existing licensing caution around this source.

## Accepted defect evidence

I-4A records fidelity failure for each of 3×3, 5×5, and 7×7, with boundary
and interior mismatches. Aggregate findings are:

| Kernel | Edge mismatches | Interior mismatches |
|---|---:|---:|
| 3×3 | 38 | 62 |
| 5×5 | 44 | 48 |
| 7×7 | 38 | 48 |

The 5×5 case is the current production-default family, and repeated-pass
behavior was exercised. Fixing only padding/boundaries is insufficient unless
executable reference tests also prove interior parity.

## Scope

### In scope

- `mpips/processing/imagej.py`, specifically `ImageJReplicator.hybrid_median_filter_2d()`.
- Small private helpers in that module only when they clarify authoritative
  semantics and are independently testable.
- Focused deterministic Hybrid Median fidelity tests and the minimum required
  migration/reference/evidence updates.
- Reuse of the retained verified reference environment
  `/tmp/mpips-imagej-reference-LyDbYJ` when present and valid, following the
  tracked reference README.

### Out of scope

- CLAHE, Circular Median, ContrastEnhancer, threshold, inversion, wavelet,
  calibration, cropping/rotation, DICOM conversion, workers, DAG/workflow,
  deployment, real-radiograph ablation, new defaults, active median type or
  default radius changes.
- API changes, broad `ImageJReplicator` refactoring, RGB fidelity work unless
  required to prevent regression of the existing channel-wise contract, and
  performance optimization beyond the required correctness sanity check.
- Combining this task with another fidelity family.

### Preserved behavior

- `ImageJReplicator.hybrid_median_filter_2d(image, kernel_size=..., repetitions=...)`.
- Kernel sizes 3, 5, and 7.
- `apply_median_filter(..., filter_type="hybrid_imagej", radius=...)`.
- `median_filter_type="hybrid_imagej"` and `median_filter_radius=2` defaults;
  radius 2 remains the 5×5 production path.
- input must remain a NumPy ndarray; empty arrays remain invalid; supported
  kernel sizes remain only 3, 5, and 7; and repetitions below 1 retain current
  behavior unless authoritative evidence proves a bounded conflict.
- dtype, shape, and existing channel-wise multi-channel behavior.
- Unrelated processing behavior, repository package boundaries, and existing
  licensing notices.

## Required behavior constraints

Derive exact behavior from the executable I-4A reference, pinned source, and
deterministic cases; do not assume NumPy, SciPy, or OpenCV padding is equivalent.
The correction and tests must cover:

- PLUS-neighborhood statistic, X-neighborhood statistic, center participation,
  and final median-of-three;
- 3×3, 5×5, and 7×7;
- top, bottom, left, and right boundaries, all corners, and genuine interiors;
- repeated passes, including `repetitions=2` for production-default 5×5.

## Test-driven execution contract

1. Add or isolate deterministic tests invoking current MPIPS and comparing exact
   authoritative outputs/reference outputs.
2. Run them on baseline `6c5e7772c93e8b498b47bedcaa2b4261f42e9420` and preserve
   evidence that they fail for the known defect.
3. Implement the minimum production correction.
4. Rerun the same tests and preserve evidence that they pass.

Fixtures must be human-auditable and include asymmetric values exposing PLUS,
X, center selection, every boundary class, corners, genuine interior behavior,
and repeated passes. Cover both uint8 and uint16 for every kernel. At least one
7×7 fixture must have an interior region larger than radius 3. The existing
retained characterization/reference tooling may be minimally extended only as
needed to verify this remediation.

The historical Hybrid Median expected output in
`tests/test_imagej_migration.py` may be updated only when traceable to
authoritative output. Do not change ContrastEnhancer arrays, CLAHE hashes, or
unrelated migration expectations to make the suite green.

The implementation must not add a Java runtime dependency to production. Do
not use a system Java installation, `sudo`, an OS package manager, dependency
changes, a new JDK download, or any new unapproved third-party executable or
runtime download. The retained reference workspace
`/tmp/mpips-imagej-reference-LyDbYJ` may be reused only after verifying that it
remains present and consistent with accepted I-4A provenance. Already-retained
pinned artifacts may be rebuilt locally according to the tracked README only
without a new download or permission expansion.

If the retained workspace is unavailable or unusable and authoritative
reference execution would require a new JDK/JRE, replacement executable
artifacts beyond existing authority, system installation, dependency
modification, or permission expansion, stop: **PLANNING REQUIRED**.

## Acceptance criteria

- [ ] Exact array equality, with `mismatch_count == 0`, is demonstrated for
  authoritative deterministic cases for uint8 and uint16 at 3×3, 5×5, and 7×7.
- [ ] Required PLUS, X, center, boundary, corner, genuine-interior, asymmetric,
  and repeated-pass cases all have zero mismatches; 5×5 includes repetitions=2.
- [ ] The production wrapper path `filter_type="hybrid_imagej", radius=2`
  produces the authoritative 5×5 output.
- [ ] Public callable/config contracts, dtype, shape, channel-wise behavior,
  defaults, and unrelated processing remain preserved.
- [ ] No CLAHE, Circular Median, ContrastEnhancer, or other out-of-scope
  remediation is introduced.
- [ ] The implementation is independently written Python and retains existing
  licensing caution; no upstream Java/source/binary is vendored.

No tolerance, SSIM, PSNR, correlation, or visual inspection substitutes for
exact deterministic equality.

## Verification requirements

### Required checks

- Baseline red/green focused fidelity tests as specified above.
- Post-fix authoritative exact parity for 3×3 uint8, 3×3 uint16, 5×5 uint8,
  5×5 uint16, 7×7 uint8, and 7×7 uint16; boundary and genuine interior parity;
  repetitions=2 parity; and the production wrapper
  `filter_type="hybrid_imagej", radius=2`.
- `tests/test_imagej_migration.py`, relevant processing/filtering tests, and
  `tests/test_converter_protection.py`.
- Black, Flake8, mypy, and full pytest when practical, using repository
  commands and reporting actual results.
- SHA256 verification of the protected converter
  `mpips/conversion/tiff_json_to_dcm.py`:
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- A lightweight performance sanity check on a representative moderate
  grayscale array after correctness is achieved. Record basic elapsed time
  before/after when practical; no strict speed threshold applies and a modest
  slowdown for faithful semantics is acceptable.
- Reference harness/tooling checks when modified.

### Required evidence

Report the exact implementation revision or working-tree state, commands and
observed output, tests added/changed, per-case mismatch results, baseline red
evidence, green evidence, deviations, gaps, and blockers. Do not represent
unobserved local checks as CI or acceptance. If full pytest times out, report
the exact command, timeout duration, last test observed, and whether any
failure was observed before timeout; never report a timeout as pass. Report
GitHub Actions separately only when an actual run exists. The protected
converter must remain unchanged.

## Dependencies and approvals

### Dependencies

- Accepted I-4A evidence revision and pinned Hybrid Median reference identity.
- Baseline and branch state remain safely applicable; reference environment may
  be reused only after validity is checked.

### Remaining approval requirements

- None beyond Planner/Reviewer implementation review and acceptance. Release,
  deployment, publication outside this task, and production mutation remain
  separate gates.

## Required capabilities

- Repository read/write and local command execution.
- Python test execution.
- Access to the retained reference environment or tracked reconstruction path.

## Stop conditions

Stop and return to planning if the baseline, pinned reference identity, or
authoritative executable behavior cannot be established; if required authority
is contradictory; if implementation requires changed public/config contracts,
new defaults, broad refactoring, dependency/licensing decisions, or any
out-of-scope change; or if exact parity cannot be achieved within this bounded
objective. Do not silently reinterpret the task.

## Side-effect authorization

Implementation is bounded to the scope above. The future Executor is explicitly
authorized to:

- modify only the bounded Hybrid Median implementation, test, and evidence
  surfaces;
- create normal implementation/evidence commit(s) on
  `refactor/package-boundaries`; and
- push normally to `origin/refactor/package-boundaries`.

The Executor must stop after push at **Review Required** and return immutable
implementation revision(s). The Executor is not authorized to force-push,
modify `main`, rewrite history, mutate tags, delete branches, create a pull
request unless separately authorized, deploy, or release. Dependency changes,
system installation, permission expansion, production/external-system
mutation, destructive operations, secret access, and unrelated repository
changes remain prohibited.

## Expected terminal outcome

The Executor returns **Review Required** with a reviewable implementation state
and truthful evidence, or **Planning Required** with the blocking evidence.
When implementation succeeds within scope, the Executor must audit the final
diff, create normal commit(s), push normally, verify local `HEAD ==
origin/refactor/package-boundaries` and a clean worktree, return the exact
implementation/evidence SHA(s), and stop at **Review Required**. The Executor
does not self-declare acceptance.
