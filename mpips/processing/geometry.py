"""Pure geometry operations for radiography arrays."""

import cv2
import numpy as np


def crop_and_rotate(
    image: np.ndarray,
    detector_mode: str,
    *,
    crop_top: int = 0,
    crop_bottom: int = 0,
    crop_left: int = 0,
    crop_right: int = 0,
) -> np.ndarray:
    """Crop image borders and rotate TRX images counterclockwise."""
    height, width = image.shape[:2]
    cropped = image[crop_top : height - crop_bottom, crop_left : width - crop_right]

    if detector_mode == "TRX":
        return cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return cropped
