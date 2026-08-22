---
title: MPIPS I-5A Real-Radiograph CLAHE Ablation — Bounded Cohort Addendum
document_id: AGENT-TASK-MPIPS-I5A-CLAHE-BOUNDED-COHORT-ADDENDUM
version: 1.0
status: Validated/Published
language: en-US
scope:
  - bounded real-radiograph CLAHE ablation cohort
  - exploratory structural-preservation decision support
authority_note: This addendum changes only I-5A corpus breadth and primary sampling. All other original-task requirements and controls remain authoritative.
---

# Executable Addendum

## Task identity and joint authority

This is a supplementary governing addendum for the active I-5A task:

- Original task: `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation.md`
  @ `a1585bbf1b1710d955595703f7821526b3073b23`
- Accepted implementation/evidence baseline:
  `15305dd000538aaf3459e4124975ac17892c4d31`

Future I-5A execution is governed jointly by the original task at the
immutable revision above and this immutable addendum publication revision.
This addendum overrides only corpus breadth and primary sampling requirements.
All other original-task requirements, acceptance criteria, stop conditions,
scientific controls, and side-effect boundaries remain authoritative.

## Rationale and bounded primary cohort

The original task requires more than one logical case, both `Kepala` and
`Tulang Belakang`, and multiple independent mapped cases; multiple goats and
acquisitions are preferred. It does not require all 38 previously comparable
images. Running 19 `Kepala` plus 19 `Tulang Belakang` identities would produce
380 full candidate/image combinations and is unnecessary for this bounded
semantic-decision experiment.

The amended I-5A primary cohort is exactly:

- 3 `Kepala` identities;
- 3 `Tulang Belakang` identities;
- 6 logical identities total.

Each selected identity MUST be deterministically mapped, unambiguous, eligible
under the original raw-to-reference mapping rules, and capable of paired
evaluation under the original geometry rules. An ambiguous or technically
excluded identity does not count toward the six.

## Deterministic selection

Build the eligible raw-to-reference mapping inventory before candidate scoring.
Within each anatomy, sort eligible mapped identities by the repository's
established numeric/logical acquisition and goat identity ordering, not by
lexicographic accidents. Choose the first three eligible identities in each
anatomy. If an identity is technically excluded before candidate scoring,
advance to the next eligible identity in that same anatomy.

Record the exact six identities before inspecting aggregate candidate
performance. Selection MUST be independent of candidate metrics or visual
appearance. If an already-completed checkpoint identity belongs to this
deterministic cohort and satisfies all original gates, reuse it without
recomputation.

## Primary candidate matrix

Every selected identity executes exactly the original ten candidates:

`C0`, `M06`, `M103`, `M15`, `M20`, `M30`, `F103`, `F15`, `F20`, `F30`.

The intended primary workload is exactly 6 × 10 = 60 candidate/image
combinations before technical exclusions. FastFlat, extra slopes, and
threshold variants are excluded.

Completed checkpoint outputs may be reused only when they were produced under
the exact original governing task, the pipeline freeze remains valid, the
candidate matrix is exact, and determinism, reference, and other original
validation gates passed. Completed identities outside the final six-case
cohort may remain in temporary local evidence but MUST NOT influence selection
or the primary six-case aggregate; if retained, classify them as
`SUPPLEMENTAL / OUTSIDE PRIMARY BOUNDED COHORT`.

## Preserved controls and evidence

This addendum does not weaken or replace any original control, including:

- CLAHE-only isolation, pipeline freeze, and fingerprints;
- the full-resolution pinned-Fiji sentinel;
- determinism and pinned Fiji authority;
- lossless geometry reconciliation;
- structural-IQA, intensity, and clipping metrics;
- per-case paired analysis and non-cherry-picked qualitative inspection;
- no weighted quality score and no clinical conclusion;
- production/default `HOLD`.

The complete original matrix, evidence artifacts, validation gates, and
non-comparability rules remain required for the bounded cohort.

## Decision-strength and corpus boundary

The six-case result is exploratory decision-support evidence, not
population-level validation. Allowed outcomes remain:

- evidence favors legacy MPIPS semantics;
- evidence favors future Fiji Flat migration;
- no dominant candidate / trade-off unresolved;
- evidence insufficient.

If candidate behavior is materially inconsistent across the six cases or the
two anatomy groups, do not escalate automatically to the remaining 32
identities. Use the unresolved or insufficient outcome and return to
Planner/Reviewer. Completion of all 38 identities is NOT an I-5A acceptance
criterion. The remaining eligible corpus is optional confirmatory work only,
requiring separate Planner/Reviewer authorization.

## Protected and unchanged scope

No production CLAHE, pipeline, threshold, Hybrid Median, schema, default,
test, dependency, converter, Drive-data, or reference-tool changes are
authorized by this addendum. `clahe_max_slope = 0.6` remains unchanged. The
protected converter SHA256 remains
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

## Future execution terminal condition

After this addendum has been independently reviewed, the Executor MUST load
the original task and this exact addendum revision, determine the deterministic
six-case cohort, reuse valid completed checkpoints, process only missing cohort
identities and candidates, and stop after the six-case primary cohort and all
original evidence requirements are complete. The Executor MUST NOT continue to
the remaining corpus without separate authorization and MUST stop at
`Review Required`.

This addendum publication does not authorize resuming candidate processing in
the publication turn.
