# Session State

## 1. System Technology Stack

- Runtime: Python 3.12 (`.python-version` contains `3.12`; system Python
  observed as Python 3.12.3).
- Package metadata: `pyproject.toml` with setuptools build backend and
  `uv.lock` present.
- Backend: FastAPI, Uvicorn, Pydantic v2, Celery, Redis, boto3, httpx, PyJWT,
  cryptography.
- Image processing: OpenCV headless, NumPy, SciPy, scikit-image, PyWavelets.
- API: versioned `/v1` routes plus `/`, `/health`, `/docs`, `/redoc`,
  `/dashboard/`, and `/v1/secure-test`.
- Worker: Celery app in `celery_tasks/worker.py`; execution task in
  `celery_tasks/tasks.py`.
- Runtime state: Redis keys under `mpips:job:*`; no application metadata
  database detected.
- Object storage: AWS S3 or S3-compatible storage through `boto3`, with
  optional presigned URL input/output paths.
- Deployment: Docker image with `api` and `worker` roles through
  `docker/entrypoint.sh`.
- Static UI: dashboard assets in `app/dashboard/` mounted by FastAPI.
- CI/CD: no `.github/workflows/` files detected during bootstrap.

## 2. Active Goal

Project Onboarding

## 3. Recent Milestones

- 2026-07-08: Bootstrapped `.agents/` control center for the Python/FastAPI
  MPIPS repository.
- 2026-07-08: Replaced stale Laravel/Pest/Dusk agent guidance with
  Python/FastAPI/Celery-specific project rules.
- 2026-07-08: Captured detected environment variables, modules, test commands,
  deployment constraints, and verification blockers in `.agents/`.

## 4. Environment & Health Status

- Current shell path audited: `/var/www/mpips`.
- Worktree at audit time had one pre-existing modified file:
  `.agents/prompts/bootstrap-new-repo.md`.
- `uv run pytest` was attempted and failed because `uv` is not installed.
- `python3 -m pytest` was attempted and failed because `pytest` is not
  installed in system Python.
- Test suite exists under `tests/` and covers API, Celery/webhook behavior,
  DAG sorting/execution, image nodes, scientific nodes, security, storage,
  package imports, and root route behavior.
- No CI workflow was detected, so automated verification is not currently
  discoverable from repository files.

## 5. Known Issues

- Local verification is blocked until development dependencies are installed
  with `uv sync` or `python3 -m venv .venv && pip install -e ".[dev]"`.
- Root `README.md` references `.env.example`, but bootstrap only detected
  `.env.production.example` at the repository root.
- `.agents/prompts/bootstrap-new-repo.md` remains a pre-existing modified file
  and still contains the original bootstrap prompt wording. Do not overwrite it
  without explicit user direction.
- The repo contains bundled prototype/research folders
  `camera-callibration-dotgrid/` and `imager-pipeline/`; future agents must
  avoid treating those folders as part of the packaged MPIPS service unless a
  task explicitly targets them.
- No CI/CD workflow files were detected even though deployment should happen
  through committed pipeline/configuration changes rather than direct server
  access.

## 6. Next Steps

- Install development tooling and rerun `uv run pytest`, `uv run black --check .`,
  `uv run flake8 .`, and `uv run mypy .`.
- Add or confirm CI/CD workflow files for test, lint, type check, Docker build,
  and deployment promotion.
- Decide whether to add a root `.env.example` or update `README.md` to point
  consistently at `.env.production.example` plus local development overrides.
- Clarify whether `camera-callibration-dotgrid/` and `imager-pipeline/` should
  remain bundled in this repo, be ignored by core verification, or be extracted.
