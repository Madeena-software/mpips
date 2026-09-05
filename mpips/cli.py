"""Console entrypoints installed with the `mpips` package."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _int_env(name: str, default: str) -> int:
    value = os.getenv(name, default)
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {value!r}") from exc


def _load_imager_env() -> dict[str, str]:
    """Load the supported imager environment with legacy precedence."""
    env = dict(os.environ)
    candidates = (env.get("MPIPS_RADIOGRAPHY_ENV"), str(Path.cwd() / ".env"))
    env_path = next(
        (Path(path) for path in candidates if path and Path(path).exists()), None
    )
    if env_path is not None:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def run_imager() -> None:
    """Run the canonical file-oriented imager pipeline."""
    from mpips.pipelines.config import ImagerPipelineConfig
    from mpips.workflows.imager_pipeline.file_runner import process_tiff_triplet

    env = _load_imager_env()
    config = ImagerPipelineConfig.from_env(env)
    raw_path = env.get("RAW_PATH") or r"test\BED_1765259553954_rad.tiff"
    dark_path = env.get("DARK_PATH") or r"test\BED_1765259553954_dark.tiff"
    flat_path = env.get("FLAT_PATH") or r"test\BED_1765259553954_gain.tiff"
    output_dir = env.get("OUTPUT_DIR") or r"test\output"
    raw_name = os.path.splitext(os.path.basename(raw_path))[0]
    output_path = Path(output_dir) / f"{raw_name}_processed.tiff"
    imagej_available = env.get("USE_IMAGEJ", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    print(f"MPIPS imager: processing {raw_path}")
    success = process_tiff_triplet(
        raw_path,
        dark_path,
        flat_path,
        output_path,
        config=config,
        imagej_available=imagej_available,
    )
    print(f"MPIPS imager: {'succeeded' if success else 'failed'} ({output_path})")


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
