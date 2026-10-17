from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
import zipfile
import traceback
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

REAL_TRX_PROFILE_ID = "GOTRI-TRX-001"
REAL_TRX_CAMERA_SERIAL = "DA5234480"
REAL_TRX_FINGERPRINT = (
    "606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d"
)
REAL_TRX_REMAP_SHA256 = (
    "32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893"
)
REAL_TRX_IMAGE_SHAPE = (3000, 4096)


def _apply_startup_resource_limits() -> None:
    """Enforces Linux RLIMIT_CPU before opening NPZ files.

    Logs a diagnostic message to stderr if RLIMIT_CPU cannot be set on Linux,
    and raises RuntimeError if running under Linux with RLIMIT_CPU unavailable.
    """
    try:
        import resource

        cpu_limit = int(os.getenv("MPIPS_DICOM_WORKER_CPU_SECONDS", "120"))

        if cpu_limit > 0 and hasattr(resource, "RLIMIT_CPU"):
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 5))
            except (ValueError, OSError) as exc:
                if sys.platform.startswith("linux"):
                    sys.stderr.write(
                        f"Warning: Failed to set RLIMIT_CPU on Linux: {exc}\n"
                    )
                    raise RuntimeError(
                        f"Failed to set RLIMIT_CPU on Linux: {exc}"
                    ) from exc
        elif sys.platform.startswith("linux") and not hasattr(resource, "RLIMIT_CPU"):
            sys.stderr.write("Warning: RLIMIT_CPU not supported on Linux platform\n")
            raise RuntimeError("RLIMIT_CPU attribute missing on Linux")
    except ImportError:
        if sys.platform.startswith("linux"):
            sys.stderr.write("Warning: resource module unavailable on Linux\n")
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
        calibration_dir_str = args.get("calibration_dir")
        max_rows = int(args.get("max_rows", 16384))
        max_cols = int(args.get("max_cols", 16384))
        max_pixels = int(args.get("max_pixels", 268435456))
        output_tiff_path = args["output_tiff_path"]

        # 1. Load radiograph and gain catalog
        if not calibration_dir_str:
            raise NPZValidationError("Missing calibration_dir in worker arguments")

        cal_dir = Path(calibration_dir_str)
        if not cal_dir.is_dir():
            raise NPZValidationError("Calibration artifact directory does not exist")

        rad_info = load_radiograph(radiograph_npz_path)
        gain_catalog = load_gain_catalog([gain_npz_path])
        rad_mode = rad_info["detector_mode"]

        # 2. Resolve calibration artifact directory (single-mode or multi-mode)
        rad_camera_params = rad_info.get("camera_params") or {}
        rad_camera_serial = rad_camera_params.get(
            "serialNumber"
        ) or rad_camera_params.get("cameraSerial")

        selected_cal_dir = None
        if (cal_dir / "metadata.json").is_file():
            selected_cal_dir = cal_dir
        else:
            candidates = []
            for sub in sorted(cal_dir.iterdir()):
                if sub.is_dir() and (sub / "metadata.json").is_file():
                    try:
                        sub_meta = json.loads(
                            (sub / "metadata.json").read_text(encoding="utf-8")
                        )
                        if isinstance(sub_meta, dict):
                            src_meta = sub_meta.get("source_metadata", {})
                            if isinstance(src_meta, dict):
                                sub_mode = src_meta.get("detector_mode")
                                if sub_mode == rad_mode:
                                    # If camera serial is present in both, verify match
                                    cal_cam = src_meta.get("camera_params", {})
                                    cal_serial = cal_cam.get(
                                        "serialNumber"
                                    ) or cal_cam.get("cameraSerial")
                                    # Match if serials agree, or if either is
                                    # unspecified
                                    if (
                                        rad_camera_serial is None
                                        or cal_serial is None
                                        or rad_camera_serial == cal_serial
                                    ):
                                        candidates.append(
                                            (sub, cal_serial == rad_camera_serial)
                                        )
                    except Exception:
                        continue

            if len(candidates) == 1:
                selected_cal_dir = candidates[0][0]
            elif len(candidates) > 1:
                # Disambiguate by exact camera serial match
                exact_matches = [p for p, exact in candidates if exact]
                if len(exact_matches) == 1:
                    selected_cal_dir = exact_matches[0]
                else:
                    raise NPZValidationError(
                        f"Ambiguous calibration profiles found for mode {rad_mode}"
                    )

        if not selected_cal_dir:
            raise NPZValidationError(
                f"No matching calibration artifact found for detector mode {rad_mode}"
            )

        cal_metadata_path = selected_cal_dir / "metadata.json"
        cal_remap_path = selected_cal_dir / "remap.npz"
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
            with cal_remap_path.open("rb") as f_remap:
                remap_bytes = f_remap.read()
            remap_sha = hashlib.sha256(remap_bytes).hexdigest()

            with np.load(cal_remap_path) as remap_data:
                if "map_x" not in remap_data or "map_y" not in remap_data:
                    raise NPZValidationError("remap.npz missing map_x or map_y arrays")
                map_x = remap_data["map_x"].astype(np.float32)
                map_y = remap_data["map_y"].astype(np.float32)
        except NPZValidationError:
            raise
        except Exception as exc:
            raise NPZValidationError(f"Failed to load remap.npz: {exc}") from exc

        cal_source_meta = cal_metadata.get("source_metadata", {})
        cal_mode = None
        cal_serial = None
        cal_profile_id = None
        if isinstance(cal_source_meta, dict):
            cal_mode = cal_source_meta.get("detector_mode")
            cal_profile_id = cal_source_meta.get("id")
            cal_cam = cal_source_meta.get("camera_params", {})
            if isinstance(cal_cam, dict):
                cal_serial = cal_cam.get("serialNumber") or cal_cam.get("cameraSerial")

        # Determine if this conversion is operating under embedded calibration
        # resources (e.g. standalone runtime interface 2-experimental or
        # embedded bundle)
        calibration_origin = args.get("calibration_origin")
        if calibration_origin == "external":
            is_embedded_cal = False
        elif calibration_origin == "embedded":
            is_embedded_cal = True
        else:
            # Fallback for standalone frozen execution or direct worker execution
            is_embedded_cal = bool(
                getattr(sys, "frozen", False)
                or (
                    selected_cal_dir.parent / "embedded_calibration_manifest.json"
                ).is_file()
            )

        # Scoped fail-closed integrity validation for designated real TRX profile:
        # 1. Under embedded calibration, ALL TRX conversions MUST strictly use
        #    the approved real TRX calibration.
        # 2. For any TRX radiograph or profile matching real TRX characteristics:
        #    - If camera serial matches real TRX or is absent in calibration or
        #      profile claims TRX, it must validate against approved real TRX specs.
        #    - Alternate substitute TRX profiles attempting to bypass fingerprint
        #      or remap hash checks are rejected.
        is_real_trx = (
            (rad_mode == "TRX" and is_embedded_cal)
            or cal_profile_id == REAL_TRX_PROFILE_ID
            or cal_fingerprint == REAL_TRX_FINGERPRINT
            or (rad_mode == "TRX" and rad_camera_serial == REAL_TRX_CAMERA_SERIAL)
            or (rad_mode == "TRX" and expected_cal_shape == REAL_TRX_IMAGE_SHAPE)
        )

        if is_real_trx:
            if cal_mode != "TRX":
                raise NPZValidationError(
                    f"Real TRX calibration invalid detector_mode: {cal_mode}"
                )
            if cal_profile_id != REAL_TRX_PROFILE_ID:
                raise NPZValidationError(
                    f"Real TRX calibration invalid profile id: {cal_profile_id}"
                )
            if cal_fingerprint != REAL_TRX_FINGERPRINT:
                raise NPZValidationError(
                    f"Real TRX calibration fingerprint mismatch: {cal_fingerprint}"
                )
            if cal_serial != REAL_TRX_CAMERA_SERIAL:
                raise NPZValidationError(
                    f"Real TRX calibration serial mismatch: {cal_serial}"
                )
            if expected_cal_shape != REAL_TRX_IMAGE_SHAPE:
                raise NPZValidationError(
                    f"Real TRX calibration shape mismatch: {expected_cal_shape}"
                )
            if remap_sha != REAL_TRX_REMAP_SHA256:
                raise NPZValidationError(
                    f"Real TRX remap payload hash altered: {remap_sha}"
                )
            if (
                map_x.shape != REAL_TRX_IMAGE_SHAPE
                or map_y.shape != REAL_TRX_IMAGE_SHAPE
            ):
                raise NPZValidationError(
                    "Real TRX remap array shapes do not match expected image shape"
                )
            if not rad_camera_serial:
                raise NPZValidationError(
                    "Missing camera identity in radiograph for real TRX calibration"
                )
            if rad_camera_serial != REAL_TRX_CAMERA_SERIAL:
                raise NPZValidationError(
                    f"Camera serial mismatch: radiograph '{rad_camera_serial}' "
                    f"!= calibration '{REAL_TRX_CAMERA_SERIAL}'"
                )

        expected_gain_id = args.get("expected_gain_id") or rad_info["gain_id"]
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

        raw = to_uint16(raw, "radiograph raw")
        dark = to_uint16(dark, "gain dark")
        flat = to_uint16(flat, "gain flat")

        if raw.shape != dark.shape or raw.shape != flat.shape:
            raise NPZValidationError("Radiograph raw and gain dark/flat shapes differ")

        if raw.shape != expected_cal_shape:
            raise NPZValidationError(
                "Radiograph shape does not match calibration image shape"
            )

        if map_x.shape != map_y.shape:
            raise NPZValidationError(
                "Calibration remap shape does not match image shape"
            )

        rad_mode = rad_info["detector_mode"]
        if rad_mode != gain_record.detector_mode:
            raise NPZValidationError("Radiograph and gain detector modes differ")

        if cal_mode and rad_mode != cal_mode:
            raise NPZValidationError(
                "Detector mode does not match calibration artifact detector mode"
            )

        if expected_detector_mode:
            exp_norm = (
                "TRX"
                if expected_detector_mode.upper() == "THORAX"
                else expected_detector_mode.upper()
            )
            rad_norm = "TRX" if rad_mode.upper() == "THORAX" else rad_mode.upper()
            if rad_norm != exp_norm:
                raise NPZValidationError("Detector mode does not match expected config")

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

    except NPZValidationError as exc:
        result_data["sanitized_error_code"] = "NPZ_VALIDATION_ERROR"
        result_data["error_detail"] = str(exc)
        sys.stderr.write(f"NPZValidationError: {exc}\n{traceback.format_exc()}\n")
    except (OSError, EOFError, pickle.UnpicklingError, zipfile.BadZipFile) as exc:
        result_data["sanitized_error_code"] = "NPZ_VALIDATION_ERROR"
        result_data["error_detail"] = str(exc)
        sys.stderr.write(f"NPZ OSError: {exc}\n{traceback.format_exc()}\n")
    except ValueError as exc:
        result_data["sanitized_error_code"] = "MANIFEST_OR_DATA_ERROR"
        result_data["error_detail"] = str(exc)
        sys.stderr.write(f"ValueError: {exc}\n{traceback.format_exc()}\n")
    except Exception as exc:
        result_data["sanitized_error_code"] = "CONVERSION_WORKER_FAILURE"
        result_data["error_detail"] = str(exc)
        sys.stderr.write(f"Worker Exception: {exc}\n{traceback.format_exc()}\n")
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
    _apply_startup_resource_limits()
    execute_conversion_worker(sys.argv[1], sys.argv[2])
