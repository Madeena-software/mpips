import importlib
import subprocess
import sys
import textwrap

import cv2
import numpy as np
import pytest

from mpips.dag.nodes.adjustments import (
    BrightnessContrastNode,
    CLAHENode,
    GammaCorrectionNode,
    GrayscaleNode,
    ThresholdingNode,
)
from mpips.dag.nodes.base import BaseNode
from mpips.dag.nodes.calibration import CameraCalibrationWarpNode
from mpips.dag.nodes.composite import MergeNode
from mpips.dag.nodes.filtering import (
    CannyNode,
    GaussianBlurNode,
    MedianBlurNode,
    SobelNode,
)
from mpips.dag.nodes.geometry import CropNode, FlipNode, ResizeNode, RotateNode
from mpips.dag.nodes.iqa import (
    BrisqueNode,
    ContrastImprovementIndexNode,
    EnhancementMeasureNode,
    EntropyNode,
)


def test_base_node_execute_preserves_exact_error_contract() -> None:
    with pytest.raises(NotImplementedError) as exc_info:
        BaseNode().execute({}, {})

    assert str(exc_info.value) == "Subclasses must implement the execute method."


def test_geometry_defaults_and_resize_interpolation_mapping() -> None:
    image = np.arange(12, dtype=np.uint8).reshape(3, 4)
    node = ResizeNode()

    assert node.execute({"input_image": image}, {})["output_image"].shape == (
        600,
        800,
    )

    interpolation_flags = {
        "NEAREST": cv2.INTER_NEAREST,
        "BILINEAR": cv2.INTER_LINEAR,
        "BICUBIC": cv2.INTER_CUBIC,
        "LANCZOS4": cv2.INTER_LANCZOS4,
        "unknown": cv2.INTER_LINEAR,
    }
    for interpolation, flag in interpolation_flags.items():
        result = node.execute(
            {"input_image": image},
            {"width": 5, "height": 4, "interpolation": interpolation},
        )["output_image"]
        expected = cv2.resize(image, (5, 4), interpolation=flag)
        np.testing.assert_array_equal(result, expected)


def test_crop_clips_coordinates_and_keeps_minimum_crop_size() -> None:
    image = np.arange(20, dtype=np.uint8).reshape(4, 5)
    node = CropNode()

    clipped = node.execute(
        {"input_image": image},
        {"x_start": 3, "y_start": 2, "width": 20, "height": 20},
    )["output_image"]
    np.testing.assert_array_equal(clipped, image[2:, 3:])

    minimum = node.execute(
        {"input_image": image},
        {"x_start": 100, "y_start": 100, "width": 0, "height": 0},
    )["output_image"]
    np.testing.assert_array_equal(minimum, image[-1:, -1:])


def test_rotate_preserves_historical_expanded_and_fixed_canvas_sizes() -> None:
    image = np.arange(6, dtype=np.uint8).reshape(2, 3)
    node = RotateNode()

    expanded = node.execute({"input_image": image}, {"angle": 90.0, "expand": True})[
        "output_image"
    ]
    fixed = node.execute({"input_image": image}, {"angle": 90.0, "expand": False})[
        "output_image"
    ]

    assert expanded.shape == (3, 2)
    assert fixed.shape == image.shape


def test_flip_handles_horizontal_vertical_both_and_unknown_directions() -> None:
    image = np.arange(12, dtype=np.uint8).reshape(3, 4)
    node = FlipNode()

    np.testing.assert_array_equal(
        node.execute({"input_image": image}, {"direction": "horizontal"})[
            "output_image"
        ],
        np.fliplr(image),
    )
    np.testing.assert_array_equal(
        node.execute({"input_image": image}, {"direction": "vertical"})["output_image"],
        np.flipud(image),
    )
    expected_both = np.flip(image)
    np.testing.assert_array_equal(
        node.execute({"input_image": image}, {"direction": "both"})["output_image"],
        expected_both,
    )
    np.testing.assert_array_equal(
        node.execute({"input_image": image}, {"direction": "diagonal"})["output_image"],
        expected_both,
    )


def test_adjustment_nodes_preserve_grayscale_and_numeric_contracts() -> None:
    bgr = np.array([[[0, 0, 255], [255, 0, 0]]], dtype=np.uint8)
    bgra = np.concatenate([bgr, np.full((1, 2, 1), 77, dtype=np.uint8)], axis=2)
    np.testing.assert_array_equal(
        GrayscaleNode().execute({"input_image": bgr}, {})["output_image"],
        cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY),
    )
    np.testing.assert_array_equal(
        GrayscaleNode().execute({"input_image": bgra}, {})["output_image"],
        cv2.cvtColor(bgra, cv2.COLOR_BGRA2GRAY),
    )

    uint8 = np.array([[10, 250]], dtype=np.uint8)
    adjusted_uint8 = BrightnessContrastNode().execute(
        {"input_image": uint8}, {"alpha": 2.0, "beta": 10.0}
    )["output_image"]
    np.testing.assert_array_equal(adjusted_uint8, np.array([[30, 255]], dtype=np.uint8))

    uint16 = np.array([[1000]], dtype=np.uint16)
    adjusted_uint16 = BrightnessContrastNode().execute(
        {"input_image": uint16}, {"alpha": 2.0, "beta": 500.0}
    )["output_image"]
    assert adjusted_uint16.dtype == np.uint16
    np.testing.assert_array_equal(adjusted_uint16, np.array([[2500]], dtype=np.uint16))

    float_image = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    adjusted_float = BrightnessContrastNode().execute(
        {"input_image": float_image}, {"alpha": 2.0, "beta": -0.25}
    )["output_image"]
    assert adjusted_float.dtype == np.float32
    np.testing.assert_allclose(adjusted_float, [[-0.25, 0.75, 1.75]])


def test_thresholding_preserves_binary_otsu_and_float_paths() -> None:
    binary = np.array([[0, 100, 200, 255]], dtype=np.uint8)
    binary_result = ThresholdingNode().execute(
        {"input_image": binary}, {"threshold_value": 100, "type": "binary"}
    )["output_image"]
    np.testing.assert_array_equal(binary_result, [[0, 0, 255, 255]])

    otsu_uint8 = np.array([[0, 0, 255, 255]], dtype=np.uint8)
    otsu_result = ThresholdingNode().execute(
        {"input_image": otsu_uint8}, {"type": "otsu"}
    )["output_image"]
    np.testing.assert_array_equal(otsu_result, [[0, 0, 255, 255]])

    otsu_uint16 = np.array([[0, 0, 65535, 65535]], dtype=np.uint16)
    otsu_uint16_result = ThresholdingNode().execute(
        {"input_image": otsu_uint16}, {"type": "otsu"}
    )["output_image"]
    assert otsu_uint16_result.dtype == np.uint16
    np.testing.assert_array_equal(otsu_uint16_result, [[0, 0, 65535, 65535]])

    otsu_float = np.array([[0.0, 0.0, 1.0, 1.0]], dtype=np.float32)
    otsu_float_result = ThresholdingNode().execute(
        {"input_image": otsu_float}, {"type": "otsu"}
    )["output_image"]
    assert otsu_float_result.dtype == np.float32
    np.testing.assert_array_equal(otsu_float_result, [[0.0, 0.0, 1.0, 1.0]])


def test_gamma_defaults_non_default_and_exact_invalid_value_error() -> None:
    image = np.array([[0, 128, 255]], dtype=np.uint8)
    default = GammaCorrectionNode().execute({"input_image": image}, {})["output_image"]
    np.testing.assert_array_equal(default, image)

    float_image = np.array([[0.0, 0.25, 1.0]], dtype=np.float32)
    corrected = GammaCorrectionNode().execute(
        {"input_image": float_image}, {"gamma": 2.0}
    )["output_image"]
    assert corrected.dtype == np.float32
    np.testing.assert_allclose(corrected, [[0.0, 0.5, 1.0]], atol=1e-6)

    with pytest.raises(ValueError) as exc_info:
        GammaCorrectionNode().execute({"input_image": image}, {"gamma": 0})
    assert str(exc_info.value) == "Gamma parameter must be strictly positive."


def test_clahe_preserves_gray_color_alpha_high_depth_and_errors() -> None:
    gray = np.arange(64, dtype=np.uint8).reshape(8, 8)
    gray_result = CLAHENode().execute({"input_image": gray}, {})["output_image"]
    assert gray_result.shape == gray.shape
    assert gray_result.dtype == gray.dtype

    bgr = np.stack([gray, np.flipud(gray), np.fliplr(gray)], axis=2)
    bgr_result = CLAHENode().execute({"input_image": bgr}, {})["output_image"]
    assert bgr_result.shape == bgr.shape
    assert bgr_result.dtype == bgr.dtype

    alpha = np.full((8, 8, 1), 123, dtype=np.uint8)
    bgra = np.concatenate([bgr, alpha], axis=2)
    bgra_result = CLAHENode().execute({"input_image": bgra}, {})["output_image"]
    np.testing.assert_array_equal(bgra_result[:, :, 3], alpha[:, :, 0])

    high_depth = (gray.astype(np.uint16) * 1024).astype(np.uint16)
    high_depth_result = CLAHENode().execute({"input_image": high_depth}, {})[
        "output_image"
    ]
    assert high_depth_result.shape == high_depth.shape
    assert high_depth_result.dtype == np.uint16

    with pytest.raises(ValueError) as exc_info:
        CLAHENode().execute({"input_image": np.zeros((8, 8, 2), dtype=np.uint8)}, {})
    assert str(exc_info.value) == "Unsupported channel size in CLAHE: 2"

    with pytest.raises(ValueError) as exc_info:
        CLAHENode().execute({"input_image": np.zeros(8, dtype=np.uint8)}, {})
    assert str(exc_info.value) == "Invalid image dimensions."


def test_filtering_nodes_preserve_kernel_canny_and_sobel_contracts() -> None:
    image = np.zeros((9, 9), dtype=np.uint8)
    image[4, 4] = 255
    for node, name in ((GaussianBlurNode(), "gaussian"), (MedianBlurNode(), "median")):
        for requested, effective in ((3, 3), (4, 5), (0, 5), (-2, 5)):
            params = {"kernel_size": requested}
            result = node.execute({"input_image": image}, params)["output_image"]
            if name == "gaussian":
                expected = cv2.GaussianBlur(image, (effective, effective), 1.0)
            else:
                expected = cv2.medianBlur(image, effective)
            np.testing.assert_array_equal(result, expected)

    high_depth = np.zeros((10, 10), dtype=np.uint16)
    high_depth[:, 5:] = np.iinfo(np.uint16).max
    canny = CannyNode().execute({"input_image": high_depth}, {})["output_image"]
    normalized = np.zeros_like(high_depth, dtype=np.uint8)
    normalized[:, 5:] = 255
    np.testing.assert_array_equal(canny, cv2.Canny(normalized, 50.0, 150.0))
    assert canny.dtype == np.uint8

    expected_sobel = np.abs(cv2.Sobel(high_depth, cv2.CV_64F, 1, 0, ksize=3))
    expected_sobel = np.clip(expected_sobel, 0, np.iinfo(np.uint16).max).astype(
        np.uint16
    )
    sobel = SobelNode().execute({"input_image": high_depth}, {})["output_image"]
    np.testing.assert_array_equal(sobel, expected_sobel)
    assert sobel.dtype == np.uint16

    invalid_ksize = SobelNode().execute(
        {"input_image": high_depth}, {"dx": 1, "dy": 0, "ksize": 9}
    )["output_image"]
    np.testing.assert_array_equal(invalid_ksize, expected_sobel)


def test_iqa_wrappers_preserve_keys_rounding_fallback_and_errors() -> None:
    image = np.arange(256, dtype=np.uint8).reshape(16, 16)
    reference = np.flipud(image)

    assert EntropyNode().execute({"input_image": image}, {}) == {"entropy_score": 8.0}
    assert EnhancementMeasureNode().execute({"input_image": image}, {}) == {
        "eme_score": 9.0201
    }
    assert BrisqueNode().execute({"input_image": image}, {}) == {
        "brisque_score": 87.5396
    }
    assert ContrastImprovementIndexNode().execute(
        {"input_image": image, "reference_image": reference}, {}
    ) == {"cii_score": 1.0}
    assert ContrastImprovementIndexNode().execute({"input_image": image}, {}) == {
        "cii_score": 1.0
    }

    cases = [
        (EntropyNode(), "EntropyNode requires 'input_image' input."),
        (
            EnhancementMeasureNode(),
            "EnhancementMeasureNode requires 'input_image' input.",
        ),
        (BrisqueNode(), "BrisqueNode requires 'input_image' input."),
        (
            ContrastImprovementIndexNode(),
            "ContrastImprovementIndexNode requires 'input_image' input.",
        ),
    ]
    for node, message in cases:
        with pytest.raises(ValueError) as exc_info:
            node.execute({}, {})
        assert str(exc_info.value) == message


def test_calibration_wrapper_preserves_precedence_identity_and_map_conversion() -> None:
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    identity_x, identity_y = np.meshgrid(
        np.arange(4, dtype=np.float64), np.arange(4, dtype=np.float64)
    )
    zero_x = np.zeros((4, 4), dtype=np.float64)
    zero_y = np.zeros((4, 4), dtype=np.float64)

    input_precedence = CameraCalibrationWarpNode().execute(
        {"input_image": image, "map_x": identity_x, "map_y": identity_y},
        {"map_x": zero_x.tolist(), "map_y": zero_y.tolist()},
    )["output_image"]
    np.testing.assert_array_equal(input_precedence, image)

    supplied = CameraCalibrationWarpNode().execute(
        {"input_image": image}, {"map_x": identity_x, "map_y": identity_y}
    )["output_image"]
    np.testing.assert_array_equal(supplied, image)

    identity_fallback = CameraCalibrationWarpNode().execute(
        {"input_image": image, "map_x": zero_x}, {}
    )["output_image"]
    np.testing.assert_array_equal(identity_fallback, image)

    with pytest.raises(ValueError) as exc_info:
        CameraCalibrationWarpNode().execute({}, {})
    assert str(exc_info.value) == "CameraCalibrationWarpNode requires 'input_image'."


def test_merge_preserves_fan_in_weight_resize_normalization_and_errors() -> None:
    first = np.array([[10, 20], [30, 40]], dtype=np.uint8)
    second = np.full((2, 2), 20, dtype=np.uint8)
    node = MergeNode()
    assert node.MAX_INPUTS == 10

    one = node.execute({"input_1": first}, {})["output_image"]
    np.testing.assert_array_equal(one, first)

    weighted = node.execute(
        {"input_1": first, "input_2": second},
        {"input_1_weight": 1.0, "input_2_weight": 3.0},
    )["output_image"]
    np.testing.assert_array_equal(
        weighted, np.array([[17, 20], [22, 25]], dtype=np.uint8)
    )

    unnormalized = node.execute(
        {"input_1": np.ones((2, 2), dtype=np.uint8), "input_2": second},
        {"normalize": False},
    )["output_image"]
    np.testing.assert_array_equal(unnormalized, np.full((2, 2), 21, dtype=np.uint8))

    resized = node.execute(
        {
            "input_1": np.full((2, 2), 10, dtype=np.uint8),
            "input_2": np.array([[20]], dtype=np.uint8),
        },
        {},
    )["output_image"]
    np.testing.assert_array_equal(resized, np.full((2, 2), 15, dtype=np.uint8))

    with pytest.raises(ValueError) as exc_info:
        node.execute({}, {})
    assert str(exc_info.value) == "MergeNode requires at least one wired input."

    with pytest.raises(ValueError) as exc_info:
        node.execute({"input_1": first}, {"input_1_weight": 0.0})
    assert (
        str(exc_info.value)
        == "Sum of MergeNode input weights must be positive when normalize is enabled."
    )


def test_registry_entries_resolve_exact_canonical_classes() -> None:
    registry = importlib.import_module("mpips.dag.registry")
    canonical = {
        "resize": ResizeNode,
        "crop": CropNode,
        "rotate": RotateNode,
        "flip": FlipNode,
        "grayscale": GrayscaleNode,
        "brightness_contrast": BrightnessContrastNode,
        "thresholding": ThresholdingNode,
        "gamma_correction": GammaCorrectionNode,
        "clahe": CLAHENode,
        "gaussian_blur": GaussianBlurNode,
        "median_blur": MedianBlurNode,
        "canny": CannyNode,
        "sobel": SobelNode,
        "cii": ContrastImprovementIndexNode,
        "ent": EntropyNode,
        "eme": EnhancementMeasureNode,
        "brisque": BrisqueNode,
        "camera_calibration_warp": CameraCalibrationWarpNode,
        "merge": MergeNode,
    }
    for node_id, node_class in canonical.items():
        assert registry.NODE_CLASSES[node_id] is node_class
        assert registry.get_node_class(node_id) is node_class


def test_dag_and_node_package_imports_remain_lightweight() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.dag
        import mpips.dag.nodes

        forbidden = {
            "mpips.engine",
            "mpips.api",
            "mpips.worker",
            "fastapi",
            "celery",
            "boto3",
            "cv2",
            "numpy",
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


def test_canonical_node_modules_do_not_import_engine() -> None:
    script = textwrap.dedent("""
        import importlib
        import sys

        for module_name in (
            "mpips.dag.nodes.base",
            "mpips.dag.nodes.geometry",
            "mpips.dag.nodes.adjustments",
            "mpips.dag.nodes.filtering",
            "mpips.dag.nodes.iqa",
            "mpips.dag.nodes.calibration",
            "mpips.dag.nodes.composite",
        ):
            importlib.import_module(module_name)

        assert not [
            name
            for name in sys.modules
            if name == "mpips.engine" or name.startswith("mpips.engine.")
        ]
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
