from typing import Any, Dict
from mpips.dag.nodes.base import BaseNode


class ControlFlowNode(BaseNode):
    """Control nodes are evaluated by PipelinePlan, with iteration/branch context."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Control-flow nodes require the pipeline scheduler.")
