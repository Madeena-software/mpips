from typing import Dict, Type, Any
from mpips.engine.nodes.base import BaseNode
from mpips.engine.nodes.geometry import ResizeNode, CropNode, RotateNode, FlipNode
from mpips.engine.nodes.adjustments import (
    GrayscaleNode,
    BrightnessContrastNode,
    ThresholdingNode,
    GammaCorrectionNode,
)
from mpips.engine.nodes.filtering import (
    GaussianBlurNode,
    MedianBlurNode,
    CannyNode,
    SobelNode,
)
from mpips.engine.nodes.iqa import (
    BrisqueNode,
    ContrastImprovementIndexNode,
    EnhancementMeasureNode,
    EntropyNode,
)
from mpips.engine.nodes.scientific import (
    NonLocalMeansNode,
    HomomorphicFilterNode,
    WaveletDenoisingNode,
    FlatFieldCorrectionNode,
    CameraCalibrationNode,
    FABEMDNode,
)
from mpips.engine.nodes.calibration import CameraCalibrationWarpNode


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
    "nlm_denoising": NonLocalMeansNode,
    "homomorphic_filter": HomomorphicFilterNode,
    "wavelet_denoising": WaveletDenoisingNode,
    "flat_field_correction": FlatFieldCorrectionNode,
    "camera_calibration": CameraCalibrationNode,
    "camera_calibration_warp": CameraCalibrationWarpNode,
    "fabemd": FABEMDNode,
    "cii": ContrastImprovementIndexNode,
    "ent": EntropyNode,
    "eme": EnhancementMeasureNode,
    "brisque": BrisqueNode,
}


def get_node_class(node_type: str) -> Type[BaseNode]:
    """Returns the node behavior class associated with the given node type string."""
    if node_type not in NODE_CLASSES:
        raise ValueError(f"Unknown node type: {node_type}")
    return NODE_CLASSES[node_type]
