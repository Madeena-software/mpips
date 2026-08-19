"""Canonical median and denoising filters for radiography arrays."""

from typing import Any, cast

import cv2
import numpy as np
import skimage.restoration
from scipy.ndimage import median_filter

from mpips.processing.imagej import ImageJReplicator

MAX_8BIT = 255
MAX_16BIT = 65535


def apply_median_filter(
    image: np.ndarray,
    filter_type: str = "hybrid_imagej",
    radius: int = 2,
    *,
    imagej_available: bool = True,
) -> np.ndarray:
    """Apply the historical advanced median filter implementation."""
    if filter_type == "standard":
        ksize = 2 * radius + 1
        return cast(np.ndarray, median_filter(image, size=ksize).astype(image.dtype))

    if filter_type == "bilateral":
        if image.dtype == np.uint16:
            img_8bit = (image / MAX_16BIT * MAX_8BIT).astype(np.uint8)
            filtered_8bit = cv2.bilateralFilter(
                img_8bit, d=radius * 2 + 1, sigmaColor=30, sigmaSpace=30
            )
            return (filtered_8bit.astype(np.float32) / MAX_8BIT * MAX_16BIT).astype(
                np.uint16
            )
        return cast(
            np.ndarray,
            cv2.bilateralFilter(image, d=radius * 2 + 1, sigmaColor=30, sigmaSpace=30),
        )

    if filter_type == "adaptive":
        return _adaptive_median_filter(image, max_kernel_size=radius * 2 + 1)

    if filter_type == "nlm":
        try:
            if image.dtype == np.uint16:
                img_float = image.astype(np.float32) / MAX_16BIT
                filtered_float = cast(Any, skimage.restoration.denoise_nl_means)(
                    img_float, h=0.1, fast_mode=True, multichannel=False
                )
                return cast(
                    np.ndarray,
                    (filtered_float * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16),
                )
            img_float = image.astype(np.float32) / MAX_8BIT
            filtered_float = cast(Any, skimage.restoration.denoise_nl_means)(
                img_float, h=0.1, fast_mode=True, multichannel=False
            )
            return cast(
                np.ndarray,
                (filtered_float * MAX_8BIT).clip(0, MAX_8BIT).astype(np.uint8),
            )
        except Exception as error:
            print(f"    Warning: NLM failed ({error}), falling back to standard median")
            return apply_median_filter(image, "standard", radius)

    if filter_type == "morphological":
        try:
            kernel_size = radius * 2 + 1
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
            )
            return cast(np.ndarray, cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel))
        except Exception as error:
            print(
                f"    Warning: Morphological filter failed ({error}), "
                "falling back to standard median"
            )
            return apply_median_filter(image, "standard", radius)

    if filter_type == "hybrid_imagej":
        try:
            if not imagej_available:
                print(
                    "    Warning: ImageJ not available, falling back to adaptive median"
                )
                return apply_median_filter(image, "adaptive", radius)

            kernel_size = radius * 2 + 1
            if kernel_size < 3:
                kernel_size = 3
            elif kernel_size > 7:
                kernel_size = 7
            elif kernel_size % 2 == 0:
                kernel_size += 1

            return ImageJReplicator.hybrid_median_filter_2d(
                image, kernel_size=kernel_size, repetitions=1
            )
        except Exception as error:
            print(
                f"    Warning: ImageJ Hybrid filter failed ({error}), "
                "falling back to adaptive median"
            )
            return apply_median_filter(image, "adaptive", radius)

    if filter_type == "circular_imagej":
        try:
            if not imagej_available:
                print(
                    "    Warning: ImageJ not available, falling back to standard median"
                )
                return apply_median_filter(image, "standard", radius)

            return ImageJReplicator.median_filter_imagej(image, radius=float(radius))
        except Exception as error:
            print(
                f"    Warning: ImageJ circular filter failed ({error}), "
                "falling back to standard median"
            )
            return apply_median_filter(image, "standard", radius)

    print(f"    Warning: Unknown filter type '{filter_type}', using hybrid ImageJ")
    return apply_median_filter(
        image, "hybrid_imagej", radius, imagej_available=imagej_available
    )


def _adaptive_median_filter(image: np.ndarray, max_kernel_size: int = 7) -> np.ndarray:
    """Apply the historical adaptive median filter."""
    filtered = np.copy(image)
    height, width = image.shape

    for i in range(1, height - 1):
        for j in range(1, width - 1):
            kernel_size = 3

            while kernel_size <= max_kernel_size:
                half_size = kernel_size // 2
                i_start = max(0, i - half_size)
                i_end = min(height, i + half_size + 1)
                j_start = max(0, j - half_size)
                j_end = min(width, j + half_size + 1)
                window = image[i_start:i_end, j_start:j_end]

                med_val = np.median(window)
                min_val = np.min(window)
                max_val = np.max(window)
                current_val = image[i, j]

                if min_val < med_val < max_val:
                    if min_val < current_val < max_val:
                        filtered[i, j] = current_val
                    else:
                        filtered[i, j] = med_val
                    break
                kernel_size += 2

            if kernel_size > max_kernel_size:
                half_size = max_kernel_size // 2
                i_start = max(0, i - half_size)
                i_end = min(height, i + half_size + 1)
                j_start = max(0, j - half_size)
                j_end = min(width, j + half_size + 1)
                window = image[i_start:i_end, j_start:j_end]
                filtered[i, j] = np.median(window)

    return filtered.astype(image.dtype)
