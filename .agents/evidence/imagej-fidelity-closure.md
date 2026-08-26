# MPIPS ImageJ/Fiji Fidelity Closure — Phase 3 CLAHE Semantic Closure

Status: **Review Required**. This artifact preserves the Phase 1 inventory and
Phase 2 accepted-parity/N/A provenance and records the Phase 3 CLAHE semantic
closure. It records observed implementation reality; it does not change
production behavior.

## Governing identity and preflight

| Item | Observed value |
|---|---|
| Governing task | `.agents/tasks/imagej-fidelity-closure.md` |
| Exact governing task revision | `97beff699318dce2f80ade9333f195c7f5647387` |
| Accepted implementation baseline | `8396fbc768285cc68ed3bbe572561cd664b70e8b` |
| Accepted Phase-1 evidence revision | `1be8ba791bc187be0c8b107cf165ac24f88ee412` |
| Accepted Phase-2 baseline | `b4c032ce58605095de82c67097c61ebf458041a5` |
| Accepted direct predecessor | `fdf38094320de1dc81037e6516c17e11022d4fde` |
| Execution revision / pre-evidence HEAD | `97beff699318dce2f80ade9333f195c7f5647387` |
| Branch | `refactor/package-boundaries` |
| Origin branch before evidence | same revision as local HEAD |
| Baseline ancestry | verified: accepted baseline is an ancestor of HEAD |
| Protected converter SHA256 | `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` |
| Worktree precondition | clean |

## Methodology

The inventory combined direct inspection of current source, configuration,
schemas, API/worker/workflow callers, and the retained reference README with
the accepted I-4A characterization, Hybrid Median remediation, I-4C0 CLAHE
contract evidence, I-5A evidence, and closed I-5B evidence. Graphify was used
only as discovery support; material conclusions below were verified against
current files. No new reference execution, dependency installation, JDK
installation, benchmark, or CI claim was made.

The production trace is:

```text
POST /v1/radiographs/dicom
  -> run_isolated_dicom_conversion()
  -> conversion worker process_radiography_arrays()
  -> RadiographyPipeline.process()
  -> ImagerPipelineConfig defaults
  -> ImageJReplicator / filtering dispatch
```

The worker call supplies no alternate processing configuration, so the
`ImagerPipelineConfig()` defaults govern the current DICOM path. The same
pipeline is also directly importable through the imager workflow and file
runner.

## Phase 2 execution result

The existing `tests/test_hybrid_median_fidelity.py` already covered accepted
uint8/uint16 parity for kernels 3x3, 5x5, and 7x7, repeated passes, edges,
corners, interiors, PLUS/X/center selection, and the radius-2 wrapper. It was
not modified.

The only sentinel gaps were uint16 reference-backed coverage for Contrast
Stretch and uint8 coverage for classic Equalization. The existing
`tests/test_imagej_migration.py` was minimally extended with the accepted I-4A
`sparse` fixture (`[0] * 20 + [17, 17, 200, 255, 255]`, scaled by 257 for
uint16) and exact accepted-reference output hashes. The sparse fixture
discriminates weighted from classic Equalization; their hashes differ for
both dtypes. Every new sentinel also asserts shape and dtype.

| Operation | Dtype | Fixture/parameters | Reference-backed output SHA256 |
|---|---|---|---|
| Contrast Stretch | uint16 | ramp, `saturated_pixels=0.35` | `776abec193b4d98a9ba397b111718d3b40cb921c2faa224bd21dbec1b9f04dbd` |
| Weighted Equalization | uint8 | sparse | `37c75a82822033dec9f4cc9c504a46664d0a816a648953be4bb054890ffca3f7` |
| Classic Equalization | uint8 | sparse | `3ed1dd4695afb31ff8fb96a14efbe8f22e9b87ff06d5b785f73f1c3c1b9f9e55` |
| Weighted Equalization | uint16 | sparse × 257 | `172fdc9ad53f216f5c4c41e6de9582abcc5a73217a9b0e6ab3ab616effe695fb` |
| Classic Equalization | uint16 | sparse × 257 | `577694133e8f9225f5b45cc07a9f1bd81caab768a70f76c279cd151d19cdf2d8` |

Observed local verification:

```text
.venv/bin/python -m pytest -q tests/test_imagej_migration.py       10 passed
.venv/bin/python -m pytest -q tests/test_hybrid_median_fidelity.py 12 passed
```

These are LOCAL TESTS, not CI. The Temporal Median reachability refresh found
only `ImageJReplicator.fast_temporal_median` and its documentation/example;
there is still no production API, workflow, configuration, schema, or caller.
It is therefore closed as `NOT PRODUCTION REACHABLE — N/A — CLOSED`.

## Authoritative closure matrix

| Operation | REFERENCE | MPIPS IMPLEMENTATION | PRODUCTION REACHABILITY | DEFAULT REACHABILITY | DTYPE | PRIOR ACCEPTED STATUS | CURRENT VERIFIED STATUS | UNRESOLVED GAP | NEXT REQUIRED PHASE |
|---|---|---|---|---|---|---|---|---|---|
| Contrast Stretch | ImageJ `ContrastEnhancer` normalized stretch | `ImageJReplicator.enhance_contrast(equalize=False, normalize=True)`; wrappers in `mpips/processing/radiography.py` | PRODUCTION-REACHABLE — CONFIGURABLE; `contrast_mode="stretch"` | NOT DEFAULT; default mode is `equalize` | uint8, uint16; pipeline converts to uint16 | PARITY CONFIRMED | PARITY CONFIRMED — REGRESSION PROTECTED; uint16 sentinel added and focused test passes | None for Phase 2 | Phase 3 — not required for this settled item |
| Equalization — weighted ImageJ variant | ImageJ `ContrastEnhancer` weighted/sqrt histogram equalization | `ImageJReplicator._equalize_imagej_variant(classic_equalization=False)` via `enhance_contrast` | PRODUCTION-REACHABLE — DEFAULT | PRODUCTION-REACHABLE — DEFAULT; `contrast_mode="equalize"`, `classic=false` | uint8, uint16; pipeline working output uint16 | PARITY CONFIRMED | PARITY CONFIRMED — REGRESSION PROTECTED; uint16 sentinel added and focused test passes | None for Phase 2 | Phase 3 — not required for this settled item |
| Equalization — classic | ImageJ `ContrastEnhancer` classic histogram equalization | `ImageJReplicator._equalize_imagej_variant(classic_equalization=True)`; config `contrast_classic_equalization` | PRODUCTION-REACHABLE — CONFIGURABLE | NOT DEFAULT; weighted variant is default | uint8, uint16; pipeline working output uint16 | PARITY CONFIRMED | PARITY CONFIRMED — REGRESSION PROTECTED; uint16 sentinel added and focused test passes | None for Phase 2 | Phase 3 — not required for this settled item |
| Hybrid Median | Pinned `Hybrid_2D_Median_Filter.java` | `ImageJReplicator.hybrid_median_filter_2d`; `filtering.apply_median_filter("hybrid_imagej")` maps radius 2 to 5x5 | PRODUCTION-REACHABLE — DEFAULT; pipeline calls median dispatch | PRODUCTION-REACHABLE — DEFAULT; `use_median_filter=true`, type `hybrid_imagej`, radius 2 | uint16 in radiography; implementation also preserves uint8/uint16 | REMEDIATED AND PARITY CONFIRMED | REMEDIATED AND PARITY CONFIRMED — REGRESSION PROTECTED; existing focused coverage passes unchanged | None for Phase 2 | Phase 3 — not required for this settled item |
| CLAHE — MPIPS precise | Pinned Fiji `Flat.java` retained as comparison reference; governed contract is separate | `ImageJReplicator.apply_clahe(..., fast=False)` -> `_clahe_precise`; displayed bins 256 maps to internal bins 255; blocksize 127 maps to radius 63 | PRODUCTION-REACHABLE — DEFAULT when ImageJ processing is available | PRODUCTION-REACHABLE — DEFAULT; `use_clahe=true`, `fast=false`, slope 0.6, bins 256, blocksize 127, composite true | uint8 and direct uint16 semantics; radiography output is uint16 | FIDELITY FAILURE relative to Fiji Flat (historical) | LEGACY MPIPS CONTRACT; INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED; NOT FIJI FLAT PARITY | No fidelity-semantic gap under Option A; slope quality/optimization remains separate | Phase 5 runtime measurement; Phase 6/7 later if authorized |
| CLAHE — MPIPS fast/OpenCV | Pinned Fiji `FastFlat.java` retained as comparison reference; governed contract is separate | `ImageJReplicator.apply_clahe(..., fast=True)` -> OpenCV `createCLAHE` path | PRODUCTION-REACHABLE — CONFIGURABLE | NOT DEFAULT; `clahe_fast=false` | uint8 and uint16; OpenCV preserves the single-channel dtype | MPIPS/OpenCV is not Fiji FastFlat parity (historical mismatch) | MPIPS/OPENCV ALTERNATE CONTRACT; INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED; NOT FIJI FASTFLAT PARITY | No semantic identity gap under Option A; performance and broader regression remain separate | Phase 5 runtime measurement; Phase 6/7 later if authorized |
| Fiji CLAHE Flat reference | Pinned `axtimwalde/mpicbg` `Flat.java` and supporting `Apply`/`ShortApply` code | No Java/Fiji runtime in MPIPS production path; retained reference tooling only | NOT PRODUCTION-REACHABLE | NOT DEFAULT | Byte working domain; uint16 uses ShortProcessor 8-bit working representation and ShortApply mapping | REFERENCE ONLY / historical cross-reference mismatch | REFERENCE ONLY; NOT PRODUCTION REACHABLE | No production contract obligation; retained provenance and execution limits remain | Phase 5 reference measurement if authorized |
| Fiji CLAHE FastFlat reference | Pinned `axtimwalde/mpicbg` `FastFlat.java` and supporting fast apply code | No Java/Fiji runtime in MPIPS production path; retained reference tooling only | NOT PRODUCTION-REACHABLE | NOT DEFAULT | Distinct byte working representation and dtype-specific uint16 mapping | REFERENCE ONLY / historical cross-reference mismatch | REFERENCE ONLY; NOT PRODUCTION REACHABLE | No production contract obligation; retained provenance and execution limits remain | Phase 5 reference measurement if authorized |
| Circular Median | ImageJ core `RankFilters.MEDIAN` circular-kernel semantics | `ImageJReplicator.median_filter_imagej`; `filtering.apply_median_filter("circular_imagej")` | PRODUCTION-REACHABLE — CONFIGURABLE through canonical/config paths; DICOM endpoint itself supplies no alternate processing config | NOT DEFAULT; default type is `hybrid_imagej`, radius 2 | uint8 and uint16 | FIDELITY FAILURE for accepted special-radius cases; exposed alternative, not active default | REMEDIATED AND PARITY CONFIRMED ACROSS ACCEPTED I-4A CHARACTERIZATION MATRIX | No universal positive-radius parity claim; broader domain and typing/documentation debt remain separate | Phase 5+ only if later authorized |
| Temporal Median | ImageJ `Fast_Temporal_Median.java` plugin identity | `ImageJReplicator.fast_temporal_median(stack, ...)` only; no wrapper/config/pipeline caller found | NOT PRODUCTION-REACHABLE | NOT DEFAULT | Library method accepts 3D uint8/uint16 stacks | NOT PRODUCTION-REACHABLE — N/A | NOT PRODUCTION REACHABLE — N/A — CLOSED; refreshed caller/config/API/schema search remains empty | No production fidelity obligation established; standalone method remains outside current production surface | Phase 3 — no further Phase-2 work |

## Phase 3 — CLAHE semantic closure

### Governing decision and execution identity

- Governing task revision: `97beff699318dce2f80ade9333f195c7f5647387`.
- Accepted Phase-2 baseline: `b4c032ce58605095de82c67097c61ebf458041a5`.
- Accepted direct predecessor: `fdf38094320de1dc81037e6516c17e11022d4fde`.
- Pre-change HEAD: `97beff699318dce2f80ade9333f195c7f5647387`.
- Planner decision: **Option A — Legacy MPIPS Contract**, selected and
  governing. No implementation, configuration, or test change occurred.

Option A preserves the current MPIPS production semantics and stops treating
Fiji Flat/FastFlat as the required production algorithms. It makes the
historical cross-reference mismatches intentional governed divergences, not
current unresolved production fidelity failures. This is not a clinical,
visual, mathematical, or quality-superiority claim.

### Current production defaults and precise contract

The verified production defaults are:

```text
use_clahe=true
clahe_blocksize=127
clahe_histogram_bins=256
clahe_max_slope=0.6
clahe_fast=false
clahe_composite=true
```

The default path is `RadiographyPipeline.process` ->
`ImageJReplicator.apply_clahe(..., fast=False)` -> `_clahe_precise`.
`histogram_bins=256` maps to `bins=255`; `blocksize=127` maps to
`block_radius=63`.

The **Legacy MPIPS Contract** is defined by the current implementation:

- uint8 values are quantized over 0..255 into 256 internal levels; uint16
  values are quantized directly over 0..65535 into the same 255-index
  internal range, with no uint16-to-uint8 working conversion for the precise
  grayscale path;
- each local histogram is the clipped image window centered on a computed
  block center, restricted to positive mask pixels when a mask is supplied;
- the clip limit is `int(slope * n_pixels / (bins + 1))`, with a minimum-one
  clamp; excess is redistributed as floating-point mass across all bins, with
  the implementation's residual stepping behavior;
- each histogram becomes a normalized cumulative-distribution LUT; LUTs are
  placed on a block-center grid derived from the image dimensions and the
  127-pixel block size, with one center at the image midpoint for a single
  grid cell;
- each pixel selects the four surrounding LUTs and receives bilinear
  interpolation; the result is restored to the original dtype and clipped to
  its full range; masked-out pixels retain their input value.

This is not Fiji Flat replication. The precise path is
`PRODUCTION-REACHABLE — DEFAULT`, classified
`INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED` and `NOT FIJI FLAT PARITY`.

### Precise MPIPS versus pinned Fiji Flat

| Semantic surface | MPIPS precise | Fiji Flat reference |
|---|---|---|
| Local support | Custom block-center windows | True per-pixel sliding local window |
| LUT placement | Block-center LUT grid | Sliding-window transfer at each pixel |
| Clip calculation | Floating formula with minimum-one clamp | Integer `clipHistogram` semantics |
| Redistribution | Floating redistribution plus residual stepping | Integer redistribution/remainder behavior |
| uint16 | Direct quantization across uint16 range | ShortProcessor 8-bit working representation and ShortApply mapping back to short |
| slope 0.6 | Produces a deterministic numeric output | Pinned retained geometry hits the established execution-domain failure |

These are semantic differences, not a superiority claim for either
implementation.

### Fast/OpenCV alternate contract

`ImageJReplicator.apply_clahe(..., fast=True)` routes to `_clahe_fast` and
`cv2.createCLAHE`. For a single channel it uses `clipLimit=slope` and derives
`tileGridSize=(max(1, width // block_size), max(1, height // block_size))`,
where `block_size=2 * block_radius + 1` (127 for the production settings).
OpenCV handles uint8 and uint16 natively on the single-channel path. A mask,
when supplied, preserves the original working value outside positive mask
pixels. Composite color processing applies the path channel-wise when
`composite=true`; the non-composite path works through an 8-bit LAB image and
restores uint16 by the existing 256 scaling.

This path is `PRODUCTION-REACHABLE — CONFIGURABLE`, `NOT DEFAULT`, and is the
**MPIPS/OPENCV ALTERNATE CONTRACT**. It is classified
`INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED` and `NOT FIJI FASTFLAT PARITY`.

### Fiji Flat and FastFlat reference contracts

Fiji Flat remains **REFERENCE ONLY — NOT PRODUCTION REACHABLE**. Its pinned
contract is a true sliding local window with integer histogram clipping and
redistribution, established displayed/internal bin behavior, retained
execution-domain limits, and ShortProcessor 8-bit working representation plus
ShortApply mapping for uint16.

Fiji FastFlat remains **REFERENCE ONLY — NOT PRODUCTION REACHABLE**. It is a
distinct fixed-block algorithm with its own histogram/LUT construction,
interpolation, clipping behavior, execution limits, and uint16 working
representation. `fast=True` is not evidence of FastFlat equivalence, and
OpenCV CLAHE is not Fiji FastFlat.

| Semantic surface | MPIPS fast/OpenCV | Fiji FastFlat reference |
|---|---|---|
| Block model | OpenCV tile grid derived from image size and block size | Fixed FastFlat block structure |
| Histogram/LUT | OpenCV `createCLAHE` implementation | Fiji FastFlat LUT construction |
| Interpolation | OpenCV tile interpolation | FastFlat interpolation |
| Clipping | OpenCV clip-limit semantics | Fiji integer clipping/redistribution semantics |
| uint16 | Native OpenCV uint16 single-channel processing | Fiji working-representation semantics |

### Dtype, slope, and execution-domain boundaries

The precise and fast paths both preserve uint8 and uint16 single-channel
dtype contracts, but their internal quantization/working behavior differs as
documented above. The slope remains
`INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED`. Option A preserves 0.6
because it preserves current production semantics; it does not establish
optimality, Fiji compatibility, clinical preference, quality superiority, or
an I-5A/I-5B M06 production selection. Parameter ablation and optimization
remain outside Phase 3.

Accepted execution-domain observations for the characterized geometry are
approximately `1.02722168` for Fiji Flat and `1.00394` for Fiji FastFlat.
These are execution-domain boundaries only, not recommendations or
replacements for MPIPS slope 0.6.

### Regression and documentation assessment

Existing `tests/test_imagej_migration.py` sentinels are sufficient for this
minimal semantic closure: precise uint16 CLAHE hash
`5d94b2940b94f2dfbcfe41f130edef7bebfa59fa5a050e7cdbb9bbfbe140dcf6` and
fast/OpenCV uint16 CLAHE hash
`1c4bb383c6e5af18532aff7f0c68e094fdb81c8dc545493758d11e2de8b49ea2`, with
shape and uint16 dtype checks. No tests were modified. Local verification:

```text
.venv/bin/python -m pytest -q tests/test_imagej_migration.py
10 passed
```

The current source docstring says it “replicates” the ImageJ/Fiji CLAHE
plugin, which is misleading under the selected Option A contract. Because
source changes are excluded, this remains bounded documentation debt:
`SOURCE DOCUMENTATION MISNOMER — NO BEHAVIORAL EFFECT`. Correction requires a
later explicitly authorized documentation/source phase.

### Phase 3 unresolved items and limitations

- No CLAHE fidelity-semantic gap remains for the governed MPIPS contracts;
  performance remains Phase 5 and broader sentinel consolidation remains
  Phase 6.
- Circular Median remains unchanged and routed to Phase 4.
- Final umbrella closure remains Phases 6/7; no clinical safety or quality
  recommendation is established.
- Fiji reference execution was not rerun because accepted pinned evidence was
  consistent and no contradiction required regeneration.

No production algorithm, defaults, configuration, tests, reference tooling,
converter, main, deployment, or release action changed in Phase 3.

**Terminal state: Review Required.**

## Phase 6 — Minimal Reference / Regression Sentinel Suite

**Status:** **EXECUTED — REVIEW REQUIRED**. This phase added only minimal
deterministic regression protection. No production algorithm, configuration,
reference tooling, dependency, benchmark, or real-radiograph experiment was
changed or run.

### Governing identity

- Governing task publication: `a92d5283b7c703d03c57b97807b8a7966103fd3f`.
- Accepted Phase-5 baseline: `a625deac10153a2c7c69a3523dd77751518b298e`.
- Accepted Phase-4 implementation baseline:
  `232f148ce24d6df5569a4b2c290e93adf0a03d5f`.
- Pre-execution HEAD: `a92d5283b7c703d03c57b97807b8a7966103fd3f`.
- Branch: `refactor/package-boundaries`.
- Protected converter SHA256 before and after:
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

### Audit and sentinel inventory

| Operation | Accepted contract/status | Existing deterministic protection | Phase-6 action |
|---|---|---|---|
| Contrast Stretch | PARITY CONFIRMED | Accepted uint16 and prior uint8 behavior hashes in `tests/test_imagej_migration.py` | NO NEW SENTINEL REQUIRED |
| Weighted Equalization | PARITY CONFIRMED | Accepted uint8/uint16 hashes in `tests/test_imagej_migration.py` | NO NEW SENTINEL REQUIRED |
| Classic Equalization | PARITY CONFIRMED | Accepted uint8/uint16 hashes in `tests/test_imagej_migration.py` | NO NEW SENTINEL REQUIRED |
| Hybrid Median | REMEDIATED AND PARITY CONFIRMED | Accepted kernel/radius behavior protection in existing tests | NO NEW SENTINEL REQUIRED |
| CLAHE — MPIPS precise | INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED; LEGACY MPIPS CONTRACT; NOT FIJI FLAT PARITY | Existing uint16 hash; divergence was not executable | Added uint16 divergence and uint8 contract sentinels |
| CLAHE — MPIPS fast/OpenCV | INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED; MPIPS/OPENCV ALTERNATE CONTRACT; NOT FIJI FASTFLAT PARITY | Existing uint16 hash; divergence was not executable | Added uint16 divergence and uint8 contract sentinels |
| Fiji Flat reference | REFERENCE ONLY; NOT PRODUCTION REACHABLE | Accepted reference hash from Phase-5 reconstruction smoke | NO NEW SENTINEL REQUIRED; constant used for inequality only |
| Fiji FastFlat reference | REFERENCE ONLY; NOT PRODUCTION REACHABLE | Accepted reference hash from Phase-5 reconstruction smoke | NO NEW SENTINEL REQUIRED; constant used for inequality only |
| Circular Median | REMEDIATED AND PARITY CONFIRMED across accepted I-4A matrix | Complete 10-radius × 2-dtype exact matrix | NO NEW SENTINEL REQUIRED |
| Temporal Median | NOT PRODUCTION REACHABLE — N/A — CLOSED | Reachability status, not production output | NO NEW SENTINEL REQUIRED; refreshed bounded search remains empty |

Existing Contrast Stretch, Equalization, Hybrid Median, and Circular Median
coverage was reused. `tests/test_filtering_processing.py` was unchanged.

### CLAHE uint16 divergence sentinel

The exact accepted reconstruction smoke fixture was generated in memory:

```text
shape: 128 x 128
dtype: uint16
value = (x*257 + y*509 + ((x*y)%251)*131) % 65536
input SHA256: 01941aeb2b4070d224e0271e9ef3f8bd6075001638d4cd75f9bfd06e4b0355c1
```

The common context was slope `1.5`, blocksize `127`, block radius `63`,
displayed histogram bins `256`, internal Fiji bins `255`, and
`composite=True` for MPIPS. Accepted Fiji reference constants were Flat
`b12db91a188b0dccdf2703dc3caa948bab24613e61256ef0002023d147daa34b` and
FastFlat
`b4a4958976bd092c0bc12d4d02b52e80d693549a72ee9ec9a7916cbf319b8fda`.

Two pre-edit runs of each current implementation were deterministic:

| MPIPS contract | Output SHA256 on both runs | Classification |
|---|---|---|
| Precise (`fast=False`) | `cf2067619fe4078bb2294d5449fd0ed2541e0286fda341fa0452af3595b1867d` | LEGACY MPIPS CONTRACT REGRESSION BASELINE |
| Fast/OpenCV (`fast=True`) | `6dc3be3cb86149a8cd8ae9677da482c32cabea0326930d028b2260bac2ceea02` | LEGACY MPIPS CONTRACT REGRESSION BASELINE |

The new parameterized test in `tests/test_imagej_migration.py` asserts the
fixture identity, output shape and uint16 dtype, each frozen Legacy MPIPS
hash, and inequality to its corresponding accepted Fiji reference hash. The
inequality encodes only **INTENTIONAL SEMANTIC DIVERGENCE — GOVERNED**; it is
not a failure, superiority, quality, or clinical claim.

### CLAHE uint8 audit

The bounded repository audit found no explicit accepted uint8 CLAHE golden
sentinel for either MPIPS precise or MPIPS fast/OpenCV. A single parameterized
test was therefore added using `np.arange(64, dtype=np.uint8).reshape(8, 8)`
with input SHA256
`fdeab9acf3710362bd2658cdc9a29e8f9c757fcf9811603a8c447cd1d9151108`,
blocksize `5`, histogram bins `256`, slope `0.6`, and `composite=True`.
Two pre-edit runs of each path were deterministic. The frozen values are
classified as **LEGACY MPIPS CONTRACT REGRESSION BASELINE**, not Fiji
references:

| MPIPS contract | Output SHA256 |
|---|---|
| Precise (`fast=False`) | `4b7790391a5d0fcc5dabc7059b44a6f877df5ea4236252560ba81ec7d578797e` |
| Fast/OpenCV (`fast=True`) | `dee626ac2c1c97e49ff9f810c3429660a40dea9c0ca0b1d9a9a3bad7b53013c9` |

### Temporal Median reachability refresh

The bounded current search found only the standalone
`ImageJReplicator.fast_temporal_median` definition and its documentation/example.
No production caller, configuration, API, schema, workflow, or worker path was
found. Status remains **NOT PRODUCTION REACHABLE — N/A — CLOSED**. No
algorithm-output sentinel was created.

### Routine-regression dependency boundary

**NO JAVA / FIJI RUNTIME / NETWORK REQUIRED BY PHASE-6 ORDINARY PYTEST
SENTINELS.** The new tests use accepted Fiji SHA constants only and execute
through the normal Python MPIPS implementation.

### Verification

All results below are **LOCAL TESTS, NOT CI**:

```text
./.venv/bin/python -m pytest -q tests/test_imagej_migration.py -k 'governed_mpips_divergence or legacy_mpips_contract'
4 passed, 10 deselected

./.venv/bin/python -m pytest -q tests/test_imagej_migration.py
14 passed

./.venv/bin/python -m pytest -q tests/test_filtering_processing.py
39 passed
```

`git diff --check` passed. No Phase-5 benchmark was rerun. The protected
converter hash remained exact before and after.

### Remaining closure gaps

- Final all-operation closure and review remain Phase 7 work; Phase 7 is not
  authorized by this execution.
- Existing source documentation still contains the previously recorded CLAHE
  “replicates” misnomer; correcting it requires separately authorized scope.
- No universal Circular Median parity claim beyond the accepted I-4A matrix is
  made.

### Exact modified files

- `tests/test_imagej_migration.py`
- `.agents/evidence/imagej-fidelity-closure.md`

No task, filtering test, production source, script, dependency, configuration,
schema, API, worker, or reference-harness file changed. Phase-6 execution did
not modify or require Java/Fiji runtime files, and no main/deployment/release
action occurred.

**Terminal state: Review Required.**

## Phase 5 — Bounded Performance Baseline

**Status:** **LOCAL PERFORMANCE CHARACTERIZATION, NOT CI**. This section
records bounded measurements only; the four implementations are semantically
non-equivalent and the timings do not rank image quality, fidelity, or
clinical performance.

### Governing identity

- Governing task publication: `e78e27e85e11996f4e2b5cc85fc3cbef73eaf4d0`
- Accepted Phase-4 baseline: `232f148ce24d6df5569a4b2c290e93adf0a03d5f`
- Accepted reconstruction publication: `e7e3669bcbf0c2e3242b2f44f6bd2b2ac0d422f8`
- Pre-measurement HEAD: `e78e27e85e11996f4e2b5cc85fc3cbef73eaf4d0`

### Accepted reconstructed runtime

Revalidation passed for `/tmp/mpips-imagej-reference-phase5-iY6Lqk`:

- executable Java reported Temurin/OpenJDK `17.0.19+10`; `javac` reported
  `17.0.19`;
- ImageJ `ij-1.54p.jar` existed and matched SHA256
  `2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20`;
- reference classes, harness classes, and `ReferenceHarness.class` existed;
- tracked `ReferenceHarness.java` matched SHA256
  `4dd097ff92002f6d3d6a52ef6d2231e31aa3b32610c8af9e0c9e300559f2bcd5`.

### Environment

Linux WSL2, kernel `6.18.33.2-microsoft-standard-WSL2`, x86_64; CPU
`12th Gen Intel(R) Core(TM) i7-1265U`, 12 logical CPUs; Python `3.12.14`,
NumPy `2.4.6`, SciPy `1.17.1`, OpenCV `4.13.0` with 12 reported threads;
Temurin Java `17.0.19+10`; pinned Fiji commit
`0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0`; reconstructed root as above.
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and
`NUMEXPR_NUM_THREADS` were unset. Thread settings were not changed.

### Controlled fixture

One in-memory C-contiguous single-channel uint16 fixture was shared across
all runs, generated by:

```text
for y in range(1024):
    for x in range(1024):
        value = (x*257 + y*509 + ((x*y)%251)*131) % 65536
```

Shape `1024 x 1024`; dtype `uint16`; minimum `0`; maximum `65535`; input
SHA256 `70f5d243cbd130bdf30009f50711179d7e9d9f725dabef9c808be37a7c614858`.
The harness input contained exactly `1,048,576` values and was prepared in
temporary storage outside the timed process execution.

### Context A — MPIPS production parameters

Parameters were `blocksize=127`, displayed `histogram_bins=256`,
`slope=0.6`, `composite=True`. Precise (`fast=False`) is the current default;
fast/OpenCV (`fast=True`) is configurable and not default. Slope `0.6` is
`INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED`.

Each tuple ran in a fresh Python child: one untimed warm-up, then three timed
`time.perf_counter()` calls containing only `ImageJReplicator.apply_clahe`.
RSS is **PYTHON CHILD PROCESS MAX RSS — PROCESS-LEVEL, INCLUDES INTERPRETER
AND LOADED LIBRARIES**, not algorithm-exclusive allocation.

| Implementation / slope | Individual seconds | Median | Min–max | Output SHA256 (each run) | Shape/dtype | Determinism | Max RSS KB |
|---|---:|---:|---:|---|---|---|---:|
| MPIPS precise / 0.6 | 1.628050159, 1.569099018, 1.583727094 | 1.583727094 | 1.569099018–1.628050159 | `1c20709fd9df718ece101ab8495ff63a66a4114ed043f40eedf518a458ec12aa` | 1024x1024 / uint16 | PASS | 170584 |
| MPIPS fast/OpenCV / 0.6 | 0.005585588, 0.005403822, 0.004844453 | 0.005403822 | 0.004844453–0.005585588 | `6c09a5bcbb9778a84571b9fd6273e7c427ce7610bc843558ab0918eb0bb71f7d` | 1024x1024 / uint16 | PASS | 164444 |

### Context B — common executable parameters

Parameters were slope `1.5`, blocksize `127`, block radius `63`, displayed
bins `256`, internal Fiji bins `255`, and `composite=True` for MPIPS. Slope
`1.5` is a common executable runtime-characterization value only; it is not a
production, quality, clinical, optimized, or replacement value for `0.6`.

MPIPS timing scope and RSS semantics were the same as Context A.

| Implementation / slope | Individual seconds | Median | Min–max | Output SHA256 (each run) | Shape/dtype | Determinism | Max RSS KB |
|---|---:|---:|---:|---|---|---|---:|
| MPIPS precise / 1.5 | 1.568529932, 1.524837515, 1.550276505 | 1.550276505 | 1.524837515–1.568529932 | `549f3d1a6d91153e74aa67c5bb9ea843360e5c6245d1b82993a757b08c0264cc` | 1024x1024 / uint16 | PASS | 170468 |
| MPIPS fast/OpenCV / 1.5 | 0.005421374, 0.008350507, 0.004395398 | 0.005421374 | 0.004395398–0.008350507 | `6c09a5bcbb9778a84571b9fd6273e7c427ce7610bc843558ab0918eb0bb71f7d` | 1024x1024 / uint16 | PASS | 164484 |
| Fiji Flat / 1.5 | 2.188214484, 2.092817912, 2.095351675 | 2.095351675 | 2.092817912–2.188214484 | `86a13b858102807c5353ec1430b08e0f1e924dfa1d95161fcda288a1bcfb0e6e` | 1024x1024 / uint16; 1,048,576 values | PASS | 277248–279792 |
| Fiji FastFlat / 1.5 | 1.508505964, 1.864892977, 2.227222911 | 1.864892977 | 1.508505964–2.227222911 | `6a2fa0b3624173286685048a6f433b135dde3a4eb73ae625fd59288a38f843a9` | 1024x1024 / uint16; 1,048,576 values | PASS | 223076–275216 |

Every Fiji run exited with code `0`. Every Fiji time is
**REFERENCE HARNESS END-TO-END WALL TIME — INCLUDES JVM/PROCESS STARTUP,
INPUT PARSING, ALGORITHM EXECUTION, AND HARNESS OUTPUT SERIALIZATION**.
Fiji RSS is **JAVA PROCESS MAX RSS — REFERENCE HARNESS END-TO-END**, measured
with `/usr/bin/time -v`.

### Real radiograph

FULL-RESOLUTION RADIOGRAPH MEASUREMENT NOT PERFORMED — RETAINED LOCAL INPUT
UNAVAILABLE

### Determinism and interpretation

All six implementation/input/parameter tuples produced identical output
hashes across their three repetitions. Cross-implementation hash differences
are expected under the governed semantic classifications. The measured
performance facts are limited to this single environment, this bounded
synthetic fixture, and the timing scopes above. MPIPS precise and fast/OpenCV
were directly comparable only within the same fresh-child Python scope; Fiji
times include JVM/process and I/O overhead and are not warm in-process Python
timings. RSS is process-level, not algorithm-exclusive. No image-quality,
fidelity-superiority, scientific-validity, or clinical conclusion is made.

### Performance-only conclusions

Under the exact tested scopes, MPIPS fast/OpenCV had lower measured wall time
than MPIPS precise in both tuples. This is a runtime observation only and does
not establish quality, fidelity, default-selection, or production suitability.

**NO PRODUCTION CONFIGURATION OR OPTIMIZATION DECISION IS AUTHORIZED BY
PHASE 5.** No source, algorithm, parameter, threading, configuration, or
ReferenceHarness change was made.

**Terminal state: Review Required.**

## Phase 4 — Circular Median Radius-Domain / Reachability Resolution

### Governing identity and first-gate result

- Governing task revision: `aec68e1b933ec86d54d42b7499366bd038a41a78`.
- Accepted Phase-3 baseline: `8c7b479947ee2b67856fd644e95b6d9eede52739`.
- Pre-evidence HEAD: `aec68e1b933ec86d54d42b7499366bd038a41a78`.
- First gate: **CIRCULAR MEDIAN RADIUS-DOMAIN / REACHABILITY RESOLUTION**.
- Selected outcome: **PLANNING REQUIRED — CIRCULAR MEDIAN REMEDIATION**.

The outcome is required because a positive fractional radius such as `1.5`
can be supplied through the structured canonical configuration path and reach
`circular_imagej`. The accepted failures at radii `1.5` and `2.5` therefore
are not limited to direct-library use. No remediation or contract tightening
was performed.

### Production trace and default boundary

The current DICOM trace is:

```text
POST /v1/radiographs/dicom
  -> run_isolated_dicom_conversion()
  -> execute_conversion_worker()
  -> process_radiography_arrays(config=None)
  -> ImagerPipelineConfig()
  -> RadiographyPipeline.process()
  -> apply_median_filter(...)
```

The worker does not accept or construct an `ImagerPipelineConfig`; the
canonical pipeline therefore constructs the default config. The default is
`use_median_filter=true`, `median_filter_type="hybrid_imagej"`, and
`median_filter_radius=2`. Circular Median is not selected on this route and
is not the current default production behavior. The file runner and batch
workflow accept an explicit config object, but they are distinct configurable
workflow surfaces rather than the DICOM endpoint's request schema.

### Radius-domain and reachability matrix

| Surface | Reachable / Circular selectable | Declared type | Runtime validation/coercion | Actual radius domain | Classification |
|---|---|---|---|---|---|
| DICOM default route | Reachable; circular not selectable from request; default Hybrid only | Config defaults `int`, value 2 | `process_radiography_arrays(config=None)` constructs defaults; no custom radius input | Fixed default 2; Circular Median unreachable on this route | Production default |
| Direct `RadiographyPipeline(config=...)` | Yes, when supplied a config with `circular_imagej` | Config field `int` annotation | Constructor `_validate()` checks only `radius > 0`; no integer check/coercion | Arbitrary positive numeric, including fractional | Configurable canonical pipeline |
| `ImagerPipelineConfig(...)` | Yes | `median_filter_radius: int` | No runtime `isinstance` or `int()` check; only positivity check | Arbitrary positive numeric, including fractional | Configurable production-adjacent |
| `ImagerPipelineConfig.from_dict()` structured | Yes | Structured `radius` has no runtime schema type | Value is forwarded unchanged to constructor; only positivity check applies | Fractional possible; probe accepted `1.5` | Configurable canonical config |
| `ImagerPipelineConfig.from_dict()` flat | Yes | Flat value passed through `**data` | Same constructor behavior; no integer coercion | Fractional possible; probe accepted `1.5` | Configurable canonical config |
| `ImagerPipelineConfig.from_env()` / CLI | Yes through CLI/file workflow | Mapping declares `int` | `int(raw_val)` is explicit; `"1.5"` raises `ValueError` | Integer text only; fractional text rejected | Configurable workflow surface |
| API/schema DICOM request | No processing config field | Manifest schemas contain no median config | `extra="forbid"`; no radius field exposed | Unreachable from current API request | Not API-reachable |
| Worker/DICOM construction | Reachable only through default pipeline construction | No radius/config argument in worker call | No custom config is forwarded | Fixed default Hybrid path; no Circular selection or custom radius | Production worker path |
| File runner / batch workflow | Yes with explicit config object | Config object as above | Delegates unchanged to pipeline | Arbitrary positive numeric if config was constructed accordingly | Configurable workflow surface |
| Direct `apply_median_filter()` | Yes with `filter_type="circular_imagej"` | `radius: int` annotation | No runtime type check; calls `float(radius)` | Positive numeric, including fractional; probe accepted `1.5` | Library adapter |
| Direct `ImageJReplicator.median_filter_imagej()` | Yes | `radius: float` | Checks only `radius > 0` | Positive numeric, including fractional | Direct library only |

The API/schema conclusion is limited to the current DICOM endpoint and its
manifest models. Importable Python and workflow objects must not be called
API-reachable merely because they are configurable.

### Accepted I-4A characterization

The retained pinned ImageJ 1.54p `RankFilters` comparisons report the same
classification for uint8 and uint16. The metrics below are transcribed from
the accepted I-4A JSON; `mismatch count` and `interior mismatches` are distinct
fields.

| Radius | Dtype | Mismatch count | Mismatch fraction | Interior mismatches | Max absolute difference | Classification |
|---:|---|---:|---:|---:|---:|---|
| 0.5 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 1.0 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 1.5 | uint8 | 11 | 0.44 | 3 | 3 | FIDELITY FAILURE |
| 1.74 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 1.75 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 2.0 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 2.5 | uint8 | 8 | 0.32 | 5 | 2 | FIDELITY FAILURE |
| 2.84 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 2.85 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 3.0 | uint8 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 0.5 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 1.0 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 1.5 | uint16 | 11 | 0.44 | 3 | 771 | FIDELITY FAILURE |
| 1.74 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 1.75 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 2.0 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 2.5 | uint16 | 8 | 0.32 | 5 | 514 | FIDELITY FAILURE |
| 2.84 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 2.85 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |
| 3.0 | uint16 | 0 | 0.0 | 0 | 0 | PARITY CONFIRMED |

These are accepted sampled cases only and are not extrapolated to all
positive radii.

### Runtime validation and fractional reachability

The config and adapter annotations express integer intent but do not enforce
it. `ImagerPipelineConfig._validate()` tests only `median_filter_radius <= 0`;
it performs no `isinstance(radius, int)`, `int(radius)`, or integral-value
check. Structured and flat `from_dict()` both preserve a float radius. The
read-only probe constructed valid circular configs with `1.5`, and direct
`apply_median_filter()` and `median_filter_imagej()` accepted and processed
that radius. Conversely, `from_env()` maps `MEDIAN_FILTER_RADIUS` to `int` and
rejects `"1.5"` before config construction.

Thus fractional radius is configurable through canonical structured config
and can reach `RadiographyPipeline`/the circular dispatch when a caller
supplies that config. It is not reachable through the current DICOM request
schema or worker construction, and it is not the default path.

### Reference and implementation structural assessment

`_make_circular_kernel_imagej()` uses the retained ImageJ-style
`int(radius * radius) + 1` footprint construction, and
`median_filter_imagej()` uses SciPy `median_filter(..., mode="nearest")` for
the duplicate-edge behavior. This explains why many sampled footprints match,
but it does not establish universal parity for every positive integer radius:
the current configuration has no upper bound, the accepted matrix samples
only selected radii, and the retained evidence does not prove equivalence of
all ImageJ RankFilters special cases or all edge/median-selection behavior.
The 1.5 and 2.5 failures are footprint/semantic divergences in the existing
float-capable implementation; this gate does not assign a narrower causal
claim or modify it. uint8 and uint16 show the same radius classification, with
dtype-specific mismatch magnitudes.

No additional Fiji/Java reference execution or expanded characterization was
performed. The only new checks were the bounded local Python configuration and
direct-call probe above.

### Outcome, smallest likely remediation surface, and limits

**PLANNING REQUIRED — CIRCULAR MEDIAN REMEDIATION**

The exact reachable failing path is:

```text
ImagerPipelineConfig.from_dict({"median_filter": {
  "type": "circular_imagej", "radius": 1.5
}})
  -> ImagerPipelineConfig._validate() [positive-only]
  -> RadiographyPipeline(config).process()
  -> apply_median_filter(..., "circular_imagej", 1.5)
  -> ImageJReplicator.median_filter_imagej(..., radius=1.5)
```

The smallest likely remediation decision is whether the governed config
contract should reject/coerce fractional radii at its boundary or whether the
Circular Median implementation should be remediated to match ImageJ for the
fractional domain. Either choice requires explicit later authorization,
targeted tests/reference verification, and consistent handling across
constructor, structured config, CLI/environment, workflow, and any future API
surface. This gate performs none of those changes.

No clinical or quality claim is made. Phase 5+ remain unauthorized, the
accepted CLAHE classifications are unchanged, and Circular Median remains
the only unresolved subject of this first gate.

**Terminal state: Planning Required — Circular Median Remediation.**

## Phase 4 — Circular Median Fidelity Remediation

### Governing identity and bounded execution

- Governing task publication: `98d0d9eadee94f0c801eb8ada97491870a1dae4d`.
- Accepted first-gate baseline: `84b4a8cd271fcf7b262bd625530a974357704f9b`.
- Pre-remediation HEAD: `98d0d9eadee94f0c801eb8ada97491870a1dae4d`.
- Remediation: **IMAGEJ RANKFILTERS SEMANTIC REMEDIATION**.
- No integer-only contract tightening was introduced.

The targeted root cause was the omission of ImageJ 1.54p
`RankFilters.makeLineRadii(double radius)` compatibility normalization in
`ImageJReplicator._make_circular_kernel_imagej()`. Before the existing
`r2 = int(radius * radius) + 1` calculation, the implementation now maps
`1.5 <= radius < 1.75` to effective radius `1.75` and
`2.5 <= radius < 2.85` to effective radius `2.85`. The existing footprint
construction, SciPy `median_filter`, `mode="nearest"`, median selection,
dtype handling, channel handling, validation, and public signature are
unchanged.

### Fixture and accepted reference matrix

The test uses the accepted I-4A 5x5 `median_grid` fixture:

```text
[[9, 2, 7, 4, 6],
 [3, 8, 1, 5, 0],
 [6, 4, 9, 2, 7],
 [5, 1, 8, 3, 6],
 [0, 7, 2, 9, 4]]
```

The uint8 fixture is direct; uint16 is the same fixture multiplied by 257.
The accepted reference hashes are:

| Dtype | Radius 0.5 | 1.0 | 1.5 | 1.74 | 1.75 | 2.0 | 2.5 | 2.84 | 2.85 | 3.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| uint8 | `5157cd80de4ea935cee4a786a516ff7f2041260c36fdb0ccb67fa682e82c0992` | `0fcd11108eedbad87ff6f194652203a9478e0e997024716a46db80748ef5bb3b` | `e72a4b5f10de3bd85f019d2cea69faec40726c470bc7217984ec849e92a52de7` | `e72a4b5f10de3bd85f019d2cea69faec40726c470bc7217984ec849e92a52de7` | `e72a4b5f10de3bd85f019d2cea69faec40726c470bc7217984ec849e92a52de7` | `89b7c92981dbe70477e5e60a21ef40d927ffeb270212b097699d401a74bef8c7` | `90e689333cf6fe68d803bd0f087ff303e67e23f6c821d0969b5bdd13dfd597b0` | `90e689333cf6fe68d803bd0f087ff303e67e23f6c821d0969b5bdd13dfd597b0` | `90e689333cf6fe68d803bd0f087ff303e67e23f6c821d0969b5bdd13dfd597b0` | `8e4e5923599608e8bbe2f7834794f8881475a32e6db199cd70ac50668634a6d1` |
| uint16 | `591fb6b495566b159d3608336c22e84074ba41eaa092677626206f63eff29ad9` | `12cba42e4296eac0dd557f6a9106f1acba6073014076bae71f2701bb0504a6c5` | `b9a0490d260ecc63e135441b67389da4b756de8e4b1c053c3a9d02ffa6d37b05` | `b9a0490d260ecc63e135441b67389da4b756de8e4b1c053c3a9d02ffa6d37b05` | `b9a0490d260ecc63e135441b67389da4b756de8e4b1c053c3a9d02ffa6d37b05` | `af5398c57504217097440e2a525bb1b2026315083306d7f36a9d27430504a7a8` | `b2047c7fe0fcdfb4c1cdeaf540414771ac56938da77d73d280f3a96ad54ceec6` | `b2047c7fe0fcdfb4c1cdeaf540414771ac56938da77d73d280f3a96ad54ceec6` | `b2047c7fe0fcdfb4c1cdeaf540414771ac56938da77d73d280f3a96ad54ceec6` | `b65b95665a2d108ad31a02b7b66554b22f77a2418f880db0d6c97c90be64605c` |

### Results and claim boundary

The required transition cases (`1.5`, `1.74`, `1.75`, `2.5`, `2.84`, `2.85`)
and non-regression cases (`0.5`, `1.0`, `2.0`, `3.0`) all matched the accepted
reference hashes for both dtypes: **20/20 passed**. The final classification
is:

`REMEDIATED AND PARITY CONFIRMED ACROSS ACCEPTED I-4A CHARACTERIZATION MATRIX`

This does not establish universal parity for all positive radii. The
configuration domain remains broader than the accepted matrix.

### Verification and preserved boundaries

```text
.venv/bin/python -m pytest -q tests/test_filtering_processing.py -k circular_median_matches_accepted_i4a_matrix
20 passed, 19 deselected

.venv/bin/python -m pytest -q tests/test_filtering_processing.py
39 passed

.venv/bin/python -m pytest -q tests/test_imagej_migration.py
10 passed
```

These are **LOCAL TESTS, NOT CI**. The test file was modified only to add the
accepted reference-backed Circular Median matrix; no new test file was
created. The stable evidence file was also updated. No config parsing,
validation, API/schema, worker, DICOM default, Hybrid Median, CLAHE, or
converter behavior changed. Integer-oriented annotations remain
`TYPING / CONTRACT-DOCUMENTATION DEBT — NO RUNTIME EFFECT`.

The protected converter SHA remained
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` before
and after. Phase 5+ remain unauthorized; no performance, deployment, release,
or main action occurred.

**Terminal state: Review Required.**

## Direct reachability observations

- `ImagerPipelineConfig` defaults are `use_contrast_enhancement=true`,
  `contrast_mode="equalize"`, `contrast_classic_equalization=false`,
  `use_clahe=true`, `clahe_blocksize=127`, `clahe_histogram_bins=256`,
  `clahe_max_slope=0.6`, `clahe_fast=false`, `clahe_composite=true`,
  `use_median_filter=true`, `median_filter_type="hybrid_imagej"`, and
  `median_filter_radius=2` (`mpips/pipelines/config.py:103-123`).
- `RadiographyPipeline.process` calls weighted/classic contrast according to
  config, then `ImageJReplicator.apply_clahe`, then median dispatch
  (`mpips/pipelines/radiography.py:100-155`). Its working image is converted
  to uint16 before the ImageJ-derived stages and its return contract is uint16.
- The DICOM worker invokes the canonical array workflow without a replacement
  config (`mpips/conversion/worker.py:239-248`); the registered route invokes
  the isolated conversion service (`mpips/api/routes/v1/dicom.py:273-281`).
- Circular Median is not merely a dead function: its `circular_imagej` value
  is accepted by the config enum/schema and dispatches to the implementation.
  It is configurable reachability, not default reachability.
- Temporal Median occurs only as a static method and module documentation;
  refreshed search found no current caller or configuration/API/schema exposure.
- No additional current production operation was found that is both
  ImageJ/Fiji-derived or inspired and outside the matrix above.

## Prior status versus current verification

The accepted prior statuses were verified rather than copied. Hybrid Median
remediation evidence establishes exact accepted parity and the current source
still contains that implementation. I-4C0 establishes that MPIPS precise and
fast CLAHE are distinct from Fiji Flat and FastFlat, and that the execution-safe
slope observations are not quality recommendations. I-5A remains exploratory
with production HOLD; I-5B remains closed and is not reopened. No contradiction
against accepted evidence was found.

## Unresolved gaps and later routing

1. MPIPS precise and fast CLAHE require the Phase 3 semantic decision. This
   inventory does not choose Legacy MPIPS, Fiji Flat, or Fiji FastFlat.
2. Circular Median requires Phase 4 reachability-aware fidelity resolution.
3. Runtime questions belong to Phase 5; no performance work was done here.
4. Final umbrella closure belongs to Phases 6 and 7.

## Phase boundary and terminal state

Phase 2 performed only the authorized sentinel and reachability closure. No
production remediation, configuration/schema change, reference-tooling change,
threshold/stage-order work, benchmark, deployment, release, or semantic CLAHE
selection occurred. The Phase 2 limitations are that tests are local rather
than CI, no clinical safety claim is made, and this artifact does not establish
a quality recommendation or final production semantic contract.

**Terminal state: Review Required.**
