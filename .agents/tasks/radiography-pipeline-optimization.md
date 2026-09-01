---

title: Radiography Pipeline Optimization
document_id: TASK-RADIOGRAPHY-PIPELINE-OPTIMIZATION-001
version: 1.1
status: Validated/Published
language: en-US
authority_note: >-
  This task authorizes evidence-driven optimization of the existing canonical
  radiography processing flow while preserving the accepted behavior and
  boundaries established by the closed Main Hotfix Reconciliation. It does not
  authorize new image-processing policy, calibration-policy changes, DICOM
  conversion changes, deployment, release, or production mutation.
---

# Executable Task

## Task identity

**Task title:**
`Radiography Pipeline Optimization`

**Task path:**
`.agents/tasks/radiography-pipeline-optimization.md`

**Task contract state:**
`Validated/Published`

**Delivery objective / Work Package / MVP:**
`Radiography Pipeline Optimization after Main Hotfix Reconciliation`

## Baseline and task revision

**Implementation baseline:**

`d43397427d817a997bb1eb6eb4fe065470588b05`

**Task revision:**

The exact immutable Git revision containing this published task must be returned by the publication Executor and accepted by Planner/Reviewer before implementation begins.

The implementation baseline and governing task revision are separate identities.

## Delivery context

Main Hotfix Reconciliation is accepted/closed.

The accepted canonical array-processing path is:

`mpips.workflows.imager_pipeline.pipeline.process_radiography_arrays()`

→ `mpips.pipelines.radiography.RadiographyPipeline.process()`

→ canonical processing primitives under `mpips.processing`.

Optimization must improve measurable performance without altering accepted image-processing semantics.

Profiling is part of this optimization delivery objective and is not a separate top-level task.

## Objective

Improve performance of the canonical radiography processing path based on measured bottlenecks while preserving accepted output behavior, configuration semantics, architecture boundaries, and compatibility.

Profiling must precede production implementation changes.

Do not retain an optimization merely because it appears theoretically faster.

A retained optimization must demonstrate reproducible measured improvement beyond observed benchmark noise while satisfying semantic regression requirements.

If profiling finds no safe and meaningful bounded optimization, return that evidence rather than forcing implementation.

## Governing authority

* `AGENTS.md`
* `.agents/AGENTS.md`
* `.agents/software-workflow.md`
* `.agents/context/project.md`
* applicable scoped repository instructions
* current Human Request
* closed `.agents/tasks/main-hotfix-reconciliation.md` v1.14
* accepted Phase-8 evidence at `4c6ed59743568d5139db8e56cd3f014d5381bfba`
* accepted baseline `d43397427d817a997bb1eb6eb4fe065470588b05`

## Primary implementation evidence

* `mpips/pipelines/radiography.py`
* `mpips/pipelines/config.py`
* `mpips/workflows/imager_pipeline/pipeline.py`
* relevant canonical modules under `mpips/processing/`
* `tests/test_radiography_pipeline.py`
* `tests/test_imager_pipeline_workflow.py`
* relevant threshold, geometry, ImageJ/Fiji, calibration-remap, and converter-protection tests

Observed implementation is evidence of current reality and does not authorize semantic changes.

## In scope

* reproducible baseline profiling of the canonical radiography pipeline;
* representative BED and TRX benchmark scenarios;
* end-to-end timing;
* stage attribution sufficient to identify material bottlenecks;
* peak process memory measurement when practical with existing tooling;
* reduction of unnecessary copies, dtype conversions, allocations, redundant calculations, or repeated object construction;
* bounded changes to canonical pipeline/processing implementation justified by profiling;
* bounded benchmark/profiling support;
* regression tests necessary to demonstrate preservation;
* read-only use of existing representative inputs where available;
* deterministic synthetic benchmark fixtures where appropriate.

## Out of scope

* image-quality recipe redesign;
* stage reordering that changes accepted output semantics;
* threshold algorithm or policy changes;
* BED threshold bypass;
* TRX threshold-policy changes;
* TRX orientation changes;
* ImageJ/Fiji fidelity changes;
* CLAHE parameter/policy changes;
* denoise/filtering-policy changes;
* calibration generation-policy changes;
* numeric expanded-remap `0.80` gate adoption;
* canonical `fixed → expanded` default switch;
* calibration carrier promotion/substitution;
* DICOM conversion changes;
* modification of `mpips/conversion/tiff_json_to_dcm.py`;
* API behavior changes;
* worker/Celery/distributed-concurrency optimization;
* GPU/CUDA implementation;
* approximate image-processing algorithms;
* deployment/Docker/build-cache optimization;
* production or release work;
* unrelated refactoring.

## Preserved behavior

The implementation must preserve:

* BED configured-threshold behavior;
* TRX threshold bypass;
* TRX canonical clockwise orientation;
* crop/rotation semantics;
* calibration-remap source-domain semantics;
* expanded remap support;
* invalid-remap zeroing;
* input/map immutability;
* `uint16` output;
* accepted output geometry;
* configuration defaults;
* ImageJ/Fiji fidelity;
* canonical package/import boundaries;
* protected converter integrity.

Protected converter SHA-256:

`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`

Calibration default remains:

`fixed`

Expanded mode remains opt-in.

Numeric expanded-remap acceptance thresholds remain unadopted.

## Execution slices

This is one umbrella task.

### Slice A — Baseline and profiling

Before production implementation changes:

* record exact execution-start SHA;
* establish deterministic benchmark scenarios;
* distinguish BED and TRX;
* include representative remap geometry where applicable;
* warm runtime before steady-state measurement;
* run repeated measurements;
* record environment/workload identity;
* identify material bottlenecks.

Where practical, distinguish major costs including:

* uint16/float conversions;
* initial denoise;
* flat-field correction;
* remap and valid-mask construction;
* crop/rotation;
* threshold handling;
* inversion;
* contrast;
* CLAHE;
* optional final denoise;
* median filtering;
* final masking/output conversion.

Profiling instrumentation must not silently become a required public runtime feature.

### Slice B — Bounded optimization

Implement only changes supported by Slice-A measurements.

Executor retains bounded discretion over implementation mechanism.

Prefer established repository patterns.

Do not preselect an optimization merely from source inspection.

### Slice C — Regression and performance verification

Compare baseline and candidate using materially equivalent:

* environment;
* inputs;
* configuration;
* detector mode;
* remap geometry;
* measurement boundaries.

Retain changes only when improvement reproduces beyond benchmark noise and accepted output behavior remains preserved.

## Benchmark evidence

For material benchmark scenarios report:

* execution baseline SHA;
* candidate revision;
* Python version;
* relevant NumPy/OpenCV/PyWavelets versions;
* available CPU/environment information;
* detector mode;
* raw/dark/flat shape;
* remap presence/shape;
* relevant config;
* warm-up policy;
* measured iterations;
* repeated timings or adequate statistical summary;
* median wall time;
* observed dispersion/noise;
* peak process memory when practical;
* baseline output identity/hash;
* candidate output identity/hash.

Fixture-loading time must not be silently mixed into array-processing timing unless the measured scenario explicitly includes it.

Synthetic measurements must be identified as synthetic.

Local performance results must not be called CI or production benchmarks.

## Performance acceptance rule

A retained optimization must demonstrate reproducible measured improvement.

For end-to-end optimization:

* candidate median must improve over baseline;
* improvement must exceed observed run-to-run noise;
* improvement must reproduce across repeated measurements;
* another required scenario must not show a reproducible material regression.

For stage-local optimization:

* stage improvement must be demonstrated;
* end-to-end behavior must not materially regress;
* the improvement must correspond to the changed mechanism.

Measurements within noise are not sufficient acceptance evidence.

## Acceptance criteria

* reproducible pre-change benchmark/profile exists;
* BED benchmark exists;
* TRX benchmark exists;
* synthetic versus real evidence is distinguished;
* each retained optimization is justified by observed profiling;
* retained optimization demonstrates reproducible improvement beyond benchmark noise;
* deterministic candidate outputs remain exactly equal to accepted baseline outputs where exact comparison applies;
* existing accepted pixel/hash contracts remain satisfied;
* BED threshold behavior remains unchanged;
* TRX threshold bypass remains unchanged;
* TRX clockwise orientation remains unchanged;
* expanded remap and invalid-border behavior remain unchanged;
* inputs/maps remain unmodified;
* output remains uint16;
* configuration defaults/public behavior remain unchanged;
* ImageJ/Fiji fidelity remains unchanged;
* no calibration-policy/default change is introduced;
* protected converter remains unchanged;
* no material new dependency is introduced without Planner review;
* focused regression tests pass;
* broader test suite passes where environment permits, with unrelated/pre-existing failures identified truthfully;
* applicable formatting/lint/type checks pass;
* final evidence records baseline, candidate, measured delta, retained/rejected optimization rationale, regressions, and limitations.

## Verification

Run applicable focused tests covering:

* radiography pipeline;
* imager workflow;
* threshold behavior;
* geometry/orientation;
* calibration remap;
* ImageJ/Fiji code affected by the change;
* converter protection.

Run the broader repository suite where practical.

Run applicable Black, Flake8, mypy, import, or repository quality checks for changed code.

Run:

`git diff --check`

Verify:

`sha256sum mpips/conversion/tiff_json_to_dcm.py`

Expected:

`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`

## Stop conditions

Stop and return to Planner/Reviewer if:

* actual start baseline materially differs from expected baseline;
* governing task revision cannot be established;
* benchmark noise prevents a reliable optimization conclusion;
* accepted image semantics must change;
* exact regression preservation cannot be maintained;
* optimization requires a new image-processing policy;
* calibration acceptance policy/default must change;
* protected converter must change;
* a materially consequential new dependency is required;
* GPU/concurrency/distributed/infrastructure changes become necessary;
* API/deployment/production scope is required;
* a security, privacy, data-integrity, clinical, or operational issue needs new authority;
* unrelated repository state cannot be safely preserved.

## Side-effect authorization

After Planner accepts the immutable task publication revision, Executor may:

* inspect repository;
* modify bounded in-scope source/tests/benchmark support;
* run non-destructive local profiling/tests;
* create temporary local benchmark artifacts;
* create ordinary bounded local implementation commits.

This task does NOT authorize:

* push;
* PR/issue writes;
* merge;
* rebase;
* unrelated cherry-pick;
* deploy;
* release;
* production mutation;
* external-system mutation;
* destructive Git cleanup;
* force push;
* secrets handling;
* committing real subject/patient datasets or large benchmark binaries.

## Expected execution terminal

Successful implementation:

`RADIOGRAPHY PIPELINE OPTIMIZATION CANDIDATE — PLANNER REVIEW REQUIRED`

Blocked execution:

`RADIOGRAPHY PIPELINE OPTIMIZATION BLOCKED — PLANNER REVIEW REQUIRED`

Executor does not self-declare final acceptance.

---
