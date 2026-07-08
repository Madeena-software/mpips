import cv2
import numpy as np
from typing import Dict, Any
from mpips.engine.nodes.base import BaseNode


class ResizeNode(BaseNode):
    """Resizes an image based on width, height, and interpolation mode."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("ResizeNode requires 'input_image' input.")

        width = params.get("width", 800)
        height = params.get("height", 600)
        interpolation_str = params.get("interpolation", "BILINEAR")

        interp_map = {
            "NEAREST": cv2.INTER_NEAREST,
            "BILINEAR": cv2.INTER_LINEAR,
            "BICUBIC": cv2.INTER_CUBIC,
            "LANCZOS4": cv2.INTER_LANCZOS4,
        }

        interp = interp_map.get(interpolation_str, cv2.INTER_LINEAR)
        resized = cv2.resize(image, (width, height), interpolation=interp)
        return {"output_image": resized}


class CropNode(BaseNode):
    """Crops an image based on x_start, y_start, width, and height."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("CropNode requires 'input_image' input.")

        x_start = params.get("x_start", 0)
        y_start = params.get("y_start", 0)
        width = params.get("width", 100)
        height = params.get("height", 100)

        h, w = image.shape[:2]
        x_start = max(0, min(w - 1, x_start))
        y_start = max(0, min(h - 1, y_start))
        crop_w = max(1, min(w - x_start, width))
        crop_h = max(1, min(h - y_start, height))

        cropped = image[y_start : y_start + crop_h, x_start : x_start + crop_w]
        return {"output_image": cropped}


class RotateNode(BaseNode):
    """Rotates an image by an angle, optionally expanding canvas boundaries."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("RotateNode requires 'input_image' input.")

        angle = float(params.get("angle", 0.0))
        expand = bool(params.get("expand", True))

        h, w = image.shape[:2]
        cX, cY = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)

        if expand:
            cos = np.abs(M[0, 0])
            sin = np.abs(M[0, 1])
            nW = int((h * sin) + (w * cos))
            nH = int((h * cos) + (w * sin))
            M[0, 2] += (nW / 2) - cX
            M[1, 2] += (nH / 2) - cY
            rotated = cv2.warpAffine(image, M, (nW, nH))
        else:
            rotated = cv2.warpAffine(image, M, (w, h))

        return {"output_image": rotated}


class FlipNode(BaseNode):
    """Flips an image horizontally, vertically, or both."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("FlipNode requires 'input_image' input.")

        direction = params.get("direction", "horizontal")

        if direction == "horizontal":
            flipped = cv2.flip(image, 1)
        elif direction == "vertical":
            flipped = cv2.flip(image, 0)
        else:  # both
            flipped = cv2.flip(image, -1)

        return {"output_image": flipped}
