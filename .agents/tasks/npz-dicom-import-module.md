---
title: NPZ to DICOM Public Import Module and Direct Git Distribution
document_id: TASK-NPZ-DICOM-IMPORT-MODULE-001
version: 1.0-candidate
status: Candidate / Draft (Planner Review Required)
language: en-US
last_updated: 2026-09-05
scope:
  - public Python import surface for NPZ-to-DICOM conversion
  - direct Git distribution via pip and uv without manual clone
  - HTTP API and protected converter preservation
  - clinical DICOM and orientation invariant enforcement
  - clean-environment installation and end-to-end verification
authority_note: >-
  This candidate task artifact authors the reviewable delivery contract for the
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
manually cloning it, then use a supported Python import surface for NPZ-to-DICOM
conversion, while preserving the existing HTTP API, package boundaries, protected
converter SHA, and clinical DICOM invariants.

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
   lacks `mpips/conversion/__init__.py`. Because `pyproject.toml` uses
   `tool.setuptools.packages.find` with `include = ["mpips*"]`, setuptools only
   packages directories containing an `__init__.py`. Consequently, installing `mpips`
   from Git currently omits `mpips.conversion` entirely from the built wheel.
3. Users who want to programmatically convert radiographs from NPZ arrays and gain
   calibrations to DICOM in Python without running or calling an HTTP service have no
   supported, documented import entrypoint.
4. The distribution model requires direct installation from public GitHub via `pip`
   or `uv` without requiring manual repository cloning.

This candidate delivery contract specifies the technical requirements, design
options, invariants, and verification obligations to implement this capability
safely and reproducibly.

## Baseline and task revision

**Implementation baseline:**  
`c612ca4067a4cae83fb364858d0ed38cb8c2a0a0` (`main` @ HEAD)

**Task revision:**  
`resolved when published` (Draft candidate; will resolve to the task-only commit
on `feat/npz-dicom-import-module`)

The implementation baseline and governing task revision are separate references.
Do not change the implementation baseline silently during execution.

## Objective

Deliver a supported, documented, and thoroughly verified Python import surface for
converting NPZ radiograph and gain data plus manifest metadata into standard
DICOM files, installable directly from public GitHub via `pip` or `uv` without
cloning, with zero regressions to the existing HTTP API or clinical DICOM invariants.

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
   - Ensure `mpips.conversion` is recognized and packaged by setuptools so that
     direct Git installs contain all necessary modules.
   - Introduce `mpips/conversion/__init__.py` to define the public conversion package.
2. **Public import surface**:
   - Provide a clean, documented public import spelling for NPZ-to-DICOM conversion.
   - Ensure input parameters accept paths (`Path` or `str`), dictionaries, or
     pydantic manifest objects (`MHCSManifest`, `ResolvedMHCSManifest`).
   - Decouple library-level exception reporting from web-framework exceptions
     (`fastapi.HTTPException`), so that library users experience standard Python
     exceptions (`ValueError`, `RuntimeError`, or a lightweight `ConversionError`).
3. **HTTP API preservation**:
   - The existing HTTP endpoint `POST /v1/radiographs/dicom` and `GET /health` must
     remain completely supported, unchanged, and operational.
   - The endpoint handler may delegate to the public import surface or share the
     underlying isolated execution service.
4. **Direct Git installation verification**:
   - Support installation via `pip` and `uv` directly from GitHub using a Git URL.
   - Verify installation in an isolated, clean virtual environment without repository
     cloning.
5. **Comprehensive verification**:
   - Add focused tests for the public import surface (`tests/test_conversion_import.py`
     or integration into `tests/test_public_boundaries.py`).
   - Run existing test suites for API surface, DICOM conversion, converter protection,
     and static analysis (Black, Flake8, mypy).

### Out of scope (non-goals)

1. PyPI publishing or credentials management.
2. Private package registry setup or publishing.
3. Deployment, server provisioning, container release, or production mutation.
4. Modifying the protected converter `mpips/conversion/tiff_json_to_dcm.py` or its SHA.
5. Altering clinical image processing algorithms, thresholding, CLAHE, or TRX calibration.
6. Refactoring unrelated subsystems (e.g. DAG executor, Celery workers, dotgrid neural models).
7. Adding heavy external dependencies not already in `pyproject.toml`.

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

## Design options and recommendations for Planner/Reviewer decision

### 1. Supported Git installation command and Git reference

**Analysis of Git reference alternatives:**

| Reference Type | Example | Reproducibility | Maintenance & Conventions |
| :--- | :--- | :--- | :--- |
| **Branch** | `git+https://github.com/Madeena-software/mpips.git@main` | Mutable; changes when commits land; risk of non-deterministic behavior in clinical pipelines. | Convenient for rolling consumers, but violates immutable baseline requirements of `.agents/AGENTS.md`. |
| **Release Tag** | `git+https://github.com/Madeena-software/mpips.git@v0.1.0` | High; semantic versioning; standard Python packaging convention. | Currently **no git tags exist** in the repository (`git tag -l` returns empty). Tag creation belongs to release governance, which is out of scope. |
| **Immutable Commit SHA** (Recommended) | `git+https://github.com/Madeena-software/mpips.git@c612ca4067a4cae83fb364858d0ed38cb8c2a0a0` | **Absolute (Cryptographic)**; 100% reproducible; immune to branch drift or upstream changes. | Strongly aligns with `.agents/` delivery contract and medical device software traceability. Works natively in `pip` and `uv`. |

**Proposed supported installation commands:**

- Primary (reproducible):
  ```bash
  pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
  ```
  ```bash
  uv pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
  ```
- Secondary (rolling development convenience):
  ```bash
  pip install "git+https://github.com/Madeena-software/mpips.git@main"
  ```
  ```bash
  uv pip install "git+https://github.com/Madeena-software/mpips.git@main"
  ```

### 2. Public import surface spelling

**Analysis of import spelling options:**

- **Option A (Subpackage canonical entrypoint — Recommended)**:
  ```python
  from mpips.conversion import convert_npz_to_dicom
  ```
  *Justification*: Matches the established pattern in MPIPS for domain subpackages:
  - `from mpips.calibration import warp_image`
  - `from mpips.dag import DAGExecutor`
  - `from mpips.iqa import calculate_all_metrics`
  Exposing `convert_npz_to_dicom` in `mpips.conversion` follows the existing convention
  identically.

- **Option B (Top-level package export)**:
  ```python
  import mpips
  mpips.convert_npz_to_dicom(...)
  # or
  from mpips import convert_npz_to_dicom
  ```
  *Justification*: Matches `mpips.app` and `mpips.DAGExecutor` in `mpips/__init__.py`.
  Can be implemented via lazy `__getattr__` in `mpips/__init__.py` to avoid eager loading.

- **Option C (Both Option A and Option B)**:
  Provide the canonical symbol in `mpips.conversion` and re-export lazily in `mpips`
  top-level `__init__.py`.

- **Option D (Direct service function exposure)**:
  ```python
  from mpips.conversion.service import run_isolated_dicom_conversion
  ```
  *Limitation*: Currently raises `fastapi.HTTPException`, coupling the library caller
  to FastAPI error models.

**Recommended spelling for Planner/Reviewer adoption:**
Option C (primary in `mpips.conversion`, lazy convenience alias in `mpips`).

### 3. Public function signature & exception decoupling

**Proposed signature:**
```python
def convert_npz_to_dicom(
    radiograph_npz_path: str | Path,
    gain_npz_path: str | Path,
    manifest: str | Path | dict[str, Any] | MHCSManifest | ResolvedMHCSManifest,
    output_dicom_path: str | Path,
    *,
    calibration_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Convert NPZ radiograph and gain arrays into an enriched DICOM file.
    
    Args:
        radiograph_npz_path: Path to radiograph NPZ file.
        gain_npz_path: Path to gain calibration NPZ file.
        manifest: Manifest as file path, JSON string, dict, or Pydantic model.
        output_dicom_path: Destination path for output DICOM file.
        calibration_dir: Optional path to directory containing calibration assets.
                         If omitted, uses default resolved calibration directory.
                         
    Returns:
        dict with execution status, output byte size, and validation flags.
        
    Raises:
        ValueError: If input arguments, manifests, or NPZ contents fail validation.
        FileNotFoundError: If input files or calibration assets do not exist.
        ConversionError: If conversion worker process fails or times out.
    """
```

**Exception handling decoupling:**
`run_isolated_dicom_conversion` currently raises `fastapi.HTTPException`.
The recommended implementation will introduce a core conversion layer (or wrap
exceptions) that raises standard Python exceptions (`ConversionError`, `ValueError`,
`FileNotFoundError`), while the HTTP route in `mpips/api/routes/v1/dicom.py` maps
these exceptions cleanly to HTTP 400, 422, 500, or 504 responses.

### 4. Packaging prerequisite

**Observed evidence in current baseline:**
Running `setuptools.find_packages` currently discovers:
`['mpips', 'mpips.workflows', 'mpips.processing', 'mpips.api', 'mpips.dag', 'mpips.calibration', 'mpips.pipelines', 'mpips.iqa', 'mpips.worker', ...]`
`mpips.conversion` is **missing** from package discovery because `mpips/conversion/__init__.py`
does not exist.
Creating `mpips/conversion/__init__.py` with proper `__all__` and lazy exports solves
this issue immediately and enables full packaging during `pip install`.

## Dependencies and assumptions

### Dependencies

- Baseline `c612ca4067a4cae83fb364858d0ed38cb8c2a0a0` remains the starting point.
- Python 3.12 environment with declared dependencies.
- Git, pip, and uv available for installation verification.

### Approved assumptions

- The public GitHub repository URL is `https://github.com/Madeena-software/mpips.git`.
- Base dependencies declared in `pyproject.toml` (`numpy`, `opencv-python-headless`,
  `pydantic`, `scipy`, `scikit-image`, `PyWavelets`, `pydicom`, `python-multipart`)
  are sufficient for NPZ-to-DICOM conversion.
- Optional dependencies like `fastapi`, `uvicorn`, `celery`, `redis`, `boto3` must
  NOT be required for basic Python library import and conversion.

### Remaining approval requirements

- Formal Planner/Reviewer review and validation of this candidate task contract.
- Reviewer confirmation on preferred import spelling (`mpips.conversion` vs `mpips`).
- No release, tagging, or PyPI publishing is authorized.

## Required capabilities

- Repository read and local write;
- Local shell execution for tests and static checks;
- Creation of isolated virtual environments for installation verification;
- Git branch management and remote push to `origin/feat/npz-dicom-import-module`.

## Execution constraints

1. **Strict non-modification of protected converter**:
   `mpips/conversion/tiff_json_to_dcm.py` MUST NOT be touched.
2. **Strict preservation of HTTP API**:
   Do not remove, alter, or rename any routes or existing API models.
3. **Ponytail reuse discipline**:
   Reuse existing validation logic in `mpips/conversion/service.py`, `validation.py`,
   and `metadata.py`. Do not create parallel conversion engines.
4. **Clean boundary separation**:
   Pure library usage must not import `fastapi`, `celery`, or `boto3`.

## Acceptance criteria

- [ ] `mpips.conversion` is properly recognized by setuptools and included in package
      builds (`python -m build --wheel` or `pip install`).
- [ ] MPIPS can be installed directly in a clean virtual environment using:
      `pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"`
      and `uv pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"`.
- [ ] Public import `from mpips.conversion import convert_npz_to_dicom` (and/or
      `from mpips import convert_npz_to_dicom`) works cleanly without requiring
      `fastapi` or background service daemons.
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
   /tmp/test-mpips-env/bin/python -c "from mpips.conversion import convert_npz_to_dicom; print('Import succeeded')"
   rm -rf /tmp/test-mpips-env
   ```
6. **Code Quality**:
   `black --check mpips tests`  
   `flake8 mpips tests`  
   `mypy mpips tests`

### Required evidence

The Executor must report:
- Pre-task baseline commit SHA (`c612ca4067a4cae83fb364858d0ed38cb8c2a0a0`);
- Git status proving only `.agents/tasks/npz-dicom-import-module.md` was created;
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
`CANDIDATE SUCCESSOR DELIVERY CONTRACT — PLANNER REVIEW REQUIRED`
