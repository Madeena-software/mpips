from __future__ import annotations

import io
import json
from pathlib import Path
import numpy as np
import pytest

from scripts.local_dicom_burn_in import (
    CAMERA,
    SHAPE,
    BurnIn,
    _manifest_template,
    _npz_bytes,
    prepare,
    resolve_fixture_calibration_dir,
)


def _create_cal_artifact(
    directory: Path,
    *,
    detector_mode: str = "TRX",
    shape: tuple[int, int] = (128, 128),
    remap_shape: tuple[int, int] = (120, 120),
    camera_sn: str = "SN-TRX-1234",
    validated: bool = True,
    fingerprint: str = "fp-trx-v1",
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    meta = {
        "validated": validated,
        "fingerprint": fingerprint,
        "image_shape": list(shape),
        "source_metadata": {
            "detector_mode": detector_mode,
            "camera_params": {"serialNumber": camera_sn},
        },
    }
    (directory / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    y_map, x_map = np.indices(remap_shape, dtype=np.float32)
    np.savez_compressed(directory / "remap.npz", map_x=x_map, map_y=y_map)
    return directory


def test_resolve_calibration_missing_root_returns_defaults(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist"
    in_shape, cam, out_shape = resolve_fixture_calibration_dir(non_existent, detector_mode="TRX")
    assert in_shape == SHAPE
    assert cam == CAMERA
    assert out_shape == SHAPE


def test_resolve_calibration_none_returns_defaults() -> None:
    in_shape, cam, out_shape = resolve_fixture_calibration_dir(None, detector_mode="TRX")
    assert in_shape == SHAPE
    assert cam == CAMERA
    assert out_shape == SHAPE


def test_resolve_calibration_multi_mode_selects_trx(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(
        cal_root / "BED",
        detector_mode="BED",
        shape=(64, 64),
        remap_shape=(60, 60),
        camera_sn="CAMERA-BED",
    )
    _create_cal_artifact(
        cal_root / "TRX",
        detector_mode="TRX",
        shape=(256, 256),
        remap_shape=(240, 240),
        camera_sn="CAMERA-TRX",
    )

    in_shape, cam, out_shape = resolve_fixture_calibration_dir(cal_root, detector_mode="TRX")
    assert in_shape == (256, 256)
    assert cam == "CAMERA-TRX"
    assert out_shape == (240, 240)


def test_resolve_calibration_multi_mode_selects_bed(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(
        cal_root / "BED",
        detector_mode="BED",
        shape=(64, 64),
        remap_shape=(60, 60),
        camera_sn="CAMERA-BED",
    )
    _create_cal_artifact(
        cal_root / "TRX",
        detector_mode="TRX",
        shape=(256, 256),
        remap_shape=(240, 240),
        camera_sn="CAMERA-TRX",
    )

    in_shape, cam, out_shape = resolve_fixture_calibration_dir(cal_root, detector_mode="BED")
    assert in_shape == (64, 64)
    assert cam == "CAMERA-BED"
    assert out_shape == (60, 60)


def test_resolve_calibration_legacy_layout(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(
        cal_root,
        detector_mode="TRX",
        shape=(100, 100),
        remap_shape=(90, 90),
        camera_sn="LEGACY-TRX",
    )

    in_shape, cam, out_shape = resolve_fixture_calibration_dir(cal_root, detector_mode="TRX")
    assert in_shape == (100, 100)
    assert cam == "LEGACY-TRX"
    assert out_shape == (90, 90)


def test_resolve_calibration_fails_closed_when_mode_missing(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(
        cal_root / "BED",
        detector_mode="BED",
        shape=(64, 64),
        remap_shape=(60, 60),
    )

    with pytest.raises(RuntimeError, match="Multi-mode calibration root contains no matching artifact for detector mode TRX"):
        resolve_fixture_calibration_dir(cal_root, detector_mode="TRX")


def test_resolve_calibration_fails_closed_when_unvalidated(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(
        cal_root / "TRX",
        detector_mode="TRX",
        validated=False,
    )

    with pytest.raises(RuntimeError, match="is not validated"):
        resolve_fixture_calibration_dir(cal_root, detector_mode="TRX")


def test_resolve_calibration_fails_closed_when_missing_remap(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(cal_root / "TRX", detector_mode="TRX")
    (cal_root / "TRX" / "remap.npz").unlink()

    with pytest.raises(RuntimeError, match="missing remap.npz"):
        resolve_fixture_calibration_dir(cal_root, detector_mode="TRX")


def test_npz_bytes_sets_detector_mode_and_shape() -> None:
    trx_rad = _npz_bytes(radiograph=True, shape=(128, 128), camera="CAM-1", detector_mode="TRX")
    with np.load(io.BytesIO(trx_rad), allow_pickle=True) as data:
        assert data["rawimage"].shape == (128, 128)
        assert data["xrayparams"].item()["detectorMode"] == "TRX"
        assert data["cameraparams"].item()["serialNumber"] == "CAM-1"

    trx_gain = _npz_bytes(radiograph=False, shape=(128, 128), camera="CAM-1", detector_mode="TRX")
    with np.load(io.BytesIO(trx_gain), allow_pickle=True) as data:
        assert data["rawimage"].shape == (128, 128)
        assert data["darkimage"].shape == (128, 128)
        assert data["xrayparams"].item()["detectorMode"] == "TRX"


def test_manifest_template_defaults_to_trx() -> None:
    manifest = _manifest_template()
    assert manifest["capture"]["detector_type"] == "TRX"
    assert manifest["capture"]["body_part_examined"] == "CHEST"
    assert manifest["capture"]["projection"] == "PA"

    manifest_bed = _manifest_template(detector_type="BED")
    assert manifest_bed["capture"]["detector_type"] == "BED"


def test_prepare_and_burn_in_init_trx(tmp_path: Path) -> None:
    cal_root = tmp_path / "calibration"
    _create_cal_artifact(
        cal_root / "TRX",
        detector_mode="TRX",
        shape=(150, 150),
        remap_shape=(140, 140),
        camera_sn="SN-TRX-CAM",
    )

    burn_dir = tmp_path / "burn-in"
    prepare(burn_dir, detector_mode="TRX")

    # Fixtures check
    rad_path = burn_dir / "fixtures" / "radiograph.npz"
    gain_path = burn_dir / "fixtures" / "gain.npz"
    manifest_path = burn_dir / "fixtures" / "manifest.json"

    assert rad_path.is_file()
    assert gain_path.is_file()
    assert manifest_path.is_file()

    with np.load(rad_path, allow_pickle=True) as data:
        assert data["rawimage"].shape == (150, 150)
        assert data["xrayparams"].item()["detectorMode"] == "TRX"
        assert data["cameraparams"].item()["serialNumber"] == "SN-TRX-CAM"

    manifest_data = json.loads(manifest_path.read_text("utf-8"))
    assert manifest_data["capture"]["detector_type"] == "TRX"
    assert manifest_data["capture"]["body_part_examined"] == "CHEST"
    assert manifest_data["capture"]["projection"] == "PA"

    burn_in = BurnIn(burn_dir, "http://127.0.0.1:8014", detector_mode="TRX")
    assert burn_in.detector_mode == "TRX"
    assert burn_in.target_shape == (140, 140)
    burn_in.close()
