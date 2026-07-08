import cv2
import numpy as np
from typing import Dict, Any
from mpips.engine.nodes.base import BaseNode
from mpips.engine.nodes.bit_depth import (
    clip_to_input_dtype,
    dtype_limits,
    grayscale_any_depth,
    normalize_to_uint8,
)


class GrayscaleNode(BaseNode):
    """Converts multi-channel RGB/RGBA images into single-channel luminance arrays."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("GrayscaleNode requires 'input_image' input.")

        return {"output_image": grayscale_any_depth(image)}


class BrightnessContrastNode(BaseNode):
    """Adjusts brightness and contrast using linear scaling and clipping."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("BrightnessContrastNode requires 'input_image' input.")

        alpha = float(params.get("alpha", 1.0))
        beta = float(params.get("beta", 0.0))

        adjusted = clip_to_input_dtype(image.astype(np.float64) * alpha + beta, image)
        return {"output_image": adjusted}


class ThresholdingNode(BaseNode):
    """Converts image to binary using simple threshold value or Otsu's thresholding."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("ThresholdingNode requires 'input_image' input.")

        gray = grayscale_any_depth(image)

        threshold_value = int(params.get("threshold_value", 127))
        algo_type = params.get("type", "binary")
        _, max_val = dtype_limits(gray)

        if algo_type == "otsu":
            if gray.dtype in (np.uint8, np.uint16):
                _, th = cv2.threshold(
                    gray, 0, max_val, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
            else:
                gray_u8 = normalize_to_uint8(gray)
                _, th_u8 = cv2.threshold(
                    gray_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                th = np.where(th_u8 > 0, max_val, 0)
                th = clip_to_input_dtype(th, gray)
        else:
            _, th = cv2.threshold(gray, threshold_value, max_val, cv2.THRESH_BINARY)

        return {"output_image": th}


class GammaCorrectionNode(BaseNode):
    """Applies non-linear luminance correction using power-law transformations."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("GammaCorrectionNode requires 'input_image' input.")

        gamma = float(params.get("gamma", 1.0))
        if gamma <= 0:
            raise ValueError("Gamma parameter must be strictly positive.")

        min_val, max_val = dtype_limits(image)
        if max_val <= min_val:
            return {"output_image": image.copy()}

        inv_gamma = 1.0 / gamma
        normalized = (image.astype(np.float64) - min_val) / (max_val - min_val)
        corrected = clip_to_input_dtype(
            np.power(np.clip(normalized, 0.0, 1.0), inv_gamma) * (max_val - min_val)
            + min_val,
            image,
        )
        return {"output_image": corrected}
