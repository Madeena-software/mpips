"""Reusable array adapters over the canonical radiography implementations."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _engine() -> Any:
    from mpips.engine.imager_pipeline import complete_pipeline

    return complete_pipeline


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


def denoise_wavelet(
    image: np.ndarray, wavelet: str, level: int, method: str, mode: str
) -> np.ndarray:
    engine = _engine()
    return np.asarray(engine.denoise_wavelet(image, wavelet, level, method, mode))


def flat_field_correction(
    raw: np.ndarray, dark: np.ndarray, flat: np.ndarray
) -> np.ndarray:
    engine = _engine()
    return np.asarray(engine.flat_field_correction(raw, dark, flat))


def auto_threshold(image: np.ndarray, method: str = "auto") -> float:
    if method != "auto":
        raise ValueError(
            "The canonical research implementation supports only 'auto' thresholding"
        )

    engine = _engine()
    return float(engine.auto_threshold_detection(image))


def apply_threshold_separation(image: np.ndarray, threshold: float) -> np.ndarray:
    engine = _engine()
    return np.asarray(engine.apply_threshold_separation(image, threshold))


def imagej_stretch(image: np.ndarray, saturated_pixels: float) -> np.ndarray:
    from mpips.engine.imager_pipeline.imagej_replicator import ImageJReplicator

    return np.asarray(
        ImageJReplicator.enhance_contrast(
            image,
            saturated_pixels=saturated_pixels,
            equalize=False,
            normalize=True,
        )
    )


def imagej_equalize(image: np.ndarray, classic: bool = False) -> np.ndarray:
    from mpips.engine.imager_pipeline.imagej_replicator import ImageJReplicator

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
    from mpips.engine.imager_pipeline.imagej_replicator import ImageJReplicator

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
    from mpips.engine.imager_pipeline.imagej_replicator import ImageJReplicator

    kernel_size = min(7, max(3, int(radius) * 2 + 1))
    return np.asarray(
        ImageJReplicator.hybrid_median_filter_2d(
            image, kernel_size=kernel_size, repetitions=1
        )
    )


def apply_median_filter(image: np.ndarray, filter_type: str, radius: int) -> np.ndarray:
    engine = _engine()
    return np.asarray(engine.apply_advanced_median_filter(image, filter_type, radius))
