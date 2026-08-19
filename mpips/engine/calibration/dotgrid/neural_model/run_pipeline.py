"""Compatibility bridge for the canonical aggregate calibration CLI."""

import sys

from mpips.calibration.dotgrid.neural_model.run_pipeline import (
    CANVAS_MODE,
    CENTER_MARKER_MODES,
    cli,
    default_artifact_path,
    evaluate_model,
    main,
    run_opencv_comparison,
    train_model,
    validate_outputs,
    warp_image,
)

__all__ = [
    "CANVAS_MODE",
    "CENTER_MARKER_MODES",
    "cli",
    "default_artifact_path",
    "evaluate_model",
    "main",
    "run_opencv_comparison",
    "train_model",
    "validate_outputs",
    "warp_image",
]


if __name__ == "__main__":
    sys.exit(cli())
