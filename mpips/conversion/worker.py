from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

from mpips.workflows.imager_pipeline.npz_io import (
    NPZValidationError,
    load_gain_catalog,
    load_radiograph,
    to_uint16,
    write_tiff,
)
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays


def _apply_startup_resource_limits() -> None:
    """Enforces Linux RLIMIT_CPU and RLIMIT_AS before opening NPZ files."""
    try:
        import resource

        cpu_limit = int(os.getenv("MPIPS_DICOM_WORKER_CPU_SECONDS", "120"))
        mem_limit = int(
            os.getenv("MPIPS_DICOM_WORKER_MEMORY_BYTES", str(2 * 1024 * 1024 * 1024))
        )

        if cpu_limit > 0 and hasattr(resource, "RLIMIT_CPU"):
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 5))
            except (ValueError, OSError) as exc:
                if sys.platform.startswith("linux"):
                    raise RuntimeError(
                        f"Failed to set RLIMIT_CPU on Linux: {exc}"
                    ) from exc

        if mem_limit > 0 and hasattr(resource, "RLIMIT_DATA"):
            try:
                resource.setrlimit(resource.RLIMIT_DATA, (mem_limit, mem_limit))
            except (ValueError, OSError):
                pass
        elif mem_limit > 0 and hasattr(resource, "RLIMIT_AS"):
            try:
                # Use 4GB virtual address space for 64-bit Python C extensions
                # while cgroups limit physical RAM
                as_limit = max(mem_limit, 4 * 1024 * 1024 * 1024)
                resource.setrlimit(resource.RLIMIT_AS, (as_limit, as_limit))
            except (ValueError, OSError):
                pass
    except ImportError:
        if sys.platform.startswith("linux"):
            raise RuntimeError("resource module unavailable on Linux")


def execute_conversion_worker(args_path: str, result_path: str) -> None:
    result_data = {
        "status": "failed",
        "sanitized_error_code": "CONVERSION_WORKER_FAILURE",
        "rows": 0,
        "cols": 0,
        "pixel_bytes": 0,
    }

    try:
        with Path(args_path).open("r", encoding="utf-8") as f:
            args = json.load(f)

        radiograph_npz_path = args["radiograph_npz_path"]
        gain_npz_path = args["gain_npz_path"]
        expected_gain_id = args["expected_gain_id"]
        expected_detector_mode = args.get("expected_detector_mode")
        expected_camera_serial = args.get("expected_camera_serial")
        calibration_dir_str = args.get("calibration_dir")
        max_rows = int(args.get("max_rows", 16384))
        max_cols = int(args.get("max_cols", 16384))
        max_pixels = int(args.get("max_pixels", 268435456))
        output_tiff_path = args["output_tiff_path"]

        # 1. Resolve and validate calibration artifact
        if not calibration_dir_str:
            raise NPZValidationError("Missing calibration_dir in worker arguments")

        cal_dir = Path(calibration_dir_str)
        if not cal_dir.is_dir():
            raise NPZValidationError("Calibration artifact directory does not exist")

        cal_metadata_path = cal_dir / "metadata.json"
        cal_remap_path = cal_dir / "remap.npz"
        if not cal_metadata_path.is_file() or not cal_remap_path.is_file():
            raise NPZValidationError(
                "Calibration artifact missing metadata.json or remap.npz"
            )

        try:
            cal_metadata = json.loads(cal_metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise NPZValidationError(
                f"Invalid calibration metadata JSON: {exc}"
            ) from exc

        if not isinstance(cal_metadata, dict):
            raise NPZValidationError("Calibration metadata is not a dict")

        if cal_metadata.get("validated") is not True:
            raise NPZValidationError("Calibration artifact is not validated")

        cal_fingerprint = cal_metadata.get("fingerprint")
        if not cal_fingerprint or not isinstance(cal_fingerprint, str):
            raise NPZValidationError("Calibration artifact missing valid fingerprint")

        cal_shape_raw = cal_metadata.get("image_shape")
        if not isinstance(cal_shape_raw, (list, tuple)) or len(cal_shape_raw) != 2:
            raise NPZValidationError("Calibration artifact missing valid image_shape")

        expected_cal_shape = (int(cal_shape_raw[0]), int(cal_shape_raw[1]))

        try:
            with np.load(cal_remap_path) as remap_data:
                if "map_x" not in remap_data or "map_y" not in remap_data:
                    raise NPZValidationError("remap.npz missing map_x or map_y arrays")
                map_x = remap_data["map_x"].astype(np.float32)
                map_y = remap_data["map_y"].astype(np.float32)
        except NPZValidationError:
            raise
        except Exception as exc:
            raise NPZValidationError(f"Failed to load remap.npz: {exc}") from exc

        # 2. Load radiograph and gain catalog
        rad_info = load_radiograph(radiograph_npz_path)
        gain_catalog = load_gain_catalog([gain_npz_path])

        if rad_info["gain_id"] != expected_gain_id:
            raise NPZValidationError(
                "Radiograph gain_id does not match expected gain_id"
            )

        if expected_gain_id not in gain_catalog.records:
            raise NPZValidationError("Gain NPZ does not contain required gain_id")

        gain_record = gain_catalog.records[expected_gain_id]

        raw = rad_info["raw"]
        dark = gain_record.dark
        flat = gain_record.flat

        if raw.shape != dark.shape or raw.shape != flat.shape:
            raise NPZValidationError("Radiograph raw and gain dark/flat shapes differ")

        if raw.shape != expected_cal_shape:
            raise NPZValidationError(
                "Radiograph shape does not match calibration image shape"
            )

        if map_x.shape != map_y.shape or map_x.shape != raw.shape:
            raise NPZValidationError(
                "Calibration remap shape does not match image shape"
            )

        rad_mode = rad_info["detector_mode"]
        if rad_mode != gain_record.detector_mode:
            raise NPZValidationError("Radiograph and gain detector modes differ")

        cal_source_meta = cal_metadata.get("source_metadata", {})
        if isinstance(cal_source_meta, dict):
            cal_mode = cal_source_meta.get("detector_mode")
            if cal_mode and rad_mode != cal_mode:
                raise NPZValidationError(
                    "Detector mode does not match calibration artifact detector mode"
                )

        if expected_detector_mode and rad_mode != expected_detector_mode:
            raise NPZValidationError("Detector mode does not match expected config")

        # Camera serial verification across radiograph, gain, and calibration artifact
        rad_cam_sn = str(
            rad_info.get("camera_params", {}).get("serialNumber")
            or rad_info.get("camera_params", {}).get("cameraSerial")
            or ""
        )
        gain_cam_sn = str(
            gain_record.camera_params.get("serialNumber")
            or gain_record.camera_params.get("cameraSerial")
            or ""
        )
        cal_cam_sn = ""
        if isinstance(cal_source_meta, dict):
            cal_cam_params = cal_source_meta.get("camera_params", {})
            if isinstance(cal_cam_params, dict):
                cal_cam_sn = str(
                    cal_cam_params.get("serialNumber")
                    or cal_cam_params.get("cameraSerial")
                    or ""
                )

        serials = {s for s in (rad_cam_sn, gain_cam_sn, cal_cam_sn) if s}
        if len(serials) > 1:
            raise NPZValidationError(
                f"Camera serial number mismatch: {sorted(serials)}"
            )

        if (
            expected_camera_serial
            and rad_cam_sn
            and str(rad_cam_sn) != str(expected_camera_serial)
        ):
            raise NPZValidationError("Camera serial does not match expected config")

        rows, cols = raw.shape
        if rows > max_rows or cols > max_cols or (rows * cols) > max_pixels:
            raise NPZValidationError("Image dimensions exceed configured maxima")

        # 3. Process image pipeline with map_x and map_y
        processed_img = process_radiography_arrays(
            raw,
            dark,
            flat,
            rad_mode,
            map_x=map_x,
            map_y=map_y,
        )
        processed_uint16 = to_uint16(processed_img)

        # 3. Write verified uint16 TIFF output
        write_tiff(output_tiff_path, processed_uint16)

        out_rows, out_cols = processed_uint16.shape
        result_data = {
            "status": "success",
            "sanitized_error_code": None,
            "rows": out_rows,
            "cols": out_cols,
            "pixel_bytes": processed_uint16.nbytes,
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
    try:
        _apply_startup_resource_limits()
    except Exception:
        pass
    execute_conversion_worker(sys.argv[1], sys.argv[2])
