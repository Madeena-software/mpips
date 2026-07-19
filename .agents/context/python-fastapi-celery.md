# Python FastAPI Celery Rules

## Architecture And Routing

- The primary FastAPI app entrypoint is `mpips/api/application.py`; the
  installed ASGI entrypoint is `mpips.asgi:app`.
- Keep versioned product routes under `mpips/api/routes/v1/router.py`.
- Public utility routes may live in `mpips/api/application.py` only when they
  are global service concerns such as `/`, `/health`, `/docs`, `/redoc`,
  or `/v1/secure-test`.
- Route handlers should remain thin: validate request bodies, call security
  dependencies, enqueue Celery work, read/write Redis job state, and return
  Pydantic response models.
- Add or change request/response contracts in `mpips/api/schemas/` first, then
  wire routes to those contracts.
- Keep engine/catalog node schemas in `mpips/engine/schemas.py`.
- Keep DAG validation and execution in `mpips/engine/dag.py` and image
  operations in `mpips/engine/nodes/`.
- When adding a processing node, update all required places together:
  `mpips/engine/nodes/`, `mpips/engine/registry.py`,
  `mpips/engine/catalog.py`, and focused tests.
- Experimental code starts in `research/<topic>/`; backend code must only use
  logic promoted into `mpips/engine/`.

## State Management And Storage

- Redis is runtime state, not a business database. Job state is stored under
  `mpips:job:*`.
- Do not introduce persistent metadata tables unless `docs/PRD.md` is updated.
- Preserve tenant path validation in `mpips/tenant_paths.py` for direct S3 keys
  and output prefixes.
- S3 bucket overrides inside execution must be restored after use. Be careful
  with any change that mutates `os.environ["AWS_BUCKET"]`.
- Temporary files created during DAG execution must be cleaned in `finally`
  blocks.
- Preserve native image bit depth when node semantics allow it. Only force
  8-bit conversion when the node behavior or explicit parameter requires it.

## Security

- Protected routes must depend on `verify_token`.
- Production auth must use JWKS/JWT verification and required scopes from
  `MADEENA_REQUIRED_SCOPES`.
- `DEV_AUTH_BYPASS=true` is for local development and tests only. Never commit
  production examples with bypass enabled.
- Do not log secrets, bearer tokens, full signed URLs, or raw webhook secrets.
- Webhook callbacks must remain HMAC-signed with `X-Madeena-Signature` and
  `X-Madeena-Timestamp`.
- Do not allow cross-tenant S3 key access through new input or output modes.

## Performance

- Keep API endpoints responsive. Long-running image processing belongs in
  Celery tasks.
- Preserve Celery settings that protect worker stability:
  `task_acks_late`, `task_reject_on_worker_lost`, task time limits, and
  prefetch controls.
- Avoid loading unnecessary duplicate image arrays for large TIFF/high bit
  depth workflows.
- Keep worker concurrency and max-tasks-per-child configurable through env
  variables.
- Avoid expensive network calls during FastAPI startup. JWKS resolution is
  intentionally lazy.

## Verification And Testing Commands

Preferred commands from the repository documentation:

```bash
uv run pytest
uv run black --check .
uv run flake8 .
uv run mypy .
```

Fallback commands after activating a virtualenv and installing dev
dependencies:

```bash
python -m pytest
python -m black --check .
python -m flake8 .
python -m mypy .
```

For targeted service-only checks, scope tools to the packaged service paths:

```bash
python -m pytest tests
python -m black --check mpips tests
python -m flake8 mpips tests
python -m mypy mpips tests
```

Default Black/flake8/mypy configuration excludes `research/`; research scripts
are not part of service quality gates unless a task explicitly targets them.
