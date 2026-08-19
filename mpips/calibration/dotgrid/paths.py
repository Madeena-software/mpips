"""Resolve dot-grid artifacts without coupling package code to the checkout."""

from __future__ import annotations

import os
from pathlib import Path


def artifact_root() -> Path | None:
    """Return the configured or source-checkout calibration artifact root."""
    configured = os.environ.get("MPIPS_ARTIFACT_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        nested = root / "camera-calibration-dotgrid"
        return nested if nested.is_dir() else root

    checkout_root = Path(__file__).resolve().parents[3]
    candidate = checkout_root / "artifacts" / "camera-calibration-dotgrid"
    return candidate if candidate.is_dir() else None


def default_artifact_path(relative: str) -> str | None:
    """Resolve a legacy data/output path when artifacts are available."""
    root = artifact_root()
    return str(root / relative) if root is not None else None
