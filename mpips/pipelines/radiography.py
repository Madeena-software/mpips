"""Canonical array-only radiography pipeline."""

from __future__ import annotations

import numpy as np

from mpips.processing.correction import flat_field_correction
from mpips.processing.filtering import apply_median_filter
from mpips.processing.geometry import crop_and_rotate
from mpips.processing.imagej import ImageJReplicator
from mpips.processing.intensity import invert_image
from mpips.processing.radiography import apply_calibration_remap
from mpips.processing.thresholding import apply_threshold_separation, detect_threshold
from mpips.processing.wavelet import WaveletDenoiser

from .config import ImagerPipelineConfig

MAX_8BIT = 255
MAX_16BIT = 65535
_THRESHOLD_SKIP_VALUES = {"none", "off", "skip", "no"}


class RadiographyPipeline:
    """Process radiography arrays without engine, workflow, or file I/O state."""

    def __init__(
        self,
        config: ImagerPipelineConfig | None = None,
        *,
        imagej_available: bool = True,
    ) -> None:
        self.config = config or ImagerPipelineConfig()
        self.imagej_available = imagej_available

    def process(
        self,
        raw: np.ndarray,
        dark: np.ndarray,
        flat: np.ndarray,
        detector_mode: str,
        *,
        map_x: np.ndarray | None = None,
        map_y: np.ndarray | None = None,
    ) -> np.ndarray:
        """Return the processed uint16 radiography array."""
        if raw.shape != dark.shape or raw.shape != flat.shape:
            raise ValueError(
                f"Raw/dark/flat shapes differ: {raw.shape}, {dark.shape}, {flat.shape}"
            )
        if map_x is not None or map_y is not None:
            if map_x is None or map_y is None:
                raise ValueError("Both map_x and map_y are required")

        raw_image = raw.astype(np.float32) / MAX_16BIT
        dark_image = dark.astype(np.float32) / MAX_16BIT
        flat_image = flat.astype(np.float32) / MAX_16BIT

        if self.config.use_denoise:
            dark_image = self._denoise(dark_image)
            flat_image = self._denoise(flat_image)
            raw_image = self._denoise(raw_image)

        ffc_result = flat_field_correction(raw_image, dark_image, flat_image)

        valid_remap_mask: np.ndarray | None = None
        if map_x is not None and map_y is not None:
            source_height, source_width = ffc_result.shape[:2]
            valid_remap_mask = (
                (map_x >= 0)
                & (map_x <= source_width - 1)
                & (map_y >= 0)
                & (map_y <= source_height - 1)
            ).astype(np.uint8)
            ffc_result = apply_calibration_remap(ffc_result, map_x, map_y)

        if self.config.use_crop_rotate:
            ffc_result = self._crop_and_rotate(ffc_result, detector_mode)
            if valid_remap_mask is not None:
                valid_remap_mask = (
                    self._crop_and_rotate(valid_remap_mask, detector_mode) > 0
                )

        if self.config.use_normalize:
            normalized_result = self._normalize_to_max_value(ffc_result)
        else:
            normalized_result = ffc_result.copy()

        threshold_method = self.config.threshold_method.lower()
        if not self.config.use_threshold or threshold_method in _THRESHOLD_SKIP_VALUES:
            threshold_result = normalized_result.copy()
        else:
            threshold = detect_threshold(normalized_result, method=threshold_method)
            threshold_result = apply_threshold_separation(normalized_result, threshold)

        if self.config.use_invert:
            inverted = invert_image(threshold_result)
        else:
            inverted = threshold_result

        if not self.config.use_contrast_enhancement or not self.imagej_available:
            enhanced_uint16 = (
                (inverted * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
            )
        else:
            inverted_uint16 = (
                (inverted * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
            )
            enhanced = ImageJReplicator.enhance_contrast(
                inverted_uint16,
                saturated_pixels=self.config.contrast_saturated_pixels,
                normalize=self.config.contrast_normalize,
                equalize=self.config.contrast_equalize,
                classic_equalization=self.config.contrast_classic_equalization,
            )
            if enhanced.dtype == np.uint8:
                enhanced_uint16 = (
                    enhanced.astype(np.float32) / MAX_8BIT * MAX_16BIT
                ).astype(np.uint16)
            else:
                enhanced_uint16 = enhanced

        if not self.config.use_clahe or not self.imagej_available:
            final_result_uint16 = enhanced_uint16
        else:
            clahe_result = ImageJReplicator.apply_clahe(
                enhanced_uint16,
                blocksize=self.config.clahe_blocksize,
                histogram_bins=self.config.clahe_histogram_bins,
                max_slope=self.config.clahe_max_slope,
                mask=None,
                fast=self.config.clahe_fast,
                composite=self.config.clahe_composite,
            )
            if clahe_result.dtype == np.uint8:
                final_result_uint16 = (
                    clahe_result.astype(np.float32) / MAX_8BIT * MAX_16BIT
                ).astype(np.uint16)
            else:
                final_result_uint16 = clahe_result

        if self.config.use_final_denoise:
            final_denoised = self._denoise(
                final_result_uint16.astype(np.float32) / MAX_16BIT
            )
            final_result_uint16 = (
                (final_denoised * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
            )

        if self.config.use_median_filter:
            final_result_uint16 = apply_median_filter(
                final_result_uint16,
                filter_type=self.config.median_filter_type,
                radius=self.config.median_filter_radius,
                imagej_available=self.imagej_available,
            )

        if valid_remap_mask is not None:
            final_result_uint16[~valid_remap_mask] = 0

        return np.asarray(final_result_uint16, dtype=np.uint16)

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        denoiser = WaveletDenoiser(self.config.wavelet, self.config.wavelet_level)
        return denoiser.denoise_wavelet(
            image,
            method=self.config.wavelet_method,
            mode=self.config.wavelet_mode,
        )

    def _crop_and_rotate(self, image: np.ndarray, detector_mode: str) -> np.ndarray:
        return crop_and_rotate(
            image,
            detector_mode,
            crop_top=self.config.crop_top,
            crop_bottom=self.config.crop_bottom,
            crop_left=self.config.crop_left,
            crop_right=self.config.crop_right,
        )

    def _normalize_to_max_value(self, image: np.ndarray) -> np.ndarray:
        if not self.imagej_available:
            return image

        if image.dtype == np.float32 or image.dtype == np.float64:
            image_uint16 = np.clip(image, 0, MAX_16BIT).astype(np.uint16)
        else:
            image_uint16 = image

        return ImageJReplicator.enhance_contrast(
            image_uint16,
            saturated_pixels=self.config.normalize_saturated_pixels,
            equalize=False,
            normalize=True,
            classic_equalization=False,
        )
