from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.dicom_enrichment import enrich_dicom_file
from mpips.conversion.metadata import build_converter_metadata_json
from mpips.conversion.validation import validate_dicom_dataset
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.npz_io import (
    NPZValidationError,
    load_gain_catalog,
    load_radiograph,
    to_uint16,
    write_tiff,
)
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays


def _apply_startup_resource_limits() -> None:
    try:
        import resource

        cpu_limit = int(os.getenv("MPIPS_DICOM_WORKER_CPU_SECONDS", "120"))
        mem_limit = int(
            os.getenv("MPIPS_DICOM_WORKER_MEMORY_BYTES", str(2 * 1024 * 1024 * 1024))
        )

        if cpu_limit > 0:
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 5))
            except (ValueError, OSError):
                pass

        if mem_limit > 0 and hasattr(resource, "RLIMIT_DATA"):
            try:
                resource.setrlimit(resource.RLIMIT_DATA, (mem_limit, mem_limit))
            except (ValueError, OSError):
                pass
    except ImportError:
        pass


def execute_conversion_worker(args_path: str, result_path: str) -> None:
    _apply_startup_resource_limits()

    result_data: Dict[str, Any] = {
        "status": "failed",
        "sanitized_error_code": "UNKNOWN_ERROR",
        "output_byte_size": 0,
        "validation_flags": {"valid": False},
    }

    try:
        with Path(args_path).open("r", encoding="utf-8") as f:
            args = json.load(f)

        radiograph_npz_path = args["radiograph_npz_path"]
        gain_npz_path = args["gain_npz_path"]
        manifest_data = args["manifest"]
        output_dicom_path = args["output_dicom_path"]

        manifest = MHCSManifest.model_validate(manifest_data)

        # 1. Load radiograph and gain catalog
        rad_info = load_radiograph(radiograph_npz_path)
        gain_catalog = load_gain_catalog([gain_npz_path])

        expected_gain_id = manifest.capture.gain.gain_id
        if rad_info["gain_id"] != expected_gain_id:
            raise NPZValidationError(
                "Radiograph gain_id does not match manifest gain_id"
            )

        if expected_gain_id not in gain_catalog.records:
            raise NPZValidationError("Gain NPZ does not contain required gain_id")

        gain_record = gain_catalog.records[expected_gain_id]

        raw = rad_info["raw"]
        dark = gain_record.dark
        flat = gain_record.flat

        if raw.shape != dark.shape or raw.shape != flat.shape:
            raise NPZValidationError("Radiograph raw and gain dark/flat shapes differ")

        rad_mode = rad_info["detector_mode"]
        if rad_mode != gain_record.detector_mode:
            raise NPZValidationError("Radiograph and gain detector modes differ")

        # Camera serial verification if present in both
        rad_cam_sn = rad_info.get("camera_params", {}).get("serialNumber")
        gain_cam_sn = gain_record.camera_params.get("serialNumber")
        if rad_cam_sn and gain_cam_sn and str(rad_cam_sn) != str(gain_cam_sn):
            raise NPZValidationError(
                "Camera serial number mismatch between radiograph and gain"
            )

        # 2. Process image pipeline
        processed_img = process_radiography_arrays(raw, dark, flat, rad_mode)
        processed_uint16 = to_uint16(processed_img)

        # 3. Intermediate TIFF & adapter JSON generation
        with tempfile.TemporaryDirectory(prefix="mpips-worker-stage-") as temp_dir:
            temp_tiff = Path(temp_dir) / "processed.tiff"
            temp_json = Path(temp_dir) / "adapter.json"

            write_tiff(temp_tiff, processed_uint16)

            converter_dict = build_converter_metadata_json(manifest)
            with temp_json.open("w", encoding="utf-8") as f:
                json.dump(converter_dict, f)

            # 4. Invoke Pak Andre's approved converter
            tiff_json_to_dcm(
                str(temp_tiff), str(temp_json), str(output_dicom_path)
            )  # type: ignore[no-untyped-call]

        # 5. Enrich final DICOM dataset
        enrich_dicom_file(output_dicom_path, manifest)

        # 6. Validate final DICOM dataset
        val_res = validate_dicom_dataset(
            output_dicom_path, manifest, processed_uint16.shape
        )

        out_size = Path(output_dicom_path).stat().st_size

        result_data = {
            "status": "success",
            "sanitized_error_code": None,
            "output_byte_size": out_size,
            "validation_flags": {
                "valid": True,
                "pixel_bytes": val_res.get("pixel_bytes", 0),
            },
        }

    except NPZValidationError:
        result_data["sanitized_error_code"] = "NPZ_VALIDATION_ERROR"
    except ValueError:
        result_data["sanitized_error_code"] = "MANIFEST_OR_DATA_ERROR"
    except Exception:
        result_data["sanitized_error_code"] = "CONVERSION_WORKER_FAILURE"
    finally:
        try:
            with Path(result_path).open("w", encoding="utf-8") as f:
                json.dump(result_data, f)
        except Exception:
            pass

    if result_data["status"] != "success":
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)
    execute_conversion_worker(sys.argv[1], sys.argv[2])
