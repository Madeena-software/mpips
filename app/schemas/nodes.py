from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any


class InputSlot(BaseModel):
    """Declares an input connection point on a processor node."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "input_image", "type": "image"}]}
    )

    name: str = Field(..., description="Name of the input slot")
    type: str = Field(
        ...,
        description="Data type of the input, e.g. 'image'",
    )


class OutputSlot(BaseModel):
    """Declares an output connection point on a processor node."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "output_image", "type": "image"}]}
    )

    name: str = Field(..., description="Name of the output slot")
    type: str = Field(
        ...,
        description=("Data type of the output, " "e.g. 'image', 'float'"),
    )


class Parameter(BaseModel):
    """Configurable parameter exposed by a processor node."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "kernel_size",
                    "type": "integer",
                    "default": 5,
                    "description": "Size of the " "blurring kernel (must be odd)",
                    "min": 1,
                    "max": None,
                    "options": None,
                }
            ]
        }
    )

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
        None,
        description=("Brief description of the parameter's usage"),
    )
    min: Optional[float] = Field(
        None,
        description=("Minimum allowed value for numeric parameters"),
    )
    max: Optional[float] = Field(
        None,
        description=("Maximum allowed value for numeric parameters"),
    )
    options: Optional[List[str]] = Field(
        None,
        description=("Allowed options for choice-based parameters"),
    )


class ProcessorNodeSchema(BaseModel):
    """Full schema of an image-processing node in the catalog."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "gaussian_blur",
                    "name": "Gaussian Blur",
                    "category": "filtering",
                    "description": "Smooths images to "
                    "reduce noise using Gaussian filter.",
                    "inputs": [
                        {
                            "name": "input_image",
                            "type": "image",
                        }
                    ],
                    "outputs": [
                        {
                            "name": "output_image",
                            "type": "image",
                        }
                    ],
                    "parameters": [
                        {
                            "name": "kernel_size",
                            "type": "integer",
                            "default": 5,
                            "description": "Size of " "the blurring kernel",
                            "min": 1,
                            "max": None,
                            "options": None,
                        }
                    ],
                    "version": "1.0.0",
                }
            ]
        }
    )

    id: str = Field(
        ...,
        description=("Unique machine name identifier " "of the processor node type"),
    )
    name: str = Field(
        ...,
        description=("Human-readable name of the processor node"),
    )
    category: str = Field(
        ...,
        description=(
            "Category group, e.g. "
            "'geometry', 'adjustments', "
            "'filtering', 'advanced', 'iqa'"
        ),
    )
    description: Optional[str] = Field(
        None,
        description=("Detailed explanation of " "the node's function"),
    )
    inputs: List[InputSlot] = Field(
        default_factory=list,
        description="Input slots definition",
    )
    outputs: List[OutputSlot] = Field(
        default_factory=list,
        description="Output slots definition",
    )
    parameters: List[Parameter] = Field(
        default_factory=list,
        description="Parameters definition",
    )
    version: str = Field(
        ...,
        description=("Semantic version of the node definition"),
    )


class NodeCatalogResponse(BaseModel):
    """Complete catalog of available processing nodes."""

    nodes: List[ProcessorNodeSchema]
