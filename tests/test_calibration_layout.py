import json
from pathlib import Path

import numpy as np
import pytest

from scripts.validate_calibration_layout import validate_calibration_layout


def _write_artifact(
    root: Path,
    mode: str | None = "BED",
    *,
    validated: bool = True,
    fingerprint: str = "fingerprint",
    remap: str = "valid",
    detector_mode: str | None = None,
) -> Path:
    directory = root if mode is None else root / mode
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {
        "validated": validated,
        "fingerprint": fingerprint,
        "image_shape": [2, 3],
        "source_metadata": {
            "detector_mode": detector_mode or mode or "BED",
            "camera_params": {"cameraSerial": "camera"},
        },
    }
    (directory / "metadata.json").write_text(json.dumps(metadata))
    if remap == "valid":
        np.savez(
            directory / "remap.npz", map_x=np.zeros((2, 3)), map_y=np.zeros((2, 3))
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
