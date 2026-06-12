from pydantic import BaseModel, Field
from typing import List, Optional, Any


class InputSlot(BaseModel):
    name: str = Field(..., description="Name of the input slot")
    type: str = Field(..., description="Data type of the input, e.g. 'image'")


class OutputSlot(BaseModel):
    name: str = Field(..., description="Name of the output slot")
    type: str = Field(..., description="Data type of the output, e.g. 'image', 'float'")


class Parameter(BaseModel):
    name: str = Field(..., description="Name of the parameter")
    type: str = Field(
        ...,
        description=(
            "Data type of the parameter, e.g. "
            "'integer', 'float', 'string', 'boolean'"
        ),
    )
    default: Optional[Any] = Field(None, description="Default value of the parameter")
    description: Optional[str] = Field(
        None, description="Brief description of the parameter's usage"
    )
    min: Optional[float] = Field(
        None, description="Minimum allowed value for numeric parameters"
    )
    max: Optional[float] = Field(
        None, description="Maximum allowed value for numeric parameters"
    )
    options: Optional[List[str]] = Field(
        None, description="Allowed options for choice-based parameters"
    )


class ProcessorNodeSchema(BaseModel):
    id: str = Field(
        ..., description="Unique machine name identifier of the processor node type"
    )
    name: str = Field(..., description="Human-readable name of the processor node")
    category: str = Field(
        ...,
        description=(
            "Category group, e.g. "
            "'geometry', 'adjustments', 'filtering', 'advanced', 'iqa'"
        ),
    )
    description: Optional[str] = Field(
        None, description="Detailed explanation of the node's function"
    )
    inputs: List[InputSlot] = Field(
        default_factory=list, description="Input slots definition"
    )
    outputs: List[OutputSlot] = Field(
        default_factory=list, description="Output slots definition"
    )
    parameters: List[Parameter] = Field(
        default_factory=list, description="Parameters definition"
    )
    version: str = Field(..., description="Semantic version of the node definition")


class NodeCatalogResponse(BaseModel):
    nodes: List[ProcessorNodeSchema]
