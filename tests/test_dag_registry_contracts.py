from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

from mpips.dag import NODE_CLASSES as FacadeNodeClasses
from mpips.dag import get_node_class as FacadeGetNodeClass
from mpips.dag.catalog import NODE_CATALOG
from mpips.dag.nodes.base import BaseNode
from mpips.dag.nodes.io import (
    InputNode as CanonicalInputNode,
    MadeenaNpzOutputNode as CanonicalMadeenaNpzOutputNode,
    OutputNode as CanonicalOutputNode,
)
from mpips.dag.registry import (
    NODE_CLASSES as CanonicalNodeClasses,
    get_node_class as CanonicalGetNodeClass,
)
from mpips.engine.registry import (
    NODE_CLASSES,
    InputNode,
    MadeenaNpzOutputNode,
    OutputNode,
    get_node_class,
)

EXPECTED_NODE_IDS = [
    "input",
    "input_npz",
    "output",
    "output_npz",
    "resize",
    "crop",
    "rotate",
    "flip",
    "grayscale",
    "brightness_contrast",
    "thresholding",
    "gamma_correction",
    "clahe",
    "gaussian_blur",
    "median_blur",
    "canny",
    "sobel",
    "nlm_denoising",
    "homomorphic_filter",
    "wavelet_denoising",
    "flat_field_correction",
    "leveling",
    "camera_calibration",
    "camera_calibration_warp",
    "fabemd",
    "merge",
    "cii",
    "ent",
    "eme",
    "brisque",
]

EXPECTED_CLASS_NAMES = {
    "input": "InputNode",
    "input_npz": "InputNode",
    "output": "OutputNode",
    "output_npz": "MadeenaNpzOutputNode",
    "resize": "ResizeNode",
    "crop": "CropNode",
    "rotate": "RotateNode",
    "flip": "FlipNode",
    "grayscale": "GrayscaleNode",
    "brightness_contrast": "BrightnessContrastNode",
    "thresholding": "ThresholdingNode",
    "gamma_correction": "GammaCorrectionNode",
    "clahe": "CLAHENode",
    "gaussian_blur": "GaussianBlurNode",
    "median_blur": "MedianBlurNode",
    "canny": "CannyNode",
    "sobel": "SobelNode",
    "nlm_denoising": "NonLocalMeansNode",
    "homomorphic_filter": "HomomorphicFilterNode",
    "wavelet_denoising": "WaveletDenoisingNode",
    "flat_field_correction": "FlatFieldCorrectionNode",
    "leveling": "LevelingNode",
    "camera_calibration": "CameraCalibrationNode",
    "camera_calibration_warp": "CameraCalibrationWarpNode",
    "fabemd": "FABEMDNode",
    "merge": "MergeNode",
    "cii": "ContrastImprovementIndexNode",
    "ent": "EntropyNode",
    "eme": "EnhancementMeasureNode",
    "brisque": "BrisqueNode",
}


def test_baseline_registry_order_membership_and_class_names() -> None:
    assert len(NODE_CLASSES) == 30
    assert list(NODE_CLASSES) == EXPECTED_NODE_IDS
    assert set(NODE_CLASSES) == set(EXPECTED_NODE_IDS)
    assert {
        node_id: node_class.__name__ for node_id, node_class in NODE_CLASSES.items()
    } == EXPECTED_CLASS_NAMES
    assert NODE_CLASSES["input"] is NODE_CLASSES["input_npz"]
    assert all(issubclass(node_class, BaseNode) for node_class in NODE_CLASSES.values())


def test_baseline_registry_lookup_and_unknown_type_error() -> None:
    for node_id, node_class in NODE_CLASSES.items():
        assert get_node_class(node_id) is node_class

    with pytest.raises(ValueError) as exc_info:
        get_node_class("definitely_unknown")

    assert str(exc_info.value) == "Unknown node type: definitely_unknown"


def test_baseline_input_node_copies_slots_and_preserves_values() -> None:
    image = object()
    metadata = object()
    inputs: dict[str, Any] = {"output_image": image, "npz_metadata": metadata}

    result = InputNode().execute(inputs, {"ignored": True})

    assert result == inputs
    assert result is not inputs
    assert result["output_image"] is image
    assert result["npz_metadata"] is metadata
    assert InputNode().execute({}, {}) == {}


def test_baseline_output_node_uses_optional_input_image_only() -> None:
    image = object()

    assert OutputNode().execute({"input_image": image, "extra": object()}, {}) == {
        "output_image": image
    }
    assert OutputNode().execute({"extra": image}, {}) == {"output_image": None}


def test_baseline_npz_output_node_copies_all_slots_and_preserves_values() -> None:
    rawimage = object()
    metadata = object()
    inputs: dict[str, Any] = {
        "rawimage": rawimage,
        "darkimage": object(),
        "processedimage": object(),
        "npz_metadata": metadata,
        "other": object(),
    }

    result = MadeenaNpzOutputNode().execute(inputs, {})

    assert result == inputs
    assert result is not inputs
    assert result["rawimage"] is rawimage
    assert result["npz_metadata"] is metadata
    assert MadeenaNpzOutputNode().execute({}, {}) == {}


def test_canonical_registry_and_legacy_exports_preserve_identity() -> None:
    from mpips.engine.registry import (
        InputNode as LegacyInputNode,
        MadeenaNpzOutputNode as LegacyMadeenaNpzOutputNode,
        OutputNode as LegacyOutputNode,
    )

    assert CanonicalNodeClasses is NODE_CLASSES
    assert CanonicalGetNodeClass is get_node_class
    assert FacadeNodeClasses is CanonicalNodeClasses
    assert FacadeGetNodeClass is CanonicalGetNodeClass
    assert LegacyInputNode is CanonicalInputNode
    assert LegacyOutputNode is CanonicalOutputNode
    assert LegacyMadeenaNpzOutputNode is CanonicalMadeenaNpzOutputNode
    assert all(
        node_class.__module__.startswith("mpips.dag.nodes.")
        for node_class in CanonicalNodeClasses.values()
    )


def test_canonical_registry_and_catalog_have_identical_ordered_ids() -> None:
    catalog_ids = [node.id for node in NODE_CATALOG]

    assert catalog_ids == list(CanonicalNodeClasses)
    assert set(catalog_ids) == set(CanonicalNodeClasses)


def test_public_registry_access_stays_engine_free_until_requested() -> None:
    script = """
import sys

import mpips.dag

assert "mpips.engine" not in sys.modules
classes = mpips.dag.NODE_CLASSES
assert "mpips.dag.registry" in sys.modules
assert "mpips.engine" not in sys.modules
assert "mpips.engine.registry" not in sys.modules
assert classes["input"].__module__ == "mpips.dag.nodes.io"
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
