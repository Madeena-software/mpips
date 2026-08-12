from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import numpy as np
import pydicom
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mpips.api.application import app, _validate_production_configuration
from mpips.api.api_key import API_KEY
from mpips.api.idempotency import ClaimResult
from mpips.api.routes.v1.dicom import _get_upload_limits
from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.service import _cleanup_workspace, _validate_tiff_descriptor
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.npz_io import sha256_file, write_tiff

CONVERTER_PATH = "mpips/engine/imager_pipeline/tiff_json_to_dcm.py"
EXPECTED_HASH = "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0"


@pytest.fixture(autouse=True)
def setup_env_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    cal_dir = tmp_path_factory.mktemp("default_cal")
    y_vals, x_vals = np.indices((64, 64), dtype=np.float32)
    np.savez_compressed(cal_dir / "remap.npz", map_x=x_vals, map_y=y_vals)
    metadata = {
        "validated": True,
        "fingerprint": "default-test-cal-fp",
        "image_shape": [64, 64],
        "source_metadata": {
            "detector_mode": "BED",
            "camera_params": {"serialNumber": "CAM123"},
        },
    }
    (cal_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    monkeypatch.setenv("MPIPS_CALIBRATION_ARTIFACT_DIR", str(cal_dir))


def generate_test_npzs(temp_dir: str) -> tuple[str, str, str, str, int, int]:
    """Helper to generate valid dummy radiograph and gain NPZ files."""
    rad_dir = Path(temp_dir) / "radiograph"
    gain_dir = Path(temp_dir) / "gain"
    rad_dir.mkdir(parents=True, exist_ok=True)
    gain_dir.mkdir(parents=True, exist_ok=True)

    rad_path = rad_dir / "capture-001.npz"
    gain_path = gain_dir / "gain-042.npz"

    gain_id = "GAIN-000042"
    rad_id = "CAP-000001"

    raw_img = np.ones((64, 64), dtype=np.uint16) * 1000
    dark_img = np.ones((64, 64), dtype=np.uint16) * 50
    flat_img = np.ones((64, 64), dtype=np.uint16) * 2000

    np.savez_compressed(
        rad_path,
        id=np.array(rad_id),
        gainid=np.array(gain_id),
        rawimage=raw_img,
        xrayparams=np.array({"detectorMode": "BED"}),
        cameraparams=np.array({"serialNumber": "CAM123"}),
    )

    np.savez_compressed(
        gain_path,
        id=np.array(gain_id),
        rawimage=flat_img,
        darkimage=dark_img,
        xrayparams=np.array({"detectorMode": "BED"}),
        cameraparams=np.array({"serialNumber": "CAM123"}),
    )

    rad_sha = sha256_file(rad_path)
    gain_sha = sha256_file(gain_path)
    rad_size = rad_path.stat().st_size
    gain_size = gain_path.stat().st_size

    return str(rad_path), str(gain_path), rad_sha, gain_sha, rad_size, gain_size


def make_test_manifest(
    rad_sha: str,
    gain_sha: str,
    rad_size: int,
    gain_size: int,
    job_id: str = "97eeb9ef-d93c-43e7-aebe-c9ada5cc29fa",
) -> Dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "conversion_job_id": job_id,
        "submission_id": "a46c3061-220a-4a1f-babe-a99f446439e5",
        "correlation_id": "29722404-a494-46ca-960b-537255d37982",
        "examination": {
            "examination_id": "EXM-20260804-000001",
            "booking_id": "BKG-00000123",
            "service_request_id": "SR-00000123",
            "encounter_id": "ENC-00000123",
            "accession_number": "RF260804000123",
            "study_id": "STUDY00000123",
            "performed_at": "2026-08-04T19:30:00+07:00",
            "study_description": "Chest Radiography",
            "protocol_name": "Adult Chest PA",
        },
        "patient": {
            "member_id": "c41c449e-2f28-42c8-a0ed-0832265dd6c1",
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
            "protocol_version": "CHEST-PA-V1",
            "body_part_examined": "CHEST",
            "laterality": "U",
            "projection": "PA",
            "captured_at": "2026-08-04T19:30:00+07:00",
            "radiograph": {
                "filename": "capture-001.npz",
                "byte_size": rad_size,
                "sha256": rad_sha,
            },
            "gain": {
                "gain_id": "GAIN-000042",
                "filename": "gain-042.npz",
                "byte_size": gain_size,
                "sha256": gain_sha,
            },
            "image_spacing": {"row_um": 140.0, "column_um": 140.0},
        },
        "dicom": {
            "study_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.1",
            "series_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.2",
            "sop_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.3",
            "series_number": 1,
            "instance_number": 1,
            "series_description": "Chest PA",
            "presentation_intent": "FOR PRESENTATION",
        },
    }


# ── 1. TOCTOU-Safe Parent TIFF Descriptor Validation Tests ───────────


def test_validate_tiff_descriptor_success() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir) / "output"
        out_dir.mkdir()
        tiff_path = out_dir / "processed.tiff"
        res_path = out_dir / "worker-result.json"

        img_data = np.ones((32, 32), dtype=np.uint16) * 500
        write_tiff(tiff_path, img_data)
        with res_path.open("w") as f:
            json.dump({"status": "success"}, f)

        arr, shape = _validate_tiff_descriptor(out_dir, max_tiff_bytes=10 * 1024 * 1024)
        assert shape == (32, 32)
        assert arr.dtype == np.uint16


def test_validate_tiff_descriptor_rejects_extra_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir) / "output"
        out_dir.mkdir()
        tiff_path = out_dir / "processed.tiff"
        res_path = out_dir / "worker-result.json"
        extra_path = out_dir / "malicious.sh"

        img_data = np.ones((32, 32), dtype=np.uint16)
        write_tiff(tiff_path, img_data)
        with res_path.open("w") as f:
            json.dump({"status": "success"}, f)
        extra_path.write_text("echo hacked")

        with pytest.raises(HTTPException) as exc:
            _validate_tiff_descriptor(out_dir, max_tiff_bytes=10 * 1024 * 1024)
        assert exc.value.detail == "TIFF_VALIDATION_ERROR"


# ── 2. Converter Immutability & Basic Tests ──────────────────────────


def test_converter_immutability() -> None:
    current_hash = sha256_file(CONVERTER_PATH)
    assert current_hash == EXPECTED_HASH, "Pak Andre's converter was modified!"
    assert callable(tiff_json_to_dcm)


# ── 3. End-to-End Successful Conversion Endpoint Test ────────────────


def test_successful_dicom_conversion_endpoint() -> None:
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        raw_manifest_bytes = json.dumps(manifest_dict).encode("utf-8")

        files = {
            "radiograph_npz": (
                "capture-001.npz",
                open(r_path, "rb"),
                "application/octet-stream",
            ),
            "gain_npz": (
                "gain-042.npz",
                open(g_path, "rb"),
                "application/octet-stream",
            ),
            "manifest": ("manifest.json", raw_manifest_bytes, "application/json"),
        }
        headers = {
            "X-MPIPS-API-Key": API_KEY,
        }

        mock_claim = ClaimResult(status="CLAIMED", lease_token="lease_123")
        with (
            patch(
                "mpips.api.routes.v1.dicom.IdempotencyService.claim_job",
                return_value=mock_claim,
            ),
            patch(
                "mpips.api.routes.v1.dicom.IdempotencyService.mark_success"
            ) as mock_mark_success,
        ):
            resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
            assert resp.status_code == 200, f"Error: {resp.text}"
            assert resp.headers["Content-Type"] == "application/dicom"
            assert "Content-Disposition" in resp.headers
            assert resp.headers["X-Correlation-ID"] == (
                "29722404-a494-46ca-960b-537255d37982"
            )
            assert resp.headers["X-Conversion-Job-ID"] == (
                "97eeb9ef-d93c-43e7-aebe-c9ada5cc29fa"
            )

            dcm_bytes = resp.content
            ds = pydicom.dcmread(io.BytesIO(dcm_bytes))

            assert ds.PatientID == "MHCS-00000123"
            assert ds.PatientName == "Adlan^Faliq"
            assert ds.OperatorsName == "Nasution^Andre"
            assert ds.PatientSex == "M"
            assert ds.PatientBirthDate == "19900101"
            assert ds.AccessionNumber == "RF260804000123"
            assert ds.StudyID == "STUDY00000123"
            assert ds.PresentationIntentType == "FOR PRESENTATION"
            assert ds.BurnedInAnnotation == "NO"
            assert ds.LossyImageCompression == "00"
            assert ds.Rows == 64
            assert ds.Columns == 64
            assert ds.pixel_array.dtype == np.uint16

            assert mock_mark_success.called


# ── 4. Production Startup Configuration Validation Tests ─────────────


def test_production_startup_validation_requires_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        _validate_production_configuration()


def test_production_startup_validation_accepts_fixed_key_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    _validate_production_configuration()


def test_default_radiograph_upload_limit_is_100_mib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MPIPS_DICOM_MAX_RADIOGRAPH_BYTES", raising=False)
    assert _get_upload_limits()[1] == 100 * 1024 * 1024


# ── 5. OpenAPI Privacy Audit Test ────────────────────────────────────


def test_no_nik_in_openapi() -> None:
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi_str = resp.text.lower()
    assert '"nik"' not in openapi_str


# ── 6. Calibration Pipeline Correction Tests ─────────────────────────


def create_test_calibration_artifact(
    cal_dir: Path,
    shape: tuple[int, int] = (64, 64),
    detector_mode: str = "BED",
    camera_serial: str = "CAM123",
    remap_offset: float = 0.0,
    fingerprint: str = "test-cal-fp-123",
    validated: bool = True,
) -> Path:
    cal_dir.mkdir(parents=True, exist_ok=True)
    y_vals, x_vals = np.indices(shape, dtype=np.float32)
    map_x = x_vals + remap_offset
    map_y = y_vals + remap_offset
    np.savez_compressed(cal_dir / "remap.npz", map_x=map_x, map_y=map_y)
    metadata = {
        "validated": validated,
        "fingerprint": fingerprint,
        "image_shape": list(shape),
        "source_metadata": {
            "detector_mode": detector_mode,
            "camera_params": {"serialNumber": camera_serial},
        },
    }
    (cal_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return cal_dir


def test_worker_passes_map_x_and_map_y_to_process_radiography_arrays(
    tmp_path: Path,
) -> None:
    cal_dir = create_test_calibration_artifact(tmp_path / "calibration")
    r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(str(tmp_path))

    args_data = {
        "radiograph_npz_path": r_path,
        "gain_npz_path": g_path,
        "calibration_dir": str(cal_dir),
        "expected_gain_id": "GAIN-000042",
        "expected_detector_mode": "BED",
        "expected_camera_serial": "CAM123",
        "output_tiff_path": str(tmp_path / "output.tiff"),
        "result_path": str(tmp_path / "result.json"),
    }
    args_file = tmp_path / "args.json"
    args_file.write_text(json.dumps(args_data))

    from mpips.conversion.worker import execute_conversion_worker

    captured_kwargs = {}

    def mock_process_radiography_arrays(
        raw: Any, dark: Any, flat: Any, mode: str, **kwargs: Any
    ) -> Any:
        captured_kwargs.update(kwargs)
        return np.ones((64, 64), dtype=np.uint16) * 500

    with patch(
        "mpips.conversion.worker.process_radiography_arrays",
        side_effect=mock_process_radiography_arrays,
    ):
        execute_conversion_worker(str(args_file), str(tmp_path / "result.json"))

    assert "map_x" in captured_kwargs
    assert "map_y" in captured_kwargs
    assert captured_kwargs["map_x"] is not None
    assert captured_kwargs["map_y"] is not None
    assert captured_kwargs["map_x"].shape == (64, 64)
    assert captured_kwargs["map_y"].shape == (64, 64)


def test_worker_rejects_malformed_npz_as_validation_error(tmp_path: Path) -> None:
    cal_dir = create_test_calibration_artifact(tmp_path / "calibration")
    radiograph_path, gain_path, *_ = generate_test_npzs(str(tmp_path))
    Path(radiograph_path).write_bytes(b"not-an-npz")
    args_path = tmp_path / "args.json"
    result_path = tmp_path / "result.json"
    args_path.write_text(
        json.dumps(
            {
                "radiograph_npz_path": radiograph_path,
                "gain_npz_path": gain_path,
                "calibration_dir": str(cal_dir),
                "expected_gain_id": "GAIN-000042",
                "output_tiff_path": str(tmp_path / "output.tiff"),
                "result_path": str(result_path),
            }
        )
    )

    from mpips.conversion.worker import execute_conversion_worker

    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_path), str(result_path))

    assert json.loads(result_path.read_text())["sanitized_error_code"] == (
        "NPZ_VALIDATION_ERROR"
    )


def test_missing_calibration_artifact_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MPIPS_CALIBRATION_ARTIFACT_DIR", str(tmp_path / "nonexistent"))
    r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(str(tmp_path))
    manifest = MHCSManifest.model_validate(make_test_manifest(r_sha, g_sha, r_sz, g_sz))

    from mpips.conversion.service import run_isolated_dicom_conversion

    with pytest.raises(HTTPException) as exc_info:
        run_isolated_dicom_conversion(
            Path(r_path), Path(g_path), manifest, tmp_path / "output.dcm"
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "CALIBRATION_ARTIFACT_MISSING"


def test_remap_shape_mismatch_fails(tmp_path: Path) -> None:
    cal_dir = create_test_calibration_artifact(tmp_path / "calibration", shape=(32, 32))
    r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(str(tmp_path))

    args_data = {
        "radiograph_npz_path": r_path,
        "gain_npz_path": g_path,
        "calibration_dir": str(cal_dir),
        "expected_gain_id": "GAIN-000042",
        "output_tiff_path": str(tmp_path / "output.tiff"),
        "result_path": str(tmp_path / "result.json"),
    }
    args_file = tmp_path / "args.json"
    args_file.write_text(json.dumps(args_data))

    from mpips.conversion.worker import execute_conversion_worker

    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_file), str(tmp_path / "result.json"))

    res = json.loads((tmp_path / "result.json").read_text())
    assert res["status"] == "failed"
    assert res["sanitized_error_code"] == "NPZ_VALIDATION_ERROR"


def test_map_x_map_y_shape_mismatch_fails(tmp_path: Path) -> None:
    cal_dir = tmp_path / "calibration_mismatch"
    cal_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cal_dir / "remap.npz",
        map_x=np.zeros((70, 70), dtype=np.float32),
        map_y=np.zeros((64, 64), dtype=np.float32),
    )
    metadata = {
        "validated": True,
        "fingerprint": "test-cal-fp-mismatch",
        "image_shape": [64, 64],
        "source_metadata": {
            "detector_mode": "BED",
            "camera_params": {"serialNumber": "CAM123"},
        },
    }
    (cal_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    r_path, g_path, *_ = generate_test_npzs(str(tmp_path))
    args_data = {
        "radiograph_npz_path": r_path,
        "gain_npz_path": g_path,
        "calibration_dir": str(cal_dir),
        "expected_gain_id": "GAIN-000042",
        "output_tiff_path": str(tmp_path / "output.tiff"),
        "result_path": str(tmp_path / "result.json"),
    }
    args_file = tmp_path / "args.json"
    args_file.write_text(json.dumps(args_data))

    from mpips.conversion.worker import execute_conversion_worker

    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_file), str(tmp_path / "result.json"))

    res = json.loads((tmp_path / "result.json").read_text())
    assert res["status"] == "failed"
    assert res["sanitized_error_code"] == "NPZ_VALIDATION_ERROR"


def test_expanded_canvas_remap_shape_accepted(tmp_path: Path) -> None:
    cal_dir = tmp_path / "calibration_expanded"
    cal_dir.mkdir(parents=True, exist_ok=True)
    y_vals, x_vals = np.indices((70, 70), dtype=np.float32)
    np.savez_compressed(
        cal_dir / "remap.npz",
        map_x=x_vals,
        map_y=y_vals,
    )
    metadata = {
        "validated": True,
        "fingerprint": "test-cal-fp-expanded",
        "image_shape": [64, 64],
        "source_metadata": {
            "detector_mode": "BED",
            "camera_params": {"serialNumber": "CAM123"},
        },
    }
    (cal_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    r_path, g_path, *_ = generate_test_npzs(str(tmp_path))
    args_data = {
        "radiograph_npz_path": r_path,
        "gain_npz_path": g_path,
        "calibration_dir": str(cal_dir),
        "expected_gain_id": "GAIN-000042",
        "output_tiff_path": str(tmp_path / "output.tiff"),
        "result_path": str(tmp_path / "result.json"),
    }
    args_file = tmp_path / "args.json"
    args_file.write_text(json.dumps(args_data))

    from mpips.conversion.worker import execute_conversion_worker

    execute_conversion_worker(str(args_file), str(tmp_path / "result.json"))

    res = json.loads((tmp_path / "result.json").read_text())
    assert res["status"] == "success"
    assert Path(tmp_path / "output.tiff").exists()



def test_detector_and_camera_mismatch_fails(tmp_path: Path) -> None:
    # Test A: detector mode mismatch
    cal_dir_det = create_test_calibration_artifact(
        tmp_path / "cal_det", detector_mode="TRX"
    )
    r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(str(tmp_path))

    args_data = {
        "radiograph_npz_path": r_path,
        "gain_npz_path": g_path,
        "calibration_dir": str(cal_dir_det),
        "expected_gain_id": "GAIN-000042",
        "output_tiff_path": str(tmp_path / "output.tiff"),
        "result_path": str(tmp_path / "result_det.json"),
    }
    args_file = tmp_path / "args_det.json"
    args_file.write_text(json.dumps(args_data))

    from mpips.conversion.worker import execute_conversion_worker

    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_file), str(tmp_path / "result_det.json"))

    res_det = json.loads((tmp_path / "result_det.json").read_text())
    assert res_det["status"] == "failed"
    assert res_det["sanitized_error_code"] == "NPZ_VALIDATION_ERROR"

    # Test B: camera serial mismatch
    cal_dir_cam = create_test_calibration_artifact(
        tmp_path / "cal_cam", camera_serial="CAM999"
    )
    args_data["calibration_dir"] = str(cal_dir_cam)
    args_file_cam = tmp_path / "args_cam.json"
    args_file_cam.write_text(json.dumps(args_data))

    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_file_cam), str(tmp_path / "result_cam.json"))

    res_cam = json.loads((tmp_path / "result_cam.json").read_text())
    assert res_cam["status"] == "failed"
    assert res_cam["sanitized_error_code"] == "NPZ_VALIDATION_ERROR"


def test_calibrated_output_differs_from_uncalibrated_control_fixture() -> None:
    from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays
    from mpips.workflows.imager_pipeline.models import ImagerPipelineConfig

    shape = (64, 64)
    y_vals, x_vals = np.indices(shape, dtype=np.uint16)
    raw = (1000 + x_vals * 10 + y_vals * 5).astype(np.uint16)
    dark = np.ones(shape, dtype=np.uint16) * 50
    flat = np.ones(shape, dtype=np.uint16) * 2000

    config = ImagerPipelineConfig(use_denoise=False, use_clahe=False)

    y_idx, x_idx = np.indices(shape, dtype=np.float32)

    # Control fixture (identity remap)
    control_out = process_radiography_arrays(
        raw, dark, flat, "BED", config, map_x=x_idx, map_y=y_idx
    )

    # Calibrated fixture with spatial warp
    warped_x = x_idx + 3.0
    warped_y = y_idx + 3.0
    calibrated_out = process_radiography_arrays(
        raw, dark, flat, "BED", config, map_x=warped_x, map_y=warped_y
    )

    assert not np.array_equal(calibrated_out, control_out)


def test_no_dicom_conversion_until_parent_tiff_valid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cal_dir = create_test_calibration_artifact(tmp_path / "calibration")
    monkeypatch.setenv("MPIPS_CALIBRATION_ARTIFACT_DIR", str(cal_dir))
    r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(str(tmp_path))
    manifest = MHCSManifest.model_validate(make_test_manifest(r_sha, g_sha, r_sz, g_sz))

    from mpips.conversion.service import run_isolated_dicom_conversion

    # Patch _validate_tiff_descriptor to simulate failed TIFF descriptor validation
    with (
        patch(
            "mpips.conversion.service._validate_tiff_descriptor",
            side_effect=HTTPException(status_code=500, detail="TIFF_VALIDATION_ERROR"),
        ),
        patch("mpips.conversion.service.tiff_json_to_dcm") as mock_converter,
    ):
        with pytest.raises(HTTPException) as exc_info:
            run_isolated_dicom_conversion(
                Path(r_path), Path(g_path), manifest, tmp_path / "output.dcm"
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "TIFF_VALIDATION_ERROR"
        # Converter MUST NOT be called!
        assert not mock_converter.called


def test_workspace_cleanup_removes_read_only_nested_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "job-read-only"
    nested = workspace / "calibration"
    nested.mkdir(parents=True)
    (nested / "metadata.json").write_text("{}", encoding="utf-8")
    os.chmod(workspace, 0o700)
    os.chmod(nested, 0o500)
    os.chmod(nested / "metadata.json", 0o400)

    _cleanup_workspace(workspace)

    assert not workspace.exists()


def generate_custom_mode_npzs(
    temp_dir: str, detector_mode: str = "TRX"
) -> tuple[str, str, str, str, int, int]:
    """Helper to generate valid dummy radiograph and gain NPZ files with a custom detector_mode."""
    rad_dir = Path(temp_dir) / f"radiograph_{detector_mode}"
    gain_dir = Path(temp_dir) / f"gain_{detector_mode}"
    rad_dir.mkdir(parents=True, exist_ok=True)
    gain_dir.mkdir(parents=True, exist_ok=True)

    rad_path = rad_dir / "capture-001.npz"
    gain_path = gain_dir / "gain-042.npz"

    gain_id = f"GAIN-{detector_mode}-042"
    rad_id = f"CAP-{detector_mode}-001"

    raw_img = np.ones((64, 64), dtype=np.uint16) * 1000
    dark_img = np.ones((64, 64), dtype=np.uint16) * 50
    flat_img = np.ones((64, 64), dtype=np.uint16) * 2000

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

    return str(rad_path), str(gain_path), rad_sha, gain_sha, rad_size, gain_size


def test_multi_mode_calibration_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from mpips.conversion.service import resolve_calibration_artifact_dir
    from mpips.conversion.worker import execute_conversion_worker

    multi_cal_root = tmp_path / "multi_cal"
    bed_cal_dir = multi_cal_root / "BED"
    stand_cal_dir = multi_cal_root / "STAND"

    create_test_calibration_artifact(
        bed_cal_dir, shape=(64, 64), detector_mode="BED", camera_serial="CAM123"
    )
    create_test_calibration_artifact(
        stand_cal_dir, shape=(64, 64), detector_mode="TRX", camera_serial="CAM123"
    )

    # 1. Verify resolve_calibration_artifact_dir accepts multi-mode root
    monkeypatch.setenv("MPIPS_CALIBRATION_ARTIFACT_DIR", str(multi_cal_root))
    assert resolve_calibration_artifact_dir() == multi_cal_root

    # 2. Test BED radiograph payload selects BED calibration subdirectory
    bed_r, bed_g, *_ = generate_test_npzs(str(tmp_path / "bed_npzs"))
    args_data_bed = {
        "radiograph_npz_path": bed_r,
        "gain_npz_path": bed_g,
        "calibration_dir": str(multi_cal_root),
        "expected_gain_id": "GAIN-000042",
        "output_tiff_path": str(tmp_path / "out_bed.tiff"),
        "result_path": str(tmp_path / "result_bed.json"),
    }
    args_file_bed = tmp_path / "args_bed.json"
    args_file_bed.write_text(json.dumps(args_data_bed))

    execute_conversion_worker(str(args_file_bed), str(tmp_path / "result_bed.json"))
    res_bed = json.loads((tmp_path / "result_bed.json").read_text())
    assert res_bed["status"] == "success"
    assert (tmp_path / "out_bed.tiff").exists()

    # 3. Test TRX/STAND radiograph payload selects STAND calibration subdirectory (detector_mode=TRX)
    trx_r, trx_g, *_ = generate_custom_mode_npzs(
        str(tmp_path / "trx_npzs"), detector_mode="TRX"
    )
    args_data_trx = {
        "radiograph_npz_path": trx_r,
        "gain_npz_path": trx_g,
        "calibration_dir": str(multi_cal_root),
        "expected_gain_id": "GAIN-TRX-042",
        "output_tiff_path": str(tmp_path / "out_trx.tiff"),
        "result_path": str(tmp_path / "result_trx.json"),
    }
    args_file_trx = tmp_path / "args_trx.json"
    args_file_trx.write_text(json.dumps(args_data_trx))

    execute_conversion_worker(str(args_file_trx), str(tmp_path / "result_trx.json"))
    res_trx = json.loads((tmp_path / "result_trx.json").read_text())
    assert res_trx["status"] == "success"
    assert (tmp_path / "out_trx.tiff").exists()

    # 4. Test unmapped detector_mode payload fails when calibration artifact for mode is missing
    multi_cal_only_bed = tmp_path / "multi_cal_only_bed"
    create_test_calibration_artifact(
        multi_cal_only_bed / "BED", shape=(64, 64), detector_mode="BED", camera_serial="CAM123"
    )
    args_data_unmapped = {
        "radiograph_npz_path": trx_r,
        "gain_npz_path": trx_g,
        "calibration_dir": str(multi_cal_only_bed),
        "expected_gain_id": "GAIN-TRX-042",
        "output_tiff_path": str(tmp_path / "out_unmapped.tiff"),
        "result_path": str(tmp_path / "result_unmapped.json"),
    }
    args_file_unmapped = tmp_path / "args_unmapped.json"
    args_file_unmapped.write_text(json.dumps(args_data_unmapped))

    with pytest.raises(SystemExit):
        execute_conversion_worker(
            str(args_file_unmapped), str(tmp_path / "result_unmapped.json")
        )

    res_unmapped = json.loads((tmp_path / "result_unmapped.json").read_text())
    assert res_unmapped["status"] == "failed"
    assert res_unmapped["sanitized_error_code"] == "NPZ_VALIDATION_ERROR"


def test_input_shape_differs_from_remap_output_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verifies that when remap map_x/map_y shape differs from input raw shape, the output canvas shape matches remap shape."""
    from mpips.conversion.worker import execute_conversion_worker
    import cv2

    cal_dir = tmp_path / "custom_remap_cal"
    cal_dir.mkdir(parents=True, exist_ok=True)

    input_shape = (64, 64)
    remap_output_shape = (48, 52)

    y_vals, x_vals = np.indices(remap_output_shape, dtype=np.float32)
    np.savez_compressed(cal_dir / "remap.npz", map_x=x_vals, map_y=y_vals)
    metadata = {
        "validated": True,
        "fingerprint": "remap-diff-test-fp",
        "image_shape": list(input_shape),
        "source_metadata": {
            "detector_mode": "BED",
            "camera_params": {"serialNumber": "CAM123"},
        },
    }
    (cal_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    rad_path, gain_path, *_ = generate_test_npzs(str(tmp_path / "npzs"))
    out_tiff = tmp_path / "out_remap_diff.tiff"
    res_path = tmp_path / "result_remap_diff.json"

    args_data = {
        "radiograph_npz_path": rad_path,
        "gain_npz_path": gain_path,
        "calibration_dir": str(cal_dir),
        "expected_gain_id": "GAIN-000042",
        "output_tiff_path": str(out_tiff),
        "result_path": str(res_path),
    }
    args_file = tmp_path / "args_remap_diff.json"
    args_file.write_text(json.dumps(args_data), encoding="utf-8")

    execute_conversion_worker(str(args_file), str(res_path))

    res = json.loads(res_path.read_text(encoding="utf-8"))
    assert res["status"] == "success"
    assert res["rows"] == remap_output_shape[0]
    assert res["cols"] == remap_output_shape[1]

    out_img = cv2.imread(str(out_tiff), cv2.IMREAD_UNCHANGED)
    assert out_img is not None
    assert out_img.shape == remap_output_shape


