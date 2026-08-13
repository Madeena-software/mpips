import cv2
import numpy as np
from typing import Dict, Any

from mpips.engine.nodes.base import BaseNode
from mpips.engine.nodes.bit_depth import clip_to_input_dtype


class MergeNode(BaseNode):
    """Weighted sum of multiple wired image inputs.

    Fan-in / recombination node: declares a generous fixed set of named
    input slots (input_1..input_10), each with its own weight parameter,
    and sums whichever ones are actually wired — unwired slots are simply
    ignored. This is the recombination step in fan-out/fan-in pipelines
    such as PACE 2.0's I_L = I_E + βI_HMF (select BIMFs get filtered,
    others pass straight through, then merge back together here).
    """

    MAX_INPUTS = 10

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        wired = [
            (f"input_{i}", inputs[f"input_{i}"])
            for i in range(1, self.MAX_INPUTS + 1)
            if inputs.get(f"input_{i}") is not None
        ]
        if not wired:
            raise ValueError("MergeNode requires at least one wired input.")

        reference = wired[0][1]
        total = np.zeros(reference.shape, dtype=np.float64)
        weight_sum = 0.0

        for name, image in wired:
            weight = float(params.get(f"{name}_weight", 1.0))
            img_float = image.astype(np.float64)
            if img_float.shape != reference.shape:
                img_float = cv2.resize(
                    img_float, (reference.shape[1], reference.shape[0])
                )
            total += img_float * weight
            weight_sum += weight

        if bool(params.get("normalize", True)):
            if weight_sum <= 0:
                raise ValueError(
                    "Sum of MergeNode input weights must be positive when "
                    "normalize is enabled."
                )
            total = total / weight_sum

        return {"output_image": clip_to_input_dtype(total, reference)}
