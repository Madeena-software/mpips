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
| Circular Median | ImageJ core `RankFilters.MEDIAN` circular-kernel semantics | `ImageJReplicator.median_filter_imagej`; `filtering.apply_median_filter("circular_imagej")` | PRODUCTION-REACHABLE — CONFIGURABLE; config enum/schema and median dispatch can activate it | NOT DEFAULT; default type is `hybrid_imagej` | uint16 on radiography; implementation supports uint8/uint16 | FIDELITY FAILURE for accepted special-radius cases; exposed alternative, not active default | Reachability confirmed. Current implementation remains parity-sensitive: accepted characterization found failures at radii 1.5 and 2.5, with other tested radii exact | Fidelity status for all supported/configurable radii is unresolved; no remediation performed | Phase 4 — Circular Median resolution |
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
