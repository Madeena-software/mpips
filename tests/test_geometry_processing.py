"""Regression tests for canonical crop and detector rotation."""

import subprocess
import sys
import textwrap
from typing import Any, cast

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
            "mpips.engine.imager_pipeline.complete_pipeline",
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


def test_trx_zero_crop_rotates_counterclockwise() -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(12, dtype=np.uint8).reshape(3, 4)

    result = crop_and_rotate(image, "TRX")

    np.testing.assert_array_equal(
        result,
        np.array(
            [[3, 7, 11], [2, 6, 10], [1, 5, 9], [0, 4, 8]],
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

    np.testing.assert_array_equal(result, np.array([[8, 13], [7, 12], [6, 11]]))
    assert result.shape == (3, 2)
    assert result.dtype == np.uint16


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
def test_geometry_preserves_supported_integer_dtype(dtype: type[np.generic]) -> None:
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(12, dtype=dtype).reshape(3, 4)

    result = crop_and_rotate(image, "TRX")

    assert result.dtype == image.dtype


def test_workflow_crop_and_rotate_uses_config_without_mutating_engine() -> None:
    from mpips.engine.imager_pipeline import complete_pipeline as engine
    from mpips.pipelines.config import ImagerPipelineConfig
    from mpips.processing.geometry import crop_and_rotate
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
    before = engine.CONFIG.copy()

    result = workflow_crop(image, "TRX", config)
    expected = crop_and_rotate(
        image,
        "TRX",
        crop_top=config.crop_top,
        crop_bottom=config.crop_bottom,
        crop_left=config.crop_left,
        crop_right=config.crop_right,
    )

    np.testing.assert_array_equal(result, expected)
    assert engine.CONFIG == before


def test_legacy_crop_adapter_matches_canonical_processing() -> None:
    from mpips.engine.imager_pipeline import complete_pipeline as engine
    from mpips.pipelines.config import ImagerPipelineConfig
    from mpips.processing.geometry import crop_and_rotate

    image = np.arange(20, dtype=np.uint16).reshape(4, 5)
    config = ImagerPipelineConfig(
        crop_top=1,
        crop_bottom=1,
        crop_left=1,
        crop_right=1,
    )
    keys = ("CROP_TOP", "CROP_BOTTOM", "CROP_LEFT", "CROP_RIGHT")
    before = {key: engine.CONFIG[key] for key in keys}
    engine.CONFIG.update(
        {
            "CROP_TOP": config.crop_top,
            "CROP_BOTTOM": config.crop_bottom,
            "CROP_LEFT": config.crop_left,
            "CROP_RIGHT": config.crop_right,
        }
    )

    try:
        legacy_crop = cast(Any, engine.crop_and_rotate_by_detector)
        result = legacy_crop(image, "TRX")
    finally:
        engine.CONFIG.update(before)

    expected = crop_and_rotate(
        image,
        "TRX",
        crop_top=config.crop_top,
        crop_bottom=config.crop_bottom,
        crop_left=config.crop_left,
        crop_right=config.crop_right,
    )
    np.testing.assert_array_equal(result, expected)
