# mypy: disable-error-code=no-untyped-call

import hashlib
import inspect
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import cast

import cv2
import numpy as np
import pytest

from mpips.calibration.dotgrid import extract_grid


def _write_grid(
    path: Path,
    rows: list[list[tuple[int, int, int, int]]],
    shape: tuple[int, int] = (240, 180),
) -> None:
    image = np.zeros(shape, dtype=np.uint8)
    for row in rows:
        for x, y, radius, value in row:
            cv2.circle(image, (x, y), radius, value, -1)
    assert cv2.imwrite(str(path), image)


def _rectangular_grid() -> list[list[tuple[int, int, int, int]]]:
    return [
        [(20 + column * 40, 30 + row * 60, 7, 200) for column in range(3)]
        for row in range(3)
    ]


def _extract_grid(
    image_path: Path, output_dir: Path, **kwargs: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    result = extract_grid(str(image_path), str(output_dir), **kwargs)
    assert result is not None
    return cast(tuple[np.ndarray, np.ndarray, np.ndarray], result)


def test_canonical_and_legacy_extractors_are_identical() -> None:
    import importlib

    legacy_module = importlib.import_module(
        "mpips.engine.calibration.dotgrid.extract_grid"
    )

    assert legacy_module.extract_grid is extract_grid
    assert extract_grid.__module__ == "mpips.calibration.dotgrid.extract_grid"


def test_dotgrid_import_is_engine_and_optional_dependency_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.calibration.dotgrid import extract_grid

        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "matplotlib",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.pipelines",
            "mpips.worker",
            "mpips.workflows",
            "PIL",
            "torch",
        }
        loaded = sorted(
            name
            for name in sys.modules
            if name in forbidden
            or any(name.startswith(item + ".") for item in forbidden)
        )
        assert not loaded, loaded
        assert extract_grid.__module__ == "mpips.calibration.dotgrid.extract_grid"
        """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_rectangular_grid_matches_historical_arrays_and_csvs(tmp_path: Path) -> None:
    image_path = tmp_path / "grid.png"
    _write_grid(image_path, _rectangular_grid(), shape=(220, 150))

    coordinates, diameters, circularities = _extract_grid(
        image_path, tmp_path, row_tolerance=20
    )

    expected_coordinates = np.array(
        [
            [[20.0, 30.0], [60.0, 30.0], [100.0, 30.0]],
            [[20.0, 90.0], [60.0, 90.0], [100.0, 90.0]],
            [[20.0, 150.0], [60.0, 150.0], [100.0, 150.0]],
        ],
        dtype=np.float32,
    )
    expected_diameters = np.full((3, 3), 14.000200271606445, dtype=np.float32)
    expected_circularities = np.full((3, 3), 0.8330177068710327, dtype=np.float32)

    np.testing.assert_array_equal(coordinates, expected_coordinates)
    np.testing.assert_array_equal(diameters, expected_diameters)
    np.testing.assert_array_equal(circularities, expected_circularities)
    assert coordinates.dtype == np.float32
    assert diameters.dtype == np.float32
    assert circularities.dtype == np.float32
    assert coordinates.shape == (3, 3, 2)
    assert diameters.shape == (3, 3)
    assert circularities.shape == (3, 3)

    expected_csv = {
        "grid_coordinates.csv": (
            '"(20.0, 30.0)","(60.0, 30.0)","(100.0, 30.0)"\n'
            '"(20.0, 90.0)","(60.0, 90.0)","(100.0, 90.0)"\n'
            '"(20.0, 150.0)","(60.0, 150.0)","(100.0, 150.0)"\n'
        ),
        "grid_diameters.csv": "14.0,14.0,14.0\n14.0,14.0,14.0\n14.0,14.0,14.0\n",
        "grid_circularity.csv": (
            "0.833,0.833,0.833\n0.833,0.833,0.833\n" "0.833,0.833,0.833\n"
        ),
    }
    expected_hashes = {
        "grid_coordinates.csv": (
            "9d0dbbfb0a7047d5a69eddd6d7c740b6f486b2d8d3297fc8ea034271639f71bb"
        ),
        "grid_diameters.csv": (
            "0139fa02c346880766044f79fbbfc2d332a2a8a1643a379b7e6648e271680661"
        ),
        "grid_circularity.csv": (
            "1a6c60d4e2f7e0c1d4bd7768a5990c91372ad54e813d78e263e80ba66c8b9785"
        ),
    }
    for filename, expected in expected_csv.items():
        file_path = tmp_path / filename
        content = file_path.read_text()
        assert content == expected
        assert (
            hashlib.sha256(file_path.read_bytes()).hexdigest()
            == expected_hashes[filename]
        )


def test_threshold_values_above_and_below_boundary_are_characterized(
    tmp_path: Path,
) -> None:
    rows = [
        [(30, 25, 7, 129), (70, 25, 7, 129)],
        [(30, 65, 7, 129), (70, 65, 7, 129)],
        [(30, 125, 7, 127), (70, 125, 7, 127)],
        [(30, 165, 7, 127), (70, 165, 7, 127)],
    ]
    image_path = tmp_path / "threshold.png"
    _write_grid(image_path, rows)

    above_only = _extract_grid(image_path, tmp_path, threshold=128, row_tolerance=20)
    all_values = _extract_grid(image_path, tmp_path, threshold=126, row_tolerance=20)

    assert above_only[0].shape == (2, 2, 2)
    assert all_values[0].shape == (4, 2, 2)
    np.testing.assert_array_equal(above_only[0][0], [[30.0, 25.0], [70.0, 25.0]])
    np.testing.assert_array_equal(all_values[0][-1], [[30.0, 165.0], [70.0, 165.0]])


def test_minimum_contour_area_remains_strictly_greater_than_threshold(
    tmp_path: Path,
) -> None:
    rows = [
        [(30, 20, 2, 200), (70, 20, 2, 200)],
        [(30, 40, 2, 200), (70, 40, 2, 200)],
        [(30, 100, 7, 200), (70, 100, 7, 200)],
        [(30, 140, 7, 200), (70, 140, 7, 200)],
    ]
    image_path = tmp_path / "area.png"
    _write_grid(image_path, rows)

    at_boundary = _extract_grid(
        image_path, tmp_path, minimum_contour_area=8, row_tolerance=20
    )
    above_boundary = _extract_grid(
        image_path, tmp_path, minimum_contour_area=7, row_tolerance=20
    )

    assert at_boundary[0].shape == (2, 2, 2)
    assert above_boundary[0].shape == (4, 2, 2)
    np.testing.assert_array_equal(above_boundary[0][0], [[30.0, 20.0], [70.0, 20.0]])


def test_row_tolerance_grouping_and_auto_trim_match_historical_behavior(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jittered = [
        [(30, 30, 7, 200), (70, 36, 7, 200), (110, 42, 7, 200)],
        [(30, 100, 7, 200), (70, 106, 7, 200), (110, 112, 7, 200)],
    ]
    jittered_path = tmp_path / "jittered.png"
    _write_grid(jittered_path, jittered)

    grouped = _extract_grid(jittered_path, tmp_path, row_tolerance=15)
    assert grouped[0].shape == (2, 3, 2)
    np.testing.assert_array_equal(
        grouped[0][0], [[30.0, 30.0], [70.0, 36.0], [110.0, 42.0]]
    )

    with pytest.raises(
        ValueError,
        match=r"Detected dot grid is not rectangular; row widths: 1, 1, 1, 1, 1, 1",
    ):
        extract_grid(str(jittered_path), str(tmp_path), row_tolerance=5)

    trimmed = [
        [(30, 30, 7, 200), (70, 30, 7, 200), (110, 30, 7, 200)],
        [(30, 70, 7, 200), (70, 70, 7, 200)],
        [(30, 110, 7, 200), (70, 110, 7, 200)],
    ]
    trimmed_path = tmp_path / "trimmed.png"
    _write_grid(trimmed_path, trimmed)
    result = _extract_grid(trimmed_path, tmp_path, row_tolerance=20)

    assert result[0].shape == (2, 2, 2)
    np.testing.assert_array_equal(
        result[0], [[[30.0, 70.0], [70.0, 70.0]], [[30.0, 110.0], [70.0, 110.0]]]
    )
    assert (
        "Auto-trimmed grid from 3 rows to 2 rectangular rows of width 2"
        in capsys.readouterr().out
    )


def test_invalid_grid_error_and_missing_image_behavior_are_preserved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid_path = tmp_path / "invalid.png"
    _write_grid(
        invalid_path,
        [
            [(30, 30, 7, 200), (70, 30, 7, 200), (110, 30, 7, 200)],
            [(30, 70, 7, 200), (70, 70, 7, 200)],
        ],
    )

    with pytest.raises(
        ValueError,
        match=r"Detected dot grid is not rectangular; row widths: 3, 2",
    ):
        extract_grid(str(invalid_path), str(tmp_path), row_tolerance=20)

    missing = tmp_path / "missing.png"
    assert extract_grid(str(missing), str(tmp_path)) is None
    assert f"Error: Could not load image at {missing}" in capsys.readouterr().out


def test_extract_grid_signature_and_defaults_are_preserved() -> None:
    parameters = inspect.signature(extract_grid).parameters

    assert list(parameters) == [
        "image_path",
        "output_dir",
        "threshold",
        "minimum_contour_area",
        "row_tolerance",
    ]
    assert parameters["threshold"].default == 128
    assert parameters["minimum_contour_area"].default == 10
    assert parameters["row_tolerance"].default == 50


def test_workflow_extract_dot_grid_delegates_to_canonical_extractor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib

    workflow = importlib.import_module("mpips.workflows.imager_pipeline.calibration")
    canonical_module = importlib.import_module("mpips.calibration.dotgrid.extract_grid")

    expected: tuple[np.ndarray, np.ndarray, np.ndarray] = (
        np.zeros((2, 2, 2)),
        np.zeros((2, 2)),
        np.zeros((2, 2)),
    )
    calls: list[tuple[str, str, int, float, float]] = []

    def spy(
        image_path: str,
        output_dir: str,
        threshold: int,
        minimum_contour_area: float,
        row_tolerance: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        calls.append(
            (image_path, output_dir, threshold, minimum_contour_area, row_tolerance)
        )
        return expected

    monkeypatch.setattr(canonical_module, "extract_grid", spy)

    image = np.zeros((4, 4), dtype=np.uint8)
    result = workflow.extract_dot_grid(
        image,
        workflow.NeuralCalibrationConfig(
            threshold=129, minimum_contour_area=11, row_tolerance=12
        ),
    )

    assert result is expected
    assert len(calls) == 1
    assert calls[0][2:] == (129, 11, 12)
