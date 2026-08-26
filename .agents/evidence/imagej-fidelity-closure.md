# MPIPS ImageJ/Fiji Fidelity Closure — Phase 1 Inventory

Status: **Review Required**. This artifact is the Phase 1 inventory and
production-reachability closure for the published umbrella task. It records
observed implementation reality; it does not select a CLAHE semantic contract
or change production behavior.

## Governing identity and preflight

| Item | Observed value |
|---|---|
| Governing task | `.agents/tasks/imagej-fidelity-closure.md` |
| Exact governing task revision | `a75353a6880227b2eda4aeea83437a968748c2c0` |
| Accepted implementation baseline | `8396fbc768285cc68ed3bbe572561cd664b70e8b` |
| Execution revision / pre-evidence HEAD | `a75353a6880227b2eda4aeea83437a968748c2c0` |
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

## Authoritative closure matrix

| Operation | REFERENCE | MPIPS IMPLEMENTATION | PRODUCTION REACHABILITY | DEFAULT REACHABILITY | DTYPE | PRIOR ACCEPTED STATUS | CURRENT VERIFIED STATUS | UNRESOLVED GAP | NEXT REQUIRED PHASE |
|---|---|---|---|---|---|---|---|---|---|
| Contrast Stretch | ImageJ `ContrastEnhancer` normalized stretch | `ImageJReplicator.enhance_contrast(equalize=False, normalize=True)`; wrappers in `mpips/processing/radiography.py` | PRODUCTION-REACHABLE — CONFIGURABLE; `contrast_mode="stretch"` | NOT DEFAULT; default mode is `equalize` | uint8, uint16; pipeline converts to uint16 | PARITY CONFIRMED | PARITY CONFIRMED on accepted uint8/uint16 characterization; no contradictory current evidence | Regression sentinel remains to be added/retained in later closure | Phase 2 — accepted parity sentinel |
| Equalization — weighted ImageJ variant | ImageJ `ContrastEnhancer` weighted/sqrt histogram equalization | `ImageJReplicator._equalize_imagej_variant(classic_equalization=False)` via `enhance_contrast` | PRODUCTION-REACHABLE — DEFAULT | PRODUCTION-REACHABLE — DEFAULT; `contrast_mode="equalize"`, `classic=false` | uint8, uint16; pipeline working output uint16 | PARITY CONFIRMED | PARITY CONFIRMED on accepted uint8/uint16 characterization | Regression sentinel remains to be added/retained in later closure | Phase 2 — accepted parity sentinel |
| Equalization — classic | ImageJ `ContrastEnhancer` classic histogram equalization | `ImageJReplicator._equalize_imagej_variant(classic_equalization=True)`; config `contrast_classic_equalization` | PRODUCTION-REACHABLE — CONFIGURABLE | NOT DEFAULT; weighted variant is default | uint8, uint16; pipeline working output uint16 | PARITY CONFIRMED | PARITY CONFIRMED on accepted uint8/uint16 characterization | Regression sentinel remains to be added/retained in later closure | Phase 2 — accepted parity sentinel |
| Hybrid Median | Pinned `Hybrid_2D_Median_Filter.java` | `ImageJReplicator.hybrid_median_filter_2d`; `filtering.apply_median_filter("hybrid_imagej")` maps radius 2 to 5x5 | PRODUCTION-REACHABLE — DEFAULT; pipeline calls median dispatch | PRODUCTION-REACHABLE — DEFAULT; `use_median_filter=true`, type `hybrid_imagej`, radius 2 | uint16 in radiography; implementation also preserves uint8/uint16 | REMEDIATED AND PARITY CONFIRMED | REMEDIATED AND PARITY CONFIRMED; accepted direct uint8/uint16 3x3, 5x5, 7x7 and repeated 5x5 evidence remains consistent | No Phase 1 gap; regression protection is still a later task concern | Phase 2 — accepted parity sentinel |
| CLAHE — MPIPS precise | Fiji `Flat` semantics used as reference identity; MPIPS contract is separate | `ImageJReplicator.apply_clahe(..., fast=False)` -> `_clahe_precise`; displayed bins 256 maps to internal bins 255; blocksize 127 maps to radius 63 | PRODUCTION-REACHABLE — DEFAULT when ImageJ processing is available | PRODUCTION-REACHABLE — DEFAULT; `use_clahe=true`, `fast=false`, slope 0.6, bins 256, blocksize 127, composite true | uint16 on radiography; implementation supports uint8/uint16 | FIDELITY FAILURE; not Fiji Flat parity | FIDELITY FAILURE remains verified; MPIPS returns numeric output at slope 0.6 while pinned Fiji runtime errors on the retained runtime geometry | Semantic contract and production fidelity divergence are unresolved; slope 0.6 is inherited with rationale not recovered | Phase 3 — CLAHE semantic closure; Phase 5 runtime measurement if later authorized |
| CLAHE — MPIPS fast/OpenCV | Fiji `FastFlat` semantics used as reference identity; MPIPS contract is separate | `ImageJReplicator.apply_clahe(..., fast=True)` -> OpenCV `createCLAHE` path | PRODUCTION-REACHABLE — CONFIGURABLE | NOT DEFAULT; `clahe_fast=false` | uint16 on radiography; implementation supports uint8/uint16 | FIDELITY FAILURE; not Fiji FastFlat parity | FIDELITY FAILURE remains verified; current code is an OpenCV-based alternate semantics | Semantic contract and parity divergence remain unresolved | Phase 3 — CLAHE semantic closure; Phase 5 runtime measurement if later authorized |
| Fiji CLAHE Flat reference | Pinned `axtimwalde/mpicbg` `Flat.java` and supporting `Apply`/`ShortApply` code | No Java/Fiji runtime in MPIPS production path; retained reference tooling only | NOT PRODUCTION-REACHABLE | NOT DEFAULT | Reference execution is byte working domain with ShortProcessor remapping; uint8/uint16 cases characterized | REFERENCE ONLY / FIDELITY FAILURE against MPIPS | REFERENCE ONLY; pinned identity and execution boundaries are established, not a production implementation | Product/technical semantic choice is not made here | Phase 3 — semantic closure |
| Fiji CLAHE FastFlat reference | Pinned `axtimwalde/mpicbg` `FastFlat.java` and supporting fast apply code | No Java/Fiji runtime in MPIPS production path; retained reference tooling only | NOT PRODUCTION-REACHABLE | NOT DEFAULT | Reference uses byte working domain and dtype-specific ShortProcessor remapping | REFERENCE ONLY / FIDELITY FAILURE against MPIPS | REFERENCE ONLY; distinct fixed-block/interpolation algorithm is established | Product/technical semantic choice is not made here | Phase 3 — semantic closure |
| Circular Median | ImageJ core `RankFilters.MEDIAN` circular-kernel semantics | `ImageJReplicator.median_filter_imagej`; `filtering.apply_median_filter("circular_imagej")` | PRODUCTION-REACHABLE — CONFIGURABLE; config enum/schema and median dispatch can activate it | NOT DEFAULT; default type is `hybrid_imagej` | uint16 on radiography; implementation supports uint8/uint16 | FIDELITY FAILURE for accepted special-radius cases; exposed alternative, not active default | Reachability confirmed. Current implementation remains parity-sensitive: accepted characterization found failures at radii 1.5 and 2.5, with other tested radii exact | Fidelity status for all supported/configurable radii is unresolved; no remediation performed | Phase 4 — Circular Median resolution |
| Temporal Median | ImageJ `Fast_Temporal_Median.java` plugin identity | `ImageJReplicator.fast_temporal_median(stack, ...)` only; no wrapper/config/pipeline caller found | NOT PRODUCTION-REACHABLE | NOT DEFAULT | Library method accepts 3D uint8/uint16 stacks | NOT PRODUCTION-REACHABLE — N/A | NOT PRODUCTION-REACHABLE — N/A; current caller search found no production API, workflow, config, or schema path | No production fidelity obligation established; standalone method remains outside current production surface | Phase 2 — close as N/A if review accepts current reachability |

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
  no current caller or configuration/API/schema exposure was found.
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

1. Contrast Stretch, weighted Equalization, classic Equalization, and accepted
   Hybrid Median need the Phase 2 sentinel/closure treatment; no new fidelity
   repair is indicated.
2. MPIPS precise and fast CLAHE require the Phase 3 semantic decision. This
   inventory does not choose Legacy MPIPS, Fiji Flat, or Fiji FastFlat.
3. Circular Median requires Phase 4 reachability-aware fidelity resolution.
4. Runtime questions belong to Phase 5; no performance work was done here.
5. Regression protection and final umbrella closure belong to Phases 6 and 7.

## Phase boundary and terminal state

Phase 1 performed inventory and characterization only. No remediation, source,
configuration, schema, test, reference-tooling, threshold, stage-order,
performance, deployment, release, or semantic CLAHE selection occurred.
The Phase 1 limitations are the accepted evidence limits: reachability was
verified statically, no clinical safety claim is made, and this artifact does
not establish a quality recommendation or final production semantic contract.

**Terminal state: Review Required.**
