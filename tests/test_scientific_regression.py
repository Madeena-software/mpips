"""Deterministic regression contracts for canonical radiography operations."""

import hashlib
from typing import Any, cast

import numpy as np

from mpips.processing import (
    apply_calibration_remap,
    apply_threshold_separation,
    auto_threshold,
    denoise_wavelet,
    flat_field_correction,
)


def _wavelet_fixture() -> np.ndarray:
    height, width = 64, 80
    y_values, x_values = np.indices((height, width), dtype=np.float64)
    background = (
        12000
        + 180 * x_values
        + 95 * y_values
        + 700 * np.sin(x_values / 4)
        + 500 * np.cos(y_values / 5)
    )
    edges = np.where((x_values >= 25) & (x_values < 34), 5200, 0)
    edges += np.where((y_values >= 38) & (y_values < 45), -3100, 0)
    texture = (
        (x_values * 17 + y_values * 29 + (x_values * y_values) % 13 * 41) % 401
    ) - 200
    return cast(
        np.ndarray,
        np.clip(background + edges + texture, 0, 65535).astype(np.uint16),
    )


def test_wavelet_sym4_bayesshrink_soft_matches_historical_golden() -> None:
    image = _wavelet_fixture()
    output = denoise_wavelet(image, "sym4", 3, "BayesShrink", "soft")

    assert output.shape == image.shape
    assert output.dtype == np.uint16
    assert 0 <= output.min() <= output.max() <= 65535
    assert np.isfinite(output).all()
    assert hashlib.sha256(output.tobytes()).hexdigest() == (
        "b58366976b1c25c368d412e4f16ebc1a0537cda86afebd1ee6fddce63b32f6d9"
    )
    np.testing.assert_array_equal(
        output[[0, 10, 30, 40, 50, 63], [0, 10, 30, 30, 60, 79]],
        np.array([12908, 14972, 26416, 24059, 27491, 33086], dtype=np.uint16),
    )


def test_wavelet_preserves_uint8_uint16_and_float32_contracts() -> None:
    uint16_image = _wavelet_fixture()
    cases = (
        (uint16_image.astype(np.uint8), np.dtype(np.uint8), 255.0),
        (uint16_image, np.dtype(np.uint16), 65535.0),
        (uint16_image.astype(np.float32) / 65535.0, np.dtype(np.float32), 1.0),
    )

    for image, expected_dtype, maximum in cases:
        output = denoise_wavelet(image, "sym4", 3, "BayesShrink", "soft")
        assert output.shape == image.shape
        assert output.dtype == expected_dtype
        assert np.isfinite(output).all()
        assert 0 <= output.min() <= output.max() <= maximum


def test_flat_field_correction_matches_historical_pixels_and_zero_denominator() -> None:
    raw = np.array([[10, 20, 30], [40, 50, 60]], dtype=np.uint16)
    dark = np.full_like(raw, 5)
    flat = np.array([[5, 15, 25], [35, 45, 55]], dtype=np.uint16)

    output = flat_field_correction(raw, dark, flat)

    assert output.shape == raw.shape
    assert output.dtype == np.uint16
    np.testing.assert_array_equal(
        output,
        np.array([[0, 37, 31], [29, 28, 27]], dtype=np.uint16),
    )
    zero_denominator = flat_field_correction(
        np.array([[4]], dtype=np.uint16),
        np.array([[4]], dtype=np.uint16),
        np.array([[4]], dtype=np.uint16),
    )
    np.testing.assert_array_equal(zero_denominator, np.zeros((1, 1), dtype=np.uint16))


def test_flat_field_correction_preserves_supported_dtypes() -> None:
    for dtype in (np.uint8, np.uint16, np.float32):
        raw = np.array([[10, 20], [30, 40]], dtype=dtype)
        output = flat_field_correction(raw, np.zeros_like(raw), np.full_like(raw, 100))
        assert output.shape == raw.shape
        assert output.dtype == raw.dtype
        if dtype == np.float32:
            np.testing.assert_allclose(output, cast(Any, raw), rtol=0, atol=3e-6)
        else:
            np.testing.assert_array_equal(output, raw)


def test_auto_threshold_and_separation_lock_boundary_behavior() -> None:
    image = np.array(
        [0.10] * 32 + [0.20] * 32 + [0.70] * 32 + [0.80] * 32, dtype=np.float32
    ).reshape(8, 16)

    threshold = auto_threshold(image)
    assert threshold == 0.21826171875

    output = apply_threshold_separation(
        np.array([[threshold - 0.01, threshold, threshold + 0.01]], dtype=np.float32),
        threshold,
    )
    assert output.shape == (1, 3)
    assert output.dtype == np.float32
    assert np.isfinite(output).all()
    assert 0 <= output.min() <= output.max() <= 1
    np.testing.assert_array_equal(output, np.array([[0.0, 1.0, 1.0]], dtype=np.float32))


def test_calibration_remap_identity_preserves_shape_and_dtype() -> None:
    image = np.arange(25, dtype=np.uint16).reshape(5, 5)
    y_values, x_values = np.indices(image.shape, dtype=np.float32)

    output = apply_calibration_remap(image, x_values, y_values)

    assert output.shape == image.shape
    assert output.dtype == np.uint16
    np.testing.assert_array_equal(output, image)


def test_calibration_remap_subpixel_translation_locks_border_behavior() -> None:
    image = np.arange(25, dtype=np.uint16).reshape(5, 5)
    y_values, x_values = np.indices(image.shape, dtype=np.float32)

    output = apply_calibration_remap(image, x_values - 0.5, y_values - 0.5)

    np.testing.assert_array_equal(
        output,
        np.array(
            [
                [0, 0, 1, 1, 2],
                [1, 3, 4, 5, 6],
                [4, 8, 9, 10, 11],
                [6, 13, 14, 15, 16],
                [9, 18, 19, 20, 21],
            ],
            dtype=np.uint16,
        ),
    )
