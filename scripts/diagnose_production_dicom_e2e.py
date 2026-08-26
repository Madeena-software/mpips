#!/usr/bin/env python3
"""Read-only production MPIPS/MHCS DICOM diagnostic."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.parse
import uuid
import zipfile
from pathlib import Path

import numpy as np
import pydicom
import requests
from pydicom.uid import ExplicitVRLittleEndian, UID

from mpips.workflows.imager_pipeline.npz_io import (
    sha256_file,
)

RADIOGRAPH_ID = "1EwG5WPLcR30vSTHaOAybTVg6S9P4GSMB"
GAIN_ID = "1R6o53hMVBy3B__cAqJBUhwcoTn14VGWF"
ALLOWED_DRIVE_IDS = (RADIOGRAPH_ID, GAIN_ID)
FILES = {RADIOGRAPH_ID: "BED_1785646321389.npz", GAIN_ID: "BED_1785642964117.npz"}
API = "http://127.0.0.1:8014/v1/radiographs/dicom"
SUMMARY_FIELDS = (
    "repository_workflow_sha",
    "production_runtime_sha",
    "running_mpips_api_image",
    "runtime_provenance",
    "BED_INPUT_COMPATIBILITY",
    "BED_CALIBRATION",
    "BED_DIRECT_CONVERSION",
    "BED_DICOM_STRUCTURE",
    "BED_CALIBRATION_SELECTION",
    "BED_CALIBRATION_PRESENT",
    "BED_CALIBRATION_VALIDATED",
    "BED_CALIBRATION_FINGERPRINT",
    "BED_CALIBRATION_SHAPE",
    "BED_CALIBRATION_DETECTOR_MODE",
    "BED_CALIBRATION_CAMERA",
    "BED_CALIBRATION_REMAP",
    "TRX_CALIBRATION",
    "TRX_CALIBRATION_PRESENT",
    "TRX_CALIBRATION_VALIDATED",
    "TRX_CALIBRATION_FINGERPRINT",
    "TRX_CALIBRATION_SHAPE",
    "TRX_CALIBRATION_DETECTOR_MODE",
    "TRX_CALIBRATION_CAMERA",
    "TRX_CALIBRATION_REMAP",
    "SYNTHETIC_THORAX_PIXEL_IDENTITY",
    "SYNTHETIC_THORAX_DIRECT_CONVERSION",
    "SYNTHETIC_THORAX_DICOM_STRUCTURE",
    "THORAX_CALIBRATION_SELECTION",
    "MHCS_IMAGE_WORKER",
    "MHCS_PRIVATE_NETWORK",
    "MHCS_MPIPS_CONFIG",
    "MHCS_MPIPS_TARGET",
    "MHCS_MPIPS_DNS",
    "MHCS_MPIPS_HEALTH",
    "MHCS_MPIPS_HEALTH_STATUS",
    "MHCS_BED_MPIPSCLIENT",
    "MHCS_BED_DICOM_STRUCTURE",
    "MHCS_THORAX_MPIPSCLIENT",
    "MHCS_THORAX_DICOM_STRUCTURE",
    "CLEANUP",
    "FINAL_DIAGNOSTIC_CLASSIFICATION",
)


class DiagnosticFailure(Exception):
    def __init__(self, classification: str):
        self.classification = classification


def map_failure(stage: str) -> str:
    return {
        "download": "TEST_DATA_DOWNLOAD_BLOCKED",
        "bed_input": "BED_INPUT_PAIR_INCOMPATIBLE",
        "bed_calibration": "BED_CALIBRATION_NOT_AVAILABLE",
        "bed_conversion": "BED_CONVERSION_FAILED",
        "bed_dicom": "BED_DICOM_INVALID",
        "trx_calibration": "TRX_CALIBRATION_NOT_AVAILABLE",
        "trx_compatibility": "SYNTHETIC_THORAX_CALIBRATION_INCOMPATIBLE",
        "thorax_conversion": "SYNTHETIC_THORAX_CONVERSION_FAILED",
        "thorax_dicom": "SYNTHETIC_THORAX_DICOM_INVALID",
    }[stage]


def classify_runtime(
    version_sha: str, api_image: str, worker_image: str, workflow_sha: str
) -> dict:
    image_sha = (
        api_image.rsplit(":", 1)[-1] if api_image.startswith("mpips-api:") else ""
    )
    worker_sha = (
        worker_image.rsplit(":", 1)[-1]
        if worker_image.startswith("mpips-npz-worker:")
        else ""
    )

    def valid(value):
        return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))

    if (
        valid(version_sha)
        and valid(image_sha)
        and version_sha == image_sha
        and (not worker_sha or worker_sha == version_sha)
    ):
        return {
            "classification": (
                "MATCHES_WORKFLOW_SHA"
                if version_sha == workflow_sha
                else "DIFFERS_FROM_WORKFLOW_SHA"
            ),
            "sha": version_sha,
        }
    if valid(version_sha) and valid(image_sha) and version_sha != image_sha:
        return {"classification": "UNPROVEN", "sha": version_sha}
    return {
        "classification": "UNPROVEN",
        "sha": version_sha if valid(version_sha) else "UNPROVEN",
    }


def discover_worker(candidates: list[str]) -> dict:
    candidates = [value for value in candidates if value]
    if not candidates:
        return {"classification": "MHCS_IMAGE_WORKER_NOT_FOUND"}
    if len(candidates) > 1:
        return {"classification": "MHCS_IMAGE_WORKER_AMBIGUOUS"}
    return {"classification": "PASS", "container": candidates[0]}


def classify_mhcs_response(info: dict) -> str:
    if info.get("config") is False:
        return "CONFIG_FAILED"
    if info.get("dns") is False:
        return "DNS_FAILED"
    if info.get("http_status") != 200 or info.get("health_status") != 200:
        return "HEALTH_FAILED" if info.get("health_status") != 200 else "FAIL"
    if info.get("content_type", "").split(";", 1)[
        0
    ] != "application/dicom" or not info.get("response_bytes"):
        return "FAIL"
    return "PASS" if info.get("dicom_structure") is True else "DICOM_INVALID"


def classify_mhcs_probe(info: dict, mode: str) -> str:
    stage = info.get("stage")
    if stage in {"bootstrap", "config"}:
        return "MHCS_MPIPS_CONFIG_FAILED"
    if stage == "dns":
        return "MHCS_MPIPS_DNS_FAILED"
    if stage == "health":
        return "MHCS_MPIPS_HEALTH_FAILED"
    if stage in {"mpips_client", "response"}:
        return f"MHCS_{mode}_MPIPSCLIENT_FAILED"
    return classify_mhcs_response(info)


def camera_compatibility(*cameras: dict) -> str:
    serials = {
        str(camera.get("serialNumber") or camera.get("cameraSerial"))
        for camera in cameras
        if camera.get("serialNumber") or camera.get("cameraSerial")
    }
    return "UNKNOWN" if not serials else "PASS" if len(serials) == 1 else "FAIL"


def safe_cleanup_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if path.parent != root.resolve() or path == root.resolve():
        raise ValueError("cleanup path escapes diagnostic directory")
    return path


def final_classification(results: dict) -> str:
    ordered = (
        ("CLEANUP", "DIAGNOSTIC_INTERNAL_FAILURE"),
        ("BED_INPUT_COMPATIBILITY", "BED_INPUT_PAIR_INCOMPATIBLE"),
        ("BED_CALIBRATION", "BED_CALIBRATION_NOT_AVAILABLE"),
        ("BED_DIRECT_CONVERSION", "BED_CONVERSION_FAILED"),
        ("BED_DICOM_STRUCTURE", "BED_DICOM_INVALID"),
        ("TRX_CALIBRATION", "TRX_CALIBRATION_NOT_AVAILABLE"),
        (
            "SYNTHETIC_THORAX_PIXEL_IDENTITY",
            "SYNTHETIC_THORAX_CALIBRATION_INCOMPATIBLE",
        ),
        ("SYNTHETIC_THORAX_DIRECT_CONVERSION", "SYNTHETIC_THORAX_CONVERSION_FAILED"),
        ("SYNTHETIC_THORAX_DICOM_STRUCTURE", "SYNTHETIC_THORAX_DICOM_INVALID"),
        ("MHCS_IMAGE_WORKER", "MHCS_IMAGE_WORKER_NOT_FOUND"),
        ("MHCS_PRIVATE_NETWORK", "MHCS_PRIVATE_NETWORK_FAILED"),
        ("MHCS_MPIPS_CONFIG", "MHCS_MPIPS_CONFIG_FAILED"),
        ("MHCS_MPIPS_DNS", "MHCS_MPIPS_DNS_FAILED"),
        ("MHCS_MPIPS_HEALTH", "MHCS_MPIPS_HEALTH_FAILED"),
        ("MHCS_BED_MPIPSCLIENT", "MHCS_BED_MPIPSCLIENT_FAILED"),
        ("MHCS_BED_DICOM_STRUCTURE", "MHCS_BED_DICOM_INVALID"),
        ("MHCS_THORAX_MPIPSCLIENT", "MHCS_THORAX_MPIPSCLIENT_FAILED"),
        ("MHCS_THORAX_DICOM_STRUCTURE", "MHCS_THORAX_DICOM_INVALID"),
    )
    for key, classification in ordered:
        value = results.get(key)
        if value in {"FAIL", "DICOM_INVALID"} or value in {
            "MHCS_IMAGE_WORKER_NOT_FOUND",
            "MHCS_IMAGE_WORKER_AMBIGUOUS",
        }:
            return value if key == "MHCS_IMAGE_WORKER" else classification
    if results.get("runtime_provenance") == "DIFFERS_FROM_WORKFLOW_SHA":
        return "PRODUCTION_RUNTIME_NOT_WORKFLOW_SHA"
    if results.get("runtime_provenance") == "UNPROVEN":
        return "PRODUCTION_RUNTIME_SHA_UNPROVEN"
    return "PRODUCTION_MPIPS_BED_AND_SYNTHETIC_THORAX_MHCS_E2E_PASS"


def _download(file_id: str, target: Path) -> None:
    url = "https://drive.google.com/uc?" + urllib.parse.urlencode(
        {"export": "download", "id": file_id}
    )
    session = requests.Session()
    response = session.get(
        url, headers={"User-Agent": "mpips-production-diagnostic/1"}, timeout=60
    )
    data = response.content
    if not zipfile.is_zipfile(io.BytesIO(data)):
        token = re.search(rb"confirm=([0-9A-Za-z_-]+)", data)
        if token:
            response = session.get(
                url + "&confirm=" + token.group(1).decode(), timeout=120
            )
            data = response.content
    if (
        data.startswith(b"<!DOCTYPE")
        or data.startswith(b"<html")
        or not zipfile.is_zipfile(io.BytesIO(data))
    ):
        raise RuntimeError("Google Drive returned a non-NPZ response")
    target.write_bytes(data)


def _metadata(path: Path) -> dict:
    with np.load(path, allow_pickle=True) as data:

        def scalar(key):
            return data[key].item()

        return {
            "id": str(scalar("id")),
            "gainid": str(scalar("gainid")) if "gainid" in data else None,
            "mode": str(scalar("xrayparams").get("detectorMode", "")).upper(),
            "camera": scalar("cameraparams"),
            "raw": np.asarray(data["rawimage"]).copy() if "rawimage" in data else None,
            "dark": (
                np.asarray(data["darkimage"]).copy() if "darkimage" in data else None
            ),
        }


def rewrite_detector_mode(source: Path, target: Path) -> None:
    with np.load(source, allow_pickle=True) as data:
        payload = {key: data[key] for key in data.files}
        params = payload["xrayparams"].item().copy()
        if str(params.get("detectorMode", "")).upper() != "BED":
            raise ValueError("source NPZ is not BED")
        params["detectorMode"] = "TRX"
        payload["xrayparams"] = np.asarray(params, dtype=object)
        np.savez_compressed(target, **payload)


def _calibrations(root: Path) -> dict[str, dict]:
    if not root.is_dir():
        return {}
    candidates = [root] + sorted(p for p in root.iterdir() if p.is_dir())
    result = {}
    for directory in candidates:
        metadata = directory / "metadata.json"
        remap = directory / "remap.npz"
        if not metadata.is_file() or not remap.is_file():
            continue
        try:
            value = json.loads(metadata.read_text())
            source = value.get("source_metadata", {})
            mode = str(source.get("detector_mode", "")).upper()
            if mode in {"BED", "TRX"} and mode not in result:
                result[mode] = {"dir": directory, "meta": value, "source": source}
        except (OSError, ValueError, TypeError):
            continue
    return result


def find_calibration(
    root: Path,
    mode: str,
    shape: tuple[int, int],
    camera: dict,
    gain_camera: dict | None = None,
) -> dict:
    calibration = _calibrations(root).get(mode)
    if not calibration:
        return {
            "present": False,
            "validated": False,
            "compatible": False,
            "remap": False,
            "fingerprint": False,
            "camera_compatibility": "UNKNOWN",
            "shape": (),
        }
    source_camera = calibration["source"].get("camera_params", {})
    camera_result = camera_compatibility(camera, gain_camera or {}, source_camera)
    metadata = calibration["meta"]
    remap_ok = False
    try:
        with np.load(calibration["dir"] / "remap.npz") as remap:
            remap_ok = (
                "map_x" in remap
                and "map_y" in remap
                and remap["map_x"].shape == remap["map_y"].shape
            )
    except (OSError, ValueError):
        pass
    compatible = (
        tuple(metadata.get("image_shape", ())) == tuple(shape)
        and remap_ok
        and camera_result == "PASS"
    )
    return {
        "present": True,
        "validated": metadata.get("validated") is True,
        "compatible": compatible,
        "mode": mode,
        "shape": tuple(metadata.get("image_shape", ())),
        "camera_compatible": camera_result == "PASS",
        "camera_compatibility": camera_result,
        "fingerprint": bool(metadata.get("fingerprint")),
        "remap": remap_ok,
    }


def record_calibration(results: dict, mode: str, evidence: dict) -> None:
    results[f"{mode}_CALIBRATION_PRESENT"] = (
        "PASS" if evidence.get("present") else "FAIL"
    )
    results[f"{mode}_CALIBRATION_VALIDATED"] = (
        "PASS" if evidence.get("validated") else "FAIL"
    )
    results[f"{mode}_CALIBRATION_FINGERPRINT"] = (
        "PASS" if evidence.get("fingerprint") else "FAIL"
    )
    results[f"{mode}_CALIBRATION_SHAPE"] = (
        "x".join(map(str, evidence.get("shape", ()))) or "UNKNOWN"
    )
    results[f"{mode}_CALIBRATION_DETECTOR_MODE"] = evidence.get("mode", "UNKNOWN")
    results[f"{mode}_CALIBRATION_CAMERA"] = evidence.get(
        "camera_compatibility", "UNKNOWN"
    )
    results[f"{mode}_CALIBRATION_REMAP"] = "PASS" if evidence.get("remap") else "FAIL"


def validate_dicom_structure(path: Path) -> dict:
    ds = pydicom.dcmread(path)
    if not getattr(ds, "file_meta", None) or not getattr(
        ds.file_meta, "TransferSyntaxUID", None
    ):
        raise ValueError("missing DICOM file meta or transfer syntax")
    if UID(str(ds.file_meta.TransferSyntaxUID)) != UID(str(ExplicitVRLittleEndian)):
        raise ValueError("unsupported DICOM transfer syntax")
    if int(getattr(ds, "Rows", 0)) <= 0 or int(getattr(ds, "Columns", 0)) <= 0:
        raise ValueError("invalid DICOM dimensions")
    if "PixelData" not in ds or int(getattr(ds, "BitsAllocated", 0)) != 16:
        raise ValueError("missing PixelData or BitsAllocated is not 16")
    if int(getattr(ds, "PixelRepresentation", -1)) != 0:
        raise ValueError("PixelRepresentation is not unsigned")
    for key in (
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "SOPInstanceUID",
        "SOPClassUID",
    ):
        value = getattr(ds, key, None)
        if not value or not UID(str(value)).is_valid:
            raise ValueError(f"missing {key}")
    if any(elem.tag.is_private for elem in ds):
        raise ValueError("unexpected private DICOM tag")
    pixels = ds.pixel_array
    if pixels.ndim != 2 or pixels.dtype != np.uint16:
        raise ValueError("DICOM pixels are not a uint16 matrix")
    return {
        "rows": int(ds.Rows),
        "columns": int(ds.Columns),
        "bytes": path.stat().st_size,
    }


def _manifest(rad: Path, gain: Path, mode: str) -> str:
    now = "2026-08-26T00:00:00+00:00"
    payload = {
        "manifest_version": "1.0",
        "conversion_job_id": str(uuid.uuid4()),
        "submission_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "examination": {
            "examination_id": "MPIPS-DIAGNOSTIC",
            "booking_id": "MPIPS-DIAGNOSTIC",
            "service_request_id": "MPIPS-DIAGNOSTIC",
            "encounter_id": "MPIPS-DIAGNOSTIC",
            "accession_number": "MPIPS-DIAGNOSTIC",
            "study_id": "MPIPS-DIAGNOSTIC",
            "performed_at": now,
            "study_description": "MPIPS production diagnostic",
            "protocol_name": "MPIPS production diagnostic",
        },
        "patient": {
            "member_id": str(uuid.uuid4()),
            "medical_record_number": "MPIPS-DIAGNOSTIC",
            "name": {"full_name": "MPIPS Diagnostic", "family_name": "Diagnostic"},
            "sex": "unknown",
            "birth_date": "2000-01-01",
        },
        "operator": {
            "operator_id": str(uuid.uuid4()),
            "name": {"full_name": "MPIPS Diagnostic", "family_name": "Diagnostic"},
        },
        "site": {
            "organization_id": "MPIPS-DIAGNOSTIC",
            "site_id": "MPIPS-DIAGNOSTIC",
            "institution_name": "MPIPS Diagnostic",
            "department_name": "Radiology",
            "station_name": "MPIPS-DIAGNOSTIC",
            "timezone": "UTC",
        },
        "capture": {
            "capture_id": str(uuid.uuid4()),
            "protocol_version": "MPIPS-DIAGNOSTIC",
            "body_part_examined": "CHEST",
            "laterality": "U",
            "projection": "PA",
            "captured_at": now,
            "radiograph": {
                "filename": rad.name,
                "byte_size": rad.stat().st_size,
                "sha256": sha256_file(rad),
            },
            "gain": {
                "filename": gain.name,
                "byte_size": gain.stat().st_size,
                "gain_id": _metadata(gain)["id"],
                "sha256": sha256_file(gain),
            },
            "image_spacing": {"row_um": 140.0, "column_um": 140.0},
            "detector_type": mode,
        },
        "dicom": {
            "study_instance_uid": "1.2.826.0.1.3680043.10.1356.9.1",
            "series_instance_uid": "1.2.826.0.1.3680043.10.1356.9.2",
            "sop_instance_uid": "1.2.826.0.1.3680043.10.1356.9.3",
            "series_number": 1,
            "instance_number": 1,
            "series_description": "MPIPS diagnostic",
            "presentation_intent": "FOR PRESENTATION",
        },
    }
    return json.dumps(payload)


def _direct(rad: Path, gain: Path, mode: str, out: Path) -> tuple[bool, dict]:
    start = time.monotonic()
    try:
        response = requests.post(
            API,
            headers={"X-MPIPS-API-Key": os.environ["MPIPS_API_KEY"]},
            files={
                "radiograph_npz": (
                    rad.name,
                    rad.open("rb"),
                    "application/octet-stream",
                ),
                "gain_npz": (gain.name, gain.open("rb"), "application/octet-stream"),
                "manifest": (
                    "manifest.json",
                    _manifest(rad, gain, mode),
                    "application/json",
                ),
            },
            timeout=360,
        )
        if (
            response.status_code == 200
            and response.headers.get("content-type", "").split(";")[0]
            == "application/dicom"
        ):
            out.write_bytes(response.content)
            return True, {
                "status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "bytes": len(response.content),
                "seconds": round(time.monotonic() - start, 2),
            }
        return False, {
            "status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "bytes": len(response.content),
            "seconds": round(time.monotonic() - start, 2),
        }
    except Exception as exc:
        return False, {"error": type(exc).__name__}


def _docker(*args: str, check=True) -> str:
    return subprocess.run(
        ["docker", *args], check=check, capture_output=True, text=True
    ).stdout.strip()


def _runtime_provenance(results: dict) -> None:
    workflow_sha = results["repository_workflow_sha"]
    version_path = Path("/var/www/mpips-runtime/.mpips-version")
    deployed = (
        version_path.read_text().strip() if version_path.is_file() else "UNPROVEN"
    )
    api = _docker(
        "ps",
        "-q",
        "--filter",
        "name=mpips-api",
        "--filter",
        "status=running",
        check=False,
    ).splitlines()
    image = (
        _docker("inspect", "--format", "{{.Config.Image}}", api[0], check=False)
        if len(api) == 1
        else "UNPROVEN"
    )
    worker_path = Path("/var/www/mpips-runtime/.mpips-worker-image")
    worker = worker_path.read_text().strip() if worker_path.is_file() else "UNPROVEN"
    results.update(
        {
            "production_runtime_sha": deployed,
            "running_mpips_api_image": image,
            "running_mpips_worker_image": worker,
        }
    )
    results.update(classify_runtime(deployed, image, worker, workflow_sha))
    results["runtime_provenance"] = results.pop("classification")


def _mhcs_probe(
    container: str, rad: Path, gain: Path, manifest: str, out: Path
) -> dict:
    token = f"mpips-diagnostic-{uuid.uuid4()}"
    remote = f"/tmp/{token}"
    php = out.parent / f"{token}.php"
    php.write_text("""<?php
$stage = 'bootstrap';
try {
    require '/var/www/html/vendor/autoload.php';
    $app = require '/var/www/html/bootstrap/app.php';
    $app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();
    $stage = 'config';
    $base = config('mhcs.mpips.base_url');
    if (!is_string($base) || trim($base) === '' || !parse_url($base, PHP_URL_HOST)) throw new RuntimeException(); # noqa: E501
    $stage = 'dns';
    $host = parse_url($base, PHP_URL_HOST);
    $dns = $host ? gethostbyname($host) !== $host || filter_var($host, FILTER_VALIDATE_IP) : false; # noqa: E501
    if (!$dns) throw new RuntimeException();
    $stage = 'health';
    $health = Illuminate\\Support\\Facades\\Http::timeout(10)->get(rtrim($base, '/').'/health'); # noqa: E501
    if ($health->status() !== 200) throw new RuntimeException();
    $stage = 'mpips_client';
    $r = (new App\\Modules\\ImageGateway\\Infrastructure\\MpipsClient())->convert($argv[1], $argv[2], file_get_contents($argv[3])); # noqa: E501
    $stage = 'response';
    file_put_contents($argv[4], $r->body());
    echo json_encode(['ok'=>true, 'status'=>$r->status(), 'content_type'=>$r->header('Content-Type'), 'bytes'=>strlen($r->body()), 'target'=>parse_url($base, PHP_URL_SCHEME).'://'.parse_url($base, PHP_URL_HOST).':'.(parse_url($base, PHP_URL_PORT) ?: 80), 'health_status'=>$health->status(), 'dns'=>$dns]); # noqa: E501
} catch (\\Throwable $e) {
    echo json_encode(['ok'=>false, 'stage'=>$stage]);
}
""")
    try:
        _docker("exec", container, "mkdir", remote)
        for source, name in ((rad, "rad.npz"), (gain, "gain.npz"), (php, "probe.php")):
            _docker("cp", str(source), f"{container}:{remote}/{name}")
        manifest_path = out.parent / f"{token}-manifest.json"
        manifest_path.write_text(manifest)
        _docker("cp", str(manifest_path), f"{container}:{remote}/manifest.json")
        result = _docker(
            "exec",
            container,
            "php",
            f"{remote}/probe.php",
            f"{remote}/rad.npz",
            f"{remote}/gain.npz",
            f"{remote}/manifest.json",
            f"{remote}/out.dcm",
        )
        info = json.loads(result)
        if not info.get("ok"):
            return info
        _docker("cp", f"{container}:{remote}/out.dcm", str(out))
        info["http_status"] = info.pop("status", None)
        info["response_bytes"] = info.pop("bytes", 0)
        info["dicom_structure"] = False
        try:
            info["dicom_structure"] = validate_dicom_structure(out) is not None
        except Exception:
            pass
        return info
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {
            "config": False,
            "http_status": None,
            "health_status": None,
            "response_bytes": 0,
            "dicom_structure": False,
        }
    finally:
        _docker("exec", container, "rm", "-rf", remote, check=False)
        cleanup = subprocess.run(
            ["docker", "exec", container, "test", "!", "-e", remote],
            capture_output=True,
        )
        if cleanup.returncode != 0:
            raise RuntimeError("container diagnostic cleanup could not be verified")
        php.unlink(missing_ok=True)
        if "manifest_path" in locals():
            manifest_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    args = parser.parse_args()
    results = {
        "repository_workflow_sha": os.environ.get("GITHUB_SHA", "UNPROVEN"),
        "test_radiograph": FILES[RADIOGRAPH_ID],
        "test_gain": FILES[GAIN_ID],
        "CLEANUP": "PASS",
    }
    results.update({key: "NOT_RUN" for key in SUMMARY_FIELDS if key not in results})
    with tempfile.TemporaryDirectory(prefix="mpips-diagnostic-") as raw_dir:
        root = Path(raw_dir)
        try:
            _runtime_provenance(results)
            if not os.environ.get("MPIPS_API_KEY", "").strip():
                raise DiagnosticFailure("DIAGNOSTIC_INTERNAL_FAILURE")
            rad, gain = root / FILES[RADIOGRAPH_ID], root / FILES[GAIN_ID]
            try:
                _download(RADIOGRAPH_ID, rad)
                _download(GAIN_ID, gain)
            except Exception:
                raise DiagnosticFailure(map_failure("download"))
            rm, gm = _metadata(rad), _metadata(gain)
            compatible = (
                rm["gainid"] == gm["id"]
                and rm["mode"] == gm["mode"] == "BED"
                and rm["raw"].shape == gm["raw"].shape == gm["dark"].shape
            )
            results["BED_INPUT_COMPATIBILITY"] = "PASS" if compatible else "FAIL"
            if not compatible:
                raise DiagnosticFailure(map_failure("bed_input"))
            bed_cal = find_calibration(
                Path("/var/www/mpips-runtime/calibration"),
                "BED",
                rm["raw"].shape,
                rm["camera"],
                gm["camera"],
            )
            record_calibration(results, "BED", bed_cal)
            results["BED_CALIBRATION"] = (
                "PASS"
                if bed_cal["present"]
                and bed_cal["validated"]
                and bed_cal["fingerprint"]
                and bed_cal["remap"]
                and bed_cal["compatible"]
                else "FAIL"
            )
            if results["BED_CALIBRATION"] != "PASS":
                raise DiagnosticFailure(map_failure("bed_calibration"))
            bed = root / "bed.dcm"
            ok, info = _direct(rad, gain, "BED", bed)
            results["BED_DIRECT_CONVERSION"] = "PASS" if ok else "FAIL"
            if not ok:
                raise DiagnosticFailure(map_failure("bed_conversion"))
            try:
                validate_dicom_structure(bed)
                bed_valid = True
            except Exception:
                bed_valid = False
            results["BED_DICOM_STRUCTURE"] = "PASS" if bed_valid else "FAIL"
            if not bed_valid:
                raise DiagnosticFailure(map_failure("bed_dicom"))
            results["BED_CALIBRATION_SELECTION"] = (
                "DETERMINISTICALLY_INFERRED_PASS"
                if results["runtime_provenance"] == "MATCHES_WORKFLOW_SHA"
                else "UNPROVEN"
            )
            trx_rad, trx_gain = root / "trx-rad.npz", root / "trx-gain.npz"
            rewrite_detector_mode(rad, trx_rad)
            rewrite_detector_mode(gain, trx_gain)
            tm, tgm = _metadata(trx_rad), _metadata(trx_gain)
            identity = (
                np.array_equal(rm["raw"], tm["raw"])
                and np.array_equal(gm["raw"], tgm["raw"])
                and np.array_equal(gm["dark"], tgm["dark"])
                and tm["mode"] == tgm["mode"] == "TRX"
                and tm["gainid"] == tgm["id"]
            )
            results["SYNTHETIC_THORAX_PIXEL_IDENTITY"] = "PASS" if identity else "FAIL"
            trx_cal = find_calibration(
                Path("/var/www/mpips-runtime/calibration"),
                "TRX",
                tm["raw"].shape,
                tm["camera"],
                tgm["camera"],
            )
            record_calibration(results, "TRX", trx_cal)
            results["TRX_CALIBRATION"] = (
                "PASS"
                if trx_cal["present"]
                and trx_cal["validated"]
                and trx_cal["fingerprint"]
                and trx_cal["remap"]
                and trx_cal["compatible"]
                else "FAIL"
            )
            if not identity:
                raise DiagnosticFailure(map_failure("trx_compatibility"))
            if results["TRX_CALIBRATION"] != "PASS":
                raise DiagnosticFailure(map_failure("trx_calibration"))
            thorax = root / "thorax.dcm"
            ok, info = _direct(trx_rad, trx_gain, "THORAX", thorax)
            results["SYNTHETIC_THORAX_DIRECT_CONVERSION"] = "PASS" if ok else "FAIL"
            if not ok:
                raise DiagnosticFailure(map_failure("thorax_conversion"))
            try:
                validate_dicom_structure(thorax)
                thorax_valid = True
            except Exception:
                thorax_valid = False
            results["SYNTHETIC_THORAX_DICOM_STRUCTURE"] = (
                "PASS" if thorax_valid else "FAIL"
            )
            if not thorax_valid:
                raise DiagnosticFailure(map_failure("thorax_dicom"))
            results["THORAX_CALIBRATION_SELECTION"] = (
                "DETERMINISTICALLY_INFERRED_PASS"
                if results["runtime_provenance"] == "MATCHES_WORKFLOW_SHA"
                else "UNPROVEN"
            )
            worker_candidates = _docker(
                "ps",
                "-q",
                "--filter",
                "label=com.docker.swarm.service.name=mhcs_core_image-worker",
            ).splitlines()
            worker_info = discover_worker(worker_candidates)
            results["MHCS_IMAGE_WORKER"] = worker_info["classification"]
            worker = worker_info.get("container")
            if worker and results["MHCS_IMAGE_WORKER"] == "PASS":
                networks = _docker(
                    "inspect",
                    "--format",
                    "{{json .NetworkSettings.Networks}}",
                    worker,
                    check=False,
                )
                results["MHCS_PRIVATE_NETWORK"] = (
                    "PASS" if "mhcs-mpips-integration-v1" in networks else "FAIL"
                )
            else:
                results["MHCS_PRIVATE_NETWORK"] = "NOT_RUN"
            if worker and results["MHCS_PRIVATE_NETWORK"] == "PASS":
                bed_mhcs = _mhcs_probe(
                    worker,
                    rad,
                    gain,
                    _manifest(rad, gain, "BED"),
                    root / "mhcs-bed.dcm",
                )
                stage = bed_mhcs.get("stage")
                results["MHCS_MPIPS_CONFIG"] = (
                    "FAIL" if stage in {"bootstrap", "config"} else "PASS"
                )
                results["MHCS_MPIPS_TARGET"] = bed_mhcs.get("target", "UNPROVEN")
                results["MHCS_MPIPS_DNS"] = (
                    "FAIL"
                    if stage == "dns"
                    else "PASS" if stage not in {"bootstrap", "config"} else "NOT_RUN"
                )
                results["MHCS_MPIPS_HEALTH"] = (
                    "FAIL"
                    if stage == "health"
                    else (
                        "PASS"
                        if stage not in {"bootstrap", "config", "dns"}
                        else "NOT_RUN"
                    )
                )
                results["MHCS_MPIPS_HEALTH_STATUS"] = bed_mhcs.get(
                    "health_status", "UNPROVEN"
                )
                results["MHCS_BED_MPIPSCLIENT"] = classify_mhcs_probe(bed_mhcs, "BED")
                results["MHCS_BED_DICOM_STRUCTURE"] = (
                    "PASS" if bed_mhcs.get("dicom_structure") else "FAIL"
                )
                thorax_mhcs = _mhcs_probe(
                    worker,
                    trx_rad,
                    trx_gain,
                    _manifest(trx_rad, trx_gain, "THORAX"),
                    root / "mhcs-thorax.dcm",
                )
                results["MHCS_THORAX_MPIPSCLIENT"] = classify_mhcs_probe(
                    thorax_mhcs, "THORAX"
                )
                results["MHCS_THORAX_DICOM_STRUCTURE"] = (
                    "PASS" if thorax_mhcs.get("dicom_structure") else "FAIL"
                )
            else:
                results["MHCS_BED_MPIPSCLIENT"] = results["MHCS_THORAX_MPIPSCLIENT"] = (
                    "NOT_RUN"
                )
                results["MHCS_BED_DICOM_STRUCTURE"] = results[
                    "MHCS_THORAX_DICOM_STRUCTURE"
                ] = "NOT_RUN"
            results["FINAL_DIAGNOSTIC_CLASSIFICATION"] = final_classification(results)
        except DiagnosticFailure as exc:
            results["FINAL_DIAGNOSTIC_CLASSIFICATION"] = exc.classification
        except Exception as exc:
            results["FINAL_DIAGNOSTIC_CLASSIFICATION"] = "DIAGNOSTIC_INTERNAL_FAILURE"
            results["error"] = type(exc).__name__
    results["CLEANUP"] = "PASS" if not Path(raw_dir).exists() else "FAIL"
    if results["CLEANUP"] == "FAIL":
        results["FINAL_DIAGNOSTIC_CLASSIFICATION"] = "DIAGNOSTIC_INTERNAL_FAILURE"
    lines = [
        "# Production DICOM diagnostic",
        "",
        *[
            f"{key}={results.get(key, 'NOT_RUN')}"
            for key in SUMMARY_FIELDS
            if key in results
        ],
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.summary:
        Path(args.summary).write_text(report + "\n")
    return (
        0
        if results.get("FINAL_DIAGNOSTIC_CLASSIFICATION")
        != "DIAGNOSTIC_INTERNAL_FAILURE"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
