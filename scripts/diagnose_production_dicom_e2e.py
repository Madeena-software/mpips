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
    "TRX_CALIBRATION",
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
    if info.get("http_status") != 200 or info.get("health_status") != 200:
        return "FAIL"
    if info.get("content_type", "").split(";", 1)[
        0
    ] != "application/dicom" or not info.get("response_bytes"):
        return "FAIL"
    return "PASS" if info.get("dicom_structure") is True else "DICOM_INVALID"


def safe_cleanup_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if path.parent != root.resolve() or path == root.resolve():
        raise ValueError("cleanup path escapes diagnostic directory")
    return path


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
    root: Path, mode: str, shape: tuple[int, int], camera: dict
) -> dict:
    calibration = _calibrations(root).get(mode)
    if not calibration:
        return {"present": False, "validated": False, "compatible": False}
    source_camera = calibration["source"].get("camera_params", {})
    camera_ids = {
        str(value.get(key, ""))
        for value in (camera, source_camera)
        for key in ("serialNumber", "cameraSerial")
        if value.get(key)
    }
    metadata = calibration["meta"]
    compatible = (
        tuple(metadata.get("image_shape", ())) == tuple(shape) and len(camera_ids) <= 1
    )
    return {
        "present": True,
        "validated": metadata.get("validated") is True,
        "compatible": compatible,
        "mode": mode,
        "shape": tuple(metadata.get("image_shape", ())),
        "camera_compatible": len(camera_ids) <= 1,
        "fingerprint": bool(metadata.get("fingerprint")),
    }


def validate_dicom_structure(path: Path) -> dict:
    ds = pydicom.dcmread(path)
    if not getattr(ds, "file_meta", None) or not getattr(
        ds.file_meta, "TransferSyntaxUID", None
    ):
        raise ValueError("missing DICOM file meta or transfer syntax")
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
        if not getattr(ds, key, None):
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
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();
$base = config('mhcs.mpips.base_url');
$host = parse_url($base, PHP_URL_HOST);
$dns = $host ? gethostbyname($host) !== $host || filter_var($host, FILTER_VALIDATE_IP) : false;
$health = Illuminate\\Support\\Facades\\Http::timeout(10)->get(
    rtrim($base, '/').'/health'
); # noqa: E501
$r = (new App\\Modules\\ImageGateway\\Infrastructure\\MpipsClient())->convert(
    $argv[1], $argv[2], file_get_contents($argv[3])
); # noqa: E501
file_put_contents($argv[4], $r->body());
echo json_encode([
    'status'=>$r->status(), 'content_type'=>$r->header('Content-Type'),
    'bytes'=>strlen($r->body()), 'target'=>parse_url($base, PHP_URL_SCHEME).'://'.parse_url($base, PHP_URL_HOST).':'.(parse_url($base, PHP_URL_PORT) ?: 80),
    'health_status'=>$health->status(), 'dns'=>$dns
]); # noqa: E501
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
        _docker("cp", f"{container}:{remote}/out.dcm", str(out))
        info = json.loads(result)
        info["http_status"] = info.pop("status", None)
        info["response_bytes"] = info.pop("bytes", 0)
        info["dicom_structure"] = False
        try:
            info["dicom_structure"] = validate_dicom_structure(out) is not None
        except Exception:
            pass
        return info
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
            _download(RADIOGRAPH_ID, rad)
            _download(GAIN_ID, gain)
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
            )
            results["BED_CALIBRATION"] = (
                "PASS"
                if bed_cal["present"] and bed_cal["validated"] and bed_cal["compatible"]
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
            if results["BED_CALIBRATION_SELECTION"] == "UNPROVEN":
                raise DiagnosticFailure("PRODUCTION_RUNTIME_SHA_UNPROVEN")
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
            )
            results["TRX_CALIBRATION"] = (
                "PASS"
                if trx_cal["present"] and trx_cal["validated"] and trx_cal["compatible"]
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
                results["MHCS_MPIPS_CONFIG"] = (
                    "PASS" if bed_mhcs.get("target") else "FAIL"
                )
                results["MHCS_MPIPS_TARGET"] = bed_mhcs.get("target", "UNPROVEN")
                results["MHCS_MPIPS_DNS"] = "PASS" if bed_mhcs.get("dns") else "FAIL"
                results["MHCS_MPIPS_HEALTH"] = (
                    "PASS" if bed_mhcs.get("health_status") == 200 else "FAIL"
                )
                results["MHCS_MPIPS_HEALTH_STATUS"] = bed_mhcs.get(
                    "health_status", "UNPROVEN"
                )
                results["MHCS_BED_MPIPSCLIENT"] = classify_mhcs_response(bed_mhcs)
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
                results["MHCS_THORAX_MPIPSCLIENT"] = classify_mhcs_response(thorax_mhcs)
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
            required = (
                "BED_INPUT_COMPATIBILITY",
                "BED_CALIBRATION",
                "BED_DIRECT_CONVERSION",
                "BED_DICOM_STRUCTURE",
                "TRX_CALIBRATION",
                "SYNTHETIC_THORAX_PIXEL_IDENTITY",
                "SYNTHETIC_THORAX_DIRECT_CONVERSION",
                "SYNTHETIC_THORAX_DICOM_STRUCTURE",
                "MHCS_IMAGE_WORKER",
                "MHCS_PRIVATE_NETWORK",
                "MHCS_MPIPS_CONFIG",
                "MHCS_MPIPS_DNS",
                "MHCS_MPIPS_HEALTH",
                "MHCS_BED_MPIPSCLIENT",
                "MHCS_BED_DICOM_STRUCTURE",
                "MHCS_THORAX_MPIPSCLIENT",
                "MHCS_THORAX_DICOM_STRUCTURE",
            )
            results["FINAL_DIAGNOSTIC_CLASSIFICATION"] = (
                "PRODUCTION_MPIPS_BED_AND_SYNTHETIC_THORAX_MHCS_E2E_PASS"
                if all(results.get(key) == "PASS" for key in required)
                and results.get("BED_CALIBRATION_SELECTION", "").endswith("PASS")
                and results.get("THORAX_CALIBRATION_SELECTION", "").endswith("PASS")
                else "MHCS_THORAX_MPIPSCLIENT_FAILED"
            )
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
