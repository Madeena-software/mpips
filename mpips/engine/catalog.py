"""Compatibility exports for the canonical DAG catalog metadata."""

from mpips.dag.catalog import (
    NODE_CATALOG,
    OUTPUTS_8BIT,
    PRESERVES_BIT_DEPTH,
    USES_8BIT_WORKING_COPY,
)

__all__ = [
    "NODE_CATALOG",
    "OUTPUTS_8BIT",
    "PRESERVES_BIT_DEPTH",
    "USES_8BIT_WORKING_COPY",
]
