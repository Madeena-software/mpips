# mypy: disable-error-code=no-untyped-call
# mypy: disable-error-code=untyped-decorator

import argparse
import importlib
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

CANONICAL_MODULE = "mpips.calibration.dotgrid.neural_model.run_pipeline"
LEGACY_MODULE = "mpips.engine.calibration.dotgrid.neural_model.run_pipeline"


def _module(name: str) -> Any:
    return importlib.import_module(name)


def _args(**overrides: Any) -> argparse.Namespace:
    values = {
        "coords": "coords.csv",
        "diams": "diams.csv",
        "out_dir": "output",
        "model": "existing-model.pth",
        "image": "image.tiff",
        "calibrated": "calibrated.tiff",
        "epochs": 5000,
        "lr": 1e-3,
        "target_loss": 5.0,
        "hidden_dim": 64,
        "seed": 42,
        "smoothness_weight": 1e-3,
        "edge_balance_weight": 0.3,
        "center_marker_mode": "auto",
        "center_marker_min_ratio": 1.5,
        "image_width": 4096,
        "image_height": 3000,
        "object_spacing": 30.0,
        "step": 4,
        "iterations": 10,
        "batch_size": 262144,
        "device": "auto",
        "interpolation": "linear",
        "border_mode": "constant",
        "border_value": 0,
        "mask_out": "mask.png",
        "canvas_mode": "fixed",
        "expanded_bounds_step": 4,
        "expanded_margin": 16,
        "metadata_out": None,
        "crop_valid": False,
        "crop_out": "cropped.tiff",
        "csv_tolerance": 0.01,
        "skip_train": False,
        "skip_evaluate": False,
        "skip_opencv_comparison": False,
        "opencv_out_dir": "opencv",
        "opencv_fix_aspect": False,
        "opencv_skip_image": False,
        "skip_warp": False,
        "skip_validate": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _help_options(output: str) -> list[str]:
    return re.findall(r"^\s+(-{1,2}[A-Za-z0-9-]+)", output, re.MULTILINE)


def test_canonical_module_import_and_legacy_identity() -> None:
    canonical = _module(CANONICAL_MODULE)
    legacy = _module(LEGACY_MODULE)

    assert canonical.main is legacy.main
    assert canonical.cli is legacy.cli
    assert canonical.main.__module__ == CANONICAL_MODULE


def test_canonical_run_pipeline_import_does_not_load_runtime_layers() -> None:
    script = textwrap.dedent(f"""
        import sys

        import {CANONICAL_MODULE}

        forbidden = {{
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.worker",
            "mpips.workflows",
        }}
        loaded = sorted(
            name
            for name in sys.modules
            if name in forbidden
            or any(name.startswith(item + ".") for item in forbidden)
        )
        assert not loaded, loaded
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_parent_calibration_imports_remain_lightweight() -> None:
    script = textwrap.dedent(f"""
        import sys

        import mpips.calibration
        import mpips.calibration.dotgrid

        assert "{CANONICAL_MODULE}" not in sys.modules
        assert "mpips.calibration.dotgrid.neural_model" not in sys.modules
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_canonical_and_legacy_module_help_have_same_options() -> None:
    outputs: list[str] = []
    for module_name in (CANONICAL_MODULE, LEGACY_MODULE):
        result = subprocess.run(
            [sys.executable, "-m", module_name, "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(result.stdout)

    assert _help_options(outputs[0]) == _help_options(outputs[1])


def test_mpips_dotgrid_entry_point_targets_canonical_module() -> None:
    import tomllib

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    assert pyproject["project"]["scripts"]["mpips-dotgrid"] == f"{CANONICAL_MODULE}:cli"


def test_cli_defaults_and_skip_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module(CANONICAL_MODULE)
    monkeypatch.setattr(
        module, "default_artifact_path", lambda relative: f"/artifacts/{relative}"
    )
    captured: dict[str, Any] = {}

    def fake_main(args: Any) -> int:
        captured["args"] = args
        return 37

    monkeypatch.setattr(module, "main", fake_main)
    monkeypatch.setattr(sys, "argv", ["mpips-dotgrid"])

    assert module.cli() == 37
    args = captured["args"]
    assert args.coords == "/artifacts/output/grid_coordinates.csv"
    assert args.diams == "/artifacts/output/grid_diameters.csv"
    assert args.out_dir == "/artifacts/output/neural_model"
    assert args.model == "/artifacts/output/neural_model/compensation_model.pth"
    assert args.image == "/artifacts/data/lowanu-bed-kalibrasi.tiff"
    assert args.calibrated == "/artifacts/output/neural_model/calibrated_image.tiff"
    assert args.epochs == 5000
    assert args.lr == 1e-3
    assert args.target_loss == 5.0
    assert args.hidden_dim == 64
    assert args.seed == 42
    assert args.smoothness_weight == 1e-3
    assert args.edge_balance_weight == 0.3
    assert args.center_marker_mode == "auto"
    assert args.center_marker_min_ratio == 1.5
    assert args.image_width == 4096
    assert args.image_height == 3000
    assert args.object_spacing == 30.0
    assert args.step == 4
    assert args.iterations == 10
    assert args.batch_size == 262144
    assert args.device == "auto"
    assert args.interpolation == "linear"
    assert args.border_mode == "constant"
    assert args.border_value == 0
    assert args.canvas_mode == "fixed"
    assert args.expanded_bounds_step == 4
    assert args.expanded_margin == 16
    assert args.csv_tolerance == 0.01
    assert args.opencv_out_dir == "/artifacts/output/opencv_baseline"
    assert not any(
        getattr(args, name)
        for name in (
            "skip_train",
            "skip_evaluate",
            "skip_opencv_comparison",
            "skip_warp",
            "skip_validate",
            "opencv_fix_aspect",
            "opencv_skip_image",
            "crop_valid",
        )
    )


def test_cli_rejects_missing_artifact_root(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _module(CANONICAL_MODULE)
    monkeypatch.setattr(module, "default_artifact_path", lambda relative: None)
    monkeypatch.setattr(sys, "argv", ["mpips-dotgrid"])

    with pytest.raises(SystemExit) as error:
        module.cli()

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert (
        "no artifact root is available; set MPIPS_ARTIFACT_ROOT or provide "
        "--coords, --diams, --out-dir, --model, --image, --calibrated, "
        "--opencv-out-dir"
    ) in stderr


def _install_spies(
    monkeypatch: pytest.MonkeyPatch, module: Any, calls: list[str]
) -> None:
    def train(*args: Any, **kwargs: Any) -> None:
        calls.append("train")

    def evaluate(*args: Any, **kwargs: Any) -> None:
        calls.append("evaluate")

    def opencv(*args: Any, **kwargs: Any) -> None:
        calls.append("opencv")

    def warp(*args: Any, **kwargs: Any) -> None:
        calls.append("warp")

    def validate(*args: Any, **kwargs: Any) -> bool:
        calls.append("validate")
        return True

    monkeypatch.setattr(module, "train_model", train)
    monkeypatch.setattr(module, "evaluate_model", evaluate)
    monkeypatch.setattr(module, "run_opencv_comparison", opencv)
    monkeypatch.setattr(module, "warp_image", warp)
    monkeypatch.setattr(module, "validate_outputs", validate)


def test_main_runs_operations_in_order_and_uses_trained_model_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module(CANONICAL_MODULE)
    calls: list[str] = []
    trained_model = "output/compensation_model.pth"
    _install_spies(monkeypatch, module, calls)
    observed: dict[str, str] = {}

    def evaluate(model_path: str, *args: Any, **kwargs: Any) -> None:
        observed["evaluate"] = model_path
        calls.append("evaluate")

    def opencv(*args: Any, **kwargs: Any) -> None:
        observed["opencv"] = kwargs["neural_model_path"]
        calls.append("opencv")

    def warp(*args: Any, **kwargs: Any) -> None:
        observed["warp"] = args[1]
        calls.append("warp")

    def validate(*args: Any, **kwargs: Any) -> bool:
        observed["validate"] = args[2]
        calls.append("validate")
        return True

    monkeypatch.setattr(module, "evaluate_model", evaluate)
    monkeypatch.setattr(module, "run_opencv_comparison", opencv)
    monkeypatch.setattr(module, "warp_image", warp)
    monkeypatch.setattr(module, "validate_outputs", validate)

    assert module.main(_args()) == 0
    assert calls == ["train", "evaluate", "opencv", "warp", "validate"]
    assert observed == {name: trained_model for name in observed}


def test_main_skip_train_keeps_existing_model_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module(CANONICAL_MODULE)
    args = _args(skip_train=True)
    observed: list[str] = []

    def fail_train(*args: Any, **kwargs: Any) -> None:
        pytest.fail("training should be skipped")

    def evaluate(model_path: str, *args: Any, **kwargs: Any) -> None:
        observed.append(model_path)

    def opencv(*args: Any, **kwargs: Any) -> None:
        observed.append(kwargs["neural_model_path"])

    def warp(*args: Any, **kwargs: Any) -> None:
        observed.append(args[1])

    def validate(*args: Any, **kwargs: Any) -> bool:
        observed.append(args[2])
        return True

    monkeypatch.setattr(module, "train_model", fail_train)
    monkeypatch.setattr(module, "evaluate_model", evaluate)
    monkeypatch.setattr(module, "run_opencv_comparison", opencv)
    monkeypatch.setattr(module, "warp_image", warp)
    monkeypatch.setattr(module, "validate_outputs", validate)

    assert module.main(args) == 0
    assert observed == [args.model] * 4


@pytest.mark.parametrize(
    "skip_name, expected_calls",
    (
        ("skip_train", ["evaluate", "opencv", "warp", "validate"]),
        ("skip_evaluate", ["train", "opencv", "warp", "validate"]),
        ("skip_opencv_comparison", ["train", "evaluate", "warp", "validate"]),
        ("skip_warp", ["train", "evaluate", "opencv", "validate"]),
        ("skip_validate", ["train", "evaluate", "opencv", "warp"]),
    ),
)
def test_main_skip_flags_preserve_operation_order(
    monkeypatch: pytest.MonkeyPatch, skip_name: str, expected_calls: list[str]
) -> None:
    module = _module(CANONICAL_MODULE)
    calls: list[str] = []
    _install_spies(monkeypatch, module, calls)

    assert module.main(_args(**{skip_name: True})) == 0
    assert calls == expected_calls


@pytest.mark.parametrize("valid, expected_status", ((True, 0), (False, 1)))
def test_main_validation_status_is_preserved(
    monkeypatch: pytest.MonkeyPatch, valid: bool, expected_status: int
) -> None:
    module = _module(CANONICAL_MODULE)
    monkeypatch.setattr(module, "validate_outputs", lambda *args, **kwargs: valid)
    args = _args(
        skip_train=True,
        skip_evaluate=True,
        skip_opencv_comparison=True,
        skip_warp=True,
    )

    assert module.main(args) == expected_status
