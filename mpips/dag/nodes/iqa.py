from typing import Any, Dict

from mpips.iqa import (
    calculate_brisque,
    calculate_cii,
    calculate_eme,
    calculate_entropy,
)
from mpips.dag.nodes.base import BaseNode


class EntropyNode(BaseNode):
    """DAG node wrapper for entropy image quality assessment."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("EntropyNode requires 'input_image' input.")

        return {"entropy_score": round(calculate_entropy(image), 4)}


class EnhancementMeasureNode(BaseNode):
    """DAG node wrapper for EME image quality assessment."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("EnhancementMeasureNode requires 'input_image' input.")

        block_size = int(params.get("block_size", 8))

        return {"eme_score": round(calculate_eme(image, block_size), 4)}


class BrisqueNode(BaseNode):
    """DAG node wrapper for BRISQUE image quality assessment."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("BrisqueNode requires 'input_image' input.")

        return {"brisque_score": round(calculate_brisque(image), 4)}


class ContrastImprovementIndexNode(BaseNode):
    """DAG node wrapper for CII image quality assessment."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        processed = inputs.get("input_image")
        if processed is None:
            raise ValueError(
                "ContrastImprovementIndexNode requires 'input_image' input."
            )
        original = inputs.get("reference_image")
        if original is None:
            original = processed

        return {"cii_score": round(calculate_cii(processed, original), 4)}
