from typing import Tuple, cast

import cv2
import numpy as np


def dtype_limits(image: np.ndarray) -> Tuple[float, float]:
    """Return the numeric range for an image dtype."""
    if np.issubdtype(image.dtype, np.integer):
        info = np.iinfo(image.dtype)
        return float(info.min), float(info.max)

    if image.size == 0:
        return 0.0, 1.0

    min_val = float(np.nanmin(image))
    max_val = float(np.nanmax(image))
    if max_val > min_val:
        return min_val, max_val

    if max_val <= 1.0:
        return 0.0, 1.0

    return 0.0, max_val


def clip_to_input_dtype(values: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Clip numeric results back to the input dtype without forcing uint8."""
    if np.issubdtype(reference.dtype, np.integer):
        min_val, max_val = dtype_limits(reference)
        return cast(
            np.ndarray, np.clip(values, min_val, max_val).astype(reference.dtype)
        )

    return values.astype(reference.dtype, copy=False)


def normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    """Create an 8-bit working copy for algorithms that require uint8."""
    if image.dtype == np.uint8:
        return image

    min_val, max_val = dtype_limits(image)
    if max_val > min_val:
        return (
            (image.astype(np.float64) - min_val) / (max_val - min_val) * 255.0
        ).astype(np.uint8)

    return np.zeros(image.shape, dtype=np.uint8)


def scale_unit_to_dtype(values: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Scale a 0..1 float result back into the reference image dtype/range."""
    min_val, max_val = dtype_limits(reference)
    scaled = values.astype(np.float64) * (max_val - min_val) + min_val
    return clip_to_input_dtype(scaled, reference)


def grayscale_any_depth(image: np.ndarray) -> np.ndarray:
    """Convert BGR/BGRA images to grayscale while preserving input bit depth."""
    if len(image.shape) == 2:
        return image

    channels = image.shape[2]
    if channels == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if channels == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    raise ValueError(f"Unsupported number of channels: {channels}")
