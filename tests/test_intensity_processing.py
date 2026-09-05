"""Regression tests for canonical image intensity operations."""

import subprocess
import sys
import textwrap

import numpy as np


def test_inversion_import_is_processing_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.intensity import invert_image

        assert callable(invert_image)
        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.pipelines",
            "mpips.worker",
            "mpips.workflows",
        }
        assert forbidden.isdisjoint(sys.modules)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_uint8_inversion_matches_exact_historical_pixels() -> None:
    from mpips.processing import invert_image

    image = np.array([[0, 1, 127], [128, 254, 255]], dtype=np.uint8)

    result = invert_image(image)

    np.testing.assert_array_equal(
        result,
        np.array([[255, 254, 128], [127, 1, 0]], dtype=np.uint8),
    )
    assert result.shape == image.shape
    assert result.dtype == image.dtype


def test_uint16_inversion_matches_exact_historical_pixels() -> None:
    from mpips.processing import invert_image

    image = np.array([[0, 1, 32768], [32767, 65534, 65535]], dtype=np.uint16)

    result = invert_image(image)

    np.testing.assert_array_equal(
        result,
        np.array([[65535, 65534, 32767], [32768, 1, 0]], dtype=np.uint16),
    )
    assert result.shape == image.shape
    assert result.dtype == image.dtype


def test_float32_inversion_matches_exact_subtraction() -> None:
    from mpips.processing import invert_image

    image = np.array([[0.0, 0.125], [0.5, 1.0]], dtype=np.float32)

    result = invert_image(image)

    np.testing.assert_array_equal(result, 1.0 - image)
    assert result.shape == image.shape
    assert result.dtype == np.float32
