from typing import Any, Dict

from mpips.dag.nodes.base import BaseNode


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
