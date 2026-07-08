# Task Prompt: Verify MPIPS Implementation Against The PRD

Use this prompt to systematically audit MPIPS source code against
`docs/PRD.md`. The goal is to identify implementation gaps, schema mismatches,
security regressions, and test coverage deficiencies.

## 1. Context And Setup

- PRD location: `docs/PRD.md`
- Project context: `.agents/rules/project-context.md`
- Stack rules: `.agents/rules/python-fastapi-celery.md`
- Testing standard: `.agents/rules/testing-pyramid.md`
- Current state: `.agents/memory/state.md`

## 2. Objective

Produce a Markdown audit report that maps PRD requirements to implemented code
and tests. Classify each requirement as fully met, partially met, or unmet, and
produce a prioritized remediation backlog.

The audit must preserve the MPIPS service boundary:

- MPIPS owns FastAPI image-processing APIs, Celery job execution, DAG
  interpretation, image-processing nodes, S3-compatible IO, Redis job state,
  IQA metadata, tenant path validation, and signed webhook callbacks.
- Calling applications own user-facing workflows, visual pipeline builders,
  user profiles, billing, direct end-user image serving, and domain business
  metadata.
- Do not require Laravel/PHP routes, migrations, Filament resources, browser
  UI flows, or member-core behavior from this repository unless the PRD is
  explicitly revised.

## 3. Step-by-Step Instructions

### Step 1: Extract Requirements From The PRD

Read `docs/PRD.md` and extract requirements from:

- Product overview, goals, and non-goals.
- Target clients and access model.
- Feature inventory.
- API specification.
- Processing node catalog.
- System flows.
- Data/state model.
- Security requirements.
- Deployment and operational requirements.
- Testing and quality requirements.

### Step 2: Audit The Codebase

Verify each requirement against:

- API routing: `app/main.py`, `app/api/v1/router.py`, `app/api/v1/health.py`.
- Schemas: `app/schemas/jobs.py`, `app/schemas/nodes.py`.
- DAG and execution: `app/core/dag.py`, `app/core/catalog.py`,
  `image_engine/`, `celery_tasks/`.
- Security and isolation: `app/core/security.py`,
  `app/core/tenant_paths.py`, `app/core/storage.py`.
- Package entrypoints: `mpips/`.
- Static dashboard: `app/dashboard/`.
- Deployment: `Dockerfile`, `docker/entrypoint.sh`,
  `.env.production.example`, `.dockerignore`.
- Tests: `tests/`.
- CI/CD: `.github/workflows/` if present.

### Step 3: Generate The Verification Matrix

Create a Markdown table:

| Category | Requirement | Implemented? | Tested? | Evidence | Gaps |
|---|---|---|---|---|---|

Evidence should use concrete file paths and, when possible, line references.

### Step 4: Identify Contract And Security Mismatches

Specifically check:

- PRD routes vs actual FastAPI routes.
- PRD request/response payloads vs Pydantic schemas.
- Required scopes vs `MADEENA_REQUIRED_SCOPES` and route dependencies.
- Developer bypass behavior and production-safety expectations.
- Tenant path validation for all direct S3 key and prefix flows.
- Webhook signature payload, timestamp, headers, and error behavior.
- Redis job-state fields vs documented status schema.
- Node catalog entries vs `image_engine.factory` and node tests.
- Docker/env examples vs variables read by code.

### Step 5: Review Test Coverage

Map requirements to tests in:

- `tests/test_api_v1.py`
- `tests/test_celery_webhook.py`
- `tests/test_dag.py`
- `tests/test_image_nodes.py`
- `tests/test_scientific_nodes.py`
- `tests/test_security.py`
- `tests/test_storage.py`
- `tests/test_package_import.py`
- `tests/test_main.py`

Record missing tests and identify whether they should be unit, integration, or
service smoke tests under the testing pyramid.

## 4. Deliverable Format

Save the audit as a Markdown artifact under an appropriate docs or artifacts
path requested by the user. Use this structure:

1. Executive Summary
   - Overall readiness percentage.
   - Highest-risk gaps.
   - Verification commands run and blocked commands.
2. Verification Matrix
   - Requirement-by-requirement table.
3. Contract And Security Gaps
   - Concrete mismatches with evidence.
4. Testing Gaps
   - Missing tests by pyramid layer.
5. Remediation Backlog
   - Prioritized, actionable code/doc/test tasks.

## 5. Verification

Run the relevant commands after installing dev dependencies:

```bash
uv run pytest
uv run black --check .
uv run flake8 .
uv run mypy .
```

If `uv` is unavailable, use the virtualenv fallback from
`.agents/rules/testing-pyramid.md`.
