#!/usr/bin/env python3
"""Read-only Stage C acceptance of real TRX data through production MPIPS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, cast

import numpy as np
import requests

from scripts import promote_production_calibration as promotion

EXPECTED_RUNTIME_SHA = "dd7c21eead66a2c5396522a2310f5dd9cbd85b85"
EXPECTED_API_IMAGE = f"mpips-api:{EXPECTED_RUNTIME_SHA}"
EXPECTED_WORKER_IMAGE = f"mpips-npz-worker:{EXPECTED_RUNTIME_SHA}"
EXPECTED_TRX_FINGERPRINT = (
    "1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492"
)
EXPECTED_BED_HASHES = {
    "metadata.json": "15741968305c7b74bc1c84f5487216f7e944cdeaace0150500ede4aa32326ecd",
    "remap.npz": "f5ae883bd17960a56c60add99d5e8d2f393ea9427ec5ce3fd1a5d0b920c671bb",
}
API_URL = "http://127.0.0.1:8014"
CALIBRATION_ROOT = Path("/var/www/mpips-runtime/calibration")
MANIFEST_PATH = Path(__file__).parents[1] / (
    "artifacts/test-data/real-thorax-trx-da5277082.json"
)
FINAL_CLASSIFICATION = "PRODUCTION_REAL_TRX_ACCEPTANCE_PASS"


class VerificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if len(manifest["radiographs"]) != 3:
            raise ValueError("manifest must contain three radiographs")
        expected = manifest["expected"]
        if expected != {
            "detector_mode": "TRX",
            "external_detector_type": "THORAX",
            "image_shape": [3000, 4096],
            "gain_id": "1787726609597",
        }:
            raise ValueError("manifest semantics mismatch")
        entries = [manifest["gain"], *manifest["radiographs"]]
        if len({entry["file_id"] for entry in entries}) != 4:
            raise ValueError("manifest input IDs are not unique")
        if {item["case"] for item in manifest["radiographs"]} != {1, 2, 3}:
            raise ValueError("manifest cases are incomplete")
        return cast(dict[str, Any], manifest)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VerificationError("invalid canonical real TRX manifest") from exc


def validate_runtime_markers(
    runtime_root: Path, api_image: str, worker_image: str | None = None
) -> dict[str, str]:
    runtime = (runtime_root / ".mpips-version").read_text().strip()
    worker = (runtime_root / ".mpips-worker-image").read_text().strip()
    if (
        runtime != EXPECTED_RUNTIME_SHA
        or worker != (worker_image or EXPECTED_WORKER_IMAGE)
        or api_image != EXPECTED_API_IMAGE
    ):
        raise VerificationError("production runtime provenance mismatch")
    return {
        "PRODUCTION_RUNTIME_SHA": runtime,
        "PRODUCTION_API_IMAGE": api_image,
        "PRODUCTION_WORKER_IMAGE": worker,
        "CAMERA_INDEPENDENT_RUNTIME": "PASS",
        "TRX_PIPELINE_RUNTIME": "PASS",
    }


def validate_calibration(calibration_root: Path) -> dict[str, str]:
    if (calibration_root / "metadata.json").exists() or (
        calibration_root / "remap.npz"
    ).exists():
        raise VerificationError("calibration layout is not multimode")
    bed = calibration_root / "BED"
    trx = calibration_root / "TRX"
    metadata = json.loads((trx / "metadata.json").read_text(encoding="utf-8"))
    with np.load(trx / "remap.npz", allow_pickle=False) as remap:
        remap_shape = tuple(int(value) for value in remap["map_x"].shape)
    if (
        metadata.get("fingerprint") != EXPECTED_TRX_FINGERPRINT
        or metadata.get("image_shape") != [3000, 4096]
        or tuple(metadata.get("expanded_origin_xy", ())) != (42, -73)
        or remap_shape != (3045, 4114)
    ):
        raise VerificationError("TRX calibration fingerprint or layout mismatch")
    hashes = {name: sha256(bed / name) for name in EXPECTED_BED_HASHES}
    if hashes != EXPECTED_BED_HASHES:
        raise VerificationError("BED calibration byte identity mismatch")
    if promotion.container_calibration_view() != "PASS":
        raise VerificationError("production container calibration view mismatch")
    return {
        "TRX_CALIBRATION_FINGERPRINT": EXPECTED_TRX_FINGERPRINT,
        "TRX_CALIBRATION_LAYOUT": "PASS",
        "BED_CALIBRATION_BYTE_IDENTITY": "PASS",
        "CALIBRATION_MUTATION": "NO",
    }


def require_health(api_url: str = API_URL) -> None:
    response = requests.get(f"{api_url}/health", timeout=10)
    if response.status_code != 200:
        raise VerificationError(f"health check returned HTTP {response.status_code}")


def download_inputs(destination: Path, manifest: dict[str, Any]) -> None:
    import gdown

    entries = [manifest["gain"], *manifest["radiographs"]]
    for entry in entries:
        final = destination / entry["filename"]
        partial = final.with_name(final.name + ".part")
        try:
            if (
                gdown.download(id=entry["file_id"], output=str(partial), quiet=True)
                is None
            ):
                raise VerificationError("STAGE_C_REAL_INPUT_DOWNLOAD_FAILED")
            promotion._verify_npz_archive(partial, entry["size"], entry["sha256"])
            final_path = partial.with_name(partial.name.removesuffix(".part"))
            partial.replace(final_path)
        except (OSError, RuntimeError, zipfile.BadZipFile, VerificationError) as exc:
            raise VerificationError("STAGE_C_REAL_INPUT_INTEGRITY_FAILED") from exc
        finally:
            partial.unlink(missing_ok=True)


def verify(
    *,
    runtime_root: Path = Path("/var/www/mpips-runtime"),
    calibration_root: Path = CALIBRATION_ROOT,
    api_url: str = API_URL,
) -> dict[str, str]:
    manifest = load_manifest()
    result = validate_runtime_markers(runtime_root, EXPECTED_API_IMAGE)
    observed_runtime = promotion.runtime_preflight(runtime_dir=runtime_root)
    if any(
        observed_runtime.get(key) != result[key]
        for key in (
            "PRODUCTION_RUNTIME_SHA",
            "PRODUCTION_API_IMAGE",
            "PRODUCTION_WORKER_IMAGE",
        )
    ) or any(
        observed_runtime.get(key) != "PASS"
        for key in ("CAMERA_INDEPENDENT_RUNTIME", "TRX_PIPELINE_RUNTIME")
    ):
        raise VerificationError("STAGE_C_RUNTIME_PREFLIGHT_FAILED")
    result.update(observed_runtime)
    if not os.environ.get("MPIPS_API_KEY"):
        raise VerificationError("STAGE_C_RUNTIME_PREFLIGHT_FAILED")
    require_health(api_url)
    calibration_before = validate_calibration(calibration_root)
    result.update(calibration_before)
    result["PRE_DOWNLOAD_PREFLIGHT"] = "PASS"
    with tempfile.TemporaryDirectory(prefix="mpips-real-trx-stage-c-") as directory:
        data_dir = Path(directory)
        download_inputs(data_dir, manifest)
        inputs = promotion.validate_real_thorax_inputs(data_dir)
        result.update(inputs)
        if inputs["REAL_THORAX_INPUTS_ALL_PASS"] != "PASS":
            raise VerificationError("STAGE_C_REAL_INPUT_INTEGRITY_FAILED")
        result.update(promotion.run_real_thorax_checks(data_dir))
        if result.get("REAL_THORAX_ALL_PASS") != "PASS":
            raise VerificationError("STAGE_C_REAL_TRX_IMAGE_ACCEPTANCE_FAILED")
    require_health(api_url)
    if validate_calibration(calibration_root) != calibration_before:
        raise VerificationError("STAGE_C_CALIBRATION_PREFLIGHT_FAILED")
    result.update(
        {
            "POST_ACCEPTANCE_HEALTH": "PASS",
            "REAL_TRX_TEMP_CLEANUP": "PASS",
            "PRODUCTION_REAL_TRX_ACCEPTANCE": "PASS",
            "FINAL_STAGE_C_CLASSIFICATION": FINAL_CLASSIFICATION,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    try:
        result = verify()
    except (OSError, ValueError, VerificationError, requests.RequestException) as exc:
        print(f"FINAL_STAGE_C_CLASSIFICATION={exc}")
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    if args.summary:
        args.summary.write_text("\n".join(f"{k}={v}" for k, v in result.items()) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
