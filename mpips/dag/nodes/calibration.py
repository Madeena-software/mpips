from typing import Any, Dict

import numpy as np

from mpips.calibration import warp_image
from mpips.dag.nodes.base import BaseNode


class CameraCalibrationWarpNode(BaseNode):
    """Apply a promoted calibration remap to an image."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("CameraCalibrationWarpNode requires 'input_image'.")

        map_x = inputs.get("map_x", params.get("map_x"))
        map_y = inputs.get("map_y", params.get("map_y"))

        if map_x is None or map_y is None:
            height, width = image.shape[:2]
            map_x, map_y = np.meshgrid(
                np.arange(width, dtype=np.float32),
                np.arange(height, dtype=np.float32),
            )
        else:
            map_x = np.asarray(map_x, dtype=np.float32)
            map_y = np.asarray(map_y, dtype=np.float32)

        return {"output_image": warp_image(image, map_x, map_y)}
