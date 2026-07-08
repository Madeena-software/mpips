# Project Context

## Purpose

MPIPS is the Madeena Python Image Processing Services repository. It provides a
reusable execution plane for image-processing Directed Acyclic Graphs (DAGs).
Clients submit jobs over a secured FastAPI API, workers execute long-running
image transformations through Celery, job state is tracked in Redis, images are
read from and written to S3-compatible object storage, and callers can receive
signed webhook callbacks.

MPIPS is a shared service for Madeena clients such as `mipc`, Madeena mobile
and web apps, and internal research tooling. It is not responsible for end-user
business workflows, user profiles, billing, visual builder UI, or direct
end-user image serving.

## Key Features

- Secure versioned REST API under `/v1`.
- OAuth2/JWKS JWT verification with required scope checks.
- Developer auth bypass for local testing through `DEV_AUTH_BYPASS` and
  `DEV_BEARER_TOKEN`.
- Dynamic 24-node image-processing catalog exposed by `GET /v1/nodes`.
- Asynchronous job submission, polling, listing, and cancellation.
- Redis-backed job state under `mpips:job:*`.
- Celery worker execution for long-running DAG workloads.
- Topological DAG sorting with cycle detection.
- S3-compatible object storage and presigned URL IO.
- Tenant prefix validation for S3 keys and output prefixes.
- HMAC-signed webhook callbacks with timestamp headers.
- IQA metrics in output metadata.
- Docker runtime supporting `api` and `worker` roles.
- Static dashboard mounted at `/dashboard/`.

## Setup Instructions

Preferred dependency path, once `uv` is installed:

```bash
uv sync
```

Standard virtualenv path:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or after editable/package install:

```bash
mpips-api
```

Run the worker:

```bash
celery -A celery_tasks.worker worker --loglevel=info
```

Or after editable/package install:

```bash
mpips-worker
```

Docker roles:

```bash
docker run --env-file .env.production -p 8000:8000 mpips:latest api
docker run --env-file .env.production mpips:latest worker
```

## Environment Variables & Configuration

Root bootstrap detected `.env.production.example`. No root `.env.example` file
was detected.

Detected keys in `.env.production.example`:

- `DEV_AUTH_BYPASS`: Enables static developer-token auth bypass when set to
  `true`. Must stay disabled in production.
- `DEV_BEARER_TOKEN`: Static token accepted when developer bypass is enabled.
- `MADEENA_IDP_JWKS_URL`: JWKS endpoint for production JWT verification.
- `MADEENA_REQUIRED_SCOPES`: Comma-separated scopes required by protected API
  routes. Current default is `image:process,nodes:read`.
- `REDIS_URL`: Redis URL for direct job-state health and task state helpers.
- `CELERY_BROKER_URL`: Celery broker URL.
- `CELERY_RESULT_BACKEND`: Celery result backend URL.
- `AWS_ACCESS_KEY_ID`: S3-compatible access key.
- `AWS_SECRET_ACCESS_KEY`: S3-compatible secret key.
- `AWS_DEFAULT_REGION`: S3 region. Current example uses `us-east-1`.
- `AWS_BUCKET`: Default bucket for direct S3 input/output operations.
- `AWS_ENDPOINT_URL`: Optional S3-compatible endpoint, for example MinIO.
- `WEBHOOK_SECRET`: Shared HMAC secret for outgoing webhook signatures.
- `PORT`: Container API port used by `docker/entrypoint.sh`.
- `MPIPS_API_WORKERS`: Number of Uvicorn workers for the API role.
- `MPIPS_WORKER_LOG_LEVEL`: Celery worker log level.
- `MPIPS_WORKER_CONCURRENCY`: Celery worker process concurrency.
- `MPIPS_WORKER_MAX_TASKS_PER_CHILD`: Worker child recycle threshold.
- `MPIPS_WORKER_PREFETCH_MULTIPLIER`: Celery task prefetch multiplier.
- `MPIPS_WORKER_TASK_SOFT_TIME_LIMIT`: Soft time limit for pipeline tasks in
  seconds.
- `MPIPS_WORKER_TASK_TIME_LIMIT`: Hard time limit for pipeline tasks in
  seconds.

Additional environment keys used by code but not present in
`.env.production.example`:

- `API_HOST`: Host used by `mpips-api`; defaults to `0.0.0.0`.
- `API_PORT`: Port used by `mpips-api`; falls back to `PORT` or `8000`.
- `MPIPS_VERSION`: Overrides FastAPI and health-check version display.
- `MPIPS_ENVIRONMENT`: Displayed by `/health`; defaults to `development`.
- `MPIPS_WORKER_QUEUES`: Optional Celery queue list for worker startup.

## Repository Structure

- `.agents/`: Agent control center and project operating rules.
- `app/main.py`: FastAPI app, docs, root, health, dashboard mount, and router
  inclusion.
- `app/api/v1/`: Versioned FastAPI routes for nodes and jobs.
- `app/core/`: Catalog, DAG execution, auth, storage, and tenant path rules.
- `app/schemas/`: Pydantic request/response and catalog schemas.
- `app/dashboard/`: Static dashboard assets served by FastAPI.
- `celery_tasks/`: Celery app and task definitions.
- `image_engine/`: Image-processing node implementations, factory, and IQA.
- `mpips/`: Installable package interface, ASGI entrypoint, CLI, and public
  engine exports.
- `tests/`: Pytest suite.
- `docker/`: Runtime entrypoint scripts.
- `Dockerfile`: Python 3.12 slim container image for API and worker roles.
- `docs/PRD.md`: Product requirements and service boundary authority.
- `camera-callibration-dotgrid/`: Bundled calibration research/prototype
  artifacts; not included in the packaged MPIPS service.
- `imager-pipeline/`: Bundled legacy/prototype image pipeline scripts; not
  included in the packaged MPIPS service.

## General Coding Conventions

- Keep the public API versioned under `app/api/v1/`.
- Keep Pydantic models in `app/schemas/`; avoid duplicating request/response
  shapes inside route functions.
- Keep execution logic out of route handlers. Routes should validate, enqueue,
  read Redis state, and return schemas.
- Keep reusable image operations in `image_engine/nodes/` and register catalog
  metadata in `app/core/catalog.py`.
- Preserve tenant-prefix validation for direct S3 keys and output prefixes.
- Do not enable developer auth bypass in production configuration.
- Do not add persistent application metadata storage without a PRD update.
- Keep legacy/prototype folders out of normal service changes unless the task
  explicitly targets them.
- Use Black line length 88, flake8 max line length 88, and strict mypy settings
  from `pyproject.toml`.
