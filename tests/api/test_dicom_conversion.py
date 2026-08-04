from __future__ import annotations

import io
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import numpy as np
import pydicom
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mpips.api.application import app, _validate_production_configuration
from mpips.api.idempotency import ClaimResult
from mpips.api.manifest_security import (
    canonicalize_tenant_id,
    compute_manifest_signature_digest,
)
from mpips.api.security import verify_token_payload
from mpips.conversion.service import _validate_tiff_descriptor
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.npz_io import sha256_file, write_tiff

CONVERTER_PATH = "mpips/engine/imager_pipeline/tiff_json_to_dcm.py"
EXPECTED_HASH = "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0"
HMAC_SECRET = "c8e73f91d0a5491fb3421e89b70c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c"


@pytest.fixture(autouse=True)
def setup_env_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("MPIPS_MANIFEST_HMAC_SECRET", HMAC_SECRET)
    monkeypatch.setenv("MPIPS_MANIFEST_MAX_CLOCK_SKEW_SECONDS", "300")


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


def compute_test_signature(
    tenant_id: str, timestamp: str, raw_bytes: bytes, secret: str = HMAC_SECRET
) -> str:
    canonical_tenant = canonicalize_tenant_id(tenant_id)
    digest = compute_manifest_signature_digest(
        secret, canonical_tenant, timestamp, raw_bytes
    )
    return "sha256=" + digest


# ── 1. Tenant Canonicalization & HMAC Tests ──────────────────────────


def test_tenant_canonicalization() -> None:
    uuid_str = "c41c449e-2f28-42c8-a0ed-0832265dd6c1"
    assert canonicalize_tenant_id(uuid_str) == uuid_str
    assert canonicalize_tenant_id(uuid_str.upper()) == uuid_str
    assert canonicalize_tenant_id("tenant-123") == "tenant-123"

    with pytest.raises(HTTPException) as exc1:
        canonicalize_tenant_id(" tenant-123 ")
    assert exc1.value.status_code == 401

    with pytest.raises(HTTPException) as exc2:
        canonicalize_tenant_id("tenant.123")
    assert exc2.value.status_code == 401


# ── 2. TOCTOU-Safe Parent TIFF Descriptor Validation Tests ───────────


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


# ── 3. Converter Immutability & Basic Tests ──────────────────────────


def test_converter_immutability() -> None:
    current_hash = sha256_file(CONVERTER_PATH)
    assert current_hash == EXPECTED_HASH, "Pak Andre's converter was modified!"
    assert callable(tiff_json_to_dcm)


# ── 4. End-to-End Successful Conversion Endpoint Test ────────────────


def test_successful_dicom_conversion_endpoint() -> None:
    client = TestClient(app)
    tenant_id = "test-tenant-123"

    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        raw_manifest_bytes = json.dumps(manifest_dict).encode("utf-8")

        ts = str(int(time.time()))
        sig = compute_test_signature(tenant_id, ts, raw_manifest_bytes)

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
            "Authorization": "Bearer mock_developer_token_xyz",
            "X-Madeena-Manifest-Timestamp": ts,
            "X-Madeena-Manifest-Signature": sig,
        }

        mock_claim = ClaimResult(status="CLAIMED", lease_token="lease_123")
        token_mock = {
            "sub": "dev",
            "iss": "https://sso.madeena.com",
            "aud": "https://api.madeena.com",
            "exp": int(time.time()) + 3600,
            "scope": "image:convert",
            "tenant_id": tenant_id,
        }

        app.dependency_overrides[verify_token_payload] = lambda: token_mock
        try:
            with (
                patch(
                    "mpips.api.routes.v1.dicom.IdempotencyService.claim_job",
                    return_value=mock_claim,
                ),
                patch(
                    "mpips.api.routes.v1.dicom.IdempotencyService.mark_success"
                ) as mock_mark_success,
            ):

                resp = client.post(
                    "/v1/radiographs/dicom", files=files, headers=headers
                )
                assert resp.status_code == 200, f"Error: {resp.text}"
                assert resp.headers["Content-Type"] == "application/dicom"
                assert "Content-Disposition" in resp.headers
                assert (
                    resp.headers["X-Correlation-ID"]
                    == "29722404-a494-46ca-960b-537255d37982"
                )
                assert (
                    resp.headers["X-Conversion-Job-ID"]
                    == "97eeb9ef-d93c-43e7-aebe-c9ada5cc29fa"
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
        finally:
            app.dependency_overrides.clear()


# ── 5. Production Startup Configuration Validation Tests ─────────────


def test_production_startup_validation_refuses_dev_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    with pytest.raises(RuntimeError) as exc:
        _validate_production_configuration()
    assert "DEV_AUTH_BYPASS" in str(exc.value)


def test_production_startup_validation_refuses_placeholder_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("MPIPS_MANIFEST_HMAC_SECRET", "replace-with-secret")
    with pytest.raises(RuntimeError) as exc:
        _validate_production_configuration()
    assert "MPIPS_MANIFEST_HMAC_SECRET" in str(exc.value)


def test_production_startup_validation_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("MPIPS_MANIFEST_HMAC_SECRET", HMAC_SECRET)
    monkeypatch.setenv("MADEENA_IDP_JWKS_URL", "https://sso.madeena.com/jwks.json")
    monkeypatch.setenv("MADEENA_IDP_ISSUER", "https://sso.madeena.com")
    monkeypatch.setenv("MADEENA_IDP_AUDIENCE", "https://api.madeena.com")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    # Should pass without raising
    _validate_production_configuration()


# ── 6. OpenAPI Privacy Audit Test ────────────────────────────────────


def test_no_nik_in_openapi() -> None:
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi_str = resp.text.lower()
    assert '"nik"' not in openapi_str
