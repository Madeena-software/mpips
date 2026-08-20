<!-- antigravity-code-agent-template:managed -->
# Project Context

**Status:** Verified
**Last verified:** 2026-08-05
**Repository checkpoint:** `3a17baca`

## Purpose and users

MPIPS is a Python service and library whose current production API surface is
the synchronous MHCS radiograph conversion endpoint. It accepts one
radiograph NPZ, its matching gain NPZ, and a JSON manifest, then returns a
validated DICOM response. The package also exposes importable calibration and
radiography workflows. Evidence: `mpips/api/application.py`,
`mpips/api/routes/v1/dicom.py`, and `mpips/workflows/`.

The intended consumers are Madeena services, internal processing tools, and
Python/Colab users of the packaged workflows. End-user accounts, billing,
business workflows, and a visual pipeline builder are outside this repository.
Evidence: API contracts in `mpips/api/schemas/` and the package entry points in
`pyproject.toml`.

## Current capabilities and flows

- `POST /v1/radiographs/dicom` is the one current business endpoint. It accepts
  the fixed internal-beta API-key header, runs the calibrated image-processing
  flow synchronously, calls the approved TIFF-to-DICOM converter, enriches and
  validates the DICOM, and returns it as `application/dicom`. `GET /health`
  reports only MPIPS service status and is unauthenticated.
  Evidence: `mpips/api/application.py`, `mpips/api/routes/v1/dicom.py`,
  `mpips/api/routes/v1/health.py`, and `tests/api/test_api_surface.py`.
- Generic DAG, Celery, S3, arbitrary URL, callback, webhook, and node-catalog
  functionality is outside the current production release. Its source code
  may remain in the repository for later work, but it is not registered by the
  running FastAPI application.
- The active DICOM route uses only the fixed API-key dependency in
  `mpips/api/api_key.py`; legacy JWT/JWKS modules are not called by the
  registered route. Idempotency uses the fixed `internal-beta` namespace.
- The importable imager workflow resolves NPZ inputs, validates gain and
  radiograph metadata, and adapts arrays to the canonical TIFF pipeline.
  Evidence: `mpips/workflows/imager_pipeline/` and
  `tests/test_imager_pipeline_workflow.py`.
- Calibration and legacy imager CLIs remain optional package entry points.
  Evidence: `[project.scripts]` and optional dependencies in `pyproject.toml`.

## Stack and architecture

- Python 3.12, setuptools, and `uv.lock`; FastAPI/Pydantic for HTTP contracts,
  Celery/Redis for jobs, boto3 for S3-compatible storage, and
  NumPy/OpenCV/SciPy/scikit-image/PyWavelets for processing. Evidence:
  `.python-version`, `pyproject.toml`, and `uv.lock`.
- `mpips/api/` owns the DICOM and health HTTP routes, schemas, auth, and
  request controls; `mpips/conversion/` and `mpips/engine/` own the current
  processing flow; `mpips/workflows/` owns library-facing orchestration.
  Generic worker, DAG, storage, and catalog modules remain available in the
  repository but are outside the current registered API surface.
- Runtime entry points are `mpips.asgi:app`, `mpips-api`, and `mpips-worker`.
  Docker selects `api` or `worker` through `docker/entrypoint.sh`. Evidence:
  `mpips/asgi.py`, `mpips/cli.py`, `Dockerfile`, and `pyproject.toml`.

## Commands

| Purpose | Command | Evidence | Remediation evidence |
|---|---|---|---|
| Install service | `python -m pip install -e ".[service]"` | `pyproject.toml` | Not run this pass |
| Install development tools | `python -m pip install -e ".[dev]"` | `pyproject.toml` | Existing `.venv` used |
| Run calibration | `python -m pip install -e ".[calibration]" && mpips-dotgrid` | `pyproject.toml` | Not run this pass |
| Run imager pipeline | `python -m pip install -e ".[imager]" && mpips-imager` | `pyproject.toml` | Not run this pass |
| Run API | `uvicorn mpips.asgi:app --host 0.0.0.0 --port 8000` | `mpips/asgi.py`, `docker/entrypoint.sh` | Not run this pass |
| Run worker | `celery -A mpips.worker worker --loglevel=info` | `mpips/worker/__init__.py` | Not run this pass |
| API surface test | `python -m uv run pytest tests/api/test_api_surface.py -v` | `tests/api/test_api_surface.py` | 3 passed, 1 warning |
| DICOM conversion test | `python -m uv run pytest tests/api/test_dicom_conversion.py -v` | `tests/api/test_dicom_conversion.py` | 15 passed, 5 warnings |
| DICOM authentication test | `python -m uv run pytest tests/api/test_dicom_authentication.py -v` | `tests/api/test_dicom_authentication.py` | Covered by the current focused pass |
| Full test suite | `python -m uv run pytest -v` | `tests/` | 100 passed, 9 warnings |
| Format check | `python -m uv run black --check mpips tests` | `pyproject.toml` | Failed only on unchanged `tests/test_host_launcher.py` |
| Lint | `python -m uv run flake8 mpips tests` | `.flake8` | Failed only on unchanged `tests/test_host_launcher.py` |
| Type check | `python -m uv run mypy mpips tests` | `pyproject.toml` | Passed; no issues in 67 source files |
| Build wheel | `.venv/bin/python -m build --wheel --no-isolation` | `pyproject.toml` | Not run in this remediation |

The `uv` executable was unavailable on `PATH`; the installed uv module was
invoked through `.venv/bin/python -m uv run` for these checks.

## Operational workflows

### Calibration

`mpips-dotgrid` runs the packaged dot-grid pipeline under
`mpips.calibration.dotgrid`; `MPIPS_ARTIFACT_ROOT` overrides its
artifact location. Model metadata, remap, validity mask, metrics, and detector
metadata must stay together. Fixed-canvas output preserves source dimensions
and requires the mask; expanded-canvas output preserves corrected edges and
writes coordinate-offset metadata. Filled border pixels are not measured image
data. Evidence: the calibration entry point and optional dependency in
`pyproject.toml`, plus `mpips/calibration/dotgrid/`.

### Imager pipeline

`mpips-imager` runs the canonical implementation in
`mpips.engine.imager_pipeline`; library and Colab callers should use
`mpips.workflows.imager_pipeline`. `MPIPS_RADIOGRAPHY_ENV` selects a settings
file, while the `colab` extra adds public Google Drive resolution. The workflow
validates NPZ gain, radiograph, calibration, camera, detector, identifier, and
shape data before returning 16-bit processed arrays. Reusable research code
must be promoted into `mpips.engine` rather than imported from `research/`.
Evidence: `pyproject.toml`, `mpips/workflows/imager_pipeline/`, and
`tests/test_imager_pipeline_workflow.py`.

Both workflows require distribution review against `THIRD_PARTY_NOTICES.md`
and `LICENSES/`; the ImageJ replication component carries GPL-v2 obligations.

## Data and integrations

- The current business flow receives NPZ files and a JSON manifest through the
  DICOM endpoint; it does not expose generic S3, URL, callback, or webhook API
  routes. Generic Redis, Celery, and S3 integration code remains outside this
  production API surface.
- Configuration names are documented in `.env.production.example`. Additional
  code-read names are `API_HOST`, `API_PORT`, `MPIPS_ENVIRONMENT`,
  `MPIPS_VERSION`, `MPIPS_WORKER_QUEUES`, `MPIPS_RADIOGRAPHY_ENV`, and
  `MPIPS_ARTIFACT_ROOT`. Never record their secret values.

## Conventions and constraints

- Keep route handlers thin and processing logic in `mpips/engine/`; canonical
  DAG node implementation, registry entry, catalog metadata, and focused tests
  belong under `mpips/dag/` and should move together. Evidence: current layout
  and `tests/test_promotion_flow.py`.
- Preserve the API-key boundary, fixed idempotency namespace,
  temporary-file cleanup, image bit depth where semantics allow, isolated
  worker time/resource limits, and webhook signing in legacy flows. Evidence:
  implementation and focused tests.
- Black and flake8 use line length 88; mypy is strict. Research and bundled
  legacy engines are excluded from the default quality gates. Evidence:
  `pyproject.toml` and `.flake8`.
- Repository policy prohibits direct SSH. Operational changes must use
  committed configuration or an approved platform/CI path; never commit
  secrets. This is a human-authored policy, not a runtime-enforced property.

## Proposed behavior

- Maintained documentation is centered in `.agents/context/`; do not recreate
  a root `docs/` directory or root `README.md`. This is explicit direction
  approved on 2026-07-19.

## Superseded facts

- Earlier context described now-absent research directory names and stale test
  counts. The current tree uses `research/kambing-260714/`; test counts and
  quality-gate results are recorded only when produced by the current pass.
- Separate stack, server, testing-pyramid, and project-context documents were
  consolidated here to remove conflicting authorities.

## Deployment

The internal-beta deployment is implemented by
`.github/workflows/deploy-internal-beta.yml` and
`docker-compose.prod.yml`. It builds commit-SHA API and NPZ-worker images,
binds the API only to `127.0.0.1:8014` (the canonical approved host-side port
for both local and production environments), keeps Redis private, mounts
calibration read-only, and retains the host launcher plus isolated worker
controls. The container listens on internal port 8000; only the host-side
published port 8014 is exposed on the loopback interface. Live workflow
evidence is recorded by the executing task.

## Local DICOM burn-in evidence

On 2026-08-11, the local Compose stack deployment (`docker-compose.local.yml`) was executed and validated with both synthetic fixtures and real kambing radiograph NPZ data (`BED_1783222264263.npz` and `BED_1783219207291.npz`). The stack bound strictly to `127.0.0.1:8000`, used private Redis, mounted the real calibration cache read-only (`4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b`), and launched isolated worker containers via the host launcher (`docker/host-launcher/mpips-launcher.py`).

The synthetic burn-in script completed 19/19 HTTP test cases (health, route checks, API key authentication, valid DICOM conversion, malformed input, idempotency, bounded concurrency, launcher error boundaries, and workspace cleanup).

Real kambing NPZ POST verification was executed against the running API container (`http://127.0.0.1:8000/v1/radiographs/dicom`) and produced a valid DICOM output (`24,785,860` bytes) with exact dimensions `Rows == 3053`, `Columns == 4059`, `BitsAllocated == 16`, `PixelRepresentation == 0`, and zero private DICOM tags.

The full focused test suite passed 32/32 tests. The protected converter SHA-256 remained `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

The
[Madeena deployment-template repository](https://github.com/Madeena-software/deploy-templates)
is the external authority for environment-template implementation. Copy and
specialize the applicable templates in `mpips`; do not duplicate their
implementation details in this context.


## Known gaps and open questions
- Redis, Celery, S3, JWKS, and webhook behavior were tested with local
  doubles; live infrastructure was not contacted.
- Wheel building remains unverified because the existing environment lacks the
  declared `wheel` build dependency. Dependencies were not installed during
  onboarding.
- No open product questions were identified for this documentation cleanup.
