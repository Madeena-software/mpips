"""Compatibility exports for the canonical DAG node registry."""

from mpips.dag.nodes.io import InputNode, MadeenaNpzOutputNode, OutputNode
from mpips.dag.registry import NODE_CLASSES, get_node_class

__all__ = [
    "InputNode",
    "OutputNode",
    "MadeenaNpzOutputNode",
    "NODE_CLASSES",
    "get_node_class",
]
