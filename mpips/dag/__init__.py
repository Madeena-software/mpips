"""Public DAG execution, catalog, and registry helpers."""

from importlib import import_module
from typing import Any

__all__ = [
    "DAGExecutor",
    "NODE_CATALOG",
    "NODE_CLASSES",
    "get_node_class",
    "topological_sort",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return getattr(import_module("mpips.engine"), name)
    raise AttributeError(f"module 'mpips.dag' has no attribute {name!r}")
