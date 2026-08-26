from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.verify_production_real_bed_image_integrity import (
    EXPECTED_API_IMAGE,
    EXPECTED_RUNTIME_SHA,
    EXPECTED_WORKER_IMAGE,
    CalibrationSnapshot,
    RuntimeProvenanceError,
    calculate_metrics,
    evaluate_image_integrity,
    read_runtime_provenance,
    validate_bed_inputs,
)


def write_runtime(
    root: Path, sha: str = EXPECTED_RUNTIME_SHA, worker: str = EXPECTED_WORKER_IMAGE
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".mpips-version").write_text(sha)
    (root / ".mpips-worker-image").write_text(worker)


def test_runtime_provenance_accepts_exact_markers(tmp_path: Path) -> None:
    write_runtime(tmp_path)

    result = read_runtime_provenance(tmp_path, EXPECTED_API_IMAGE, "127.0.0.1:8014")

    assert result.runtime_sha == EXPECTED_RUNTIME_SHA
    assert result.worker_image == EXPECTED_WORKER_IMAGE


@pytest.mark.parametrize(
    "marker, value",
    [
        (".mpips-version", None),
        (".mpips-version", "wrong"),
        (".mpips-worker-image", "mpips-npz-worker:wrong"),
    ],
)
def test_runtime_provenance_rejects_bad_markers(
    tmp_path: Path, marker: str, value: str | None
) -> None:
    write_runtime(tmp_path)
    path = tmp_path / marker
    if value is None:
        path.unlink()
    else:
        path.write_text(value)

    with pytest.raises(RuntimeProvenanceError):
        read_runtime_provenance(tmp_path, EXPECTED_API_IMAGE, "127.0.0.1:8014")


def test_local_api_image_is_rejected(tmp_path: Path) -> None:
    write_runtime(tmp_path)

    with pytest.raises(RuntimeProvenanceError):
        read_runtime_provenance(tmp_path, "mpips-api:local", "127.0.0.1:8014")


def test_metrics_on_uint16_array() -> None:
    metrics = calculate_metrics(np.array([[0, 2], [4, 6]], dtype=np.uint16))

    assert metrics.dtype == "uint16"
    assert metrics.shape == (2, 2)
    assert metrics.minimum == 0
    assert metrics.maximum == 6
    assert metrics.zero_ratio == 0.25
    assert metrics.nonzero_bbox == (0, 0, 1, 1)
    assert metrics.support_width_ratio == 1.0
    assert metrics.support_height_ratio == 1.0


def test_image_integrity_rejects_destructive_zero_ratio() -> None:
    metrics = calculate_metrics(np.zeros((10, 10), dtype=np.uint16))

    assert evaluate_image_integrity(metrics) is False


def test_image_integrity_accepts_broad_nonzero_support() -> None:
    image = np.ones((10, 10), dtype=np.uint16)
    image[0, 0] = 0

    assert evaluate_image_integrity(calculate_metrics(image)) is True


def test_image_integrity_rejects_narrow_support() -> None:
    image = np.zeros((10, 10), dtype=np.uint16)
    image[4:6, 4:6] = 1

    assert evaluate_image_integrity(calculate_metrics(image)) is False


def test_camera_metadata_does_not_affect_bed_compatibility() -> None:
    radiograph = {
        "detector_mode": "BED",
        "gain_id": "gain-1",
        "raw": np.zeros((3000, 4096), dtype=np.uint16),
        "camera_params": {"serialNumber": "different-camera"},
    }
    gain = SimpleNamespace(
        id="gain-1",
        detector_mode="BED",
        flat=np.zeros((3000, 4096), dtype=np.uint16),
        camera_params={"serialNumber": "another-camera"},
    )

    validate_bed_inputs(radiograph, gain)


def test_calibration_snapshot_hash_mismatch_is_detectable(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.json"
    remap = tmp_path / "remap.npz"
    metadata.write_text(
        '{"fingerprint":"test","validated":true,"image_shape":[2,2],'
        '"source_metadata":{"detector_mode":"BED"}}'
    )
    np.savez(remap, map_x=np.zeros((2, 2)), map_y=np.zeros((2, 2)))

    before = CalibrationSnapshot.from_directory(tmp_path)
    np.savez(remap, map_x=np.ones((2, 2)), map_y=np.ones((2, 2)))
    after = CalibrationSnapshot.from_directory(tmp_path)

    assert before != after
