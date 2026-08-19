"""Thin array adapters over the canonical imager pipeline engine."""

from __future__ import annotations

import numpy as np

from mpips.pipelines.config import ImagerPipelineConfig
from mpips.pipelines.radiography import RadiographyPipeline
import mpips.processing as processing

apply_calibration_remap = processing.apply_calibration_remap
apply_clahe = processing.apply_clahe
apply_median_filter = processing.apply_median_filter
apply_threshold_separation = processing.apply_threshold_separation
auto_threshold = processing.auto_threshold
denoise_wavelet = processing.denoise_wavelet
flat_field_correction = processing.flat_field_correction
hybrid_median_filter = processing.hybrid_median_filter
imagej_equalize = processing.imagej_equalize
imagej_stretch = processing.imagej_stretch


def crop_and_rotate(
    image: np.ndarray, detector_mode: str, config: ImagerPipelineConfig
) -> np.ndarray:
    return processing.crop_and_rotate(
        image,
        detector_mode,
        crop_top=config.crop_top,
        crop_bottom=config.crop_bottom,
        crop_left=config.crop_left,
        crop_right=config.crop_right,
    )


def process_radiography_arrays(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    detector_mode: str,
    config: ImagerPipelineConfig | None = None,
    *,
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
    imagej_available: bool = True,
) -> np.ndarray:
    """Run arrays through the canonical array-only radiography pipeline."""
    config = config or ImagerPipelineConfig()
    return RadiographyPipeline(
        config,
        imagej_available=imagej_available,
    ).process(
        raw,
        dark,
        flat,
        detector_mode,
        map_x=map_x,
        map_y=map_y,
    )
