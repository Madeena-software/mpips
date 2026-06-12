import cv2
import numpy as np
from typing import Dict, Any
from image_engine.nodes.base import BaseNode


class GrayscaleNode(BaseNode):
    """Converts multi-channel RGB/RGBA images into single-channel luminance arrays."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("GrayscaleNode requires 'input_image' input.")

        if len(image.shape) == 2:
            # Already grayscale
            return {"output_image": image}

        channels = image.shape[2]
        if channels == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif channels == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            raise ValueError(
                f"Unsupported number of channels for GrayscaleNode: {channels}"
            )

        return {"output_image": gray}


class BrightnessContrastNode(BaseNode):
    """Adjusts brightness and contrast using linear scaling and clipping."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("BrightnessContrastNode requires 'input_image' input.")

        alpha = float(params.get("alpha", 1.0))
        beta = float(params.get("beta", 0.0))

        adjusted = np.clip(image.astype(float) * alpha + beta, 0, 255).astype(np.uint8)
        return {"output_image": adjusted}


class ThresholdingNode(BaseNode):
    """Converts image to binary using simple threshold value or Otsu's thresholding."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("ThresholdingNode requires 'input_image' input.")

        # Convert to grayscale first if multi-channel
        if len(image.shape) == 3:
            channels = image.shape[2]
            if channels == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif channels == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                raise ValueError(f"Unsupported channels: {channels}")
        else:
            gray = image

        threshold_value = int(params.get("threshold_value", 127))
        algo_type = params.get("type", "binary")

        if algo_type == "otsu":
            _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            _, th = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

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

        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in range(256)]).astype(
            "uint8"
        )
        corrected = cv2.LUT(image, table)
        return {"output_image": corrected}
