"""Pure image warping helpers for runtime calibration."""

from __future__ import annotations

import cv2
import numpy as np


def warp_image(
    image: np.ndarray,
    map_x: np.ndarray,
    map_y: np.ndarray,
    interpolation: int = cv2.INTER_LINEAR,
    border_mode: int = cv2.BORDER_CONSTANT,
    border_value: int | float = 0,
) -> np.ndarray:
    """Apply OpenCV remap using explicit coordinate maps."""
    return cv2.remap(
        image,
        map_x.astype(np.float32, copy=False),
        map_y.astype(np.float32, copy=False),
        interpolation,
        borderMode=border_mode,
        borderValue=border_value,
    )
