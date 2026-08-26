"""Local A/B/C geometry QA for the pinned real TRX inputs."""

from __future__ import annotations

import hashlib
import csv
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pydicom

from mpips.engine.imager_pipeline import complete_pipeline as engine
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.npz_io import (
    load_calibration_processed_image,
    load_gain_catalog,
    load_radiograph,
)
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays
from scripts.promote_production_calibration import (
    _extract_carrier,
    validate_real_thorax_inputs,
    verify_carrier,
)

MANIFEST = (
    Path(__file__).parents[1] / "artifacts/test-data/real-thorax-trx-da5277082.json"
)
MODES = (
    "NO_REMAP",
    "IDENTITY_REMAP",
    "HISTORICAL_789ADFF_REMAP",
    "NEW_606DB560_REMAP",
)
SUPPORT_DIR = Path(
    "research/phantom-gotri-thorax/output/neural_model/"
    "789adff52ed296d956f81ae8dc38247a73768d863495f91a916fc251aaf67811"
)
HISTORICAL_FINGERPRINT = (
    "789adff52ed296d956f81ae8dc38247a73768d863495f91a916fc251aaf67811"
)


def inspect_neural_support(directory: Path = SUPPORT_DIR) -> dict[str, object]:
    """Compare learned displacement inside/outside detected grid support."""
    import torch

    from mpips.engine.calibration.dotgrid.neural_model.model import MLPCompensation

    coordinates = []
    with (directory / "grid_coordinates.csv").open() as source:
        for row in csv.reader(source):
            coordinates.extend(
                [
                    [float(value) for value in cell.strip("()").split(",")]
                    for cell in row
                ]
            )
    grid = np.asarray(coordinates, dtype=np.float32)
    xmin, ymin = grid.min(axis=0)
    xmax, ymax = grid.max(axis=0)
    model = MLPCompensation()
    model.load_state_dict(
        torch.load(
            directory / "compensation_model.pth", map_location="cpu", weights_only=True
        )
    )
    model.eval()
    xs = np.arange(0, 4096, 64, dtype=np.float32)
    ys = np.arange(0, 3000, 64, dtype=np.float32)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    points = np.column_stack((xx.ravel(), yy.ravel()))
    with torch.no_grad():
        offsets = model(torch.from_numpy(points) / float(grid.max())).numpy()
    magnitudes = np.linalg.norm(offsets * float(grid.max()), axis=1)
    inside = (
        (points[:, 0] >= xmin)
        & (points[:, 0] <= xmax)
        & (points[:, 1] >= ymin)
        & (points[:, 1] <= ymax)
    )

    def stats(values: np.ndarray) -> dict[str, float]:
        return {
            "mean_px": round(float(values.mean()), 3),
            "p95_px": round(float(np.percentile(values, 95)), 3),
            "max_px": round(float(values.max()), 3),
        }

    return {
        "GRID_SUPPORT_X_MIN": float(xmin),
        "GRID_SUPPORT_X_MAX": float(xmax),
        "GRID_SUPPORT_Y_MIN": float(ymin),
        "GRID_SUPPORT_Y_MAX": float(ymax),
        "GRID_SUPPORT_WIDTH_RATIO": float((xmax - xmin) / 4096),
        "GRID_SUPPORT_HEIGHT_RATIO": float((ymax - ymin) / 3000),
        "DISPLACEMENT_INSIDE_SUPPORT": stats(magnitudes[inside]),
        "DISPLACEMENT_OUTSIDE_SUPPORT": stats(magnitudes[~inside]),
        "EXTRAPOLATION_HYPOTHESIS": (
            "NOT_FALSIFIED_OUTSIDE_DISPLACEMENT_LARGER"
            if magnitudes[~inside].mean() > magnitudes[inside].mean()
            else "NOT_SUPPORTED_OUTSIDE_DISPLACEMENT_NOT_LARGER"
        ),
    }


def _support_bounds(directory: Path = SUPPORT_DIR) -> tuple[float, float, float, float]:
    coordinates = []
    with (directory / "grid_coordinates.csv").open() as source:
        for row in csv.reader(source):
            coordinates.extend(
                [
                    [float(value) for value in cell.strip("()").split(",")]
                    for cell in row
                ]
            )
    grid = np.asarray(coordinates, dtype=np.float32)
    return (*grid.min(axis=0), *grid.max(axis=0))


def _support_bounded_maps(
    map_x: np.ndarray,
    map_y: np.ndarray,
    width: int,
    height: int,
    directory: Path = SUPPORT_DIR,
) -> tuple[np.ndarray, np.ndarray]:
    """Blend neural displacement to identity outside detected grid support."""
    xmin, ymin, xmax, ymax = _support_bounds(directory)
    yy, xx = np.mgrid[0:height, 0:width]
    distance = np.maximum.reduce(
        [xmin - xx, xx - xmax, ymin - yy, yy - ymax, np.zeros_like(xx)]
    )
    weight = np.clip(1.0 - distance / 128.0, 0.0, 1.0).astype(np.float32)
    identity_x, identity_y = xx.astype(np.float32), yy.astype(np.float32)
    return (
        identity_x + weight * (map_x - identity_x),
        identity_y + weight * (map_y - identity_y),
    )


def remap_control_metrics(
    remap_path: Path, metadata_path: Path, prefix: str
) -> dict[str, object]:
    """Compute identical source-domain coverage metrics for BED and TRX maps."""
    metadata = json.loads(metadata_path.read_text())
    height, width = metadata["image_shape"]
    with np.load(remap_path, allow_pickle=False) as remap:
        map_x, map_y = remap["map_x"], remap["map_y"]
    valid = (map_x >= 0) & (map_x <= width - 1) & (map_y >= 0) & (map_y <= height - 1)
    ys, xs = np.where(valid)
    bbox = (
        [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        if xs.size
        else None
    )
    valid_fraction = float(np.mean(valid))
    return {
        f"{prefix}_MAP_X_MIN": float(map_x.min()),
        f"{prefix}_MAP_X_MAX": float(map_x.max()),
        f"{prefix}_MAP_Y_MIN": float(map_y.min()),
        f"{prefix}_MAP_Y_MAX": float(map_y.max()),
        f"{prefix}_REMAP_VALID_FRACTION": valid_fraction,
        f"{prefix}_REMAP_OUT_OF_BOUNDS_FRACTION": 1.0 - valid_fraction,
        f"{prefix}_VALID_REMAP_BBOX": bbox,
        f"{prefix}_VALID_REMAP_WIDTH_RATIO": (
            ((bbox[2] - bbox[0] + 1) / map_x.shape[1]) if bbox else 0.0
        ),
        f"{prefix}_VALID_REMAP_HEIGHT_RATIO": (
            ((bbox[3] - bbox[1] + 1) / map_x.shape[0]) if bbox else 0.0
        ),
        f"{prefix}_SOURCE_IMAGE_SHAPE": [int(height), int(width)],
    }


def write_remap_control(
    output: str | Path = "research/real-thorax-dicom",
) -> dict[str, object]:
    output = Path(output)
    bed = remap_control_metrics(
        Path(
            "research/kambing-260714/data/output/calibration-cache/"
            "4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/remap.npz"
        ),
        Path(
            "research/kambing-260714/data/output/calibration-cache/"
            "4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/"
            "metadata.json"
        ),
        "BED",
    )
    trx_dir = SUPPORT_DIR
    trx = remap_control_metrics(trx_dir / "remap.npz", trx_dir / "metadata.json", "TRX")
    result = {**bed, **trx}
    result["BED_REMAP_CONTROL"] = (
        "PASS"
        if bed["BED_REMAP_VALID_FRACTION"] > trx["TRX_REMAP_VALID_FRACTION"]
        else "FAIL"
    )
    result["TRX_REMAP_GEOMETRY"] = (
        "FAIL" if trx["TRX_REMAP_VALID_FRACTION"] < 0.85 else "PASS"
    )
    result["BED_VS_TRX_REMAP_DIAGNOSIS"] = (
        "BED broad coverage; current TRX remap severe out-of-bounds coverage"
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "remap-control.json").write_text(json.dumps(result, indent=2) + "\n")
    summary_path = output / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text())
        summary.update(result)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return result


def write_neural_support(
    output: str | Path = "research/real-thorax-dicom",
) -> dict[str, object]:
    output = Path(output)
    result = inspect_neural_support()
    (output / "neural-support.json").write_text(json.dumps(result, indent=2) + "\n")
    summary_path = output / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text())
        summary["neural_support"] = result
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return result


def _preview(path: Path, image: np.ndarray) -> None:
    image = np.asarray(image, dtype=np.float32)
    low, high = np.percentile(image, (1, 99))
    scaled = np.clip((image - low) / max(high - low, 1e-6) * 255, 0, 255)
    cv2.imwrite(str(path), scaled.astype(np.uint8))


def _geometry(image: np.ndarray) -> dict[str, object]:
    image = np.asarray(image)
    foreground_ys, foreground_xs = np.where(image > np.percentile(image, 5))
    nonzero_ys, nonzero_xs = np.where(image != 0)
    height, width = image.shape[:2]
    bbox = (
        [
            int(foreground_xs.min()),
            int(foreground_ys.min()),
            int(foreground_xs.max()),
            int(foreground_ys.max()),
        ]
        if foreground_xs.size
        else []
    )
    nonzero_bbox = (
        [
            int(nonzero_xs.min()),
            int(nonzero_ys.min()),
            int(nonzero_xs.max()),
            int(nonzero_ys.max()),
        ]
        if nonzero_xs.size
        else []
    )
    return {
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "min": float(image.min()),
        "max": float(image.max()),
        "mean": float(image.mean()),
        "p01": float(np.percentile(image, 1)),
        "p25": float(np.percentile(image, 25)),
        "p50": float(np.percentile(image, 50)),
        "p75": float(np.percentile(image, 75)),
        "p99": float(np.percentile(image, 99)),
        "non_background_bbox": bbox,
        "final_nonzero_bbox": nonzero_bbox,
        "final_exact_zero_ratio": round(float(np.mean(image == 0)), 6),
        "final_dynamic_range": float(image.max() - image.min()),
        "final_percentiles": {
            "p01": float(np.percentile(image, 1)),
            "p25": float(np.percentile(image, 25)),
            "p50": float(np.percentile(image, 50)),
            "p75": float(np.percentile(image, 75)),
            "p99": float(np.percentile(image, 99)),
        },
        "non_background_width_ratio": (
            round((bbox[2] - bbox[0] + 1) / width, 6) if bbox else 0.0
        ),
        "non_background_height_ratio": (
            round((bbox[3] - bbox[1] + 1) / height, 6) if bbox else 0.0
        ),
        "zero_pixel_ratio": round(float(np.mean(image == 0)), 6),
    }


def _geometry_failure(metrics: dict[str, object]) -> bool:
    return bool(
        # This is a known-dataset catastrophic-collapse gate, not a clinical
        # image-quality rule.
        metrics["zero_pixel_ratio"] > 0.5
        or metrics["non_background_width_ratio"] < 0.5
        or metrics["non_background_height_ratio"] < 0.5
    )


def _first_collapse_stage(stages: dict[str, dict[str, object]]) -> str:
    """Return the first stage whose occupancy gate shows catastrophic collapse."""
    for name in (
        "SOURCE_RAW",
        "SOURCE_PROCESSED_REFERENCE",
        "DENOISED_RAW",
        "FFC",
        "REMAP",
        "CROP_ROTATE",
        "PRE_THRESHOLD",
        "THRESHOLD_SEPARATION",
        "INVERT",
        "CONTRAST",
        "CLAHE",
        "MEDIAN",
        "REMAP_MASK",
        "FINAL_IMAGE",
    ):
        metrics = stages.get(name)
        if metrics and (
            metrics["exact_zero_ratio"] > 0.5 or metrics["nonzero_ratio"] < 0.5
        ):
            return name
    return "NONE"


def _case(
    data_dir: Path,
    neural_dir: Path,
    case: int,
    mode: str,
    output: Path,
    threshold_mode: str = "bypass",
) -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text())
    item = next(value for value in manifest["radiographs"] if value["case"] == case)
    raw_info = load_radiograph(data_dir / item["filename"])
    reference, _ = load_calibration_processed_image(data_dir / item["filename"])
    gain = load_gain_catalog([data_dir / manifest["gain"]["filename"]]).records[
        manifest["expected"]["gain_id"]
    ]
    raw, dark, flat = raw_info["raw"], gain.dark, gain.flat
    if mode == "NO_REMAP":
        map_x = map_y = None
    elif mode == "IDENTITY_REMAP":
        map_x, map_y = np.meshgrid(
            np.arange(raw.shape[1], dtype=np.float32),
            np.arange(raw.shape[0], dtype=np.float32),
        )
    else:
        with np.load(neural_dir / "remap.npz", allow_pickle=False) as remap:
            map_x, map_y = remap["map_x"], remap["map_y"]
        if mode == "HISTORICAL_789ADFF_REMAP":
            with np.load(SUPPORT_DIR / "remap.npz", allow_pickle=False) as remap:
                map_x, map_y = remap["map_x"], remap["map_y"]
    corrected = engine.flat_field_correction(
        raw.astype(np.float32) / 65535,
        dark.astype(np.float32) / 65535,
        flat.astype(np.float32) / 65535,
    )
    remapped = (
        corrected
        if map_x is None
        else cv2.remap(
            corrected,
            map_x.astype(np.float32),
            map_y.astype(np.float32),
            cv2.INTER_LINEAR,
        )
    )
    stages: dict[str, dict[str, object]] = {}
    final = process_radiography_arrays(
        raw,
        dark,
        flat,
        "TRX",
        map_x=map_x,
        map_y=map_y,
        stage_observer=stages.__setitem__,
        threshold_method_override=("auto" if threshold_mode == "auto" else None),
    )
    engine._report_stage(stages.__setitem__, "SOURCE_PROCESSED_REFERENCE", reference)
    mode_dir = output / f"case-{case}" / threshold_mode / mode.lower().replace("_", "-")
    mode_dir.mkdir(parents=True, exist_ok=True)
    _preview(mode_dir / "final-preview.png", final)
    tiff, adapter, dcm = (
        mode_dir / "processed.tiff",
        mode_dir / "adapter.json",
        mode_dir / "output.dcm",
    )
    cv2.imwrite(str(tiff), final)
    adapter.write_text(json.dumps({"StudyDescription": "local TRX A/B/C QA"}))
    tiff_json_to_dcm(str(tiff), str(adapter), str(dcm))
    dataset = pydicom.dcmread(dcm, stop_before_pixels=False)
    geometry = _geometry(final)
    failed = _geometry_failure(geometry)
    metrics: dict[str, object] = {
        "case": case,
        "mode": mode,
        "threshold_mode": threshold_mode,
        "source_filename": item["filename"],
        "raw_shape": list(raw.shape),
        "gain_corrected_shape": list(corrected.shape),
        "remapped_shape": list(remapped.shape),
        "final_shape": list(final.shape),
        "final_dicom_shape": [int(dataset.Rows), int(dataset.Columns)],
        "dicom_structure_valid": bool(
            int(dataset.BitsAllocated) == 16
            and int(dataset.PixelRepresentation) == 0
            and bool(dataset.PixelData)
        ),
        **geometry,
        "unexpected_border_ratio": geometry["zero_pixel_ratio"],
        "stage_metrics": stages,
        "dicom_structure_metrics": {
            "shape": [int(dataset.Rows), int(dataset.Columns)],
            "dtype": str(dataset.pixel_array.dtype),
            "valid": bool(
                int(dataset.BitsAllocated) == 16
                and int(dataset.PixelRepresentation) == 0
                and bool(dataset.PixelData)
            ),
        },
        "first_geometry_failure_stage": _first_collapse_stage(stages),
        "pipeline_result": "FAIL" if failed else "PASS",
        "calibration_fingerprint": (
            HISTORICAL_FINGERPRINT
            if mode == "HISTORICAL_789ADFF_REMAP"
            else (
                "606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d"
                if mode == "NEW_606DB560_REMAP"
                else None
            )
        ),
        "FINAL_EXACT_ZERO_RATIO": geometry["final_exact_zero_ratio"],
        "FINAL_NONZERO_RATIO": round(float(np.mean(final != 0)), 6),
        "FINAL_NONZERO_BBOX": geometry["final_nonzero_bbox"],
        "FINAL_DYNAMIC_RANGE": geometry["final_dynamic_range"],
        "FINAL_PERCENTILES": geometry["final_percentiles"],
    }
    if mode in ("HISTORICAL_789ADFF_REMAP", "NEW_606DB560_REMAP"):
        valid_fraction = float(
            np.mean(
                (map_x >= 0)
                & (map_x <= raw.shape[1] - 1)
                & (map_y >= 0)
                & (map_y <= raw.shape[0] - 1)
            )
        )
        metrics.update(
            {
                "map_x_min": float(map_x.min()),
                "map_x_max": float(map_x.max()),
                "map_y_min": float(map_y.min()),
                "map_y_max": float(map_y.max()),
                "map_valid_source_coordinate_ratio": round(valid_fraction, 6),
            }
        )
        if valid_fraction < 0.85:
            metrics.update(
                first_geometry_failure_stage="CALIBRATION_REMAP", pipeline_result="FAIL"
            )
    (mode_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    tiff.unlink(missing_ok=True)
    adapter.unlink(missing_ok=True)
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
            "REAL_TRX_LOCAL_PIPELINE": "FAIL",
            "FIRST_FAILURE_STAGE": "RAW",
            "cases": {},
        }
    with tempfile.TemporaryDirectory(
        prefix="mpips-local-trx-calibration-"
    ) as temporary:
        neural_dir = calibration_dir
        if calibration_dir.is_file():
            verify_carrier(
                calibration_dir,
                calibration_dir.stat().st_size,
                hashlib.sha256(calibration_dir.read_bytes()).hexdigest(),
            )
            neural_dir = _extract_carrier(calibration_dir, Path(temporary))
        cases = {
            f"case-{case}": {
                mode: _case(data_dir, neural_dir, case, mode, output) for mode in MODES
            }
            for case in (1, 2, 3)
        }
    current = [cases[f"case-{case}"]["NEW_606DB560_REMAP"] for case in (1, 2, 3)]
    passthrough = all(
        cases[f"case-{case}"][mode]["pipeline_result"] == "PASS"
        for case in (1, 2, 3)
        for mode in ("NO_REMAP", "IDENTITY_REMAP")
    )
    result: dict[str, object] = {
        "REAL_TRX_LOCAL_OUTPUT_DIR": str(output),
        "cases": cases,
        "TRX_PIPELINE_WITHOUT_BAD_REMAP": "PASS" if passthrough else "FAIL",
        "TRX_GEOMETRY_PASSTHROUGH_CANDIDATE": "YES" if passthrough else "NO",
        "TRX_CURRENT_CALIBRATION": (
            "REJECTED"
            if any(item["pipeline_result"] == "FAIL" for item in current)
            else "ACCEPTED"
        ),
        "REAL_TRX_LOCAL_PIPELINE": (
            "PASS"
            if all(item["pipeline_result"] == "PASS" for item in current)
            else "FAIL"
        ),
        "FIRST_FAILURE_STAGE": next(
            (
                item["first_geometry_failure_stage"]
                for item in current
                if item["pipeline_result"] == "FAIL"
            ),
            "NONE",
        ),
    }
    if SUPPORT_DIR.is_dir():
        result["neural_support"] = inspect_neural_support()
        (output / "neural-support.json").write_text(
            json.dumps(result["neural_support"], indent=2) + "\n"
        )
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
