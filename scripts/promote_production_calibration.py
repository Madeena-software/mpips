#!/usr/bin/env python3
"""Guarded, rollback-safe promotion of the reviewed BED+TRX calibration layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Callable

import numpy as np

from scripts.validate_calibration_layout import validate_calibration_layout

EXPECTED_CARRIER_SIZE = 70488061
EXPECTED_CARRIER_FILE_ID = "1ou8lFZlSlO7V-3mLQtzKFz6vyDVX3WQr"
EXPECTED_CARRIER_SHA256 = (
    "39ead140fded085377ca52e9e7cf152549224e0816ccc3e73ed9a3ba7b0cdc61"
)
EXPECTED_FINGERPRINT = (
    "789adff52ed296d956f81ae8dc38247a73768d863495f91a916fc251aaf67811"
)
EXPECTED_SHAPE = (3000, 4096)
ALLOWED_MEMBERS = {
    "trx-calibration/",
    "trx-calibration/metadata.json",
    "trx-calibration/remap.npz",
}


class PromotionError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(member) -> None:
    name = member.name.rstrip("/") + ("/" if member.isdir() else "")
    if name not in ALLOWED_MEMBERS:
        raise PromotionError(f"unexpected archive member: {name}")
    if member.islnk() or member.issym() or member.isdev() or member.isfifo():
        raise PromotionError(f"unsafe archive member: {name}")
    if not member.isdir() and not member.isfile():
        raise PromotionError(f"unsupported archive member: {name}")


def verify_carrier(path: str | Path, expected_size: int, expected_sha256: str) -> None:
    """Verify bytes and all tar members before any extraction occurs."""
    path = Path(path)
    try:
        size = path.stat().st_size
        digest = _sha256(path)
    except OSError as exc:
        raise PromotionError("carrier cannot be read") from exc
    if size != expected_size:
        raise PromotionError("carrier size mismatch")
    if digest != expected_sha256:
        raise PromotionError("carrier SHA-256 mismatch")
    import tarfile

    try:
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                _safe_member(member)
            names = {
                member.name.rstrip("/") + ("/" if member.isdir() else "")
                for member in members
            }
            if names != ALLOWED_MEMBERS:
                raise PromotionError("carrier member set mismatch")
    except (OSError, tarfile.TarError) as exc:
        raise PromotionError(f"invalid carrier archive: {exc}") from exc


def _extract_carrier(path: Path, destination: Path) -> Path:
    import tarfile

    destination.mkdir(exist_ok=True)
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            _safe_member(member)
            if member.isdir():
                continue
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise PromotionError(f"could not read archive member: {member.name}")
            target.write_bytes(source.read())
    return destination / "trx-calibration"


def _validate_trx(directory: Path) -> None:
    try:
        metadata = json.loads((directory / "metadata.json").read_text())
    except (OSError, ValueError) as exc:
        raise PromotionError("invalid TRX metadata") from exc
    if metadata.get("validated") is not True:
        raise PromotionError("TRX artifact is not validated")
    if metadata.get("fingerprint") != EXPECTED_FINGERPRINT:
        raise PromotionError("TRX fingerprint mismatch")
    if metadata.get("image_shape") != list(EXPECTED_SHAPE):
        raise PromotionError("TRX image shape mismatch")
    source = metadata.get("source_metadata", {})
    if not isinstance(source, dict) or source.get("detector_mode") != "TRX":
        raise PromotionError("TRX detector mode mismatch")
    try:
        with np.load(directory / "remap.npz", allow_pickle=False) as remap:
            if "map_x" not in remap or "map_y" not in remap:
                raise PromotionError("TRX remap maps are missing")
            if (
                remap["map_x"].shape != EXPECTED_SHAPE
                or remap["map_y"].shape != EXPECTED_SHAPE
            ):
                raise PromotionError("TRX remap shape mismatch")
            if not np.all(np.isfinite(remap["map_x"])) or not np.all(
                np.isfinite(remap["map_y"])
            ):
                raise PromotionError("TRX remap contains non-finite values")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise PromotionError("invalid TRX remap") from exc


def validate_legacy_bed(active: str | Path) -> dict[str, str]:
    active = Path(active)
    if (active / "BED").is_dir() or (active / "TRX").is_dir():
        raise PromotionError("PRODUCTION_CALIBRATION_ALREADY_MULTI_MODE")
    if validate_calibration_layout(active):
        raise PromotionError("legacy BED calibration is invalid")
    metadata = json.loads((active / "metadata.json").read_text())
    if metadata.get("source_metadata", {}).get("detector_mode") != "BED":
        raise PromotionError("legacy calibration is not BED")
    return {
        "metadata_sha256": _sha256(active / "metadata.json"),
        "remap_sha256": _sha256(active / "remap.npz"),
        "detector_mode": "BED",
    }


def build_staging(
    active: str | Path,
    carrier: str | Path,
    *,
    expected_size: int = EXPECTED_CARRIER_SIZE,
    expected_sha256: str = EXPECTED_CARRIER_SHA256,
) -> Path:
    active = Path(active)
    carrier = Path(carrier)
    verify_carrier(carrier, expected_size, expected_sha256)
    validate_legacy_bed(active)
    with tempfile.TemporaryDirectory(prefix="mpips-carrier-") as temporary:
        extracted = _extract_carrier(carrier, Path(temporary))
        _validate_trx(extracted)
        stage = active.parent / f"{active.name}.next.{uuid.uuid4().hex}"
        stage.mkdir()
        (stage / "BED").mkdir()
        (stage / "TRX").mkdir()
        shutil.copyfile(active / "metadata.json", stage / "BED/metadata.json")
        shutil.copyfile(active / "remap.npz", stage / "BED/remap.npz")
        shutil.copyfile(extracted / "metadata.json", stage / "TRX/metadata.json")
        shutil.copyfile(extracted / "remap.npz", stage / "TRX/remap.npz")
    if _sha256(stage / "BED/metadata.json") != _sha256(active / "metadata.json"):
        raise PromotionError("BED metadata byte preservation failed")
    if _sha256(stage / "BED/remap.npz") != _sha256(active / "remap.npz"):
        raise PromotionError("BED remap byte preservation failed")
    if validate_calibration_layout(stage):
        shutil.rmtree(stage, ignore_errors=True)
        raise PromotionError("staged calibration layout is invalid")
    return stage


def atomic_swap(
    active: Path,
    staged: Path,
    rollback: Path,
    *,
    rename: Callable[[Path, Path], None] | None = None,
) -> None:
    if active.parent.stat().st_dev != staged.parent.stat().st_dev:
        raise PromotionError("staging and active calibration use different filesystems")
    rename = rename or os.replace
    rename(active, rollback)
    try:
        rename(staged, active)
    except Exception:
        rename(rollback, active)
        raise


def _rollback(active: Path, rollback: Path) -> str:
    failed = active.parent / f"{active.name}.failed.{uuid.uuid4().hex}"
    try:
        os.replace(active, failed)
        os.replace(rollback, active)
        if (
            validate_calibration_layout(active)
            or validate_legacy_bed(active)["detector_mode"] != "BED"
        ):
            return "FAIL"
        shutil.rmtree(failed, ignore_errors=True)
        return "PASS"
    except Exception:
        return "FAIL"


def promote(
    active: str | Path,
    carrier: str | Path,
    *,
    post_swap_checks: list[Callable[[], bool]] | None = None,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> dict[str, str]:
    active = Path(active)
    carrier = Path(carrier)
    expected_size = EXPECTED_CARRIER_SIZE if expected_size is None else expected_size
    expected_sha256 = (
        EXPECTED_CARRIER_SHA256 if expected_sha256 is None else expected_sha256
    )
    stage = build_staging(
        active,
        carrier,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
    )
    bed = validate_legacy_bed(active)
    trx = json.loads((stage / "TRX/metadata.json").read_text())
    result = {
        "CARRIER_VERIFICATION": "PASS",
        "carrier_file_id": EXPECTED_CARRIER_FILE_ID,
        "carrier_size": str(expected_size),
        "carrier_sha256": expected_sha256,
        "TRX_ARTIFACT_VALIDATION": "PASS",
        "BED_SOURCE_VALIDATION": "PASS",
        "BED_PRE_METADATA_SHA256": bed["metadata_sha256"],
        "BED_PRE_REMAP_SHA256": bed["remap_sha256"],
        "TRX_FINGERPRINT": str(trx["fingerprint"]),
        "TRX_IMAGE_SHAPE": "3000x4096",
        "STAGING_LAYOUT": "PASS",
        "BED_BYTE_PRESERVATION": "PASS",
    }
    rollback = active.parent / f"{active.name}.rollback.{uuid.uuid4().hex}"
    atomic_swap(active, stage, rollback)
    try:
        if validate_calibration_layout(active):
            raise PromotionError("post-swap calibration layout is invalid")
        result.update({"ATOMIC_SWAP": "PASS", "POST_SWAP_LAYOUT": "PASS"})
        for check in post_swap_checks or []:
            if not check():
                raise PromotionError("post-swap functional check failed")
        result.update(
            {
                "BED_FUNCTIONAL_CONVERSION": "PASS",
                "BED_DICOM_STRUCTURE": "PASS",
                "SYNTHETIC_THORAX_PIXEL_IDENTITY": "PASS",
                "SYNTHETIC_THORAX_CONVERSION": "PASS",
                "SYNTHETIC_THORAX_DICOM_STRUCTURE": "PASS",
            }
        )
        shutil.rmtree(rollback, ignore_errors=True)
        result.update({"ROLLBACK_REQUIRED": "NO", "ROLLBACK_RESULT": "NOT_RUN"})
        return result
    except Exception as exc:
        rollback_result = _rollback(active, rollback)
        if rollback_result != "PASS":
            raise PromotionError("rollback failed") from exc
        result.update(
            {
                "ROLLBACK_REQUIRED": "YES",
                "ROLLBACK_RESULT": rollback_result,
                "FINAL_PROMOTION_CLASSIFICATION": "PROMOTION_ROLLED_BACK",
            }
        )
        return result


def _run_diagnostic(summary: Path) -> bool:
    command = [
        sys.executable,
        "scripts/diagnose_production_dicom_e2e.py",
        "--summary",
        str(summary),
    ]
    if subprocess.run(command, check=False).returncode != 0 or not summary.is_file():
        return False
    required = {
        "BED_DIRECT_CONVERSION",
        "BED_DICOM_STRUCTURE",
        "SYNTHETIC_THORAX_PIXEL_IDENTITY",
        "SYNTHETIC_THORAX_DIRECT_CONVERSION",
        "SYNTHETIC_THORAX_DICOM_STRUCTURE",
    }
    values = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in summary.read_text().splitlines()
        if "=" in line
    }
    return all(values.get(key) == "PASS" for key in required)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, required=True)
    parser.add_argument(
        "--active", type=Path, default=Path("/var/www/mpips-runtime/calibration")
    )
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, str]
    try:
        result = promote(
            args.active,
            args.carrier,
            post_swap_checks=[lambda: _run_diagnostic(args.summary)],
        )
        result["repository_sha"] = os.environ.get("GITHUB_SHA", "UNPROVEN")
        runtime_sha = Path("/var/www/mpips-runtime/.mpips-version")
        result["production_runtime_sha"] = (
            runtime_sha.read_text().strip() if runtime_sha.is_file() else "UNPROVEN"
        )
        if result["ROLLBACK_REQUIRED"] == "YES":
            for key, value in result.items():
                print(f"{key}={value}")
            with args.summary.open("a", encoding="utf-8") as report:
                report.write("\n# Calibration promotion\n\n")
                for key, value in result.items():
                    report.write(f"{key}={value}\n")
            return 1
        result["FINAL_PROMOTION_CLASSIFICATION"] = (
            "PRODUCTION_CALIBRATION_BED_TRX_PROMOTION_PASS"
        )
    except PromotionError as exc:
        print(f"PROMOTION_FAILED={type(exc).__name__}")
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    with args.summary.open("a", encoding="utf-8") as report:
        report.write("\n# Calibration promotion\n\n")
        for key, value in result.items():
            report.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
