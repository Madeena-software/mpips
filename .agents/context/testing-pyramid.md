# Testing Pyramid Strategy

This repository uses pytest for service, API, and image-processing verification.
All new work must keep the suite biased toward fast, deterministic tests.

## Distribution

- 60% Unit tests: isolated node behavior, DAG sorting, schemas, tenant path
  validation, IQA helpers, auth helpers, and small pure functions.
- 30% Feature/Integration tests: FastAPI routes through `TestClient`, Celery
  task behavior with mocked Redis/S3/webhooks, storage helpers with moto or
  equivalent fakes, and package entrypoint behavior.
- 10% E2E/service smoke tests: API plus worker plus Redis plus S3-compatible
  storage in a real or containerized environment. No browser E2E framework is
  currently detected.

## Methodology

- Test-Driven Development is mandatory for bug fixes. First write or update a
  failing test that reproduces the bug, then implement the fix, then rerun the
  relevant test and any broader impacted suite.
- New processing nodes must include unit tests for the node implementation,
  catalog/factory exposure, and at least one DAG execution path when the node
  participates in normal pipelines.
- Security changes must include tests for no-token, invalid-token, missing
  scope, and permitted-token paths.
- Storage changes must include tenant-boundary tests and direct S3 or presigned
  URL behavior as applicable.
- Webhook changes must test signature generation and failure/edge behavior.
- Do not add tests that require real production services, real secrets, or
  direct SSH access.

## Commands

Repository-documented commands:

```bash
uv run pytest
uv run black --check .
uv run flake8 .
uv run mypy .
```

Fallback commands after installing dev dependencies into a virtualenv:

```bash
python -m pytest
python -m black --check .
python -m flake8 .
python -m mypy .
```

Targeted commands for common changes:

```bash
python -m pytest tests/test_api_v1.py
python -m pytest tests/test_dag.py tests/test_image_nodes.py
python -m pytest tests/test_celery_webhook.py
python -m pytest tests/test_security.py tests/test_storage.py
```

Current bootstrap note: local verification was blocked on 2026-07-08 because
`uv` was not installed and `pytest` was not installed in system Python.
