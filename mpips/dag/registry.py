from typing import Dict, Type

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
from mpips.dag.nodes.io import InputNode, MadeenaNpzOutputNode, OutputNode
from mpips.dag.nodes.iqa import (
    BrisqueNode,
    ContrastImprovementIndexNode,
    EnhancementMeasureNode,
    EntropyNode,
)
from mpips.dag.nodes.scientific import (
    FABEMDNode,
    CameraCalibrationNode,
    FlatFieldCorrectionNode,
    HomomorphicFilterNode,
    LevelingNode,
    NonLocalMeansNode,
    WaveletDenoisingNode,
)

NODE_CLASSES: Dict[str, Type[BaseNode]] = {
    "input": InputNode,
    "input_npz": InputNode,
    "output": OutputNode,
    "output_npz": MadeenaNpzOutputNode,
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
    "nlm_denoising": NonLocalMeansNode,
    "homomorphic_filter": HomomorphicFilterNode,
    "wavelet_denoising": WaveletDenoisingNode,
    "flat_field_correction": FlatFieldCorrectionNode,
    "leveling": LevelingNode,
    "camera_calibration": CameraCalibrationNode,
    "camera_calibration_warp": CameraCalibrationWarpNode,
    "fabemd": FABEMDNode,
    "merge": MergeNode,
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
