"""Public import surface for MPIPS."""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

try:
    __version__ = version("mpips")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "__version__",
    "app",
    "create_app",
    "DAGExecutor",
    "NODE_CATALOG",
    "get_node_class",
    "topological_sort",
]


def __getattr__(name: str) -> Any:
    if name in {"app", "create_app"}:
        from mpips.api import app, create_app

        return {"app": app, "create_app": create_app}[name]

    if name in {"DAGExecutor", "topological_sort"}:
        from mpips.dag import DAGExecutor, topological_sort

        return {
            "DAGExecutor": DAGExecutor,
            "topological_sort": topological_sort,
        }[name]

    if name == "NODE_CATALOG":
        from mpips.dag import NODE_CATALOG

        return NODE_CATALOG

    if name == "get_node_class":
        from mpips.dag import get_node_class

        return get_node_class

    raise AttributeError(f"module 'mpips' has no attribute {name!r}")
