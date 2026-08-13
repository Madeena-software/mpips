from typing import Dict, Type, Any
from mpips.engine.nodes.base import BaseNode
from mpips.engine.nodes.geometry import ResizeNode, CropNode, RotateNode, FlipNode
from mpips.engine.nodes.adjustments import (
    GrayscaleNode,
    BrightnessContrastNode,
    ThresholdingNode,
    GammaCorrectionNode,
    CLAHENode,
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
    LevelingNode,
    CameraCalibrationNode,
    FABEMDNode,
)
from mpips.engine.nodes.calibration import CameraCalibrationWarpNode
from mpips.engine.nodes.composite import MergeNode


class InputNode(BaseNode):
    """Placeholder node for mapping pipeline inputs.

    Backs both catalog entries "input" (general image input) and "input_npz"
    (Madeena radiograph capture NPZ input) — same passthrough behavior for
    both; DAGExecutor decides which slots each node type actually gets
    populated with before calling execute().

    Passes through every slot it's given (output_image plus, for input_npz,
    any named NPZ images such as rawimage/darkimage/processedimage) so each
    is individually wireable to a different downstream node.
    """

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return dict(inputs)


class OutputNode(BaseNode):
    """Placeholder node for mapping pipeline outputs."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return {"output_image": inputs.get("input_image")}


class MadeenaNpzOutputNode(BaseNode):
    """Placeholder node for the Madeena NPZ output ("output_npz" catalog id).

    Passes through whichever rawimage/darkimage/processedimage/npz_metadata
    slots a pipeline wired in (all individually optional) - the real NPZ
    serialization happens in DAGExecutor.execute's output-node branch, same
    pattern as OutputNode not doing the S3 upload itself.
    """

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return dict(inputs)


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
