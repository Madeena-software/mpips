"""Colab-oriented adapters over the canonical dot-grid calibration engine."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np

import mpips
from mpips.workflows.imager_pipeline.models import (
    CalibrationArtifacts,
    NeuralCalibrationConfig,
)
from mpips.workflows.imager_pipeline.npz_io import (
    NPZValidationError,
    load_gain_catalog,
    load_calibration_processed_image,
    load_radiograph,
    sha256_file,
    to_uint16,
    write_tiff,
)
from mpips.processing import (
    flat_field_correction,
    imagej_stretch,
)


class CalibrationValidationError(RuntimeError):
    """Raised when canonical calibration validation rejects an artifact set."""


# Fixed-canvas remaps must retain most of the detector, not just a valid-sized mask.
MIN_REMAP_VALID_FRACTION = 0.85
MIN_REMAP_WIDTH_RATIO = 0.75
MIN_REMAP_HEIGHT_RATIO = 0.75
MIN_EXPANDED_VALID_FRACTION = 0.80
MIN_EXPANDED_OUTPUT_WIDTH_RATIO = 0.80
MIN_EXPANDED_OUTPUT_HEIGHT_RATIO = 0.80
MIN_EXPANDED_SOURCE_WIDTH_COVERAGE = 0.80
MIN_EXPANDED_SOURCE_HEIGHT_COVERAGE = 0.80


def remap_geometry_evidence(
    map_x: np.ndarray,
    map_y: np.ndarray,
    width: int,
    height: int,
    *,
    output_shape: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Return remap coverage evidence against the source detector domain."""
    if map_x.shape != map_y.shape or map_x.ndim != 2 or not map_x.size:
        raise CalibrationValidationError("remap maps must be non-empty 2-D arrays")
    output_shape = output_shape or (height, width)
    if map_x.shape != output_shape:
        raise CalibrationValidationError("remap maps do not match the output canvas")
    if not np.isfinite(map_x).all() or not np.isfinite(map_y).all():
        raise CalibrationValidationError("remap maps contain non-finite coordinates")
    valid = (map_x >= 0) & (map_x <= width - 1) & (map_y >= 0) & (map_y <= height - 1)
    ys, xs = np.where(valid)
    if not xs.size:
        bbox = None
        width_ratio = height_ratio = 0.0
    else:
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        width_ratio = (bbox[2] - bbox[0] + 1) / output_shape[1]
        height_ratio = (bbox[3] - bbox[1] + 1) / output_shape[0]
        source_width_coverage = (
            float(map_x[valid].max()) - float(map_x[valid].min()) + 1
        ) / width
        source_height_coverage = (
            float(map_y[valid].max()) - float(map_y[valid].min()) + 1
        ) / height
    if not xs.size:
        source_width_coverage = source_height_coverage = 0.0
    valid_fraction = float(np.mean(valid))
    return {
        "REMAP_VALID_FRACTION": valid_fraction,
        "REMAP_OUT_OF_BOUNDS_FRACTION": 1.0 - valid_fraction,
        "VALID_REMAP_BBOX": bbox,
        "VALID_REMAP_WIDTH_RATIO": float(width_ratio),
        "VALID_REMAP_HEIGHT_RATIO": float(height_ratio),
        "SOURCE_IMAGE_SHAPE": [height, width],
        "REMAP_OUTPUT_SHAPE": list(output_shape),
        "VALID_OUTPUT_BBOX": bbox,
        "VALID_OUTPUT_WIDTH_RATIO": float(width_ratio),
        "VALID_OUTPUT_HEIGHT_RATIO": float(height_ratio),
        "SOURCE_COORDINATE_X_MIN": (float(map_x[valid].min()) if xs.size else None),
        "SOURCE_COORDINATE_X_MAX": float(map_x[valid].max()) if xs.size else None,
        "SOURCE_COORDINATE_Y_MIN": float(map_y[valid].min()) if xs.size else None,
        "SOURCE_COORDINATE_Y_MAX": float(map_y[valid].max()) if xs.size else None,
        "SOURCE_DOMAIN_WIDTH_COVERAGE": float(source_width_coverage),
        "SOURCE_DOMAIN_HEIGHT_COVERAGE": float(source_height_coverage),
        "MAP_X_MIN": float(map_x.min()),
        "MAP_X_MAX": float(map_x.max()),
        "MAP_Y_MIN": float(map_y.min()),
        "MAP_Y_MAX": float(map_y.max()),
    }


def validate_fixed_canvas_remap(
    map_x: np.ndarray, map_y: np.ndarray, width: int, height: int
) -> dict[str, Any]:
    """Reject maps whose valid coordinates collapse the fixed output canvas."""
    evidence = remap_geometry_evidence(map_x, map_y, width, height)
    if (
        evidence["REMAP_VALID_FRACTION"] < MIN_REMAP_VALID_FRACTION
        or evidence["VALID_REMAP_WIDTH_RATIO"] < MIN_REMAP_WIDTH_RATIO
        or evidence["VALID_REMAP_HEIGHT_RATIO"] < MIN_REMAP_HEIGHT_RATIO
    ):
        raise CalibrationValidationError(
            "Fixed-canvas remap coverage is unsafe: "
            f"valid_fraction={evidence['REMAP_VALID_FRACTION']:.6f}, "
            f"bbox={evidence['VALID_REMAP_BBOX']}"
        )
    return evidence


def validate_expanded_canvas_remap(
    map_x: np.ndarray, map_y: np.ndarray, width: int, height: int
) -> dict[str, Any]:
    """Reject expanded maps with catastrophic output or source-domain support."""
    evidence = remap_geometry_evidence(
        map_x, map_y, width, height, output_shape=map_x.shape
    )
    if (
        evidence["REMAP_VALID_FRACTION"] < MIN_EXPANDED_VALID_FRACTION
        or evidence["VALID_OUTPUT_WIDTH_RATIO"] < MIN_EXPANDED_OUTPUT_WIDTH_RATIO
        or evidence["VALID_OUTPUT_HEIGHT_RATIO"] < MIN_EXPANDED_OUTPUT_HEIGHT_RATIO
        or evidence["SOURCE_DOMAIN_WIDTH_COVERAGE"] < MIN_EXPANDED_SOURCE_WIDTH_COVERAGE
        or evidence["SOURCE_DOMAIN_HEIGHT_COVERAGE"]
        < MIN_EXPANDED_SOURCE_HEIGHT_COVERAGE
    ):
        raise CalibrationValidationError(
            "Expanded-canvas remap geometry is unsafe: "
            f"valid_fraction={evidence['REMAP_VALID_FRACTION']:.6f}, "
            f"output_bbox={evidence['VALID_OUTPUT_BBOX']}, "
            f"source_coverage=({evidence['SOURCE_DOMAIN_WIDTH_COVERAGE']:.6f}, "
            f"{evidence['SOURCE_DOMAIN_HEIGHT_COVERAGE']:.6f})"
        )
    return evidence


def _load_calibration_image(
    calibration_npz: str | Path,
    calibration_gain_npz: str | Path | None = None,
) -> tuple[np.ndarray, dict[str, Any], dict[str, str] | None]:
    source = Path(calibration_npz)
    if calibration_gain_npz is None:
        image, metadata = load_calibration_processed_image(source)
        return image, metadata, None

    radiograph = load_radiograph(source)
    gain_path = Path(calibration_gain_npz)
    gain = next(iter(load_gain_catalog([gain_path]).records.values()))
    if gain.id != radiograph["gain_id"]:
        raise NPZValidationError(
            f"Calibration gain id {gain.id!r} does not match calibration gainid "
            f"{radiograph['gain_id']!r}"
        )
    raw = radiograph["raw"]
    if raw.shape != gain.dark.shape or raw.shape != gain.flat.shape:
        raise NPZValidationError(
            "Calibration raw and gain dark/flat shape must match: "
            f"{raw.shape}, {gain.dark.shape}, {gain.flat.shape}"
        )
    if radiograph["detector_mode"] != gain.detector_mode:
        raise NPZValidationError("Calibration and gain detector mode must match")
    corrected = flat_field_correction(
        to_uint16(raw, "calibration raw"),
        to_uint16(gain.dark, "calibration gain dark"),
        to_uint16(gain.flat, "calibration gain flat"),
    )
    stretched = imagej_stretch(corrected, saturated_pixels=0.35)
    image = 1.0 - to_uint16(stretched, "calibration image").astype(np.float32) / 65535
    metadata = {
        "id": radiograph["id"],
        "gain_id": radiograph["gain_id"],
        "camera_params": radiograph["camera_params"],
        "detector_mode": radiograph["detector_mode"],
    }
    gain_metadata = {"id": gain.id, "sha256": sha256_file(gain_path)}
    return image, metadata, gain_metadata


def extract_dot_grid(
    image: np.ndarray, config: NeuralCalibrationConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Adapt an in-memory image to the canonical research grid extractor."""
    if image.ndim != 2 or image.dtype != np.uint8:
        raise ValueError("Dot-grid extraction requires a uint8 grayscale image")
    from mpips.calibration.dotgrid.extract_grid import extract_grid

    with tempfile.TemporaryDirectory(prefix="mpips-dotgrid-extract-") as temporary:
        workspace = Path(temporary)
        image_path = write_tiff(workspace / "calibration.tiff", image)
        try:
            result = extract_grid(
                str(image_path),
                str(workspace),
                threshold=config.threshold,
                minimum_contour_area=config.minimum_contour_area,
                row_tolerance=config.row_tolerance,
            )
        except ValueError as exc:
            raise CalibrationValidationError(str(exc)) from exc
    if result is None:
        raise CalibrationValidationError("No calibration dots were detected")
    return result


def _metric(metrics: dict[str, Any], canonical: str, legacy: str) -> float:
    return float(metrics[canonical] if canonical in metrics else metrics[legacy])


def _reduction(before: float, after: float) -> float:
    if before == 0 or not np.isfinite(before) or not np.isfinite(after):
        return float("nan")
    return (before - after) / abs(before) * 100.0


def _validate_metrics(
    before: dict[str, Any], after: dict[str, Any], config: NeuralCalibrationConfig
) -> dict[str, float]:
    """Apply the workflow quality gate to canonical evaluation metrics."""
    pairs = {
        "straightness": ("col_rmse", "straightness_rmse"),
        "reprojection": ("reproj", "reprojection_rmse"),
        "spacing_x": ("spacing_x_std", "spacing_x_std"),
        "spacing_y": ("spacing_y_std", "spacing_y_std"),
        "diameter": ("diam_std", "diameter_std"),
    }
    reductions = {
        name: _reduction(
            _metric(before, canonical, legacy),
            _metric(after, canonical, legacy),
        )
        for name, (canonical, legacy) in pairs.items()
    }
    minimums = {
        "straightness": config.min_straightness_reduction,
        "reprojection": config.min_reprojection_reduction,
        "spacing_x": config.min_spacing_reduction,
        "spacing_y": config.min_spacing_reduction,
        "diameter": config.min_diameter_reduction,
    }
    failures = [
        f"{name} reduction {reductions[name]:.2f}% is below {minimum:.2f}%"
        for name, minimum in minimums.items()
        if not np.isfinite(reductions[name]) or reductions[name] < minimum
    ]
    if failures:
        raise CalibrationValidationError(
            "Calibration quality gate failed: " + "; ".join(failures)
        )
    return reductions


def build_inverse_maps(
    model: Any,
    width: int,
    height: int,
    norm_scale: float,
    config: NeuralCalibrationConfig,
    coordinates: Any | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Delegate inverse-map generation to canonical calibration ownership."""
    from mpips.calibration.dotgrid.neural_model.warp_image import (
        build_inverse_maps as canonical_build_inverse_maps,
        estimate_expanded_canvas,
        resolve_device,
    )

    device = resolve_device(config.device)
    model = model.to(device).eval()
    if config.canvas_mode not in {"fixed", "expanded"}:
        raise ValueError(f"Unsupported calibration canvas mode: {config.canvas_mode}")
    output_width = width
    output_height = height
    origin = (0.0, 0.0)
    expanded = None
    if config.canvas_mode == "expanded":
        expanded = estimate_expanded_canvas(
            model,
            width,
            height,
            norm_scale,
            coords=coordinates,
            sample_step=config.expanded_bounds_step,
            margin=config.expanded_margin,
            batch_size=config.batch_size,
            device=device,
        )
        output_width = int(expanded["output_size"]["width"])
        output_height = int(expanded["output_size"]["height"])
        origin = tuple(expanded["origin_xy"])
    map_x, map_y, stats = canonical_build_inverse_maps(
        model,
        output_width,
        output_height,
        norm_scale,
        step=config.remap_step,
        iterations=config.inverse_iterations,
        batch_size=config.batch_size,
        device=device,
        dst_origin=origin,
        source_width=width,
        source_height=height,
    )
    stats["canvas_mode"] = config.canvas_mode
    if expanded is not None:
        stats["expanded_canvas"] = expanded
    return map_x, map_y, stats


def load_remap(artifacts: CalibrationArtifacts) -> tuple[np.ndarray, np.ndarray]:
    """Load the fixed inverse maps from validated calibration artifacts."""
    with np.load(artifacts.remap_path) as data:
        return data["map_x"].astype(np.float32), data["map_y"].astype(np.float32)


_CACHE_FILES = (
    "compensation_model.pth",
    "remap.npz",
    "valid_mask.png",
    "metrics.json",
    "grid_coordinates.csv",
    "grid_diameters.csv",
    "grid_circularity.csv",
    "compensated_coordinates.csv",
    "metrics.txt",
    "advanced_metrics.txt",
    "model_metadata.json",
    "compensated_x_plot.png",
    "compensated_y_plot.png",
    "compensated_diameters_plot.png",
    "compensated_vertical_diameter_plot.png",
)


def _cached_artifacts(directory: Path, fingerprint: str) -> CalibrationArtifacts | None:
    metadata_path = directory / "metadata.json"
    if not metadata_path.is_file() or not all(
        (directory / name).is_file() and (directory / name).stat().st_size > 0
        for name in _CACHE_FILES
    ):
        return None
    try:
        metadata = json.loads(metadata_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    shape = metadata.get("image_shape")
    if (
        metadata.get("fingerprint") != fingerprint
        or metadata.get("validated") is not True
        or not isinstance(shape, list)
        or len(shape) != 2
    ):
        return None
    return CalibrationArtifacts(
        fingerprint=fingerprint,
        directory=directory,
        model_path=directory / "compensation_model.pth",
        remap_path=directory / "remap.npz",
        mask_path=directory / "valid_mask.png",
        metrics_path=directory / "metrics.json",
        metadata_path=metadata_path,
        image_shape=(int(shape[0]), int(shape[1])),
        validated=True,
        cache_hit=True,
    )


def build_or_load_calibration(
    calibration_npz: str | Path,
    artifact_dir: str | Path,
    config: NeuralCalibrationConfig | None = None,
    *,
    calibration_gain_npz: str | Path | None = None,
) -> CalibrationArtifacts:
    """Build calibration artifacts, optionally rebuilding input with a gain NPZ."""
    config = config or NeuralCalibrationConfig()
    source = Path(calibration_npz)
    image, source_metadata, gain_metadata = _load_calibration_image(
        source, calibration_gain_npz
    )
    payload = {
        "source_sha256": sha256_file(source),
        "config": config.cache_dict(),
        "image_shape": list(image.shape),
        "mpips_version": mpips.__version__,
    }
    if gain_metadata is not None:
        payload["calibration_gain"] = gain_metadata
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    fingerprint = hashlib.sha256(serialized).hexdigest()
    durable_directory = Path(artifact_dir) / fingerprint
    cached = _cached_artifacts(durable_directory, fingerprint)
    if cached is not None and not config.force_retrain:
        return cached

    try:
        from mpips.calibration.dotgrid.neural_model.dataset import load_data
        from mpips.calibration.dotgrid.neural_model.evaluate import (
            evaluate_model,
        )
        from mpips.calibration.dotgrid.neural_model.train import train_model
        from mpips.calibration.dotgrid.neural_model.validate_outputs import (
            validate_outputs,
        )
    except ImportError as exc:
        raise ImportError(
            "Neural calibration requires the calibration extra: "
            "pip install 'mpips[calibration]'"
        ) from exc

    local_stage_root = Path("/content") if Path("/content").is_dir() else None
    staging = tempfile.TemporaryDirectory(
        prefix="mpips-calibration-",
        dir=str(local_stage_root) if local_stage_root is not None else None,
    )
    directory = Path(staging.name) / fingerprint
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / "compensation_model.pth"
    remap_path = directory / "remap.npz"
    mask_path = directory / "valid_mask.png"
    metrics_path = directory / "metrics.json"
    metadata_path = directory / "metadata.json"
    calibration_tiff = directory / "calibration_processed.tiff"
    calibrated_tiff = directory / "calibrated_image.tiff"
    image_u8 = np.rint(image * 255.0).clip(0, 255).astype(np.uint8)
    write_tiff(calibration_tiff, image_u8)

    from mpips.calibration.dotgrid.extract_grid import extract_grid

    try:
        extracted = extract_grid(
            str(calibration_tiff),
            str(directory),
            threshold=config.threshold,
            minimum_contour_area=config.minimum_contour_area,
            row_tolerance=config.row_tolerance,
        )
    except ValueError as exc:
        raise CalibrationValidationError(str(exc)) from exc
    if extracted is None:
        raise CalibrationValidationError("No calibration dots were detected")

    coords_path = directory / "grid_coordinates.csv"
    diams_path = directory / "grid_diameters.csv"
    model = train_model(
        str(coords_path),
        str(diams_path),
        str(directory),
        epochs=config.epochs,
        lr=config.learning_rate,
        target_loss=config.target_loss,
        hidden_dim=config.hidden_dim,
        seed=config.seed,
        smoothness_weight=config.smoothness_weight,
        edge_balance_weight=config.edge_balance_weight,
        center_marker_mode="auto",
        center_marker_min_ratio=config.center_marker_min_ratio,
        device=config.device,
    )
    before, after = evaluate_model(
        str(model_path),
        str(coords_path),
        str(diams_path),
        str(directory),
        image_size=(image.shape[1], image.shape[0]),
        hidden_dim=config.hidden_dim,
        center_marker_mode="auto",
        center_marker_min_ratio=config.center_marker_min_ratio,
    )
    reductions = _validate_metrics(before, after, config)
    coordinates, _ = load_data(str(coords_path), str(diams_path))
    norm_scale = float(coordinates.max().item())
    height, width = image.shape
    map_x, map_y, remap_stats = build_inverse_maps(
        model, width, height, norm_scale, config, coordinates=coordinates
    )
    if config.canvas_mode == "fixed":
        remap_stats.update(validate_fixed_canvas_remap(map_x, map_y, width, height))
    else:
        remap_stats.update(
            remap_geometry_evidence(
                map_x, map_y, width, height, output_shape=map_x.shape
            )
        )
    np.savez_compressed(remap_path, map_x=map_x, map_y=map_y)
    valid_mask = (
        (map_x >= 0) & (map_x <= width - 1) & (map_y >= 0) & (map_y <= height - 1)
    )
    if not cv2.imwrite(str(mask_path), valid_mask.astype(np.uint8) * 255):
        raise OSError(f"Unable to write calibration mask: {mask_path}")
    calibrated = cv2.remap(
        image_u8,
        map_x,
        map_y,
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    write_tiff(calibrated_tiff, calibrated)

    validated = validate_outputs(
        str(coords_path),
        str(diams_path),
        str(model_path),
        str(directory),
        image_path=str(calibration_tiff),
        calibrated_path=str(calibrated_tiff),
        mask_path=str(mask_path),
        hidden_dim=config.hidden_dim,
        min_straightness_reduction=config.min_straightness_reduction,
        min_reprojection_reduction=config.min_reprojection_reduction,
        min_spacing_reduction=config.min_spacing_reduction,
        min_diameter_reduction=config.min_diameter_reduction,
        center_marker_mode="auto",
        center_marker_min_ratio=config.center_marker_min_ratio,
        allow_expanded_calibrated=config.canvas_mode == "expanded",
    )
    if not validated:
        raise CalibrationValidationError(
            "Canonical calibration output validation failed; see the metrics above"
        )

    metrics_path.write_text(
        json.dumps(
            {
                "validated": True,
                "before": before,
                "after": after,
                "reductions_percent": reductions,
                "remap": remap_stats,
            },
            indent=2,
        )
        + "\n"
    )
    metadata = {
        **payload,
        "fingerprint": fingerprint,
        "validated": True,
        "source": str(source),
        "source_metadata": source_metadata,
        "grid_shape": list(extracted[0].shape[:2]),
        "SOURCE_IMAGE_SHAPE": list(image.shape),
        "REMAP_OUTPUT_SHAPE": list(map_x.shape),
        "CANVAS_MODE": config.canvas_mode,
    }
    if config.canvas_mode == "expanded":
        expanded = remap_stats.get("expanded_canvas", {})
        metadata["expanded_origin_xy"] = expanded.get("origin_xy")
        metadata["expanded_output_size"] = expanded.get("output_size")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    durable_directory.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(directory, durable_directory, dirs_exist_ok=True)
    staging.cleanup()
    return CalibrationArtifacts(
        fingerprint=fingerprint,
        directory=durable_directory,
        model_path=durable_directory / model_path.name,
        remap_path=durable_directory / remap_path.name,
        mask_path=durable_directory / mask_path.name,
        metrics_path=durable_directory / metrics_path.name,
        metadata_path=durable_directory / metadata_path.name,
        image_shape=image.shape,
        validated=True,
        cache_hit=False,
    )
