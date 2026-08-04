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

- `POST /v1/radiographs/dicom` is the one current business endpoint. It runs
  the calibrated image-processing flow synchronously, calls the approved
  TIFF-to-DICOM converter, enriches and validates the DICOM, and returns it as
  `application/dicom`. `GET /health` reports only MPIPS service status.
  Evidence: `mpips/api/application.py`, `mpips/api/routes/v1/dicom.py`,
  `mpips/api/routes/v1/health.py`, and `tests/api/test_api_surface.py`.
- Generic DAG, Celery, S3, arbitrary URL, callback, webhook, and node-catalog
  functionality is outside the current production release. Its source code
  may remain in the repository for later work, but it is not registered by the
  running FastAPI application.
- Protected routes validate bearer tokens through JWKS/JWT scopes, with an
  explicit local-development bypass. Evidence: `mpips/api/security.py`.
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
| DICOM authentication test | `python -m uv run pytest tests/api/test_dicom_authentication.py -v` | `tests/api/test_dicom_authentication.py` | 6 passed, 1 warning |
| Full test suite | `python -m uv run pytest -v` | `tests/` | 100 passed, 1 failed in unchanged `tests/test_host_launcher.py` |
| Format check | `python -m uv run black --check mpips tests` | `pyproject.toml` | Failed only on unchanged `tests/test_host_launcher.py` |
| Lint | `python -m uv run flake8 mpips tests` | `.flake8` | Failed only on unchanged `tests/test_host_launcher.py` |
| Type check | `python -m uv run mypy mpips tests` | `pyproject.toml` | Passed; no issues in 67 source files |
| Build wheel | `.venv/bin/python -m build --wheel --no-isolation` | `pyproject.toml` | Not run in this remediation |

The `uv` executable was unavailable on `PATH`; the installed uv module was
invoked through `.venv/bin/python -m uv run` for these checks.

## Operational workflows

### Calibration

`mpips-dotgrid` runs the packaged dot-grid pipeline under
`mpips.engine.calibration.dotgrid`; `MPIPS_ARTIFACT_ROOT` overrides its
artifact location. Model metadata, remap, validity mask, metrics, and detector
metadata must stay together. Fixed-canvas output preserves source dimensions
and requires the mask; expanded-canvas output preserves corrected edges and
writes coordinate-offset metadata. Filled border pixels are not measured image
data. Evidence: the calibration entry point and optional dependency in
`pyproject.toml`, plus `mpips/engine/calibration/dotgrid/`.

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

- Keep route handlers thin and processing logic in `mpips/engine/`; add node
  implementation, registry entry, catalog metadata, and focused tests
  together. Evidence: current layout and `tests/test_promotion_flow.py`.
- Preserve tenant checks, auth boundaries, temporary-file cleanup, image bit
  depth where semantics allow, Celery late acknowledgements/time limits, and
  webhook signing. Evidence: implementation and focused tests.
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

Production readiness is not yet claimed. Authentication hardening, isolated
NPZ execution, calibration binding, idempotency, and deployment controls are
separate tasks.

## Local DICOM burn-in evidence

On 2026-08-05, the local DICOM-only deployment was verified from repository
commit `45063e8479256795d0ea7e629daae840c7329e8a` using the existing virtual
environment's `.venv/bin/python -m uv` equivalent because `uv` was not on
`PATH`. The baseline focused suites were API surface 3 passed, authentication
6 passed, conversion 15 passed, and host launcher 5 passed/1 failed; the full
baseline was 100 passed/1 failed on the same launcher socket framing case. The
smallest remediations corrected the newline-delimited launcher test, stale
worker image copy paths, read-only workspace cleanup, production worker-result
error mapping, and malformed/out-of-range NPZ classification.

The final local stack used `docker-compose.local.yml` with `mpips-api` bound
only to `127.0.0.1:8000`, private Redis without a published host port, a
private JWKS double, a dedicated `mpips-local-private-v1` network, a read-only
calibration mount, and a task-owned workspace plus launcher socket. Deterministic
local images were `mpips-api:local-20260805` and
`mpips-npz-worker:local-20260805`; the API image default user is `mpips` and the
worker image defaults to UID/GID `10001:10001`. The local API service and
launcher use the task-owned UID/GID for the mounted workspace. Rendered Compose
and Docker inspection showed no
`latest` service image, no Nginx/public ingress, no Redis port publication, and
no secret environment values in either image configuration.

The synthetic burn-in script under `scripts/local_dicom_burn_in.py` completed
56 HTTP cases. It validated a 200 `application/dicom` response as explicit-VR
little-endian, 64x64 uint16 DICOM with expected synthetic patient/study/UID
values, `BurnedInAnnotation=NO`, `LossyImageCompression=00`, no private tags,
and successful DICOM validation. Authentication, HMAC, multipart, NPZ,
calibration, idempotency, worker failure, path, and concurrency cases all
returned controlled results. Redis interruption returned
`503 IDEMPOTENCY_STORAGE_UNAVAILABLE`; recovery and expired-lease reclaim
returned 200; malformed cached state returned sanitized 409. API restart
recovered health and valid conversion. The workspace directory returned to its
pre-run 33 child directories, with no task worker container orphan.

Final verification produced API surface 3 passed, authentication 6 passed,
conversion 17 passed, host launcher 6 passed, and full repository 103 passed
with only the existing warning set. Black, flake8, and mypy passed for the
task-owned and active-path files; repository black and flake8 also passed. The
protected converter SHA-256 remained
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` before
and after. Generated secrets and synthetic outputs stayed outside tracked
files, and no production service, remote deployment, push, or workflow was
used.

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
