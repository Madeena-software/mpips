import tempfile
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from mpips.engine import DAGExecutor, topological_sort
from mpips.engine.dag import load_npz_image, save_npz_image


def test_topological_sort_success() -> None:
    nodes = [
        {"id": "input_1", "type": "input"},
        {"id": "resize_1", "type": "resize"},
        {"id": "output_1", "type": "output"},
    ]
    edges = [
        {"source": "input_1", "target": "resize_1"},
        {"source": "resize_1", "target": "output_1"},
    ]

    sorted_nodes = topological_sort(nodes, edges)
    sorted_ids = [n["id"] for n in sorted_nodes]

    assert sorted_ids.index("input_1") < sorted_ids.index("resize_1")
    assert sorted_ids.index("resize_1") < sorted_ids.index("output_1")


def test_topological_sort_cycle() -> None:
    nodes = [
        {"id": "input_1", "type": "input"},
        {"id": "resize_1", "type": "resize"},
        {"id": "output_1", "type": "output"},
    ]
    edges = [
        {"source": "input_1", "target": "resize_1"},
        {"source": "resize_1", "target": "output_1"},
        {"source": "output_1", "target": "resize_1"},  # cycle
    ]

    with pytest.raises(ValueError, match="Cycle detected"):
        topological_sort(nodes, edges)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.cv2.imread")
@patch("mpips.engine.dag.cv2.imwrite")
def test_dag_executor(
    mock_imwrite: MagicMock,
    mock_imread: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # Mock return value of cv2.imread (returns a simple BGR image array)
    mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {"id": "gray_1", "type": "grayscale"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "gray_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
            {
                "source": "gray_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.png"}
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert (
        result["output_target"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/output.png"
    )

    mock_download.assert_called_once()
    mock_upload.assert_called_once()
    mock_imread.assert_called_once()
    mock_imwrite.assert_called_once()


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.cv2.imread")
@patch("mpips.engine.dag.cv2.imwrite")
def test_dag_executor_tiff_32bit_no_convert(
    mock_imwrite: MagicMock,
    mock_imread: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # Mock return value of cv2.imread: returns a float32 image array (32-bit TIFF)
    mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.float32)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input", "parameters": {"convert_to_8bit": False}},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.tiff"}
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert (
        result["output_target"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/output.tiff"
    )
    # Check that output metadata specifies tiff mime type
    outputs = result["outputs"]["out_1"]
    assert outputs["mime_type"] == "image/tiff"

    # Assert that imwrite received a float32 array
    written_img = mock_imwrite.call_args[0][1]
    assert written_img.dtype == np.float32


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.cv2.imread")
@patch("mpips.engine.dag.cv2.imwrite")
def test_dag_executor_tiff_32bit_convert_to_8bit(
    mock_imwrite: MagicMock,
    mock_imread: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # Mock return value of cv2.imread: returns a float32 image array (32-bit TIFF)
    mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.float32)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input", "parameters": {"convert_to_8bit": True}},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.tiff"}
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert (
        result["output_target"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/output.tiff"
    )
    outputs = result["outputs"]["out_1"]
    assert outputs["mime_type"] == "image/tiff"

    # Assert that imwrite received a uint8 array (8-bit conversion)
    written_img = mock_imwrite.call_args[0][1]
    assert written_img.dtype == np.uint8


def test_load_npz_image_round_trip() -> None:
    array = np.arange(12, dtype=np.uint16).reshape(3, 4)
    with tempfile.NamedTemporaryFile(suffix=".npz") as f:
        save_npz_image(f.name, array)
        loaded = load_npz_image(f.name)
    np.testing.assert_array_equal(loaded, array)


def test_load_npz_image_ambiguous_arrays_rejected() -> None:
    with tempfile.NamedTemporaryFile(suffix=".npz") as f:
        np.savez(f.name, foo=np.zeros((2, 2)), bar=np.ones((2, 2)))
        with pytest.raises(ValueError, match="ambiguous"):
            load_npz_image(f.name)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.load_npz_image")
@patch("mpips.engine.dag.save_npz_image")
def test_dag_executor_npz_round_trip(
    mock_save_npz: MagicMock,
    mock_load_npz: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    mock_load_npz.return_value = np.zeros((100, 100), dtype=np.uint16)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.npz"}
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert (
        result["output_target"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/output.npz"
    )
    outputs = result["outputs"]["out_1"]
    assert outputs["mime_type"] == "application/octet-stream"

    mock_load_npz.assert_called_once()
    mock_save_npz.assert_called_once()
    written_img = mock_save_npz.call_args[0][1]
    assert written_img.dtype == np.uint16
