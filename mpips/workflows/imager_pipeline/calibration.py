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
    load_calibration_processed_image,
    sha256_file,
    write_tiff,
)


class CalibrationValidationError(RuntimeError):
    """Raised when canonical calibration validation rejects an artifact set."""


def extract_dot_grid(
    image: np.ndarray, config: NeuralCalibrationConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Adapt an in-memory image to the canonical research grid extractor."""
    if image.ndim != 2 or image.dtype != np.uint8:
        raise ValueError("Dot-grid extraction requires a uint8 grayscale image")
    from mpips.engine.calibration.dotgrid.extract_grid import extract_grid

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
    """Delegate fixed-canvas inverse-map generation to the canonical engine."""
    from mpips.engine.calibration.dotgrid.neural_model.warp_image import (
        build_inverse_maps as engine_build_inverse_maps,
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
    map_x, map_y, stats = engine_build_inverse_maps(
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
) -> CalibrationArtifacts:
    """Train, validate, and checksum-cache the canonical neural calibration."""
    config = config or NeuralCalibrationConfig()
    source = Path(calibration_npz)
    image, source_metadata = load_calibration_processed_image(source)
    payload = {
        "source_sha256": sha256_file(source),
        "config": config.cache_dict(),
        "image_shape": list(image.shape),
        "mpips_version": mpips.__version__,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    fingerprint = hashlib.sha256(serialized).hexdigest()
    durable_directory = Path(artifact_dir) / fingerprint
    cached = _cached_artifacts(durable_directory, fingerprint)
    if cached is not None and not config.force_retrain:
        return cached

    try:
        from mpips.engine.calibration.dotgrid.neural_model.dataset import load_data
        from mpips.engine.calibration.dotgrid.neural_model.evaluate import (
            evaluate_model,
        )
        from mpips.engine.calibration.dotgrid.neural_model.train import train_model
        from mpips.engine.calibration.dotgrid.neural_model.validate_outputs import (
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

    from mpips.engine.calibration.dotgrid.extract_grid import extract_grid

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
    }
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
