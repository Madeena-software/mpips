# mypy: disable-error-code=no-untyped-call

import hashlib
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest
import torch

from mpips.calibration.dotgrid.neural_model.dataset import (
    format_coord,
    load_data,
    parse_coord,
    save_coordinates,
)
from mpips.calibration.dotgrid.neural_model.model import (
    AdaptiveLoss,
    MLPCompensation,
    apply_compensation,
    collinearity_loss,
    compute_compensated_diameters,
    edge_balance_loss,
    grid_spacing_loss,
    invert_compensation_points,
    smoothness_loss,
)
from mpips.calibration.dotgrid.neural_model.phantom import (
    CENTER_MARKER_MODES,
    center_candidate_indices,
    detect_center_marker,
)
from mpips.calibration.dotgrid.paths import artifact_root, default_artifact_path


def test_calibration_imports_are_lightweight() -> None:
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
        assert "mpips.calibration.dotgrid.neural_model" not in sys.modules
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_explicit_model_import_does_not_pull_runtime_layers() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.calibration.dotgrid.neural_model.model import MLPCompensation

        forbidden = {
            "PIL",
            "boto3",
            "celery",
            "fastapi",
            "matplotlib",
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
        assert MLPCompensation.__module__ == (
            "mpips.calibration.dotgrid.neural_model.model"
        )
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_dataset_round_trip_matches_historical_contract(tmp_path: Path) -> None:
    coords_path = tmp_path / "coords.csv"
    diams_path = tmp_path / "diams.csv"
    coords_path.write_text(
        '"(0.00, 1.00)","(2.00, 3.00)"\n' '"(4.00, 5.00)","(6.00, 7.00)"\n'
    )
    diams_path.write_text("1.0,2.5\n3.0,4.5\n")

    coords, diams = load_data(coords_path, diams_path)

    assert parse_coord("(1.25, -2.5)") == [1.25, -2.5]
    assert format_coord(1.234, -2.345) == "(1.23, -2.35)"
    assert coords.dtype == torch.float32
    assert coords.shape == (2, 2, 2)
    assert diams.dtype == torch.float32
    assert diams.shape == (2, 2)
    assert coords.tolist() == [[[0.0, 1.0], [2.0, 3.0]], [[4.0, 5.0], [6.0, 7.0]]]
    assert diams.tolist() == [[1.0, 2.5], [3.0, 4.5]]

    output_path = tmp_path / "saved.csv"
    save_coordinates(coords, output_path)
    assert output_path.read_text() == (
        '"(0.00, 1.00)","(2.00, 3.00)"\n' '"(4.00, 5.00)","(6.00, 7.00)"\n'
    )
    assert hashlib.sha256(output_path.read_bytes()).hexdigest() == (
        "10cf5a42ea06ed4c7f207a588cd0b7c9d130f01839b2e34adce7b41e3b553185"
    )


def test_model_topology_and_numerical_contract() -> None:
    model = MLPCompensation(hidden_dim=4)
    parameters = list(model.parameters())
    assert [type(module).__name__ for module in model.net] == [
        "Linear",
        "ReLU",
        "Linear",
        "ReLU",
        "Linear",
        "ReLU",
        "Linear",
    ]
    assert [list(parameter.shape) for parameter in parameters] == [
        [4, 2],
        [4],
        [4, 4],
        [4],
        [4, 4],
        [4],
        [2, 4],
        [2],
    ]
    assert float(parameters[-2].sum()) == 0.0
    assert float(parameters[-1].sum()) == 0.0

    coords = torch.tensor(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]],
            [[0.0, 1.0], [1.0, 1.5], [2.0, 1.0]],
            [[0.0, 2.0], [1.0, 2.0], [2.0, 2.5]],
        ]
    )
    torch.testing.assert_close(apply_compensation(model, coords, 2.0), coords)
    torch.testing.assert_close(
        invert_compensation_points(model, coords, 2.0, iterations=3), coords
    )

    offsets = torch.tensor(
        [
            [[0.0, 0.0], [0.1, 0.0], [0.3, 0.0]],
            [[0.0, 0.1], [0.2, 0.3], [0.4, 0.2]],
            [[0.0, 0.2], [0.1, 0.4], [0.2, 0.5]],
        ]
    )
    assert float(collinearity_loss(coords)) == pytest.approx(0.0555555559694767)
    assert float(grid_spacing_loss(coords)) == pytest.approx(0.118055559694767)
    assert float(edge_balance_loss(coords)) == pytest.approx(0.0006249999860301614)
    assert float(smoothness_loss(offsets)) == pytest.approx(0.04749999940395355)
    torch.testing.assert_close(
        compute_compensated_diameters(model, coords, torch.full((3, 3), 2.0), 2.0),
        torch.full((3, 3), 2.0),
    )

    adaptive = AdaptiveLoss(3)
    assert float(adaptive(torch.tensor([1.0, 2.0, 4.0]))) == 7.0
    torch.testing.assert_close(adaptive.log_vars, torch.zeros(3))


def test_phantom_detection_and_metadata_match_historical_contract() -> None:
    assert CENTER_MARKER_MODES == ("auto", "none")
    assert center_candidate_indices((5, 7)) == [(2, 3)]
    assert center_candidate_indices((6, 8)) == [(2, 3), (2, 4), (3, 3), (3, 4)]

    mask, metadata = detect_center_marker(
        np.array([[10.0, 10.0, 10.0], [10.0, 25.0, 10.0], [10.0, 10.0, 10.0]])
    )
    np.testing.assert_array_equal(
        mask,
        np.array([[True, True, True], [True, False, True], [True, True, True]]),
    )
    assert metadata == {
        "mode": "auto",
        "min_ratio": 1.5,
        "detected_marker_count": 1,
        "marker_index_0based": [1, 1],
        "marker_index_1based": [2, 2],
        "raw_marker_diameter": 25.0,
        "median_all_diameter": 10.0,
        "median_metal_ball_diameter": 10.0,
        "metal_ball_count": 8,
        "center_candidate_indices_0based": [[1, 1]],
        "candidate_max_to_median_ratio": 2.5,
    }

    none_mask, none_metadata = detect_center_marker(np.full((3, 3), 10.0), mode="none")
    assert none_mask.all()
    assert none_metadata["detected_marker_count"] == 0
    assert none_metadata["marker_index_0based"] is None


def test_paths_preserve_environment_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = tmp_path / "camera-calibration-dotgrid"
    nested.mkdir()
    monkeypatch.setenv("MPIPS_ARTIFACT_ROOT", str(tmp_path))
    assert artifact_root() == nested.resolve()
    assert default_artifact_path("output/model.pth") == str(nested / "output/model.pth")

    nested.rmdir()
    assert artifact_root() == tmp_path.resolve()
    assert default_artifact_path("output/model.pth") == str(
        tmp_path / "output/model.pth"
    )


def test_paths_source_checkout_fallback_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "checkout"
    module_path = checkout / "mpips/calibration/dotgrid/paths.py"
    candidate = checkout / "artifacts/camera-calibration-dotgrid"
    module_path.parent.mkdir(parents=True)
    candidate.mkdir(parents=True)
    monkeypatch.delenv("MPIPS_ARTIFACT_ROOT", raising=False)
    import mpips.calibration.dotgrid.paths as paths_module

    monkeypatch.setattr(paths_module, "__file__", str(module_path))
    assert artifact_root() == candidate
    assert default_artifact_path("x") == str(candidate / "x")
