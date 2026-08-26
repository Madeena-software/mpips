"""Local, non-clinical geometry QA for the pinned real TRX inputs."""

from __future__ import annotations

import json
import hashlib
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pydicom

from mpips.engine.imager_pipeline import complete_pipeline as engine
from mpips.workflows.imager_pipeline.npz_io import load_gain_catalog, load_radiograph
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays
from scripts.promote_production_calibration import (
    EXPECTED_FINGERPRINT,
    _extract_carrier,
    verify_carrier,
    validate_real_thorax_inputs,
)


def _preview(path: Path, image: np.ndarray) -> None:
    image = np.asarray(image, dtype=np.float32)
    low, high = np.percentile(image, (1, 99))
    scaled = np.clip((image - low) / max(high - low, 1e-6) * 255, 0, 255)
    cv2.imwrite(str(path), scaled.astype(np.uint8))


def _metrics(image: np.ndarray) -> dict[str, object]:
    image = np.asarray(image)
    background = image > np.percentile(image, 5)
    ys, xs = np.where(background)
    height, width = image.shape[:2]
    bbox = (
        [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if xs.size else []
    )
    return {
        "non_background_bbox": bbox,
        "non_background_width_ratio": (
            round((bbox[2] - bbox[0] + 1) / width, 6) if bbox else 0.0
        ),
        "non_background_height_ratio": (
            round((bbox[3] - bbox[1] + 1) / height, 6) if bbox else 0.0
        ),
        "black_or_zero_pixel_ratio": round(float(np.mean(image == 0)), 6),
    }


def _geometry_bad(metrics: dict[str, object]) -> bool:
    return bool(
        metrics["black_or_zero_pixel_ratio"] > 0.95
        or metrics["non_background_width_ratio"] < 0.5
        or metrics["non_background_height_ratio"] < 0.5
    )


def _case(
    data_dir: Path, calibration_dir: Path, case: int, output: Path
) -> dict[str, object]:
    manifest = json.loads(
        (
            Path(__file__).parents[1]
            / "artifacts/test-data/real-thorax-trx-da5277082.json"
        ).read_text()
    )
    item = next(value for value in manifest["radiographs"] if value["case"] == case)
    gain_path = data_dir / manifest["gain"]["filename"]
    rad_path = data_dir / item["filename"]
    radiograph = load_radiograph(rad_path)
    gain = load_gain_catalog([gain_path]).records[str(manifest["expected"]["gain_id"])]
    raw, dark, flat = radiograph["raw"], gain.dark, gain.flat
    with np.load(calibration_dir / "remap.npz", allow_pickle=False) as remap:
        map_x, map_y = remap["map_x"], remap["map_y"]
    corrected = engine.flat_field_correction(
        raw.astype(np.float32) / 65535,
        dark.astype(np.float32) / 65535,
        flat.astype(np.float32) / 65535,
    )
    remapped = cv2.remap(
        corrected,
        map_x.astype(np.float32),
        map_y.astype(np.float32),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    final = process_radiography_arrays(raw, dark, flat, "TRX", map_x=map_x, map_y=map_y)
    case_dir = output / f"case-{case}"
    case_dir.mkdir(parents=True, exist_ok=True)
    _preview(case_dir / "raw-preview.png", raw)
    _preview(case_dir / "gain-corrected-preview.png", corrected)
    _preview(case_dir / "remapped-preview.png", remapped)
    _preview(case_dir / "final-dicom-preview.png", final)
    dcm_path = case_dir / "output.dcm"
    from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm

    tiff_path = case_dir / "processed.tiff"
    cv2.imwrite(str(tiff_path), final)
    meta_path = case_dir / "adapter.json"
    meta_path.write_text(json.dumps({"StudyDescription": "local TRX geometry QA"}))
    tiff_json_to_dcm(str(tiff_path), str(meta_path), str(dcm_path))
    ds = pydicom.dcmread(dcm_path, stop_before_pixels=False)
    stage_metrics = {
        "RAW": _metrics(raw),
        "GAIN_CORRECTION": _metrics(corrected),
        "CALIBRATION_REMAP": _metrics(remapped),
        "ORIENTATION": _metrics(np.rot90(remapped)),
        "CROP": _metrics(np.rot90(remapped)),
        "DICOM_ENCODING": _metrics(final),
    }
    first_failure = next(
        (stage for stage, value in stage_metrics.items() if _geometry_bad(value)),
        "NONE",
    )
    metrics = {
        "source_filename": item["filename"],
        "raw_shape": list(raw.shape),
        "gain_corrected_shape": list(corrected.shape),
        "remapped_shape": list(remapped.shape),
        "final_dicom_shape": [int(ds.Rows), int(ds.Columns)],
        "map_x_min": float(map_x.min()),
        "map_x_max": float(map_x.max()),
        "map_y_min": float(map_y.min()),
        "map_y_max": float(map_y.max()),
        "map_valid_source_coordinate_ratio": round(
            float(
                np.mean(
                    (map_x >= 0)
                    & (map_x <= 4095)
                    & (map_y >= 0)
                    & (map_y <= 2999)
                )
            ),
            6,
        ),
        "map_source_domain": "x=0..4095,y=0..2999",
        **_metrics(final),
        "first_geometry_failure_stage": first_failure,
        "pipeline_result": "FAIL" if first_failure != "NONE" else "PASS",
        "calibration_fingerprint": EXPECTED_FINGERPRINT,
        "orientation_operation": "TRX rotate 90 degrees counter-clockwise",
        "crop_operation": "configured detector crop; current TRX crop is zero pixels",
        "stage_metrics": stage_metrics,
    }
    if (
        raw.shape != (3000, 4096)
        or map_x.shape != (3000, 4096)
        or not np.isfinite(map_x).all()
        or not np.isfinite(map_y).all()
    ):
        metrics.update(
            first_geometry_failure_stage="CALIBRATION_REMAP", pipeline_result="FAIL"
        )
    metrics_path = case_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")
    tiff_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
    return metrics


def run_local_real_trx_pipeline(
    data_dir: str | Path, calibration_dir: str | Path, output: str | Path
) -> dict[str, object]:
    data_dir, calibration_dir, output = (
        Path(data_dir),
        Path(calibration_dir),
        Path(output),
    )
    output.mkdir(parents=True, exist_ok=True)
    if validate_real_thorax_inputs(data_dir)["REAL_THORAX_INPUTS_ALL_PASS"] != "PASS":
        return {
            "REAL_TRX_LOCAL_OUTPUT_DIR": str(output),
            "REAL_TRX_LOCAL_PIPELINE": "FAIL",
            "FIRST_FAILURE_STAGE": "RAW",
            "cases": [],
        }
    with tempfile.TemporaryDirectory(
        prefix="mpips-local-trx-calibration-"
    ) as temporary:
        if calibration_dir.is_file():
            verify_carrier(
                calibration_dir,
                calibration_dir.stat().st_size,
                hashlib.sha256(calibration_dir.read_bytes()).hexdigest(),
            )
            calibration_dir = _extract_carrier(calibration_dir, Path(temporary))
        cases = [_case(data_dir, calibration_dir, case, output) for case in (1, 2, 3)]
    result = {
        "REAL_TRX_LOCAL_OUTPUT_DIR": str(output),
        "CASE_1_PIPELINE": cases[0]["pipeline_result"],
        "CASE_2_PIPELINE": cases[1]["pipeline_result"],
        "CASE_3_PIPELINE": cases[2]["pipeline_result"],
        "REAL_TRX_LOCAL_PIPELINE": (
            "PASS"
            if all(item["pipeline_result"] == "PASS" for item in cases)
            else "FAIL"
        ),
        "FIRST_FAILURE_STAGE": next(
            (
                item["first_geometry_failure_stage"]
                for item in cases
                if item["pipeline_result"] == "FAIL"
            ),
            "NONE",
        ),
        "cases": cases,
    }
    if result["REAL_TRX_LOCAL_PIPELINE"] != "PASS":
        result["FINAL_PROMOTION_CLASSIFICATION"] = "REAL_TRX_LOCAL_PIPELINE_REQUIRED"
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(
        0
        if run_local_real_trx_pipeline(
            "/tmp/real-thorax", "/tmp/calibration", "research/real-thorax-dicom"
        )["REAL_TRX_LOCAL_PIPELINE"]
        == "PASS"
        else 1
    )
