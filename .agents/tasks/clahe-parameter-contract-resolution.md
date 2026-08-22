---
title: MPIPS CLAHE Parameter-Contract Resolution — I-4C0
document_id: AGENT-TASK-MPIPS-I4C0-CLAHE
version: 1.0
status: Validated/Published
language: en-US
scope:
  - CLAHE parameter-contract evidence and decision support
  - pinned Fiji Flat and FastFlat characterization
authority_note: This task authorizes bounded evidence collection only. It does not authorize a production CLAHE behavior, default, schema, or image-quality decision.
---

# Executable Task

## Task identity

**Task title:** MPIPS CLAHE Parameter-Contract Resolution — I-4C0

**Task path:** `.agents/tasks/clahe-parameter-contract-resolution.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** I-4C0 — CLAHE parameter-contract
resolution

**Owner / designated planning authority:** MPIPS Planner/Reviewer

## Delivery context

The accepted I-4A ImageJ/Fiji characterization classified both `CLAHE Flat /
precise` and `CLAHE FastFlat / fast` as `FIDELITY FAILURE`. It accepted the
parameter mapping:

- displayed `histogram_bins=256` → Fiji internal `bins=255`;
- `blocksize=127` → Fiji `block_radius=63`.

The current production default `clahe_max_slope=0.6` has been observed as an
inherited MPIPS parameter. Its Git provenance and any documented Fiji-derived
semantic rationale remain to be resolved. Production CLAHE remediation is not
authorized by this task.

This task is **evidence and decision support only**. It must not choose an
image-quality default, migrate the algorithm, or alter current production
behavior.

Accepted prior evidence and current observed context:

- I-4A classified `CLAHE Flat / precise` as `FIDELITY FAILURE`.
- I-4A classified `CLAHE FastFlat / fast` as `FIDELITY FAILURE`.
- Current production defaults are:
  `use_clahe=True`, `clahe_blocksize=127`, `clahe_histogram_bins=256`,
  `clahe_max_slope=0.6`, `clahe_fast=False`, and `clahe_composite=True`.
- The production path is MPIPS Python CLAHE, not the Java/Fiji runtime itself.
- `uint16` is the production radiography path.

The accepted I-4A task/evidence are:
`.agents/tasks/imagej-fidelity-characterization.md` at governing revision
`ae873d1d8ea04cb482a7896ca84088867e5524ec` and
`.agents/evidence/imagej-fidelity-characterization.md` plus its JSON evidence.

## Baseline and task revision

**Implementation baseline:**
`979de4ee9cd24731d5adf74aa19dc412f1dedc37`

**Task revision:** `.agents/tasks/clahe-parameter-contract-resolution.md @ the
immutable publication commit containing this file`.

The publication report supplies the full publication SHA before Executor
handoff. The task revision and implementation baseline are separate.

## Objective

Produce immutable, reproducible evidence that resolves:

1. Git provenance and authority of `clahe_max_slope=0.6`;
2. authoritative Fiji Flat and FastFlat execution-domain behavior;
3. `uint8` and `uint16` semantics;
4. production reachability;
5. differences between current MPIPS precise/fast behavior and Fiji;
6. semantic options for a later product/technical decision; and
7. conditions that must be satisfied before any default or algorithm migration.

The evidence must not select an image-quality default or silently mix Flat and
FastFlat contracts.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- `.agents/tasks/_template.md`
- Accepted implementation baseline
  `979de4ee9cd24731d5adf74aa19dc412f1dedc37`
- `.agents/tasks/imagej-fidelity-characterization.md`
- `.agents/evidence/imagej-fidelity-characterization.md`
- `.agents/evidence/imagej-fidelity-characterization.json`
- `scripts/imagej_reference/README.md`
- The approved I-4C0 publication directive and its stated decision boundary.

### Requirement traceability

- I-4C0 CLAHE parameter-contract resolution → this task, the repository
  delivery contract, and the accepted I-4A characterization evidence.
- CLAHE production reachability → current MPIPS API, workflow, pipeline,
  configuration, and `ImageJReplicator` call surfaces.
- Fiji execution-domain evidence → pinned `axtimwalde/mpicbg` reference at
  `0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0` and the retained reference
  environment documented by `scripts/imagej_reference/README.md`.

Existing implementation is observed reality, not retroactive product or
algorithm authority.

## Scope

### In scope

- Independently verify the already-observed Git history for `0.6`, including:
  parent `3169a725752d0007cc97dbb58512feffd13eb864`, first-known
  introductions `6a1f48b9d3e33fbfa178b9bd09154004aa09c446` and
  `2de4a4ed13a5f7bf07628a8be63b67d11b455465`, later CLAHE configuration
  consolidation/migration commits, and current ownership around
  `ad6fa7154067ee73290b306aa84992a42e10960f`.
- Determine the earliest repository-visible `0.6`, every major ownership move,
  and whether any commit, design, or evidence explains the value. Do not invent
  human rationale. If unsupported, classify it as
  `INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED`.
- Analyze the pinned Fiji CLAHE implementation separately for Flat and
  FastFlat. Inspect `Flat.java`, `FastFlat.java`, `ShortApply.java`,
  `Apply.java`, `ByteApply.java`, `FastByteApply.java`, `FloatApply.java`,
  `RGBApply.java`, and relevant `Util.java` classes at
  `axtimwalde/mpicbg@0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0`.
- For production geometry, characterize `blocksize=127`,
  `block_radius=63`, displayed bins `256`, internal bins `255`, and `mask=None`.
- Record exact clipping equations, integer rounding semantics, actual Flat
  local-window pixel count `n` including edge and corner windows, FastFlat's
  fixed block geometry, and transfer interpolation. Determine execution-domain
  boundaries mathematically and verify representative values with the
  executable pinned reference.
- Characterize at minimum the slope matrix `0.6`, `1.0`, the first observed
  execution-safe value near the calculated boundary, `1.03`, `1.5`, `2.0`, and
  `3.0`. Add boundary-adjacent values such as `1.003`, `1.004`, `1.027`, and
  `1.028` when needed. These are test values, not quality recommendations.
- For every relevant slope, record Flat and FastFlat execution or error,
  dtype, geometry, mask, and the precise reference error when one occurs, for
  both `uint8` and `uint16` as applicable.
- Characterize Fiji `uint16` behavior from actual pinned source and execution;
  do not assume a 65,536-bin CLAHE. Explain how the byte working
  representation is built and how the transfer is applied back to
  `ShortProcessor` data. Do not claim `uint8`/`uint16` parity merely because
  execution-domain failures match.
- Document current MPIPS semantics without changing them:
  `fast=False` is the custom Python precise path and `fast=True` is based on
  OpenCV `createCLAHE`. Record current clip-limit behavior, including any
  lower-bound clamping that produces numeric MPIPS output where pinned Fiji
  errors.
- Trace the actual default DICOM/radiography flow sufficiently to establish
  `API → conversion service → worker → workflow → ImagerPipelineConfig() →
  RadiographyPipeline → ImageJReplicator.apply_clahe()` and record production
  dtype, omitted/default configuration behavior, `use_clahe` reachability,
  `fast`, slope, bins, blocksize, and composite values.
- Distinguish `PRODUCTION-REACHABLE: MPIPS Python CLAHE` from
  `NOT PRODUCTION-REACHABLE: Java/Fiji runtime itself` unless repository
  evidence proves otherwise.
- Produce the mandatory Markdown evidence artifact
  `.agents/evidence/clahe-parameter-contract-resolution.md` and optionally
  `.agents/evidence/clahe-parameter-contract-resolution.json` only when its
  structured results materially improve reproducibility.

### Out of scope

- Any change to `mpips/processing/imagej.py`, CLAHE implementation behavior,
  defaults, schema, configuration, migration, or production call paths.
- Changes to CLAHE golden tests caused by behavior changes; Flat remediation;
  FastFlat remediation; Circular Median work; threshold ablation; or any
  production data, DICOM converter, dependency, deployment, or release change.
- Choosing an image-quality default or claiming that an execution-safe floor is
  a quality recommendation.
- Executing the recommended real-radiograph ablation in this task.
- Installing or downloading a new JDK/runtime, system Java, or other system
  dependency. Reuse only the retained/reconstructible reference environment
  documented in `scripts/imagej_reference/README.md`; if it is unavailable or
  unusable, stop and return to planning.
- Modifying `scripts/imagej_reference/README.md`, the existing harness, or
  production/source/test files. If the retained tooling cannot support the
  required evidence without a material change, stop and return to planning.
- Mutating external systems, force-pushing, rewriting history, modifying
  `main`, mutating tags, deploying, or releasing.

### Preserved behavior and boundaries

- Current MPIPS CLAHE behavior and all current defaults remain unchanged.
- No config, schema, production, or golden-test behavior changes are made.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical with SHA-256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- The Java/Fiji reference remains characterization-only and never becomes a
  production dependency.
- Evidence remains deterministic, lightweight, source-pinned, and human
  auditable. No third-party source, JAR, JDK, or large binary artifact is
  committed.
- Flat and FastFlat remain separate algorithms and separate evidence rows.

## Dependencies and assumptions

### Dependencies

- The accepted baseline and the pinned I-4A evidence remain available.
- The retained/reconstructible reference environment and source identities in
  `scripts/imagej_reference/README.md` remain usable.
- Current MPIPS source, configuration, workflow, and test files are readable.

### Approved assumptions

- Current production radiography uses `uint16` and the listed default CLAHE
  configuration unless execution evidence shows otherwise.
- The I-4A displayed-to-internal parameter mapping is accepted input and must
  be preserved while independently verifying the new contract evidence.
- A reference execution error is a result to record, not a reason to substitute
  another algorithm or silently clamp the parameter.

### Remaining approval requirements

- No product or image-quality decision is approved by this task.
- A later default change or algorithm migration requires explicit semantic
  selection, documented supported geometry/bins/masks/dtypes, real-radiograph
  comparison, regression impact analysis, config/schema/migration approval,
  and a new validated implementation task.
- Any need to change production code, defaults, schema, tests, dependencies,
  reference tooling, or runtime environment returns to planning.

## Required capabilities

- Repository read/write and local command execution.
- Git history and source inspection.
- Execution of the retained pinned Java reference and existing MPIPS
  characterization tooling.
- Hash and deterministic evidence verification.

## Execution constraints

- Use exact pinned provenance and record source/artifact hashes where practical.
- Do not use floating upstream versions or infer rationale from parameter names,
  comments, or commit authorship alone.
- Derive and record Flat and FastFlat equations independently; do not conflate
  their clipping, block, or interpolation semantics.
- Include edge and corner local-window counts in Flat boundary analysis.
- Characterize `uint8` and `uint16` separately, including Fiji's
  `ShortApply` conversion path and rounding back to short data.
- Use the existing retained reference environment only. No new runtime or
  system installation is authorized.
- Record observed execution errors precisely and retain commands sufficient to
  reproduce them. Do not relabel execution-safe values as quality defaults.
- Keep all current MPIPS behavior and protected converter bytes unchanged.

## Acceptance criteria

- [ ] The evidence independently verifies the requested Git provenance and
      identifies the earliest visible `0.6`, major ownership moves, and whether
      rationale was recovered without inventing one.
- [ ] Pinned source provenance, source hashes, reference environment identity,
      and exact reproduction commands are recorded.
- [ ] Flat and FastFlat are analyzed separately for production geometry with
      exact clipping equations, rounding, edge/corner `n`, fixed-block or
      interpolation behavior, and calculated execution-domain boundaries.
- [ ] The required slope matrix includes `0.6`, `1.0`, the first observed
      execution-safe boundary value, `1.03`, `1.5`, `2.0`, `3.0`, and any
      necessary boundary-adjacent values, with Flat/FastFlat result, dtype,
      geometry, mask, and precise errors.
- [ ] Fiji `uint8` and `uint16` semantics are recorded from the pinned source
      and execution, including the `ShortApply` working representation and
      transfer-back behavior; no unsupported parity claim is made.
- [ ] Current MPIPS precise and fast semantics, clip-limit behavior, and any
      lower-bound clamping are documented without source changes.
- [ ] The actual default DICOM/radiography reachability and all relevant
      parameters are traced, with Java/Fiji runtime reachability distinguished.
- [ ] The Markdown evidence exists and contains the immutable task revision,
      baseline SHA, provenance/hashes, equations, slope-domain matrix, dtype
      findings, reachability, MPIPS semantics, decision options, default-change
      HOLD, recommended next experiment, and exact reproduction notes.
- [ ] The evidence records these future semantic options without choosing one:
      **Option A — Legacy MPIPS Contract** (keep `0.6` as MPIPS-specific and
      stop claiming exact Fiji parity); **Option B — Fiji Flat Contract**
      (authoritative Flat with a valid domain and independent implementation
      plus radiograph validation); and **Option C — Fiji FastFlat Contract**
      (distinct FastFlat algorithm requiring separate parity work).
- [ ] The evidence explicitly prohibits changing `clahe_max_slope=0.6` from
      I-4C0 and states the required default-change gates.
- [ ] The evidence recommends a later real-radiograph ablation comparing
      current MPIPS precise at `0.6`, informative higher values, and
      Fiji-Flat-compatible candidate semantics; it does not execute that
      ablation.
- [ ] No production, config, schema, golden-test, dependency, converter,
      runtime, or unrelated repository behavior changes; the protected
      converter hash remains exact.

## Verification requirements

### Required checks

- Verify the execution branch and accepted baseline ancestry before evidence
  work; do not treat the publication commit as a new implementation baseline.
- Verify the retained reference environment and pinned source/artifact hashes
  using the commands documented in `scripts/imagej_reference/README.md`.
- Run the existing pinned reference characterization for the required Flat and
  FastFlat slope/dtype/geometry matrix, recording actual outputs and errors.
- Inspect the exact current MPIPS source/configuration and trace the default
  production call path.
- Verify the protected converter SHA-256:
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Verify the final diff contains only the evidence artifact(s) authorized by
  this task and no production/config/schema/test/tooling changes.

### Required evidence

The Executor MUST report the exact governing task revision, implementation
baseline, implementation/evidence revision, commands actually run, observed
results, source and artifact hashes, slope matrix, equations, dtype findings,
production reachability, decision options, limitations, and any stop condition.
Local results MUST NOT be represented as CI or as an image-quality decision.

## Stop conditions

The Executor MUST stop and return `Planning Required` when:

- the governing task revision, implementation baseline, pinned sources, or
  retained reference environment cannot be established;
- the reference requires a new runtime download, system installation, or
  unapproved dependency/tooling change;
- the source, equations, execution domain, or production reachability is
  materially ambiguous or contradictory;
- the task would require changing production CLAHE behavior, defaults, schema,
  tests, reference tooling, dependencies, or the protected converter;
- a product/technical semantic selection or image-quality decision is required;
- the real-radiograph ablation is requested as part of this task; or
- any security, privacy, data-integrity, licensing, operational, or side-effect
  concern exceeds this bounded evidence objective.

The Executor MUST NOT silently reinterpret this task into remediation,
migration, default selection, or release work.

## Side-effect authorization

The future Executor is explicitly authorized to inspect repository history and
source, reuse the retained reference environment, execute the bounded local
characterization, create:

- `.agents/evidence/clahe-parameter-contract-resolution.md`; and
- optionally `.agents/evidence/clahe-parameter-contract-resolution.json` when
  structured results materially improve reproducibility;

then create normal evidence commit(s) on
`refactor/package-boundaries` and push normally to
`origin/refactor/package-boundaries`.

The Executor is not authorized to modify production CLAHE, defaults, schema,
golden tests, source, reference tooling, dependencies, system runtimes,
`main`, tags, history, external systems, or deployment/release state. No
force-push, pull request, deployment, or release is authorized.

### Explicitly authorized side effects

- Read-only Git/source/reference inspection and local execution.
- Creation of the bounded Markdown evidence and optional JSON evidence files.
- Normal commit and push of only those evidence changes to
  `refactor/package-boundaries`.

## Expected terminal outcome

### Review Required

The Executor returns `Review Required` after the bounded evidence is committed
and pushed, reporting the immutable evidence revision, exact task revision,
baseline, observed verification, limitations, and any unresolved non-blocking
observations. The Executor must verify local `HEAD ==
origin/refactor/package-boundaries` and a clean worktree.

### Planning Required

The Executor returns `Planning Required` with the exact blocking evidence when
a stop condition prevents safe completion within this task.

## Decision boundary and future work

### Contract options to preserve without choosing

**Option A — Legacy MPIPS Contract**

- Keep `0.6`.
- Define it as MPIPS-specific.
- Stop claiming exact Fiji CLAHE parity for that behavior.
- Focus future work on MPIPS quality and consistency.

**Option B — Fiji Flat Contract**

- Treat Flat as authoritative.
- Define the valid parameter domain.
- Independently implement observable Fiji behavior.
- Migrate a default only after real-radiograph quality validation.

**Option C — Fiji FastFlat Contract**

- Treat FastFlat as a distinct authoritative algorithm.
- Do not conflate it with Flat.
- Require separate implementation/parity work.

Do not silently mix contracts depending on slope.

### Default-change HOLD

I-4C0 MUST NOT change `clahe_max_slope=0.6`. A later default change requires:

1. explicit product/technical semantic selection;
2. documented supported geometry, bins, masks, and dtypes;
3. real-radiograph comparison;
4. regression impact analysis;
5. config/schema/migration approval; and
6. a validated implementation task.

Execution-safe mathematical floors are not approved quality defaults.

### Recommended next experiment

After this evidence is reviewed, plan a separate real-radiograph ablation
before any default migration. It should compare current MPIPS precise at `0.6`,
informative current MPIPS behavior at higher values, and Fiji Flat-compatible
semantics at candidate values such as `1.03`, `1.5`, `2.0`, and `3.0`. These
values are experimental candidates only. I-4C0 does not execute the ablation.
