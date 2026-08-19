from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mpips.dag.catalog import NODE_CATALOG
from mpips.dag.schemas import InputSlot, OutputSlot, Parameter, ProcessorNodeSchema

EXPECTED_CATALOG_SHA256 = (
    "141a2aa4b95398b49eb71b9392a94842b02b3062a76e27db759f4c3525c63c3c"
)
EXPECTED_NODE_RESPONSE_SHA256 = (
    "49c13811d248fbd1bd6c1a5d16026f473ef730abd8fdec176f37c782a58000a2"
)
EXPECTED_NODE_IDS = [
    "input",
    "input_npz",
    "output",
    "output_npz",
    "resize",
    "crop",
    "rotate",
    "flip",
    "grayscale",
    "brightness_contrast",
    "thresholding",
    "gamma_correction",
    "clahe",
    "gaussian_blur",
    "median_blur",
    "canny",
    "sobel",
    "nlm_denoising",
    "homomorphic_filter",
    "wavelet_denoising",
    "flat_field_correction",
    "leveling",
    "camera_calibration",
    "camera_calibration_warp",
    "fabemd",
    "merge",
    "cii",
    "ent",
    "eme",
    "brisque",
]


def _slot(name: str, type_: str) -> tuple[str, str]:
    return name, type_


def _parameter(
    name: str,
    type_: str,
    default: Any = None,
    min_: float | None = None,
    max_: float | None = None,
    options: list[str] | None = None,
) -> tuple[str, str, Any, float | None, float | None, list[str] | None]:
    return name, type_, default, min_, max_, options


EXPECTED_CATALOG_STRUCTURE = {
    "input": {
        "category": "io",
        "version": "1.0.0",
        "inputs": [],
        "outputs": [_slot("output_image", "image")],
        "parameters": [_parameter("convert_to_8bit", "boolean", False)],
        "executable_in_browser": False,
    },
    "input_npz": {
        "category": "io",
        "version": "1.0.0",
        "inputs": [],
        "outputs": [
            _slot("output_image", "image"),
            _slot("rawimage", "image"),
            _slot("darkimage", "image"),
            _slot("processedimage", "image"),
            _slot("npz_metadata", "metadata"),
            _slot("gain_flat_image", "image"),
            _slot("gain_dark_image", "image"),
        ],
        "parameters": [_parameter("convert_to_8bit", "boolean", False)],
        "executable_in_browser": False,
    },
    "output": {
        "category": "io",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [],
        "parameters": [],
        "executable_in_browser": False,
    },
    "output_npz": {
        "category": "io",
        "version": "1.0.0",
        "inputs": [
            _slot("rawimage", "image"),
            _slot("darkimage", "image"),
            _slot("processedimage", "image"),
            _slot("npz_metadata", "metadata"),
        ],
        "outputs": [],
        "parameters": [],
        "executable_in_browser": False,
    },
    "resize": {
        "category": "geometry",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("width", "integer", 800, 1),
            _parameter("height", "integer", 600, 1),
            _parameter(
                "interpolation",
                "string",
                "BILINEAR",
                options=["NEAREST", "BILINEAR", "BICUBIC", "LANCZOS4"],
            ),
        ],
        "executable_in_browser": True,
    },
    "crop": {
        "category": "geometry",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("x_start", "integer", 0, 0),
            _parameter("y_start", "integer", 0, 0),
            _parameter("width", "integer", 100, 1),
            _parameter("height", "integer", 100, 1),
        ],
        "executable_in_browser": True,
    },
    "rotate": {
        "category": "geometry",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("angle", "float", 0.0),
            _parameter("expand", "boolean", True),
        ],
        "executable_in_browser": True,
    },
    "flip": {
        "category": "geometry",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter(
                "direction",
                "string",
                "horizontal",
                options=["horizontal", "vertical", "both"],
            )
        ],
        "executable_in_browser": True,
    },
    "grayscale": {
        "category": "adjustments",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [],
        "executable_in_browser": True,
    },
    "brightness_contrast": {
        "category": "adjustments",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("alpha", "float", 1.0, 0),
            _parameter("beta", "float", 0.0),
        ],
        "executable_in_browser": True,
    },
    "thresholding": {
        "category": "adjustments",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("threshold_value", "integer", 127, 0, 255),
            _parameter("type", "string", "binary", options=["binary", "otsu"]),
        ],
        "executable_in_browser": True,
    },
    "gamma_correction": {
        "category": "adjustments",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [_parameter("gamma", "float", 1.0, 0.1)],
        "executable_in_browser": True,
    },
    "clahe": {
        "category": "adjustments",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("clip_limit", "float", 2.0, 0.1),
            _parameter("tile_grid_size", "integer", 8, 1),
        ],
        "executable_in_browser": False,
    },
    "gaussian_blur": {
        "category": "filtering",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("kernel_size", "integer", 5, 1),
            _parameter("sigma", "float", 1.0, 0),
        ],
        "executable_in_browser": True,
    },
    "median_blur": {
        "category": "filtering",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [_parameter("kernel_size", "integer", 5, 1)],
        "executable_in_browser": True,
    },
    "canny": {
        "category": "filtering",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("low_threshold", "float", 50.0, 0, 255),
            _parameter("high_threshold", "float", 150.0, 0, 255),
        ],
        "executable_in_browser": True,
    },
    "sobel": {
        "category": "filtering",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("dx", "integer", 1, 0, 2),
            _parameter("dy", "integer", 0, 0, 2),
            _parameter("ksize", "integer", 3, 1),
        ],
        "executable_in_browser": True,
    },
    "nlm_denoising": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("h", "float", 3.0, 0),
            _parameter("template_window_size", "integer", 7, 1),
            _parameter("search_window_size", "integer", 21, 1),
        ],
        "executable_in_browser": False,
    },
    "homomorphic_filter": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("low_frequency_gain", "float", 0.5, 0),
            _parameter("high_frequency_gain", "float", 1.5, 0),
            _parameter("cutoff_frequency", "float", 30.0, 1),
        ],
        "executable_in_browser": False,
    },
    "wavelet_denoising": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("wavelet", "string", "db1", options=["db1", "sym2", "haar"]),
            _parameter("mode", "string", "soft", options=["soft", "hard"]),
        ],
        "executable_in_browser": False,
    },
    "flat_field_correction": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [
            _slot("input_image", "image"),
            _slot("dark_field_image", "image"),
            _slot("flat_field_image", "image"),
        ],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("dark_field_key", "string", ""),
            _parameter("flat_field_key", "string", ""),
        ],
        "executable_in_browser": False,
    },
    "leveling": {
        "category": "adjustments",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("target_mean", "float", 0.0, 0),
            _parameter("x_start", "integer", 0, 0),
            _parameter("y_start", "integer", 0, 0),
            _parameter("width", "integer", 0, 0),
            _parameter("height", "integer", 0, 0),
        ],
        "executable_in_browser": False,
    },
    "camera_calibration": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [_parameter("calibration_file_key", "string", "")],
        "executable_in_browser": False,
    },
    "camera_calibration_warp": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            _parameter("map_x", "array"),
            _parameter("map_y", "array"),
        ],
        "executable_in_browser": False,
    },
    "fabemd": {
        "category": "advanced",
        "version": "1.1.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [
            *[_slot(f"bimf_{i}", "image") for i in range(1, 11)],
            _slot("residual", "image"),
        ],
        "parameters": [_parameter("num_imfs", "integer", 2, 1, 10)],
        "executable_in_browser": False,
    },
    "merge": {
        "category": "advanced",
        "version": "1.0.0",
        "inputs": [_slot(f"input_{i}", "image") for i in range(1, 11)],
        "outputs": [_slot("output_image", "image")],
        "parameters": [
            *[_parameter(f"input_{i}_weight", "float", 1.0, 0) for i in range(1, 11)],
            _parameter("normalize", "boolean", True),
        ],
        "executable_in_browser": False,
    },
    "cii": {
        "category": "iqa",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("cii_score", "float")],
        "parameters": [],
        "executable_in_browser": False,
    },
    "ent": {
        "category": "iqa",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("entropy_score", "float")],
        "parameters": [],
        "executable_in_browser": False,
    },
    "eme": {
        "category": "iqa",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("eme_score", "float")],
        "parameters": [_parameter("block_size", "integer", 8, 2)],
        "executable_in_browser": False,
    },
    "brisque": {
        "category": "iqa",
        "version": "1.0.0",
        "inputs": [_slot("input_image", "image")],
        "outputs": [_slot("brisque_score", "float")],
        "parameters": [],
        "executable_in_browser": False,
    },
}


def _catalog_semantic_json() -> str:
    return json.dumps(
        [node.model_dump(mode="json") for node in NODE_CATALOG],
        sort_keys=True,
        separators=(",", ":"),
    )


def _catalog_structure() -> dict[str, dict[str, Any]]:
    return {
        node.id: {
            "category": node.category,
            "version": node.version,
            "inputs": [(slot.name, slot.type) for slot in node.inputs],
            "outputs": [(slot.name, slot.type) for slot in node.outputs],
            "parameters": [
                (
                    parameter.name,
                    parameter.type,
                    parameter.default,
                    parameter.min,
                    parameter.max,
                    parameter.options,
                )
                for parameter in node.parameters
            ],
            "executable_in_browser": node.executable_in_browser,
        }
        for node in NODE_CATALOG
    }


def test_catalog_preserves_order_structure_and_semantic_hash() -> None:
    assert len(NODE_CATALOG) == 30
    assert [node.id for node in NODE_CATALOG] == EXPECTED_NODE_IDS
    assert len({node.id for node in NODE_CATALOG}) == len(NODE_CATALOG)
    assert _catalog_structure() == EXPECTED_CATALOG_STRUCTURE
    assert hashlib.sha256(_catalog_semantic_json().encode()).hexdigest() == (
        EXPECTED_CATALOG_SHA256
    )


@pytest.mark.parametrize(
    ("model", "expected_dump", "expected_schema_sha256"),
    [
        (
            InputSlot(name="input_image", type="image"),
            {"name": "input_image", "type": "image"},
            "528b4bf04f2bfbaf7bb6918bb77c3d1907a0842e9422b759dff22662368b7cd1",
        ),
        (
            OutputSlot(name="output_image", type="image"),
            {"name": "output_image", "type": "image"},
            "c37442a3f793be98f5f0da26b97f078b0e747db0e60f1f2d29c8cb0eab0bd1f8",
        ),
        (
            Parameter(
                name="kernel_size",
                type="integer",
                default=5,
                description="Size",
                min=1,
            ),
            {
                "name": "kernel_size",
                "type": "integer",
                "default": 5,
                "description": "Size",
                "min": 1.0,
                "max": None,
                "options": None,
            },
            "7d6ebdd89e997a4a5dbe1bd511503fb1f40840a751ca5634cd479475fc751406",
        ),
        (
            ProcessorNodeSchema(
                id="sample",
                name="Sample",
                category="filtering",
                inputs=[InputSlot(name="input_image", type="image")],
                outputs=[OutputSlot(name="output_image", type="image")],
                parameters=[
                    Parameter(name="kernel_size", type="integer", default=5, min=1)
                ],
                version="1.0.0",
            ),
            {
                "id": "sample",
                "name": "Sample",
                "category": "filtering",
                "description": None,
                "inputs": [{"name": "input_image", "type": "image"}],
                "outputs": [{"name": "output_image", "type": "image"}],
                "parameters": [
                    {
                        "name": "kernel_size",
                        "type": "integer",
                        "default": 5,
                        "description": None,
                        "min": 1.0,
                        "max": None,
                        "options": None,
                    }
                ],
                "version": "1.0.0",
                "executable_in_browser": False,
            },
            "35641a75297dacbe1f961a861c2f1793e4754d46da863746df0f8d0323a9a46f",
        ),
    ],
)
def test_schema_serialization_and_json_schema(
    model: Any, expected_dump: dict[str, Any], expected_schema_sha256: str
) -> None:
    assert model.model_dump(mode="json") == expected_dump
    schema_json = json.dumps(
        model.model_json_schema(), sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(schema_json.encode()).hexdigest() == expected_schema_sha256


def test_schema_validation_defaults_and_metadata_behavior() -> None:
    for model_class in (InputSlot, OutputSlot, Parameter):
        with pytest.raises(ValidationError):
            model_class.model_validate({"name": "missing_type"})

    with pytest.raises(ValidationError):
        ProcessorNodeSchema.model_validate({"id": "x", "name": "X", "category": "x"})

    parameter = Parameter(name="x", type="integer", default=0, min=1, max=2)
    assert parameter.default == 0
    assert parameter.min == 1
    assert parameter.max == 2

    first = ProcessorNodeSchema(id="x", name="X", category="x", version="1.0.0")
    second = ProcessorNodeSchema(id="y", name="Y", category="x", version="1.0.0")
    assert first.executable_in_browser is False
    first.inputs.append(InputSlot(name="input_image", type="image"))
    assert second.inputs == []


def test_dag_catalog_and_api_schema_use_canonical_symbols() -> None:
    from mpips.api.routes.v1 import router as router_module
    from mpips.api.schemas.nodes import ProcessorNodeSchema as ApiNodeSchema
    from mpips.dag import NODE_CATALOG as FacadeNodeCatalog
    from mpips.engine.catalog import NODE_CATALOG as EngineNodeCatalog
    from mpips.engine.schemas import ProcessorNodeSchema as EngineNodeSchema

    assert FacadeNodeCatalog is NODE_CATALOG
    assert EngineNodeCatalog is NODE_CATALOG
    assert EngineNodeSchema is ProcessorNodeSchema
    assert ApiNodeSchema is ProcessorNodeSchema
    assert router_module.get_nodes.__globals__["NODE_CATALOG"] is NODE_CATALOG


def test_dag_imports_are_lazy_and_engine_free() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.dag

        forbidden = {
            "mpips.engine",
            "mpips.api",
            "mpips.worker",
            "fastapi",
            "celery",
            "boto3",
            "cv2",
            "numpy",
            "torch",
            "matplotlib",
            "PIL",
        }

        def loaded_forbidden():
            return sorted(
                name
                for name in sys.modules
                if name in forbidden
                or any(name.startswith(item + ".") for item in forbidden)
            )

        assert loaded_forbidden() == []
        assert "mpips.dag.catalog" not in sys.modules
        catalog = mpips.dag.NODE_CATALOG
        assert catalog[0].id == "input"
        assert catalog[0].__class__.__module__ == "mpips.dag.schemas"
        assert loaded_forbidden() == []
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_nodes_endpoint_matches_baseline_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mpips.api.application import app

    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("DEV_BEARER_TOKEN", "mock_developer_token_xyz")
    response = TestClient(app).get(
        "/v1/nodes",
        headers={"Authorization": "Bearer mock_developer_token_xyz"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["nodes"]
    assert [node["id"] for node in payload["nodes"]] == EXPECTED_NODE_IDS
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(payload_json.encode()).hexdigest() == (
        EXPECTED_NODE_RESPONSE_SHA256
    )
