"""Local, manifest-driven TRX batch conversion."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pydicom

from mpips.api.schemas.dicom import (
    CaptureSchema,
    ExaminationSchema,
    FileManifestSchema,
    MHCSManifest,
    PatientSchema,
    PersonNameSchema,
)
from mpips.conversion.service import run_isolated_dicom_conversion
from mpips.conversion.validation import validate_dicom_dataset
from mpips.workflows.imager_pipeline.npz_io import (
    NPZValidationError,
    load_gain_catalog,
    load_radiograph,
)

_TRX_FILENAME = re.compile(r"^TRX_(?P<id>[0-9]+)(?: \([0-9]+\))?\.npz$")


class ManifestValidationError(ValueError):
    """Raised when an emergency batch manifest is unsafe or invalid."""


class DuplicateCaptureError(ManifestValidationError):
    """Raised when more than one manifest row claims the same TRX identity."""


def parse_trx_filename(filename: str) -> str:
    """Return the numeric TRX identity from one canonical or copy-suffixed name."""
    match = _TRX_FILENAME.fullmatch(Path(filename).name)
    if match is None:
        raise ManifestValidationError(f"Invalid TRX filename: {filename!r}")
    return match.group("id")


def derive_mrn(capture_id: str) -> str:
    if not capture_id.isdecimal() or not capture_id:
        raise ManifestValidationError("TRX capture ID must be numeric")
    return f"MRN-{capture_id}"


def _local_path(value: Any, root: Path, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} must be a non-empty path")
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (root / path).resolve()
    if path.is_absolute() or resolved.is_relative_to(root.resolve()):
        return resolved
    raise ManifestValidationError(f"{field} escapes the manifest directory")


def _load_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"Cannot read manifest: {path}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("cases"), list):
        raise ManifestValidationError("manifest must contain a cases list")
    if not document["cases"]:
        raise ManifestValidationError("manifest cases cannot be empty")
    return document


def _build_case(row: Any, root: Path, index: int) -> tuple[Path, MHCSManifest, str]:
    if not isinstance(row, dict):
        raise ManifestValidationError(f"case {index} must be an object")
    source = _local_path(row.get("source"), root, f"case {index} source")
    capture_id = parse_trx_filename(source.name)
    name = row.get("patient_name")
    if not isinstance(name, str) or not name.strip():
        raise ManifestValidationError(f"case {index} patient_name is required")
    patient = PatientSchema(
        medical_record_number=derive_mrn(capture_id),
        name=PersonNameSchema(full_name=name.strip()),
        sex=row.get("sex", "unknown"),
        birth_date=row.get("birth_date"),
    )
    capture = CaptureSchema(
        capture_id=f"TRX-{capture_id}",
        detector_type="TRX",
        captured_at=row.get("captured_at"),
        radiograph=FileManifestSchema(filename=source.name),
    )
    examination = ExaminationSchema(
        examination_id=row.get("examination_id"),
        performed_at=row.get("performed_at"),
        study_description=row.get("study_description", "CHEST RADIOGRAPH"),
    )
    return (
        source,
        MHCSManifest(patient=patient, capture=capture, examination=examination),
        capture_id,
    )


def _preflight(
    document: dict[str, Any], root: Path
) -> tuple[list[tuple[Path, MHCSManifest, str, str | None]], Path, Path]:
    gain_path = _local_path(document.get("gain_path"), root, "gain_path")
    calibration_dir = _local_path(
        document.get("calibration_dir"), root, "calibration_dir"
    )
    if not calibration_dir.is_dir():
        raise ManifestValidationError("calibration_dir does not exist")
    metadata_path = calibration_dir / "metadata.json"
    remap_path = calibration_dir / "remap.npz"
    if not metadata_path.is_file() or not remap_path.is_file():
        raise ManifestValidationError(
            "calibration requires metadata.json and remap.npz"
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError("calibration metadata is not valid JSON") from exc
    if not isinstance(metadata, dict) or metadata.get("validated") is not True:
        raise ManifestValidationError("calibration is not validated")
    source_metadata = metadata.get("source_metadata")
    if (
        not isinstance(source_metadata, dict)
        or source_metadata.get("detector_mode") != "TRX"
    ):
        raise ManifestValidationError("calibration is not validated for TRX")
    try:
        with np.load(remap_path) as remap:
            if not {"map_x", "map_y"}.issubset(remap.files):
                raise ManifestValidationError("calibration remap lacks map_x/map_y")
            remap_shape = remap["map_x"].shape
            if remap_shape != remap["map_y"].shape:
                raise ManifestValidationError("calibration remap shapes differ")
            expected_shape = tuple(metadata.get("image_shape", ()))
            if len(expected_shape) != 2 or remap_shape != expected_shape:
                raise ManifestValidationError(
                    "calibration remap shape does not match image_shape"
                )
    except ManifestValidationError:
        raise
    except Exception as exc:
        raise ManifestValidationError("calibration remap is not readable") from exc
    try:
        gains = load_gain_catalog([gain_path])
    except (OSError, NPZValidationError) as exc:
        raise ManifestValidationError("gain NPZ failed canonical validation") from exc

    cases: list[tuple[Path, MHCSManifest, str, str | None]] = []
    seen: set[str] = set()
    for index, row in enumerate(document["cases"], start=1):
        source, manifest, capture_id = _build_case(row, root, index)
        if capture_id in seen:
            raise DuplicateCaptureError(f"duplicate TRX capture ID: {capture_id}")
        seen.add(capture_id)
        try:
            radiograph = load_radiograph(source)
            gain = gains.require(str(radiograph["gain_id"]))
        except Exception as exc:
            cases.append((source, manifest, capture_id, type(exc).__name__))
            continue
        error: str | None = None
        if radiograph["detector_mode"] != "TRX" or gain.detector_mode != "TRX":
            error = "ManifestValidationError"
        expected_shape = tuple(metadata.get("image_shape", ()))
        if len(expected_shape) != 2 or tuple(radiograph["raw"].shape) != expected_shape:
            error = "ManifestValidationError"
        if gain.dark.shape != radiograph["raw"].shape:
            error = "ManifestValidationError"
        if gain.flat.shape != radiograph["raw"].shape:
            error = "ManifestValidationError"
        cases.append((source, manifest, capture_id, error))
    return cases, gain_path, calibration_dir


def run_emergency_batch(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    converter: Callable[[MHCSManifest, Path, Path], Any] | None = None,
) -> dict[str, Any]:
    """Preflight and process a local emergency batch into deterministic outputs."""
    manifest_file = Path(manifest_path).resolve()
    root = manifest_file.parent
    document = _load_document(manifest_file)
    cases, gain_path, calibration_dir = _preflight(document, root)
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for source, case_manifest, capture_id, preflight_error in cases:
        mrn = derive_mrn(capture_id)
        output = destination / f"{mrn}.dcm"
        result: dict[str, Any] = {"capture_id": capture_id, "mrn": mrn}
        if preflight_error is not None:
            result["status"] = "failed"
            result["error"] = preflight_error
        elif output.exists():
            try:
                existing = pydicom.dcmread(output, stop_before_pixels=True)
                shape = (int(existing.Rows), int(existing.Columns))
                validate_dicom_dataset(output, case_manifest, shape)
            except Exception as exc:
                result["status"] = "failed"
                result["error"] = type(exc).__name__
            else:
                result["status"] = "skipped"
        else:
            try:
                if converter is None:
                    run_isolated_dicom_conversion(
                        source,
                        gain_path,
                        case_manifest,
                        output,
                        calibration_dir=calibration_dir,
                    )
                else:
                    converter(case_manifest, gain_path, output)
                if not output.is_file() or output.stat().st_size == 0:
                    raise OSError("converter produced no output")
                result["status"] = "completed"
            except Exception as exc:
                output.unlink(missing_ok=True)
                result["status"] = "failed"
                result["error"] = type(exc).__name__
        results.append(result)

    counts: dict[str, int] = {
        "total": len(results),
        "succeeded": sum(
            item["status"] in {"completed", "skipped"} for item in results
        ),
        "failed": sum(item["status"] == "failed" for item in results),
    }
    summary: dict[str, Any] = {
        "counts": counts,
        "items": results,
    }
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "summary.txt").write_text(
        "TRX batch summary\n"
        f"total: {summary['counts']['total']}\n"
        f"succeeded: {summary['counts']['succeeded']}\n"
        f"failed: {summary['counts']['failed']}\n"
        + "\n".join(f"{item['status']}: {item['capture_id']}" for item in results)
        + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a local TRX batch to DICOM")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        document = _load_document(args.manifest.resolve())
        cases, _, _ = _preflight(document, args.manifest.resolve().parent)
        failures = [
            f"{capture_id}: {error}"
            for _, _, capture_id, error in cases
            if error is not None
        ]
        if failures:
            print("preflight failed", file=sys.stderr)
            print("\n".join(failures), file=sys.stderr)
            raise SystemExit(1)
        print(f"preflight passed: {len(document['cases'])} cases")
        return
    summary = run_emergency_batch(args.manifest, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
