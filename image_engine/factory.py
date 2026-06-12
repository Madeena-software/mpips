from typing import Dict, Type, Any
from image_engine.nodes.base import BaseNode
from image_engine.nodes.geometry import ResizeNode, CropNode, RotateNode, FlipNode
from image_engine.nodes.adjustments import (
    GrayscaleNode,
    BrightnessContrastNode,
    ThresholdingNode,
    GammaCorrectionNode,
)
from image_engine.nodes.filtering import (
    GaussianBlurNode,
    MedianBlurNode,
    CannyNode,
    SobelNode,
)


class InputNode(BaseNode):
    """Placeholder node for mapping pipeline inputs."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return {"output_image": inputs.get("output_image")}


class OutputNode(BaseNode):
    """Placeholder node for mapping pipeline outputs."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return {"output_image": inputs.get("input_image")}


NODE_CLASSES: Dict[str, Type[BaseNode]] = {
    "input": InputNode,
    "output": OutputNode,
    "resize": ResizeNode,
    "crop": CropNode,
    "rotate": RotateNode,
    "flip": FlipNode,
    "grayscale": GrayscaleNode,
    "brightness_contrast": BrightnessContrastNode,
    "thresholding": ThresholdingNode,
    "gamma_correction": GammaCorrectionNode,
    "gaussian_blur": GaussianBlurNode,
    "median_blur": MedianBlurNode,
    "canny": CannyNode,
    "sobel": SobelNode,
}


def get_node_class(node_type: str) -> Type[BaseNode]:
    """Returns the node behavior class associated with the given node type string."""
    if node_type not in NODE_CLASSES:
        raise ValueError(f"Unknown node type: {node_type}")
    return NODE_CLASSES[node_type]
