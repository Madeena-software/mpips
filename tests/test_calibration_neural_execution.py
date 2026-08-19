# mypy: disable-error-code=no-untyped-call

import csv
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from PIL import Image

from mpips.calibration.dotgrid.neural_model.evaluate import evaluate_model
from mpips.calibration.dotgrid.neural_model.model import MLPCompensation
from mpips.calibration.dotgrid.neural_model.train import train_model
from mpips.calibration.dotgrid.neural_model.validate_outputs import validate_outputs
from mpips.calibration.dotgrid.neural_model.warp_image import (
    build_inverse_maps,
    estimate_expanded_canvas,
    warp_image,
)


def _write_case(root: Path) -> tuple[Path, Path]:
    coords = [
        [(0.00, 0.00), (10.50, 0.00), (20.00, 0.50)],
        [(0.00, 10.00), (10.00, 10.50), (20.50, 10.00)],
        [(0.50, 20.00), (10.00, 20.00), (20.00, 20.50)],
    ]
    diams = [[2.0, 2.1, 1.9], [2.2, 5.0, 2.0], [1.8, 2.05, 2.15]]
    coords_path = root / "coords.csv"
    diams_path = root / "diams.csv"
    with coords_path.open("w", newline="") as handle:
        csv.writer(handle).writerows(
            [[f"({x:.2f}, {y:.2f})" for x, y in row] for row in coords]
        )
    with diams_path.open("w", newline="") as handle:
        csv.writer(handle).writerows(diams)
    return coords_path, diams_path


def _sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _state_sha256(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str(tensor.dtype).encode())
        digest.update(repr(tuple(tensor.shape)).encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def test_canonical_and_legacy_execution_symbols_are_identical() -> None:
    canonical_names = {
        "train": ("train_model",),
        "evaluate": (
            "load_model",
            "compute_smia",
            "compute_reprojection_error",
            "estimate_brown_conrady",
            "compute_all_metrics",
            "improvement_pct",
            "format_center_marker_note",
            "write_basic_metrics",
            "write_advanced_metrics",
            "plot_compensated_x",
            "plot_compensated_y",
            "plot_diameter_hist",
            "plot_vertical_diameter_profile",
            "evaluate_model",
        ),
        "warp_image": (
            "INTERPOLATION",
            "BORDER_MODE",
            "CANVAS_MODE",
            "load_model",
            "resolve_device",
            "compute_valid_mask",
            "ensure_parent_dir",
            "largest_valid_rectangle",
            "build_inverse_maps",
            "estimate_expanded_canvas",
            "warp_image",
        ),
        "validate_outputs": (
            "REQUIRED_OUTPUTS",
            "load_coordinate_csv",
            "require",
            "check_file_outputs",
            "check_calibrated_image",
            "check_mask_image",
            "validate_outputs",
        ),
    }
    for module_name, names in canonical_names.items():
        canonical = importlib.import_module(
            f"mpips.calibration.dotgrid.neural_model.{module_name}"
        )
        legacy = importlib.import_module(
            f"mpips.engine.calibration.dotgrid.neural_model.{module_name}"
        )
        for name in names:
            assert getattr(legacy, name) is getattr(canonical, name)

    assert train_model.__module__ == ("mpips.calibration.dotgrid.neural_model.train")


def test_execution_imports_do_not_pull_runtime_layers() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.calibration.dotgrid.neural_model.evaluate
        import mpips.calibration.dotgrid.neural_model.train
        import mpips.calibration.dotgrid.neural_model.validate_outputs
        import mpips.calibration.dotgrid.neural_model.warp_image

        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.worker",
            "mpips.workflows",
        }
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


def test_legacy_execution_cli_modules_remain_runnable() -> None:
    for module_name in (
        "train",
        "evaluate",
        "warp_image",
        "validate_outputs",
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                f"mpips.engine.calibration.dotgrid.neural_model.{module_name}",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout.lower()


def test_run_pipeline_keeps_legacy_imports() -> None:
    run_pipeline = importlib.import_module(
        "mpips.engine.calibration.dotgrid.neural_model.run_pipeline"
    )
    assert run_pipeline.train_model is train_model
    assert run_pipeline.evaluate_model is evaluate_model
    assert run_pipeline.warp_image is warp_image
    assert run_pipeline.validate_outputs is validate_outputs


def test_training_and_evaluation_match_historical_contract(tmp_path: Path) -> None:
    coords_path, diams_path = _write_case(tmp_path)
    train_dir = tmp_path / "train"
    eval_dir = tmp_path / "eval"

    train_model(
        str(coords_path),
        str(diams_path),
        str(train_dir),
        epochs=3,
        lr=1e-3,
        target_loss=-1.0,
        hidden_dim=4,
        seed=7,
        device="cpu",
    )
    state = torch.load(
        train_dir / "compensation_model.pth", map_location="cpu", weights_only=True
    )
    assert _state_sha256(state) == (
        "89365cfb7528702dc8c2fe6a76a492ceed1534f9589bf7a85f53dba6bb7f5871"
    )
    assert {
        name: (list(value.shape), str(value.dtype)) for name, value in state.items()
    } == {
        "net.0.bias": ([4], "torch.float32"),
        "net.0.weight": ([4, 2], "torch.float32"),
        "net.2.bias": ([4], "torch.float32"),
        "net.2.weight": ([4, 4], "torch.float32"),
        "net.4.bias": ([4], "torch.float32"),
        "net.4.weight": ([4, 4], "torch.float32"),
        "net.6.bias": ([2], "torch.float32"),
        "net.6.weight": ([2, 4], "torch.float32"),
    }
    metadata = json.loads((train_dir / "model_metadata.json").read_text())
    assert {
        key: metadata[key]
        for key in (
            "grid_shape",
            "norm_scale",
            "hidden_dim",
            "seed",
            "epochs_requested",
            "epochs_ran",
            "learning_rate",
            "target_loss",
            "smoothness_weight",
            "edge_balance_weight",
            "device",
        )
    } == {
        "grid_shape": [3, 3, 2],
        "norm_scale": 20.5,
        "hidden_dim": 4,
        "seed": 7,
        "epochs_requested": 3,
        "epochs_ran": 3,
        "learning_rate": 0.001,
        "target_loss": -1.0,
        "smoothness_weight": 0.001,
        "edge_balance_weight": 0.3,
        "device": "cpu",
    }
    assert metadata["center_marker"] == {
        "mode": "auto",
        "min_ratio": 1.5,
        "detected_marker_count": 1,
        "marker_index_0based": [1, 1],
        "marker_index_1based": [2, 2],
        "raw_marker_diameter": 5.0,
        "median_all_diameter": 2.049999952316284,
        "median_metal_ball_diameter": 2.024999976158142,
        "metal_ball_count": 8,
        "center_candidate_indices_0based": [[1, 1]],
        "candidate_max_to_median_ratio": 2.439024446976463,
    }

    before, after = evaluate_model(
        str(train_dir / "compensation_model.pth"),
        str(coords_path),
        str(diams_path),
        str(eval_dir),
        image_size=(64, 48),
        hidden_dim=4,
    )
    assert before["col_rmse"] == pytest.approx(0.235702246427536, abs=1e-7)
    assert after["col_rmse"] == pytest.approx(0.23477870225906372, abs=1e-7)
    assert before["reproj"] == pytest.approx(0.3011571395705189, abs=1e-7)
    assert after["reproj"] == pytest.approx(0.3010649997066611, abs=1e-7)
    assert (eval_dir / "compensated_coordinates.csv").read_bytes()
    assert (
        hashlib.sha256(
            (eval_dir / "compensated_coordinates.csv").read_bytes()
        ).hexdigest()
        == "4c21c23901826d23d87d56c44e3aa8a040243d03d1b462ca644d0692b648ebc1"
    )
    assert hashlib.sha256((eval_dir / "metrics.txt").read_bytes()).hexdigest() == (
        "87b92610d6a340c648381327dfa7a432dbf4c40f64bf73ca55fe91d79c733135"
    )
    assert (
        hashlib.sha256((eval_dir / "advanced_metrics.txt").read_bytes()).hexdigest()
        == "e238f282817d953b0e60a6f5fdeffd971bd5645b6a7f93ea4ef22f8b9fdd31d8"
    )
    for filename in (
        "compensated_x_plot.png",
        "compensated_y_plot.png",
        "compensated_diameters_plot.png",
        "compensated_vertical_diameter_plot.png",
    ):
        with Image.open(eval_dir / filename) as image:
            assert image.size == (1000, 600)


def test_inverse_maps_and_file_warp_match_historical_contract(tmp_path: Path) -> None:
    zero = MLPCompensation(hidden_dim=4)
    constant = MLPCompensation(hidden_dim=4)
    with torch.no_grad():
        constant.net[-1].bias.copy_(torch.tensor([0.25, -0.5]))

    zero_x, zero_y, zero_stats = build_inverse_maps(
        zero, 5, 4, 2.0, step=1, iterations=1, batch_size=100, device="cpu"
    )
    assert zero_x.dtype == np.float32
    assert zero_x.shape == (4, 5)
    assert _sha256_array(zero_x) == (
        "e97b8b45d13d499f8883c554b4e038c818fb90d9107057e1494fd0ebb0be0543"
    )
    assert _sha256_array(zero_y) == (
        "f2ae8cc7e87953c0ea3359f79b1ee5fd48db4620dcb43fa3437d54cae379c0f6"
    )
    assert zero_stats["out_of_bounds_fraction"] == 0.0
    constant_x, constant_y, constant_stats = build_inverse_maps(
        constant, 5, 4, 2.0, step=2, iterations=1, batch_size=100, device="cpu"
    )
    assert _sha256_array(constant_x) == (
        "1d62db61960ae6fcfaaaf1527bdbc324eb5ed2f27cda20405a11fdfb81ee8eeb"
    )
    assert _sha256_array(constant_y) == (
        "044120be2e170051188c6185a65ce4b27a35941c21c0b4854ac9a802698b5264"
    )
    assert constant_stats["out_of_bounds_fraction"] == pytest.approx(0.2)
    assert estimate_expanded_canvas(
        constant, 5, 4, 2.0, sample_step=2, margin=1, batch_size=100, device="cpu"
    ) == {
        "origin_xy": [-1, -2],
        "output_size": {"width": 8, "height": 6},
        "estimated_corrected_bounds_xyxy": [0.5, -1.0, 4.5, 2.0],
        "sample_step": 2,
        "margin_px": 1,
        "sample_count": 9,
    }

    image = np.arange(20, dtype=np.uint16).reshape(4, 5) * 1000
    image_path = tmp_path / "image.tiff"
    model_path = tmp_path / "model.pth"
    output_path = tmp_path / "fixed.tiff"
    mask_path = tmp_path / "fixed-mask.png"
    coords_path, diams_path = _write_case(tmp_path)
    cv2.imwrite(str(image_path), image)
    torch.save(zero.state_dict(), model_path)
    stats = warp_image(
        str(image_path),
        str(model_path),
        str(coords_path),
        str(diams_path),
        str(output_path),
        step=1,
        iterations=1,
        batch_size=100,
        hidden_dim=4,
        device="cpu",
        mask_path=str(mask_path),
    )
    warped = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    assert warped is not None
    assert mask is not None
    assert warped.dtype == np.uint16
    assert warped.shape == (4, 5)
    assert _sha256_array(warped) == (
        "db164731037eb8130b50be20a322b34c9d207b5a0ca238341bcf5b2a893206db"
    )
    assert mask.dtype == np.uint8
    assert _sha256_array(mask) == (
        "9a8dcd3f9ff7aa3114e141f03c12989d363ea81fd74c02eea63c5f41489cb17a"
    )
    assert stats["out_of_bounds_fraction"] == 0.0


def test_validation_preserves_success_and_failure_contract(tmp_path: Path) -> None:
    coords_path, diams_path = _write_case(tmp_path)
    train_dir = tmp_path / "train"
    eval_dir = tmp_path / "eval"
    train_model(
        str(coords_path),
        str(diams_path),
        str(train_dir),
        epochs=3,
        lr=1e-3,
        target_loss=-1.0,
        hidden_dim=4,
        seed=7,
        device="cpu",
    )
    evaluate_model(
        str(train_dir / "compensation_model.pth"),
        str(coords_path),
        str(diams_path),
        str(eval_dir),
        image_size=(64, 48),
        hidden_dim=4,
    )
    for filename in ("compensation_model.pth", "model_metadata.json"):
        shutil.copy2(train_dir / filename, eval_dir / filename)
    kwargs = dict(
        hidden_dim=4,
        min_straightness_reduction=-1e9,
        min_reprojection_reduction=-1e9,
        min_spacing_reduction=-1e9,
        min_diameter_reduction=-1e9,
    )
    image_path = tmp_path / "raw.tiff"
    calibrated_path = tmp_path / "calibrated.tiff"
    mask_path = tmp_path / "mask.png"
    Image.fromarray(np.zeros((48, 64), dtype=np.uint16)).save(image_path)
    Image.fromarray(np.zeros((48, 64), dtype=np.uint16)).save(calibrated_path)
    Image.fromarray(np.full((48, 64), 255, dtype=np.uint8)).save(mask_path)
    assert validate_outputs(
        str(coords_path),
        str(diams_path),
        str(train_dir / "compensation_model.pth"),
        str(eval_dir),
        image_path=str(image_path),
        calibrated_path=str(calibrated_path),
        mask_path=str(mask_path),
        **kwargs,
    )

    wrong_raw_path = tmp_path / "wrong-raw.tiff"
    Image.fromarray(np.zeros((47, 64), dtype=np.uint16)).save(wrong_raw_path)
    assert not validate_outputs(
        str(coords_path),
        str(diams_path),
        str(train_dir / "compensation_model.pth"),
        str(eval_dir),
        image_path=str(wrong_raw_path),
        calibrated_path=str(calibrated_path),
        mask_path=str(mask_path),
        **kwargs,
    )

    stale_dir = tmp_path / "stale"
    shutil.copytree(eval_dir, stale_dir)
    with (stale_dir / "compensated_coordinates.csv").open("w", newline="") as handle:
        csv.writer(handle).writerows([["(0.00, 0.00)"] * 3] * 3)
    assert not validate_outputs(
        str(coords_path),
        str(diams_path),
        str(train_dir / "compensation_model.pth"),
        str(stale_dir),
        **kwargs,
    )

    missing_dir = tmp_path / "missing"
    shutil.copytree(eval_dir, missing_dir)
    (missing_dir / "compensation_model.pth").unlink()
    assert not validate_outputs(
        str(coords_path),
        str(diams_path),
        str(train_dir / "compensation_model.pth"),
        str(missing_dir),
        **kwargs,
    )
