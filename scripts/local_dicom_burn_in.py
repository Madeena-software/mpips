#!/usr/bin/env python3
"""Synthetic local MPIPS DICOM smoke and isolation checks."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import httpx
import numpy as np
import pydicom
from pydicom.uid import ExplicitVRLittleEndian

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.validation import validate_dicom_dataset

API_KEY = os.getenv("MPIPS_API_KEY", "")
SHAPE = (64, 64)
GAIN_ID = "SYNTH-GAIN-001"
CAMERA = "SYNTH-CAMERA-001"
BASE_JOB_ID = "00000000-0000-4000-8000-000000000001"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _uuid() -> str:
    return str(uuid4())


def _npz_bytes(
    *,
    radiograph: bool,
    shape: tuple[int, int] = SHAPE,
    camera: str = CAMERA,
    missing: Iterable[str] = (),
) -> bytes:
    raw = np.full(shape, 1000, dtype=np.uint16)
    values: dict[str, Any]
    if radiograph:
        values = {
            "id": np.array("SYNTH-RAD-001"),
            "gainid": np.array(GAIN_ID),
            "rawimage": raw,
            "xrayparams": np.array({"detectorMode": "BED"}, dtype=object),
            "cameraparams": np.array({"serialNumber": camera}, dtype=object),
        }
    else:
        values = {
            "id": np.array(GAIN_ID),
            "rawimage": np.full(shape, 2000, dtype=np.uint16),
            "darkimage": np.full(shape, 50, dtype=np.uint16),
            "xrayparams": np.array({"detectorMode": "BED"}, dtype=object),
            "cameraparams": np.array({"serialNumber": camera}, dtype=object),
        }
    for key in missing:
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
            "station_name": "SYNTH-STATION-01",
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
            "gain": {"filename": "synthetic-gain.npz"},
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
    for path, value in (changes or {}).items():
        target: dict[str, Any] = manifest
        parts = path.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return _json_bytes(manifest)


def _files(
    raw: bytes,
    radiograph: bytes,
    gain: bytes,
    *,
    include: tuple[str, ...] = ("radiograph_npz", "gain_npz", "manifest"),
) -> list[tuple[str, tuple[str, bytes, str]]]:
    values = {
        "radiograph_npz": (
            "synthetic-radiograph.npz",
            radiograph,
            "application/octet-stream",
        ),
        "gain_npz": ("synthetic-gain.npz", gain, "application/octet-stream"),
        "manifest": ("manifest.json", raw, "application/json"),
    }
    return [(key, values[key]) for key in include]


def prepare(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for name in ("fixtures", "calibration", "results"):
        (base / name).mkdir(exist_ok=True)

    input_shape = SHAPE
    target_camera = CAMERA
    cal_meta_file = base.parent / "calibration" / "metadata.json"
    remap_file = base.parent / "calibration" / "remap.npz"

    if cal_meta_file.is_file():
        try:
            meta = json.loads(cal_meta_file.read_text("utf-8"))
            if "image_shape" in meta and len(meta["image_shape"]) == 2:
                input_shape = tuple(meta["image_shape"])
            cam_params = meta.get("source_metadata", {}).get("camera_params", {})
            if isinstance(cam_params, dict):
                cam_sn = cam_params.get("serialNumber") or cam_params.get(
                    "cameraSerial"
                )
                if cam_sn:
                    target_camera = str(cam_sn)
        except Exception:
            pass

    output_shape = input_shape
    if remap_file.is_file():
        try:
            with np.load(remap_file) as remap_data:
                if "map_x" in remap_data:
                    output_shape = tuple(remap_data["map_x"].shape)
        except Exception:
            pass

    radiograph = _npz_bytes(radiograph=True, shape=input_shape, camera=target_camera)
    gain = _npz_bytes(radiograph=False, shape=input_shape, camera=target_camera)
    fixture_dir = base / "fixtures"
    (fixture_dir / "radiograph.npz").write_bytes(radiograph)
    (fixture_dir / "gain.npz").write_bytes(gain)
    (fixture_dir / "manifest.json").write_bytes(
        _with_files(_manifest_template(), radiograph, gain, job_id=BASE_JOB_ID)
    )

    y_values, x_values = np.indices(output_shape, dtype=np.float32)
    np.savez_compressed(
        base / "calibration" / "remap.npz", map_x=x_values, map_y=y_values
    )
    (base / "calibration" / "metadata.json").write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "synthetic-local-calibration-v1",
                "image_shape": list(input_shape),
                "source_metadata": {
                    "detector_mode": "BED",
                    "camera_params": {"serialNumber": target_camera},
                },
            }
        ),
        encoding="utf-8",
    )


class BurnIn:
    def __init__(self, base: Path, url: str) -> None:
        self.base = base
        self.url = url.rstrip("/")
        self.template = _manifest_template()
        self.radiograph = (base / "fixtures" / "radiograph.npz").read_bytes()
        self.gain = (base / "fixtures" / "gain.npz").read_bytes()
        self.raw_manifest = _with_files(
            self.template,
            self.radiograph,
            self.gain,
            job_id=_uuid(),
        )
        self.client = httpx.Client(timeout=120.0, follow_redirects=False)
        self.failures: list[str] = []
        self.case_count = 0
        self.initial_workspaces = {
            path.name
            for path in Path("/tmp/mpips-workspaces").glob("job-*")
            if path.is_dir()
        }
        self.api_key = os.getenv("MPIPS_API_KEY") or os.getenv("API_KEY") or ""
        self.target_shape = SHAPE
        parent_remap = base.parent / "calibration" / "remap.npz"
        parent_meta = base.parent / "calibration" / "metadata.json"
        remap_file = (
            parent_remap
            if parent_remap.is_file()
            else base / "calibration" / "remap.npz"
        )
        cal_meta_file = (
            parent_meta
            if parent_meta.is_file()
            else base / "calibration" / "metadata.json"
        )

        if remap_file.is_file():
            try:
                with np.load(remap_file) as remap_data:
                    if "map_x" in remap_data:
                        self.target_shape = tuple(remap_data["map_x"].shape)
            except Exception:
                pass

        if self.target_shape == SHAPE and cal_meta_file.is_file():
            try:
                meta = json.loads(cal_meta_file.read_text("utf-8"))
                if "image_shape" in meta and len(meta["image_shape"]) == 2:
                    self.target_shape = tuple(meta["image_shape"])
            except Exception:
                pass

    def close(self) -> None:
        self.client.close()

    def request(
        self,
        raw: bytes,
        radiograph: bytes | None = None,
        gain: bytes | None = None,
        *,
        headers: dict[str, str] | None = None,
        include: tuple[str, ...] = ("radiograph_npz", "gain_npz", "manifest"),
    ) -> httpx.Response:
        request_headers = {"X-MPIPS-API-Key": self.api_key}
        request_headers.update(headers or {})
        try:
            return self.client.post(
                f"{self.url}/v1/radiographs/dicom",
                headers=request_headers,
                files=_files(
                    raw,
                    self.radiograph if radiograph is None else radiograph,
                    self.gain if gain is None else gain,
                    include=include,
                ),
            )
        except (httpx.HTTPError, httpx.RemoteProtocolError, httpx.CloseError):
            self.client.close()
            self.client = httpx.Client(timeout=120.0, follow_redirects=False)
            return self.client.post(
                f"{self.url}/v1/radiographs/dicom",
                headers=request_headers,
                files=_files(
                    raw,
                    self.radiograph if radiograph is None else radiograph,
                    self.gain if gain is None else gain,
                    include=include,
                ),
            )

    def case(self, name: str, expected: Any, response: Any) -> None:
        expected_set = (
            {expected}
            if not isinstance(expected, (set, list, tuple))
            else set(expected)
        )
        self.case_count += 1
        detail = ""
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                detail = str(response.json().get("detail", ""))[:80]
            except (ValueError, TypeError):
                detail = "invalid-json"
        print(f"{name}: {response.status_code} {detail}")
        if response.status_code not in expected_set:
            self.failures.append(
                f"{name}: expected {sorted(expected_set)}, got {response.status_code}"
            )

    def run(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "MPIPS_API_KEY environment variable is required for burn-in "
                "run operation"
            )
        health = self.client.get(f"{self.url}/health")
        self.case("health", 200, health)

        for path in ("/", "/v1/nodes", "/v1/jobs", "/v1/secure-test", "/docs"):
            expected_code = (401, 404) if path in ("/v1/nodes", "/v1/jobs") else 404
            self.case(
                f"absent {path}", expected_code, self.client.get(f"{self.url}{path}")
            )

        self.case(
            "missing API key",
            401,
            self.request(self.raw_manifest, headers={"X-MPIPS-API-Key": ""}),
        )
        self.case(
            "wrong API key",
            401,
            self.request(self.raw_manifest, headers={"X-MPIPS-API-Key": "wrong-key"}),
        )
        self.case(
            "bearer without API key",
            401,
            self.request(
                self.raw_manifest,
                headers={"X-MPIPS-API-Key": "", "Authorization": "Bearer legacy"},
            ),
        )

        valid = self.request(self.raw_manifest)
        self.case("valid conversion", 200, valid)
        if valid.status_code == 200:
            result = self.base / "results" / "valid.dcm"
            result.write_bytes(valid.content)
            self.validate_dicom(result, self.raw_manifest)

        self.case(
            "malformed manifest",
            422,
            self.request(b"{}"),
        )
        self.case(
            "malformed radiograph",
            422,
            self.request(
                _with_files(
                    self.template,
                    b"not-an-npz",
                    self.gain,
                    job_id=_uuid(),
                ),
                radiograph=b"not-an-npz",
            ),
        )
        self.idempotency_cases()
        self.bounded_concurrency()
        self.launcher_cases()
        self.cleanup_case()

        if self.failures:
            raise RuntimeError("; ".join(self.failures))
        print(f"burn-in passed: {self.case_count} HTTP cases")

    def validate_dicom(self, path: Path, raw_manifest: bytes) -> None:
        manifest = MHCSManifest.model_validate_json(raw_manifest)
        assert manifest.dicom is not None
        dataset = pydicom.dcmread(path)
        assert dataset.file_meta.TransferSyntaxUID == ExplicitVRLittleEndian
        assert dataset.SOPInstanceUID == manifest.dicom.sop_instance_uid
        assert dataset.PatientID == manifest.patient.medical_record_number
        assert (
            dataset.Rows == self.target_shape[0]
            and dataset.Columns == self.target_shape[1]
        )
        assert dataset.BitsAllocated == 16 and dataset.PixelRepresentation == 0
        assert dataset.BurnedInAnnotation == "NO"
        assert dataset.LossyImageCompression == "00"
        assert dataset.pixel_array.dtype == np.uint16
        assert not any(element.tag.is_private for element in dataset.iterall())
        assert (
            validate_dicom_dataset(path, manifest, self.target_shape).get("valid")
            is True
        )
        h, w = self.target_shape
        print(
            f"valid DICOM: explicit-vr-little-endian, {h}x{w} uint16, no private tags"
        )

    def idempotency_cases(self) -> None:
        raw = _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
        first = self.request(raw)
        self.case("idempotency first claim", 200, first)
        self.case("idempotency replay", 200, self.request(raw))
        conflict = _with_files(
            self.template,
            self.radiograph,
            self.gain,
            job_id=json.loads(raw)["conversion_job_id"],
            changes={"examination.study_description": "Synthetic Conflict Study"},
        )
        self.case("idempotency conflict", 409, self.request(conflict))

    def bounded_concurrency(self, total_requests: int = 8) -> None:
        results: list[dict[str, Any]] = []

        def _execute_single_request(idx: int) -> dict[str, Any]:
            job_id = _uuid()
            raw = _with_files(self.template, self.radiograph, self.gain, job_id=job_id)
            res = self.request(raw)
            status_code = res.status_code
            cid = res.headers.get("X-Correlation-ID", "")
            conv_job_id = res.headers.get("X-Conversion-Job-ID", "")
            detail = ""
            if status_code != 200:
                try:
                    if res.headers.get("content-type", "").startswith(
                        "application/json"
                    ):
                        data = res.json()
                        detail = str(data.get("detail", ""))[:120]
                    else:
                        detail = res.text[:120]
                except Exception:
                    detail = "unparseable-response"
            return {
                "job_id": job_id,
                "status_code": status_code,
                "correlation_id": cid,
                "conversion_job_id": conv_job_id,
                "detail": detail,
            }

        with ThreadPoolExecutor(max_workers=total_requests) as executor:
            futures = [
                executor.submit(_execute_single_request, i)
                for i in range(total_requests)
            ]
            results = [f.result() for f in futures]

        statuses: list[int] = []
        for item in results:
            st = item["status_code"]
            statuses.append(st)
            log_line = f"job={item['job_id']} status={st}"
            if item["correlation_id"]:
                log_line += f" cid={item['correlation_id']}"
            if item["detail"]:
                log_line += f" detail={item['detail']}"
            print(log_line)

        print(f"bounded concurrency statuses: {sorted(statuses)}")

        unexpected = [s for s in statuses if s not in {200, 429}]
        if unexpected:
            unexp_str = sorted(unexpected)
            self.failures.append(
                f"concurrency verification failed with unexpected HTTP status(es) "
                f"{unexp_str}: {statuses}"
            )
        if 200 not in statuses:
            self.failures.append(
                f"concurrency verification failed: no 200 status returned in {statuses}"
            )
        if 429 not in statuses:
            self.failures.append(
                f"concurrency verification failed: no 429 status returned in {statuses}"
            )

        rejected_item = next(
            (item for item in results if item["status_code"] == 429), None
        )
        if rejected_item:
            retry_raw = _with_files(
                self.template,
                self.radiograph,
                self.gain,
                job_id=rejected_item["job_id"],
            )
            retry_res = self.request(retry_raw)
            self.case("429 retry after capacity available", 200, retry_res)

        self.case(
            "health after concurrent activity",
            200,
            self.client.get(f"{self.url}/health"),
        )

    def launcher_cases(self) -> None:
        socket_path = os.getenv("MPIPS_LAUNCHER_SOCKET_PATH", "")
        if not socket_path or not Path(socket_path).exists():
            self.failures.append("launcher socket unavailable")
            return
        workspace = Path("/tmp/mpips-workspaces")
        missing_args = workspace / "job-burnin-missing-args"
        missing_args.mkdir(exist_ok=True)
        try:
            for name, payload in (
                ("launcher malformed JSON", b"not-json\n"),
                (
                    "launcher path traversal",
                    json.dumps(
                        {"job_id": "burnin-traversal", "workspace_dir": "/tmp/outside"}
                    ).encode()
                    + b"\n",
                ),
                (
                    "launcher missing args",
                    json.dumps(
                        {"job_id": "burnin-missing", "workspace_dir": str(missing_args)}
                    ).encode()
                    + b"\n",
                ),
            ):
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(35)
                    sock.connect(socket_path)
                    sock.sendall(payload)
                    sock.shutdown(socket.SHUT_WR)
                    response = json.loads(sock.recv(4096).decode())
                self.case(
                    name,
                    "error" if response.get("status") == "error" else 1,
                    _Response(response),
                )
        finally:
            missing_args.rmdir()

    def cleanup_case(self) -> None:
        workspace_root = Path("/tmp/mpips-workspaces")
        leftovers = [
            path
            for path in workspace_root.glob("job-*")
            if path.is_dir() and path.name not in self.initial_workspaces
        ]
        if leftovers:
            self.failures.append(f"workspace cleanup left {len(leftovers)} directories")
        print(f"workspace cleanup: {len(leftovers)} job directories")


class _Response:
    def __init__(self, data: dict[str, Any]) -> None:
        self.status_code = data.get("status")
        self.headers: dict[str, str] = {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8014")
    parser.add_argument("command", choices=("prepare", "run"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.base_dir)
        print("synthetic local fixtures prepared")
        return 0
    burn_in = BurnIn(args.base_dir, args.url)
    try:
        burn_in.run()
    finally:
        burn_in.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
