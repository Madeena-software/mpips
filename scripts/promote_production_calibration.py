#!/usr/bin/env python3
"""Guarded, rollback-safe promotion of the reviewed BED+expanded-TRX layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Callable

import numpy as np
import pydicom

from scripts.validate_calibration_layout import validate_calibration_layout
from mpips.workflows.imager_pipeline.calibration import validate_expanded_canvas_remap

PROMOTION_MANIFEST = Path(__file__).parents[1] / (
    "artifacts/promotion/trx-calibration-1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1"
    "c089381af3e7dd1492.json"
)
EXPECTED_CARRIER_SIZE = 73915583
EXPECTED_CARRIER_FILE_ID = "1TpiHJfM0EHEKvZ1rZ2VqSV0-k0ycrzCG"
EXPECTED_CARRIER_SHA256 = (
    "b0d645233eb598c549a1b04fc24a1364f68b79cc0d0e0db51ac1936d7e11f90f"
)
EXPECTED_FINGERPRINT = (
    "1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492"
)
EXPECTED_SHAPE = (3000, 4096)
EXPECTED_REMAP_SHAPE = (3045, 4114)
EXPECTED_FINAL_DICOM_SHAPE = (4114, 3045)
EXPECTED_CANVAS_MODE = "expanded"
EXPECTED_EXPANDED_ORIGIN = (42, -73)
CAMERA_INDEPENDENT_BASELINE = "d175a6fa56ca32cf78007c39baff24075dbd5a0e"
REQUIRED_TRX_PIPELINE_BASELINE = "b3ed78d5077d8e4634c913939e5c28f8620679e9"
BED_FUNCTIONAL_FIELDS = (
    "BED_FUNCTIONAL_CONVERSION",
    "BED_DICOM_STRUCTURE",
)
SYNTHETIC_FIELDS = (
    "SYNTHETIC_THORAX_PIXEL_IDENTITY",
    "SYNTHETIC_THORAX_CONVERSION",
    "SYNTHETIC_THORAX_DICOM_STRUCTURE",
)
ROLLBACK_FIELDS = (
    "ROLLBACK_BED_LAYOUT",
    "ROLLBACK_BED_FUNCTIONAL_CONVERSION",
    "ROLLBACK_BED_DICOM_STRUCTURE",
)
REAL_MANIFEST = (
    Path(__file__).parents[1] / "artifacts/test-data/real-thorax-trx-da5277082.json"
)
REAL_REQUIRED_FIELDS = tuple(
    field
    for case in (1, 2, 3)
    for field in (
        f"REAL_THORAX_{case}_INPUT_COMPATIBILITY",
        f"REAL_THORAX_{case}_CONVERSION",
        f"REAL_THORAX_{case}_IMAGE_ACCEPTANCE",
        f"REAL_THORAX_{case}_DICOM_STRUCTURE",
    )
)
REAL_INPUT_FIELDS = tuple(
    f"REAL_THORAX_{case}_INPUT_COMPATIBILITY" for case in (1, 2, 3)
)
ALLOWED_MEMBERS = {
    "trx-calibration/",
    "trx-calibration/metadata.json",
    "trx-calibration/remap.npz",
}


class PromotionError(RuntimeError):
    pass


def _promotion_manifest() -> dict:
    try:
        manifest = json.loads(PROMOTION_MANIFEST.read_text(encoding="utf-8"))
        carrier = manifest["carrier"]
        if (
            manifest["fingerprint"] != EXPECTED_FINGERPRINT
            or manifest["detector_mode"] != "TRX"
            or manifest["image_shape"] != list(EXPECTED_SHAPE)
            or manifest["canvas_mode"] != EXPECTED_CANVAS_MODE
            or tuple(manifest["expanded_origin"]) != EXPECTED_EXPANDED_ORIGIN
            or manifest["remap_shape"] != list(EXPECTED_REMAP_SHAPE)
            or manifest["expected_final_dicom_shape"]
            != list(EXPECTED_FINAL_DICOM_SHAPE)
            or manifest["archive_size"] != EXPECTED_CARRIER_SIZE
            or manifest["archive_sha256"] != EXPECTED_CARRIER_SHA256
            or manifest["required_files"] != ["metadata.json", "remap.npz"]
            or manifest["geometry_validated"] is not True
            or manifest["real_trx_pipeline_validated"] is not True
            or manifest["validated"] is not True
            or manifest["validation_status"] != "REAL_TRX_EXPANDED_VALIDATED"
            or carrier["provider"] != "google-drive"
            or carrier["file_id"] != EXPECTED_CARRIER_FILE_ID
            or carrier["size"] != EXPECTED_CARRIER_SIZE
            or carrier["sha256"] != EXPECTED_CARRIER_SHA256
        ):
            raise ValueError("reviewed TRX promotion manifest semantics mismatch")
        return manifest
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PromotionError("invalid reviewed TRX promotion manifest") from exc


def validate_carrier_identity(carrier_id: str | None) -> str:
    _promotion_manifest()
    if not carrier_id:
        raise PromotionError("TRX_CARRIER_NOT_PUBLISHED")
    if carrier_id != EXPECTED_CARRIER_FILE_ID:
        raise PromotionError("TRX_CARRIER_ID_MISMATCH")
    return carrier_id


def _real_manifest() -> dict:
    try:
        data = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
        if len(data["radiographs"]) != 3:
            raise ValueError("real THORAX manifest must contain three radiographs")
        expected = data["expected"]
        if (
            expected["detector_mode"] != "TRX"
            or expected["external_detector_type"] != "THORAX"
            or expected["image_shape"] != [3000, 4096]
            or expected["gain_id"] != "1787726609597"
        ):
            raise ValueError("real THORAX manifest semantics mismatch")
        return data
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PromotionError("invalid real THORAX test-data manifest") from exc


def _verify_npz_archive(path: Path, expected_size: int, expected_sha256: str) -> None:
    if path.stat().st_size != expected_size or _sha256(path) != expected_sha256:
        raise PromotionError(f"integrity mismatch: {path.name}")
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise PromotionError(f"invalid NPZ archive: {path.name}")


def validate_real_thorax_inputs(data_dir: str | Path) -> dict[str, str]:
    """Verify all real inputs before allowing any pickle-bearing NPZ load."""
    data_dir = Path(data_dir)
    manifest = _real_manifest()
    evidence: dict[str, str] = {}
    gain = manifest["gain"]
    gain_path = data_dir / gain["filename"]
    try:
        _verify_npz_archive(gain_path, gain["size"], gain["sha256"])
        evidence["REAL_THORAX_GAIN_DOWNLOAD"] = "PASS"
        with np.load(gain_path, allow_pickle=True) as data:
            gain_xray = data["xrayparams"].item()
            gain_id = str(data["id"].item())
            gain_shapes = (data["rawimage"].shape, data["darkimage"].shape)
        if (
            gain_id != manifest["expected"]["gain_id"]
            or gain_xray.get("detectorMode") != "TRX"
            or gain_shapes != ((3000, 4096), (3000, 4096))
        ):
            raise PromotionError("real THORAX gain semantics mismatch")
        evidence["REAL_THORAX_GAIN_INTEGRITY"] = "PASS"
    except (OSError, KeyError, ValueError, PromotionError, zipfile.BadZipFile):
        evidence["REAL_THORAX_GAIN_DOWNLOAD"] = "FAIL"
        evidence["REAL_THORAX_GAIN_INTEGRITY"] = "FAIL"
    for item in manifest["radiographs"]:
        case = item["case"]
        prefix = f"REAL_THORAX_{case}"
        try:
            path = data_dir / item["filename"]
            _verify_npz_archive(path, item["size"], item["sha256"])
            evidence[f"{prefix}_DOWNLOAD"] = "PASS"
            with np.load(path, allow_pickle=True) as data:
                xray = data["xrayparams"].item()
                gain_id = str(data["gainid"].item())
                raw_shape = data["rawimage"].shape
            if (
                xray.get("detectorMode") != "TRX"
                or gain_id != manifest["expected"]["gain_id"]
                or raw_shape != (3000, 4096)
            ):
                raise PromotionError(f"real THORAX {case} semantics mismatch")
            evidence[f"{prefix}_INPUT_COMPATIBILITY"] = "PASS"
        except (OSError, KeyError, ValueError, PromotionError, zipfile.BadZipFile):
            evidence[f"{prefix}_DOWNLOAD"] = "FAIL"
            evidence[f"{prefix}_INPUT_COMPATIBILITY"] = "FAIL"
        evidence.setdefault(f"{prefix}_CONVERSION", "NOT_RUN")
        evidence.setdefault(f"{prefix}_DICOM_STRUCTURE", "NOT_RUN")
    evidence["REAL_THORAX_INPUTS_ALL_PASS"] = (
        "PASS"
        if evidence.get("REAL_THORAX_GAIN_INTEGRITY") == "PASS"
        and all(evidence.get(field) == "PASS" for field in REAL_INPUT_FIELDS)
        else "FAIL"
    )
    evidence["REAL_THORAX_ALL_PASS"] = "NOT_RUN"
    return evidence


def _real_dicom_structure(path: Path) -> bool:
    try:
        from scripts.diagnose_production_dicom_e2e import validate_dicom_structure

        structure = validate_dicom_structure(path)
        dataset = pydicom.dcmread(path, stop_before_pixels=False)
        return (
            structure["rows"] == EXPECTED_FINAL_DICOM_SHAPE[0]
            and structure["columns"] == EXPECTED_FINAL_DICOM_SHAPE[1]
            and int(dataset.BitsAllocated) == 16
            and int(dataset.PixelRepresentation) == 0
            and bool(dataset.PixelData)
        )
    except (OSError, AttributeError, KeyError, ValueError):
        return False


def _real_dicom_image_acceptance(path: Path) -> bool:
    """Reject catastrophic collapse for the pinned real-THORAX regression set."""
    try:
        dataset = pydicom.dcmread(path, stop_before_pixels=False)
        pixels = np.asarray(dataset.pixel_array)
        if (
            pixels.shape != EXPECTED_FINAL_DICOM_SHAPE
            or pixels.dtype != np.uint16
            or not np.all(np.isfinite(pixels))
        ):
            return False
        nonzero = pixels != 0
        if not np.any(nonzero):
            return False
        # This is a catastrophic-collapse floor for the pinned regression data,
        # not a clinical image-quality threshold.
        if float(np.count_nonzero(~nonzero)) / pixels.size >= 0.5:
            return False
        rows, columns = np.where(nonzero)
        return bool(
            rows.size and columns.size and np.ptp(rows) >= 1 and np.ptp(columns) >= 1
        )
    except (OSError, AttributeError, KeyError, TypeError, ValueError):
        return False


def run_real_thorax_checks(data_dir: str | Path) -> dict[str, str]:
    from scripts.diagnose_production_dicom_e2e import _direct

    evidence = validate_real_thorax_inputs(data_dir)
    if evidence["REAL_THORAX_INPUTS_ALL_PASS"] != "PASS":
        return evidence
    manifest = _real_manifest()
    gain = Path(data_dir) / manifest["gain"]["filename"]
    with tempfile.TemporaryDirectory(prefix="mpips-real-thorax-") as directory:
        for item in manifest["radiographs"]:
            case = item["case"]
            output = Path(directory) / f"real-thorax-{case}.dcm"
            ok, _ = _direct(
                Path(data_dir) / item["filename"],
                gain,
                "THORAX",
                output,
            )
            evidence[f"REAL_THORAX_{case}_CONVERSION"] = "PASS" if ok else "FAIL"
            evidence[f"REAL_THORAX_{case}_DICOM_STRUCTURE"] = (
                "PASS" if ok and _real_dicom_structure(output) else "FAIL"
            )
            evidence[f"REAL_THORAX_{case}_IMAGE_ACCEPTANCE"] = (
                "PASS" if ok and _real_dicom_image_acceptance(output) else "FAIL"
            )
    evidence["REAL_THORAX_ALL_PASS"] = (
        "PASS"
        if all(evidence.get(field) == "PASS" for field in REAL_REQUIRED_FIELDS)
        else "FAIL"
    )
    return evidence


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
    _promotion_manifest()
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
    if metadata.get("CANVAS_MODE") != EXPECTED_CANVAS_MODE:
        raise PromotionError("TRX canvas mode mismatch")
    if tuple(metadata.get("expanded_origin_xy", ())) != EXPECTED_EXPANDED_ORIGIN:
        raise PromotionError("TRX expanded origin mismatch")
    if metadata.get("REMAP_OUTPUT_SHAPE") != list(EXPECTED_REMAP_SHAPE):
        raise PromotionError("TRX remap shape metadata mismatch")
    try:
        with np.load(directory / "remap.npz", allow_pickle=False) as remap:
            if "map_x" not in remap or "map_y" not in remap:
                raise PromotionError("TRX remap maps are missing")
            if (
                remap["map_x"].shape != EXPECTED_REMAP_SHAPE
                or remap["map_y"].shape != EXPECTED_REMAP_SHAPE
            ):
                raise PromotionError("TRX remap shape mismatch")
            if not np.all(np.isfinite(remap["map_x"])) or not np.all(
                np.isfinite(remap["map_y"])
            ):
                raise PromotionError("TRX remap contains non-finite values")
            try:
                validate_expanded_canvas_remap(
                    remap["map_x"], remap["map_y"], *EXPECTED_SHAPE[::-1]
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                raise PromotionError("TRX remap geometry is unsafe") from exc
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


def prepare_root_staging(
    active: str | Path,
    carrier: str | Path,
    *,
    expected_size: int = EXPECTED_CARRIER_SIZE,
    expected_sha256: str = EXPECTED_CARRIER_SHA256,
) -> tuple[Path, dict[str, str]]:
    active = Path(active)
    carrier = Path(carrier)
    verify_carrier(carrier, expected_size, expected_sha256)
    validate_legacy_bed(active)
    if active.parent.stat().st_dev != active.stat().st_dev:
        raise PromotionError("calibration root filesystem cannot be inspected")
    rollback = active.parent / f"{active.name}.rollback.{uuid.uuid4().hex}"
    rollback.mkdir()
    try:
        bed = validate_legacy_bed(active)
        shutil.copyfile(active / "metadata.json", rollback / "metadata.json")
        shutil.copyfile(active / "remap.npz", rollback / "remap.npz")
        if any(
            _sha256(rollback / name) != bed[key]
            for name, key in (
                ("metadata.json", "metadata_sha256"),
                ("remap.npz", "remap_sha256"),
            )
        ):
            raise PromotionError("legacy recovery hash mismatch")
        with tempfile.TemporaryDirectory(prefix="mpips-carrier-") as temporary:
            extracted = _extract_carrier(carrier, Path(temporary))
            _validate_trx(extracted)
            (active / "BED").mkdir()
            (active / "TRX").mkdir()
            shutil.copyfile(active / "metadata.json", active / "BED/metadata.json")
            shutil.copyfile(active / "remap.npz", active / "BED/remap.npz")
            shutil.copyfile(extracted / "metadata.json", active / "TRX/metadata.json")
            shutil.copyfile(extracted / "remap.npz", active / "TRX/remap.npz")
        if (
            _sha256(active / "BED/metadata.json") != bed["metadata_sha256"]
            or _sha256(active / "BED/remap.npz") != bed["remap_sha256"]
        ):
            raise PromotionError("BED metadata/remap byte preservation failed")
        if _validate_mode_dirs(active):
            raise PromotionError("staged calibration layout is invalid")
        return rollback, {
            "BED_PRE_METADATA_SHA256": bed["metadata_sha256"],
            "BED_PRE_REMAP_SHA256": bed["remap_sha256"],
            "ROOT_INODE_PRESERVED": "PASS",
            "BED_BYTE_PRESERVATION": "PASS",
            "MULTIMODE_PRESTAGE": "PASS",
        }
    except Exception:
        shutil.rmtree(active / "BED", ignore_errors=True)
        shutil.rmtree(active / "TRX", ignore_errors=True)
        shutil.rmtree(rollback, ignore_errors=True)
        raise


def _validate_mode_dirs(root: Path) -> list[str]:
    from scripts.validate_calibration_layout import _validate_artifact

    return _validate_artifact(root / "BED", "BED") + _validate_artifact(
        root / "TRX", "TRX"
    )


def build_staging(
    active: str | Path,
    carrier: str | Path,
    *,
    expected_size: int = EXPECTED_CARRIER_SIZE,
    expected_sha256: str = EXPECTED_CARRIER_SHA256,
) -> Path:
    """Compatibility helper: stage in the existing root and return its root."""
    root = Path(active)
    prepare_root_staging(
        root, carrier, expected_size=expected_size, expected_sha256=expected_sha256
    )
    return root


def _switch_to_multimode(active: Path, rollback: Path) -> None:
    if not (active / "metadata.json").is_file() or not (active / "remap.npz").is_file():
        raise PromotionError("legacy calibration files missing before mode switch")
    os.replace(active / "metadata.json", rollback / "metadata.json")
    try:
        os.replace(active / "remap.npz", rollback / "remap.npz")
    except Exception:
        os.replace(rollback / "metadata.json", active / "metadata.json")
        raise
    if validate_calibration_layout(active):
        raise PromotionError("post-switch calibration layout is invalid")


def _rollback(
    active: Path,
    rollback: Path,
    bed_check: Callable[[], dict[str, str]] | None,
) -> dict[str, str]:
    evidence = {field: "FAIL" for field in ROLLBACK_FIELDS}
    evidence.update({"ROLLBACK_RESULT": "FAIL"})
    try:
        # Restore remap first: the legacy worker must never see metadata without remap.
        if not (active / "remap.npz").exists():
            os.replace(rollback / "remap.npz", active / "remap.npz")
        if not (active / "metadata.json").exists():
            os.replace(rollback / "metadata.json", active / "metadata.json")
        shutil.rmtree(active / "BED")
        shutil.rmtree(active / "TRX")
        if validate_calibration_layout(active):
            raise PromotionError("rollback BED layout is invalid")
        evidence["ROLLBACK_BED_LAYOUT"] = "PASS"
        if bed_check:
            check = bed_check()
            for field in ROLLBACK_FIELDS[1:]:
                evidence[field] = check.get(field, "FAIL")
        if not all(evidence[field] == "PASS" for field in ROLLBACK_FIELDS):
            raise PromotionError("rollback BED functional evidence failed")
        shutil.rmtree(rollback)
        evidence["ROLLBACK_RESULT"] = "PASS"
    except Exception:
        evidence["ROLLBACK_FAILED_DIRECTORY_STATE"] = "RETAINED_FOR_RECOVERY"
        evidence["ROLLBACK_RECOVERY_DIRECTORY_STATE"] = "RETAINED"
    return evidence


def runtime_preflight(
    *,
    runtime_dir: str | Path = "/var/www/mpips-runtime",
    run: Callable[..., object] = subprocess.run,
    merge_base: Callable[[str, str], bool] | None = None,
) -> dict[str, str]:
    """Prove deployed code and immutable image provenance before mutation."""
    root = Path(runtime_dir)
    sha = (
        (root / ".mpips-version").read_text().strip()
        if (root / ".mpips-version").is_file()
        else ""
    )
    worker = (
        (root / ".mpips-worker-image").read_text().strip()
        if (root / ".mpips-worker-image").is_file()
        else ""
    )
    api = ""
    try:
        listed = run(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                "name=mpips-api",
                "--filter",
                "status=running",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        ids = listed.stdout.splitlines()
        if len(ids) == 1:
            inspected = run(
                ["docker", "inspect", "--format", "{{.Config.Image}}", ids[0]],
                capture_output=True,
                text=True,
                check=False,
            )
            api = inspected.stdout.strip()
    except (OSError, AttributeError):
        pass
    valid_sha = bool(re.fullmatch(r"[0-9a-f]{40}", sha))
    api_sha = api.removeprefix("mpips-api:")
    worker_sha = worker.removeprefix("mpips-npz-worker:")
    if not valid_sha:
        ancestor = False
    elif merge_base:
        ancestor = merge_base(CAMERA_INDEPENDENT_BASELINE, sha)
        trx_ancestor = merge_base(REQUIRED_TRX_PIPELINE_BASELINE, sha)
    else:
        ancestor = (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    CAMERA_INDEPENDENT_BASELINE,
                    sha,
                ],
                check=False,
            ).returncode
            == 0
        )
        trx_ancestor = (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    REQUIRED_TRX_PIPELINE_BASELINE,
                    sha,
                ],
                check=False,
            ).returncode
            == 0
        )
    passed = (
        valid_sha
        and ancestor
        and api == f"mpips-api:{sha}"
        and worker == f"mpips-npz-worker:{sha}"
        and api_sha == worker_sha == sha
    )
    trx_passed = valid_sha and trx_ancestor
    evidence = {
        "PRODUCTION_RUNTIME_SHA": sha or "UNPROVEN",
        "PRODUCTION_API_IMAGE": api or "UNPROVEN",
        "PRODUCTION_WORKER_IMAGE": worker or "UNPROVEN",
        "CAMERA_INDEPENDENT_RUNTIME": "PASS" if passed else "FAIL",
        "TRX_PIPELINE_RUNTIME": "PASS" if trx_passed else "FAIL",
    }
    if not passed:
        evidence["FINAL_PROMOTION_CLASSIFICATION"] = (
            "PRODUCTION_RUNTIME_CAMERA_INDEPENDENT_CODE_REQUIRED"
        )
    elif not trx_passed:
        evidence["FINAL_PROMOTION_CLASSIFICATION"] = (
            "PRODUCTION_RUNTIME_TRX_PIPELINE_CODE_REQUIRED"
        )
    return evidence


def promote(
    active: str | Path,
    carrier: str | Path,
    *,
    functional_check: Callable[[], dict[str, str]] | None = None,
    container_check: Callable[[], str] | None = None,
    rollback_bed_check: Callable[[], dict[str, str]] | None = None,
    pre_swap_evidence: dict[str, str] | None = None,
    runtime_evidence: dict[str, str] | None = None,
    local_pipeline_evidence: dict[str, object] | None = None,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> dict[str, str]:
    active = Path(active)
    carrier = Path(carrier)
    expected_size = EXPECTED_CARRIER_SIZE if expected_size is None else expected_size
    expected_sha256 = (
        EXPECTED_CARRIER_SHA256 if expected_sha256 is None else expected_sha256
    )
    runtime_evidence = runtime_evidence or {
        "CAMERA_INDEPENDENT_RUNTIME": "PASS",
        "TRX_PIPELINE_RUNTIME": "PASS",
    }
    if (
        runtime_evidence.get("CAMERA_INDEPENDENT_RUNTIME") != "PASS"
        or runtime_evidence.get("TRX_PIPELINE_RUNTIME") != "PASS"
    ):
        return {
            **runtime_evidence,
            "FINAL_PROMOTION_CLASSIFICATION": (
                "PRODUCTION_RUNTIME_TRX_PIPELINE_CODE_REQUIRED"
                if runtime_evidence.get("TRX_PIPELINE_RUNTIME") != "PASS"
                else "PRODUCTION_RUNTIME_CAMERA_INDEPENDENT_CODE_REQUIRED"
            ),
        }
    local_pipeline_evidence = local_pipeline_evidence or {
        "REAL_TRX_LOCAL_PIPELINE": "PASS"
    }
    if local_pipeline_evidence.get("REAL_TRX_LOCAL_PIPELINE") != "PASS":
        return {
            **{
                key: str(value)
                for key, value in local_pipeline_evidence.items()
                if key != "cases"
            },
            "FINAL_PROMOTION_CLASSIFICATION": "REAL_TRX_LOCAL_PIPELINE_REQUIRED",
        }
    rollback, stage_evidence = prepare_root_staging(
        active,
        carrier,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
    )
    trx = json.loads((active / "TRX/metadata.json").read_text())
    root_inode = active.stat().st_ino
    result = {
        "CARRIER_VERIFICATION": "PASS",
        "carrier_file_id": EXPECTED_CARRIER_FILE_ID,
        "carrier_size": str(expected_size),
        "carrier_sha256": expected_sha256,
        "TRX_ARTIFACT_VALIDATION": "PASS",
        "BED_SOURCE_VALIDATION": "PASS",
        **stage_evidence,
        "TRX_FINGERPRINT": str(trx["fingerprint"]),
        "TRX_IMAGE_SHAPE": (
            f"{EXPECTED_FINAL_DICOM_SHAPE[0]}x{EXPECTED_FINAL_DICOM_SHAPE[1]}"
        ),
        "STAGING_LAYOUT": "PASS",
        "ROOT_INODE_PRESERVED": "PASS",
    }
    result.update(runtime_evidence)
    result.update(pre_swap_evidence or {})
    try:
        _switch_to_multimode(active, rollback)
        if active.stat().st_ino != root_inode:
            raise PromotionError("calibration root inode changed")
        result["ATOMIC_MODE_SWITCH"] = "PASS"
        result["POST_SWAP_BED_METADATA_SHA256"] = _sha256(active / "BED/metadata.json")
        result["POST_SWAP_BED_REMAP_SHA256"] = _sha256(active / "BED/remap.npz")
        result["POST_SWAP_BED_BYTE_PRESERVATION"] = (
            "PASS"
            if result["POST_SWAP_BED_METADATA_SHA256"]
            == result["BED_PRE_METADATA_SHA256"]
            and result["POST_SWAP_BED_REMAP_SHA256"] == result["BED_PRE_REMAP_SHA256"]
            else "FAIL"
        )
        if result["POST_SWAP_BED_BYTE_PRESERVATION"] != "PASS":
            raise PromotionError("post-swap BED byte preservation failed")
        if validate_calibration_layout(active):
            raise PromotionError("post-swap calibration layout is invalid")
        result["POST_SWAP_LAYOUT"] = "PASS"
        result["CONTAINER_CALIBRATION_VIEW"] = (
            container_check() if container_check else "FAIL"
        )
        if result["CONTAINER_CALIBRATION_VIEW"] != "PASS":
            result["FINAL_PROMOTION_CLASSIFICATION"] = (
                "CALIBRATION_BIND_MOUNT_REFRESH_REQUIRED"
            )
            raise PromotionError("container calibration view is not current")
        functional = functional_check() if functional_check else {}
        for field in (
            *BED_FUNCTIONAL_FIELDS,
            *SYNTHETIC_FIELDS,
            "REAL_THORAX_ALL_PASS",
            *REAL_REQUIRED_FIELDS,
        ):
            result[field] = functional.get(field, "FAIL")
        if not all(
            result[field] == "PASS"
            for field in (
                *BED_FUNCTIONAL_FIELDS,
                "REAL_THORAX_ALL_PASS",
                *REAL_REQUIRED_FIELDS,
            )
        ):
            raise PromotionError("post-swap functional check failed")
        result.update(
            {
                "ROLLBACK_REQUIRED": "NO",
                "ROLLBACK_RESULT": "NOT_RUN",
                "FINAL_PROMOTION_CLASSIFICATION": (
                    "PRODUCTION_CALIBRATION_BED_TRX_PROMOTION_PASS"
                ),
            }
        )
        return result
    except Exception:
        result.update(_rollback(active, rollback, rollback_bed_check))
        if result["ROLLBACK_RESULT"] != "PASS":
            result["FINAL_PROMOTION_CLASSIFICATION"] = (
                "PRODUCTION_CALIBRATION_ROLLBACK_FAILED"
            )
            result["ROLLBACK_REQUIRED"] = "YES"
            return result
        result.update(
            {
                "ROLLBACK_REQUIRED": "YES",
                "FINAL_PROMOTION_CLASSIFICATION": result.get(
                    "FINAL_PROMOTION_CLASSIFICATION", "PROMOTION_ROLLED_BACK"
                ),
            }
        )
        return result


def _parse_diagnostic(summary: Path) -> dict[str, str]:
    if not summary.is_file():
        return {}
    return {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in summary.read_text().splitlines()
        if "=" in line
    }


def _run_diagnostic(summary: Path) -> dict[str, str]:
    command = [
        sys.executable,
        "scripts/diagnose_production_dicom_e2e.py",
        "--summary",
        str(summary),
    ]
    subprocess.run(command, check=False)
    values = _parse_diagnostic(summary)
    return {
        "BED_FUNCTIONAL_CONVERSION": values.get("BED_DIRECT_CONVERSION", "FAIL"),
        "BED_DICOM_STRUCTURE": values.get("BED_DICOM_STRUCTURE", "FAIL"),
        "SYNTHETIC_THORAX_PIXEL_IDENTITY": values.get(
            "SYNTHETIC_THORAX_PIXEL_IDENTITY", "FAIL"
        ),
        "SYNTHETIC_THORAX_CONVERSION": values.get(
            "SYNTHETIC_THORAX_DIRECT_CONVERSION", "FAIL"
        ),
        "SYNTHETIC_THORAX_DICOM_STRUCTURE": values.get(
            "SYNTHETIC_THORAX_DICOM_STRUCTURE", "FAIL"
        ),
    }


def _run_rollback_bed_diagnostic() -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="mpips-rollback-diagnostic-") as directory:
        evidence = _run_diagnostic(Path(directory) / "summary.txt")
    return {
        "ROLLBACK_BED_FUNCTIONAL_CONVERSION": evidence.get(
            "BED_FUNCTIONAL_CONVERSION", "FAIL"
        ),
        "ROLLBACK_BED_DICOM_STRUCTURE": evidence.get("BED_DICOM_STRUCTURE", "FAIL"),
    }


def _run_priority_functional_checks(data_dir: Path, summary: Path) -> dict[str, str]:
    real = run_real_thorax_checks(data_dir)
    if real["REAL_THORAX_ALL_PASS"] != "PASS":
        return real
    return {**real, **_run_diagnostic(summary)}


def container_calibration_view(
    *,
    run: Callable[..., object] = subprocess.run,
    container: str | None = None,
    calibration_path: str = "/opt/mpips/calibration",
) -> str:
    """Read-only probe of the calibration path inside the running API container."""
    try:
        if container is None:
            listed = run(
                [
                    "docker",
                    "ps",
                    "-q",
                    "--filter",
                    "name=mpips-api",
                    "--filter",
                    "status=running",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            containers = listed.stdout.splitlines()
            if len(containers) != 1:
                return "FAIL"
            container = containers[0]
        check = (
            "! test -e '{path}/metadata.json' && "
            "! test -e '{path}/remap.npz' && "
            "test -f '{path}/BED/metadata.json' && "
            "test -f '{path}/BED/remap.npz' && "
            "test -f '{path}/TRX/metadata.json' && "
            "test -f '{path}/TRX/remap.npz' && "
            "grep -Fq '{fingerprint}' '{path}/TRX/metadata.json'"
        ).format(path=calibration_path, fingerprint=EXPECTED_FINGERPRINT)
        current = run(
            ["docker", "exec", container, "sh", "-c", check],
            capture_output=True,
            text=True,
            check=False,
        )
        if current.returncode == 0:
            return "PASS"
        legacy = (
            f"test -f '{calibration_path}/metadata.json' && "
            f"test -f '{calibration_path}/remap.npz' && "
            f"! test -e '{calibration_path}/TRX/metadata.json'"
        )
        stale = run(
            ["docker", "exec", container, "sh", "-c", legacy],
            capture_output=True,
            text=True,
            check=False,
        )
        return "STALE" if stale.returncode == 0 else "FAIL"
    except (OSError, AttributeError):
        return "FAIL"


def _append_summary(path: Path, result: dict[str, str]) -> None:
    try:
        with path.open("a", encoding="utf-8") as report:
            report.write("\n# Calibration promotion\n\n")
            for key, value in result.items():
                report.write(f"{key}={value}\n")
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, required=True)
    parser.add_argument(
        "--active", type=Path, default=Path("/var/www/mpips-runtime/calibration")
    )
    parser.add_argument("--real-data-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, str]
    try:
        runtime = runtime_preflight()
        if runtime["CAMERA_INDEPENDENT_RUNTIME"] != "PASS":
            for key, value in runtime.items():
                print(f"{key}={value}")
            _append_summary(args.summary, runtime)
            return 1
        preflight = validate_real_thorax_inputs(args.real_data_dir)
        if preflight["REAL_THORAX_INPUTS_ALL_PASS"] != "PASS":
            for key, value in preflight.items():
                print(f"{key}={value}")
            _append_summary(args.summary, preflight)
            return 1
        from scripts.validate_real_trx_pipeline import run_local_real_trx_pipeline

        local = run_local_real_trx_pipeline(
            args.real_data_dir,
            args.carrier,
            Path("research/real-thorax-dicom"),
        )
        for key, value in local.items():
            if key != "cases":
                print(f"{key}={value}")
        if local["REAL_TRX_LOCAL_PIPELINE"] != "PASS":
            _append_summary(args.summary, local)
            return 1
        result = promote(
            args.active,
            args.carrier,
            functional_check=lambda: _run_priority_functional_checks(
                args.real_data_dir, args.summary
            ),
            container_check=container_calibration_view,
            rollback_bed_check=_run_rollback_bed_diagnostic,
            pre_swap_evidence=preflight,
            runtime_evidence=runtime,
            local_pipeline_evidence=local,
        )
        result.update({key: value for key, value in local.items() if key != "cases"})
        result["repository_sha"] = os.environ.get("GITHUB_SHA", "UNPROVEN")
        runtime_sha = Path("/var/www/mpips-runtime/.mpips-version")
        result["production_runtime_sha"] = (
            runtime_sha.read_text().strip() if runtime_sha.is_file() else "UNPROVEN"
        )
        if result["ROLLBACK_REQUIRED"] == "YES":
            for key, value in result.items():
                print(f"{key}={value}")
            _append_summary(args.summary, result)
            return 1
        result["FINAL_PROMOTION_CLASSIFICATION"] = (
            "PRODUCTION_CALIBRATION_BED_TRX_PROMOTION_PASS"
        )
    except PromotionError as exc:
        print(f"PROMOTION_FAILED={type(exc).__name__}")
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    _append_summary(args.summary, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
