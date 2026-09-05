---
title: NPZ to DICOM Public Import Module and Direct Git Distribution
document_id: TASK-NPZ-DICOM-IMPORT-MODULE-001
version: 1.1-candidate
status: Candidate / Draft (Planner Review Required)
language: en-US
last_updated: 2026-09-05
scope:
  - public Python import surface for NPZ-to-DICOM conversion (from mpips import convert_npz_to_dicom)
  - direct Git distribution via pip against an immutable commit SHA without manual clone
  - HTTP API and protected converter preservation
  - clinical DICOM and orientation invariant enforcement
  - clean-environment installation and end-to-end verification
authority_note: >-
  This candidate task artifact defines the reviewable delivery contract for the
  NPZ-to-DICOM import module and direct Git distribution successor work. It does
  not implement product code or mutate dependencies. Implementation begins only
  after formal Planner/Reviewer validation and acceptance.
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
`NPZ to DICOM Public Import Module and Direct Git Distribution`

**Task path:**  
`.agents/tasks/npz-dicom-import-module.md`

**Task contract state:**  
`Candidate / Draft (Planner Review Required)`

The task file is the executable delivery contract.

Execution and review lifecycle states such as `In Execution`, `Review Required`,
`Remediation Required`, and `Accepted` SHOULD normally be tracked by orchestration,
review records, repository metadata, or another mechanism that preserves the exact
governing task revision.

A lifecycle-status update MUST NOT silently replace the immutable task revision
that governed an execution attempt.

When remediation materially changes this executable contract, edit the same
stable task path, return it to Draft as needed, and republish it as a new
immutable governing task revision before renewed execution.

**Delivery objective / Work Package / MVP:**  
Enable a user to install MPIPS directly from the public GitHub repository without
manually cloning it, then use the required public Python import surface
`from mpips import convert_npz_to_dicom` for NPZ-to-DICOM conversion, while
preserving the existing HTTP API, package boundaries, protected converter SHA,
and clinical DICOM invariants.

**Owner / designated planning authority:**  
Repository Planner/Reviewer under the `.agents/` delivery contract.

## Delivery context

Following the completion and merge of PR #4 (`refactor/package-boundaries`) into
`main` at baseline `c612ca4067a4cae83fb364858d0ed38cb8c2a0a0`, the repository
established unified package boundaries, retired the legacy `mpips.engine` package,
and consolidated the canonical DICOM converter under `mpips.conversion.tiff_json_to_dcm`.

As explicitly anticipated in `.agents/tasks/package-boundaries-integration-readiness.md`
(Section: "Importable-module successor boundary"), exposing NPZ-to-DICOM conversion
as a supported Python import surface (library interface) was separated as a distinct,
dependent successor objective.

Currently:
1. `mpips` can be run as an HTTP microservice exposing `POST /v1/radiographs/dicom`.
2. `mpips.conversion` contains conversion modules (`service.py`, `validation.py`,
   `metadata.py`, `dicom_enrichment.py`, `worker.py`, `tiff_json_to_dcm.py`), but
   lacks packaging discovery configuration. Consequently, installing `mpips` from
   Git must ensure that all conversion modules are included in the built wheel.
3. Users who want to programmatically convert radiographs from NPZ arrays and gain
   calibrations to DICOM in Python without running or calling an HTTP service have no
   supported, documented top-level import entrypoint.
4. The distribution model requires direct installation from public GitHub via `pip`
   against an immutable commit SHA without requiring manual repository cloning.

This candidate delivery contract specifies the technical requirements, concrete
architectural contracts, invariants, and verification obligations to implement this
capability safely and reproducibly.

## Baseline and task revision

**Implementation baseline:**  
`c612ca4067a4cae83fb364858d0ed38cb8c2a0a0` (`main` @ HEAD)

**Task revision:**  
`resolved when published` (Draft candidate; will resolve to the task-only commit
on `feat/npz-dicom-import-module`)

The implementation baseline and governing task revision are separate references.
Do not change the implementation baseline silently during execution.

## Objective

Deliver a supported, documented, and thoroughly verified Python import surface
`from mpips import convert_npz_to_dicom` (with `from mpips.conversion import convert_npz_to_dicom`
as an optional convenience) for converting NPZ radiograph and gain data plus
manifest metadata into standard DICOM files, installable directly from public
GitHub via `pip` against an immutable commit SHA without manual cloning, with
zero regressions to the existing HTTP API or clinical DICOM invariants.

## Authoritative inputs

### Governing authority

- Human Request: "Enable a user to install MPIPS directly from the public GitHub
  repository without manually cloning it, then use a supported Python import surface
  for NPZ-to-DICOM conversion. The existing HTTP API must remain supported and unchanged."
- `AGENTS.md` (root Codex runtime adapter);
- `.agents/AGENTS.md` (repository AI delivery contract);
- `.agents/software-workflow.md` (normative delivery protocol);
- Baseline commit `c612ca4067a4cae83fb364858d0ed38cb8c2a0a0` on `main`.

### Supporting context and procedure

- `.agents/context/project.md`;
- `.agents/tasks/package-boundaries-integration-readiness.md` (successor boundary definition);
- `tests/test_converter_protection.py` (canonical converter path and hash invariant);
- `tests/test_public_boundaries.py` (package boundary constraints and import isolation);
- `tests/test_package_import.py` (public package export tests);
- `tests/api/test_dicom_conversion.py` (DICOM conversion end-to-end and clinical assertions);
- `tests/api/test_api_surface.py` (route registration and health check invariants);
- `pyproject.toml` (packaging configuration and dependencies).

### Requirement traceability

- `REQ-DIST-001` (Direct Git installation) → Human Request;
- `REQ-IMPORT-001` (Supported public Python import surface) → Human Request;
- `REQ-API-001` (HTTP API preservation) → Human Request & `tests/api/test_api_surface.py`;
- `REQ-CONV-001` (Protected converter immutability) → `tests/test_converter_protection.py`;
- `REQ-CLIN-001` (DICOM pixel, metadata, and TRX orientation) → `tests/api/test_dicom_conversion.py`.

## Scope

### In scope

1. **Packaging configuration**:
   - Ensure `mpips.conversion` and all required submodules are recognized and packaged
     by setuptools so that direct Git installs contain all necessary conversion modules.
2. **Public import surface**:
   - Deliver the required consumer-facing import: `from mpips import convert_npz_to_dicom`.
   - An import via `from mpips.conversion import convert_npz_to_dicom` may be provided
     and documented as an additional convenience only; it is not an alternative to the
     required top-level interface.
   - Satisfy outcome-level conversion obligations: library callers can invoke NPZ-to-DICOM
     conversion with the file-based inputs necessary for the existing supported conversion
     workflow (radiograph NPZ path, gain NPZ path, manifest metadata, destination output
     DICOM path, and optional calibration assets directory).
   - Ensure ordinary Python-library usage does not require a running API/worker service
     or web-framework background daemons.
   - Decouple library-level exception reporting from web-framework exceptions
     (`fastapi.HTTPException`), raising standard Python exceptions on failure.
   - Preserve Executor technical discretion over internal mechanics (exact module layout,
     export technique, internal signature details, and exception types) consistent
     with existing repository patterns.
3. **HTTP API preservation**:
   - The existing HTTP endpoint `POST /v1/radiographs/dicom` and `GET /health` must
     remain completely supported, unchanged, and operational.
   - The endpoint handler may delegate to the public import surface or share
     underlying isolated execution services.
4. **Direct Git installation verification**:
   - Support installation via `pip` directly from GitHub using a Git URL targeting
     an immutable commit SHA without manual cloning.
   - Require clean-environment testing of the primary `pip` command with minimal
     declared extras/dependencies actually required.
   - Do not claim a bare install is sufficient unless verification proves all
     required runtime imports succeed without optional extras.
   - If `uv` installation is documented, it must also be tested and verified.
5. **Comprehensive verification**:
   - Add focused tests for the public import surface.
   - Run existing test suites for API surface, DICOM conversion, converter protection,
     and static analysis (Black, Flake8, mypy).

### Out of scope (non-goals)

1. PyPI publishing or credentials management.
2. Private package registry setup or publishing.
3. Deployment, server provisioning, container release, or production mutation.
4. Modifying the protected converter `mpips/conversion/tiff_json_to_dcm.py` or its SHA.
5. Altering clinical image processing algorithms, thresholding, CLAHE, or TRX calibration.
6. Refactoring unrelated subsystems (e.g. DAG executor, Celery workers, dotgrid neural models).
7. Adding heavy external dependencies not already declared in `pyproject.toml`.
8. Tag creation or release branching (reserved for release governance).

### Preserved behavior and invariants

1. **HTTP API endpoints & contracts**:
   - `POST /v1/radiographs/dicom` behavior, multipart parsing, status codes (200, 400,
     422, 500, 504), idempotency handling, and API key authentication remain unchanged.
   - `GET /health` continues returning `{"service": "mpips", "status": "healthy", ...}`.
2. **Protected converter hash and location**:
   - `mpips/conversion/tiff_json_to_dcm.py` MUST maintain exact SHA-256:
     `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
   - Legacy path `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` must remain absent.
3. **DICOM clinical and metadata invariants**:
   - Output DICOM files must be readable by standard `pydicom.dcmread`.
   - Modality, SOP Class UID, Study/Series/SOP Instance UIDs must be populated per manifest.
   - 16-bit pixel data, photometric interpretation (`MONOCHROME2`), and aspect/spacing
     must be preserved.
4. **TRX-orientation invariant**:
   - Output DICOM orientation must preserve the verified clockwise orientation and
     threshold bypass invariants established in production.

## Concrete delivery specification and architectural contracts

### 1. Direct Git installation contract

The primary installation method for consumers is direct installation from GitHub via
`pip` targeting an immutable commit SHA without manual cloning:

```bash
pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
```

- **Minimal declared extras/dependencies**: The Executor must verify whether a bare
  `pip install` satisfies all runtime requirements for `from mpips import convert_npz_to_dicom`
  or if a minimal declared extra (e.g. `[service]` or a dedicated conversion extra) is required.
  A bare install must NOT be claimed sufficient unless clean-environment testing proves it.
  If an extra is required, the primary command must explicitly specify the minimal declared
  extra (e.g. `pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>#egg=mpips[<extra>]"`
  or `pip install "mpips[<extra>] @ git+https://github.com/Madeena-software/mpips.git@<commit-sha>"`).
- **No manual clone**: Consumers must not be instructed or required to clone the repository manually.
- **Secondary tool testing (`uv`)**: If `uv` installation is documented (e.g. `uv pip install ...`),
  it must also be tested and verified in an isolated clean environment.

### 2. Public import surface contract

- **Required acceptance interface**:
  ```python
  from mpips import convert_npz_to_dicom
  ```
  This top-level import is mandatory and forms the primary public library contract.
- **Convenience interface**:
  ```python
  from mpips.conversion import convert_npz_to_dicom
  ```
  May be documented and provided as an additional convenience only, but does not substitute
  for or weaken the requirement for `from mpips import convert_npz_to_dicom`.
- **Outcome-level functional obligations**:
  - Library callers can invoke `convert_npz_to_dicom` passing the file-based inputs
    necessary for the supported conversion workflow:
    - radiograph NPZ file path,
    - gain calibration NPZ file path,
    - manifest metadata (file path, raw JSON, parsed dict, or manifest model),
    - output DICOM destination path,
    - optional calibration directory override.
  - The invocation must execute locally and must NOT require a running FastAPI HTTP
    server, Celery worker process, Redis instance, or external daemon.
  - The invocation must decouple from web framework error models: library consumers
    must receive standard Python exceptions (e.g. `ValueError`, `FileNotFoundError`,
    or runtime error) rather than `fastapi.HTTPException`.
- **Executor technical discretion**:
  - The Executor retains discretion over bounded implementation details: exact argument
    typing, helper function layout, export mechanism (e.g. `__all__` list and lazy loading
    patterns), internal exception class hierarchy, and worker isolation mechanism, provided
    they adhere to existing repository conventions and meet all functional obligations.

### 3. HTTP API compatibility contract

- The existing endpoint `POST /v1/radiographs/dicom` and `GET /health` must remain
  fully operational and backward-compatible.
- Route handlers in `mpips/api/routes/v1/dicom.py` may delegate to the public import
  surface or share underlying conversion services, mapping any internal errors cleanly
  to existing HTTP status codes (200, 400, 422, 500, 504) as asserted by existing tests.

### 4. Packaging requirements

- Setuptools configuration and package directory layout must ensure `mpips.conversion`
  and all required modules are discovered and packaged into distribution wheels.
- A wheel built from the repository or installed via Git must contain all modules
  needed to execute `from mpips import convert_npz_to_dicom`.

## Dependencies and assumptions

### Dependencies

- Baseline `c612ca4067a4cae83fb364858d0ed38cb8c2a0a0` remains the starting point.
- Python 3.12 environment with declared dependencies.
- Git, pip, and uv available for installation verification.

### Approved assumptions

- The public GitHub repository URL is `https://github.com/Madeena-software/mpips.git`.
- Base dependencies declared in `pyproject.toml` (`numpy`, `opencv-python-headless`,
  `pydantic`, `scipy`, `scikit-image`, `PyWavelets`, `pydicom`, `python-multipart`)
  are the baseline for conversion.
- Optional service dependencies (`fastapi`, `uvicorn`, `celery`, `redis`, `boto3`)
  must NOT be required for basic Python library import and conversion invocation.

### Remaining approval requirements

- Formal Planner/Reviewer validation of this candidate task revision (`1.1-candidate`)
  before implementation begins.
- No release, tagging, or PyPI publishing is authorized.

## Required capabilities

- Repository read and local write;
- Local shell execution for tests and static checks;
- Creation of isolated virtual environments for clean installation verification;
- Git branch management and remote push to `origin/feat/npz-dicom-import-module`.

## Execution constraints

1. **Strict non-modification of protected converter**:
   `mpips/conversion/tiff_json_to_dcm.py` MUST NOT be touched (SHA-256 invariant).
2. **Strict preservation of HTTP API**:
   Do not remove, alter, or rename any routes or existing API models.
3. **Ponytail reuse discipline**:
   Reuse existing validation logic in `mpips/conversion/service.py`, `validation.py`,
   and `metadata.py`. Do not create parallel conversion engines.
4. **Clean boundary separation**:
   Pure library usage must not require importing or running `fastapi`, `celery`, or `boto3`.

## Acceptance criteria

- [ ] `mpips.conversion` is properly recognized by setuptools and included in package
      builds (`python -m build --wheel` or `pip install`).
- [ ] MPIPS can be installed directly in a clean virtual environment without manual cloning
      using the documented primary command:
      `pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"`
      (with minimal declared extras if required, as verified by test).
- [ ] If `uv` installation is documented, it is also verified in an isolated clean environment.
- [ ] Bare install is not claimed sufficient unless clean-environment verification proves
      all required runtime imports succeed without optional extras.
- [ ] Required public import `from mpips import convert_npz_to_dicom` works cleanly and
      successfully converts NPZ radiograph, gain, and manifest to DICOM.
- [ ] Convenience import `from mpips.conversion import convert_npz_to_dicom` may be supported
      as an additional convenience, but does not substitute for `from mpips import convert_npz_to_dicom`.
- [ ] Ordinary library usage does not require a running API/worker service or raise
      `fastapi.HTTPException`.
- [ ] Protected converter SHA-256 remains
      `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` at
      `mpips/conversion/tiff_json_to_dcm.py` (`tests/test_converter_protection.py` passes).
- [ ] End-to-end NPZ radiograph + gain + manifest conversion produces a valid DICOM
      file readable by `pydicom`.
- [ ] Output DICOM adheres to all clinical invariants: 16-bit uint16 depth, correct
      dimensions, preserved spacing, populated UIDs, and canonical TRX clockwise orientation.
- [ ] All existing HTTP API endpoints (`POST /v1/radiographs/dicom`, `GET /health`)
      continue to pass all tests in `tests/api/test_dicom_conversion.py` and
      `tests/api/test_api_surface.py`.
- [ ] Full quality gates pass: Black, Flake8, mypy, and relevant pytest suites.
- [ ] Zero product code or test changes are executed before this candidate contract
      is accepted by the Planner/Reviewer.

## Verification requirements

### Required checks

1. **Converter Protection**:
   `pytest tests/test_converter_protection.py -v`
2. **Package Boundaries & Public Surface**:
   `pytest tests/test_public_boundaries.py tests/test_package_import.py -v`
3. **API Surface & DICOM Conversion**:
   `pytest tests/api/test_api_surface.py tests/api/test_dicom_conversion.py -v`
4. **Radiography Pipeline Invariants**:
   `pytest tests/test_imager_pipeline_workflow.py tests/test_radiography_pipeline.py -v`
5. **Clean Virtual Environment Git Install Smoke Test**:
   ```bash
   python3 -m venv /tmp/test-mpips-env
   /tmp/test-mpips-env/bin/pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
   /tmp/test-mpips-env/bin/python -c "from mpips import convert_npz_to_dicom; print('Top-level import succeeded')"
   rm -rf /tmp/test-mpips-env
   ```
   (If minimal declared extras are required, test with those extras; verify `uv` similarly if documented).
6. **Code Quality**:
   `black --check mpips tests`  
   `flake8 mpips tests`  
   `mypy mpips tests`

### Required evidence

The Executor must report:
- Pre-task baseline commit SHA (`c612ca4067a4cae83fb364858d0ed38cb8c2a0a0`);
- Git status proving only `.agents/tasks/npz-dicom-import-module.md` was updated;
- Verification that no product code, tests, CI workflows, or dependencies were altered;
- Branch push confirmation to `origin/feat/npz-dicom-import-module`.

## Stop conditions

The Executor must stop implementation and return to planning if:
1. The protected converter SHA deviates from `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
2. Preserving the HTTP API requires conflicting architectural compromises.
3. Git URL installation reveals unresolvable native binary packaging requirements
   that cannot be satisfied by standard `pip` or `uv`.
4. The Planner/Reviewer requests an alternative distribution or API structure
   outside this contract.

## Side-effect authorization

Under this candidate task authoring phase, the only authorized side effects are:
1. Authoring the candidate delivery contract at `.agents/tasks/npz-dicom-import-module.md`.
2. Committing this single task file to branch `feat/npz-dicom-import-module`.
3. Non-force pushing `feat/npz-dicom-import-module` to `origin`.

No product code modifications, dependency alterations, tagging, or pull request
merging are authorized.

## Expected terminal outcome

Candidate task authored and pushed for formal review:
`CANDIDATE TASK REMEDIATED — PLANNER REVIEW REQUIRED`
