"""NumPy flat-field correction for radiography arrays."""

from typing import cast

import numpy as np


def flat_field_correction(
    raw_image: np.ndarray, dark_image: np.ndarray, flat_image: np.ndarray
) -> np.ndarray:
    """Perform the legacy CPU flat-field correction calculation."""
    raw_32 = raw_image.astype(np.float32, copy=False)
    dark_32 = dark_image.astype(np.float32, copy=False)
    flat_32 = flat_image.astype(np.float32, copy=False)

    # Calculate (flat - dark)
    flat_minus_dark = np.maximum(0, flat_32 - dark_32)

    # Calculate mean of (flat - dark)
    mean_value = np.mean(flat_minus_dark)

    # Calculate (raw - dark)
    raw_minus_dark = np.maximum(0, raw_32 - dark_32)

    # Calculate (raw - dark) / (flat - dark)
    corrected = np.zeros_like(raw_minus_dark)
    mask = flat_minus_dark != 0
    corrected[mask] = raw_minus_dark[mask] / flat_minus_dark[mask]

    # Multiply by mean to restore intensity scale
    corrected = corrected * mean_value

    # Clip negative values
    corrected = np.clip(corrected, 0, None)

    # Keep as float32 if input is float, otherwise convert back to original dtype
    if raw_image.dtype == np.float32:
        return cast(np.ndarray, corrected.astype(np.float32))
    if raw_image.dtype == np.uint8:
        return cast(np.ndarray, np.clip(corrected, 0, 255).astype(np.uint8))
    if raw_image.dtype == np.uint16:
        return cast(np.ndarray, np.clip(corrected, 0, 65535).astype(np.uint16))
    return cast(np.ndarray, corrected.astype(raw_image.dtype))
