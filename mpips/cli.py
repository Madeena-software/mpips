"""Console entrypoints installed with the `mpips` package."""

from __future__ import annotations

import os
import sys


def _int_env(name: str, default: str) -> int:
    value = os.getenv(name, default)
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {value!r}") from exc


def run_api() -> None:
    """Run the MPIPS FastAPI service with Uvicorn."""
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = _int_env("API_PORT", os.getenv("PORT", "8000"))
    workers = _int_env("MPIPS_API_WORKERS", "1")

    uvicorn.run("mpips.asgi:app", host=host, port=port, workers=workers)


def run_worker() -> None:
    """Run the MPIPS Celery worker using the installed Celery command."""
    args = [
        "celery",
        "-A",
        "mpips.worker",
        "worker",
        f"--loglevel={os.getenv('MPIPS_WORKER_LOG_LEVEL', 'info')}",
        f"--concurrency={os.getenv('MPIPS_WORKER_CONCURRENCY', '1')}",
        (
            "--max-tasks-per-child="
            f"{os.getenv('MPIPS_WORKER_MAX_TASKS_PER_CHILD', '100')}"
        ),
    ]

    queues = os.getenv("MPIPS_WORKER_QUEUES")
    if queues:
        args.append(f"--queues={queues}")

    args.extend(sys.argv[1:])
    os.execvp("celery", args)
