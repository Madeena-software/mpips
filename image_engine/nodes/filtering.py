import cv2
from typing import Dict, Any
from image_engine.nodes.base import BaseNode


class GaussianBlurNode(BaseNode):
    """Smooths images to reduce noise using Gaussian filter."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("GaussianBlurNode requires 'input_image' input.")

        ksize = int(params.get("kernel_size", 5))
        if ksize <= 0:
            ksize = 5
        elif ksize % 2 == 0:
            ksize = ksize + 1

        sigma = float(params.get("sigma", 1.0))
        blurred = cv2.GaussianBlur(image, (ksize, ksize), sigma)
        return {"output_image": blurred}


class MedianBlurNode(BaseNode):
    """Smooths images using non-linear median filter."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("MedianBlurNode requires 'input_image' input.")

        ksize = int(params.get("kernel_size", 5))
        if ksize <= 0:
            ksize = 5
        elif ksize % 2 == 0:
            ksize = ksize + 1

        blurred = cv2.medianBlur(image, ksize)
        return {"output_image": blurred}


class CannyNode(BaseNode):
    """Detects edges using Canny multi-stage hysteresis thresholding."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("CannyNode requires 'input_image' input.")

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

        low = float(params.get("low_threshold", 50.0))
        high = float(params.get("high_threshold", 150.0))

        edges = cv2.Canny(gray, low, high)
        return {"output_image": edges}


class SobelNode(BaseNode):
    """Computes horizontal or vertical derivatives to extract gradients."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("SobelNode requires 'input_image' input.")

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

        dx = int(params.get("dx", 1))
        dy = int(params.get("dy", 0))
        ksize = int(params.get("ksize", 3))

        if ksize not in (1, 3, 5, 7):
            ksize = 3

        sobel = cv2.Sobel(gray, cv2.CV_64F, dx, dy, ksize=ksize)
        sobel = cv2.convertScaleAbs(sobel)
        return {"output_image": sobel}
