# Session State

## 1. System Technology Stack

- Runtime: Python 3.12 (`.python-version` contains `3.12`; system Python
  observed as Python 3.12.3).
- Package metadata: `pyproject.toml` with setuptools build backend and
  `uv.lock` present.
- Backend: FastAPI, Uvicorn, Pydantic v2, Celery, Redis, boto3, httpx, PyJWT,
  cryptography.
- Image processing: OpenCV headless, NumPy, SciPy, scikit-image, PyWavelets.
- API: versioned `/v1` routes plus `/`, `/health`, `/docs`, `/redoc`, and
  `/v1/secure-test`.
- Worker: Celery app in `mpips/worker/__init__.py`; execution task in
  `mpips/worker/tasks.py`.
- Runtime state: Redis keys under `mpips:job:*`; no application metadata
  database detected.
- Object storage: AWS S3 or S3-compatible storage through `boto3`, with
  optional presigned URL input/output paths.
- Deployment: Docker image with `api` and `worker` roles through
  `docker/entrypoint.sh`.
- Static UI: none. The service is backend-only; `/docs` and `/redoc` are API
  documentation endpoints.
- CI/CD: no `.github/workflows/` files detected during bootstrap.

## 2. Active Goal

Google Colab Integration & Research for `kambing-260714`

## 3. Recent Milestones

- 2026-07-14: Created `imager_pipeline_tweak.ipynb` under `research/kambing-260714/` allowing colleagues to interactively research and tweak imager pipeline parameters with matplotlib visualizations on Google Colab.
- 2026-07-14: Created an NPZ to temporary TIFF wrapper so pipeline processes the 12-bit detector array formats seamlessly.
- 2026-07-08: Bootstrapped `.agents/` control center for the Python/FastAPI
  MPIPS repository.
- 2026-07-08: Replaced stale Laravel/Pest/Dusk agent guidance with
  Python/FastAPI/Celery-specific project rules.
- 2026-07-08: Captured detected environment variables, modules, test commands,
  deployment constraints, and verification blockers in `.agents/`.
- 2026-07-08: Refactored package ownership so `mpips/` is the only
  importable/service source. Removed legacy `app/`, `image_engine/`, and
  `celery_tasks/` trees after confirming the project should be clean rather
  than compatibility-first.
- 2026-07-08: Removed dashboard static frontend assets; MPIPS is backend-only.
- 2026-07-08: Moved prototype folders to `research/`, renamed
  `camera-callibration-dotgrid` to `research/camera-calibration-dotgrid`, and
  removed tracked `*:Zone.Identifier` metadata files.
- 2026-07-08: Added promotion-flow example with
  `mpips.engine.calibration.warp_image` and backend node
  `camera_calibration_warp`, increasing the catalog to 25 nodes.

## 4. Environment & Health Status

- Current shell path audited: `/var/www/mpips`.
- A local `.venv` was created for verification because system Python is
  externally managed and did not have project tooling installed.
- `.venv/bin/pip install -e ".[dev]"` completed successfully.
- `.venv/bin/pip install matplotlib python-dotenv` completed successfully to enable pipeline research scripts.
- `.venv/bin/pip install -e ".[calibration]"` completed successfully to enable neural calibration in Jupyter notebooks.
- `.venv/bin/uv lock` refreshed `uv.lock` after dependency extra changes.
- `.venv/bin/pytest -q` passed: 62 tests, 4 warnings.
- `.venv/bin/black --check .` passed.
- `.venv/bin/flake8 .` passed.
- `.venv/bin/mypy .` passed: no issues in 46 source files.
- Test suite exists under `tests/` and covers API, Celery/webhook behavior,
  DAG sorting/execution, image nodes, scientific nodes, security, storage,
  package imports, and root route behavior.
- No CI workflow was detected, so automated verification is not currently
  discoverable from repository files.

## 5. Known Issues

- The root `README.md` now references `.env.production.example` for local env
  bootstrap.
- `.agents/prompts/bootstrap-new-repo.md` remains a pre-existing modified file
  and still contains the original bootstrap prompt wording. Do not overwrite it
  without explicit user direction.
- The repo contains bundled prototype/research folders
  under `research/`; future agents must avoid treating those folders as part of
  the packaged MPIPS service unless a task explicitly targets them.
- No CI/CD workflow files were detected even though deployment should happen
  through committed pipeline/configuration changes rather than direct server
  access.

## 6. Next Steps

- Add or confirm CI/CD workflow files for test, lint, type check, Docker build,
  and deployment promotion.
- Consider future extraction or pruning of large tracked research outputs if
  repository size becomes a practical problem.
