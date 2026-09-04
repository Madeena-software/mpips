import sys

from mpips.calibration.dotgrid.neural_model import run_pipeline
from mpips.workflows.imager_pipeline.models import NeuralCalibrationConfig


def test_neural_calibration_defaults_to_expanded():
    assert NeuralCalibrationConfig().canvas_mode == "expanded"


def test_neural_calibration_explicit_fixed_remains_supported():
    assert NeuralCalibrationConfig(canvas_mode="fixed").canvas_mode == "fixed"


def test_calibration_cli_defaults_to_expanded(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setenv("MPIPS_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setattr(
        run_pipeline, "main", lambda args: captured.setdefault("args", args)
    )
    monkeypatch.setattr(sys, "argv", ["mpips-dotgrid", "--skip-train", "--skip-warp"])
    run_pipeline.cli()
    assert captured["args"].canvas_mode == "expanded"


def test_calibration_cli_explicit_fixed_remains_supported(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setenv("MPIPS_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setattr(
        run_pipeline, "main", lambda args: captured.setdefault("args", args)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mpips-dotgrid",
            "--canvas-mode",
            "fixed",
            "--skip-train",
            "--skip-warp",
        ],
    )
    run_pipeline.cli()
    assert captured["args"].canvas_mode == "fixed"
