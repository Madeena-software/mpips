# mypy: disable-error-code=no-untyped-call

import csv
import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch

from mpips.calibration.dotgrid.neural_model.model import MLPCompensation
from mpips.calibration.dotgrid.opencv_baseline.calibrate_and_compare import (
    METRIC_SPECS,
    calibrate_opencv,
    comparison_rows,
    compute_undistorted_diameters,
    dist_coeff_dict,
    image_size_from_file,
    make_object_points,
    metric_reduction,
    run_opencv_comparison,
    undistort_points,
)

# Values and artifact hashes below were derived by running this fixture against
# historical SHA 0d06c4762e14b6bde595f0da631d1158a1af8344 in a detached worktree.
COORDINATES = np.asarray(
    [
        [[20.0, 30.0], [60.0, 30.0], [100.0, 30.0]],
        [[20.0, 90.0], [60.0, 90.0], [100.0, 90.0]],
        [[20.0, 150.0], [60.0, 150.0], [100.0, 150.0]],
    ],
    dtype=np.float32,
)
DIAMETERS = np.asarray(
    [[14.0, 14.0, 14.0], [14.0, 30.0, 14.0], [14.0, 14.0, 14.0]],
    dtype=np.float32,
)
IMAGE_SIZE = (150, 220)


def _write_case(root: Path) -> tuple[Path, Path, Path]:
    coords_path = root / "coords.csv"
    diams_path = root / "diams.csv"
    image_path = root / "image.tiff"
    with coords_path.open("w", newline="") as handle:
        csv.writer(handle).writerows(
            [[f"({x:.2f}, {y:.2f})" for x, y in row] for row in COORDINATES]
        )
    with diams_path.open("w", newline="") as handle:
        csv.writer(handle).writerows(DIAMETERS.tolist())
    image = np.arange(IMAGE_SIZE[0] * IMAGE_SIZE[1], dtype=np.uint16).reshape(
        IMAGE_SIZE[1], IMAGE_SIZE[0]
    )
    assert cv2.imwrite(str(image_path), image)
    return coords_path, diams_path, image_path


def _write_zero_model(path: Path) -> None:
    model = MLPCompensation(hidden_dim=4)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    torch.save(model.state_dict(), path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_basic_calibration_import_is_lightweight() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.calibration
        import mpips.calibration.dotgrid

        forbidden = {
            "PIL",
            "boto3",
            "celery",
            "fastapi",
            "matplotlib",
            "mpips.api",
            "mpips.calibration.dotgrid.opencv_baseline",
            "mpips.conversion",
            "mpips.engine",
            "mpips.worker",
            "mpips.workflows",
            "torch",
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


def test_explicit_opencv_import_does_not_load_runtime_layers() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.calibration.dotgrid.opencv_baseline.calibrate_and_compare import (
            run_opencv_comparison,
        )

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
        assert run_opencv_comparison.__module__ == (
            "mpips.calibration.dotgrid.opencv_baseline.calibrate_and_compare"
        )
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_canonical_module_cli_remains_usable() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mpips.calibration.dotgrid.opencv_baseline.calibrate_and_compare",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


def test_make_object_points_matches_historical_contract() -> None:
    points = make_object_points(3, 3, 30.0)
    expected = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [30.0, 0.0, 0.0],
            [60.0, 0.0, 0.0],
            [0.0, 30.0, 0.0],
            [30.0, 30.0, 0.0],
            [60.0, 30.0, 0.0],
            [0.0, 60.0, 0.0],
            [30.0, 60.0, 0.0],
            [60.0, 60.0, 0.0],
        ],
        dtype=np.float32,
    )
    assert points.shape == (9, 3)
    assert points.dtype == np.float32
    np.testing.assert_array_equal(points, expected)


def test_calibrate_opencv_matches_historical_numeric_contract() -> None:
    calibration = calibrate_opencv(COORDINATES, IMAGE_SIZE, object_spacing=30.0)

    assert calibration["camera_matrix"].shape == (3, 3)
    assert calibration["camera_matrix"].dtype == np.float64
    assert calibration["dist_coeffs"].shape == (1, 5)
    assert calibration["dist_coeffs"].dtype == np.float64
    assert calibration["flags"] == 5
    assert calibration["flag_names"] == [
        "CALIB_USE_INTRINSIC_GUESS",
        "CALIB_FIX_PRINCIPAL_POINT",
    ]
    assert calibration["object_spacing"] == 30.0
    assert calibration["rms"] == pytest.approx(3.3495305785253868e-15, abs=1e-10)
    np.testing.assert_allclose(
        calibration["camera_matrix"],
        np.asarray(
            [
                [131.9611526312743, 0.0, 75.0],
                [0.0, 197.94172894691147, 110.0],
                [0, 0, 1],
            ]
        ),
        rtol=1e-7,
        atol=1e-10,
    )
    np.testing.assert_allclose(
        calibration["dist_coeffs"],
        [
            [
                -3.192158732517721e-15,
                2.4818255172669312e-14,
                4.791814059849113e-17,
                -8.101702383925107e-17,
                -4.5401372588435476e-14,
            ]
        ],
        rtol=1e-7,
        atol=1e-25,
    )
    assert calibration["projected_points"].shape == (3, 3, 2)
    assert calibration["projected_points"].dtype == np.float32
    np.testing.assert_allclose(
        calibration["projected_points"], COORDINATES, rtol=0, atol=1e-5
    )


def test_undistortion_and_image_size_match_historical_contract(tmp_path: Path) -> None:
    image_path = tmp_path / "image.tiff"
    image = np.zeros((IMAGE_SIZE[1], IMAGE_SIZE[0]), dtype=np.uint16)
    assert cv2.imwrite(str(image_path), image)
    assert image_size_from_file(image_path, (1, 2)) == IMAGE_SIZE
    assert image_size_from_file(None, (1, 2)) == (1, 2)

    calibration = calibrate_opencv(COORDINATES, IMAGE_SIZE, object_spacing=30.0)
    points = undistort_points(
        COORDINATES,
        calibration["camera_matrix"],
        calibration["dist_coeffs"],
        calibration["camera_matrix"],
    )
    diameters = compute_undistorted_diameters(
        COORDINATES,
        DIAMETERS,
        calibration["camera_matrix"],
        calibration["dist_coeffs"],
        calibration["camera_matrix"],
    )
    assert points.shape == COORDINATES.shape
    assert points.dtype == np.float32
    assert diameters.shape == DIAMETERS.shape
    assert diameters.dtype == np.float32
    np.testing.assert_allclose(points, COORDINATES, rtol=0, atol=1e-5)
    np.testing.assert_allclose(diameters, DIAMETERS, rtol=0, atol=1e-5)


def test_metric_and_serialization_helpers_match_historical_contract() -> None:
    assert metric_reduction(10.0, 7.5) == 25.0
    assert metric_reduction(-10.0, -5.0, compare_abs=True) == 50.0
    assert np.isnan(metric_reduction(0.0, 1.0))
    assert np.isnan(metric_reduction(np.nan, 1.0))
    assert np.isnan(metric_reduction(1.0, np.inf))

    assert dist_coeff_dict(np.arange(1.0, 10.0).reshape(1, 9)) == {
        "k1": 1.0,
        "k2": 2.0,
        "p1": 3.0,
        "p2": 4.0,
        "k3": 5.0,
        "k4": 6.0,
        "k5": 7.0,
        "k6": 8.0,
        "c9": 9.0,
    }

    raw = {
        "reproj": 10.0,
        "col_rmse": 2.0,
        "smia_v": -4.0,
        "smia_h": 3.0,
        "spacing_x_std": 1.0,
        "spacing_y_std": 0.5,
        "diam_std": 2.0,
    }
    corrected = {
        "reproj": 7.0,
        "col_rmse": 1.0,
        "smia_v": -2.0,
        "smia_h": 1.5,
        "spacing_x_std": 0.5,
        "spacing_y_std": 0.25,
        "diam_std": 1.0,
    }
    rows = comparison_rows(raw, corrected, None)
    assert [row["metric"] for row in rows] == [name for name, *_ in METRIC_SPECS]
    assert list(rows[0]) == [
        "metric",
        "label",
        "unit",
        "raw",
        "opencv",
        "neural",
        "opencv_reduction_pct",
        "neural_reduction_pct",
    ]
    assert rows[0]["opencv_reduction_pct"] == 30.0
    assert rows[2]["opencv_reduction_pct"] == 50.0
    assert rows[2]["neural"] is None
    assert np.isnan(rows[2]["neural_reduction_pct"])


def _assert_integration_artifacts(
    output_dir: Path, comparison_hash: str, report_hash: str
) -> None:
    expected_hashes = {
        "undistorted_coordinates.csv": (
            "642f92315b38e621d757a4e09dcdf8ddec4ae0b5c8ecd810b40d709475a0fdcf"
        ),
        "opencv_projected_coordinates.csv": (
            "642f92315b38e621d757a4e09dcdf8ddec4ae0b5c8ecd810b40d709475a0fdcf"
        ),
        "comparison_metrics.csv": comparison_hash,
        "opencv_parameters.json": (
            "47aa39ef7085c93b8ca3976c6a128252d009899d3528dab825974d76c324e028"
        ),
        "comparison_report.md": report_hash,
    }
    expected_files = set(expected_hashes) | {
        "undistorted_image.tiff",
        "undistorted_valid_mask.png",
        "comparison_bar_metrics.png",
    }
    assert {path.name for path in output_dir.iterdir()} == expected_files
    for name, expected in expected_hashes.items():
        assert _sha256(output_dir / name) == expected

    tiff = cv2.imread(str(output_dir / "undistorted_image.tiff"), cv2.IMREAD_UNCHANGED)
    assert tiff is not None
    assert tiff.shape == (220, 150)
    assert tiff.dtype == np.uint16
    assert hashlib.sha256(np.ascontiguousarray(tiff).tobytes()).hexdigest() == (
        "cb879fc1a69dd08970ebfb82d8277b476bdf49cafca470903e523d2bac95d19c"
    )
    assert [int(tiff[0, 0]), int(tiff[0, 1]), int(tiff[10, 10]), int(tiff[-1, -1])] == [
        0,
        1,
        1510,
        32999,
    ]

    mask = cv2.imread(
        str(output_dir / "undistorted_valid_mask.png"), cv2.IMREAD_UNCHANGED
    )
    assert mask is not None
    assert mask.shape == (220, 150)
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)) <= {0, 255}
    assert np.count_nonzero(mask == 0) == 138
    assert hashlib.sha256(np.ascontiguousarray(mask).tobytes()).hexdigest() == (
        "6eb7f329f9012adf6fb0c39907ce227f9f8439fbdbf49128b094a765cf0556e3"
    )

    bar = cv2.imread(
        str(output_dir / "comparison_bar_metrics.png"), cv2.IMREAD_UNCHANGED
    )
    assert bar is not None
    assert bar.shape[:2] == (600, 1100)
    assert bar.size > 0

    parameters = json.loads((output_dir / "opencv_parameters.json").read_text())
    assert parameters["image_size"] == {"width": 150, "height": 220}
    assert parameters["grid_shape"] == {"rows": 3, "cols": 3}
    assert parameters["flags"] == [
        "CALIB_USE_INTRINSIC_GUESS",
        "CALIB_FIX_PRINCIPAL_POINT",
    ]
    assert parameters["invalid_pixel_fraction"] == pytest.approx(0.0041818181818181754)


def test_run_opencv_comparison_preserves_neural_present_and_missing_contract(
    tmp_path: Path,
) -> None:
    coords_path, diams_path, image_path = _write_case(tmp_path)
    missing_dir = tmp_path / "missing"
    missing = run_opencv_comparison(
        coords_path=coords_path,
        diams_path=diams_path,
        image_path=image_path,
        neural_model_path=tmp_path / "missing-model.pth",
        output_dir=missing_dir,
        image_size=IMAGE_SIZE,
        object_spacing=30.0,
        hidden_dim=4,
        write_image=True,
    )
    assert set(missing) == {"raw", "opencv", "neural", "calibration", "rows"}
    assert missing["neural"] is None
    assert (
        "Neural metrics were not computed"
        in (missing_dir / "comparison_report.md").read_text()
    )
    _assert_integration_artifacts(
        missing_dir,
        "ef6cb7807f6bf8c28b71044a6d35d9dcd2bbd2a00c89a2daa4c837b372728394",
        "8f41384d464839397943bdabd638d50219740e8137e10d2eff767d5af1974a26",
    )

    model_path = tmp_path / "model.pth"
    _write_zero_model(model_path)
    present_dir = tmp_path / "present"
    present = run_opencv_comparison(
        coords_path=coords_path,
        diams_path=diams_path,
        image_path=image_path,
        neural_model_path=model_path,
        output_dir=present_dir,
        image_size=IMAGE_SIZE,
        object_spacing=30.0,
        hidden_dim=4,
        write_image=True,
    )
    assert present["neural"] is not None
    assert (
        "Neural metrics were not computed"
        not in (present_dir / "comparison_report.md").read_text()
    )
    assert present["raw"] == present["opencv"] == present["neural"]
    _assert_integration_artifacts(
        present_dir,
        "8d81d739c1382c424023816a4e608e4794a82868b2a3c9a7e4606c09cc31d3bf",
        "f263f3a3a92b3c02f73ba6bb4f6111783e6b743e7ef947c264542d888f354486",
    )
