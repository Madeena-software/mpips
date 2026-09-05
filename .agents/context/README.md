<!-- antigravity-code-agent-template:managed -->
# MPIPS

MPIPS is Madeena's Python execution service and library for scientific
image-processing pipelines. It provides a secured FastAPI API, asynchronous
Celery workers, S3-compatible image IO, and reusable calibration and
radiography workflows.

## Install

Python 3.12 is required.

### Direct Git Installation (Library Distribution)

Install directly from GitHub via `pip` or `uv` using an immutable commit SHA without manual cloning:

```bash
pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
```

Or using `uv`:

```bash
uv pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
```

> [!NOTE]
> A bare installation satisfies all dependencies required for the NPZ-to-DICOM library conversion interface (`from mpips import convert_npz_to_dicom`).

### Local Development Installation

```bash
python -m pip install -e ".[dev]"
```

Use `service`, `calibration`, `imager`, or `colab` instead of `dev` when only
that dependency set is needed.


## Run

```bash
uvicorn mpips.asgi:app --host 0.0.0.0 --port 8000
celery -A mpips.worker worker --loglevel=info
```

Docker provides equivalent `api` and `worker` roles through
`docker/entrypoint.sh`. Copy configuration names from
`.env.production.example`; keep developer auth bypass disabled outside local
development and never commit secret values.

## Verify

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m black --check mpips tests
.venv/bin/python -m flake8 mpips tests
.venv/bin/python -m mypy mpips tests
```

The verification pass on 2026-07-19 completed with 83 tests passing and all
three quality checks clean.

## Context

[`project.md`](project.md) is the verified authority for architecture, commands,
operational workflows, integrations, policies, and known gaps.

This directory is the documentation center. Do not create a root `docs/`
directory or root `README.md`.
