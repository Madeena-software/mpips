import hashlib
import importlib
import subprocess
import sys
import textwrap
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

import mpips.processing as processing


def _imagej_class() -> type[Any]:
    from mpips.processing.imagej import ImageJReplicator

    return ImageJReplicator


def test_imagej_replicator_is_canonical_in_processing() -> None:
    canonical = _imagej_class()

    assert canonical.__module__ == "mpips.processing.imagej"


def test_legacy_imagej_module_is_retired() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("mpips.engine.imager_pipeline.imagej_replicator")


def test_processing_imagej_wrappers_do_not_import_legacy_module() -> None:
    _imagej_class()
    image = np.array([[0, 0, 1, 2], [2, 2, 3, 3]], dtype=np.uint8)

    with patch.dict(
        sys.modules,
        {"mpips.engine.imager_pipeline.imagej_replicator": None},
    ):
        processing.imagej_stretch(image, 0.0)
        processing.imagej_equalize(image)
        processing.apply_clahe(
            np.arange(16, dtype=np.uint16).reshape(4, 4),
            3,
            256,
            0.6,
        )
        processing.hybrid_median_filter(image, radius=1)


def test_canonical_imagej_import_is_service_runtime_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.imagej import ImageJReplicator

        assert ImageJReplicator.__module__ == "mpips.processing.imagej"
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
        assert not forbidden.intersection(sys.modules)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_imagej_wrappers_preserve_baseline_outputs() -> None:
    image = np.array([[0, 0, 1, 2], [2, 2, 3, 3]], dtype=np.uint8)
    equalized = processing.imagej_equalize(image)
    stretched = processing.imagej_stretch(image, 0.0)
    assert equalized.shape == image.shape
    assert equalized.dtype == np.uint8
    assert stretched.shape == image.shape
    assert stretched.dtype == np.uint8
    np.testing.assert_array_equal(
        equalized,
        np.array([[0, 0, 63, 135], [135, 135, 218, 218]], dtype=np.uint8),
    )
    np.testing.assert_array_equal(
        stretched,
        np.array([[0, 0, 85, 170], [170, 170, 255, 255]], dtype=np.uint8),
    )

    clahe_input = np.arange(64, dtype=np.uint16).reshape(8, 8) * 1000
    precise = processing.apply_clahe(
        clahe_input,
        5,
        256,
        0.6,
        fast=False,
        composite=True,
    )
    assert precise.shape == clahe_input.shape
    assert precise.dtype == np.uint16
    assert 0 <= precise.min() <= precise.max() <= 65535
    assert hashlib.sha256(precise.tobytes()).hexdigest() == (
        "5d94b2940b94f2dfbcfe41f130edef7bebfa59fa5a050e7cdbb9bbfbe140dcf6"
    )
    fast = processing.apply_clahe(
        clahe_input,
        5,
        256,
        0.6,
        fast=True,
        composite=True,
    )
    assert fast.shape == clahe_input.shape
    assert fast.dtype == np.uint16
    assert 0 <= fast.min() <= fast.max() <= 65535
    assert hashlib.sha256(fast.tobytes()).hexdigest() == (
        "1c4bb383c6e5af18532aff7f0c68e094fdb81c8dc545493758d11e2de8b49ea2"
    )

    median_input = np.array(
        [
            [9, 2, 7, 4, 6],
            [3, 8, 1, 5, 0],
            [6, 4, 9, 2, 7],
            [5, 1, 8, 3, 6],
            [0, 7, 2, 9, 4],
        ],
        dtype=np.uint16,
    )
    median = processing.hybrid_median_filter(median_input, radius=2)
    assert median.shape == median_input.shape
    assert median.dtype == np.uint16
    np.testing.assert_array_equal(
        median,
        np.array(
            [
                [9, 2, 7, 4, 6],
                [3, 7, 4, 5, 4],
                [6, 4, 6, 3, 5],
                [5, 4, 7, 4, 6],
                [3, 7, 2, 9, 4],
            ],
            dtype=np.uint16,
        ),
    )
