---
title: MPIPS I-5B Real-Radiograph Threshold × CLAHE Interaction Ablation
document_id: AGENT-TASK-MPIPS-I5B-THRESHOLD-CLAHE-INTERACTION
version: 1.1
status: Validated/Published
language: en-US
scope:
  - bounded real-radiograph threshold characterization
  - threshold × current-MPIPS-CLAHE interaction decision support
authority_note: This task authorizes only the bounded exploratory experiment and evidence described below. It does not authorize production change, stage reordering, release, or clinical conclusions.
---

# Executable Task

## Task identity

**Task title:** MPIPS I-5B Real-Radiograph Threshold × CLAHE Interaction Ablation

**Task path:** `.agents/tasks/real-radiograph-threshold-clahe-interaction-ablation.md`

**Task contract state:** `Validated/Published`

**Delivery objective / Work Package / MVP:** I-5 threshold and CLAHE decision-support experiments

**Owner / designated planning authority:** MPIPS Planner/Reviewer

## Delivery context

Accepted I-5A evidence found **NO DOMINANT CANDIDATE / TRADE-OFF UNRESOLVED** while isolating CLAHE with Threshold held at production behavior. This successor experiment determines, on exactly the same six-case bounded cohort, whether Threshold has structural value, whether current MPIPS CLAHE has structural value, and whether CLAHE's effect materially depends on Threshold behavior.

The observed pipeline order is:

```text
upstream preprocessing → threshold detection/separation → invert → contrast enhancement → CLAHE → downstream processing / Hybrid Median
```

Threshold is therefore upstream of CLAHE and can change the distribution presented to CLAHE. This task is exploratory decision support, not population-level validation.

## Baseline and task revision

**Implementation baseline:** `fe164f7c39697765f1c34b876c080efb34ffe36f`

**Task revision:** resolved by the immutable publication commit containing this file.

**Prior accepted I-5A task:** `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation.md @ a1585bbf1b1710d955595703f7821526b3073b23`

**Prior accepted I-5A bounded-cohort addendum:** `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation-addendum.md @ 7e5d28c0a1cad2c70fec57d634bbdc72fd62a07e`

**Accepted I-5A implementation/evidence baseline:** `fe164f7c39697765f1c34b876c080efb34ffe36f`

## Objective

Determine on the accepted six-identity real-radiograph cohort:

1. whether the current Threshold stage provides structural value;
2. whether the current MPIPS CLAHE stage provides structural value; and
3. whether the structural effect of CLAHE materially depends on Threshold behavior.

Hold every non-Threshold/non-CLAHE pipeline stage constant and leave production configuration unchanged.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- `.agents/tasks/_template.md`
- Accepted I-5A evidence: `.agents/evidence/clahe-real-radiograph-ablation.md`
- Accepted I-5A artifacts:
  `artifacts/real-data-regression/clahe-semantic-parameter-ablation.md`,
  `clahe-semantic-parameter-ablation.json`, and
  `clahe-semantic-parameter-ablation.csv`
- Accepted baseline `fe164f7c39697765f1c34b876c080efb34ffe36f`

### Requirement traceability

- I-5A unresolved CLAHE decision support → this bounded Threshold × CLAHE follow-up.
- Accepted real-radiograph mapping, geometry, structural-IQA, and evidence rules → I-5A task/addendum and accepted artifacts.
- Current implementation reality → `mpips/pipelines/config.py`, `mpips/pipelines/radiography.py`, `mpips/processing/thresholding.py`, and `mpips/processing/imagej.py`.

## Scope

### In scope

- Reuse exactly the accepted I-5A bounded primary cohort:
  - `Kepala`: `I-1-1`, `I-1-2`, `I-1-4`;
  - `Tulang Belakang`: `I-1-1`, `I-1-2`, `I-1-3`.
- Characterize all seven supported threshold configurations before using reference-quality or candidate results to select alternatives:
  `none`, `auto`, `valley`, `otsu`, `knee`, `percentile_25`, `secondary_peak`.
- Run the exact Phase-B four-threshold-state × three-CLAHE-state matrix defined below.
- Reuse valid accepted I-5A rows only after proving exact identity and pipeline equivalence.
- Produce bounded textual, JSON, and CSV evidence with hashes, metrics, provenance, and decision-support classifications.

### Out of scope

- Production config/default/schema/API changes, deployment, release, or DICOM converter changes.
- Threshold algorithm or CLAHE algorithm implementation changes.
- Stage reordering, broad pipeline permutation search, or automatic expansion to the 38-image corpus.
- Fiji CLAHE, FastFlat, Circular Median remediation, wavelet/FFC/geometry/contrast/Hybrid Median changes.
- Clinical or diagnostic claims, population-level validation, weighted composite scores, or a single-metric winner.
- New dependencies, runtime installation, reference-tool changes, or external-data mutation.

### Preserved behavior and boundaries

- Production remains:

  ```text
  use_threshold = True
  threshold_method = "auto"
  use_clahe = True
  clahe_blocksize = 127
  clahe_histogram_bins = 256
  clahe_max_slope = 0.6
  clahe_fast = False
  clahe_composite = True
  ```

- Freeze raw radiograph; gain/dark/flat and calibration fingerprint; detector mode; wavelet denoise; FFC; crop/rotate/geometry; normalization; inversion; contrast enhancement/equalization; final denoise; Hybrid Median; output dtype; geometry reconciliation; and IQA definitions.
- Do not change stage ordering. External radiograph/reference data is read-only.
- Preserve `mpips/conversion/tiff_json_to_dcm.py` byte-for-byte with SHA256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Commit metadata, hashes, metrics, and bounded textual/machine-readable evidence only; do not commit NPZ/TIFF radiographs, generated full-resolution images, thumbnails, arrays, or Java/JDK/JAR/class binaries.

## Experimental design

### Phase A — threshold characterization

For every image × requested threshold method, record at minimum:

- requested method and actual effective behavior;
- actual selected/fallback branch and numeric threshold where applicable;
- threshold content-mask fraction and background fraction;
- threshold mask SHA256 and threshold-stage output SHA256;
- shape, dtype, execution/fallback condition;
- distance from AUTO mask;
- whether output is identical to AUTO or another requested method.

For `none`, explicitly record that separation is disabled and numeric threshold/mask semantics are not applicable. Do not report it as a numeric method.

Audit `secondary_peak`: if no valid secondary peak exists, record the implementation's actual fallback and do not label it successful secondary-peak semantics. This distinction is required in machine-readable evidence.

### Deterministic alternative selection

Choose `T_ALT1` and `T_ALT2` only from Phase-A threshold-stage behavior, without structural IQA, final candidate scores, visual attractiveness, or CLAHE results.

For each eligible alternative, compute mean mask disagreement fraction versus `T_AUTO` across all six cases. Exclude a method only if it cannot produce a valid governed threshold-stage result or its threshold-stage output is identical to AUTO for all six cases. Rank by descending mean disagreement, breaking ties in this fixed order: `valley`, `otsu`, `knee`, `percentile_25`, `secondary_peak`.

Select the first ranked method as `T_ALT1`. Select the next ranked method whose threshold-stage output is not identical to `T_ALT1` across all six cases as `T_ALT2`. If fewer than two distinct eligible alternatives remain, stop before Phase B with `PLANNING REQUIRED` and complete Phase-A evidence.

### Phase B — exact primary matrix

Use exactly these four threshold states:

| State | Meaning |
|---|---|
| `T_NONE` | threshold disabled |
| `T_AUTO` | current production threshold behavior |
| `T_ALT1` | first deterministic Phase-A alternative |
| `T_ALT2` | second deterministic Phase-A alternative |

Use exactly these three CLAHE states:

| State | Meaning |
|---|---|
| `C0` | CLAHE disabled |
| `M06` | current MPIPS precise CLAHE, slope `0.6` |
| `M15` | current MPIPS precise CLAHE, slope `1.5` |

For active CLAHE, retain `blocksize=127`, `histogram_bins=256`, `fast=False`, and `composite=True`. Do not add other slopes, Fiji variants, or FastFlat.

The exact matrix is `4 × 3 × 6 = 72` logical candidate × image combinations, with IDs:

```text
T_NONE_C0   T_NONE_M06   T_NONE_M15
T_AUTO_C0   T_AUTO_M06   T_AUTO_M15
T_ALT1_C0   T_ALT1_M06   T_ALT1_M15
T_ALT2_C0   T_ALT2_M06   T_ALT2_M15
```

Record the actual methods selected for ALT1 and ALT2 in every relevant row.

### I-5A reuse

The accepted I-5A rows for `T_AUTO_C0`, `T_AUTO_M06`, and `T_AUTO_M15` may be reused for all six identities only after proving exact raw/reference identity, calibration fingerprint, upstream processing, AUTO behavior, downstream processing, CLAHE definition, output hashes, and pipeline freeze. Tie each reused row unambiguously to accepted evidence. The Phase-B matrix always has 72 logical rows. Define `reused_rows = R`, where `0 <= R <= 18`, and `newly_computed_rows = 72 - reused_rows`. For every reused row no new computation is required; every row whose reuse cannot be proven must be recomputed. Thus the best case/minimum new computation is 54 rows when all 18 reuse proofs succeed, and the worst case/maximum new computation is 72 rows when none can be reused. Do not weaken any reuse proof to reduce compute; computational efficiency is subordinate to evidence integrity.

### Reference and metrics

Reuse accepted mapping and geometry rules. Permit only previously accepted lossless reconciliation; never resize, interpolate, warp, or resample. Classify unreconcilable cases `NON-COMPARABLE` with a reason.

For every Phase-B result retain the accepted metrics: `edge_recall`, `gradient_energy_retention`, `informative_tile_count`, `lost_informative_tile_fraction`, `low_percentile_tile_retention`, and `informative_extreme_fraction`, plus Pearson alignment sanity and valid-overlap fraction.

Also record dtype, shape, min, max, mean, median, p01, p50, p99, zero-pixel fraction, `uint16` 65535 saturation fraction, dynamic-range span, nonzero count, and ndarray SHA256.

Record elapsed runtime for new candidates and peak memory/RSS for representative full-resolution runs where practical. Performance is evidence, not an optimization target.

## Analysis and classifications

Analyze separately for `Kepala`, `Tulang Belakang`, and all six cases.

- **Threshold relevance:** compare `T_NONE` vs `T_AUTO` under each of `C0`, `M06`, and `M15`; do not infer value from one CLAHE condition.
- **CLAHE relevance:** within every threshold state compare `C0` vs `M06`, `C0` vs `M15`, and `M06` vs `M15`.
- **Interaction:** for each structural metric and case report contrasts such as `(M06−C0 under Tx) − (M06−C0 under T_AUTO)` and the equivalent M15 contrast for `T_NONE`, `T_ALT1`, and `T_ALT2`. Report direction, magnitude, anatomy grouping, median/range or equivalent transparent summaries, sign consistency, and worst-case degradation.

Do not use arbitrary weights or collapse conflicting metrics, cases, or anatomy groups into a winner. Produce three independent classifications:

- Threshold: `THRESHOLD VALUE SUPPORTED`, `THRESHOLD VALUE NOT SUPPORTED`, or `THRESHOLD RELEVANCE UNRESOLVED`.
- CLAHE: `CLAHE VALUE SUPPORTED`, `CLAHE VALUE NOT SUPPORTED`, or `CLAHE RELEVANCE UNRESOLVED`.
- Interaction: `INTERACTION SIGNAL PRESENT — STAGE-ORDER FOLLOW-UP JUSTIFIED`, `NO MATERIAL INTERACTION SIGNAL OBSERVED`, or `INTERACTION / TRADE-OFF UNRESOLVED`.

These are decision-support labels only. They must not trigger production changes. A future Stage-Order Ablation requires a new validated task and must not be performed here.

## Required evidence artifacts

Future execution must produce only these bounded artifacts unless a technically necessary addition is explicitly justified:

```text
artifacts/real-data-regression/threshold-clahe-interaction-ablation.md
artifacts/real-data-regression/threshold-clahe-interaction-ablation.json
artifacts/real-data-regression/threshold-clahe-interaction-ablation.csv
.agents/evidence/threshold-clahe-interaction-ablation.md
```

An experiment-only helper such as `scripts/threshold_clahe_interaction_ablation.py` may be added only if necessary, orchestrates existing canonical components, duplicates no production algorithm, changes no canonical semantics, and does not become a production dependency. No helper is authorized by this publication turn.

The JSON must include governing task revision, implementation baseline, I-5A accepted baseline, six identities and anatomy counts, calibration fingerprints, production snapshot, non-variable pipeline fingerprint, Phase-A characterization, requested/actual semantics and fallbacks, thresholds, masks and disagreements, ALT selection proof, exact matrix, reused/new rows, determinism, structural/IQA and intensity metrics, grouped aggregates, paired deltas, interaction contrasts, worst cases, all three classifications, limitations, production HOLD, and converter hash.

## Acceptance criteria

- [ ] Exactly six accepted I-5A identities are retained and no 38-image expansion occurs.
- [ ] All seven Phase-A threshold configurations are characterized.
- [ ] Requested versus actual semantics, including secondary-peak fallback, are machine-readable.
- [ ] ALT1/ALT2 selection is deterministic and free of reference-IQA/candidate-score leakage.
- [ ] Exactly four threshold states and exactly three CLAHE states are established.
- [ ] The Phase-B logical matrix is exactly 72 combinations.
- [ ] Valid I-5A rows are reused only after exact identity/fingerprint/pipeline/output-equivalence proof; at most 18 rows may be reused. The Phase-B matrix always contains 72 logical rows, and `newly_computed_rows = 72 - reused_rows`, ranging from 54 when all 18 reuse proofs succeed to 72 when none can be reused.
- [ ] All non-Threshold/non-CLAHE stages, geometry, output contract, and IQA definitions are frozen.
- [ ] All six structural metrics, Pearson sanity, overlap, and intensity/clipping metrics are present.
- [ ] Results are reported by both anatomy groups and all six cases.
- [ ] Threshold relevance, CLAHE relevance, and interaction each receive one bounded classification.
- [ ] No weighted score, clinical claim, population-level claim, automatic corpus expansion, or single-metric winner is used.
- [ ] Stage reordering and Fiji are excluded.
- [ ] Production remains on HOLD with current defaults; no production, API, schema, reference-tool, dependency, deployment, or release change is made.
- [ ] The protected converter bytes/hash are unchanged and no radiograph/runtime binaries are committed.

## Verification requirements

Before review, verify as applicable:

- JSON parses;
- CSV ↔ JSON and Markdown ↔ JSON are consistent;
- six-case cohort, Phase-A methods, ALT proof, and 4 × 3 × 6 matrix are complete;
- reused-row hashes and identity/fingerprint equivalence are valid;
- required targeted check `tests/test_iqa_safety.py` passes;
- if a helper is authorized and added: Black, Flake8, mypy, and focused syntax/import checks;
- `git diff --check` passes;
- converter SHA256 equals `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`;
- GitHub Actions status is checked separately and local checks are not described as CI.

## Dependencies and assumptions

### Dependencies

- Accepted I-5A task/addendum, evidence, artifacts, and baseline remain readable.
- Read-only access to the authorized real-radiograph/reference collection remains available.
- Existing mapping, geometry, pipeline, threshold, CLAHE, and IQA implementations remain usable without modification.

### Approved assumptions

- I-5A identity mapping and reference provenance may be reused only when hashes and fingerprints prove equivalence.
- Existing canonical threshold behavior is the observed implementation authority for Phase A; no threshold semantics may be invented.

### Remaining approval requirements

- Planner/Reviewer review is required after execution or any stop condition.
- Any stage-order experiment, production change, release, deployment, dependency/runtime installation, external-data mutation, or scope expansion requires a new validated task and applicable approval.

## Stop conditions and terminal outcomes

Return `PLANNING REQUIRED` rather than improvising if fewer than six governed mapped cases remain usable; raw/reference identity cannot be established; fewer than two distinct valid ALT methods remain; Phase B requires production-code changes, new dependencies, or architecture changes; canonical Threshold/CLAHE behavior cannot be isolated; geometry cannot be reconciled under accepted rules; external data is not read-only; converter integrity fails; or the implementation baseline materially changes.

On a valid completed execution with all evidence, stop at `Review Required`. This task authorizes no deployment, release, production modification, stage reordering, or automatic follow-up experiment.

## Explicitly authorized side effects

Future execution may create only the bounded evidence artifacts and, if technically necessary, the narrow experiment-only helper described above. It may not mutate production code/configuration/defaults/schema/tests/reference tooling, external data, deployment state, or release state. Publication of this task is the only side effect authorized in the planning turn.
