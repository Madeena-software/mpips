import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pydicom
import pytest

from mpips import convert_npz_to_dicom
from mpips.conversion import (
    ConversionError,
    convert_npz_to_dicom as convenience_convert_npz_to_dicom,
)
from mpips.workflows.imager_pipeline.npz_io import sha256_file


def _create_calibration_artifact(
    cal_dir: Path,
    shape: tuple[int, int] = (64, 64),
    detector_mode: str = "BED",
) -> Path:
    cal_dir.mkdir(parents=True, exist_ok=True)
    y_vals, x_vals = np.indices(shape, dtype=np.float32)
    np.savez_compressed(cal_dir / "remap.npz", map_x=x_vals, map_y=y_vals)
    metadata = {
        "validated": True,
        "fingerprint": f"test-cal-fp-{detector_mode}",
        "image_shape": list(shape),
        "source_metadata": {
            "detector_mode": detector_mode,
            "camera_params": {"serialNumber": "CAM123"},
        },
    }
    (cal_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return cal_dir


def _create_test_npzs(
    base_dir: Path, detector_mode: str = "BED", shape: tuple[int, int] = (64, 64)
) -> tuple[Path, Path, str, str, int, int]:
    rad_dir = base_dir / "radiograph"
    gain_dir = base_dir / "gain"
    rad_dir.mkdir(parents=True, exist_ok=True)
    gain_dir.mkdir(parents=True, exist_ok=True)

    rad_path = rad_dir / "capture.npz"
    gain_path = gain_dir / "gain.npz"

    gain_id = "GAIN-001"
    rad_id = "RAD-001"

    raw_img = (np.ones(shape, dtype=np.uint16) * 1000).astype(np.uint16)
    dark_img = (np.ones(shape, dtype=np.uint16) * 50).astype(np.uint16)
    flat_img = (np.ones(shape, dtype=np.uint16) * 2000).astype(np.uint16)

    np.savez_compressed(
        rad_path,
        id=np.array(rad_id),
        gainid=np.array(gain_id),
        rawimage=raw_img,
        xrayparams=np.array({"detectorMode": detector_mode}),
        cameraparams=np.array({"serialNumber": "CAM123"}),
    )

    np.savez_compressed(
        gain_path,
        id=np.array(gain_id),
        rawimage=flat_img,
        darkimage=dark_img,
        xrayparams=np.array({"detectorMode": detector_mode}),
        cameraparams=np.array({"serialNumber": "CAM123"}),
    )

    rad_sha = sha256_file(rad_path)
    gain_sha = sha256_file(gain_path)
    rad_size = rad_path.stat().st_size
    gain_size = gain_path.stat().st_size

    return rad_path, gain_path, rad_sha, gain_sha, rad_size, gain_size


def _build_manifest(
    rad_sha: str,
    gain_sha: str,
    rad_size: int,
    gain_size: int,
    detector_mode: str = "BED",
) -> Dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "conversion_job_id": "97eeb9ef-d93c-43e7-aebe-c9ada5cc29fa",
        "submission_id": "a46c3061-220a-4a1f-babe-a99f446439e5",
        "correlation_id": "29722404-a494-46ca-960b-537255d37982",
        "examination": {
            "examination_id": "EXM-20260804-000001",
            "accession_number": "RF260804000123",
            "study_id": "STUDY00000123",
            "performed_at": "2026-08-04T19:30:00+07:00",
            "study_description": "Chest Radiography",
            "protocol_name": "Adult Chest PA",
        },
        "patient": {
            "medical_record_number": "MHCS-00000123",
            "name": {"full_name": "Faliq Adlan", "family_name": "Adlan"},
            "sex": "male",
            "birth_date": "1990-01-01",
        },
        "operator": {
            "operator_id": "9df6240c-6094-4814-a40e-e14a5026b910",
            "name": {"full_name": "Andre Nasution", "family_name": "Nasution"},
        },
        "site": {
            "organization_id": "ORG-000001",
            "site_id": "SITE-000001",
            "institution_name": "Klinik Contoh",
            "department_name": "Radiology",
            "station_name": "XRAY-ROOM-01",
            "timezone": "Asia/Jakarta",
        },
        "capture": {
            "capture_id": "CAP-000001",
            "detector_type": detector_mode,
            "protocol_version": "CHEST-PA-V1",
            "body_part_examined": "CHEST",
            "laterality": "U",
            "projection": "PA",
            "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
            "view_code_sequence": [
                {
                    "code_value": "272479007",
                    "coding_scheme_designator": "SCT",
                    "code_meaning": "postero-anterior",
                }
            ],
            "captured_at": "2026-08-04T19:30:00+07:00",
            "radiograph": {
                "filename": "capture.npz",
                "byte_size": rad_size,
                "sha256": rad_sha,
            },
            "gain": {
                "filename": "gain.npz",
                "byte_size": gain_size,
                "sha256": gain_sha,
            },
        },
        "dicom": {
            "study_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.1",
            "series_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.2",
            "sop_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.3",
            "series_number": 1,
            "instance_number": 1,
            "series_description": "Chest PA",
            "presentation_intent": "FOR PRESENTATION",
            "pixel_source": "CANONICAL_PRE_PRESENTATION",
            "pixel_intensity_relationship": "LIN",
            "pixel_intensity_relationship_sign": 1,
        },
    }


def test_public_import_surfaces() -> None:
    assert callable(convert_npz_to_dicom)
    assert convenience_convert_npz_to_dicom is convert_npz_to_dicom
    assert issubclass(ConversionError, RuntimeError)


def test_convert_npz_to_dicom_validates_missing_inputs(tmp_path: Path) -> None:
    dummy_rad = tmp_path / "missing_rad.npz"
    dummy_gain = tmp_path / "missing_gain.npz"
    dummy_out = tmp_path / "output.dcm"

    # Missing radiograph
    with pytest.raises(FileNotFoundError, match="Radiograph NPZ file not found"):
        convert_npz_to_dicom(
            dummy_rad,
            dummy_gain,
            {},
            dummy_out,
        )

    # Existing rad, missing gain
    existing_rad = tmp_path / "rad.npz"
    existing_rad.write_bytes(b"dummy")
    with pytest.raises(FileNotFoundError, match="Gain NPZ file not found"):
        convert_npz_to_dicom(
            existing_rad,
            dummy_gain,
            {},
            dummy_out,
        )

    # Existing rad & gain, missing manifest file
    existing_gain = tmp_path / "gain.npz"
    existing_gain.write_bytes(b"dummy")
    missing_manifest = tmp_path / "missing_manifest.json"
    with pytest.raises(FileNotFoundError, match="Manifest file not found"):
        convert_npz_to_dicom(
            existing_rad,
            existing_gain,
            missing_manifest,
            dummy_out,
        )

    # Invalid manifest JSON / dict
    with pytest.raises(ValueError, match="Invalid manifest"):
        convert_npz_to_dicom(
            existing_rad,
            existing_gain,
            "{ invalid json",
            dummy_out,
        )

    # Missing calibration directory
    with pytest.raises(FileNotFoundError, match="Calibration directory not found"):
        convert_npz_to_dicom(
            existing_rad,
            existing_gain,
            {"invalid": "schema"},
            dummy_out,
            calibration_dir=tmp_path / "nonexistent_cal",
        )


def test_convert_npz_to_dicom_end_to_end_dict_manifest(tmp_path: Path) -> None:
    cal_dir = _create_calibration_artifact(tmp_path / "cal", shape=(64, 64))
    rad_p, gain_p, r_sha, g_sha, r_sz, g_sz = _create_test_npzs(
        tmp_path, shape=(64, 64)
    )
    manifest_dict = _build_manifest(r_sha, g_sha, r_sz, g_sz)
    out_dcm = tmp_path / "destination" / "result.dcm"

    result_path = convert_npz_to_dicom(
        radiograph_npz_path=rad_p,
        gain_npz_path=gain_p,
        manifest=manifest_dict,
        output_dicom_path=out_dcm,
        calibration_dir=cal_dir,
    )

    assert result_path == out_dcm.resolve()
    assert out_dcm.is_file()
    assert out_dcm.stat().st_size > 0

    ds = pydicom.dcmread(str(out_dcm))
    assert ds.Modality == "DX"
    assert ds.SOPClassUID == "1.2.840.10008.5.1.4.1.1.1.1.1"
    assert ds.StudyInstanceUID == "1.2.826.0.1.3680043.10.1356.1.1.1"
    assert ds.SeriesInstanceUID == "1.2.826.0.1.3680043.10.1356.1.1.2"
    assert ds.SOPInstanceUID == "1.2.826.0.1.3680043.10.1356.1.1.3"
    assert ds.PatientName == "Adlan^Faliq"
    assert ds.PatientID == "MHCS-00000123"
    assert ds.BitsAllocated == 16
    assert ds.BitsStored == 16
    assert ds.HighBit == 15
    assert ds.PixelRepresentation == 0
    assert ds.PhotometricInterpretation == "MONOCHROME2"
    assert ds.pixel_array.shape == (64, 64)
    assert ds.pixel_array.dtype == np.uint16


def test_convert_npz_to_dicom_end_to_end_json_string_and_file_manifest(
    tmp_path: Path,
) -> None:
    cal_dir = _create_calibration_artifact(tmp_path / "cal", shape=(64, 64))
    rad_p, gain_p, r_sha, g_sha, r_sz, g_sz = _create_test_npzs(
        tmp_path, shape=(64, 64)
    )
    manifest_dict = _build_manifest(r_sha, g_sha, r_sz, g_sz)

    # 1. JSON string
    json_str = json.dumps(manifest_dict)
    out_1 = tmp_path / "out1.dcm"
    res_1 = convert_npz_to_dicom(
        radiograph_npz_path=rad_p,
        gain_npz_path=gain_p,
        manifest=json_str,
        output_dicom_path=out_1,
        calibration_dir=cal_dir,
    )
    assert res_1 == out_1.resolve()
    assert out_1.is_file()
    ds1 = pydicom.dcmread(str(out_1))
    assert ds1.Modality == "DX"

    # 2. Manifest file path
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json_str, encoding="utf-8")
    out_2 = tmp_path / "out2.dcm"
    res_2 = convert_npz_to_dicom(
        radiograph_npz_path=rad_p,
        gain_npz_path=gain_p,
        manifest=manifest_file,
        output_dicom_path=out_2,
        calibration_dir=cal_dir,
    )
    assert res_2 == out_2.resolve()
    assert out_2.is_file()
    ds2 = pydicom.dcmread(str(out_2))
    assert ds2.Modality == "DX"


def test_convert_npz_to_dicom_trx_mode_clockwise_rotation(tmp_path: Path) -> None:
    cal_dir = _create_calibration_artifact(
        tmp_path / "cal_trx", shape=(64, 64), detector_mode="TRX"
    )
    rad_p, gain_p, r_sha, g_sha, r_sz, g_sz = _create_test_npzs(
        tmp_path, detector_mode="TRX", shape=(64, 64)
    )
    manifest_dict = _build_manifest(r_sha, g_sha, r_sz, g_sz, detector_mode="TRX")
    out_dcm = tmp_path / "trx_result.dcm"

    result_path = convert_npz_to_dicom(
        radiograph_npz_path=rad_p,
        gain_npz_path=gain_p,
        manifest=manifest_dict,
        output_dicom_path=out_dcm,
        calibration_dir=cal_dir,
    )

    assert result_path == out_dcm.resolve()
    assert out_dcm.is_file()
    ds = pydicom.dcmread(str(out_dcm))
    assert ds.Modality == "DX"
    assert ds.pixel_array.dtype == np.uint16


def test_convert_npz_to_dicom_raises_standard_exceptions_never_http_exception(
    tmp_path: Path,
) -> None:
    cal_dir = _create_calibration_artifact(tmp_path / "cal", shape=(64, 64))
    rad_p, gain_p, r_sha, g_sha, r_sz, g_sz = _create_test_npzs(
        tmp_path, shape=(64, 64)
    )
    manifest_dict = _build_manifest(r_sha, g_sha, r_sz, g_sz)

    # Corrupt radiograph file content
    corrupt_rad = tmp_path / "corrupt.npz"
    corrupt_rad.write_bytes(b"not an npz file")

    with pytest.raises(Exception) as exc_info:
        convert_npz_to_dicom(
            radiograph_npz_path=corrupt_rad,
            gain_npz_path=gain_p,
            manifest=manifest_dict,
            output_dicom_path=tmp_path / "fail.dcm",
            calibration_dir=cal_dir,
        )

    # Must NOT be an HTTPException or subclass
    exc = exc_info.value
    assert not exc.__class__.__name__.endswith("HTTPException")
    assert isinstance(exc, (ValueError, RuntimeError, ConversionError))
