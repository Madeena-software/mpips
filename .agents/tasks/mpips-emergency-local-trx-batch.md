---
title: MPIPS emergency local TRX batch DICOM capability
document_id: TASK-MPIPS-EMERGENCY-LOCAL-TRX-BATCH
version: 1.0
status: Validated/Published
language: en-US
scope:
  - bounded local manifest-driven TRX NPZ to DICOM batch processing
  - emergency local operational workflow only
authority_note: This task authorizes local implementation and verification only. It does not authorize real-patient processing, external upload, deployment, or production mutation.
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

**Implementation baseline:** `e94784db65bb134d43e87a2046037ab4d1cbfe02`

**Task revision:** resolved as the immutable Git publication revision before Executor handoff.

The accepted TRX clockwise-orientation correction is present in the baseline via `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a` and must not be regressed, replaced, bypassed, duplicated, or reinterpreted.

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
- No real-patient artifacts or external-system mutation → emergency operational handoff and repository delivery contract.

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
- Human review is required before implementation acceptance. No deployment, release, or external upload authorization is granted.

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

This task does not authorize real-patient processing, downloading or uploading patient data, Drive mutation, China AI-PACS interaction, deployment, production mutation, secrets, or push/PR creation.

## Expected terminal outcome

### Review Required

The Executor should return a reviewable implementation revision with observed verification evidence, or a truthful Planning Required stop result when a task stop condition is reached. The Executor does not self-declare final acceptance or release readiness.
