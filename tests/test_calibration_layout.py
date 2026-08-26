import json
from pathlib import Path

import numpy as np
import pytest

from scripts.validate_calibration_layout import validate_calibration_layout
from mpips.workflows.imager_pipeline.calibration import (
    CalibrationValidationError,
    remap_geometry_evidence,
    validate_fixed_canvas_remap,
)


def _write_artifact(
    root: Path,
    mode: str | None = "BED",
    *,
    validated: bool = True,
    fingerprint: str = "fingerprint",
    remap: str = "valid",
    detector_mode: str | None = None,
    image_shape: object = None,
    canvas_mode: str | None = None,
    remap_shape: tuple[int, int] = (2, 3),
) -> Path:
    directory = root if mode is None else root / mode
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {
        "validated": validated,
        "fingerprint": fingerprint,
        "image_shape": [2, 3] if image_shape is None else image_shape,
        "source_metadata": {
            "detector_mode": detector_mode or mode or "BED",
            "camera_params": {"cameraSerial": "camera"},
        },
    }
    if canvas_mode is not None:
        metadata["config"] = {"canvas_mode": canvas_mode}
    (directory / "metadata.json").write_text(json.dumps(metadata))
    if remap == "valid":
        np.savez(
            directory / "remap.npz", map_x=np.zeros(remap_shape), map_y=np.zeros(remap_shape)
        )
    elif remap == "missing_maps":
        np.savez(directory / "remap.npz", map_x=np.zeros((2, 3)))
    elif remap == "mismatch":
        np.savez(
            directory / "remap.npz", map_x=np.zeros((2, 3)), map_y=np.zeros((2, 2))
        )
    elif remap == "malformed":
        (directory / "remap.npz").write_bytes(b"not an npz")
    return directory


def test_legacy_root_layout_passes(tmp_path: Path):
    _write_artifact(tmp_path, None)
    assert validate_calibration_layout(tmp_path) == []


def test_bed_subdirectory_only_passes(tmp_path: Path):
    _write_artifact(tmp_path)
    assert validate_calibration_layout(tmp_path) == []


def test_bed_and_trx_subdirectories_pass(tmp_path: Path):
    _write_artifact(tmp_path, "BED")
    _write_artifact(tmp_path, "TRX")
    assert validate_calibration_layout(tmp_path) == []


def test_missing_bed_fails(tmp_path: Path):
    _write_artifact(tmp_path, "TRX")
    assert validate_calibration_layout(tmp_path)


def test_mode_metadata_mismatch_fails(tmp_path: Path):
    _write_artifact(tmp_path, detector_mode="TRX")
    assert validate_calibration_layout(tmp_path)


@pytest.mark.parametrize("remap", ["missing_maps", "mismatch", "malformed"])
def test_invalid_remap_fails(tmp_path: Path, remap: str):
    _write_artifact(tmp_path, remap=remap)
    assert validate_calibration_layout(tmp_path)


def test_metadata_shape_matches_remap_shape(tmp_path: Path):
    _write_artifact(tmp_path, image_shape=[2, 3])
    assert validate_calibration_layout(tmp_path) == []


def test_metadata_shape_mismatch_fails(tmp_path: Path):
    _write_artifact(tmp_path, image_shape=[3000, 4096])
    assert validate_calibration_layout(tmp_path)


def test_expanded_canvas_accepts_output_shape_different_from_source(tmp_path: Path):
    directory = _write_artifact(
        tmp_path,
        image_shape=[3000, 4096],
        canvas_mode="expanded",
        remap_shape=(3053, 4059),
    )
    y_values, x_values = np.indices((3053, 4059), dtype=np.float32)
    np.savez(directory / "remap.npz", map_x=x_values, map_y=y_values)
    assert validate_calibration_layout(tmp_path) == []


def test_fixed_canvas_rejects_output_shape_different_from_source(tmp_path: Path):
    _write_artifact(
        tmp_path,
        image_shape=[3000, 4096],
        canvas_mode="fixed",
        remap_shape=(3053, 4059),
    )
    assert validate_calibration_layout(tmp_path)


@pytest.mark.parametrize("image_shape", [[2], [2, 3, 4], "2x3", [2, 3.0]])
def test_malformed_image_shape_fails(tmp_path: Path, image_shape):
    _write_artifact(tmp_path, image_shape=image_shape)
    assert validate_calibration_layout(tmp_path)


@pytest.mark.parametrize("image_shape", [[0, 3], [-2, 3], [2, 0], [True, 3]])
def test_non_positive_image_shape_fails(tmp_path: Path, image_shape):
    _write_artifact(tmp_path, image_shape=image_shape)
    assert validate_calibration_layout(tmp_path)


def test_missing_remap_fails(tmp_path: Path):
    directory = _write_artifact(tmp_path)
    (directory / "remap.npz").unlink()
    assert validate_calibration_layout(tmp_path)


def test_metadata_validation_and_fingerprint_are_required(tmp_path: Path):
    _write_artifact(tmp_path, validated=False)
    assert validate_calibration_layout(tmp_path)
    _write_artifact(tmp_path, fingerprint="")
    assert validate_calibration_layout(tmp_path)


def test_symlink_artifact_fails(tmp_path: Path):
    source = tmp_path / "source.npz"
    np.savez(source, map_x=np.zeros((2, 3)), map_y=np.zeros((2, 3)))
    directory = _write_artifact(tmp_path / "artifact")
    (directory / "remap.npz").unlink()
    (directory / "remap.npz").symlink_to(source)
    assert validate_calibration_layout(tmp_path / "artifact")


def test_symlink_metadata_is_not_dereferenced(tmp_path: Path):
    external = tmp_path / "external-metadata.json"
    external.write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "external",
                "image_shape": [2, 3],
                "source_metadata": {"detector_mode": "BED"},
            }
        )
    )
    directory = _write_artifact(tmp_path / "artifact")
    (directory / "metadata.json").unlink()
    (directory / "metadata.json").symlink_to(external)
    errors = validate_calibration_layout(directory)
    assert errors
    assert any("metadata.json" in error for error in errors)


def test_trx_promotion_manifest_is_immutable():
    manifest = json.loads(
        Path(
            "artifacts/promotion/"
            "trx-calibration-789adff52ed296d956f81ae8dc38247a73768d863495f91a916"
            "fc251aaf67811"
            ".json"
        ).read_text()
    )
    assert manifest == {
        "artifact_type": "mpips-calibration",
        "detector_mode": "TRX",
        "fingerprint": (
            "789adff52ed296d956f81ae8dc38247a73768d863495f91a916fc251aaf67811"
        ),
        "image_shape": [3000, 4096],
        "camera_serial": "DA5234480",
        "archive_size": 70488061,
        "archive_sha256": (
            "39ead140fded085377ca52e9e7cf152549224e0816ccc3e73ed9a3ba7b0cdc61"
        ),
        "required_files": ["metadata.json", "remap.npz"],
        "validated": True,
        "carrier": {
            "type": "google-drive",
            "file_id": "1ou8lFZlSlO7V-3mLQtzKFz6vyDVX3WQr",
        },
    }


def test_identity_remap_passes_full_frame_geometry_validation():
    height, width = 100, 120
    map_x, map_y = np.meshgrid(
        np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32)
    )
    evidence = validate_fixed_canvas_remap(map_x, map_y, width, height)
    assert evidence["REMAP_VALID_FRACTION"] == 1.0
    assert evidence["VALID_REMAP_BBOX"] == [0, 0, width - 1, height - 1]


def test_mild_edge_displacement_passes_full_frame_geometry_validation():
    height, width = 100, 120
    map_x, map_y = np.meshgrid(
        np.arange(width, dtype=np.float32) - 2,
        np.arange(height, dtype=np.float32) - 2,
    )
    evidence = validate_fixed_canvas_remap(map_x, map_y, width, height)
    assert evidence["REMAP_VALID_FRACTION"] > 0.9
    assert evidence["REMAP_OUT_OF_BOUNDS_FRACTION"] < 0.1


def test_catastrophic_remap_is_rejected_even_with_correct_mask_dimensions():
    height, width = 100, 120
    map_x, map_y = np.meshgrid(
        np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32)
    )
    map_x[28:] = -1
    map_y[28:] = -1
    evidence = remap_geometry_evidence(map_x, map_y, width, height)
    assert 0.27 < evidence["REMAP_VALID_FRACTION"] < 0.29
    with pytest.raises(CalibrationValidationError, match="coverage is unsafe"):
        validate_fixed_canvas_remap(map_x, map_y, width, height)


def test_expanded_geometry_uses_source_domain_and_output_shape():
    map_y, map_x = np.indices((12, 10), dtype=np.float32)
    evidence = remap_geometry_evidence(map_x, map_y, 8, 10, output_shape=(12, 10))
    assert evidence["REMAP_VALID_FRACTION"] > 0.5
    assert evidence["MAP_X_MAX"] == 9.0
