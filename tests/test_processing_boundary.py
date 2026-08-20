import subprocess
import sys
import textwrap

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
    "detect_threshold",
    "dtype_limits",
    "clip_to_input_dtype",
    "normalize_to_uint8",
    "scale_unit_to_dtype",
    "grayscale_any_depth",
)


def test_processing_exports_only_reusable_array_operations() -> None:
    assert processing.__all__ == list(PUBLIC_OPERATIONS)
    assert all(callable(getattr(processing, name)) for name in PUBLIC_OPERATIONS)


def test_workflow_operations_are_compatibility_aliases() -> None:
    for name in PUBLIC_OPERATIONS:
        if name in {
            "crop_and_rotate",
            "invert_image",
            "detect_threshold",
            "dtype_limits",
            "clip_to_input_dtype",
            "normalize_to_uint8",
            "scale_unit_to_dtype",
            "grayscale_any_depth",
        }:
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
            "mpips.engine",
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


def test_public_processing_calls_do_not_load_engine() -> None:
    script = textwrap.dedent("""
        import sys

        import numpy as np

        from mpips.processing import (
            apply_median_filter,
            auto_threshold,
            denoise_wavelet,
        )

        image = np.arange(64, dtype=np.float32).reshape(8, 8) / 63.0
        denoise_wavelet(image, "sym4", 3, "BayesShrink", "soft")
        auto_threshold(image)
        apply_median_filter(
            (image * 65535).astype(np.uint16), "standard", 1
        )

        forbidden = {
            "boto3",
            "celery",
            "cupy",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.worker",
            "mpips.workflows",
        }
        loaded = sorted(
            name
            for name in sys.modules
            if name in forbidden
            or any(
                name.startswith(item + ".")
                for item in forbidden
            )
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


def test_processing_flat_field_correction_has_canonical_behavior() -> None:
    raw = np.array([[10, 20], [30, 40]], dtype=np.float32)
    dark = np.zeros_like(raw)
    flat = np.full_like(raw, 100)

    np.testing.assert_allclose(processing.flat_field_correction(raw, dark, flat), raw)


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
