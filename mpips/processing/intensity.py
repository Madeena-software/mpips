"""Pure image intensity operations for radiography arrays."""

import cv2
import numpy as np


def invert_image(image: np.ndarray) -> np.ndarray:
    """Invert float32 images by subtraction and other images by bitwise complement."""
    if image.dtype == np.float32:
        return 1.0 - image
    return cv2.bitwise_not(image)
