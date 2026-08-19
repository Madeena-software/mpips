import importlib
import subprocess
import sys
import textwrap

import cv2
import numpy as np
import pytest

HELPER_NAMES = (
    "dtype_limits",
    "clip_to_input_dtype",
    "normalize_to_uint8",
    "scale_unit_to_dtype",
    "grayscale_any_depth",
)


def test_dtype_limits_preserves_historical_ranges() -> None:
    bit_depth = importlib.import_module("mpips.processing.bit_depth")

    cases: list[tuple[np.ndarray, tuple[float, float]]] = [
        (np.array([0, 255], dtype=np.uint8), (0.0, 255.0)),
        (np.array([0, 65535], dtype=np.uint16), (0.0, 65535.0)),
        (np.array([-32768, 32767], dtype=np.int16), (-32768.0, 32767.0)),
        (np.array([np.nan, 0.25, 0.75], dtype=np.float32), (0.25, 0.75)),
        (np.array([2.0, 4.0, 6.0], dtype=np.float32), (2.0, 6.0)),
        (np.array([0.5, 0.5], dtype=np.float32), (0.0, 1.0)),
        (np.array([4.0, 4.0], dtype=np.float32), (0.0, 4.0)),
        (np.array([], dtype=np.float32), (0.0, 1.0)),
    ]

    for image, expected in cases:
        assert bit_depth.dtype_limits(image) == expected


def test_clip_to_input_dtype_preserves_dtype_and_clipping() -> None:
    bit_depth = importlib.import_module("mpips.processing.bit_depth")

    np.testing.assert_array_equal(
        bit_depth.clip_to_input_dtype(
            np.array([-1.5, 12.9, 70000.2]), np.array([0], dtype=np.uint16)
        ),
        np.array([0, 12, 65535], dtype=np.uint16),
    )
    np.testing.assert_array_equal(
        bit_depth.clip_to_input_dtype(
            np.array([-40000.0, -1.5, 40000.0]), np.array([0], dtype=np.int16)
        ),
        np.array([-32768, -1, 32767], dtype=np.int16),
    )

    result = bit_depth.clip_to_input_dtype(
        np.array([-2.5, 3.75], dtype=np.float64), np.array([0], dtype=np.float32)
    )
    assert result.dtype == np.float32
    np.testing.assert_array_equal(result, np.array([-2.5, 3.75], dtype=np.float32))


def test_normalize_to_uint8_preserves_historical_scaling() -> None:
    bit_depth = importlib.import_module("mpips.processing.bit_depth")

    uint8 = np.array([0, 127, 255], dtype=np.uint8)
    result = bit_depth.normalize_to_uint8(uint8)
    assert result is uint8

    cases: list[tuple[np.ndarray, list[int]]] = [
        (np.array([0, 32768, 65535], dtype=np.uint16), [0, 127, 255]),
        (np.array([0.0, 0.5, 1.0], dtype=np.float32), [0, 127, 255]),
        (np.array([2.0, 4.0, 6.0], dtype=np.float32), [0, 127, 255]),
        (np.array([0.5, 0.5], dtype=np.float32), [127, 127]),
        (np.array([], dtype=np.float32), []),
    ]

    for image, expected in cases:
        result = bit_depth.normalize_to_uint8(image)
        assert result.dtype == np.uint8
        assert result.shape == image.shape
        np.testing.assert_array_equal(result, np.array(expected, dtype=np.uint8))


def test_scale_unit_to_dtype_preserves_reference_range_and_casting() -> None:
    bit_depth = importlib.import_module("mpips.processing.bit_depth")
    values = np.array([0.0, 0.5, 1.0], dtype=np.float32)

    np.testing.assert_array_equal(
        bit_depth.scale_unit_to_dtype(values, np.array([0], dtype=np.uint8)),
        np.array([0, 127, 255], dtype=np.uint8),
    )
    np.testing.assert_array_equal(
        bit_depth.scale_unit_to_dtype(values, np.array([0], dtype=np.uint16)),
        np.array([0, 32767, 65535], dtype=np.uint16),
    )
    np.testing.assert_array_equal(
        bit_depth.scale_unit_to_dtype(values, np.array([10.0, 20.0], dtype=np.float32)),
        np.array([10.0, 15.0, 20.0], dtype=np.float32),
    )


def test_grayscale_any_depth_preserves_channels_and_values() -> None:
    bit_depth = importlib.import_module("mpips.processing.bit_depth")
    gray = np.array([[1, 2]], dtype=np.uint16)
    bgr = np.array(
        [[[0, 0, 255], [255, 0, 0]], [[0, 255, 0], [10, 20, 30]]],
        dtype=np.uint8,
    )
    bgra = np.concatenate([bgr, np.full((2, 2, 1), 77, dtype=np.uint8)], axis=2)

    assert bit_depth.grayscale_any_depth(gray) is gray
    np.testing.assert_array_equal(
        bit_depth.grayscale_any_depth(bgr), cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    )
    np.testing.assert_array_equal(
        bit_depth.grayscale_any_depth(bgra),
        cv2.cvtColor(bgra, cv2.COLOR_BGRA2GRAY),
    )

    with pytest.raises(ValueError, match="^Unsupported number of channels: 2$"):
        bit_depth.grayscale_any_depth(np.zeros((2, 2, 2), dtype=np.uint8))


def test_canonical_and_legacy_symbols_are_identical() -> None:
    canonical = importlib.import_module("mpips.processing.bit_depth")
    legacy = importlib.import_module("mpips.engine.nodes.bit_depth")

    for name in HELPER_NAMES:
        assert getattr(legacy, name) is getattr(canonical, name)
        assert getattr(canonical, name).__module__ == "mpips.processing.bit_depth"


def test_active_consumers_resolve_canonical_helpers() -> None:
    canonical = importlib.import_module("mpips.processing.bit_depth")
    modules = [
        importlib.import_module("mpips.iqa.metrics"),
        importlib.import_module("mpips.engine.nodes.adjustments"),
        importlib.import_module("mpips.engine.nodes.composite"),
        importlib.import_module("mpips.engine.nodes.filtering"),
        importlib.import_module("mpips.engine.nodes.scientific"),
    ]

    for module in modules:
        for name in dir(module):
            if name in HELPER_NAMES:
                assert getattr(module, name) is getattr(canonical, name)


def test_processing_exports_canonical_helpers() -> None:
    processing = importlib.import_module("mpips.processing")
    canonical = importlib.import_module("mpips.processing.bit_depth")

    for name in HELPER_NAMES:
        assert getattr(processing, name) is getattr(canonical, name)
        assert name in processing.__all__


def test_processing_bit_depth_import_is_engine_free() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.processing
        import mpips.processing.bit_depth

        forbidden = {
            "mpips.engine",
            "mpips.workflows",
            "mpips.api",
            "mpips.worker",
            "fastapi",
            "celery",
            "boto3",
            "torch",
            "matplotlib",
            "PIL",
        }
        loaded = sorted(
            name
            for name in sys.modules
            if name in forbidden
            or any(name.startswith(item + ".") for item in forbidden)
        )
        assert not loaded, loaded
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
