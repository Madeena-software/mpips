---
title: MPIPS ImageJ/Fiji Fidelity Closure
document_id: AGENT-TASK-IMAGEJ-FIDELITY-CLOSURE-001
version: 1.1
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
`8396fbc768285cc68ed3bbe572561cd664b70e8b`

**Task revision:** `.agents/tasks/imagej-fidelity-closure.md @ the full
publication commit containing this file`.

The task revision and implementation baseline are separate. A later material
phase MUST republish this same task path at a new immutable revision before
execution.

**Current released phase:** **PHASE 2 — ACCEPTED PARITY + N/A CLOSURE**

**Accepted Phase-1 evidence revision:**
`1be8ba791bc187be0c8b107cf165ac24f88ee412`

Phase 1 is accepted at that revision. Its conclusions are not reopened unless
direct contradictory repository evidence is found.

This publication explicitly authorizes Phase 1 execution to:

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

Publication releases Phase 1 planning/inventory only. No later phase is
automatically authorized. Each phase ends at `Review Required`; material next
phase work requires Planner/Reviewer review and a new immutable revision of
this same task path.

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

### Phase 2 — Accepted Parity + N/A Closure

Phase 2 is explicitly released by this task revision for exactly the following
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

Phase 3 and all later phases remain unauthorized until Planner/Reviewer review,
acceptance or remediation, and republication of this same stable task path at
a new immutable revision.

**Gate:** Review Required; republish before Phase 3.

### Phase 3 — CLAHE Semantic Closure

Document MPIPS precise, MPIPS fast/OpenCV, Fiji Flat, and Fiji FastFlat
contracts, uint8/uint16 semantics, parameter domains, reachability, and
truthful labels using accepted I-4C0/I-5A/I-5B evidence. Do not change slope
`0.6` automatically.

The contract MUST be deliberately selected as exactly one of:

- **Option A — Legacy MPIPS Contract:** current custom MPIPS semantics remain
  authoritative; stop claiming Fiji parity; slope remains a later
  quality/config decision.
- **Option B — Fiji Flat Contract:** Fiji Flat becomes intended behavior and
  requires an independent production-compatible implementation plus supported
  parameter-domain and real-radiograph validation.
- **Option C — Fiji FastFlat Contract:** FastFlat remains a distinct intended
  algorithm and requires separate fidelity implementation and validation.

If authority is insufficient, stop with `PLANNING REQUIRED — CLAHE SEMANTIC
SELECTION`. Do not infer a quality recommendation from execution-safe floors.

**Gate:** Review Required; republish before any implementation/remediation.

### Phase 4 — Circular Median Resolution

First verify production/config/API reachability. If reachable and intended,
characterize the exact mismatch against pinned ImageJ and authorize bounded
remediation only in a republished phase revision, with parity/regression
evidence. If unreachable or no longer intended, produce explicit governed
deprecation/exclusion/N/A closure. Do not silently remove behavior.

**Gate:** Review Required; republish before remediation or closure changes.

### Phase 5 — Bounded Performance Baseline

Measure, without optimization, MPIPS precise CLAHE, MPIPS fast/OpenCV CLAHE,
pinned Fiji Flat, and pinned Fiji FastFlat where executable. Use controlled
fixtures and, when practical, one accepted full-resolution radiograph. Record
shape/dtype, parameters, warm/cold distinction where material, wall time, peak
RSS where practical, deterministic output hash, and execution environment.
Do not draw image-quality conclusions from speed.

**Gate:** Review Required; republish before final suite work.

### Phase 6 — Minimal Reference / Regression Sentinel Suite

Create or consolidate cheap deterministic coverage for accepted operations,
retained Circular Median variants, CLAHE contract characterization, and
explicit expected divergence where applicable. Do not build another large
real-radiograph experiment.

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

### Not authorized

- Any production/source/test/reference/evidence change beyond the task file.
- Any implementation phase, stage-order work, production configuration change,
  dependency/JDK installation, deployment, release, main change, or force push.

## Expected terminal outcome

This publication ends at **Review Required** with the immutable publication
commit as the task revision. It does not execute ImageJ/Fiji fidelity work.

## Review and remediation handling

Review each phase against this exact task revision, the accepted baseline, and
observed evidence. Bounded remediation updates this same stable path and must
be republished at a new immutable revision. Materially new scope returns to
Delivery Planning. Final implementation acceptance remains separate from
production release authorization.
