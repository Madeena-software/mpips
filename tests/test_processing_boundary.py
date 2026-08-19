import subprocess
import sys
import textwrap
from typing import Any, cast

import cv2
import numpy as np

import mpips.processing as processing
from mpips.workflows.imager_pipeline import pipeline as workflow_pipeline

PUBLIC_OPERATIONS = (
    "apply_calibration_remap",
    "crop_and_rotate",
    "denoise_wavelet",
    "flat_field_correction",
    "auto_threshold",
    "apply_threshold_separation",
    "imagej_stretch",
    "imagej_equalize",
    "apply_clahe",
    "hybrid_median_filter",
    "apply_median_filter",
    "invert_image",
)


def test_processing_exports_only_reusable_array_operations() -> None:
    assert processing.__all__ == list(PUBLIC_OPERATIONS)
    assert all(callable(getattr(processing, name)) for name in PUBLIC_OPERATIONS)


def test_workflow_operations_are_compatibility_aliases() -> None:
    for name in PUBLIC_OPERATIONS:
        if name in {"crop_and_rotate", "invert_image"}:
            continue
        assert getattr(workflow_pipeline, name) is getattr(processing, name)


def test_processing_import_is_lazy_and_service_safe() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.processing

        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "httpx",
            "mpips.api",
            "mpips.engine.imager_pipeline.complete_pipeline",
            "mpips.worker",
            "mpips.workflows",
        }
        loaded = forbidden.intersection(sys.modules)
        assert not loaded, sorted(loaded)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_processing_remap_matches_existing_array_transform() -> None:
    image = np.arange(16, dtype=np.uint16).reshape(4, 4)
    y_values, x_values = np.indices((3, 5), dtype=np.float32)
    expected = cv2.remap(
        image,
        x_values,
        y_values,
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    np.testing.assert_array_equal(
        processing.apply_calibration_remap(image, x_values, y_values), expected
    )


def test_processing_delegates_flat_field_correction_to_canonical_engine() -> None:
    from mpips.engine.imager_pipeline import complete_pipeline as legacy_engine

    raw = np.array([[10, 20], [30, 40]], dtype=np.float32)
    dark = np.zeros_like(raw)
    flat = np.full_like(raw, 100)

    legacy_flat_field = cast(Any, legacy_engine.flat_field_correction)
    legacy_result = legacy_flat_field(raw, dark, flat)
    np.testing.assert_array_equal(
        processing.flat_field_correction(raw, dark, flat), legacy_result
    )


def test_processing_delegates_imagej_stretch_to_canonical_engine() -> None:
    from mpips.processing.imagej import ImageJReplicator

    image = np.array([[0, 0, 1, 2], [2, 2, 3, 3]], dtype=np.uint8)

    np.testing.assert_array_equal(
        processing.imagej_stretch(image, 0.0),
        ImageJReplicator.enhance_contrast(
            image,
            saturated_pixels=0.0,
            equalize=False,
            normalize=True,
        ),
    )
