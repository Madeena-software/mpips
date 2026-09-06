---
title: MHCS Core Grabber Round-Trip Integration
document_id: TASK-MPIPS-MHCS-GRABBER-ROUNDTRIP-001
version: 1.0
status: Validated/Published
language: en-US
last_updated: 2026-09-06
scope:
  - additive MHCS Core Grabber HTTP client and adapter
  - workflow orchestration for manifest lookup → NPZ conversion → DICOM upload
  - idempotency and safe retry for DICOM ingestion
  - controlled local end-to-end rehearsal
  - offline NPZ-to-DICOM conversion preservation
authority_note: >-
  This task is validated and published. Execution and review are tied to the
  exact immutable task revision at .agents/tasks/mhcs-core-grabber-roundtrip.md
  @ the commit SHA recorded at publication. The protected converter, existing
  public API, and existing HTTP endpoint are preserved unchanged.
---

# Executable Task

This file defines a bounded software-delivery contract for implementation.

A validated task MUST provide enough authority, scope, acceptance, verification,
and stop-condition information for an Executor to proceed without inventing
material product, requirement, architecture, scope, or approval decisions.

A task is not a generic coding recipe. Implementation technique remains the
Executor's responsibility within the constraints established here.

## Task identity

**Task title:**
`MHCS Core Grabber Round-Trip Integration`

**Task path:**
`.agents/tasks/mhcs-core-grabber-roundtrip.md`

**Task contract state:**
`Validated/Published`

The task file is the executable delivery contract.

Execution and review lifecycle states such as `In Execution`, `Review Required`,
`Remediation Required`, and `Accepted` SHOULD normally be tracked by
orchestration, review records, repository metadata, or another mechanism that
preserves the exact governing task revision.

A lifecycle-status update MUST NOT silently replace the immutable task revision
that governed an execution attempt.

When remediation materially changes this executable contract, edit the same
stable task path, return it to Draft as needed, and republish it as a new
immutable governing task revision before renewed execution.

**Delivery objective / Work Package / MVP:**
Additive MPIPS workflow that accepts a four-digit radiography-session locator
code, authenticates to MHCS Core using a provisioned Grabber credential,
retrieves the patient/examination minimal DICOM manifest, converts the local
NPZ radiograph and gain into a validated Part 10 DICOM, and uploads the
resulting DICOM to MHCS Core via the authenticated direct-DICOM ingestion API,
with idempotent retry and local DICOM preservation on failure.

**Owner / designated planning authority:**
Repository Planner/Reviewer under the `.agents/` delivery contract.

---

## Delivery context

PR #5 (`feat/npz-dicom-import-module`) was merged into `main` at baseline
`084639395e7ecada982be72f46a2b8aff8ef79ac`, establishing the supported public
import surface `from mpips import convert_npz_to_dicom`.

MHCS Core has implemented the Grabber authentication and direct-DICOM ingestion
API at commit `5a3626b1d5e2624ec7818ca88545e36d320f0294` on branch
`task/urgent-operator-field-operations`. The authoritative server-side
integration contract is at
`mhcs-core/docs/mpips/mhcs-grabber-dicom-ingestion-contract.md`.

MPIPS currently has no capability to:
- authenticate to MHCS Core as a Grabber client;
- retrieve the minimal DICOM manifest for a radiography session by locator code;
- upload a converted DICOM directly to MHCS Core;
- manage idempotent submission identifiers across upload attempts.

This task delivers an additive integration that closes that gap while preserving
all existing MPIPS behavior.

The existing legacy NPZ upload pathway (MHCS → MPIPS `POST /v1/radiographs/dicom`)
is NOT replaced. The new MPIPS round-trip client is strictly additive.

---

## Baseline and task revision

**Implementation baseline:**
`084639395e7ecada982be72f46a2b8aff8ef79ac`
(`main` at the merge of PR #5, verified against the planning baseline)

**Task revision:**
`resolved when published`

Before this task is handed to an Executor, the exact immutable task-content
revision MUST be resolved. For Git repositories, the published task identity is:

```text
.agents/tasks/mhcs-core-grabber-roundtrip.md @ <full Git commit SHA containing this task content>
```

The immutable revision is supplied by version-control history after the
task-only commit is pushed to `origin/task/mhcs-core-grabber-roundtrip`.

---

## Objective

Deliver an additive, independently importable MPIPS integration module that
orchestrates the full Grabber round-trip:

1. Accepts a four-digit active radiography-session locator code.
2. Authenticates to MHCS Core using provisioned Grabber credentials from
   environment/configuration.
3. Retrieves the patient/examination minimal DICOM manifest for that locator
   via the MHCS Core Grabber manifest endpoint.
4. Provides the returned manifest to the existing supported
   `convert_npz_to_dicom()` Python API.
5. Converts the local radiograph NPZ and matching gain NPZ into a validated
   Part 10 DICOM.
6. Computes the SHA-256 checksum of the generated DICOM bytes.
7. Generates and persists a stable client submission/idempotency identifier
   for this study attempt.
8. Uploads the resulting DICOM to MHCS Core using the authenticated
   direct-DICOM ingestion endpoint.
9. Safely retries interrupted uploads without creating duplicate studies.
10. Preserves the generated local DICOM when an upload fails so the same
    artifact can be retried with the same bytes, checksum, and submission ID.
11. Returns or records a non-sensitive workflow result containing the MHCS
    study reference and server-selected terminal state.
12. Supports a controlled local end-to-end rehearsal between local MPIPS and
    local MHCS Core (localhost-only, synthetic or deidentified fixtures).

Offline NPZ-to-DICOM conversion MUST continue to work without MHCS Core
availability or credentials.

---

## Authoritative inputs

### Governing authority

- Human planning request: `task/mhcs-core-grabber-roundtrip` planning
  instruction delivered 2026-09-06, establishing planning baseline
  `084639395e7ecada982be72f46a2b8aff8ef79ac`.
- `AGENTS.md` (root Codex runtime adapter).
- `.agents/AGENTS.md` (repository AI delivery contract, version 1.2).
- `.agents/software-workflow.md` (normative delivery protocol, version 2.2).
- `.agents/context/project.md` (verified repository context, checkpoint
  `3a17baca`).

### Governing MHCS Core integration baseline

- **Repository:** `Madeena-software/mhcs-core`
- **Governing commit:** `5a3626b1d5e2624ec7818ca88545e36d320f0294`
- **Authoritative contract document:**
  `mhcs-core/docs/mpips/mhcs-grabber-dicom-ingestion-contract.md`
- **Verified canonical routes** (observed in `routes/api.php` at governing
  commit; all routes require `AuthenticateGrabberClient` middleware):

  | Purpose | Canonical route | Alias routes |
  |---|---|---|
  | Manifest lookup by path parameter | `GET /api/v1/grabber/manifest/{code}` | `GET /api/v1/grabber/radiography-sessions/{code}/manifest`; `POST /api/v1/grabber/manifest/lookup` |
  | Direct DICOM upload by path parameter | `POST /api/v1/grabber/radiography-sessions/{code}/dicom` | `POST /api/v1/grabber/dicom/upload`; `POST /api/v1/grabber/dicom`; `POST /api/v1/grabber/upload` |

  **Canonical routes for the MPIPS client (one route per operation):**
  - Manifest: `GET /api/v1/grabber/manifest/{code}`
  - Upload: `POST /api/v1/grabber/radiography-sessions/{code}/dicom`

  Using the canonical routes does not break compatibility with MHCS Core.

- **Authentication** (observed `AuthenticateGrabberClient.php` at governing
  commit):
  - `Authorization: Bearer <grabber_api_token>` OR
    `X-Grabber-Token: <grabber_api_token>` (required).
  - `X-Grabber-ID: <grabber_id>` (optional; verified if provided).

- **Required upload request fields** (observed `GrabberDicomUploadController`
  and `mhcs-grabber-dicom-ingestion-contract.md` at governing commit):
  - `X-Submission-ID` header — client-generated, non-empty, max 191 chars.
  - `X-Checksum-SHA256` header — 64 hex chars (SHA-256 of DICOM bytes).
  - DICOM payload as multipart `file` field (Content-Type:
    `multipart/form-data`) OR raw binary body (Content-Type:
    `application/dicom` / `application/octet-stream`).

- **Success response** (observed `GrabberDicomIngestionService.php` at
  governing commit):
  - Initial upload: `201 Created`, `replayed: false`.
  - Exact retry: `200 OK`, `replayed: true`.
  - Response body: `status`, `study_id`, `display_reference`,
    `admission_id`, `locator_code`, `terminal_state`, `checksum`, `bytes`.
  - Server-selected terminal state: `awaiting_ai` (enforced server-side;
    client cannot select or override it).

- **Manifest response** (observed `GrabberManifestService.php` at governing
  commit):
  - Returns a JSON object structurally compatible with the MPIPS
    `MHCSManifest` minimal manifest schema (contains `examination`,
    `patient`, `capture` blocks; no `dicom` block).
  - No schema conflict found between the MHCS Core manifest output and the
    existing `MHCSManifest` Pydantic model in `mpips/api/schemas/dicom.py`.

- **Rate limits** (observed in controllers at governing commit):
  - Manifest: 60 req/min total; 10 failed/min per client. `429` with
    `Retry-After`.
  - Upload: 60 req/min total; 10 failed/min per client. `429` with
    `Retry-After`.

- **No contract conflict found** between MHCS Core server implementation and
  the authoritative contract document at the governing commit.

### Existing MPIPS authority references

- `mpips/api/schemas/dicom.py` — `MHCSManifest` and `ResolvedMHCSManifest`
  (manifest schema).
- `mpips/conversion/__init__.py` — `convert_npz_to_dicom`, `ConversionError`
  (public import surface).
- `mpips/conversion/tiff_json_to_dcm.py` — protected canonical converter;
  SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- `mpips/__init__.py` — top-level `__all__` and lazy import surface.
- `tests/test_converter_protection.py` — converter hash invariant test.
- `tests/api/test_dicom_conversion.py` — DICOM conversion regression tests.
- `tests/api/test_api_surface.py` — HTTP API surface regression tests.
- `tests/test_public_boundaries.py`, `tests/test_package_import.py` —
  package boundary and import surface tests.
- `pyproject.toml` — `httpx>=0.28.1` is already declared in the `service`
  and `dev` extras and present in `uv.lock`; no new top-level HTTP
  dependency is required.

### Requirement traceability

- `REQ-GRABBER-001` (Grabber authentication) → Human planning request.
- `REQ-GRABBER-002` (Manifest retrieval by locator) → Human planning request +
  `mhcs-grabber-dicom-ingestion-contract.md`.
- `REQ-GRABBER-003` (NPZ-to-DICOM conversion via existing API) → Human
  planning request + `convert_npz_to_dicom` import surface.
- `REQ-GRABBER-004` (DICOM checksum) → `mhcs-grabber-dicom-ingestion-contract.md`.
- `REQ-GRABBER-005` (Stable client submission ID) →
  `mhcs-grabber-dicom-ingestion-contract.md`.
- `REQ-GRABBER-006` (DICOM upload with idempotency) → Human planning request +
  `mhcs-grabber-dicom-ingestion-contract.md`.
- `REQ-GRABBER-007` (Exact retry without duplication) →
  `mhcs-grabber-dicom-ingestion-contract.md`.
- `REQ-GRABBER-008` (Local DICOM preservation on failure) → Human planning
  request.
- `REQ-GRABBER-009` (Non-sensitive workflow result) → Human planning request.
- `REQ-GRABBER-010` (Local rehearsal) → Human planning request +
  `mhcs-grabber-dicom-ingestion-contract.md` Section 9.
- `REQ-GRABBER-011` (Offline conversion preserved) → Human planning request.
- `REQ-GRABBER-012` (Additive; legacy pathway preserved) → Human planning
  request.
- `REQ-CONV-001` (Protected converter immutability) →
  `tests/test_converter_protection.py`.
- `REQ-API-001` (Existing HTTP API preserved) → Human planning request +
  `tests/api/test_api_surface.py`.

---

## Scope

### In scope

1. **Typed MHCS Core Grabber HTTP client/adapter** — a new module (e.g.
   `mpips/integrations/mhcs_core/` or similar; Executor retains discretion
   over module naming and layout within existing repository conventions) that:
   - Reads Grabber credentials from environment/configuration (never from
     code, fixtures, or hard-coded values).
   - Authenticates to MHCS Core Grabber API using `Authorization: Bearer`
     or `X-Grabber-Token`.
   - Exposes a typed method for manifest lookup:
     `GET /api/v1/grabber/manifest/{code}` with the four-digit locator.
   - Exposes a typed method for DICOM upload:
     `POST /api/v1/grabber/radiography-sessions/{code}/dicom`
     with `X-Submission-ID` and `X-Checksum-SHA256`.
   - Uses `httpx` (already in `service` and `dev` extras).
   - Handles HTTP errors, timeouts, and rate-limit responses.
   - Never logs credentials, authorization headers, patient fields from
     manifest responses, or raw response bodies containing patient data.
   - Returns sanitized error diagnostics.

2. **Grabber round-trip orchestration workflow** — a new module that:
   - Accepts: locator code (4-digit string), radiograph NPZ path, gain NPZ
     path, output DICOM directory, and optional configuration overrides.
   - Executes in order: manifest lookup → `convert_npz_to_dicom()` → SHA-256
     compute → submission ID generate/load → DICOM upload.
   - Persists the generated DICOM and submission ID to controlled local
     private storage so that a retry reuses exactly the same bytes, checksum,
     and submission identifier.
   - Returns or records a non-sensitive `GrabberWorkflowResult` (containing
     at minimum: `study_id`, `display_reference`, `terminal_state`,
     `replayed`, `locator_code`; no patient fields, no credential fields).
   - Does NOT contact MHCS Core when operating in offline/library-only mode.

3. **Stable submission ID generation and persistence** — deterministic or
   UUID-based per-study identifier stored locally; reused on exact retry;
   never reused with different DICOM bytes.

4. **SHA-256 checksum calculation** of the final DICOM bytes prior to upload.

5. **Error handling and bounded retry**:
   - All failure cases listed under "Failure and retry contract" MUST be
     handled explicitly.
   - Retries MUST use timeouts, bounded attempt count, and exponential backoff
     with jitter.
   - A retry MUST reuse the same DICOM bytes, checksum, and submission ID.
   - Generated DICOM MUST be retained for bounded retry when upload fails.
   - MPIPS MUST NOT claim local success when upload was not server-confirmed.

6. **New configuration names** for MHCS Core Grabber credentials and endpoint:
   - `MHCS_GRABBER_BASE_URL` (or equivalent; Executor retains naming
     discretion within repository conventions).
   - `MHCS_GRABBER_TOKEN` (bearer token credential; must never appear in
     logs, exceptions, fixtures, or commits).
   - `MHCS_GRABBER_ID` (optional; grabber client identifier).
   - Document these names in `.env.production.example` as
     placeholder-only entries (never their values).

7. **Unit and integration tests** (see Verification requirements).

8. **Controlled local rehearsal script or test** — a localhost-only
   integration rehearsal (not a production test) against MHCS Core at the
   accepted integration commit. The rehearsal uses synthetic or deidentified
   fixtures. No real-patient data. No external network access. Guard with a
   skip marker when the local MHCS Core stack is absent.

9. **`.env.production.example` additions** for the new credential names.

### Out of scope

1. Modifying `mpips/conversion/tiff_json_to_dcm.py` or its SHA-256.
2. Modifying the existing `POST /v1/radiographs/dicom` HTTP endpoint,
   its handler, schemas, or idempotency logic.
3. Modifying `mpips/api/`, `mpips/pipelines/`, `mpips/processing/`,
   `mpips/calibration/`, or any existing module outside the new integration
   boundary and its test files.
4. AI PACS integration.
5. Production activation or real-patient transfer (separate approval gate).
6. Deployment, container release, tagging, or PyPI publishing.
7. Changing the legacy MHCS → MPIPS NPZ upload pathway.
8. Modifying `mhcs-core`.
9. Any changes to `mpips/__init__.py` unless needed to expose a top-level
   import for the new workflow (Executor discretion; not required).
10. Pull requests, merges, force-pushes, external AI service calls, or
    external network access beyond `localhost`.

### Preserved behavior and invariants

1. **Protected converter**: `mpips/conversion/tiff_json_to_dcm.py` MUST
   remain unmodified. SHA-256:
   `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
2. **Public import surface**: `from mpips import convert_npz_to_dicom` and
   `from mpips.conversion import convert_npz_to_dicom` MUST remain
   importable, functional, and unchanged.
3. **HTTP API**: `POST /v1/radiographs/dicom` and `GET /health` MUST remain
   fully operational, backward-compatible, and passing all existing tests.
4. **API-key authentication**: The existing `X-MPIPS-API-Key` guard for the
   DICOM endpoint MUST remain unchanged.
5. **Offline conversion**: `convert_npz_to_dicom()` MUST continue to work
   without MHCS Core availability or credentials.
6. **DICOM clinical invariants**: 16-bit uint16 depth, `MONOCHROME2`,
   canonical TRX clockwise orientation, populated UIDs, `pydicom`
   readability — all unchanged.
7. **Imager pipeline and CLI**: `mpips-imager`, `mpips-dotgrid`, and all
   existing CLI entry points MUST remain operational.
8. **Direct Git installation**: Bare `pip install
   "git+https://github.com/Madeena-software/mpips.git@<sha>"` MUST
   continue to satisfy all runtime dependencies for `convert_npz_to_dicom`.
   The new integration module MAY require the `service` extra (which already
   declares `httpx`) but MUST NOT add new top-level base dependencies.
9. **Existing test suite**: All existing passing tests MUST continue to pass
   with no regressions.
10. **TRX-orientation invariant**: Production clockwise rotation and threshold
    bypass invariants remain in force.
11. **Secret discipline**: No credential values in code, fixtures, commits,
    logs, exceptions, or reports.

---

## Dependencies and assumptions

### Dependencies

- Implementation baseline `084639395e7ecada982be72f46a2b8aff8ef79ac` on
  `main` is the required ancestor, not the expected HEAD. Before beginning
  material mutations, the Executor MUST:
  1. Start from the Reviewer-accepted published task revision on
     `task/mhcs-core-grabber-roundtrip`.
  2. Confirm a clean working tree (`git status --porcelain` is empty).
  3. Record `git rev-parse HEAD` as the actual execution-start SHA.
  4. Verify `084639395e7ecada982be72f46a2b8aff8ef79ac` is an ancestor of
     the execution-start revision
     (`git merge-base --is-ancestor 084639395e7ecada982be72f46a2b8aff8ef79ac HEAD`).
  5. Verify `git diff 084639395e7ecada982be72f46a2b8aff8ef79ac HEAD --name-only`
     lists only approved task-authoring and remediation artifacts
     (i.e., files under `.agents/tasks/` and `.agents/` governance paths;
     no product source, test, configuration, or dependency changes).
  6. Stop if the task revision is not the one accepted by Planner/Reviewer
     or if unrelated commits are detected between the baseline and
     execution-start.
- Python 3.12 and declared dependencies (including `httpx>=0.28.1` available
  in `service`/`dev` extras and `uv.lock`).
- MHCS Core at `5a3626b1d5e2624ec7818ca88545e36d320f0294` is the governing
  integration baseline. The Executor MUST NOT implement against a later MHCS
  Core revision during this task.
- The local rehearsal requires MHCS Core running at localhost. The rehearsal
  test MUST be skipped automatically when the local stack is absent, so
  mocked tests can run in CI without it.

### Approved assumptions

- `httpx>=0.28.1` is sufficient for the Grabber HTTP client (already in
  `uv.lock`; no new dependency installation required).
- The MHCS Core manifest response is structurally compatible with
  `MHCSManifest` (verified against `GrabberManifestService.php` at governing
  commit: `examination`, `patient`, `capture` blocks match minimal manifest
  shape; no schema conflict).
- The four-digit locator code is an operational locator, not a secret. It
  MAY appear in logs at an appropriate level without patient-data risk.
- `MPIPS MUST NOT request or select` `completed` as a terminal state; the
  server always enforces `awaiting_ai` (verified in
  `GrabberDicomIngestionService.php` and Slice 3 tests at governing commit).
- Submission ID persistence uses controlled local private storage (e.g. a
  local JSON sidecar or SQLite file in a configured work directory); the
  Executor retains discretion over the persistence mechanism within
  repository conventions, provided it does not require the HTTP service or
  Redis.
- Synthetic or deidentified fixtures (not real patient data) are used for
  all automated and local integration rehearsal tests.
- The MHCS Core Grabber API prefix is `/api/v1/grabber` (verified in
  `routes/api.php` at governing commit).

### Remaining approval requirements

- Production activation and real-patient transfer require a separate
  designated human approval gate beyond this task.
- No release, tagging, or deployment is authorized by this task.
- The local rehearsal (step 12 of the objective) MAY proceed against a local
  MHCS Core stack once all mocked tests pass, within the localhost-only and
  synthetic-fixture boundary defined by this task.

---

## Required capabilities

- Repository read and local write.
- Local shell execution for tests and static checks.
- Git branch management and remote push to
  `origin/task/mhcs-core-grabber-roundtrip`.
- Local MHCS Core stack access (localhost only, for rehearsal step; not
  required for mocked tests).

---

## Execution constraints

### Architecture boundary

1. **No network behavior inside `convert_npz_to_dicom()`**: The existing
   pure conversion function and its call path MUST remain unmodified. All
   MHCS Core HTTP calls are in the new, separate integration boundary.
2. **Additive only**: No existing module is changed except `.env.production.example`
   (credential name placeholders) and potentially `mpips/__init__.py` (only
   if the Executor chooses to expose a top-level import for the workflow).
3. **httpx for the Grabber client**: Do not introduce a second HTTP client
   library. `httpx` is already declared.
4. **Ponytail reuse discipline**: Reuse `MHCSManifest` from
   `mpips/api/schemas/dicom.py` for manifest parsing. Reuse
   `convert_npz_to_dicom` from `mpips.conversion`. Do not create parallel
   conversion engines or duplicate schema models.
5. **No parallel authentication model**: The new Grabber credential is
   entirely separate from and MUST NOT interact with the existing
   `X-MPIPS-API-Key` guard used by the MPIPS HTTP service.
6. **Module location**: The Executor retains discretion over the internal
   module name and layout (e.g., `mpips/integrations/mhcs_core/` or
   `mpips/mhcs/`), subject to existing repository conventions. The chosen
   location must not conflict with existing module paths.

### Security and privacy constraints

7. **Credentials from environment only**: `MHCS_GRABBER_TOKEN` (and any
   other credential) MUST come from environment variables or configuration
   and MUST NEVER appear in logs, exceptions, reports, fixtures, commits, or
   command output.
8. **No patient data in logs**: Manifest response fields (patient MRN, name,
   birth date, sex, study description) MUST NOT appear in log output,
   exception messages, or diagnostics at any log level.
9. **No DICOM content in logs**: DICOM binary content, checksums of patient
   data, and authorization headers MUST NOT appear in logs or exceptions.
10. **Sanitized error diagnostics**: Error messages propagated to callers
    MUST omit raw response bodies that may contain patient data.
11. **Private storage for DICOM and retry metadata**: Generated DICOM files
    and submission ID records MUST be written to a private/local controlled
    storage path (not a publicly accessible location). The storage path MUST
    be configurable.
12. **Synthetic fixtures only**: Automated and local rehearsal tests MUST use
    synthetic or deidentified DICOM bytes (e.g., 132 bytes minimum with
    correct DICM magic) and synthetic patient data. Do not use real patient
    NPZ files as test fixtures for the integration tests.

### Retry and idempotency constraints

13. **Bounded retry**: HTTP retries MUST have a configurable maximum attempt
    count, per-attempt timeout, and exponential backoff with jitter.
14. **Same artifact on retry**: A retry MUST reuse exactly the same generated
    DICOM bytes, the same SHA-256 checksum, and the same submission ID as the
    initial attempt.
15. **No false local success**: MPIPS MUST NOT record or return a successful
    result unless the MHCS Core server returns `201 Created` (initial) or
    `200 OK` with `replayed: true` (exact retry).
16. **No `completed` state**: MPIPS MUST NOT attempt to set or request
    `terminal_state: completed`. The expected successful server-selected
    state is `awaiting_ai`.

---

## Acceptance criteria

- [ ] `REQ-GRABBER-001`: A new typed MHCS Core Grabber HTTP client/adapter
      exists at a new module path. It reads credentials from environment only.
      It authenticates using `Authorization: Bearer` or `X-Grabber-Token`.
- [ ] `REQ-GRABBER-002`: The client exposes a manifest lookup method calling
      canonical route `GET /api/v1/grabber/manifest/{code}` with the
      four-digit locator. It returns a payload consumable by `MHCSManifest`.
- [ ] `REQ-GRABBER-003`: The orchestration workflow calls
      `convert_npz_to_dicom()` using the manifest returned by MHCS Core.
      The existing `from mpips import convert_npz_to_dicom` import surface is
      unchanged and continues to function for offline use.
- [ ] `REQ-GRABBER-004`: The generated DICOM SHA-256 checksum is computed and
      transmitted as `X-Checksum-SHA256`.
- [ ] `REQ-GRABBER-005`: A stable client submission ID is generated per
      study, persisted locally, and reused on retry. A new study attempt
      generates a new ID.
- [ ] `REQ-GRABBER-006`: The client calls canonical route
      `POST /api/v1/grabber/radiography-sessions/{code}/dicom` with the
      required `X-Submission-ID` and `X-Checksum-SHA256` headers and the
      DICOM payload as multipart `file` field.
- [ ] `REQ-GRABBER-007`: An exact retry (same DICOM bytes + same submission
      ID) receives `200 OK` with `replayed: true` and no duplicate study is
      created. The workflow records the replayed result.
- [ ] `REQ-GRABBER-008`: When an upload fails (timeout, connection loss, or
      non-retryable server error), the generated DICOM file is retained on
      disk so the exact same artifact can be retried later.
- [ ] `REQ-GRABBER-009`: The workflow result returned/recorded contains only
      non-sensitive fields: `study_id`, `display_reference`, `terminal_state`,
      `replayed`, `locator_code`, `checksum`, `bytes`. No patient identity
      fields, no credentials.
- [ ] `REQ-GRABBER-010`: A localhost-only integration rehearsal script or
      test exercises the full round-trip against a local MHCS Core stack with
      synthetic fixtures. It is skipped automatically when the local stack is
      absent.
- [ ] `REQ-GRABBER-011`: `convert_npz_to_dicom()` continues to work
      offline without MHCS Core availability or configured credentials.
- [ ] `REQ-GRABBER-012`: The existing `POST /v1/radiographs/dicom` legacy
      NPZ upload pathway is unchanged and all its existing tests pass.
- [ ] `REQ-CONV-001`: Protected converter SHA-256 remains
      `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- [ ] `REQ-API-001`: `POST /v1/radiographs/dicom` and `GET /health` continue
      to pass all tests in `tests/api/test_dicom_conversion.py` and
      `tests/api/test_api_surface.py`.
- [ ] Credentials (`MHCS_GRABBER_TOKEN` and any other Grabber secrets) do not
      appear in logs, exception messages, fixtures, commits, or test output.
- [ ] Patient identity fields from manifests (MRN, name, sex, birth date) do
      not appear in log output at any level.
- [ ] All new configuration names are documented in `.env.production.example`
      as placeholder-only entries with no secret values.
- [ ] Full quality gates pass: Black, Flake8, mypy (strict), pytest full
      suite.
- [ ] `git diff --check` passes (no whitespace errors).

---

## Verification requirements

### Required checks

Run in this order. All must pass before the Executor reports Review Required.

1. **Execution-start verification** (before any material mutations):
   ```bash
   # 1. Confirm clean working tree
   git status --porcelain
   # 2. Record execution-start SHA
   git rev-parse HEAD
   # 3. Verify implementation baseline is an ancestor of execution-start
   git merge-base --is-ancestor 084639395e7ecada982be72f46a2b8aff8ef79ac HEAD
   # 4. Inspect diff between baseline and execution-start
   git diff 084639395e7ecada982be72f46a2b8aff8ef79ac HEAD --name-only
   ```
   Required conditions before proceeding:
   - Working tree MUST be clean (no uncommitted changes).
   - Execution-start HEAD MUST be the Reviewer-accepted published task
     revision on `task/mhcs-core-grabber-roundtrip` (not necessarily
     equal to `084639395e7ecada982be72f46a2b8aff8ef79ac`).
   - `084639395e7ecada982be72f46a2b8aff8ef79ac` MUST be an ancestor of
     the execution-start revision.
   - The diff between the implementation baseline and the execution-start
     revision MUST contain ONLY approved task-authoring and remediation
     artifacts (files under `.agents/tasks/` and `.agents/` governance
     paths). Any unrelated commits MUST trigger a stop.

2. **Protected converter hash**:
   ```bash
   python -m uv run pytest tests/test_converter_protection.py -v
   ```

3. **Existing public API and conversion regression** (must pass before and
   after implementation):
   ```bash
   python -m uv run pytest tests/api/test_api_surface.py tests/api/test_dicom_conversion.py tests/api/test_dicom_authentication.py -v
   ```

4. **Public boundaries and import surface regression**:
   ```bash
   python -m uv run pytest tests/test_public_boundaries.py tests/test_package_import.py tests/test_conversion_import.py -v
   ```

5. **DICOM orientation and TRX regression**:
   ```bash
   python -m uv run pytest tests/test_imager_pipeline_workflow.py tests/test_radiography_pipeline.py tests/test_trx_false_acceptance.py -v
   ```

6. **New Grabber client unit tests** (mocked; no live server required):
   - Manifest success (valid 4-digit code, returns `MHCSManifest`-compatible
     dict).
   - Authentication failure (`401 Unauthorized` → raises specific exception).
   - Locator not found (`404 Not Found` → raises specific exception with
     anti-enumeration semantics).
   - Rate limit (`429 Too Many Requests` + `Retry-After` → raises specific
     exception; retry backoff is triggered).
   - Upload timeout / connection loss → local DICOM retained; exception raised.
   - Malformed manifest response (non-JSON or missing required fields) →
     raises schema or parse exception.
   - Idempotency conflict (`409 Conflict` with idempotency conflict message →
     raises specific non-retryable exception).
   - Idempotency replay (`200 OK` with `replayed: true` → returns replayed
     result).

7. **New orchestration workflow tests** (mocked client):
   - Full round-trip: manifest lookup → `convert_npz_to_dicom()` call →
     checksum compute → upload → `201 Created` result.
   - Retry path: existing DICOM + submission ID loaded → same bytes uploaded →
     `200 OK` replayed result.
   - Failed upload: DICOM file retained on disk, workflow raises exception
     with no false success recorded.
   - Idempotency conflict path: workflow raises non-retryable exception.
   - Patient data absence from logs: assert logging output during manifest
     lookup does not contain MRN, name, birth date, or sex values.
   - Credential absence from logs: assert logging output during upload does
     not contain the bearer token or any configured credential value.

8. **Full pytest suite**:
   ```bash
   python -m uv run pytest -v
   ```
   All tests must pass (including new ones). No existing test may be
   deleted or weakened.

9. **Code quality**:
   ```bash
   python -m uv run black --check mpips tests
   python -m uv run flake8 mpips tests
   python -m uv run mypy mpips tests
   git diff --check
   ```

10. **Localhost rehearsal** (after mocked tests pass; requires local MHCS
    Core stack at governing commit):
    - Start MHCS Core locally (localhost only, no external network).
    - Provision a synthetic `GrabberClient` record with a test token.
    - Create a synthetic active shift and radiography session with a known
      4-digit locator code.
    - Execute the MPIPS round-trip workflow with:
      - A synthetic NPZ radiograph and gain NPZ.
      - The locator code.
      - Synthetic patient data (deidentified).
    - Assert the full pipeline completes: manifest retrieved → DICOM
      generated → DICOM uploaded → `201 Created` with `terminal_state:
      awaiting_ai`.
    - Execute a second call with the same locator, DICOM bytes, and
      submission ID. Assert `200 OK` with `replayed: true`.
    - Verify no credentials or patient data appear in MPIPS log output.
    - Record the MHCS Core process ID and final exit status.
    - Use a 45–60 second watchdog progress check for background processes
      when reactive completion notification is unavailable; do not terminate
      a healthy process merely because the watchdog fires.
    - Rehearsal is skipped automatically when the local MHCS Core stack is
      absent.

### Required evidence

Upon completing implementation, the Executor MUST report:

- Execution-start SHA (the HEAD of the Reviewer-accepted published task
  revision; confirmed as a descendant of baseline
  `084639395e7ecada982be72f46a2b8aff8ef79ac` with only approved
  task-authoring/remediation artifacts in the intervening diff).
- Resulting implementation commit SHA on `task/mhcs-core-grabber-roundtrip`.
- Changed files list (`git diff --stat --name-only` against baseline).
- Confirmation that only the new integration module(s), new tests, and
  `.env.production.example` additions were changed; no existing source files
  were modified (except `.env.production.example`).
- Converter protection test result.
- API surface regression test result (pass counts).
- Full pytest suite result (pass count; zero failures; zero regressions).
- Code quality check results (Black, Flake8, mypy, git diff --check).
- New unit test results for the Grabber client (all mocked failure cases).
- New orchestration test results (all scenarios).
- Patient-data and credential absence from log assertion results.
- Protected converter SHA-256 confirmation.
- Localhost rehearsal result (or confirmed skip with reason).
- Remote push confirmation of `task/mhcs-core-grabber-roundtrip` to
  `origin`.
- Confirmation that no production action, external AI action, real-patient
  transfer, PR creation, merge, force-push, or deployment occurred.
- Any deviations, blockers, or non-blocking observations.

---

## Stop conditions

The Executor MUST stop implementation and return the issue to planning if:

1. The execution-start HEAD is not the Reviewer-accepted published task
   revision on `task/mhcs-core-grabber-roundtrip`; OR
   `084639395e7ecada982be72f46a2b8aff8ef79ac` is not an ancestor of the
   execution-start revision; OR the diff between the implementation
   baseline and execution-start contains commits that are not approved
   task-authoring or remediation artifacts.
2. The MHCS Core manifest response schema is materially incompatible with
   `MHCSManifest` (new required fields not present in the manifest output,
   or MHCS Core manifest requires schema changes in MPIPS).
3. Implementation would require any change to
   `mpips/conversion/tiff_json_to_dcm.py` or any modification of the
   existing `POST /v1/radiographs/dicom` handler, its schemas, or its
   idempotency logic.
4. The Grabber client cannot be implemented without introducing a new
   top-level base dependency not already in `pyproject.toml`.
5. A new patient-identity rule, privacy policy, or regulatory obligation
   must be invented that is not covered by this task.
6. A production credential, real-patient transfer, external endpoint,
   deployment, or external AI PACS service is required.
7. The task cannot preserve existing offline and HTTP conversion behavior.
8. Repository governance requires an unresolved approval.
9. Actual MHCS Core routes or request schemas at the governing commit
   materially conflict with the contract recorded in this task.
10. The Executor would be required to contact external services beyond
    `localhost`.

---

## Side-effect authorization

Implementation authorization is bounded to the task's defined execution scope.

Unless explicitly authorized by this task, applicable repository policy, or
designated authority, the task does NOT authorize:

- Direct push to `main`.
- Pull-request creation or modification.
- Branch merging or force-pushing (`--force`).
- Deployment, container release, cloud mutation, or production mutation.
- Release creation or tagging.
- PyPI or external package publishing.
- Secret, key, or credential manipulation or exposure.
- External-system access beyond `localhost`.
- Unrelated repository changes.

### Explicitly authorized side effects

1. Creation and modification of new integration module files under a new
   subpath of `mpips/` (e.g., `mpips/integrations/mhcs_core/` or similar).
2. Creation and modification of new test files under `tests/` corresponding
   to the new integration module.
3. Addition of Grabber credential name placeholders (no values) to
   `.env.production.example`.
4. Local commits on branch `task/mhcs-core-grabber-roundtrip`.
5. Non-force push to `origin/task/mhcs-core-grabber-roundtrip`.
6. Creation of bounded temporary artifacts for local rehearsal (outside
   tracked repository content; deleted or `.gitignore`d before completion).

---

## Expected terminal outcome

### Review Required

Use when a reviewable implementation state and truthful verification evidence
are available for Reviewer evaluation.

Expected evidence:

- Exact implementation commit SHA on `task/mhcs-core-grabber-roundtrip`.
- Verification results for all required checks.
- Deviations and known gaps.
- Unresolved non-blocking observations.

### Planning Required

Use when a stop condition prevents safe completion within the governing task.

Expected evidence:

- Blocking issue.
- Affected authority, scope, architecture, dependency, or acceptance
  condition.
- Repository evidence supporting the escalation.

The Executor does not self-declare final acceptance.

---

## Review and remediation handling

The Reviewer evaluates implementation against the exact governing task
revision, applicable authority, implementation baseline, implementation
revision, and observed evidence.

If the implementation is accepted, the reviewed immutable repository revision
MAY become the new accepted baseline when repository policy permits it.

Acceptance does not imply release authorization.

If review identifies bounded corrections within the same delivery objective,
update and republish this same task rather than creating filename-version
copies.

Materially new objectives, unrelated findings, or scope expansion MUST return
to Delivery Planning and become separate task work.

---

## Execution evidence

Execution evidence is normally reported outside the planning contract rather
than written by the Executor into the task as self-certification.

The governing review record SHOULD preserve or reference:

- governing task path and immutable task revision;
- implementation baseline;
- implementation revision;
- verification evidence;
- Reviewer verdict;
- remediation requirements when applicable;
- accepted baseline when acceptance occurs.
