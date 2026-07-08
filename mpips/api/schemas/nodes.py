from typing import List

from pydantic import BaseModel

from mpips.engine.schemas import (
    InputSlot,
    OutputSlot,
    Parameter,
    ProcessorNodeSchema,
)


class NodeCatalogResponse(BaseModel):
    """Complete catalog of available processing nodes."""

    nodes: List[ProcessorNodeSchema]


__all__ = [
    "InputSlot",
    "NodeCatalogResponse",
    "OutputSlot",
    "Parameter",
    "ProcessorNodeSchema",
]
