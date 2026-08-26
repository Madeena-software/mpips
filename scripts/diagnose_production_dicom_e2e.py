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


def validate_dicom_structure(path: Path) -> dict:
    ds = pydicom.dcmread(path)
    if not getattr(ds, "file_meta", None) or not getattr(ds, "TransferSyntaxUID", None):
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
    results["runtime_provenance"] = (
        "MATCHES_WORKFLOW_SHA"
        if deployed == workflow_sha
        else "DIFFERS_FROM_WORKFLOW_SHA" if deployed != "UNPROVEN" else "UNPROVEN"
    )


def _mhcs_probe(
    container: str, rad: Path, gain: Path, manifest: str, out: Path
) -> bool:
    token = f"mpips-diagnostic-{uuid.uuid4()}"
    remote = f"/tmp/{token}"
    php = Path(tempfile.mktemp(suffix=".php"))
    php.write_text("""<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();
$base = config('mhcs.mpips.base_url');
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
    'health_status'=>$health->status()
]); # noqa: E501
""")
    try:
        _docker("exec", container, "mkdir", remote)
        for source, name in ((rad, "rad.npz"), (gain, "gain.npz"), (php, "probe.php")):
            _docker("cp", str(source), f"{container}:{remote}/{name}")
        manifest_path = Path(tempfile.mktemp())
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
        return info.get("status") == 200 and info.get("health_status") == 200
    finally:
        _docker("exec", container, "rm", "-rf", remote, check=False)
        php.unlink(missing_ok=True)
        if "manifest_path" in locals():
            manifest_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    args = parser.parse_args()
    results = {"repository_workflow_sha": os.environ.get("GITHUB_SHA", "UNPROVEN")}
    with tempfile.TemporaryDirectory(prefix="mpips-diagnostic-") as raw_dir:
        root = Path(raw_dir)
        try:
            _runtime_provenance(results)
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
            cals = _calibrations(Path("/var/www/mpips-runtime/calibration"))
            for mode in ("BED", "TRX"):
                cal = cals.get(mode)
                results[f"{mode}_CALIBRATION"] = (
                    "PASS"
                    if cal
                    and cal["meta"].get("validated") is True
                    and list(cal["meta"].get("image_shape", []))
                    == list(rm["raw"].shape)
                    else "FAIL"
                )
            if not compatible or results["BED_CALIBRATION"] != "PASS":
                raise RuntimeError("BED preflight failed")
            bed = root / "bed.dcm"
            ok, info = _direct(rad, gain, "BED", bed)
            results["BED_DIRECT_CONVERSION"] = "PASS" if ok else "FAIL"
            results["BED_DIRECT"] = info
            results["BED_DICOM_STRUCTURE"] = (
                "PASS" if ok and validate_dicom_structure(bed) else "FAIL"
            )
            results["BED_CALIBRATION_SELECTION"] = (
                "DETERMINISTICALLY_INFERRED_PASS" if ok else "FAIL"
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
            if results["TRX_CALIBRATION"] != "PASS" or not identity:
                raise RuntimeError("TRX preflight failed")
            thorax = root / "thorax.dcm"
            ok, info = _direct(trx_rad, trx_gain, "THORAX", thorax)
            results["SYNTHETIC_THORAX_DIRECT_CONVERSION"] = "PASS" if ok else "FAIL"
            results["THORAX_DIRECT"] = info
            results["SYNTHETIC_THORAX_DICOM_STRUCTURE"] = (
                "PASS" if ok and validate_dicom_structure(thorax) else "FAIL"
            )
            results["THORAX_CALIBRATION_SELECTION"] = (
                "DETERMINISTICALLY_INFERRED_PASS" if ok else "FAIL"
            )
            worker = _docker(
                "ps",
                "-q",
                "--filter",
                "label=com.docker.swarm.service.name=mhcs_core_image-worker",
            )
            results["MHCS_IMAGE_WORKER"] = "PASS" if worker else "FAIL"
            if worker:
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
            if worker and ok:
                results["MHCS_BED_MPIPSCLIENT"] = (
                    "PASS"
                    if _mhcs_probe(
                        worker,
                        rad,
                        gain,
                        _manifest(rad, gain, "BED"),
                        root / "mhcs-bed.dcm",
                    )
                    else "FAIL"
                )
                results["MHCS_THORAX_MPIPSCLIENT"] = (
                    "PASS"
                    if _mhcs_probe(
                        worker,
                        trx_rad,
                        trx_gain,
                        _manifest(trx_rad, trx_gain, "THORAX"),
                        root / "mhcs-thorax.dcm",
                    )
                    else "FAIL"
                )
            else:
                results["MHCS_BED_MPIPSCLIENT"] = results["MHCS_THORAX_MPIPSCLIENT"] = (
                    "NOT_RUN"
                )
            results["FINAL_DIAGNOSTIC_CLASSIFICATION"] = (
                "PRODUCTION_MPIPS_BED_AND_SYNTHETIC_THORAX_MHCS_E2E_PASS"
                if results.get("MHCS_THORAX_MPIPSCLIENT") == "PASS"
                else "MHCS_THORAX_MPIPSCLIENT_FAILED"
            )
        except Exception as exc:
            results.setdefault(
                "FINAL_DIAGNOSTIC_CLASSIFICATION", "DIAGNOSTIC_INTERNAL_FAILURE"
            )
            results["error"] = type(exc).__name__
    lines = [
        "# Production DICOM diagnostic",
        "",
        *[f"{key}={value}" for key, value in results.items() if key != "error"],
        "",
        "CLEANUP=PASS",
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
