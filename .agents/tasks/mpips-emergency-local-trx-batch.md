---
title: MPIPS emergency local TRX batch DICOM capability — DICOM clinical metadata hardening
document_id: TASK-MPIPS-EMERGENCY-LOCAL-TRX-BATCH
version: 1.4
status: Validated/Published
language: en-US
scope:
  - bounded local manifest-driven TRX NPZ to DICOM batch processing
  - emergency local operational workflow only
authority_note: This task authorizes local implementation and verification only. After independent implementation review and local acceptance of exactly one corrected DICOM, it permits one bounded external YiZhun AI Assisted Diagnosis validation under the explicit post-review contract below. It does not authorize bulk processing, deployment, or production mutation.
---

# Executable Task

## Task identity

**Task title:** MPIPS emergency local TRX batch DICOM capability

**Task path:** `.agents/tasks/mpips-emergency-local-trx-batch.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Emergency local TRX recovery — bounded manifest-driven batch conversion.

**Owner / designated planning authority:** Human operator / Planner-Reviewer handoff.

## Delivery context

The normal server/self-hosted processing path is unavailable. The local MPIPS repository already provides the canonical TRX NPZ loading, gain/calibration validation, radiography pipeline, TIFF-to-DICOM conversion, DICOM enrichment, validation, and isolated worker path. This task adds only the local orchestration needed to process a bounded operator manifest into one independently traceable DICOM per valid unique examination, without coupling MPIPS to the China AI-PACS.

The observed emergency source population is operational evidence only: two Drive folders contain approximately 45 unique TRX identifiers after duplicate reconciliation. The implementation must remain reusable for a bounded local manifest and must not embed or require that real population.

## Baseline and task revision

**Implementation baseline:** `6f64ee5788286a0418d79c2a705d5d7851736e47`

**Task revision:** resolved as the immutable Git publication revision before Executor handoff.

The accepted TRX clockwise-orientation correction is present in the baseline via `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a` and must not be regressed, replaced, bypassed, duplicated, or reinterpreted.

## Remediation — Authoritative DICOM Examination Date Semantics

### Objective

Generated emergency DICOMs must use authoritative examination/capture temporal
data where it exists and MUST NOT expose deterministic `conversion_job_id`-
derived pseudo-time as a clinical examination timestamp.

### Required behavior

1. **Study Date (0008,0020)** MUST represent the authoritative examination or
   study start date. When the emergency manifest supplies
   `examination.performed_at`, StudyDate must derive from that timestamp. For
   example, `performed_at` date `2026-08-28` requires `StudyDate = 20260828`,
   not a UUID-derived date.
2. **Study Time (0008,0030)** MUST NOT fabricate time precision. If an
   authoritative examination time is genuinely supplied, represent it. If the
   source supplies only a calendar date and midnight was only a transport
   representation, use the DICOM-compliant unknown/empty representation
   appropriate to the IOD and existing converter architecture; do not claim
   midnight as an observed clinical time.
3. **Content Date (0008,0023) and Content Time (0008,0033)** remain semantically
   distinct from StudyDate/StudyTime: they represent the start of image
   pixel-data creation. Use an authoritative capture/image-content timestamp
   only when actually known. Otherwise follow applicable DICOM requirements for
   absent/unknown values and do not copy StudyDate/StudyTime without semantic
   justification.
4. Deterministic internal fallback timestamps MAY remain where required by MPIPS
   architecture, but MUST NOT leak into clinical DICOM date/time tags as factual
   examination or acquisition dates. Prefer the minimum coherent fix over a
   redesign of the resolved-manifest model.

### Preserved behavior

The remediation MUST preserve patient identity, DOB/sex semantics, deterministic
MRN derivation, Study/Series/SOP UID behavior unless strictly necessary,
calibrated pixels, gain correction, geometric remap, accepted clockwise TRX
orientation, 4096 × 3000 output dimensions, PixelSpacing, projection PA,
otherwise-identical source pixel bytes, and batch duplicate/rerun behavior.

### Validation hardening

Extend DICOM validation so this defect cannot silently pass again. For a
manifest with authoritative `performed_at`, validate StudyDate against it;
validate StudyTime only when an authoritative time is known; and reject
pseudo/inconsistent examination dates. Validate capture/content tags against
the temporal source actually claimed by the manifest/conversion path. These
checks MUST use synthetic manifests and MUST NOT depend on real-patient
fixtures.

### Regression tests

Add synthetic tests proving:

- authoritative date `2026-08-28` produces `StudyDate == 20260828`;
- an authoritative date+time is represented correctly;
- a date-only emergency input does not fabricate midnight as observed clinical
  examination time;
- changing deterministic conversion identifiers does not alter StudyDate when
  the same authoritative examination date is supplied;
- an explicit authoritative `captured_at`/content timestamp produces the
  appropriate content temporal tags; and
- existing DICOM validation, orientation, calibration, dimensions, and
  patient-isolation tests continue to pass.

## Bounded post-review one-DICOM external validation

This is a separately gated operational phase. It MUST NOT occur until
Planner/Reviewer accepts the implementation and the one corrected local DICOM.
The complete 45-study population remains unauthorized by this task.

### Automated single-DICOM directory upload

For this bounded one-DICOM YiZhun validation only, a `multiple` and/or
`webkitdirectory` file input is not itself a stop condition. Automation MAY use
Playwright's supported directory-upload behavior only when every condition
below is satisfied:

1. Create a dedicated temporary upload directory outside the repository.
2. The directory contains exactly one regular file: the previously accepted
   corrected DICOM.
3. Immediately before browser selection, that file's SHA-256 is
   `5898cc58abf1690d4f185f69a3f4e03611ff44e78a7bbe04ac0123a44618e845`.
4. The directory contains no symlinks, nested directories, hidden second DICOM,
   temporary file, sidecar, manifest, or unrelated file.
5. Supply the directory path to the existing
   `input[type=file][webkitdirectory]` using supported
   `set_input_files(directory)` behavior. Do not pass a list of 45 files, the
   complete source/DICOM directory, or the parent validation directory.
6. Do not remove or rewrite `multiple`, `webkitdirectory`, or other upload
   attributes; do not inject a synthetic `FileList` or call undocumented YiZhun
   upload APIs.
7. After selection and before any submit/import action, inspect the browser
   input/UI state and require `input.files.length == 1`; the selected filename
   must be the sole accepted corrected DICOM and any visible queue must contain
   exactly one file/study.
8. If the selected or queued count is not exactly one, stop and clear the
   selection only if that can be done without committing an upload.

Use an isolated directory such as
`/tmp/mpips-one-dicom-temporal-validation/yizhun-upload-one/`, containing only
`corrected.dcm`. Before browser interaction, verify recursively that directories
below the upload root = 0, regular files = 1, symlinks = 0, and the SHA-256
matches the accepted value above.

The one-upload maximum remains unchanged. This exception does not authorize a
second DICOM, the remaining 44 studies, bulk patient processing, deletion,
report generation, or cleanup.

### Sample selection and local acceptance

Select one sample privately from the already-authorized CV Prestige population:
complete and reconciled demographic identity, authoritative examination date,
accepted source NPZ/gain/calibration, not a known blank-PDF regression case, and
preferably no prior demographic correction. Do not commit its identity.

Before any external upload, independently verify the one corrected sample has:

- canonical MPIPS conversion PASS, gain correction, geometric calibration, and
  unchanged orientation;
- Rows = 4096, Columns = 3000, ViewPosition = PA, and patient identity/DOB/sex
  matching the private manifest;
- StudyDate matching the authoritative examination date, StudyTime making no
  unsupported precision claim, and ContentDate/Time satisfying the implemented
  semantic rule;
- a parsable DICOM with decodable `pixel_array`; and
- unchanged PixelData relative to the pre-remediation DICOM for the same source,
  unless explicitly justified.

Compute whole-file and PixelData SHA-256 separately. The PixelData hash should
normally remain unchanged because this is a metadata-only remediation.

### External test boundary

Authorized only after the gate above: authenticate to the already-authorized
YiZhun environment, enter AI Assisted Diagnosis, upload exactly one corrected
DICOM, allow only processing inherent to that upload, inspect the resulting
study/viewer state, and record private before/after evidence. Do not upload a
second DICOM, process the remaining 44, use bulk selection or `--all`, generate
a report, download a PDF, process unrelated patients, delete old studies, edit
PACS data, or mutate the repository during the operational test.

Before upload, record privately PatientID, StudyInstanceUID, SeriesInstanceUID,
SOPInstanceUID, matching-study count if discoverable, visible examination date,
and image/viewer availability. Do not return PHI in shared evidence.

After upload, privately determine matching patient/study/SOP counts and classify
the result as `REPLACED_OR_UPDATED`, `REJECTED_DUPLICATE`,
`CREATED_DUPLICATE`, or `OTHER`. Verify image opening, laterality/orientation,
visible corrected examination date where exposed, and absence of unrelated
impact. Stop after this upload regardless of outcome.

Stop immediately if automation would select more than one file, YiZhun requires
bulk patient selection, target identity cannot be established safely, an
unrelated study could be overwritten, more than one new study appears, patient
identity changes, the image is not the intended image, or deletion/destructive
remediation is required.

The one-DICOM result is a decision gate. Planner/Reviewer must inspect the local
corrected-DICOM evidence and private YiZhun before/after result before deciding
the safe strategy for the full population. This task alone does not authorize
the remaining 44 studies.

## Revision 1.3 — DICOM clinical metadata hardening and full 45-case offline validation

This revision supersedes any conflicting external-validation permission in the
earlier sections of this task. It authorizes no YiZhun, PACS, Drive clinical
DICOM, report-generation, deployment, or other external mutation.

### Human intent and current findings

The temporal provenance defect is corrected: authoritative examination date
drives StudyDate, unknown examination time remains unknown, and synthetic
captured_at does not leak into ContentDate/ContentTime. One corrected real
DICOM confirmed corrected StudyDate, empty unknown times, preserved UIDs,
unchanged PixelData, and unchanged orientation.

The remaining known gap is demographic correctness. Enrichment currently
writes PatientName, PatientID, PatientBirthDate when known, and PatientSex,
but not PatientAge. `validate_dicom_dataset()` does not adequately verify
PatientBirthDate, PatientSex, or PatientAge against authoritative data.

PatientBirthDate (0010,0030) and PatientSex (0010,0040) are Type 2 attributes:
the attribute remains present and may be zero-length when unknown. Investigate
and correct any `unknown -> "O"` behavior that conflates UNKNOWN with OTHER.
PatientAge (0010,1010), VR AS, must never be fabricated.

### Phase 1 — root-cause and data-flow audit

Before implementation, trace each clinically relevant value through:

```text
private source manifest → MHCSManifest → ResolvedMHCSManifest → converter metadata
→ base DICOM → enrichment → final DICOM → validator
```

Build a private authoritative-field matrix for all 45 studies. At minimum
audit PatientName, PatientID, PatientBirthDate, PatientSex, PatientAge,
StudyDate, StudyTime, SeriesDate, SeriesTime, AcquisitionDate,
AcquisitionTime, ContentDate, ContentTime, AcquisitionDateTime,
AccessionNumber, StudyID, Study/Series/SOPInstanceUID, Modality,
BodyPartExamined, ViewPosition, ImageLaterality, PresentationIntentType,
InstitutionName, StationName, Rows, Columns, PixelSpacing,
PhotometricInterpretation, BitsAllocated, BitsStored, HighBit,
PixelRepresentation, and PixelData hash.

Classify every populated clinical tag as AUTHORITATIVE,
DERIVED_FROM_AUTHORITATIVE, TECHNICAL_IDENTIFIER, STANDARD_REQUIRED_EMPTY,
SYSTEM_DEFAULT, or UNSUPPORTED / SPECULATIVE. No unsupported/speculative
clinical value may survive acceptance.

Explicitly cover: known DOB; absent DOB with authoritative age; neither DOB
nor age; known male; known female; and unknown sex.

If authoritative birth_date and examination date exist, derive completed age
at examination date and encode valid DICOM AS (for example `054Y`). Do not
use current time, file time, conversion time, UUID time, or pseudo captured_at.
Support authoritative age without DOB only when the private source and schema
preserve its provenance safely. Otherwise omit the age value without
fabrication.

Audit all temporal attributes: StudyDate/Time, SeriesDate/Time,
AcquisitionDate/Time, AcquisitionDateTime, ContentDate/Time,
InstanceCreationDate/Time. Synthetic timestamps must not leak into clinical
date/time attributes; distinguish legitimate instance-creation metadata from
examination/acquisition metadata.

### Phase 2 — failing tests

After Phase 1 and before production changes, add focused tests that fail on
current behavior where appropriate. Cover wrong PatientBirthDate, wrong
PatientSex, unknown sex versus OTHER, age across a birthday boundary, no
invented age, authoritative age-only data, date-only StudyTime, pseudo-time
leakage, UID preservation, PixelData preservation, and orientation/presentation
preservation.

### Phase 3 — bounded implementation and validator hardening

Implement only fixes proven necessary by Phases 1 and 2. Likely scoped files
include `mpips/api/schemas/dicom.py`, `mpips/conversion/metadata.py`,
`mpips/conversion/dicom_enrichment.py`, `mpips/conversion/validation.py`,
`mpips/workflows/imager_pipeline/emergency_batch.py`, and focused tests.
Do not refactor unrelated code.

Validation must fail closed for wrong demographic metadata and check
PatientName, PatientID, PatientBirthDate presence/value, PatientSex
presence/value, and PatientAge when authoritative or derived, in addition to
existing temporal, UID, image, and pixel checks.

### Phase 4 — full 45-case offline regeneration

After implementation tests pass and local implementation acceptance, generate
exactly the authorized 45 DICOM studies in a fresh private local workspace.
Do not contact YiZhun or PACS and do not publish clinical DICOMs to Drive.
Each case must have an anonymized index, source-date category, metadata/pixel/
visual validation results, whole-file and PixelData SHA-256, UID preservation,
temporal-tag summary, and demographic-tag summary.

Require Rows=4096, Columns=3000, authoritative ViewPosition=PA,
unchanged PixelData, no horizontal mirror, no unintended rotation, and no
crop/stretch. Preserve established StudyInstanceUID, SeriesInstanceUID, and
SOPInstanceUID. Run an independent DICOM conformance tool such as
dciodvfy/DCMTK only if already installed; do not install unfamiliar software.
Record availability and result.

### Evidence gate

Evidence publication is required before Planner/Reviewer acceptance. Use the
existing private MPIPS evidence root and create child folder
`06_full-45-dicom-correctness/` with `01_root-cause/`, `02_tests/`,
`03_metadata-audit/`, `04_pixel-orientation-audit/`, `05_conformance/`, and
`06_review-index/`. Publish anonymized root-cause, authoritative-field,
metadata, temporal, demographic, UID, pixel, test, visual, conformance (if
available), index, and review-summary evidence.

Never publish `.env`, credentials, cookies, tokens, auth-state, raw network
credentials, or the approximately 1.1 GB raw DICOM set unless separately
authorized.

### External-mutation prohibition and publication gate

This revision does not authorize YiZhun upload, PACS upload, a second
one-DICOM experiment, report generation, Drive replacement of clinical
DICOMs, production deployment, or any other external mutation.

For this immediate task-publication step only: update this task to version
1.4, validate consistency, run `git diff --check`, and commit only this task
revision. Do not implement production changes, regenerate the 45 studies,
contact YiZhun, or publish the new 45-case evidence yet. Stop for
Planner/Reviewer review after publication.

### Revision 1.4 — one real-pixel Secondary Capture QA interoperability artifact

This revision is a narrow exception to Revision 1.3. It authorizes exactly
one de-identified Secondary Capture DICOM QA artifact containing real
processed pixels from `TRX_1787899731256.npz`, using the already-authorized
gain `TRX_1787726609597.npz` and accepted TRX calibration locally.

It authorizes local processing, generation, validation, visual inspection, and
handoff of the artifact path and hashes to the human operator. The human may
manually upload exactly that one file to the already-authorized AI-PACS.
Codex MUST NOT upload it or automate browser interaction.

The artifact MUST use Secondary Capture Image Storage
(`1.2.840.10008.5.1.4.1.1.7`), synthetic identity `MPIPS^INTEROP_TEST` and
`MPIPS-REALPIXEL-SC-001`, empty birth date/sex, absent age, and the QA study
and series descriptions. It MUST preserve the real processed pixel matrix and
use new QA-specific UIDs. It MAY include only proven acquisition values: KVP
80, XRayTubeCurrent 50, ExposureTime 500, and Exposure 25. It MUST omit
`ExposureInuAs`, dose metrics, ambiguous `expTime`, and
`cameraparams.Exposure`.

The artifact MUST NOT fabricate detector spacing, `PixelSpacing`,
`ImagerPixelSpacing`, `PixelIntensityRelationship`,
`PixelIntensityRelationshipSign`, `DetectorType`, or other unresolved DX
semantics. It MUST pass pydicom parse/decode, current `dciodvfy` validation
with zero current-standard errors, burned-in-PHI inspection, and local visual
QA. The handoff directory `/tmp/mpips-ai-pacs-realpixel-sc-test/` must contain
exactly `MPIPS_REALPIXEL_SC_INTEROP_TEST.dcm` and no source, manifest,
sidecar, mapping, symlink, nested directory, or second DICOM.

This revision does not authorize production real-DX generation, processing the
remaining 44 studies, PACS automation, report generation, deletion, Drive
publication, deployment, merge, or clinical/diagnostic claims. Codex MUST stop
after handing the local artifact to the human and confirming that no PACS
upload occurred.

## Objective

Implement a local, bounded, manifest-driven capability that validates TRX inputs and metadata, derives emergency MRNs deterministically from canonical NPZ filenames, reuses the existing MPIPS processing/DICOM path, and writes safe, resumable, independently traceable DICOM results and summaries for valid unique examinations.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- This Planner-reviewed emergency operational handoff, including the hard-copy authority, local manifest contract, identity rules, and safety boundaries.

### Requirement traceability

- Local bounded recovery capability → emergency operational handoff.
- Canonical MPIPS processing and DICOM semantics → `.agents/context/project.md` and observed baseline implementation in `mpips/workflows/imager_pipeline/`, `mpips/conversion/`, and `mpips/api/schemas/`.
- Deterministic emergency MRN identity → emergency operational handoff: `TRX_<numeric-id>.npz` → `MRN-<numeric-id>`.
- No unapproved real-patient artifacts or external-system mutation → emergency operational handoff and repository delivery contract; the bounded one-DICOM post-review validation is the sole explicit exception.

## Scope

### In scope

- A small local CLI, script, command, or module using repository-established Python patterns.
- Ingestion of a simple local, non-committed manifest (CSV, JSON, JSONL, or an equivalent established format) with at least source TRX/NPZ identifier, source path, patient name, and optional permitted patient/examination metadata.
- Strict parsing of `TRX_<numeric-id>` from the NPZ filename and automatic derivation of `medical_record_number = MRN-<numeric-id>`.
- Rejection of malformed or ambiguous capture identifiers; no identity inference from filename ordering, patient name, or incidental copy suffixes.
- Explicit duplicate detection and reconciliation by normalized numeric TRX identity and, where practical, stable file hashes; duplicate physical files must not silently generate duplicate studies.
- Validation of manifest rows, NPZ structure, path containment/selection, gain compatibility, detector mode, dimensions, and required canonical calibration artifacts before processing.
- Inspection of the actual NPZ structure and canonical loader behavior to determine whether smaller raw representations are sufficient and whether embedded `processedimage` data is ignored, consumed, output-affecting, or irrelevant. The implementation must select a representation only after that evidence-based check.
- Discovery and reuse of an existing authorized TRX gain source and validated calibration artifact supported by MPIPS local configuration/artifacts.
- Reuse of `load_radiograph`, gain loading, `process_radiography_arrays`, isolated conversion, approved TIFF-to-DICOM conversion, enrichment, and DICOM validation mechanisms as applicable; no parallel medical-image interpretation.
- Per-case processing with failure isolation, continuation after bounded individual failures, deterministic output naming based on derived non-secret operational identity (for example `MRN-<numeric-id>.dcm`), resumability, and safe rerun/idempotent behavior.
- Machine-readable and human-readable final summaries without PHI in logs intended for Git/CI.
- Dry-run or validation-only behavior where it is the smallest coherent way to make preflight safe.
- Focused synthetic/local tests and concise local operational documentation if needed.

### Out of scope

- `Madeena-software/mhcs-core`, server restoration, self-hosted runner restoration, deployment, production infrastructure, or production mutation.
- China AI-PACS upload or automation, AI report generation, PDF download, or `ai-report-download-automation` changes.
- Clinical interpretation, diagnostic validation, or claims about medical accuracy.
- Changes to accepted TRX clockwise orientation, BED behavior, canonical calibration generation, calibration mutation, or accepted calibration assets.
- New NPZ semantics, separate image-processing implementations, unrelated refactoring, authentication changes, or credential handling beyond existing secure local mechanisms.
- Downloading or modifying the real emergency dataset during implementation or verification.
- Committing real names, MRNs, dates, patient mappings, NPZ/TIFF/DICOM/PDF artifacts, credentials, or real manifests.

### Preserved behavior

- Existing single-case API/library behavior and canonical DICOM conversion, enrichment, validation, and cleanup semantics remain unchanged unless a contract-level incompatibility is demonstrated.
- The accepted TRX clockwise orientation remains canonical; BED behavior remains unchanged.
- Patient metadata is sourced only from the associated manifest/hard-copy transcription; missing values remain missing or use only explicit existing MPIPS defaults. Sex must never be inferred from a name, and age must not be reverse-calculated into a birth date.
- Each output DICOM's patient identity corresponds only to its own manifest row; no cross-case metadata leakage is permitted.
- Source patient data and generated DICOMs remain local until a separately authorized human/external operational step.

## Dependencies and assumptions

### Dependencies

- The implementation baseline remains applicable. If `main` or the baseline moves in a way that affects this task, return to planning for reconciliation.
- An authorized TRX gain NPZ and validated TRX calibration artifact supported by the canonical MPIPS path must be available before real-patient processing.
- Existing Python/runtime dependencies and local filesystem access are available.
- The human hard-copy mapping supplies patient name and any optional demographic/examination values actually printed.

### Approved assumptions

- Numeric TRX identity is the sole emergency MRN identity source: `TRX_<numeric-id>` maps to `MRN-<numeric-id>` with a hyphen.
- A filename decoration such as a copy suffix is incidental unless an authorized manifest explicitly establishes a distinct examination.
- The external China AI-PACS step remains manual and outside this task.

### Remaining approval requirements

- Human/operator approval is required before using any real patient manifest or processing real patient data.
- A clear preflight must establish the authorized gain and validated calibration dependency before real-patient processing. If it cannot, real-patient conversion must stop and report the missing dependency.
- Human review is required before implementation acceptance. No deployment or release authorization is granted. External upload remains prohibited until the bounded one-DICOM post-review gate is satisfied.

## Required capabilities

- repository read/write
- shell and local test execution
- Codebase Memory MCP for implementation discovery when available
- local temporary filesystem access

## Execution constraints

### Constraints

- Keep the implementation local and bounded; do not add a framework or external service for batch orchestration.
- Use path-safe local file handling, strict manifest validation, bounded input/resource checks, and atomic or otherwise recoverable output publication.
- Validate all rows and shared dependencies before starting conversion where practical; do not partially process a batch when a shared gain/calibration preflight fails.
- A per-case failure may be recorded and isolated, but malformed identity, duplicate identity, ambiguous source selection, missing gain, invalid calibration, or metadata mismatch must not be silently repaired.
- Never fabricate gain/calibration data, substitute a patient NPZ as gain, bypass FFC/calibration validation, regenerate calibration, or mutate accepted calibration assets.
- Do not log PHI or persist the real manifest in the repository. Synthetic fixtures must use entirely fictional data.
- Reuse established repository mechanisms and preserve unrelated behavior.

## Acceptance criteria

- [ ] A bounded local manifest can describe each case's NPZ source, derived MRN, patient name, and optional allowed metadata without requiring hard-copy MRN lookup.
- [ ] Valid canonical filenames derive exactly `MRN-<numeric-id>`; malformed, ambiguous, and copy-suffix identity cases are rejected or deliberately reconciled without artificial MRNs.
- [ ] Duplicate numeric TRX identities are detected before duplicate DICOM generation; distinct studies require explicit authorized manifest identity.
- [ ] Preflight validates the manifest, NPZ structure, actual raw-data sufficiency, gain source, detector compatibility, and validated calibration, and stops real-patient work when the authorized gain/calibration dependency is unavailable.
- [ ] Each valid unique case is processed through the canonical MPIPS pipeline and DICOM conversion/enrichment/validation path, producing one deterministic local DICOM with the case's own identity.
- [ ] Reruns do not silently duplicate successful outputs; individual failures do not corrupt successful cases, and the final summaries expose per-case status without PHI leakage.
- [ ] Existing API/library behavior, accepted TRX orientation, BED behavior, calibration assets, and converter semantics remain preserved.
- [ ] No real patient data or operational artifacts are added to Git, and no China AI-PACS or production side effect is introduced.

## Verification requirements

### Required checks

- Focused tests for capture-ID parsing, MRN derivation, malformed/ambiguous identifiers, duplicate reconciliation, manifest validation, safe output naming, rerun behavior, and per-case failure isolation using fictional data only.
- Tests proving the canonical NPZ loader's raw-image boundary and the chosen handling of larger/smaller NPZ representations without real patient files.
- Synthetic/local integration coverage proving gain/calibration preflight and one validated DICOM result per unique case through the established conversion path, with patient identity isolation.
- Repository-required formatting, lint, type, and focused/full test checks proportionate to changed files.
- A dry-run or validation-only preflight against synthetic/local fixtures; real-patient processing, Drive access, and external upload are not verification requirements for this task.

### Required evidence

The Executor MUST report:

- exact implementation revision or working-tree state and governing task revision;
- commands and observed results;
- synthetic fixtures/data locations and confirmation that no real patient data was used;
- canonical pipeline/converter/calibration evidence;
- duplicate, rerun, failure-isolation, and output-validation evidence;
- known verification gaps, deviations, blockers, and any required human approval before real-patient use.

## Stop conditions

The Executor MUST stop implementation and return to planning when:

- a required authority decision, architecture decision, or scope interpretation is missing or contradictory;
- the baseline is no longer safely applicable;
- valid authorized gain/calibration material cannot be established for the requested real-patient operation;
- the canonical NPZ structure or loader boundary cannot establish which source representation is safe;
- satisfying the contract requires changing accepted orientation, calibration, BED behavior, DICOM semantics, authentication, production infrastructure, or external systems;
- execution would require real patient data, secret access/disclosure, an unapproved dependency, or an unapproved external/production side effect;
- acceptance criteria cannot be met without materially expanding the task.

## Side-effect authorization

### Explicitly authorized side effects

- create or modify local source/tests/documentation required by this task;
- write synthetic fixtures and local temporary outputs that contain no real patient data.

This task does not authorize bulk real-patient processing, downloading or uploading additional patient data, Drive mutation, deployment, production mutation, secrets, or push/PR creation. The sole exception is the exactly-one-DICOM YiZhun validation explicitly authorized only after the post-review local acceptance gate above.

## Expected terminal outcome

### Review Required

The Executor should return a reviewable implementation revision with observed verification evidence, or a truthful Planning Required stop result when a task stop condition is reached. The Executor does not self-declare final acceptance or release readiness.
