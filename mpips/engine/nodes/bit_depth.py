"""Compatibility exports for the canonical processing bit-depth helpers."""

from mpips.processing.bit_depth import (
    clip_to_input_dtype,
    dtype_limits,
    grayscale_any_depth,
    normalize_to_uint8,
    scale_unit_to_dtype,
)

__all__ = [
    "dtype_limits",
    "clip_to_input_dtype",
    "normalize_to_uint8",
    "scale_unit_to_dtype",
    "grayscale_any_depth",
]
