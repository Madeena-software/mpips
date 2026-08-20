from __future__ import annotations

import tempfile
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pytest

from mpips.dag import topological_sort as public_topological_sort
from mpips.dag.artifacts import (
    MADEENA_IMAGE_KEYS as canonical_image_keys,
    MADEENA_METADATA_KEYS as canonical_metadata_keys,
    _convert_to_8bit as canonical_convert_to_8bit,
    load_gain_npz_images as canonical_load_gain_npz_images,
    load_npz_image as canonical_load_npz_image,
    load_npz_madeena_metadata as canonical_load_npz_madeena_metadata,
    load_npz_named_images as canonical_load_npz_named_images,
    save_npz_image as canonical_save_npz_image,
    save_npz_madeena as canonical_save_npz_madeena,
)
from mpips.dag.graph import topological_sort as canonical_topological_sort
from mpips.engine import topological_sort
from mpips.engine.dag import (
    MADEENA_IMAGE_KEYS,
    MADEENA_METADATA_KEYS,
    _convert_to_8bit,
    load_gain_npz_images,
    load_npz_image,
    load_npz_madeena_metadata,
    load_npz_named_images,
    save_npz_image,
    save_npz_madeena,
)


def test_baseline_topological_sort_simple_chain_and_identity() -> None:
    nodes = [
        {"id": "input", "type": "input"},
        {"id": "resize", "type": "resize"},
        {"id": "output", "type": "output"},
    ]
    result = topological_sort(
        nodes,
        [
            {"source": "input", "target": "resize"},
            {"source": "resize", "target": "output"},
        ],
    )

    assert [node["id"] for node in result] == ["input", "resize", "output"]
    assert result == nodes
    assert all(result[index] is nodes[index] for index in range(3))


def test_baseline_topological_sort_fan_out_and_fan_in() -> None:
    fan_out_nodes = [
        {"id": "root", "type": "input"},
        {"id": "left", "type": "resize"},
        {"id": "right", "type": "crop"},
    ]
    assert [
        node["id"]
        for node in topological_sort(
            fan_out_nodes,
            [
                {"source": "root", "target": "left"},
                {"source": "root", "target": "right"},
            ],
        )
    ] == ["root", "left", "right"]

    fan_in_nodes = [
        {"id": "left", "type": "resize"},
        {"id": "right", "type": "crop"},
        {"id": "join", "type": "merge"},
    ]
    assert [
        node["id"]
        for node in topological_sort(
            fan_in_nodes,
            [
                {"source": "left", "target": "join"},
                {"source": "right", "target": "join"},
            ],
        )
    ] == ["left", "right", "join"]


def test_baseline_topological_sort_locks_independent_root_order() -> None:
    nodes = [
        {"id": "root_b", "type": "input"},
        {"id": "root_a", "type": "input"},
        {"id": "branch_b", "type": "resize"},
        {"id": "branch_a", "type": "crop"},
        {"id": "join", "type": "merge"},
    ]
    edges = [
        {"source": "root_b", "target": "branch_b"},
        {"source": "root_a", "target": "branch_a"},
        {"source": "branch_b", "target": "join"},
        {"source": "branch_a", "target": "join"},
    ]

    assert [node["id"] for node in topological_sort(nodes, edges)] == [
        "root_b",
        "root_a",
        "branch_b",
        "branch_a",
        "join",
    ]


@pytest.mark.parametrize(
    ("nodes", "edges", "message"),
    [
        (
            [{"id": "target", "type": "output"}],
            [{"source": "missing", "target": "target"}],
            "Edge references non-existent node: missing -> target",
        ),
        (
            [{"id": "source", "type": "input"}],
            [{"source": "source", "target": "missing"}],
            "Edge references non-existent node: source -> missing",
        ),
    ],
)
def test_baseline_topological_sort_missing_nodes_error(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    message: str,
) -> None:
    with pytest.raises(ValueError) as exc_info:
        topological_sort(nodes, edges)

    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    "edges",
    [
        [{"source": "a", "target": "a"}],
        [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "a"},
        ],
    ],
)
def test_baseline_topological_sort_cycle_errors(
    edges: list[dict[str, str]],
) -> None:
    nodes = [
        {"id": "a", "type": "input"},
        {"id": "b", "type": "resize"},
        {"id": "c", "type": "output"},
    ]

    with pytest.raises(ValueError) as exc_info:
        topological_sort(nodes, edges)

    assert str(exc_info.value) == "Cycle detected in graph"


def test_baseline_topological_sort_empty_and_isolated_graphs() -> None:
    assert topological_sort([], []) == []

    nodes = [
        {"id": "first", "type": "input"},
        {"id": "second", "type": "output"},
    ]
    result = topological_sort(nodes, [])

    assert result == nodes
    assert result[0] is nodes[0]
    assert result[1] is nodes[1]


def test_baseline_npz_key_orders_and_image_selection(tmp_path: Path) -> None:
    assert MADEENA_IMAGE_KEYS == ("rawimage", "processedimage", "darkimage")
    assert MADEENA_METADATA_KEYS == (
        "id",
        "gainid",
        "darkid",
        "xrayparams",
        "cameraparams",
        "frameusedcount",
        "description",
    )

    image = np.arange(6, dtype=np.uint16).reshape(2, 3)
    raw = np.full((2, 3), 10, dtype=np.uint16)
    processed = np.full((2, 3), 20, dtype=np.float32)
    dark = np.full((2, 3), 30, dtype=np.uint8)
    path = tmp_path / "capture.npz"
    np.savez(path, darkimage=dark, processedimage=processed, rawimage=raw, image=image)

    np.testing.assert_array_equal(load_npz_image(str(path)), image)
    named = load_npz_named_images(str(path))
    assert list(named) == ["rawimage", "processedimage", "darkimage"]
    np.testing.assert_array_equal(named["rawimage"], raw)
    np.testing.assert_array_equal(named["processedimage"], processed)
    np.testing.assert_array_equal(named["darkimage"], dark)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("rawimage", 10),
        ("processedimage", 20),
        ("darkimage", 30),
    ],
)
def test_baseline_npz_image_priority(tmp_path: Path, key: str, expected: int) -> None:
    path = tmp_path / f"{key}.npz"
    arrays: dict[str, Any] = {key: np.full((2, 2), expected, dtype=np.uint16)}
    np.savez(path, **arrays)

    np.testing.assert_array_equal(load_npz_image(str(path)), expected)


def test_baseline_npz_image_single_array_and_ambiguous_error(tmp_path: Path) -> None:
    single = tmp_path / "single.npz"
    value = np.arange(4, dtype=np.float32).reshape(2, 2)
    np.savez(single, unrelated=value)
    loaded = load_npz_image(str(single))
    np.testing.assert_array_equal(loaded, value)
    assert loaded.dtype == value.dtype
    assert loaded.shape == value.shape

    ambiguous = tmp_path / "ambiguous.npz"
    np.savez(ambiguous, first=np.zeros(1), second=np.ones(1))
    with pytest.raises(ValueError) as exc_info:
        load_npz_image(str(ambiguous))
    assert str(exc_info.value) == (
        f"NPZ '{ambiguous}' has no 'image' key and contains multiple arrays "
        "['first', 'second']; ambiguous which one is the image."
    )


def test_baseline_npz_metadata_order_scalars_arrays_and_missing_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metadata.npz"
    np.savez(
        path,
        description="capture",
        frameusedcount=5,
        cameraparams=np.array({"serial": 7}, dtype=object),
        xrayparams=np.array({"kv": 90}, dtype=object),
        darkid="dark",
        gainid="gain",
        id="capture",
        extra="ignored",
        non_scalar=np.array([1, 2], dtype=np.int16),
    )

    metadata = load_npz_madeena_metadata(str(path))

    assert list(metadata) == [
        "id",
        "gainid",
        "darkid",
        "xrayparams",
        "cameraparams",
        "frameusedcount",
        "description",
    ]
    assert metadata["id"] == "capture"
    assert metadata["xrayparams"] == {"kv": 90}
    assert metadata["cameraparams"] == {"serial": 7}
    assert metadata["frameusedcount"] == 5
    assert "extra" not in metadata


def test_baseline_gain_npz_mapping_order_and_optional_fields(tmp_path: Path) -> None:
    path = tmp_path / "gain.npz"
    flat = np.arange(4, dtype=np.uint16).reshape(2, 2)
    dark = np.full((2, 2), 5, dtype=np.float32)
    np.savez(path, ignored=np.ones(1), darkimage=dark, rawimage=flat)

    result = load_gain_npz_images(str(path))

    assert list(result) == ["gain_flat_image", "gain_dark_image"]
    np.testing.assert_array_equal(result["gain_flat_image"], flat)
    np.testing.assert_array_equal(result["gain_dark_image"], dark)

    only_dark = tmp_path / "only-dark.npz"
    np.savez(only_dark, darkimage=dark)
    result = load_gain_npz_images(str(only_dark))
    assert list(result) == ["gain_dark_image"]


@pytest.mark.parametrize(
    ("image", "expected", "same_object"),
    [
        (np.array([[1, 2]], dtype=np.uint8), np.array([[1, 2]], dtype=np.uint8), True),
        (
            np.array([[0, 65535]], dtype=np.uint16),
            np.array([[0, 255]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[1000, 1000]], dtype=np.uint16),
            np.array([[255, 255]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[-10, 10]], dtype=np.int32),
            np.array([[0, 255]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[0, 100]], dtype=np.uint32),
            np.array([[0, 255]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[0.0, 1.0]], dtype=np.float32),
            np.array([[0, 255]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[-1.0, 3.0]], dtype=np.float32),
            np.array([[0, 255]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[0.5, 0.5]], dtype=np.float32),
            np.array([[127, 127]], dtype=np.uint8),
            False,
        ),
        (
            np.array([[-1.0, -1.0]], dtype=np.float32),
            np.array([[0, 0]], dtype=np.uint8),
            False,
        ),
        (np.array([[1, 2]], dtype=np.int16), np.array([[1, 2]], dtype=np.int16), True),
    ],
)
def test_baseline_convert_to_8bit_contract(
    image: np.ndarray, expected: np.ndarray, same_object: bool
) -> None:
    result = _convert_to_8bit(image)

    np.testing.assert_array_equal(result, expected)
    assert result.dtype == expected.dtype
    assert (result is image) is same_object


def test_baseline_npz_save_round_trips_and_image_precedence(tmp_path: Path) -> None:
    image = np.arange(6, dtype=np.uint16).reshape(2, 3)
    image_path = tmp_path / "image.npz"
    save_npz_image(str(image_path), image)
    with np.load(image_path) as data:
        assert list(data.files) == ["image"]
        np.testing.assert_array_equal(data["image"], image)

    output_path = tmp_path / "madeena.npz"
    metadata = {"rawimage": np.zeros((1,), dtype=np.uint8), "id": "capture"}
    images: dict[str, np.ndarray] = {
        "rawimage": image,
        "processedimage": np.ones((2, 2), dtype=np.float32),
    }
    save_npz_madeena(str(output_path), images, metadata)
    with np.load(output_path, allow_pickle=True) as data:
        assert list(data.files) == ["rawimage", "id", "processedimage"]
        np.testing.assert_array_equal(data["rawimage"], image)
        assert data["id"].item() == "capture"
        np.testing.assert_array_equal(data["processedimage"], images["processedimage"])


def test_baseline_artifact_helpers_accept_file_paths_and_temp_files() -> None:
    with tempfile.NamedTemporaryFile(suffix=".npz") as file:
        array = np.array([1, 2, 3], dtype=np.uint16)
        save_npz_image(file.name, array)
        np.testing.assert_array_equal(load_npz_image(file.name), array)


def test_graph_and_artifacts_are_canonical_engine_aliases() -> None:
    assert canonical_topological_sort is topological_sort
    assert canonical_topological_sort is public_topological_sort
    assert canonical_topological_sort.__module__ == "mpips.dag.graph"

    aliases = [
        (canonical_image_keys, MADEENA_IMAGE_KEYS),
        (canonical_metadata_keys, MADEENA_METADATA_KEYS),
        (canonical_convert_to_8bit, _convert_to_8bit),
        (canonical_load_gain_npz_images, load_gain_npz_images),
        (canonical_load_npz_image, load_npz_image),
        (canonical_load_npz_madeena_metadata, load_npz_madeena_metadata),
        (canonical_load_npz_named_images, load_npz_named_images),
        (canonical_save_npz_image, save_npz_image),
        (canonical_save_npz_madeena, save_npz_madeena),
    ]
    for canonical, legacy in aliases:
        assert canonical is legacy
        if hasattr(canonical, "__module__"):
            assert canonical.__module__ == "mpips.dag.artifacts"


def test_public_graph_import_is_lightweight() -> None:
    script = """
import sys

import mpips.dag

forbidden = (
    "mpips.engine",
    "mpips.api",
    "mpips.worker",
    "cv2",
    "numpy",
    "scipy",
    "skimage",
    "fastapi",
    "celery",
    "boto3",
    "torch",
    "matplotlib",
    "PIL",
)
assert not any(name in sys.modules for name in forbidden), sys.modules.keys()

assert mpips.dag.topological_sort.__module__ == "mpips.dag.graph"
assert not any(name in sys.modules for name in forbidden), sys.modules.keys()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == ""


def test_artifact_import_avoids_engine_and_workflow_dependencies() -> None:
    script = """
import sys

import mpips.dag.artifacts

forbidden = (
    "mpips.engine",
    "mpips.api",
    "mpips.worker",
    "mpips.storage",
    "cv2",
    "scipy",
    "skimage",
    "fastapi",
    "celery",
    "boto3",
)
assert not any(name in sys.modules for name in forbidden), sys.modules.keys()
"""
    subprocess.run([sys.executable, "-c", script], check=True)
