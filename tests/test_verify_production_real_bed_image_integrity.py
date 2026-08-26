import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from mpips.api.schemas.dicom import MHCSManifest

from scripts.verify_production_real_bed_image_integrity import (
    EXPECTED_API_IMAGE,
    EXPECTED_RUNTIME_SHA,
    EXPECTED_WORKER_IMAGE,
    CalibrationSnapshot,
    RuntimeProvenanceError,
    VerificationError,
    calculate_metrics,
    classify_image_integrity,
    discover_api_container,
    evaluate_image_integrity,
    has_unexpected_private_tags,
    make_manifest,
    read_runtime_provenance,
    select_calibration,
    validate_container_identity,
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


@pytest.mark.parametrize("output", ["", "one\ntwo\n"])
def test_container_discovery_requires_exactly_one_container(output: str) -> None:
    with pytest.raises(RuntimeProvenanceError):
        discover_api_container(output)


def test_container_discovery_uses_compose_labels_without_compose_interpolation() -> (
    None
):
    assert discover_api_container("container-id\n") == "container-id"


def test_container_identity_accepts_exact_production_container() -> None:
    validate_container_identity(
        {
            "Config": {"Image": EXPECTED_API_IMAGE},
            "ConfigLabels": {
                "com.docker.compose.project": "mpips-internal-beta",
                "com.docker.compose.service": "mpips-api",
            },
        },
        "127.0.0.1:8014",
    )


def test_manifest_has_canonical_production_structure(tmp_path: Path) -> None:
    radiograph = {"gain_id": "gain-1"}
    radiograph_path = tmp_path / "radiograph.npz"
    gain_path = tmp_path / "gain.npz"
    radiograph_path.write_bytes(b"radiograph")
    gain_path.write_bytes(b"gain")

    payload = make_manifest(radiograph, radiograph_path, gain_path)
    parsed = MHCSManifest.model_validate_json(payload)

    assert parsed.capture.detector_type == "BED"
    assert set(json.loads(payload)) >= {
        "manifest_version",
        "conversion_job_id",
        "submission_id",
        "correlation_id",
        "examination",
        "patient",
        "operator",
        "site",
        "capture",
        "dicom",
    }


def test_private_tag_detection_uses_data_element_tag() -> None:
    from pydicom import Dataset
    from pydicom.dataelem import DataElement

    dataset = Dataset()
    dataset.add(DataElement(0x00110010, "LO", "private"))

    assert has_unexpected_private_tags(dataset) is True


def test_non_bed_root_calibration_is_not_selected(tmp_path: Path) -> None:
    root = tmp_path
    (root / "metadata.json").write_text(
        '{"validated":true,"fingerprint":"trx",'
        '"image_shape":[2,2],"source_metadata":{"detector_mode":"TRX"}}'
    )
    with pytest.raises(VerificationError):
        select_calibration(root, "BED")


def test_bed_child_calibration_is_selected(tmp_path: Path) -> None:
    bed = tmp_path / "BED"
    bed.mkdir()
    (bed / "metadata.json").write_text(
        '{"validated":true,"fingerprint":"bed",'
        '"image_shape":[2,2],"source_metadata":{"detector_mode":"BED"}}'
    )
    (bed / "remap.npz").write_bytes(b"placeholder")

    assert select_calibration(tmp_path, "BED") == bed


def test_image_classification_reports_zero_collapse() -> None:
    metrics = calculate_metrics(np.zeros((10, 10), dtype=np.uint16))

    assert classify_image_integrity(metrics) == "PRODUCTION_BED_IMAGE_COLLAPSE"


def test_image_classification_reports_support_collapse() -> None:
    image = np.zeros((10, 10), dtype=np.uint16)
    image[:, 1:9] = 1

    assert classify_image_integrity(calculate_metrics(image)) == (
        "PRODUCTION_BED_SUPPORT_COLLAPSE"
    )


def test_image_classification_reports_pass_only_after_all_gates() -> None:
    image = np.ones((10, 10), dtype=np.uint16)
    image[0, 0] = 2

    assert classify_image_integrity(calculate_metrics(image)) == (
        "REAL_BED_PRODUCTION_IMAGE_INTEGRITY_PASS"
    )


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
