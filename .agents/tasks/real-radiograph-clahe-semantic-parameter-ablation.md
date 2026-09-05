---
title: MPIPS Real-Radiograph CLAHE Semantic/Parameter Ablation — I-5A
document_id: AGENT-TASK-MPIPS-I5A-REAL-RADIOGRAPH-CLAHE
version: 1.0
status: Validated/Published
language: en-US
scope:
  - controlled real-radiograph CLAHE ablation
  - structural-preservation decision support
authority_note: This task authorizes bounded experimental evidence only. It does not authorize production CLAHE changes, default selection, clinical validation, or external-data mutation.
---

# Executable Task

## Task identity

**Task title:** MPIPS Real-Radiograph CLAHE Semantic/Parameter Ablation — I-5A

**Task path:** `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** I-5A — real-radiograph CLAHE
semantic/parameter ablation; controlled experiment and decision support.

**Owner / designated planning authority:** MPIPS Planner/Reviewer

## Delivery context

The accepted baseline is
`15305dd000538aaf3459e4124975ac17892c4d31`. Hybrid Median fidelity
remediation and I-4C0 CLAHE Parameter-Contract Resolution are accepted.
`clahe_max_slope=0.6` remains an inherited MPIPS default whose rationale was
not recovered. No CLAHE semantic contract or replacement production default
has been selected.

I-5A is a controlled real-radiograph experiment required before any later
semantic-selection or production-migration task. It is decision-support only:
it is not production remediation, production configuration migration, default
selection, clinical validation, or a Threshold × CLAHE ablation.

## Baseline and task revision

**Implementation baseline:**
`15305dd000538aaf3459e4124975ac17892c4d31`

**Task revision:** `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation.md`
@ the immutable publication commit containing this file. The publication
report supplies the full commit SHA before Executor handoff. The task revision
and implementation baseline are separate.

## Objective

Answer the following question with every feasible non-CLAHE processing variable
held constant:

> How do different CLAHE semantic contracts and slope candidates affect
> structural preservation on real radiographs relative to the accepted
> reference-quality images?

The result is decision-support evidence for a later semantic-selection task.
It MUST NOT select or modify the production CLAHE default.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- `.agents/tasks/_template.md`
- Accepted implementation/evidence baseline
  `15305dd000538aaf3459e4124975ac17892c4d31`
- `.agents/tasks/real-radiograph-characterization.md` @ governing revision
  `deaf1430f62c90ce02cd4cefc8b58ab380d2aad8`
- Accepted structural-characterization implementation/result lineage
  `b14625ab01fe031cb3a9258b9fc5ff2227b032b3`
- `.agents/tasks/clahe-parameter-contract-resolution.md` @ governing revision
  `396071888842b99081a0f89a9f56a1452d99235b`
- `.agents/evidence/clahe-parameter-contract-resolution.md`
- `.agents/evidence/clahe-parameter-contract-resolution.json`
- `scripts/imagej_reference/README.md`
- Pinned Fiji reference authority:
  `axtimwalde/mpicbg@0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0`

Accepted structural characterization established 19 comparable `Kepala`
pairs and 19 comparable `Tulang Belakang` pairs, structural suppression
patterns in weak/peripheral structures, no causal attribution to a single
processing stage, lossless geometry reconciliation only, and the accepted
structural-IQA metrics. Its tracked artifacts are:

- `artifacts/real-data-regression/radiograph-structural-characterization.md`
- `artifacts/real-data-regression/radiograph-structural-characterization.json`
- `artifacts/real-data-regression/radiograph-structural-characterization.csv`
- `artifacts/real-data-regression/kambing-baseline.json`

Accepted I-4C0 conclusions are that current production uses MPIPS Python
CLAHE; Java/Fiji CLAHE is reference/experimental only; `clahe_max_slope=0.6`
is inherited without recovered approved rationale; Fiji Flat and FastFlat are
distinct algorithms; changing `0.6` is not authorized; execution-safe
mathematical floors are not quality recommendations; and real-radiograph
comparison is required before semantic/default migration.

### Requirement traceability

- I-5A real-radiograph CLAHE decision support → this bounded task, the
  accepted structural-characterization outcome, and accepted I-4C0 evidence.
- Paired structural preservation →
  `mpips.iqa.analyze_structural_preservation` and the accepted structural-IQA
  metric semantics.
- Fiji candidate semantics → pinned `axtimwalde/mpicbg` revision above and
  the retained environment documented by `scripts/imagej_reference/README.md`.

The external source collection is the read-only `6 Kambing Radiografi` Drive
folder:
<https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8>.
Existing `Kepala`/`Tulang Belakang` comparison folders and identity rules from
the structural-characterization task may be reused as read-only authority.

## Scope

### In scope

- Build a deterministic raw → calibration → logical goat/acquisition/anatomy
  → accepted reference-quality TIFF mapping before ablation execution.
- Use repository metadata, filenames, Drive hierarchy, hashes, acquisition
  metadata, and tracked real-data artifacts where available. Identity MUST NOT
  be guessed.
- Require multiple independent mapped cases. Meaningful execution requires
  more than one logical case and representation of both `Kepala` and `Tulang
  Belakang`; multiple goats and acquisitions are preferred. Record every
  excluded case and reason.
- Run the exact primary candidate matrix below and no additional candidate in
  the primary matrix:

| ID | Semantic contract | Slope | Intended difference |
|---|---|---:|---|
| C0 | CLAHE disabled | N/A | `use_clahe=false` |
| M06 | MPIPS precise | 0.6 | current MPIPS precise CLAHE |
| M103 | MPIPS precise | 1.03 | MPIPS precise slope candidate |
| M15 | MPIPS precise | 1.5 | MPIPS precise slope candidate |
| M20 | MPIPS precise | 2.0 | MPIPS precise slope candidate |
| M30 | MPIPS precise | 3.0 | MPIPS precise slope candidate |
| F103 | pinned Fiji Flat | 1.03 | Fiji Flat substitution and slope |
| F15 | pinned Fiji Flat | 1.5 | Fiji Flat substitution and slope |
| F20 | pinned Fiji Flat | 2.0 | Fiji Flat substitution and slope |
| F30 | pinned Fiji Flat | 3.0 | Fiji Flat substitution and slope |

  Total intended primary candidates: **10**. FastFlat is excluded from I-5A;
  it remains separately plan-able future work because production currently uses
  `fast=false` and I-4C0 established Flat and FastFlat as materially different
  algorithms.
- Freeze, for every mapped raw input, all feasible non-CLAHE processing state:
  raw radiograph; dark/gain/calibration inputs; calibration fingerprint;
  detector mode; FFC; crop/rotation; normalization; threshold method and
  enable state; inversion; contrast enhancement; initial denoise; final
  denoise; corrected Hybrid Median; and all remaining pipeline defaults.
  Threshold MUST NOT vary.
- For MPIPS candidates, differences MUST be limited to `use_clahe` and/or
  `clahe_max_slope`. For Fiji candidates, the only intended semantic
  substitution is the CLAHE operation plus candidate slope.
- Reuse the existing production orchestration as closely as possible. Use the
  existing configuration and `RadiographyPipeline` for MPIPS candidates; use
  `use_clahe=false` for C0; and use an isolated experiment-only runtime
  substitution/injection around the CLAHE call for Fiji Flat. Do not modify
  production source to add an experiment hook, copy the complete pipeline, or
  duplicate substantial orchestration.
- Before the full matrix, run a bounded full-resolution Fiji Flat sentinel with
  one unambiguous mapped case and preferably F15. Record input shape/dtype,
  runtime, peak-memory observation when practically available, output
  shape/dtype, output SHA256, and success/failure. Do not resize or downsample.
- Reconcile geometry only with justified lossless integer crop, pad, integer
  translation, orientation correction, or valid-mask intersection. Never use
  resize, interpolation, non-integer warp, or arbitrary registration
  deformation. Mark an untrustworthy case/candidate `NON-COMPARABLE` and record
  why; do not force comparison.
- Reuse `mpips.iqa.analyze_structural_preservation` and the accepted six
  structural metrics:
  `edge_recall`, `gradient_energy_retention`, `informative_tile_count`,
  `lost_informative_tile_fraction`, `low_percentile_tile_retention`, and
  `informative_extreme_fraction`. Also retain Pearson alignment sanity and
  valid-overlap fraction. Do not redefine their semantics.
- For every comparable output record dtype, shape, min, max, mean, median,
  p01, p50, p99, zero-pixel fraction, `65535` saturation fraction for
  `uint16`, dynamic-range span, nonzero-pixel count, and deterministic ndarray
  SHA256.
- Pair every candidate by the same raw/calibration/reference identity. Report
  per-case deltas and aggregate count, mean, median, min/max or robust range,
  worst cases, and improving/degrading case counts relative to M06 and C0,
  separately for `Kepala`, `Tulang Belakang`, and all comparable cases.
- Inspect predeclared representative structures qualitatively: faint
  ear/peripheral soft tissue and hard foreground/background separation for
  `Kepala`; weak vertebral/rib/local structures and hard separation/clipping
  for `Tulang Belakang`. Use cases identified before candidate scoring. If
  unavailable, choose representatives by a deterministic rule unrelated to
  candidate performance. Qualitative inspection is non-clinical.
- Produce bounded evidence artifacts, without full-resolution image outputs:
  `artifacts/real-data-regression/clahe-semantic-parameter-ablation.md`,
  `.json`, `.csv`, and `.agents/evidence/clahe-real-radiograph-ablation.md`.
  JSON/CSV must contain the complete candidate × case matrix.

### Out of scope

- Any production change to `mpips/processing/imagej.py`,
  `mpips/pipelines/config.py`, `RadiographyPipeline`, filtering defaults,
  threshold behavior, contrast behavior, Hybrid Median behavior, CLAHE
  defaults, schema, DICOM conversion, API, workers, deployment, or
  dependencies.
- Changing `clahe_max_slope=0.6`, selecting a default, semantic migration,
  clinical validation, clinical reader study, or clinical/product verdict.
- Threshold × CLAHE combinations or any threshold variation.
- FastFlat, Circular Median work, generic experiment infrastructure, or
  production package-architecture changes.
- Resampling-based geometry reconciliation, guessed identity, unmatched
  samples, arbitrary composite/weighted quality scores, or selecting a winner
  from one metric.
- Google Drive mutation; committing, renaming, moving, deleting, uploading,
  or overwriting external data; committing raw/reference radiograph binaries
  or thumbnails.
- New JDK download, system Java installation, sudo, package-manager install,
  dependency addition, floating Fiji version, vendoring third-party code, or
  CLAHE reimplementation.

### Preserved behavior and boundaries

- All current production behavior, defaults, configuration, schema, tests,
  reference tooling, and converter bytes remain unchanged.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical with SHA256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Fiji remains experimental/reference-only and never becomes a production
  dependency.
- Generated full-resolution images remain local/temporary unless repository
  governance later authorizes a non-sensitive representation. Commit only
  hashes, paths/identities, numeric measurements, text/CSV/JSON evidence, and
  bounded experimental source code.
- Structural metrics and qualitative observations are not clinical verdicts;
  reference-quality TIFFs are comparison baselines, not asserted absolute
  clinical ground truth.

## Dependencies and assumptions

### Dependencies

- The accepted baseline, prior task revisions, accepted artifacts, and current
  production pipeline remain readable.
- Read-only access to the authorized real-radiograph source collection and
  accepted reference-quality images is available to the future Executor.
- The retained Fiji environment and pinned provenance documented in
  `scripts/imagej_reference/README.md` are available without new installation.
- Existing structural-IQA implementation and repository evidence conventions
  remain available.

### Approved assumptions

- Accepted reference TIFFs may not all have an unambiguous raw NPZ source;
  mapping feasibility must be demonstrated rather than assumed.
- Existing characterization identity rules may be reused only when they remain
  deterministic and evidence-backed.
- `fast=false` is the current production semantic boundary; this does not
  authorize FastFlat execution in I-5A.

### Remaining approval requirements

- No image-quality, semantic, or production-default decision is approved by
  this task.
- A later Fiji/MPIPS semantic selection requires explicit approval, fidelity
  implementation planning, config/schema/migration planning, independent
  review, and a new validated implementation task.
- Any new dependency/runtime, production hook, resampling requirement,
  privacy/licensing concern, or material scope/architecture decision requires
  return to planning.
- No deployment, release, or external publication is authorized by this task.

## Required capabilities

- Repository read/write and local command execution.
- Read-only access to the authorized radiograph data source.
- Existing image-array, TIFF/NPZ, hashing, and IQA measurement capability.
- The retained pinned Fiji reference runtime, with no new installation.

## Execution constraints

- The primary matrix MUST be exactly C0, M06, M103, M15, M20, M30, F103, F15,
  F20, and F30. Do not add FastFlat.
- The raw-to-reference mapping, both-anatomy coverage, and minimum case count
  are hard feasibility gates. If either anatomy cannot be represented or
  trustworthy mapping is insufficient, stop with `PLANNING REQUIRED`.
- Record an immutable pipeline-freeze/fingerprint per case and prove that
  candidate differences are CLAHE-only within feasible isolation.
- Use the existing production pipeline/runtime path and narrow non-production
  injection. If exact CLAHE-only isolation requires production modification or
  substantial pipeline duplication, stop with `PLANNING REQUIRED`.
- Execute the full-resolution Fiji sentinel before the full matrix. If it
  cannot run reliably in the authorized environment/resources, stop with
  `PLANNING REQUIRED`; ROI-only evidence is supplemental and cannot decide
  full-image semantics.
- Require exact deterministic rerun ndarray equality/hash stability for C0,
  one MPIPS candidate, and one Fiji Flat candidate. Material nondeterminism is
  a planning stop.
- Do not treat execution-safe slope floors as quality recommendations.
- Do not create a weighted quality score or clinical conclusion. If metrics
  conflict, report the trade-off.

## Acceptance criteria

- [ ] The task remains `Validated/Published` and is governed by the immutable
      publication revision reported to the Executor.
- [ ] A deterministic raw → calibration → logical identity → accepted TIFF
      mapping inventory is recorded, with rationale and all exclusions.
- [ ] Meaningful execution contains more than one logical case and both
      accepted anatomy groups; no guessed or unmatched sample substitutes for a
      failed feasibility gate.
- [ ] The primary candidate matrix is exactly the ten IDs specified above;
      FastFlat and Threshold × CLAHE are explicitly absent.
- [ ] All feasible non-CLAHE state is frozen and recorded for every mapped
      input; threshold method and enable state do not vary.
- [ ] MPIPS candidates reuse existing `RadiographyPipeline` behavior with only
      the authorized CLAHE difference, and Fiji candidates substitute only the
      pinned Flat operation plus slope in an experiment-only boundary.
- [ ] The full-resolution Fiji sentinel records all required feasibility
      observations, with no silent resizing or downsampling.
- [ ] Comparable cases use only accepted lossless geometry rules; every
      excluded/non-comparable case has a recorded reason.
- [ ] The six accepted structural metrics, Pearson alignment sanity, and
      valid-overlap fraction are reported without semantic redefinition.
- [ ] Required intensity/clipping measurements and deterministic output hashes
      are reported for every comparable candidate output.
- [ ] Per-case paired deltas, anatomy-specific and all-case aggregates,
      outliers/worst cases, and improvement/degradation counts versus M06 and
      C0 are present.
- [ ] Qualitative observations use predeclared representatives and are
      non-clinical and not candidate-driven or cherry-picked.
- [ ] The decision-support outcome is one of: `EVIDENCE FAVORS LEGACY MPIPS
      SEMANTICS`, `EVIDENCE FAVORS FUTURE FIJI FLAT MIGRATION`, `NO DOMINANT
      CANDIDATE / TRADE-OFF UNRESOLVED`, or `EVIDENCE INSUFFICIENT`; no
      arbitrary weighted score or one-metric winner is used.
- [ ] Reports are internally consistent and include provenance, mapping,
      exclusions, candidate definitions, freeze contract, Fiji feasibility,
      metrics, paired results, qualitative observations, limitations, outcome,
      and an explicit production HOLD.
- [ ] No production/default/config/schema/test behavior, dependency, Drive
      content, or radiograph binary is changed or committed; the protected
      converter hash remains exact.

## Verification requirements

### Required checks

- Verify raw/reference mapping inventory, comparable/non-comparable counts,
  anatomy coverage, and mapping rationale.
- Verify every executed candidate × case combination, exclusions/errors,
  full-resolution Fiji feasibility, and deterministic sentinel reruns.
- Verify six structural metrics, alignment/overlap, intensity/clipping
  measurements, paired deltas, anatomy-specific aggregates, worst cases, and
  predeclared qualitative observations.
- Verify JSON validity, CSV/report consistency, deterministic hashes,
  protected Fiji provenance, and the protected converter SHA256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Run `tests/test_iqa_safety.py`, `git diff --check`, and relevant static/style
  checks for any added Python helper. If a helper is added, run the repository
  conventions for Black, Flake8, and mypy on affected surfaces.
- Full-repository pytest is not automatically required for evidence-only work
  unless source/testing changes make it relevant. Local results must not be
  represented as CI.

### Required evidence

The Executor MUST report the exact governing task revision, implementation
baseline, implementation/evidence revision, commands actually run, observed
results, all exclusions and limitations, local-versus-CI provenance, and any
stop condition. Missing, skipped, or unavailable checks must be stated.

## Stop conditions

The Executor MUST stop with `PLANNING REQUIRED` when:

- trustworthy raw → reference identity cannot be established sufficiently;
- both anatomy groups or more than one meaningful logical case cannot be
  represented;
- raw/reference access is unavailable;
- full-resolution Fiji Flat cannot execute reliably;
- exact CLAHE-only isolation requires modifying production architecture or
  duplicating substantial pipeline logic;
- the experiment needs a new dependency, runtime, download, or system install;
- reference provenance is uncertain;
- candidate generation is materially nondeterministic;
- geometry comparison requires resampling;
- clinical/product judgment or semantic selection is required;
- a privacy, licensing, data-handling, security, or operational concern exceeds
  this bounded objective; or
- any required scope expands beyond controlled experimentation.

Individual bad cases may be `NON-COMPARABLE` when the overall feasibility gate
remains satisfied. Systematic failure returns to planning. The Executor MUST
NOT silently reinterpret this task into remediation, migration, default
selection, or release work.

## Side-effect authorization

This task authorizes only the bounded future experimental work described above.
It authorizes read-only repository/history and radiograph-data access, reuse of
the retained Fiji environment, temporary local candidate generation, bounded
experimental helper(s) when necessary, lightweight text/CSV/JSON evidence,
normal commit(s), and push to `origin/refactor/package-boundaries`.

It does NOT authorize Google Drive mutation; committing radiograph binaries;
production, config, default, schema, threshold, test, converter, deployment,
dependency, or reference-tooling changes; new runtime installation; force-push;
history rewrite; `main` mutation; tag mutation; deployment; release; or secret
access/disclosure.

### Explicitly authorized side effects

- Read-only access to the authorized external radiograph data.
- Temporary local full-resolution candidate images and measurements.
- The bounded evidence files and a narrowly scoped experiment helper only when
  required by the acceptance criteria.
- Normal commit and push of only authorized experiment/evidence changes to
  `refactor/package-boundaries`.

## Expected terminal outcome

### Review Required

After the bounded evidence is complete, the Executor must stop at `Review
Required` and report the exact task revision, implementation/evidence revision,
baseline, observed verification, exclusions, limitations, and production HOLD.
Implementation acceptance remains separate from release authorization.

### Planning Required

If a task-specific stop condition is reached, report the exact blocking
evidence and return to the earliest affected planning or approval boundary.
