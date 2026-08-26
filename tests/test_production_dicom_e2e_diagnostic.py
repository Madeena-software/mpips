from pathlib import Path
import numpy as np
import pydicom
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from scripts.diagnose_production_dicom_e2e import (
    ALLOWED_DRIVE_IDS,
    classify_mhcs_response,
    classify_mhcs_probe,
    camera_compatibility,
    classify_runtime,
    discover_worker,
    final_classification,
    find_calibration,
    map_failure,
    rewrite_detector_mode,
    safe_cleanup_path,
    validate_dicom_structure,
)

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/diagnose-production-dicom-e2e.yml"


def _valid_dicom(path):
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1.1"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    ds = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID, ds.SOPInstanceUID = (
        meta.MediaStorageSOPClassUID,
        meta.MediaStorageSOPInstanceUID,
    )
    ds.StudyInstanceUID, ds.SeriesInstanceUID = generate_uid(), generate_uid()
    ds.Rows, ds.Columns = 2, 2
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 0
    ds.PixelData = np.zeros((2, 2), dtype=np.uint16).tobytes()
    ds.save_as(path)


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


def test_gain_rewrite_preserves_detector_payload_and_metadata(tmp_path):
    source = tmp_path / "gain-bed.npz"
    target = tmp_path / "gain-trx.npz"
    raw = np.array([[100, 200], [300, 400]], dtype=np.uint16)
    dark = np.array([[7, 11], [13, 17]], dtype=np.uint16)
    np.savez_compressed(
        source,
        id="gain-1",
        xrayparams=np.asarray({"detectorMode": "BED", "voltage": 70}, dtype=object),
        cameraparams=np.asarray({"serialNumber": "camera-1"}, dtype=object),
        rawimage=raw,
        darkimage=dark,
    )

    rewrite_detector_mode(source, target)

    with (
        np.load(source, allow_pickle=True) as before,
        np.load(target, allow_pickle=True) as after,
    ):
        assert before["xrayparams"].item()["detectorMode"] == "BED"
        assert after["xrayparams"].item()["detectorMode"] == "TRX"
        assert after["id"].item() == "gain-1"
        assert after["cameraparams"].item() == before["cameraparams"].item()
        assert after["xrayparams"].item()["voltage"] == 70
        assert np.array_equal(after["rawimage"], raw)
        assert np.array_equal(after["darkimage"], dark)


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
    _valid_dicom(path)
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


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("syntax", "unsupported"),
        ("signed", "unsigned"),
        ("private", "private"),
        ("uid", "missing"),
    ],
)
def test_dicom_validator_rejects_each_invalid_condition(tmp_path, change, message):
    path = tmp_path / f"{change}.dcm"
    _valid_dicom(path)
    ds = pydicom.dcmread(path)
    if change == "syntax":
        ds.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2"
    elif change == "signed":
        ds.PixelRepresentation = 1
    elif change == "private":
        ds.add_new(0x00110010, "LO", "private")
    else:
        ds.StudyInstanceUID = "not-a-uid"
    ds.save_as(path, write_like_original=False)
    with pytest.raises(ValueError, match=message):
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
        np.savez(
            directory / "remap.npz", map_x=np.zeros((2, 2)), map_y=np.zeros((2, 2))
        )
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


def test_runtime_mismatch_is_not_a_functional_stop():
    assert (
        final_classification(
            {
                "runtime_provenance": "DIFFERS_FROM_WORKFLOW_SHA",
                "BED_DIRECT_CONVERSION": "PASS",
                "SYNTHETIC_THORAX_DIRECT_CONVERSION": "PASS",
            }
        )
        == "PRODUCTION_RUNTIME_NOT_WORKFLOW_SHA"
    )
    assert (
        final_classification(
            {"runtime_provenance": "UNPROVEN", "BED_DIRECT_CONVERSION": "PASS"}
        )
        == "PRODUCTION_RUNTIME_SHA_UNPROVEN"
    )


def test_final_classification_preserves_earliest_diagnostic_failure():
    assert (
        final_classification({"MHCS_IMAGE_WORKER": "MHCS_IMAGE_WORKER_NOT_FOUND"})
        == "MHCS_IMAGE_WORKER_NOT_FOUND"
    )
    assert (
        final_classification({"MHCS_PRIVATE_NETWORK": "FAIL"})
        == "MHCS_PRIVATE_NETWORK_FAILED"
    )
    assert (
        final_classification({"MHCS_MPIPS_CONFIG": "FAIL"})
        == "MHCS_MPIPS_CONFIG_FAILED"
    )
    assert final_classification({"MHCS_MPIPS_DNS": "FAIL"}) == "MHCS_MPIPS_DNS_FAILED"
    assert (
        final_classification({"MHCS_MPIPS_HEALTH": "FAIL"})
        == "MHCS_MPIPS_HEALTH_FAILED"
    )
    assert (
        final_classification({"MHCS_BED_MPIPSCLIENT": "FAIL"})
        == "MHCS_BED_MPIPSCLIENT_FAILED"
    )
    assert (
        final_classification({"MHCS_BED_DICOM_STRUCTURE": "FAIL"})
        == "MHCS_BED_DICOM_INVALID"
    )
    assert (
        final_classification({"MHCS_THORAX_MPIPSCLIENT": "FAIL"})
        == "MHCS_THORAX_MPIPSCLIENT_FAILED"
    )
    assert (
        final_classification({"MHCS_THORAX_DICOM_STRUCTURE": "FAIL"})
        == "MHCS_THORAX_DICOM_INVALID"
    )


def test_final_classification_preserves_terminal_mhcs_probe_failure():
    assert (
        final_classification(
            {
                "MHCS_BED_MPIPSCLIENT": "MHCS_BED_MPIPSCLIENT_FAILED",
                "MHCS_BED_DICOM_STRUCTURE": "FAIL",
            }
        )
        == "MHCS_BED_MPIPSCLIENT_FAILED"
    )
    assert (
        final_classification(
            {
                "MHCS_THORAX_MPIPSCLIENT": "MHCS_THORAX_MPIPSCLIENT_FAILED",
                "MHCS_THORAX_DICOM_STRUCTURE": "FAIL",
            }
        )
        == "MHCS_THORAX_MPIPSCLIENT_FAILED"
    )
    assert (
        final_classification({"MHCS_MPIPS_CONFIG": "MHCS_MPIPS_CONFIG_FAILED"})
        == "MHCS_MPIPS_CONFIG_FAILED"
    )
    assert (
        final_classification({"MHCS_MPIPS_DNS": "MHCS_MPIPS_DNS_FAILED"})
        == "MHCS_MPIPS_DNS_FAILED"
    )
    assert (
        final_classification({"MHCS_MPIPS_HEALTH": "MHCS_MPIPS_HEALTH_FAILED"})
        == "MHCS_MPIPS_HEALTH_FAILED"
    )


def test_calibration_requires_fingerprint_and_reports_unknown_camera(tmp_path):
    directory = tmp_path / "BED"
    directory.mkdir()
    np.savez(directory / "remap.npz", map_x=np.zeros((2, 2)), map_y=np.zeros((2, 2)))
    (directory / "metadata.json").write_text(
        '{"validated": true, "image_shape": [2, 2], '
        '"source_metadata": {"detector_mode": "BED"}}'
    )
    evidence = find_calibration(tmp_path, "BED", (2, 2), {})
    assert evidence["fingerprint"] is False
    assert evidence["camera_compatibility"] == "UNKNOWN"


def test_mhcs_response_classifies_explicit_failures():
    base = {
        "http_status": 200,
        "health_status": 200,
        "content_type": "application/dicom",
        "response_bytes": 10,
        "dicom_structure": True,
    }
    assert classify_mhcs_response({**base, "config": False}) == "CONFIG_FAILED"
    assert classify_mhcs_response({**base, "dns": False}) == "DNS_FAILED"
    assert classify_mhcs_response({**base, "health_status": 500}) == "HEALTH_FAILED"
    assert classify_mhcs_response({**base, "http_status": 500}) == "FAIL"


def test_camera_compatibility_uses_all_sources_and_aliases():
    assert (
        camera_compatibility(
            {"serialNumber": "cam-A"},
            {"serialNumber": "cam-A"},
            {"serialNumber": "cam-A"},
        )
        == "PASS"
    )
    assert (
        camera_compatibility(
            {"serialNumber": "cam-A"},
            {"serialNumber": "cam-B"},
            {"serialNumber": "cam-A"},
        )
        == "FAIL"
    )
    assert (
        camera_compatibility(
            {"serialNumber": "cam-A"},
            {"serialNumber": "cam-A"},
            {"cameraSerial": "cam-B"},
        )
        == "FAIL"
    )
    assert camera_compatibility({}, {}, {}) == "UNKNOWN"
    assert (
        camera_compatibility({"cameraSerial": "cam-A"}, {"serialNumber": "cam-A"}, {})
        == "PASS"
    )


def test_mhcs_probe_stage_mapping_is_explicit():
    assert (
        classify_mhcs_probe({"ok": False, "stage": "config"}, "BED")
        == "MHCS_MPIPS_CONFIG_FAILED"
    )
    assert (
        classify_mhcs_probe({"ok": False, "stage": "dns"}, "BED")
        == "MHCS_MPIPS_DNS_FAILED"
    )
    assert (
        classify_mhcs_probe({"ok": False, "stage": "health"}, "BED")
        == "MHCS_MPIPS_HEALTH_FAILED"
    )
    assert (
        classify_mhcs_probe({"ok": False, "stage": "mpips_client"}, "THORAX")
        == "MHCS_THORAX_MPIPSCLIENT_FAILED"
    )
