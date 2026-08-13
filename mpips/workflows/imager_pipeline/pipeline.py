"""Thin array adapters over the canonical imager pipeline engine."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from mpips.engine.imager_pipeline import complete_pipeline as engine
from mpips.engine.imager_pipeline.imagej_replicator import ImageJReplicator
from mpips.workflows.imager_pipeline.models import ImagerPipelineConfig

MAX_UINT16 = 65535


@contextmanager
def _configured_engine(config: ImagerPipelineConfig) -> Iterator[None]:
    updates = config.to_legacy_engine_dict()
    previous = {key: engine.CONFIG.get(key) for key in updates}
    engine.CONFIG.update(updates)
    try:
        yield
    finally:
        engine.CONFIG.update(previous)


def apply_calibration_remap(
    image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray
) -> np.ndarray:
    """Apply a canonical fixed-canvas neural inverse remap."""
    if map_x.shape != map_y.shape:
        raise ValueError(
            f"Image/remap shapes differ: {image.shape}, {map_x.shape}, {map_y.shape}"
        )
    return cv2.remap(
        image,
        map_x.astype(np.float32, copy=False),
        map_y.astype(np.float32, copy=False),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def crop_and_rotate(
    image: np.ndarray, detector_mode: str, config: ImagerPipelineConfig
) -> np.ndarray:
    with _configured_engine(config):
        return np.asarray(engine.crop_and_rotate_by_detector(image, detector_mode))


def denoise_wavelet(
    image: np.ndarray, wavelet: str, level: int, method: str, mode: str
) -> np.ndarray:
    return np.asarray(engine.denoise_wavelet(image, wavelet, level, method, mode))


def flat_field_correction(
    raw: np.ndarray, dark: np.ndarray, flat: np.ndarray
) -> np.ndarray:
    return np.asarray(engine.flat_field_correction(raw, dark, flat))


def auto_threshold(image: np.ndarray, method: str = "auto") -> float:
    if method != "auto":
        raise ValueError(
            "The canonical research implementation supports only 'auto' thresholding"
        )
    return float(engine.auto_threshold_detection(image))


def apply_threshold_separation(image: np.ndarray, threshold: float) -> np.ndarray:
    return np.asarray(engine.apply_threshold_separation(image, threshold))


def imagej_stretch(image: np.ndarray, saturated_pixels: float) -> np.ndarray:
    return np.asarray(
        ImageJReplicator.enhance_contrast(
            image,
            saturated_pixels=saturated_pixels,
            equalize=False,
            normalize=True,
        )
    )


def imagej_equalize(image: np.ndarray, classic: bool = False) -> np.ndarray:
    return np.asarray(
        ImageJReplicator.enhance_contrast(
            image,
            saturated_pixels=0.0,
            equalize=True,
            normalize=False,
            classic_equalization=classic,
        )
    )


def apply_clahe(
    image: np.ndarray,
    blocksize: int,
    histogram_bins: int,
    maximum_slope: float,
    *,
    fast: bool = False,
    composite: bool = True,
) -> np.ndarray:
    return np.asarray(
        ImageJReplicator.apply_clahe(
            image,
            blocksize=blocksize,
            histogram_bins=histogram_bins,
            max_slope=maximum_slope,
            fast=fast,
            composite=composite,
        )
    )


def hybrid_median_filter(image: np.ndarray, radius: int) -> np.ndarray:
    kernel_size = min(7, max(3, int(radius) * 2 + 1))
    return np.asarray(
        ImageJReplicator.hybrid_median_filter_2d(
            image, kernel_size=kernel_size, repetitions=1
        )
    )


def apply_median_filter(image: np.ndarray, filter_type: str, radius: int) -> np.ndarray:
    return np.asarray(engine.apply_advanced_median_filter(image, filter_type, radius))


def _write_tiff(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Unable to write temporary TIFF: {path}")


def process_radiography_arrays(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    detector_mode: str,
    config: ImagerPipelineConfig | None = None,
    *,
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
) -> np.ndarray:
    """Run arrays through the promoted research pipeline without reimplementing it."""
    config = config or ImagerPipelineConfig()
    if raw.shape != dark.shape or raw.shape != flat.shape:
        raise ValueError(
            f"Raw/dark/flat shapes differ: {raw.shape}, {dark.shape}, {flat.shape}"
        )
    if map_x is not None or map_y is not None:
        if map_x is None or map_y is None:
            raise ValueError("Both map_x and map_y are required")

    with tempfile.TemporaryDirectory(prefix="mpips-engine-radiography-") as temporary:
        workspace = Path(temporary)
        raw_path = workspace / "raw.tiff"
        dark_path = workspace / "dark.tiff"
        flat_path = workspace / "flat.tiff"
        output_path = workspace / "processed.tiff"
        _write_tiff(raw_path, raw)
        _write_tiff(dark_path, dark)
        _write_tiff(flat_path, flat)
        with _configured_engine(config):
            succeeded = engine.process_single_image(
                str(raw_path),
                str(dark_path),
                str(flat_path),
                str(output_path),
                detector_type=detector_mode,
                map_x=map_x,
                map_y=map_y,
            )
        if not succeeded:
            raise RuntimeError("The canonical radiography pipeline failed")
        result = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
        if result is None:
            raise OSError("The canonical radiography pipeline produced no TIFF")
        return np.asarray(result, dtype=np.uint16)
