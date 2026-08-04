#!/usr/bin/env python3
"""Synthetic local MPIPS DICOM smoke, abuse, and isolation checks."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import hmac
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import httpx
import jwt
import numpy as np
import pydicom
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from pydicom.uid import ExplicitVRLittleEndian

from mpips.api.schemas.dicom import MHCSManifest
from mpips.api.manifest_security import verify_manifest_signature
from mpips.conversion.validation import validate_dicom_dataset

ISSUER = "https://local.test/issuer"
AUDIENCE = "https://local.test/api"
DEFAULT_TENANT = "synthetic-tenant-a"
OTHER_TENANT = "synthetic-tenant-b"
RAD_ID = "SYNTH-RAD-001"
GAIN_ID = "SYNTH-GAIN-001"
CAMERA = "SYNTH-CAMERA-001"
SHAPE = (64, 64)
BASE_JOB_ID = "00000000-0000-4000-8000-000000000001"


def _b64(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: dict[str, Any], *, pretty: bool = False) -> bytes:
    if pretty:
        return json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _signature(secret: str, tenant: str, timestamp: str, raw: bytes) -> str:
    message = (
        b"mpips-manifest-v1\x00"
        + tenant.encode()
        + b"\x00"
        + timestamp.encode()
        + b"\x00"
        + raw
    )
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _uuid() -> str:
    return str(uuid4())


def _npz_bytes(
    *,
    radiograph: bool,
    shape: tuple[int, int] = SHAPE,
    raw_dtype: np.dtype[Any] = np.dtype(np.uint16),
    raw_value: int = 1000,
    gain_id: str = GAIN_ID,
    detector_mode: str = "BED",
    camera: str = CAMERA,
    missing: Iterable[str] = (),
    object_raw: bool = False,
) -> bytes:
    missing_set = set(missing)
    raw = np.full(shape, raw_value, dtype=raw_dtype)
    if object_raw:
        raw = np.full(shape, raw_value, dtype=object)

    values: dict[str, Any] = {}
    if radiograph:
        values = {
            "id": np.array(RAD_ID),
            "gainid": np.array(gain_id),
            "rawimage": raw,
            "xrayparams": np.array({"detectorMode": detector_mode}, dtype=object),
            "cameraparams": np.array({"serialNumber": camera}, dtype=object),
        }
    else:
        values = {
            "id": np.array(gain_id),
            "rawimage": np.full(shape, 2000, dtype=np.uint16),
            "darkimage": np.full(shape, 50, dtype=np.uint16),
            "xrayparams": np.array({"detectorMode": detector_mode}, dtype=object),
            "cameraparams": np.array({"serialNumber": camera}, dtype=object),
        }
    for key in missing_set:
        values.pop(key, None)

    output = BytesIO()
    np.savez_compressed(output, **values)
    return output.getvalue()


def _manifest_template() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "conversion_job_id": BASE_JOB_ID,
        "submission_id": "00000000-0000-4000-8000-000000000002",
        "correlation_id": "00000000-0000-4000-8000-000000000003",
        "examination": {
            "examination_id": "SYNTH-EXAM-001",
            "booking_id": "SYNTH-BOOK-001",
            "service_request_id": "SYNTH-REQUEST-001",
            "encounter_id": "SYNTH-ENCOUNTER-001",
            "accession_number": "SYNTHACC001",
            "study_id": "SYNTHSTUDY001",
            "performed_at": "2026-08-05T10:00:00+00:00",
            "study_description": "Synthetic Chest Radiography",
            "protocol_name": "Synthetic Chest PA",
        },
        "patient": {
            "member_id": "00000000-0000-4000-8000-000000000004",
            "medical_record_number": "SYNTHETIC-MRN-001",
            "name": {"full_name": "Synthetic Patient", "family_name": "Patient"},
            "sex": "unknown",
            "birth_date": "2000-01-01",
        },
        "operator": {
            "operator_id": "00000000-0000-4000-8000-000000000005",
            "name": {"full_name": "Synthetic Operator", "family_name": "Operator"},
        },
        "site": {
            "organization_id": "SYNTH-ORG-001",
            "site_id": "SYNTH-SITE-001",
            "institution_name": "Synthetic Local Test Site",
            "department_name": "Synthetic Radiology",
            "station_name": "SYNTH-STATION-001",
            "timezone": "UTC",
        },
        "capture": {
            "capture_id": "SYNTH-CAPTURE-001",
            "protocol_version": "SYNTH-V1",
            "body_part_examined": "CHEST",
            "laterality": "U",
            "projection": "PA",
            "captured_at": "2026-08-05T10:00:00+00:00",
            "radiograph": {"filename": "synthetic-radiograph.npz"},
            "gain": {"filename": "synthetic-gain.npz", "gain_id": GAIN_ID},
            "image_spacing": {"row_um": 140.0, "column_um": 140.0},
        },
        "dicom": {
            "study_instance_uid": "1.2.826.0.1.3680043.10.1356.20260805.1",
            "series_instance_uid": "1.2.826.0.1.3680043.10.1356.20260805.2",
            "sop_instance_uid": "1.2.826.0.1.3680043.10.1356.20260805.3",
            "series_number": 1,
            "instance_number": 1,
            "series_description": "Synthetic Chest PA",
            "presentation_intent": "FOR PRESENTATION",
        },
    }


def _with_files(
    template: dict[str, Any],
    radiograph: bytes,
    gain: bytes,
    *,
    job_id: str | None = None,
    changes: dict[str, Any] | None = None,
) -> bytes:
    manifest = copy.deepcopy(template)
    manifest["conversion_job_id"] = job_id or _uuid()
    manifest["capture"]["radiograph"].update(
        {"byte_size": len(radiograph), "sha256": _sha(radiograph)}
    )
    manifest["capture"]["gain"].update({"byte_size": len(gain), "sha256": _sha(gain)})
    if changes:
        for path, value in changes.items():
            target: dict[str, Any] = manifest
            parts = path.split(".")
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
    return _json_bytes(manifest)


def _key_paths(base: Path) -> tuple[Path, Path]:
    return base / "private.pem", base / "jwks" / "jwks.json"


def prepare(base: Path, secret: str) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for name in ("fixtures", "calibration", "jwks", "results"):
        (base / name).mkdir(exist_ok=True)

    private_path, jwks_path = _key_paths(base)
    private_key: Any
    if not private_path.exists():
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        private_path.chmod(0o600)
    else:
        private_key = serialization.load_pem_private_key(
            private_path.read_bytes(), password=None
        )
    public = private_key.public_key().public_numbers()
    jwks_path.write_text(
        json.dumps(
            {
                "keys": [
                    {
                        "kty": "RSA",
                        "kid": "local-burn-in",
                        "use": "sig",
                        "alg": "RS256",
                        "n": _b64(public.n),
                        "e": _b64(public.e),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    radiograph = _npz_bytes(radiograph=True)
    gain = _npz_bytes(radiograph=False)
    fixture_dir = base / "fixtures"
    (fixture_dir / "radiograph.npz").write_bytes(radiograph)
    (fixture_dir / "gain.npz").write_bytes(gain)
    template = _manifest_template()
    raw_manifest = _with_files(template, radiograph, gain, job_id=BASE_JOB_ID)
    timestamp = str(int(time.time()))
    (fixture_dir / "manifest.json").write_bytes(raw_manifest)
    (fixture_dir / "manifest.headers.json").write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "signature": (
                    "sha256="
                    + _signature(secret, DEFAULT_TENANT, timestamp, raw_manifest)
                ),
            }
        ),
        encoding="utf-8",
    )

    y_values, x_values = np.indices(SHAPE, dtype=np.float32)
    np.savez_compressed(
        base / "calibration" / "remap.npz", map_x=x_values, map_y=y_values
    )
    (base / "calibration" / "metadata.json").write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "synthetic-local-calibration-v1",
                "image_shape": list(SHAPE),
                "source_metadata": {
                    "detector_mode": "BED",
                    "camera_params": {"serialNumber": CAMERA},
                },
            }
        ),
        encoding="utf-8",
    )


def _load_private_key(base: Path) -> Any:
    return serialization.load_pem_private_key(
        (base / "private.pem").read_bytes(), password=None
    )


def _token(
    private_key: Any,
    *,
    tenant: str | None = DEFAULT_TENANT,
    scopes: list[str] | None = None,
    expiry: int | None = None,
) -> str:
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "synthetic-local-client",
        "scope": " ".join(scopes or ["image:process", "nodes:read", "image:convert"]),
        "exp": expiry or int(time.time()) + 300,
    }
    if tenant is not None:
        payload["tenant_id"] = tenant
    return str(
        jwt.encode(
            payload, private_key, algorithm="RS256", headers={"kid": "local-burn-in"}
        )
    )


def _headers(
    raw: bytes,
    secret: str,
    tenant: str = DEFAULT_TENANT,
    *,
    timestamp: str | None = None,
    signature_secret: str | None = None,
) -> dict[str, str]:
    stamp = timestamp or str(int(time.time()))
    return {
        "X-Madeena-Manifest-Timestamp": stamp,
        "X-Madeena-Manifest-Signature": (
            f"sha256={_signature(signature_secret or secret, tenant, stamp, raw)}"
        ),
    }


def _files(
    raw: bytes,
    radiograph: bytes,
    gain: bytes,
    *,
    names: tuple[str, str, str] = (
        "synthetic-radiograph.npz",
        "synthetic-gain.npz",
        "manifest.json",
    ),
    include: tuple[str, ...] = ("radiograph_npz", "gain_npz", "manifest"),
    duplicate_radiograph: bool = False,
) -> list[tuple[str, tuple[str, bytes, str]]]:
    entries: list[tuple[str, tuple[str, bytes, str]]] = []
    values = {
        "radiograph_npz": (names[0], radiograph, "application/octet-stream"),
        "gain_npz": (names[1], gain, "application/octet-stream"),
        "manifest": (names[2], raw, "application/json"),
    }
    for key in include:
        entries.append((key, values[key]))
        if key == "radiograph_npz" and duplicate_radiograph:
            entries.append((key, values[key]))
    return entries


def _detail(response: httpx.Response) -> str:
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            detail = response.json().get("detail", "")
            return str(detail)[:80]
        except (ValueError, TypeError):
            return "invalid-json"
    return "dicom" if response.status_code == 200 else "non-json"


class BurnIn:
    def __init__(self, base: Path, url: str, secret: str) -> None:
        self.base = base
        self.url = url.rstrip("/")
        self.secret = secret
        self.template = _manifest_template()
        self.private_key = _load_private_key(base)
        self.radiograph = (base / "fixtures" / "radiograph.npz").read_bytes()
        self.gain = (base / "fixtures" / "gain.npz").read_bytes()
        self.raw_manifest = (base / "fixtures" / "manifest.json").read_bytes()
        self.failures: list[str] = []
        self.case_count = 0
        self.client = httpx.Client(timeout=45.0, follow_redirects=False)

    def close(self) -> None:
        self.client.close()

    def request(
        self,
        raw: bytes,
        radiograph: bytes,
        gain: bytes,
        *,
        token: str | None = None,
        manifest_tenant: str = DEFAULT_TENANT,
        request_headers: dict[str, str] | None = None,
        names: tuple[str, str, str] = (
            "synthetic-radiograph.npz",
            "synthetic-gain.npz",
            "manifest.json",
        ),
        include: tuple[str, ...] = ("radiograph_npz", "gain_npz", "manifest"),
        duplicate_radiograph: bool = False,
        client: httpx.Client | None = None,
    ) -> httpx.Response:
        headers = _headers(raw, self.secret, manifest_tenant)
        if request_headers:
            headers.update(request_headers)
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        request_client = client or self.client
        return request_client.post(
            f"{self.url}/v1/radiographs/dicom",
            headers=headers,
            files=_files(
                raw,
                radiograph,
                gain,
                names=names,
                include=include,
                duplicate_radiograph=duplicate_radiograph,
            ),
        )

    def case(
        self,
        name: str,
        expected: int | set[int],
        response: httpx.Response,
        *,
        save_as: Path | None = None,
    ) -> httpx.Response:
        expected_set = {expected} if isinstance(expected, int) else expected
        self.case_count += 1
        status = response.status_code
        detail = _detail(response)
        print(f"{name}: {status} {_content_type(response)} {detail}")
        if status not in expected_set:
            self.failures.append(
                f"{name}: expected {sorted(expected_set)}, got {status}"
            )
        if save_as is not None and status == 200:
            save_as.write_bytes(response.content)
        return response

    def signed_case(
        self,
        name: str,
        expected: int | set[int],
        *,
        radiograph: bytes | None = None,
        gain: bytes | None = None,
        job_id: str | None = None,
        tenant: str = DEFAULT_TENANT,
        token: str | None = None,
        changes: dict[str, Any] | None = None,
        raw: bytes | None = None,
        request_headers: dict[str, str] | None = None,
        signature_secret: str | None = None,
        timestamp: str | None = None,
        include_authorization: bool = True,
        names: tuple[str, str, str] = (
            "synthetic-radiograph.npz",
            "synthetic-gain.npz",
            "manifest.json",
        ),
        include: tuple[str, ...] = ("radiograph_npz", "gain_npz", "manifest"),
        duplicate_radiograph: bool = False,
    ) -> httpx.Response:
        rad = self.radiograph if radiograph is None else radiograph
        g = self.gain if gain is None else gain
        body = raw or _with_files(self.template, rad, g, job_id=job_id, changes=changes)
        headers = _headers(
            body,
            self.secret,
            tenant,
            timestamp=timestamp,
            signature_secret=signature_secret,
        )
        if request_headers:
            headers.update(request_headers)
        request_token: str | None = token or _token(self.private_key, tenant=tenant)
        if not include_authorization:
            request_token = None
        response = self.request(
            body,
            rad,
            g,
            token=request_token,
            manifest_tenant=tenant,
            request_headers=headers,
            names=names,
            include=include,
            duplicate_radiograph=duplicate_radiograph,
        )
        return self.case(name, expected, response)

    def run(self) -> None:
        token = _token(self.private_key)
        health = self.client.get(f"{self.url}/health")
        self.case("health", 200, health)

        for path in (
            "/",
            "/v1/nodes",
            "/v1/jobs",
            "/v1/secure-test",
            "/docs",
            "/redoc",
            "/openapi.json",
        ):
            self.case(f"private {path}", 404, self.client.get(f"{self.url}{path}"))

        valid_raw = self.raw_manifest
        valid_headers = _headers(valid_raw, self.secret)
        valid_response = self.request(
            valid_raw,
            self.radiograph,
            self.gain,
            token=token,
            request_headers=valid_headers,
        )
        self.case(
            "valid conversion",
            200,
            valid_response,
            save_as=self.base / "results" / "valid.dcm",
        )
        if valid_response.status_code == 200:
            self.validate_dicom(self.base / "results" / "valid.dcm", valid_raw)

        self.authentication_cases(token)
        self.manifest_cases(token)
        self.upload_cases(token)
        self.npz_cases(token)
        self.calibration_cases(token)
        self.idempotency_cases(token)
        self.resilience_cases(token)
        self.launcher_cases()

        if self.failures:
            raise RuntimeError("; ".join(self.failures))
        print(f"burn-in passed: {self.case_count} HTTP cases")

    def validate_dicom(self, path: Path, raw_manifest: bytes) -> None:
        manifest = MHCSManifest.model_validate_json(raw_manifest)
        dataset = pydicom.dcmread(path)
        assert dataset.file_meta.TransferSyntaxUID == ExplicitVRLittleEndian
        assert dataset.SOPInstanceUID == manifest.dicom.sop_instance_uid
        assert dataset.StudyInstanceUID == manifest.dicom.study_instance_uid
        assert dataset.SeriesInstanceUID == manifest.dicom.series_instance_uid
        assert dataset.PatientID == manifest.patient.medical_record_number
        assert dataset.PatientName == "Patient^Synthetic"
        assert dataset.Rows == SHAPE[0] and dataset.Columns == SHAPE[1]
        assert dataset.BitsAllocated == 16 and dataset.PixelRepresentation == 0
        assert dataset.BurnedInAnnotation == "NO"
        assert dataset.LossyImageCompression == "00"
        assert dataset.pixel_array.dtype == np.uint16
        assert dataset.pixel_array.size > 0
        assert not any(element.tag.is_private for element in dataset.iterall())
        validation = validate_dicom_dataset(path, manifest, SHAPE)
        assert validation.get("valid") is True
        print(
            "valid DICOM: parsed, validated, explicit-vr-little-endian, "
            "64x64 uint16, no private tags"
        )

    def authentication_cases(self, valid_token: str) -> None:
        self.signed_case("auth missing header", 401, include_authorization=False)
        self.signed_case(
            "auth malformed bearer",
            {401, 403},
            include_authorization=False,
            request_headers={"Authorization": "Basic local"},
        )
        self.signed_case("auth wrong token", 401, token="not-a-jwt")
        invalid = valid_token[:-1] + ("A" if valid_token[-1] != "A" else "B")
        self.signed_case("auth invalid JWT signature", 401, token=invalid)
        self.signed_case(
            "auth missing image convert",
            403,
            token=_token(self.private_key, scopes=["image:process", "nodes:read"]),
        )
        self.signed_case(
            "auth missing tenant",
            401,
            token=_token(self.private_key, tenant=None),
        )
        self.signed_case(
            "auth malformed tenant",
            401,
            tenant="bad tenant",
            token=_token(self.private_key, tenant="bad tenant"),
        )
        self.signed_case(
            "auth tenant/signature mismatch",
            401,
            tenant=OTHER_TENANT,
            token=_token(self.private_key, tenant=DEFAULT_TENANT),
        )

    def manifest_cases(self, token: str) -> None:
        now = str(int(time.time()))
        cases: list[tuple[str, int | set[int], dict[str, str]]] = [
            (
                "manifest missing timestamp",
                {400, 401},
                {"X-Madeena-Manifest-Timestamp": ""},
            ),
            (
                "manifest nonnumeric timestamp",
                400,
                {"X-Madeena-Manifest-Timestamp": "abc"},
            ),
            (
                "manifest stale timestamp",
                401,
                {"X-Madeena-Manifest-Timestamp": str(int(now) - 3600)},
            ),
            (
                "manifest future timestamp",
                401,
                {"X-Madeena-Manifest-Timestamp": str(int(now) + 3600)},
            ),
            ("manifest missing signature", 400, {"X-Madeena-Manifest-Signature": ""}),
            (
                "manifest malformed signature prefix",
                400,
                {"X-Madeena-Manifest-Signature": "hmac=bad"},
            ),
            (
                "manifest wrong signature length",
                400,
                {"X-Madeena-Manifest-Signature": "sha256=00"},
            ),
        ]
        for name, expected, headers in cases:
            self.signed_case(name, expected, token=token, request_headers=headers)
        self.signed_case(
            "manifest wrong HMAC",
            401,
            token=token,
            signature_secret="wrong-local-secret",
        )
        modified_headers = _headers(self.raw_manifest, self.secret)
        self.case(
            "manifest modified after signing",
            401,
            self.request(
                self.raw_manifest + b" ",
                self.radiograph,
                self.gain,
                token=token,
                request_headers=modified_headers,
            ),
        )
        previous_secret = os.environ.get("MPIPS_MANIFEST_HMAC_SECRET")
        os.environ["MPIPS_MANIFEST_HMAC_SECRET"] = self.secret
        try:
            try:
                verify_manifest_signature(
                    DEFAULT_TENANT,
                    self.raw_manifest,
                    f" {now} ",
                    _headers(self.raw_manifest, self.secret)[
                        "X-Madeena-Manifest-Signature"
                    ],
                )
            except HTTPException as exc:
                print(f"manifest whitespace timestamp direct check: {exc.status_code}")
                if exc.status_code != 400:
                    self.failures.append(
                        "manifest whitespace timestamp expected 400, "
                        f"got {exc.status_code}"
                    )
            else:
                self.failures.append("manifest whitespace timestamp was accepted")
        finally:
            if previous_secret is None:
                os.environ.pop("MPIPS_MANIFEST_HMAC_SECRET", None)
            else:
                os.environ["MPIPS_MANIFEST_HMAC_SECRET"] = previous_secret
        pretty = _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
        self.signed_case(
            "manifest valid alternate whitespace", 200, token=token, raw=pretty
        )

    def upload_cases(self, token: str) -> None:
        self.signed_case(
            "upload missing radiograph",
            422,
            token=token,
            include=("gain_npz", "manifest"),
        )
        self.signed_case(
            "upload missing gain",
            422,
            token=token,
            include=("radiograph_npz", "manifest"),
        )
        self.signed_case(
            "upload missing manifest",
            422,
            token=token,
            include=("radiograph_npz", "gain_npz"),
        )
        response = self.client.post(
            f"{self.url}/v1/radiographs/dicom",
            content=b"not multipart",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        self.case("upload wrong content type", {400, 415, 422}, response)
        empty_raw = _with_files(
            self.template, self.radiograph, self.gain, job_id=_uuid()
        )
        self.signed_case(
            "upload empty files",
            422,
            token=token,
            radiograph=b"",
            gain=b"",
            raw=empty_raw,
        )
        self.signed_case(
            "upload truncated NPZ", 422, token=token, radiograph=self.radiograph[:16]
        )
        self.signed_case("upload malformed JSON", 422, token=token, raw=b"{}")
        self.signed_case(
            "upload manifest above limit", 413, token=token, raw=b"{" + b" " * 32768
        )
        self.signed_case(
            "upload radiograph above limit", 413, token=token, radiograph=b"x" * 700001
        )
        self.signed_case(
            "upload gain above limit", 413, token=token, gain=b"x" * 700001
        )
        self.signed_case(
            "upload combined body above limit",
            413,
            token=token,
            radiograph=b"x" * 600000,
            gain=b"x" * 600000,
        )
        self.signed_case(
            "upload suspicious filename is contained",
            200,
            token=token,
            names=(
                "../../synthetic-radiograph.npz",
                "..\\synthetic-gain.npz",
                "../../manifest.json",
            ),
        )
        self.signed_case(
            "upload duplicate form parts are controlled",
            {200, 400, 422},
            token=token,
            duplicate_radiograph=True,
        )

    def npz_cases(self, token: str) -> None:
        missing_rad = _npz_bytes(radiograph=True, missing=("rawimage",))
        self.signed_case(
            "npz radiograph missing key", 422, token=token, radiograph=missing_rad
        )
        missing_gain = _npz_bytes(radiograph=False, missing=("darkimage",))
        self.signed_case("npz gain missing key", 422, token=token, gain=missing_gain)
        bad_gain_id = _npz_bytes(radiograph=False, gain_id="SYNTH-GAIN-WRONG")
        self.signed_case("npz gain id mismatch", 422, token=token, gain=bad_gain_id)
        small_rad = _npz_bytes(radiograph=True, shape=(32, 32))
        self.signed_case(
            "npz image shape mismatch", 422, token=token, radiograph=small_rad
        )
        bad_dtype = _npz_bytes(
            radiograph=True, raw_dtype=np.dtype(np.uint32), raw_value=70000
        )
        self.signed_case(
            "npz unsupported dtype/range", 422, token=token, radiograph=bad_dtype
        )
        object_array = _npz_bytes(radiograph=True, object_raw=True)
        self.signed_case(
            "npz object array rejected", 422, token=token, radiograph=object_array
        )
        detector_mismatch = _npz_bytes(radiograph=True, detector_mode="TRX")
        self.signed_case(
            "npz detector mismatch", 422, token=token, radiograph=detector_mismatch
        )
        camera_mismatch = _npz_bytes(radiograph=True, camera="SYNTH-CAMERA-WRONG")
        self.signed_case(
            "npz camera serial mismatch", 422, token=token, radiograph=camera_mismatch
        )

    def calibration_cases(self, token: str) -> None:
        cal_dir = self.base / "calibration"
        metadata_path = cal_dir / "metadata.json"
        remap_path = cal_dir / "remap.npz"
        metadata = metadata_path.read_bytes()
        remap = remap_path.read_bytes()
        try:
            metadata_path.unlink()
            self.signed_case("calibration missing", 422, token=token)
            metadata_path.write_bytes(metadata)
            metadata_path.write_text(
                metadata.decode().replace("true", "false"), encoding="utf-8"
            )
            self.signed_case("calibration unvalidated", 422, token=token)
            metadata_path.write_bytes(metadata)
            np.savez_compressed(
                remap_path,
                map_x=np.zeros((32, 32), dtype=np.float32),
                map_y=np.zeros((32, 32), dtype=np.float32),
            )
            self.signed_case("calibration remap shape mismatch", 422, token=token)
        finally:
            metadata_path.write_bytes(metadata)
            remap_path.write_bytes(remap)

    def idempotency_cases(self, token: str) -> None:
        raw = _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
        first = self.case(
            "idempotency first claim",
            200,
            self.request(raw, self.radiograph, self.gain, token=token),
        )
        if first.status_code == 200:
            self.case(
                "idempotency identical completed replay",
                200,
                self.request(raw, self.radiograph, self.gain, token=token),
            )
        conflict_raw = _with_files(
            self.template,
            self.radiograph,
            self.gain,
            job_id=json.loads(raw)["conversion_job_id"],
            changes={"examination.study_description": "Synthetic Conflict Study"},
        )
        self.case(
            "idempotency fingerprint conflict",
            409,
            self.request(conflict_raw, self.radiograph, self.gain, token=token),
        )
        other_raw = _with_files(
            self.template, self.radiograph, self.gain, job_id=_uuid()
        )
        self.case(
            "idempotency cross tenant isolation",
            200,
            self.request(
                other_raw,
                self.radiograph,
                self.gain,
                token=_token(self.private_key, tenant=OTHER_TENANT),
                manifest_tenant=OTHER_TENANT,
            ),
        )

        duplicate_raw = _with_files(
            self.template, self.radiograph, self.gain, job_id=_uuid()
        )

        def duplicate() -> int:
            with httpx.Client(timeout=45.0) as client:
                return self.request(
                    duplicate_raw,
                    self.radiograph,
                    self.gain,
                    token=token,
                    client=client,
                ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: duplicate(), range(2)))
        print(f"idempotency in-progress duplicate statuses: {sorted(statuses)}")
        if not ({200, 409} <= set(statuses)):
            self.failures.append(
                f"idempotency in-progress expected 200 and 409, got {statuses}"
            )

    def resilience_cases(self, token: str) -> None:
        raw_jobs = [
            _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
            for _ in range(2)
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(self._post_raw, raw, token) for raw in raw_jobs]
            statuses = [future.result().status_code for future in futures]
        print(f"bounded concurrent valid statuses: {sorted(statuses)}")
        if statuses != [200, 200]:
            self.failures.append(
                f"bounded concurrent valid expected [200, 200], got {statuses}"
            )

        invalid_statuses = []
        for _ in range(5):
            invalid_statuses.append(
                self.client.get(f"{self.url}/v1/radiographs/dicom").status_code
            )
        print(f"repeated invalid request statuses: {invalid_statuses}")
        if any(status not in {401, 404, 405} for status in invalid_statuses):
            self.failures.append(
                f"invalid request statuses unexpected: {invalid_statuses}"
            )

        health_status = self.client.get(f"{self.url}/health").status_code
        self.case(
            "health during bounded activity", 200, self.client.get(f"{self.url}/health")
        )
        if health_status != 200:
            self.failures.append(f"health during activity returned {health_status}")

        limit_raws = [
            _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
            for _ in range(8)
        ]
        with ThreadPoolExecutor(max_workers=8) as executor:
            statuses = list(
                executor.map(
                    lambda raw: self._post_raw(raw, token).status_code, limit_raws
                )
            )
        print(f"concurrency-limit statuses: {sorted(statuses)}")
        if 429 not in statuses:
            self.failures.append(f"concurrency limit did not return 429: {statuses}")

    def _post_raw(
        self, raw: bytes, token: str, tenant: str = DEFAULT_TENANT
    ) -> httpx.Response:
        with httpx.Client(timeout=45.0) as client:
            return self.request(
                raw,
                self.radiograph,
                self.gain,
                token=token,
                manifest_tenant=tenant,
                client=client,
            )

    def launcher_cases(self) -> None:
        socket_path = os.getenv("MPIPS_LAUNCHER_SOCKET_PATH", "")
        if not socket_path or not Path(socket_path).exists():
            self.failures.append("launcher socket unavailable for direct matrix")
            return
        workspace = Path("/tmp/mpips-workspaces")
        missing_args = workspace / "job-burnin-missing-args"
        invalid_args = workspace / "job-burnin-invalid-worker"
        missing_args.mkdir(exist_ok=True)
        invalid_args.mkdir(exist_ok=True)
        (invalid_args / "args.json").write_text("{}", encoding="utf-8")
        try:
            cases = [
                ("launcher malformed JSON", b"not-json\n", "error"),
                (
                    "launcher invalid job id",
                    json.dumps(
                        {"job_id": "../bad", "workspace_dir": str(invalid_args)}
                    ).encode()
                    + b"\n",
                    "error",
                ),
                (
                    "launcher path traversal",
                    json.dumps(
                        {"job_id": "burnin-traversal", "workspace_dir": "/tmp/outside"}
                    ).encode()
                    + b"\n",
                    "error",
                ),
                (
                    "launcher missing args",
                    json.dumps(
                        {"job_id": "burnin-missing", "workspace_dir": str(missing_args)}
                    ).encode()
                    + b"\n",
                    "error",
                ),
                (
                    "launcher worker nonzero",
                    json.dumps(
                        {"job_id": "burnin-invalid", "workspace_dir": str(invalid_args)}
                    ).encode()
                    + b"\n",
                    "error",
                ),
            ]
            for name, payload, expected in cases:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(35)
                    sock.connect(socket_path)
                    sock.sendall(payload)
                    sock.shutdown(socket.SHUT_WR)
                    response = json.loads(sock.recv(4096).decode())
                status = response.get("status")
                print(f"{name}: {status} {response.get('error_code', 'controlled')}")
                if status != expected:
                    self.failures.append(f"{name}: expected {expected}, got {status}")
        finally:
            for path in (missing_args, invalid_args):
                if path.exists():
                    for child in path.iterdir():
                        if child.is_file():
                            child.unlink()
                    path.rmdir()


def _content_type(response: httpx.Response) -> str:
    return str(response.headers.get("content-type", "none")).split(";", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--secret", required=True)
    parser.add_argument("command", choices=("prepare", "run"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.base_dir, args.secret)
        print("synthetic local fixtures prepared")
        return 0
    burn_in = BurnIn(args.base_dir, args.url, args.secret)
    try:
        burn_in.run()
    finally:
        burn_in.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
