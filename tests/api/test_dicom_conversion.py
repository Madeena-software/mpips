from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pydicom
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mpips.api.application import app
from mpips.api.idempotency import ClaimResult
from mpips.api.security import verify_token_payload
from mpips.conversion.metadata import format_person_name
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.npz_io import sha256_file

CONVERTER_PATH = "mpips/engine/imager_pipeline/tiff_json_to_dcm.py"
EXPECTED_HASH = "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0"

HMAC_SECRET = "test_hmac_secret_12345"


@pytest.fixture(autouse=True)
def setup_env_secrets(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("MPIPS_MANIFEST_HMAC_SECRET", HMAC_SECRET)
    monkeypatch.setenv("MPIPS_MANIFEST_MAX_CLOCK_SKEW_SECONDS", "300")


def generate_test_npzs(temp_dir: str) -> tuple[str, str, str, str, str, str]:
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
) -> dict:
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
    timestamp: str, raw_bytes: bytes, secret: str = HMAC_SECRET
) -> str:
    sig_input = timestamp.encode("utf-8") + b"." + raw_bytes
    digest = hmac.new(secret.encode("utf-8"), sig_input, hashlib.sha256).hexdigest()
    return "sha256=" + digest


# ── 1. Person Name Formatter Tests ───────────────────────────────────


def test_person_name_formatting():
    assert (
        format_person_name({"full_name": "Faliq Adlan", "family_name": "Adlan"})
        == "Adlan^Faliq"
    )
    assert (
        format_person_name({"full_name": "Andre Nasution", "family_name": "Nasution"})
        == "Nasution^Andre"
    )
    assert (
        format_person_name({"full_name": "Suharto", "family_name": None}) == "Suharto"
    )
    assert (
        format_person_name({"full_name": "Faliq Adlan", "family_name": ""})
        == "Faliq Adlan"
    )
    assert (
        format_person_name(
            {"full_name": "Faliq Adlan Subagiya", "family_name": "Adlan"}
        )
        == "Faliq Adlan Subagiya"
    )


# ── 2. Security, Scope & Signature Tests ─────────────────────────────


def test_existing_authorization_unchanged():
    client = TestClient(app)
    headers = {"Authorization": "Bearer mock_developer_token_xyz"}
    resp = client.get("/v1/nodes", headers=headers)
    assert resp.status_code == 200


def test_exact_raw_byte_hmac_sensitivity():
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)

        raw_manifest_bytes = json.dumps(manifest_dict).encode("utf-8")
        ts = str(int(time.time()))
        sig = compute_test_signature(ts, raw_manifest_bytes)

        modified_bytes = raw_manifest_bytes + b"\n"

        files = {
            "radiograph_npz": (
                "rad.npz",
                open(r_path, "rb"),
                "application/octet-stream",
            ),
            "gain_npz": ("gain.npz", open(g_path, "rb"), "application/octet-stream"),
            "manifest": ("manifest.json", modified_bytes, "application/json"),
        }
        headers = {
            "Authorization": "Bearer mock_developer_token_xyz",
            "X-Madeena-Manifest-Timestamp": ts,
            "X-Madeena-Manifest-Signature": sig,
        }

        token_mock = {
            "sub": "dev",
            "scope": "image:convert",
            "tenant_id": "test-tenant",
        }
        with patch(
            "mpips.api.manifest_security.verify_token_payload", return_value=token_mock
        ):
            resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
            assert resp.status_code == 401
            assert "Invalid manifest signature" in resp.json()["detail"]


def test_scope_enforcement():
    client = TestClient(app)

    ts = str(int(time.time()))
    sig = compute_test_signature(ts, b"{}")
    headers = {
        "Authorization": "Bearer mock_developer_token_xyz",
        "X-Madeena-Manifest-Timestamp": ts,
        "X-Madeena-Manifest-Signature": sig,
    }
    files = {
        "radiograph_npz": ("rad.npz", b"dummy", "application/octet-stream"),
        "gain_npz": ("gain.npz", b"dummy", "application/octet-stream"),
        "manifest": ("manifest.json", b"{}", "application/json"),
    }

    mock_token = {"sub": "dev", "scope": "nodes:read", "tenant_id": "test-tenant"}
    app.dependency_overrides[verify_token_payload] = lambda: mock_token
    try:
        resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
        assert resp.status_code == 403
        assert "image:convert" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_tenant_id_missing_in_token():
    client = TestClient(app)
    headers = {"Authorization": "Bearer mock_developer_token_xyz"}
    files = {
        "radiograph_npz": ("rad.npz", b"dummy", "application/octet-stream"),
        "gain_npz": ("gain.npz", b"dummy", "application/octet-stream"),
        "manifest": ("manifest.json", b"{}", "application/json"),
    }

    app.dependency_overrides[verify_token_payload] = lambda: {
        "sub": "dev",
        "scope": "image:convert",
    }
    try:
        resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
        assert resp.status_code == 401
        assert "tenant_id" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_timestamp_skew_rejection():
    client = TestClient(app)
    ts = str(int(time.time()) - 600)
    sig = compute_test_signature(ts, b"{}")
    headers = {
        "Authorization": "Bearer mock_developer_token_xyz",
        "X-Madeena-Manifest-Timestamp": ts,
        "X-Madeena-Manifest-Signature": sig,
    }
    files = {
        "radiograph_npz": ("rad.npz", b"dummy", "application/octet-stream"),
        "gain_npz": ("gain.npz", b"dummy", "application/octet-stream"),
        "manifest": ("manifest.json", b"{}", "application/json"),
    }

    token_mock = {"sub": "dev", "scope": "image:convert", "tenant_id": "test-tenant"}
    with patch(
        "mpips.api.manifest_security.verify_token_payload", return_value=token_mock
    ):
        resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
        assert resp.status_code == 401
        assert "timestamp is expired or skewed" in resp.json()["detail"]


# ── 3. Schema & Validation Tests ──────────────────────────────────────


def test_strict_manifest_schema_rejection():
    client = TestClient(app)
    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        manifest_dict["unknown_field"] = "illegal"

        raw_bytes = json.dumps(manifest_dict).encode("utf-8")
        ts = str(int(time.time()))
        sig = compute_test_signature(ts, raw_bytes)

        files = {
            "radiograph_npz": (
                "rad.npz",
                open(r_path, "rb"),
                "application/octet-stream",
            ),
            "gain_npz": ("gain.npz", open(g_path, "rb"), "application/octet-stream"),
            "manifest": ("manifest.json", raw_bytes, "application/json"),
        }
        headers = {
            "Authorization": "Bearer mock_developer_token_xyz",
            "X-Madeena-Manifest-Timestamp": ts,
            "X-Madeena-Manifest-Signature": sig,
        }

        token_mock = {
            "sub": "dev",
            "scope": "image:convert",
            "tenant_id": "test-tenant",
        }
        with patch(
            "mpips.api.manifest_security.verify_token_payload", return_value=token_mock
        ):
            resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
            assert resp.status_code == 422
            assert "Invalid manifest JSON or schema" in resp.json()["detail"]


def test_hash_and_size_mismatch_rejection():
    client = TestClient(app)
    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        manifest_dict["capture"]["radiograph"]["sha256"] = "0" * 64

        raw_bytes = json.dumps(manifest_dict).encode("utf-8")
        ts = str(int(time.time()))
        sig = compute_test_signature(ts, raw_bytes)

        files = {
            "radiograph_npz": (
                "rad.npz",
                open(r_path, "rb"),
                "application/octet-stream",
            ),
            "gain_npz": ("gain.npz", open(g_path, "rb"), "application/octet-stream"),
            "manifest": ("manifest.json", raw_bytes, "application/json"),
        }
        headers = {
            "Authorization": "Bearer mock_developer_token_xyz",
            "X-Madeena-Manifest-Timestamp": ts,
            "X-Madeena-Manifest-Signature": sig,
        }

        token_mock = {
            "sub": "dev",
            "scope": "image:convert",
            "tenant_id": "test-tenant",
        }
        with patch(
            "mpips.api.manifest_security.verify_token_payload", return_value=token_mock
        ):
            resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
            assert resp.status_code == 422
            assert "mismatch" in resp.json()["detail"]


# ── 4. Converter Immutability & End-to-End Execution ──────────────────


def test_converter_immutability():
    current_hash = sha256_file(CONVERTER_PATH)
    assert current_hash == EXPECTED_HASH, "Pak Andre's converter was modified!"
    assert callable(tiff_json_to_dcm)


def test_successful_dicom_conversion_endpoint():
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        raw_manifest_bytes = json.dumps(manifest_dict).encode("utf-8")

        ts = str(int(time.time()))
        sig = compute_test_signature(ts, raw_manifest_bytes)

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
            "scope": "image:convert",
            "tenant_id": "test-tenant",
        }

        with (
            patch(
                "mpips.api.manifest_security.verify_token_payload",
                return_value=token_mock,
            ),
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
            assert (
                resp.headers["X-Correlation-ID"]
                == "29722404-a494-46ca-960b-537255d37982"
            )
            assert (
                resp.headers["X-Conversion-Job-ID"]
                == "97eeb9ef-d93c-43e7-aebe-c9ada5cc29fa"
            )

            dcm_bytes = resp.content
            ds = pydicom.dcmread(pydicom.filebase.BytesIO(dcm_bytes))

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


def test_idempotency_conflict_endpoint():
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        raw_manifest_bytes = json.dumps(manifest_dict).encode("utf-8")

        ts = str(int(time.time()))
        sig = compute_test_signature(ts, raw_manifest_bytes)

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

        mock_claim = ClaimResult(status="SUCCEEDED_DIFF")
        token_mock = {
            "sub": "dev",
            "scope": "image:convert",
            "tenant_id": "test-tenant",
        }

        with (
            patch(
                "mpips.api.manifest_security.verify_token_payload",
                return_value=token_mock,
            ),
            patch(
                "mpips.api.routes.v1.dicom.IdempotencyService.claim_job",
                return_value=mock_claim,
            ),
        ):

            resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
            assert resp.status_code == 409
            assert "Idempotency conflict" in resp.json()["detail"]


def test_redis_down_failure():
    client = TestClient(app)
    with tempfile.TemporaryDirectory() as temp_dir:
        r_path, g_path, r_sha, g_sha, r_sz, g_sz = generate_test_npzs(temp_dir)
        manifest_dict = make_test_manifest(r_sha, g_sha, r_sz, g_sz)
        raw_manifest_bytes = json.dumps(manifest_dict).encode("utf-8")

        ts = str(int(time.time()))
        sig = compute_test_signature(ts, raw_manifest_bytes)

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

        token_mock = {
            "sub": "dev",
            "scope": "image:convert",
            "tenant_id": "test-tenant",
        }
        redis_err = HTTPException(
            status_code=503, detail="Idempotency storage service unavailable"
        )
        with (
            patch(
                "mpips.api.manifest_security.verify_token_payload",
                return_value=token_mock,
            ),
            patch(
                "mpips.api.routes.v1.dicom.IdempotencyService.claim_job",
                side_effect=redis_err,
            ),
        ):

            resp = client.post("/v1/radiographs/dicom", files=files, headers=headers)
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["detail"]


def test_no_nik_in_openapi():
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi_str = resp.text.lower()
    assert '"nik"' not in openapi_str
