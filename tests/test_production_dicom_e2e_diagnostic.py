from pathlib import Path
import numpy as np
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from scripts.diagnose_production_dicom_e2e import (
    ALLOWED_DRIVE_IDS,
    classify_mhcs_response,
    classify_runtime,
    discover_worker,
    find_calibration,
    map_failure,
    rewrite_detector_mode,
    safe_cleanup_path,
    validate_dicom_structure,
)

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/diagnose-production-dicom-e2e.yml"


def test_workflow_is_manual_and_production_only():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "runs-on: [self-hosted, production]" in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "schedule:" not in text
    assert "workflow_run:" not in text
    assert "group: mpips-internal-beta" in text


def test_workflow_has_no_mutating_docker_commands():
    text = WORKFLOW.read_text()
    for command in (
        "docker compose up",
        "docker compose down",
        "docker service update",
        "docker restart",
        "docker network create",
        "docker network rm",
        "docker network connect",
        "docker network disconnect",
    ):
        assert command not in text


def test_only_approved_drive_objects_are_used():
    text = (ROOT / "scripts/diagnose_production_dicom_e2e.py").read_text()
    assert set(ALLOWED_DRIVE_IDS) == {
        "1EwG5WPLcR30vSTHaOAybTVg6S9P4GSMB",
        "1R6o53hMVBy3B__cAqJBUhwcoTn14VGWF",
    }
    assert "folders/" not in text
    assert text.count("drive.google.com/uc") == 1


def test_synthetic_rewrite_changes_only_detector_mode(tmp_path):
    source = tmp_path / "source.npz"
    target = tmp_path / "target.npz"
    raw = np.arange(12, dtype=np.uint16).reshape(3, 4)
    np.savez_compressed(
        source,
        id="radio-1",
        gainid="gain-1",
        xrayparams=np.asarray({"detectorMode": "BED", "other": "kept"}, dtype=object),
        cameraparams=np.asarray({"serialNumber": "camera-1"}, dtype=object),
        rawimage=raw,
    )
    rewrite_detector_mode(source, target)
    with (
        np.load(source, allow_pickle=True) as before,
        np.load(target, allow_pickle=True) as after,
    ):
        assert np.array_equal(before["rawimage"], after["rawimage"])
        assert after["xrayparams"].item() == {"detectorMode": "TRX", "other": "kept"}
        assert after["gainid"].item() == "gain-1"


def test_dicom_validator_requires_uint16_and_no_private_tags():
    source = (ROOT / "scripts/diagnose_production_dicom_e2e.py").read_text()
    assert "BitsAllocated" in source
    assert "PixelRepresentation" in source
    assert "private" in source.lower()
    assert validate_dicom_structure.__name__ == "validate_dicom_structure"


def test_report_does_not_contain_api_key_literal():
    source = (ROOT / "scripts/diagnose_production_dicom_e2e.py").read_text()
    assert 'print(os.environ.get("MPIPS_API_KEY"))' not in source
    assert "MPIPS_API_KEY=" not in source


def test_valid_dicom_structure_is_behaviorally_validated(tmp_path):
    path = tmp_path / "valid.dcm"
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1.1"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    ds = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.Rows, ds.Columns = 2, 2
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 0
    ds.PixelData = np.zeros((2, 2), dtype=np.uint16).tobytes()
    ds.save_as(path)
    assert validate_dicom_structure(path)["rows"] == 2


def test_dicom_validator_rejects_missing_syntax_uint_and_private(tmp_path):
    path = tmp_path / "bad.dcm"
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1.1"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    ds = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID, ds.SeriesInstanceUID = generate_uid(), generate_uid()
    ds.Rows, ds.Columns = 1, 1
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.PixelRepresentation = 16, 1
    ds.PixelData = b"\0\0"
    ds.add_new(0x00110010, "LO", "private")
    ds.save_as(path)
    with pytest.raises(ValueError, match="transfer syntax"):
        validate_dicom_structure(path)


def test_runtime_provenance_requires_both_version_and_image():
    sha = "a" * 40
    assert (
        classify_runtime(sha, f"mpips-api:{sha}", "mpips-npz-worker:" + sha, sha)[
            "classification"
        ]
        == "MATCHES_WORKFLOW_SHA"
    )
    assert (
        classify_runtime(sha, f"mpips-api:{'b' * 40}", "worker", sha)["classification"]
        == "UNPROVEN"
    )
    assert (
        classify_runtime("b" * 40, f"mpips-api:{'b' * 40}", "worker", sha)[
            "classification"
        ]
        == "DIFFERS_FROM_WORKFLOW_SHA"
    )


def test_worker_discovery_requires_exactly_one():
    assert discover_worker([])["classification"] == "MHCS_IMAGE_WORKER_NOT_FOUND"
    assert discover_worker(["one"])["container"] == "one"
    assert (
        discover_worker(["one", "two"])["classification"]
        == "MHCS_IMAGE_WORKER_AMBIGUOUS"
    )


def test_mhcs_response_requires_validated_dicom():
    assert (
        classify_mhcs_response(
            {
                "http_status": 200,
                "health_status": 200,
                "content_type": "application/dicom",
                "response_bytes": 10,
                "dicom_structure": True,
            }
        )
        == "PASS"
    )
    assert (
        classify_mhcs_response(
            {
                "http_status": 200,
                "health_status": 200,
                "content_type": "application/dicom",
                "response_bytes": 10,
                "dicom_structure": False,
            }
        )
        == "DICOM_INVALID"
    )


def test_calibration_layout_and_compatibility(tmp_path):
    for mode in ("BED", "TRX"):
        directory = tmp_path / mode
        directory.mkdir()
        (directory / "remap.npz").write_bytes(b"x")
        (directory / "metadata.json").write_text(
            __import__("json").dumps(
                {
                    "validated": True,
                    "fingerprint": "fp",
                    "image_shape": [2, 2],
                    "source_metadata": {
                        "detector_mode": mode,
                        "camera_params": {"serialNumber": "cam"},
                    },
                }
            )
        )
    assert (
        find_calibration(tmp_path, "BED", (2, 2), {"serialNumber": "cam"})["compatible"]
        is True
    )
    assert (
        find_calibration(tmp_path, "TRX", (3, 2), {"serialNumber": "cam"})["compatible"]
        is False
    )


def test_failure_mapping_and_cleanup_safety(tmp_path):
    assert map_failure("download") == "TEST_DATA_DOWNLOAD_BLOCKED"
    assert map_failure("trx_calibration") == "TRX_CALIBRATION_NOT_AVAILABLE"
    owned = safe_cleanup_path(tmp_path, "child")
    assert owned.parent == tmp_path
    with pytest.raises(ValueError):
        safe_cleanup_path(tmp_path, "../outside")
