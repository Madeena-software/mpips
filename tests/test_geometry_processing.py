"""Regression tests for canonical crop and detector rotation."""

import subprocess
import sys
import textwrap

import numpy as np
import pytest


def test_geometry_import_is_processing_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.geometry import crop_and_rotate

        assert callable(crop_and_rotate)
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


def test_bed_zero_crop_returns_exact_input() -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(12, dtype=np.uint16).reshape(3, 4)

    result = crop_and_rotate(image, "BED")

    np.testing.assert_array_equal(result, image)
    assert result.shape == image.shape
    assert result.dtype == image.dtype


def test_bed_nonzero_crop_preserves_expected_pixels() -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(20, dtype=np.uint16).reshape(4, 5)

    result = crop_and_rotate(
        image,
        "BED",
        crop_top=1,
        crop_bottom=1,
        crop_left=1,
        crop_right=1,
    )

    np.testing.assert_array_equal(result, np.array([[6, 7, 8], [11, 12, 13]]))
    assert result.shape == (2, 3)
    assert result.dtype == np.uint16


def test_trx_zero_crop_rotates_clockwise() -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(12, dtype=np.uint8).reshape(3, 4)

    result = crop_and_rotate(image, "TRX")

    np.testing.assert_array_equal(
        result,
        np.array(
            [[8, 4, 0], [9, 5, 1], [10, 6, 2], [11, 7, 3]],
            dtype=np.uint8,
        ),
    )
    assert result.shape == (4, 3)
    assert result.dtype == np.uint8


def test_trx_nonzero_crop_precedes_rotation() -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(20, dtype=np.uint16).reshape(4, 5)

    result = crop_and_rotate(
        image,
        "TRX",
        crop_top=1,
        crop_bottom=1,
        crop_left=1,
        crop_right=1,
    )

    np.testing.assert_array_equal(result, np.array([[11, 6], [12, 7], [13, 8]]))
    assert result.shape == (3, 2)
    assert result.dtype == np.uint16


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
def test_geometry_preserves_supported_integer_dtype(dtype: type[np.generic]) -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(12, dtype=dtype).reshape(3, 4)

    result = crop_and_rotate(image, "TRX")

    assert result.dtype == image.dtype


def test_workflow_crop_and_rotate_uses_config() -> None:
    from mpips.pipelines.config import ImagerPipelineConfig
    from mpips.workflows.imager_pipeline.pipeline import (
        crop_and_rotate as workflow_crop,
    )

    image = np.arange(20, dtype=np.uint16).reshape(4, 5)
    config = ImagerPipelineConfig(
        crop_top=1,
        crop_bottom=1,
        crop_left=1,
        crop_right=1,
    )
    result = workflow_crop(image, "TRX", config)
    np.testing.assert_array_equal(result, np.array([[11, 6], [12, 7], [13, 8]]))
    assert result.shape == (3, 2)
    assert result.dtype == np.uint16
