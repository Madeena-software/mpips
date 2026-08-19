"""Reusable array adapters over the canonical radiography implementations."""

from __future__ import annotations

import cv2
import numpy as np

from mpips.processing.correction import flat_field_correction  # noqa: F401
from mpips.processing.filtering import (
    apply_median_filter as canonical_apply_median_filter,
)
from mpips.processing.thresholding import (  # noqa: F401
    apply_threshold_separation,
    detect_threshold,
)
from mpips.processing.wavelet import WaveletDenoiser


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
    denoiser = WaveletDenoiser(wavelet=wavelet, level=level)
    return np.asarray(denoiser.denoise_wavelet(image, method=method, mode=mode))


def auto_threshold(image: np.ndarray, method: str = "auto") -> float:
    if method != "auto":
        raise ValueError(
            "The canonical research implementation supports only 'auto' thresholding"
        )

    return float(detect_threshold(image, method="auto", debug=False))


def imagej_stretch(image: np.ndarray, saturated_pixels: float) -> np.ndarray:
    from mpips.processing.imagej import ImageJReplicator

    return np.asarray(
        ImageJReplicator.enhance_contrast(
            image,
            saturated_pixels=saturated_pixels,
            equalize=False,
            normalize=True,
        )
    )


def imagej_equalize(image: np.ndarray, classic: bool = False) -> np.ndarray:
    from mpips.processing.imagej import ImageJReplicator

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
    from mpips.processing.imagej import ImageJReplicator

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
    from mpips.processing.imagej import ImageJReplicator

    kernel_size = min(7, max(3, int(radius) * 2 + 1))
    return np.asarray(
        ImageJReplicator.hybrid_median_filter_2d(
            image, kernel_size=kernel_size, repetitions=1
        )
    )


def apply_median_filter(
    image: np.ndarray,
    filter_type: str,
    radius: int,
    *,
    imagej_available: bool = True,
) -> np.ndarray:
    return np.asarray(
        canonical_apply_median_filter(
            image,
            filter_type=filter_type,
            radius=radius,
            imagej_available=imagej_available,
        )
    )
