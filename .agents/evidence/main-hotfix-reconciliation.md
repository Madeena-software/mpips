# Main Hotfix Reconciliation Evidence

## Phase 1 — Upstream Hotfix Impact Mapping

### Governing identity

- Governing task publication: `32edb5b429b29a1dc6183727a6af21fb9a5fce27`
- Accepted ImageJ/Fiji baseline: `a4a5c16881e589154680f0606c849e2a4514041f`
- Refactor implementation baseline: `a4a5c16881e589154680f0606c849e2a4514041f`
- Frozen main: `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`
- Known merge base: `fec5695048acbc3ce95d0a658032ec3701b6e045`
- Pre-execution HEAD: `32edb5b429b29a1dc6183727a6af21fb9a5fce27`
- Branch: `refactor/package-boundaries`
- `origin/refactor/package-boundaries`: `32edb5b429b29a1dc6183727a6af21fb9a5fce27`
- Observed `origin/main`: `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd` (not newer than frozen baseline).

The pre-execution worktree was clean. All named commits resolved. The protected
converter SHA-256 was verified as
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

### Frozen range inventory

The exact range `fec5695048acbc3ce95d0a658032ec3701b6e045..203c6c65cf6d6b5a8df0271ab610ded950b8f9fd` contains 25 commits:

| # | SHA | Subject | Main paths / behavior classification |
|---:|---|---|---|
| 1 | `babfe33720f9d93d197eadae8b7c523633f090d4` | ci: add production DICOM E2E diagnostic | Diagnostic workflow/script/tests; infrastructure and test-only. |
| 2 | `3cdfe114436ce06b67eba3990a656306c2b0a48f` | fix: harden production DICOM E2E diagnostic | Diagnostic assertions and failure handling; infrastructure/test-only. |
| 3 | `2cf997cf1e5715727b22db2d616e7abe7ef8be56` | fix: classify diagnostic download failures | Diagnostic classification; infrastructure-only. |
| 4 | `f377f9d9a5653b6aeed4181719eab87a00e5d414` | fix: complete production DICOM diagnostic classification | Diagnostic classification and tests; infrastructure/test-only. |
| 5 | `9f06c13c91be8e6a3ff7eb2f0687d373425b10ee` | fix: finalize production DICOM diagnostic safeguards | Diagnostic safeguards; infrastructure/test-only. |
| 6 | `28258be60c81453223baeb163bb09aa5dc2867d2` | fix: preserve production diagnostic failure precedence | Diagnostic result precedence; infrastructure/test-only. |
| 7 | `55237df29160687b7b5f3771fefb28eff5a0a5c0` | fix: harden Drive download for production diagnostic | Download staging and diagnostics; infrastructure-only. |
| 8 | `6013ef86e06f4c1ddfe5e5228260804937a4dfe0` | ci: prepare multi-mode calibration promotion | Calibration-layout validator and deployment preparation; infrastructure/test-only. |
| 9 | `253360b08cda48d33dcf1c6434d8e372b289fdf5` | fix: harden multi-mode calibration preflight | Carrier/layout preflight; infrastructure/test-only. |
| 10 | `d175a6fa56ca32cf78007c39baff24075dbd5a0e` | fix: make camera metadata non-blocking for DICOM conversion | Removes camera-serial rejection from NPZ/workflow validation; runtime compatibility semantic. |
| 11 | `be7757160ef635e703f2e5b902854fe2831038c0` | test: prepare real thorax TRX validation | Manifest fixture and test; test-only. |
| 12 | `9414d5c5b894801bc7061458e200c3e3b8f14768` | ci: add guarded production calibration promotion | Promotion workflow/script/tests; infrastructure/test-only. |
| 13 | `5db4ba15132458cf4288a09fc94e6f6449d68af0` | fix: harden calibration promotion rollback verification | Rollback and manifest checks; infrastructure/test-only. |
| 14 | `096e8b4e391daa5d0c48006d96c4470c092a33a4` | fix: update .gitignore to include additional output directories | Repository hygiene; not applicable to runtime reconciliation. |
| 15 | `e6482cea4de2b0a45fcac61a0c3aee919b9b14fd` | fix: preserve calibration root during promotion | Promotion root/rollback and TRX validation script; infrastructure/test-only. |
| 16 | `92c8c167d2d537a1de5ae27db8958e8f46cd3b78` | fix: reject unsafe calibration remaps | Fixed-canvas remap coverage guard; canonical workflow runtime validation semantic. |
| 17 | `ec1aae0448a82e615fdc39ec6ebaa1fc2ec1089` | fix: preserve complete calibration grid extraction | Legacy extractor retains complete rectangular lattice; calibration semantic. |
| 18 | `870745f92326e4df845b0b7ac23cb86b514d823b` | fix: recover calibration lattice from border artifacts | Legacy border/partial-edge recovery; calibration semantic. |
| 19 | `6f495cccbfe372e6f3ff467888d602fb9dc1656c` | fix: recover complete calibration lattice symmetrically | Legacy symmetric lattice recovery and spurious-row handling; calibration semantic. |
| 20 | `ff2d0eba741f842b721735092649f1de3289c4ab` | ci: prepare validated trx calibration promotion | Carrier and validation workflow; infrastructure/test-only. |
| 21 | `b034401f9ae290407f3eb7159402bb12583e2a68` | fix: reject collapsed trx pipeline outputs | Exact-zero/nonzero/bbox/range gates in TRX validation; production validation/test-only, not universal runtime quality policy. |
| 22 | `e268bf0d8c8692b0e65e05dd5905595095db4d23` | fix: prevent destructive trx threshold separation | TRX threshold bypass, configured BED behavior, diagnostic override; runtime policy semantic in legacy pipeline. |
| 23 | `b3ed78d5077d8e4634c913939e5c28f8620679e9` | test: complete trx threshold bypass validation | TRX bypass validation; test-only plus legacy plumbing. |
| 24 | `91263f7db860d97414bc90731c8eaf898739c4b6` | fix: require validated trx pipeline for calibration promotion | Promotion prerequisite; infrastructure-only. |
| 25 | `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd` | ci: pin validated trx calibration carrier | Carrier ID/fingerprint pinning; infrastructure-only. |

### Behavior reconciliation table

| Upstream SHA / subject | Behavior/change | Category | Relevant to canonical refactor? / owner | Presence and conflict | Proposed disposition / rationale |
|---|---|---|---|---|---|
| `babfe337`, `3cdfe114`, `2cf997cf`, `f377f9d9`, `9f06c13c`, `28258be`, `55237df` diagnostic chain | Production DICOM E2E download, classification, precedence, and failure safeguards. | Production diagnostics | No runtime owner; `scripts/` and `.github/` only. | Not present as canonical runtime behavior; no semantic conflict. | **INFRA-ONLY**. Keep out of Phase 2; these validate deployment and external data access. |
| `6013ef8`, `253360b` | Multi-mode calibration layout/preflight and carrier metadata. | Promotion validation | No canonical processing owner. | Canonical calibration artifacts are consumed by workflow code, but promotion layout is external operational policy. | **INFRA-ONLY**. |
| `d175a6f` | Camera metadata becomes optional/non-blocking while detector/gain/shape checks remain. | Conversion/NPZ compatibility | `mpips/workflows/imager_pipeline/npz_io.py`, `batch.py`, `calibration.py`, and conversion worker/service. | Current refactor still rejects camera-serial disagreement in the shown canonical calibration/batch paths; current NPZ loaders accept optional camera mappings. | **REVIEW REQUIRED**. This is a concrete runtime compatibility decision, but it is separate from Otsu/TRX and needs its own bounded task or explicit Phase-2 inclusion. |
| `be77571` | Real TRX manifest fixture. | Test data | `tests/` and `artifacts/`. | No production semantic. | **TEST-ONLY**. |
| `9414d5c`, `5db4ba1`, `e6482ce`, `ff2d0eb`, `91263f7`, `203c6c6` | Guarded promotion, fingerprint/carrier pinning, rollback, runtime preflight, and validated-TRX prerequisites. | Production operations | No canonical runtime owner. | Not present in registered API path; intentionally operational. | **INFRA-ONLY**. Do not port deployment machinery. |
| `096e8b4` | Ignore generated promotion/output directories. | Repository operations | None. | No runtime effect. | **NOT APPLICABLE**. |
| `92c8c16` | Reject fixed-canvas remaps with low valid fraction or collapsed valid bounding box; preserve evidence for expanded canvas. | Calibration/runtime validation | `mpips/workflows/imager_pipeline/calibration.py`. | Canonical workflow lacks these frozen-main coverage constants/checks. | **SEPARATE TASK REQUIRED** with calibration reconciliation; not part of minimal image hotfix. |
| `ec1aae0`, `870745f`, `6f495cc` | Preserve complete grid; recover partial border rows/columns; reject spurious rows and recover symmetric lattice. | Calibration algorithm | Canonical `mpips/calibration/dotgrid/extract_grid.py`. | Current extractor groups contours and trims to modal row width; it does not contain the frozen-main lattice-recovery algorithm. Legacy implementation is under `mpips/engine`, which must not be copied wholesale. | **PLANNING REQUIRED — CALIBRATION RECONCILIATION MUST BE SEPARATED**. |
| `b034401` | Validation records exact-zero ratio, nonzero ratio, nonzero bbox, dynamic range, and first collapse stage for real TRX acceptance. | Known-data regression gate | `scripts/validate_real_trx_pipeline.py`, promotion tests. | No equivalent general gate in canonical processing; canonical output is produced by `RadiographyPipeline`. | **TEST-ONLY** plus **INFRA-ONLY** promotion gate. Do not make dataset thresholds universal image-quality rules. |
| `e268bf0`, `b3ed78d` | `threshold_method_for_detector`: TRX defaults to `none`; BED keeps configured method; explicit diagnostic override can force a method. | Runtime detector policy / validation | Policy belongs at `mpips/workflows/imager_pipeline/pipeline.py` or `mpips/pipelines/radiography.py`; mathematics belongs in `mpips/processing/thresholding.py`. | Current canonical `RadiographyPipeline.process()` accepts `detector_mode` but applies configured threshold identically to TRX and BED; no override/stage observer exists. | **REIMPLEMENT CANONICALLY** for policy, with a separate validation-only override. Do not teach low-level threshold math detector types. |
| `d175a6f` conversion edits | Camera metadata optionality propagates through NPZ loading and conversion. | Conversion/service | `mpips/conversion/service.py`, `worker.py`, workflow adapters. | Final-image-to-DICOM boundary is already present and protected; camera policy is the only possible semantic delta. | **REVIEW REQUIRED** / separate bounded compatibility decision. Protected converter is unchanged. |

### Otsu semantic contradiction

Canonical owner: `mpips/processing/thresholding.py`, `detect_threshold()`.

Current code uses the OpenCV contract backwards in both branches:

```python
_, threshold_otsu_uint16 = cv2.threshold(image_uint16, 0, 65535, flags)
```

OpenCV returns `(threshold_value, thresholded_image)`, so the current code stores
the thresholded image in `threshold_otsu_uint16`, divides the whole image by
65535, then takes the first pixel as the apparent scalar threshold. The uint16
path therefore returns either `0.0` or `1.0`-scale data from pixel zero rather
than the Otsu scalar in the uint16 domain. The float32 path has the same error
after conversion to uint16 and normalization.

Frozen main corrects this to:

```python
threshold_otsu_uint16, _ = cv2.threshold(...)
threshold_otsu = threshold_otsu_uint16 / 65535
```

For uint16 input the returned scalar must remain in the uint16 intensity domain
(and be passed to the method selector in that domain). For normalized float32
input, conversion to uint16 for OpenCV must be followed by scalar normalization
back to `[0, 1]`. The current first-pixel dependence can produce zero, causing
Otsu-selected separation to collapse all output to the background, or a
non-threshold scalar, making historical Otsu rows materially invalid.

Existing `tests/test_thresholding_processing.py` explicitly records `otsu == 0`
and does not test scalar-vs-image return semantics. Proposed Phase-2 regression
coverage, without implementing it here: scalar return; uint16-domain threshold;
normalized float32-domain threshold; independence from the first output pixel;
and deterministic repeated execution. The smallest candidate write surface is
`mpips/processing/thresholding.py` plus `tests/test_thresholding_processing.py`.

### Detector-specific threshold policy

Threshold mathematics remains detector-agnostic in
`mpips/processing/thresholding.py`. Detector policy belongs in the orchestration
boundary, preferably `mpips/pipelines/radiography.py` (or its workflow adapter
if the API contract must stay workflow-specific), because that layer already
receives `detector_mode` and owns sequencing. The current canonical pipeline
does not bypass threshold separation for TRX. BED must retain its configured
method. A diagnostic override is useful for controlled validation, but should
be validation-only plumbing and not a production default/API contract.

Smallest candidate Phase-2 policy surface: `mpips/pipelines/radiography.py`,
possibly `mpips/workflows/imager_pipeline/pipeline.py` if the adapter must carry
the explicit override, and focused tests in `tests/test_radiography_pipeline.py`
or `tests/test_config_characterization.py`. This is separate from the Otsu math
fix and must not broaden the low-level detector API unnecessarily.

### Stage observability and collapse validation

Frozen main’s `stage_observer` reports stages including `SOURCE_RAW`,
`DENOISED_RAW`, `FFC`, `REMAP`, `CROP_ROTATE`, `PRE_THRESHOLD`,
`THRESHOLD_SEPARATION`, `INVERT`, `CONTRAST`, `CLAHE`, `MEDIAN`, `REMAP_MASK`,
and `FINAL_IMAGE`, with shape, dtype, ranges, percentiles, zero/nonzero ratios,
and a nonzero bounding box. In the frozen range this is attached to the legacy
pipeline and real-TRX diagnostic validation. The canonical pipeline has no
observer hook, and the current API does not require per-stage telemetry.

Disposition: **VALIDATION-ONLY / SEPARATE OBSERVABILITY CONCERN**. Do not port
the instrumentation into production processing in Phase 2. If needed later,
add a separately approved opt-in diagnostic interface with bounded cost and no
change to default image semantics.

The exact-zero ratio, nonzero ratio, bbox, and dynamic-range checks are
**KNOWN-DATA REGRESSION GATES** for the pinned real-TRX acceptance workflow.
They are not general clinical/image-quality rules. Keep them in diagnostic
scripts, tests, and the production promotion gate; do not add universal zero
floors to `mpips/processing`.

### Calibration reconciliation

The frozen calibration changes address border artifacts, partial edge rows and
columns, complete/symmetric lattice recovery, spurious-row rejection, and safe
remap coverage. Current canonical `mpips/calibration/dotgrid/extract_grid.py`
uses contour grouping plus modal-width trimming; it does not implement those
semantics. Current runtime remapping is exposed through canonical workflow
adapters, but the frozen lattice extractor is in legacy `mpips/engine` paths.

Disposition: **PLANNING REQUIRED — CALIBRATION RECONCILIATION MUST BE
SEPARATED**. Do not copy `mpips/engine/calibration/**`. A later task must map
the required behavior into `mpips/calibration/**`, define fixtures for border and
partial-edge cases, and separately reconcile the fixed-canvas remap coverage
guard. Calibration is not a safely bounded Phase-2 image hotfix.

### Conversion / worker / DICOM boundary

The frozen conversion changes are limited to camera metadata optionality in the
worker/service/workflow validation path. The canonical flow already separates
processed TIFF/final image generation from parent-side DICOM conversion,
enrichment, and structural validation (`mpips/conversion/service.py`,
`mpips/conversion/worker.py`, and `mpips/conversion/validation.py`). Existing
tests validate DICOM dimensions, 16-bit unsigned pixels, parseability, and
manifest-derived structure. `mpips/conversion/tiff_json_to_dcm.py` is byte/hash
protected.

Disposition: no final-image/DICOM semantic port is required. Camera metadata
optionality is a **REVIEW REQUIRED** compatibility decision, not a reason to
modify the converter or merge legacy service code. NPZ → processing → TIFF →
DICOM routing is already canonical through the workflow and conversion worker;
promotion diagnostics and output-directory behavior remain operational/test
concerns.

### Production infrastructure exclusions

Do not port the Drive download diagnostic, production DICOM E2E workflow,
carrier IDs or secrets, calibration promotion workflow, runtime preflight,
rollback directory machinery, deployment workflow edits, `.gitignore` changes,
promotion manifests, or pinned production calibration carriers. These are
**INFRA-ONLY** and remain outside the canonical processing packages.

### ImageJ/Fiji impact

**NO REOPENING REQUIRED.** Frozen-range changes do not materially change
Contrast Stretch, Weighted/Classical Equalization, Hybrid Median, Circular
Median, or CLAHE semantics. The accepted ImageJ/Fiji closure at
`a4a5c16881e589154680f0606c849e2a4514041f` remains protected. No direct
contradiction was found.

### I-5B impact

Historical I-5B publication: task `82cf2187b2efd6146de790021c1ba5e4e307b9d7`,
corrected evidence baseline `8396fbc768285cc68ed3bbe572561cd664b70e8b`.
The immutable cohort is six identities: three `Kepala` and three `Tulang
Belakang`. The original matrix is 72 rows: 4 threshold conditions × 3 CLAHE
conditions × 6 cases.

| Condition | Impact classification | Evidence |
|---|---|---|
| `NONE` | Unaffected by Otsu return-value fix. | No Otsu selection. |
| `OTSU` / `T_ALT1` | Directly affected; historical Otsu outputs collapsed to zero under the buggy scalar. | Corrected historical evidence says Otsu collapses all governed outputs. |
| `KNEE` / `T_ALT2` | Not affected merely because Otsu was buggy. | Independent threshold method. |
| `CLAHE` combinations | Not automatically invalidated; revalidate only where paired with affected threshold conditions. | CLAHE value conclusion is independent and remains supported pending bounded comparison. |
| `AUTO` | Not proven directly affected. | Auto selects valley first, then secondary peak, then Otsu only as a fallback when the scalar is positive. Historical AUTO rows were not collapsed, but the artifact does not record the selected fallback method; an AUTO→Otsu path cannot be excluded from source/evidence alone. |
| Interaction conclusion | Partially conditional. | The historical interaction signal involved Otsu collapse versus Knee/AUTO behavior; it must be rechecked after the implementation fix, without changing the original experiment identity. |

### Proposed bounded Phase-4 revalidation

Reuse the exact six original cases and their original raw/gain/calibration
identities. Do not use the later Drive source. The smallest defensible matrix is
36 rows: all 18 `T_ALT1`/Otsu rows and all 18 `T_AUTO` rows, each with C0, M06,
and M15. AUTO is included because selected-method provenance was not recorded
and the source permits an Otsu fallback; NONE and KNEE do not need reruns for
this implementation-change isolation question.

For every row, require: the corrected output and DICOM/final shape, dtype,
deterministic output hash, stage/output exact-zero and nonzero ratios, nonzero
bbox, dynamic range, the historical IQA metrics (alignment Pearson, edge
recall, gradient-energy retention, informative-tile counts/lost fraction,
low-percentile retention, informative-extreme fraction), and comparison with
the historical row values. Preserve the original cohort, calibration
fingerprint, input identities, and row keys.

Disposition: classify each row as unchanged, corrected-only, non-comparable, or
error. Confirm whether corrected Otsu remains a catastrophic collapse, whether
AUTO selected Otsu, and whether the interaction conclusion survives. Do not
rewrite the historical 72-row evidence and do not start a new population or
stage-order experiment.

### Proposed Phase-2 write surface

1. `mpips/processing/thresholding.py` — correct the OpenCV scalar return-value
   unpacking and preserve uint16/normalized-float32 domain semantics.
2. `tests/test_thresholding_processing.py` — add only the five focused Otsu
   regressions listed above.
3. `mpips/pipelines/radiography.py` — apply TRX default bypass and preserve BED
   configuration at the orchestration boundary, only if Phase-2 planning accepts
   the policy as part of this hotfix task.
4. `tests/test_radiography_pipeline.py` — verify TRX/BED policy separation and
   deterministic outputs, only with the bounded policy change.

Camera metadata optionality and calibration remap/lattice behavior are not
included in this minimal surface; each needs a separate bounded decision/task.

### Items explicitly not to port

- `mpips/engine/calibration/**` or any whole legacy engine module.
- Production diagnostic scripts/workflows and Drive download logic.
- Carrier IDs, production secrets, promotion manifests, runtime preflight,
  rollback, and deployment changes.
- Universal zero-ratio, nonzero-ratio, bbox, or dynamic-range quality rules in
  the processing runtime.
- Stage observers and diagnostic stage snapshots in the default production
  pipeline.
- Changes to `mpips/conversion/tiff_json_to_dcm.py`.
- Historical I-5B evidence or artifacts.
- ImageJ/Fiji semantic changes or stage-order changes.

### Protected converter

Observed SHA-256:
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` (matches
the required invariant).

### Remaining uncertainties

- The current I-5B row artifacts do not record the selected AUTO fallback
  method, so AUTO rows must be included in bounded Phase-4 revalidation.
- Camera-serial optionality is present in frozen main but conflicts with current
  canonical compatibility checks; it requires an explicit scoped decision.
- Calibration lattice/remap fixes cannot be bounded with the image hotfix and
  require a separate planning task.

### Verification record

Commands actually run included branch/HEAD/ref checks, commit resolvability and
range inventory, `git merge-base`, clean-worktree inspection, protected-file
`sha256sum`, frozen-range path/diff inspection, canonical source/test inspection,
and immutable I-5B artifact inspection. No runtime production data, new Drive
data, deployment, or external system was accessed.

`git diff --check`: **PASS**. Because this file is intentionally untracked,
the equivalent `/dev/null` versus evidence-file check was also run and passed.

### Terminal state

**Review Required**. Phase 2–5 remain unauthorized until review acceptance and
republished task authority.

## Phase 2 — Canonical Hotfix Port

### Governing identity

- Governing publication: `c652c0b47aa9560cf794a627550e65c8fe1f496b`.
- Pre-execution HEAD: `c652c0b47aa9560cf794a627550e65c8fe1f496b`.
- Branch: `refactor/package-boundaries`.
- `origin/refactor/package-boundaries`: `c652c0b47aa9560cf794a627550e65c8fe1f496b`.
- Frozen main: `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd` (resolvable).
- Task: `.agents/tasks/main-hotfix-reconciliation.md`, version `1.1`.
- Worktree was clean before execution. No newer main commits were absorbed.

### Otsu correction

The previous implementation retained OpenCV's thresholded output array and
used its first element as the threshold, producing `0.0` for the
representative fixture. The corrected implementation unpacks
`threshold_value, thresholded_image = cv2.threshold(...)`, uses the scalar
first return value, and discards the image output. Float32 input is converted
to uint16 and the scalar is divided by `65535`; non-float32 input retains the
scalar in its input intensity domain. The obsolete ndarray/first-pixel
fallback was removed.

Independent characterization on `_threshold_fixture()` produced OpenCV scalar
`13107.0`, first thresholded-output pixel `0`, and normalized scalar
`0.2`; the canonical result is `0.2`. Repeated calls returned `0.2`.
The accepted representative Otsu golden is `0.2`.

The deterministic uint16 fixture produced direct and canonical scalar `100.0`.
The float32 result was scalar `0.2` in `[0, 1]`; the uint16 result was scalar
`100.0` in `[0, 65535]`.

### TRX/BED policy

- TRX: **BYPASS BY DEFAULT**.
- BED: **CONFIGURED THRESHOLD PRESERVED**.
- Canonical orchestration location: `mpips/pipelines/radiography.py`.
- Detector-agnostic threshold detection remains in
  `mpips/processing/thresholding.py`.

TRX bypasses threshold separation without mutating `use_threshold`,
`threshold_method`, or unrelated CLAHE/median configuration. BED continues to
invoke configured threshold detection; `none` and `use_threshold=False` retain
the bypass behavior.

### Regression evidence

- `./.venv/bin/python -m pytest -q tests/test_thresholding_processing.py` — **18 passed**.
- `./.venv/bin/python -m pytest -q tests/test_radiography_pipeline.py` — **28 passed, 11 warnings**.
- Combined focused run — **46 passed, 11 warnings**.
- `./.venv/bin/python -m pytest -q tests/test_imager_pipeline_workflow.py` — **27 passed, 1 skipped, 3 warnings**.
- `./.venv/bin/python -m pytest -q tests/test_imagej_migration.py` — **14 passed**.
- `git diff --check` — **PASS**.
- Protected converter SHA-256 remained
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

The default BED regression remained unchanged. AUTO remains unchanged because
the representative fixture selects Valley before Otsu; Otsu is not selected.

### Explicit exclusions

Diagnostic override, stage observer, collapse gate, calibration, camera
metadata compatibility, production infrastructure, later main commits,
I-5B rerun, and ImageJ reopening were not ported or performed. The protected
converter was not modified.

### Remaining reconciliation items

Calibration reconciliation, the camera metadata compatibility decision, and
Phase-4 revalidation of the bounded 36-row I-5B AUTO/Otsu affected set remain
explicitly unresolved and unauthorized.

### Converter

Protected converter:
`mpips/conversion/tiff_json_to_dcm.py`.
SHA-256: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

### Terminal state

**Review Required**. Phase 3–5 remain unauthorized pending review and
republished task authority. Acceptance is not release authorization.

## Phase 3 — Newer-Main Radiography Semantic Drift Mapping

### Governing and observed identity

- Phase-2 task publication: `c652c0b47aa9560cf794a627550e65c8fe1f496b`.
- Phase-2 accepted implementation: `e0ff8a5c093f5ad265bf65326b40663cb4454943`.
- Historical frozen Phase-2 upstream main: `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd`.
- Accepted ImageJ/Fiji baseline: `a4a5c16881e589154680f0606c849e2a4514041f`.
- Phase-3 observed `origin/main` after fetch: `e94784db65bb134d43e87a2046037ab4d1cbfe02`.
- Merge base: `fec5695048acbc3ce95d0a658032ec3701b6e045`.
- Accepted Phase-2 branch state remained unchanged before this documentation remediation.

The newer-main observation boundary is distinct from the historical frozen
Phase-2 authority. No merge, rebase, cherry-pick, or runtime synchronization
was performed.

### Newer-main range inventory

The observed range `203c6c65cf6d6b5a8df0271ab610ded950b8f9fd..e94784db65bb134d43e87a2046037ab4d1cbfe02` contains 28 commits. The relevant inventory is:

| Commits | Classification | Disposition |
|---|---|---|
| `ae41b1d5`, `80729162` | Calibration canvas/remap validation and expanded-canvas runtime semantics | **SEPARATE CALIBRATION SCOPE** |
| `dd7c21ee` | BED and TRX threshold bypass in legacy radiography orchestration | **PORT / RECONCILE** for BED only after Planner review; Phase 3 does not implement it |
| `4495f622`, `9a38b19a`, `369619b8`, `46b0e9f7` | Real BED verifier workflow, hardening, dependency staging, and observability | **EVIDENCE REQUIRED / PRODUCTION INFRASTRUCTURE ONLY** |
| `195baf0a`, `f6b3b69f`, `3beffc3b`, `4bdac9e4`, `f34a82ce`, `392ceaec`, `86f4a66f`, `899383f4` | TRX calibration promotion modes, preflight, isolation, and promotion-only workflow | **PRODUCTION INFRASTRUCTURE ONLY** |
| `ad116c69`, `7f6b773a`, `7006dbe2`, `320e5d0d`, `bc23d68f`, `e8122ad7` | Real TRX acceptance task, verifier, and CI/runtime-preflight hardening | **EVIDENCE REQUIRED / PRODUCTION INFRASTRUCTURE ONLY** |
| `496b286f` | Published TRX orientation task | **ALREADY SATISFIED as task authority; implementation applicability requires reconciliation** |
| `f2bf7b99` | Clockwise TRX orientation implementation and deterministic tests in legacy ownership | **PORT / RECONCILE**, with canonical ownership mapping required |
| `4ccbcb1b`, `303675f2`, `bda82397`, `a05ebea2`, `e94784db` | Docker/build-cache optimization and bootstrap documentation | **DEFER TO OPTIMIZATION / PRODUCTION INFRASTRUCTURE ONLY** |

The remaining commits in this range are included in the grouped inventory
above; no additional canonical image-processing semantic was found beyond BED
threshold policy, TRX orientation, and calibration/canvas behavior.

### BED threshold default policy

Commit `dd7c21eead66a2c5396522a2310f5dd9cbd85b85` changes legacy
`mpips/engine/imager_pipeline/complete_pipeline.py` so both `BED` and `TRX`
return threshold method `none` by default, while an explicit diagnostic
override still applies. Its tests update the BED golden and assert that BED
and TRX defaults skip threshold separation while explicit override applies.

This is a newer semantic relative to accepted Phase 2: TRX bypass is already
accepted, but BED configured threshold behavior was deliberately preserved
under the frozen Phase-2 contract. Therefore current-main BED bypass is not
retroactively justified by current behavior. It is a candidate **PORT /
RECONCILE** decision for canonical orchestration, with **EVIDENCE REQUIRED**
before implementation or acceptance.

Commit `4495f6220ff610d80cfd119be6e6f9c62625acc0` adds a production-runner
BED verifier; subsequent commits harden it and stage `gdown`. The repository
contains workflow and verifier machinery, but no observed successful workflow
result in this review. The machinery is not proof of completed production BED
validation and remains production infrastructure/evidence input only.

### TRX output orientation

The published task `.agents/tasks/mpips-trx-output-orientation-hotfix.md` is
validated/published on main at `496b286f...`, with implementation commit
`f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a`. The implementation changes legacy
`crop_and_rotate_by_detector()` from `cv2.ROTATE_90_COUNTERCLOCKWISE` to
`cv2.ROTATE_90_CLOCKWISE` and adds asymmetric sentinel tests mapping
`[[1,2,3],[4,5,6]]` to `[[4,1],[5,2],[6,3]]`; BED remains unchanged.

This is a justified production semantic candidate and **PORT / RECONCILE**
for canonical ownership: the accepted refactor owns the operation in
`mpips/processing/geometry.py`, while newer main routes through legacy engine
ownership. The task/tests provide implementation evidence, but no separate
observed production acceptance result was found. Do not port it during Phase 3.

### Calibration and geometric corrections

`ae41b1d5...` adds expanded-canvas validation and `80729162...` makes expanded
calibration canvas behavior canonical across calibration/remap/model paths.
The later range also contains calibration carrier, promotion, rollback,
preflight, and TRX validation changes. Algorithm/runtime calibration semantics
are **SEPARATE CALIBRATION SCOPE**; carriers, promotion, and preflight are
**PRODUCTION INFRASTRUCTURE ONLY**. None were changed or absorbed here.

### Production validation and CI

The real BED/TRX verifier workflows, task documents, download integrity checks,
promotion modes, and build-cache commits are evidence or operations machinery,
not proof of successful production execution. No production workflow was
dispatched, no production result was imported, and no deployment or promotion
occurred. These items remain **EVIDENCE REQUIRED** or **PRODUCTION
INFRASTRUCTURE ONLY** as classified above.

### Preserved boundaries and unresolved gaps

- Phase-2 Otsu, TRX bypass, BED configured-threshold behavior, ImageJ/Fiji
  closure, and protected converter remain unchanged.
- Protected converter SHA-256 remains
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- No newer-main runtime semantic was implemented during this remediation.
- BED bypass needs a separately reviewed canonical decision and evidence plan.
- TRX orientation needs canonical geometry reconciliation and focused review.
- Calibration/canvas and camera/conversion questions remain separate scopes.
- I-5B revalidation and all optimization/ablation phases remain unauthorized.

### Deferred BED/TRX characterization inputs

These are future characterization/optimization inputs, not Phase-3 workload:

- BED: `https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8` — heterogeneous sessions, calibration, processed artifacts, and goat/radiograph material; do not treat it as one cohort.
- TRX source A: `https://drive.google.com/drive/folders/1Zn0JC4Rvg1-07ljSwA5hckSmO0FBidIv` — mixed real radiographs, calibration validation, and production carrier artifacts.
- TRX source B: `https://drive.google.com/drive/folders/10wGVGU03Zut07DBsnBllzAgz44idgwM5` — 19 full TRX NPZ acquisitions and paired `NPZ tanpa processedimage` variants; verify fields, detector, calibration fingerprint, and orientation before use.

Existing `processedimage` files are not automatically ground truth.

### Phase-3 verification record

Commands run: `git fetch origin`; branch/status/HEAD/ref/merge-base checks;
newer-main range and path inventory; direct inspection of `dd7c21ee`,
`4495f622`, `ae41b1d5`, `80729162`, `496b286f`, and `f2bf7b99`; orientation task
inspection; protected converter `sha256sum`; `git diff --check`; and final
changed-file/status checks. No production data, Drive data, deployment, or
external mutation was accessed.

### Terminal state

**Review Required**. Phase 3 is mapping/evidence only. Subsequent runtime
reconciliation, revalidation, and optimization remain unauthorized pending
Planner/Reviewer review and republication.

## Phase 3 contract remediation note

The candidate documentation/evidence commit `bc093e66c590367b663a6e95073e7e0fd86d210e`
was reviewed but was not accepted as the governing Phase-3 revision because
the task contract retained stale Phase-2 current-scope language, left Phase 3
as `CURRENT RELEASED PHASE` after the mapping was complete, and did not fully
record the current documentation write surface or detector-specific source
map. The semantic mapping itself was not rejected.

Version `1.3` corrects those defects while preserving immutable Phase-2
provenance, the Phase-3 mapping conclusions, and the deferred BED/TRX source
references. Phase 3 is now `COMPLETED / REVIEW REQUIRED`; all runtime
reconciliation, revalidation, optimization, and production work remains
`UNAUTHORIZED`.

## Phase 4 publication note

Planner accepted Phase 3 closed at `b9093b0aec5dd66cf2a5afcd5028c2876cf889bd`.
The umbrella task is republished as version `1.5` to release the bounded
canonical TRX orientation port. The residual Phase-2 wording was corrected to
historical/satisfied tense; no Phase-3 mapping conclusion was changed.

Phase 4 authorizes only `mpips/processing/geometry.py`,
`tests/test_geometry_processing.py`, and this evidence file. It ports the
accepted clockwise TRX semantic from `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a`
at canonical ownership. No runtime implementation occurred during this task
republication; BED policy, calibration, conversion, ImageJ/Fiji, deployment,
production, and optimization remain outside scope.

During Planner review, `origin/refactor/package-boundaries` was observed at
`bc093e66c590367b663a6e95073e7e0fd86d210e`. The prior Executor report stated
that no push occurred. The candidate was reported as locally created; the
remote branch was later observed at that candidate, and attribution of the
remote update is unresolved. No runtime semantic was changed during this
corrective remediation.

## Phase 4 — Canonical TRX Orientation Port Evidence

### Execution identity

- Governing task: `.agents/tasks/main-hotfix-reconciliation.md` version `1.5` at `5f6e03d928c0d7e062f1cb666f4ab57e0273ff3a`.
- Execution-start `HEAD`: `5f6e03d928c0d7e062f1cb666f4ab57e0273ff3a`.
- Branch/worktree: `refactor/package-boundaries` / `/var/www/mpips`.
- Initial worktree: clean; observed `origin/refactor/package-boundaries` at `5f6e03d928c0d7e062f1cb666f4ab57e0273ff3a`; observed `origin/main` at `e94784db65bb134d43e87a2046037ab4d1cbfe02`.

### Orientation result

Canonical owner: `mpips/processing/geometry.py`, function
`crop_and_rotate()`. The old TRX operation was
`cv2.ROTATE_90_COUNTERCLOCKWISE`; it is now
`cv2.ROTATE_90_CLOCKWISE`. Crop-before-rotation remains unchanged and no
second transform was added.

For the exact sentinel input:

```text
[[1, 2, 3],
 [4, 5, 6]]
```

the observed TRX output is:

```text
[[4, 1],
 [5, 2],
 [6, 3]]
```

The cropped TRX sentinel output was `[[11, 6], [12, 7], [13, 8]]`, with
shape `(3, 2)` and `uint16` dtype. The workflow wrapper produced the same
exact pixels, shape, and dtype. BED remained crop-only and unrotated, with
the cropped sentinel output `[[6, 7, 8], [11, 12, 13]]`, shape `(2, 3)`,
and `uint16` dtype. Zero-crop BED and supported `uint8`/`uint16` dtype
coverage also passed.

### Verification

Executor-run local results, not GitHub CI or production evidence:

- `./.venv/bin/python -m pytest -q tests/test_geometry_processing.py` — **8 passed**.
- `./.venv/bin/python -m pytest -q tests/test_imager_pipeline_workflow.py` — **27 passed, 1 skipped, 3 warnings**.
- `./.venv/bin/python -m pytest -q tests/test_radiography_pipeline.py` — **28 passed, 11 warnings**.
- `./.venv/bin/python -m pytest -q tests/test_converter_protection.py` — **1 passed**.
- `sha256sum mpips/conversion/tiff_json_to_dcm.py` — **a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0**.
- `git diff --check` — **PASS**.

Exact changed-file inventory: `mpips/processing/geometry.py`,
`tests/test_geometry_processing.py`, and
`.agents/evidence/main-hotfix-reconciliation.md`.

Explicitly unchanged: BED threshold policy (**NO change**); calibration and
calibration canvas/remap (**NO change**); DICOM converter (**NO change**);
ImageJ/Fiji (**NO change**); deployment (**NO**); production workflow dispatch
and production mutation (**NO**); Drive experiments (**NO**); optimization
(**NO**). The NPZ → processing → DICOM boundaries remain preserved.

Terminal state: **Review Required**. No next reconciliation phase was started.

## Phase 5 publication — BED Threshold Policy Evidence Characterization

Planner republished `.agents/tasks/main-hotfix-reconciliation.md` as version
`1.6`. Phase 4 remains accepted and closed at
`820948734e8b598b851135cc82c2210ead934963`.

Phase 5 is required because canonical behavior preserves BED's configured
threshold policy while later `main` defaults both BED and TRX to threshold
bypass. Existing corrected bypass evidence supports TRX only; production-main
behavior alone is insufficient evidence for BED. The authorized read-only BED
source is the heterogeneous Drive folder:

`https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8`

The publication bounds recursive provenance inventory, repository-native NPZ
validation, deterministic bounded cohort selection, paired `BED_AUTO` versus
`BED_NONE` runs, frozen non-threshold semantics, stage-local IQA, lossless
geometry, final-output statistics, and one of the three required bounded
classifications. It authorizes no BED runtime-policy change, calibration
decision, production action, optimization, or release.

The future execution write surface is limited to the characterization helper,
its report/JSON/CSV artifacts, and this evidence file as listed in the task.
No external radiograph, NPZ, image, NumPy, calibration, or other
patient/subject binary may be committed. The protected converter,
ImageJ/Fiji closure, accepted TRX orientation/bypass, current BED behavior,
and `NPZ → processing → DICOM` boundaries remain unchanged.

No Phase-5 experiment, Drive access, data analysis, or runtime modification was
performed during this task republication. Terminal state: **Review Required**.

## Phase 5 contract remediation note

Phase-5 v1.6 was published at
`0481ea6e889efb63cf6c12088d35e0b7d49fd4c0`. Planner review found stale
current-looking Phase-4 execution, verification, side-effect, and terminal
language in the governing task. No defect was found in the substantive Phase-5
experiment design. Version 1.7 corrects contract authority only.

No Phase-5 experiment was run, and no runtime, configuration, calibration,
converter, ImageJ/Fiji, or production behavior changed. During Planner review,
`origin/refactor/package-boundaries` was observed at
`0481ea6e889efb63cf6c12088d35e0b7d49fd4c0`. No attribution is made regarding
the remote update.

## Phase 5 execution evidence

The accepted v1.7 Phase-5 experiment was executed from
`e230ffc6d1ae86e09cba706c46f4632979d547b1` using the authorized Drive folder
read-only. Recursive inventory visited 96 folders and identified 200
acquisition NPZ candidates, six gain NPZ files, processed/reference material,
and calibration material. Processed/reference material was not treated as
ground truth; no calibration was generated, promoted, substituted, or
mutated.

The frozen primary cohort contains nine valid BED radiographs: three sessions
(`Ambil Data 1`, `Ambil Data 2`, `Ambil Data 3`) × three subject folders. The
selection used lexicographic session/subject grouping and stable numeric
acquisition ordering, selecting the first acquisition from each group in
round-robin order to the bounded nine-case cohort before either threshold
state was processed. Every selected case resolved to a matching gain ID and
passed repository-native NPZ validation; no cases were excluded.

Each case ran exactly `BED_AUTO` (`use_threshold=True`, `threshold_method="auto"`)
and `BED_NONE` (`threshold_method="none"`) through the canonical pipeline with
the same raw/gain inputs and no calibration remap. Pre-threshold arrays were
captured at the canonical threshold boundary. Stage-local IQA reused
`mpips.iqa.analyze_structural_preservation`; final output shape, dtype, hashes,
intensity, zero, saturation, and dynamic-range statistics are in the JSON and
CSV artifacts.

Across all nine cases, AUTO edge recall was 0.2211–0.2614 while NONE was 1.0;
AUTO lost-informative-tile fraction was 0.4967–0.5862 while NONE was 0.0.
Final hashes differed in all nine pairs, and the median final AUTO-minus-NONE
mean-intensity delta was -12633.43. The direction was consistent by session
and subject, with no conflict favoring AUTO.

Required classification: **BED BYPASS SUPPORTED**.

This is bounded decision support only. It does not authorize or implement a
BED runtime-policy change. No external binary was committed, Google Drive was
not mutated, and the protected converter remained unchanged.
