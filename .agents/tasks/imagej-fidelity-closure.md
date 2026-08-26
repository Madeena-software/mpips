---
title: MPIPS ImageJ/Fiji Fidelity Closure
document_id: AGENT-TASK-IMAGEJ-FIDELITY-CLOSURE-001
version: 1.8
status: Validated/Published
language: en-US
last_updated: 2026-08-26
scope:
  - ImageJ/Fiji-derived and ImageJ/Fiji-inspired processing fidelity closure
  - bounded characterization, remediation, regression, and runtime measurement
authority_note: This is one stable umbrella task. Publication authorizes only the bounded phase currently released by Planner; later material phases require review and republishing of this same path with a new immutable task revision.
---

# Executable Task

## Task identity

**Task title:** MPIPS ImageJ/Fiji Fidelity Closure

**Task path:** `.agents/tasks/imagej-fidelity-closure.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Complete implementation-fidelity
closure for every ImageJ/Fiji-derived or ImageJ/Fiji-inspired MPIPS operation.

**Owner / designated planning authority:** Repository Planner / designated
delivery authority.

## Delivery context

This umbrella continues from the accepted ImageJ/Fiji characterization,
Hybrid Median remediation, and CLAHE contract evidence. It closes fidelity
questions against current production reachability without treating ImageJ/Fiji
as inherently superior, without requiring byte identity where a different
governed semantic contract is selected, and without calling the work clinical
safety validation.

The accepted I-5B Threshold × CLAHE interaction is CLOSED. Its accepted
decisions remain: Threshold value not supported; CLAHE value supported;
interaction signal present and stage-order follow-up justified. I-5B is not
reopened here, and no stage-order work is authorized.

## Baseline and task revision

**Implementation baseline:**
`232f148ce24d6df5569a4b2c290e93adf0a03d5f`

**Task revision:** `.agents/tasks/imagej-fidelity-closure.md @ the full
publication commit containing this file`.

The task revision and implementation baseline are separate. A later material
phase MUST republish this same task path at a new immutable revision before
execution.

**Current released phase:** **PHASE 6 — MINIMAL REFERENCE / REGRESSION SENTINEL SUITE**

**Phase-5 status:** **ACCEPTED / CLOSED** at
`a625deac10153a2c7c69a3523dd77751518b298e`.

Accepted Phase-5 controlled fixture: 1024x1024, uint16, SHA256
`70f5d243cbd130bdf30009f50711179d7e9d9f725dabef9c808be37a7c614858`.
All six measured tuples were deterministic. MPIPS precise/OpenCV at slopes
0.6 and 1.5 had accepted median warm in-process CLAHE times of
1.583727094 s, 0.005403822 s, 1.550276505 s, and 0.005421374 s,
respectively. Fiji Flat and FastFlat at slope 1.5 had accepted reference
harness end-to-end wall times of 2.095351675 s and 1.864892977 s. These timing
scopes remain distinct and are not a production decision.

**Accepted sub-gate:** **REFERENCE RUNTIME RECONSTRUCTION — ACCEPTED / CLOSED**

The accepted runtime is **RECONSTRUCTED FROM ACCEPTED PINNED PROVENANCE**
under governing publication
`e7e3669bcbf0c2e3242b2f44f6bd2b2ac0d422f8`, at
`/tmp/mpips-imagej-reference-phase5-iY6Lqk`. No tracked reconstruction files
or reconstruction commit exist. The reconstructed JDK, ImageJ JAR, pinned
Fiji CLAHE sources, Hybrid source, and tracked harness matched the identities
and hashes below; Fiji Flat and FastFlat each completed two deterministic
128x128 uint16 smoke runs at slope 1.5, block radius 63, and internal bins
255. Flat output SHA256 was
`b12db91a188b0dccdf2703dc3caa948bab24613e61256ef0002023d147daa34b` and
FastFlat output SHA256 was
`b4a4958976bd092c0bc12d4d02b52e80d693549a72ee9ec9a7916cbf319b8fda`.
The smoke result establishes runtime availability and determinism only; it is
not performance evidence.

**Accepted Phase-2 baseline:**
`b4c032ce58605095de82c67097c61ebf458041a5`

`fdf38094320de1dc81037e6516c17e11022d4fde` is the accepted direct
predecessor of the Phase-2 baseline. Phase 1, Phase 2, and Phase 3 are
accepted/closed. The Phase-4 radius-domain/reachability first gate is
accepted/closed at `84b4a8cd271fcf7b262bd625530a974357704f9b`. Phase 4
remediation is accepted/closed at
`232f148ce24d6df5569a4b2c290e93adf0a03d5f`. Phase 6 is released by this
publication; Phase 7 remains unauthorized.

**Accepted Phase-3 baseline:**
`8c7b479947ee2b67856fd644e95b6d9eede52739`

**Accepted Phase-1 evidence revision:**
`1be8ba791bc187be0c8b107cf165ac24f88ee412`

Phase 1 is accepted at that revision. Its conclusions are not reopened unless
direct contradictory repository evidence is found.

The prior Phase-1 publication authorized Phase 1 execution to:

- inspect repository source, configuration, and call paths;
- inspect accepted ImageJ/Fiji evidence;
- run read-only/local characterization commands needed to establish
  reachability;
- verify the protected converter hash; and
- create or update exactly `.agents/evidence/imagej-fidelity-closure.md`.

`.agents/evidence/imagej-fidelity-closure.md` is the stable evidence path for
this umbrella delivery line. Later phases MUST update it rather than
proliferate phase-specific evidence filenames unless Planner explicitly
authorizes otherwise.

Phase 1 evidence MAY record the operation name, ImageJ/Fiji reference
identity, MPIPS implementation symbol/path, production/config/API reachability,
default reachability, dtype behavior, accepted prior fidelity status, current
verified status, unresolved issue, and required later phase.

## Objective

Complete implementation-fidelity closure so every applicable operation has:

1. authoritative reference identity;
2. current production reachability;
3. a defined semantic contract;
4. known parity or divergence status;
5. explicitly governed intentional divergence where applicable;
6. no unresolved production-reachable fidelity failure at final acceptance;
7. deterministic regression protection appropriate to its status; and
8. bounded runtime characterization to inform later optimization, without
   optimizing production behavior in this task.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- `.agents/prompts/plan-create-task.md`
- `.agents/tasks/_template.md`
- Accepted baseline `8396fbc768285cc68ed3bbe572561cd664b70e8b`
- `.agents/tasks/imagej-fidelity-characterization.md`
- `.agents/evidence/imagej-fidelity-characterization.md` and companion JSON
- `.agents/tasks/hybrid-median-fidelity-remediation.md` and accepted evidence
- `.agents/tasks/clahe-parameter-contract-resolution.md`
- `.agents/evidence/clahe-parameter-contract-resolution.md` and companion JSON
- accepted I-5A CLAHE real-radiograph evidence
- accepted I-5B evidence and decisions

### Current observed implementation inputs

- `mpips/processing/imagej.py`
- `mpips/processing/filtering.py`
- `mpips/processing/radiography.py`
- `mpips/pipelines/radiography.py`
- `mpips/pipelines/config.py`
- `scripts/imagej_reference/README.md`
- `scripts/imagej_reference/ReferenceHarness.java`

Observed current reachability MUST be independently verified during Phase 1.
Current evidence indicates `RadiographyPipeline.process` reaches precise CLAHE
by default (`fast=False`, blocksize `127`, displayed bins `256`, internal bins
`255`, slope `0.6`) and reaches Hybrid Median by default. Circular Median is
configurable through the production median-filter path. Temporal Median has no
production caller in the accepted/current reachability analysis; this must be
rechecked rather than assumed.

### Requirement traceability

- ImageJ/Fiji fidelity closure → this task and accepted characterization.
- Current production reachability → current source/configuration and Phase 1
  closure matrix.
- CLAHE semantic selection → accepted CLAHE evidence and Phase 3 gate.
- No unresolved production-reachable fidelity failure → Phase 7 closure.

## Scope

### In scope

- One authoritative closure matrix for all ImageJ/Fiji-derived or inspired
  operations found by inventory.
- Closure of accepted parity and not-production-reachable items without
  reopening accepted work.
- Deliberate CLAHE semantic-contract selection among the three options below.
- Circular Median remediation or governed exclusion/deprecation based on
  verified reachability and authority.
- Bounded measurement of MPIPS precise CLAHE, MPIPS fast/OpenCV CLAHE, pinned
  Fiji Flat, and pinned Fiji FastFlat where executable with retained tooling.
- A small deterministic regression/sentinel suite and final closure evidence.

### Out of scope

- Threshold removal/change, stage-order optimization, CLAHE slope production
  change, generic pipeline ablation, final production configuration selection.
- Full 38-image confirmatory study, API cutover, DICOM contract migration,
  main promotion, deployment, release, or clinical safety validation.
- Production optimization during performance characterization.
- New JDK, dependency installation, vendored JARs, compiled classes, large
  reference binaries, or external source dumps.

### Preserved behavior and boundaries

- I-5B remains closed with its accepted decisions unchanged.
- No production/source/test/reference/evidence behavior changes are authorized
  by publication alone; each later implementation phase must be separately
  republished.
- `mpips/conversion/tiff_json_to_dcm.py` MUST remain byte-identical with SHA256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Existing pinned ImageJ/Fiji provenance and retained reference environment
  remain the source of truth; do not download or install a new JDK.

## Dependencies and assumptions

### Dependencies

- Review and republish of this same path between every material phase.
- Retained pinned environment documented in `scripts/imagej_reference/README.md`.
- Accepted evidence listed above.

### Approved assumptions

- Contrast Stretch uint8/uint16, weighted and classic Equalization, and the
  accepted Hybrid Median remediation are settled unless current regression
  evidence directly contradicts acceptance.
- Current MPIPS precise CLAHE is not Fiji Flat parity; MPIPS fast/OpenCV is not
  Fiji FastFlat parity.
- Fiji execution-safe slope floors are runtime facts, not image-quality
  recommendations.

### Remaining approval requirements

- Planner/Reviewer authorization is required before each material phase after
  the current published phase.
- CLAHE semantic selection requires approved authority. If unavailable, stop
  with `PLANNING REQUIRED — CLAHE SEMANTIC SELECTION`.
- Production behavior changes, dependency changes, release, deployment, and
  external-system actions require separate explicit authority.

## Required capabilities

- Repository read/write and local command execution.
- Existing test and reference-harness execution where available.
- Codebase/reachability inspection with direct-source verification.

## Execution constraints

- Use the smallest existing repository mechanisms; do not create parallel
  harnesses, frameworks, or dependency-heavy benchmark infrastructure.
- Do not optimize implementation in the performance phase.
- Exact equality is the default for deterministic integer reference behavior.
  Tolerances require a documented contract and predeclared rationale.
- Do not duplicate large prior reference matrices; link or summarize them.
- Every final operation classification must be one of: `PARITY CONFIRMED`,
  `INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED`,
  `NOT PRODUCTION REACHABLE — N/A`, `DEPRECATED / EXCLUDED — GOVERNED`, or
  `REMEDIATED AND PARITY CONFIRMED`.

## Gated phases

The prior publications released Phases 1 through 5. This revision releases
Phase 6 only. Each phase ends at `Review Required`; material
next-phase work requires Planner/Reviewer review and a new immutable revision
of this same task path.

### Phase 1 — Inventory / Reachability Closure

Verify every ImageJ-derived/inspired operation, reference source, MPIPS
implementation, caller/API/config surfaces, production default reachability,
dtype behavior, accepted status, and unresolved issue. Produce one closure
matrix in `.agents/evidence/imagej-fidelity-closure.md`. The matrix MUST cover
at minimum Contrast Stretch, Equalization weighted, Equalization classic,
Hybrid Median, CLAHE precise MPIPS, CLAHE fast/OpenCV, Fiji Flat reference,
Fiji FastFlat reference, Circular Median, Temporal Median, and any additional
ImageJ/Fiji-derived or inspired production operation discovered. Each item
MUST record: REFERENCE, MPIPS IMPLEMENTATION, PRODUCTION REACHABILITY,
DEFAULT REACHABILITY, DTYPE, PRIOR ACCEPTED STATUS, CURRENT VERIFIED STATUS,
UNRESOLVED GAP, and NEXT REQUIRED PHASE. No fidelity remediation is performed
in Phase 1.

Phase 1 is characterization/inventory only. It MUST NOT modify MPIPS
production code, configuration/defaults/schema, tests, ImageJ reference
harness/tooling, CLAHE semantic selection A/B/C, CLAHE slope, Circular Median
behavior, performance, stage order, thresholds, deployment, release, or main.
No new dependency or JDK installation is authorized. Read-only execution of
existing reference tooling is allowed only when needed for reachability
verification and permitted by the retained environment.

**Gate:** Review Required; publish the next revision before Phase 2.

### Phase 2 — Accepted Parity + N/A Closure (Accepted / Closed)

The prior Phase-2 publication released exactly the following
settled items:

- Contrast Stretch, uint8 and uint16;
- weighted ImageJ Equalization, uint8 and uint16;
- classic Equalization, uint8 and uint16;
- accepted Hybrid Median remediation, kernels 3x3, 5x5, and 7x7, preserving
  the accepted Java/plugin boundary semantics; and
- Temporal Median reachability refresh and evidence closure as
  `NOT PRODUCTION REACHABLE — N/A` if no production API, workflow, config,
  schema, or caller exists.

The Phase-2 Executor may inspect accepted evidence and current reachability,
run targeted local tests, minimally extend existing deterministic ImageJ
fidelity tests, update `.agents/evidence/imagej-fidelity-closure.md`, verify
the protected converter hash, and commit/push the bounded evidence/test
changes. It may modify only that stable evidence path and the smallest
existing test file(s) needed for regression sentinels. No new test framework,
large characterization matrix, or new expected outputs is authorized when
accepted outputs already exist.

Phase 2 MUST NOT modify production source, defaults, configuration, schema,
reference tooling, dependencies, or JDKs; perform benchmarking, optimization,
large radiograph experiments, deployment, release, or main changes. Do not
reopen accepted work without contradictory current evidence.

CLAHE remains unchanged and unauthorized for Phase 2: do not select a semantic
option, change slope `0.6`, fast/default behavior, blocksize, bins, composite
behavior, or either MPIPS CLAHE implementation. Circular Median remains
unchanged and unauthorized for Phase 2: do not fix it, change radius handling,
remove/deprecate its exposure, or establish new parity claims.

Phase 2 was accepted at baseline
`b4c032ce58605095de82c67097c61ebf458041a5`. Its conclusions remain closed
unless contradictory current evidence is found.

**Gate:** Review Required; Phase 2 accepted; republish before Phase 3.

### Phase 3 — CLAHE Semantic Closure

Phase 3 was accepted at baseline
`8c7b479947ee2b67856fd644e95b6d9eede52739`. The governing Planner decision
was
**Option A — Legacy MPIPS Contract**. Document MPIPS precise, MPIPS
fast/OpenCV, Fiji Flat, and Fiji FastFlat contracts, uint8/uint16 semantics,
parameter domains, reachability, and truthful labels using accepted
I-4C0/I-5A/I-5B evidence. No production algorithm change is authorized.

MPIPS precise CLAHE remains the production-reachable default contract and is
not Fiji Flat parity. Its difference is classified
`INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED`.

MPIPS fast/OpenCV remains a production-reachable configurable alternate, not
the default, and is not Fiji FastFlat parity. Its difference is classified
`INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED`.

Fiji Flat and Fiji FastFlat remain reference-only and not production
reachable. They must not be equated with OpenCV CLAHE or implemented in
production.

The current production configuration remains unchanged: `use_clahe=true`,
`clahe_blocksize=127`, `clahe_histogram_bins=256`, `clahe_max_slope=0.6`,
`clahe_fast=false`, and `clahe_composite=true`. The slope is
`INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED`; no optimality, clinical,
quality-superiority, Fiji-compatibility, or I-5A/I-5B parameter-selection
claim is authorized. Parameter optimization remains out of scope.

Phase-3 evidence work may update only
`.agents/evidence/imagej-fidelity-closure.md` and, if genuinely necessary,
the smallest existing CLAHE regression-test file. Existing deterministic
sentinels must be inspected first; no new test file and no `mpips/**` change
are authorized.

The retained contract alternatives are:

- **Option A — Legacy MPIPS Contract:** current custom MPIPS semantics remain
  authoritative; stop claiming Fiji parity; slope remains a later
  quality/config decision.
- **Option B — Fiji Flat Contract:** Fiji Flat becomes intended behavior and
  requires an independent production-compatible implementation plus supported
  parameter-domain and real-radiograph validation.
- **Option C — Fiji FastFlat Contract:** FastFlat remains a distinct intended
  algorithm and requires separate fidelity implementation and validation.

Option A is selected and governing; Options B and C are not selected. Do not
infer a quality recommendation from execution-safe floors. The pinned
execution-domain facts (`~1.02722168` for Fiji Flat and `~1.00394` for Fiji
FastFlat) are not production recommendations or replacements for slope `0.6`.

**Gate:** Review Required; Phase 3 accepted; republish before Phase 4.

### Phase 4 — Circular Median Fidelity Remediation

The evidence-only first gate **CIRCULAR MEDIAN RADIUS-DOMAIN / REACHABILITY
RESOLUTION** was accepted/closed at
`84b4a8cd271fcf7b262bd625530a974357704f9b` with the conclusion
`PLANNING REQUIRED — CIRCULAR MEDIAN REMEDIATION`. This current gate
authorizes the bounded **IMAGEJ RANKFILTERS SEMANTIC REMEDIATION** below.
Integer-only contract tightening is not selected.

The only authorized production change is in
`mpips/processing/imagej.py`, method
`ImageJReplicator._make_circular_kernel_imagej()`: before the existing
`r2 = int(radius * radius) + 1` calculation, apply the pinned ImageJ
`RankFilters.makeLineRadii(double radius)` mappings:

- `1.5 <= radius < 1.75` -> effective radius `1.75`;
- `2.5 <= radius < 2.85` -> effective radius `2.85`.

Continue through the existing footprint construction. Do not replace SciPy
`median_filter`, change `mode="nearest"`, median selection, dtype behavior,
or the public `median_filter_imagej()` signature. Do not otherwise redesign
Circular Median.

The current default remains `use_median_filter=true`,
`median_filter_type="hybrid_imagej"`, `median_filter_radius=2`; Circular
Median remains configurable but not default. Do not change config parsing,
validation, API/schema, worker, or DICOM behavior, and do not introduce
integer-only validation. Existing integer-oriented annotations may remain as
`TYPING / CONTRACT-DOCUMENTATION DEBT — NO RUNTIME EFFECT`.

The preferred existing test surface is
`tests/test_filtering_processing.py`; no new test file is authorized. Use
accepted I-4A reference outputs, not outputs generated from the remediated
implementation. For both uint8 and uint16, cover transition radii `1.5`,
`1.74`, `1.75`, `2.5`, `2.84`, and `2.85`, preserving non-regression cases
`0.5`, `1.0`, `2.0`, and `3.0`, using the accepted 5x5 `median_grid` fixture
and its uint16 version scaled by 257.

The eventual remediation evidence may update only
`.agents/evidence/imagej-fidelity-closure.md`. The maximum allowed claim is
`REMEDIATED AND PARITY CONFIRMED ACROSS ACCEPTED I-4A CHARACTERIZATION
MATRIX`; universal parity for all positive radii is not authorized.

**Gate:** Review Required; republish before Phase 5.

### Phase 5 — Bounded Performance Baseline

Phase 5 is accepted/closed at `a625deac10153a2c7c69a3523dd77751518b298e`.
Its reconstruction sub-gate was accepted/closed, and its released gate was
**BOUNDED PERFORMANCE MEASUREMENT**. Use only the
accepted reconstructed runtime described below. Before any benchmark, verify
that its temporary root still exists and contains the accepted runtime; do
not assume `/tmp` persistence. At minimum, verify the absolute Java path,
Temurin 17.0.19+10 identity, ImageJ JAR SHA, tracked harness SHA, and all
final classpath components. If the root is missing or materially altered,
stop with `REVIEW BLOCKED — ACCEPTED RECONSTRUCTED RUNTIME NO LONGER
AVAILABLE`; do not reconstruct again under the benchmark gate.

The accepted reconstruction used only the exact already-pinned runtime from
`scripts/imagej_reference/README.md`:

- Eclipse Temurin 17.0.19+10 HotSpot Linux x86_64, archive
  `OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz`, SHA256
  `d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331`;
- ImageJ `ij-1.54p.jar`, SHA256
  `2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20`;
- Fiji CLAHE sources from `axtimwalde/mpicbg@0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0`,
  with every required source hash verified against the README before compile;
- `Hybrid_2D_Median_Filter.java`, SHA256
  `494cc92747ba8e01e9ad19f16d735ffe8faf0b65eba00f02fda691bc5529af03`;
- tracked `ReferenceHarness.java`, SHA256
  `4dd097ff92002f6d3d6a52ef6d2231e31aa3b32610c8af9e0c9e300559f2bcd5`.

The reconstruction may download only the exact documented artifacts, verify
each SHA256 before extraction/classpath use, compile only the documented
sources with the reconstructed absolute `java`/`javac`, and execute only from
a fresh temporary untracked directory under `/tmp`. It must not use sudo or
apt, install system-wide, modify shell startup files, persistently change
`PATH`/`JAVA_HOME`, execute downloaded scripts, or use arbitrary versions.
Downloaded content remains untrusted until its identity check passes. No JDK,
JAR, source, class, benchmark binary, or other reconstruction artifact may be
tracked or committed.

After hash verification and compilation, the reconstruction gate smoke-tested
Fiji Flat
and Fiji FastFlat at the already accepted common context: slope 1.5, block
radius 63, internal bins 255, using a small deterministic fixture. This is
environment verification, not the Phase-5 benchmark. Do not rerun the full
120-case characterization or rewrite accepted evidence. The reconstructed
runtime must be described as **RECONSTRUCTED FROM ACCEPTED PINNED PROVENANCE**,
not as an original retained runtime. The reconstruction gate makes no tracked
file changes and does not automatically start benchmarking.

Phase 5 execution is performance characterization only. Measure, when
executable, MPIPS
precise CLAHE (`fast=False`), MPIPS fast/OpenCV CLAHE (`fast=True`), pinned
Fiji Flat, and pinned Fiji FastFlat. These four implementations are not
semantically equivalent; do not treat this as a benchmark of interchangeable
algorithms or draw fidelity, image-quality, scientific-validity, or clinical
conclusions from speed.

For the current MPIPS production-context characterization, use blocksize 127,
displayed histogram bins 256, and slope 0.6. Precise is the current default;
fast/OpenCV is configurable but not default. Preserve
`use_clahe=true`, `clahe_blocksize=127`, `clahe_histogram_bins=256`,
`clahe_max_slope=0.6`, `clahe_fast=false`, and `clahe_composite=true`.
`0.6` remains `INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED`, with no
optimality, clinical, or Fiji-compatibility claim.

For a common executable reference context, use the already established tuple
of slope 1.5, blocksize 127, block radius 63, displayed bins 256, and internal
Fiji bins 255 only after verifying that both pinned Fiji implementations
execute successfully. This is a runtime-comparison parameter only, not a
production replacement, quality recommendation, or optimized parameter.

Use at least one deterministic in-memory or temporary controlled fixture,
single-channel and preferably uint16, recording exact shape, dtype, and input
SHA256. Do not commit benchmark binaries or create a tracked dataset. An
accepted local full-resolution radiograph may be measured when available; if
not, record `FULL-RESOLUTION RADIOGRAPH MEASUREMENT NOT PERFORMED — RETAINED
LOCAL INPUT UNAVAILABLE`. Do not create a cohort or perform quality ablation.

For every implementation/context, record identity, semantic classification,
input/output shape and dtype, input/output SHA256, parameters, timing scope,
warm-up policy, repetition count, individual or transparent wall-time results,
cold/warm distinction, peak RSS where practical, success/error status, and
execution environment. Use a small bounded repetition count; do not run
hundreds of repetitions. Record Python/NumPy/SciPy/OpenCV and Java/JDK
identity where readily available.

For Fiji, a new Java process per run must be labeled
`REFERENCE HARNESS END-TO-END WALL TIME — INCLUDES JVM/PROCESS STARTUP` and
must not be compared as warm in-process Python timing. Peak RSS may be
`NOT MEASURED` when reliable measurement is unavailable. Repeated runs with
the same implementation, input, and parameters must have identical output
hashes; unexpected differences stop the phase.

Phase 5 must not optimize, change algorithms/defaults/parameters/threading,
modify the reference harness, or alter production behavior. It may update
only `.agents/evidence/imagej-fidelity-closure.md`; use existing tooling and
ephemeral commands/temporary files. No tracked benchmark script is expected.

**Gate:** Review Required; republish before Phase 6.

### Phase 6 — Minimal Reference / Regression Sentinel Suite (Released)

Create or consolidate the smallest cheap deterministic regression protection
needed for every accepted ImageJ/Fiji contract/status. Audit first; do not
duplicate sufficient Phase-2/Phase-4 coverage or build another characterization
matrix, real-radiograph experiment, or performance benchmark.

The audit MUST classify Contrast Stretch, Weighted Equalization, Classic
Equalization, Hybrid Median, MPIPS precise CLAHE, MPIPS fast/OpenCV CLAHE,
Fiji Flat, Fiji FastFlat, Circular Median, and Temporal Median by accepted
contract/status, current deterministic coverage, and whether a new sentinel is
necessary. Reuse existing accepted protection for Contrast Stretch, both
Equalization variants, Hybrid Median, and the complete Circular Median I-4A
matrix. Temporal Median remains `NOT PRODUCTION REACHABLE — N/A` and requires
no artificial output sentinel; if a production caller is found, stop and
return to review.

The primary gap is executable protection for the governed CLAHE divergence.
Using the accepted 128x128 uint16 fixture
`((x*257 + y*509 + ((x*y)%251)*131) % 65536)` with input SHA256
`01941aeb2b4070d224e0271e9ef3f8bd6075001638d4cd75f9bfd06e4b0355c1`, slope
1.5, blocksize 127, block radius 63, displayed bins 256, internal Fiji bins
255, and composite true for MPIPS, add only the smallest existing-test-file
sentinel. It MUST assert shape, uint16 dtype, deterministic frozen Legacy MPIPS
hashes, and inequality to the accepted Fiji Flat hash
`b12db91a188b0dccdf2703dc3caa948bab24613e61256ef0002023d147daa34b` and
Fiji FastFlat hash
`b4a4958976bd092c0bc12d4d02b52e80d693549a72ee9ec9a7916cbf319b8fda` as
applicable. This encodes intentional semantic divergence, not quality or
approximate parity, and must not invoke Fiji at ordinary pytest runtime.

Before freezing Legacy MPIPS hashes, verify the exact accepted implementation
baseline and repeat precise and fast/OpenCV execution at least twice. If either
is nondeterministic, stop: `REVIEW BLOCKED`.

Audit accepted uint8 coverage for both MPIPS CLAHE contracts. Add only a
smallest uint8 sentinel in `tests/test_imagej_migration.py` if a genuine gap
exists; any newly frozen output is a `LEGACY MPIPS CONTRACT REGRESSION
BASELINE`, never a Fiji reference. Do not modify
`tests/test_filtering_processing.py` unless direct evidence shows a missing
accepted sentinel.

Phase 6 may modify only `tests/test_imagej_migration.py` and
`.agents/evidence/imagej-fidelity-closure.md`; no new test file, production
source, harness, dependency, or Java/Fiji runtime requirement is authorized.
Evidence MUST retain historical sections and add the Phase-6 audit,
fixture/constants, frozen hashes, sentinel behavior, uint8 result, exact
changes, local commands/results labeled `LOCAL TESTS, NOT CI`, no-Java/network
confirmation, protected converter SHA, remaining gaps, and terminal
`Review Required`.

**Gate:** Review Required; republish before final closure.

### Phase 7 — Final ImageJ Fidelity Closure

Produce final evidence for every operation covering reference, production
reachability, contract, parity, intentional divergence, regression coverage,
performance note, and final closure state. Final acceptance requires no
unresolved production-reachable fidelity failure. Acceptance does not authorize
production release.

## Acceptance criteria

- [ ] One closure matrix covers every discovered ImageJ/Fiji-derived or
  inspired operation and current reachability.
- [ ] Accepted parity and N/A items are closed without reopening I-5B.
- [ ] Exactly one governed CLAHE contract is selected, or the task stops for
  planning with the required decision string.
- [ ] Circular Median is remediated and parity-confirmed, or explicitly closed
  as governed N/A/deprecated/excluded when reachability and authority support
  that result.
- [ ] Required bounded performance measurements and deterministic hashes are
  recorded without production optimization.
- [ ] Minimal regression protection matches each final contract/status.
- [ ] No unresolved production-reachable fidelity failure remains at final
  acceptance, and the protected converter hash remains unchanged.

## Verification requirements

### Required checks

- Direct inspection of current callers/configuration and accepted evidence.
- Phase-appropriate deterministic reference/regression checks.
- Performance records with the required input, parameter, timing, memory,
  hash, and environment fields where executable.
- `sha256sum mpips/conversion/tiff_json_to_dcm.py` equals the protected hash.
- `git diff --check` and task-scoped diff inspection for every publication.

### Required evidence

The Executor MUST report exact task revision, implementation baseline,
phase/revision executed, commands and observed results, changed files,
reachability evidence, parity/divergence classifications, performance limits,
known gaps, and any planning stop. Local evidence MUST NOT be represented as
CI or release evidence.

## Stop conditions

In addition to repository stop conditions, stop and return to planning when:

- CLAHE semantic authority cannot select A, B, or C;
- the retained pinned Fiji/ImageJ environment cannot be reconstructed under
  existing authority;
- a phase requires reopening I-5B, changing threshold/stage order, changing
  slope `0.6`, or selecting production configuration;
- Circular Median reachability or intended status cannot be established;
- a requested change exceeds the current phase revision.

The Executor MUST use the exact string `PLANNING REQUIRED — CLAHE SEMANTIC
SELECTION` for the CLAHE decision stop and MUST NOT invent the decision.

## Side-effect authorization

### Explicitly authorized for this publication

- Create only `.agents/tasks/imagej-fidelity-closure.md`.
- Run `git diff --check`, inspect the task-only diff, commit the task
  publication, and push normally to `origin/refactor/package-boundaries`.
- This revision authorizes the later Phase-6 test/evidence work only in
  `tests/test_imagej_migration.py` and
  `.agents/evidence/imagej-fidelity-closure.md`, subject to the Phase-6
  constraints above.

### Not authorized

- Any Phase-6 execution during this publication.
- Any change outside the authorized future Phase-6 test/evidence surfaces,
  production behavior/configuration, source/reference harness, dependencies,
  stage-order work, deployment, release, main change, or force push.

## Expected terminal outcome

This publication ends at **Review Required** with the immutable publication
commit as the task revision. It does not execute Phase 6, benchmark, modify
tests, or modify evidence.

## Review and remediation handling

Review each phase against this exact task revision, the accepted baseline, and
observed evidence. Bounded remediation updates this same stable path and must
be republished at a new immutable revision. Materially new scope returns to
Delivery Planning. Final implementation acceptance remains separate from
production release authorization.
