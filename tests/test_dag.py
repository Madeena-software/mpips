import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from app.core.dag import topological_sort, DAGExecutor


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


@patch("app.core.dag.download_image")
@patch("app.core.dag.upload_image")
@patch("app.core.dag.cv2.imread")
@patch("app.core.dag.cv2.imwrite")
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
    inputs_config = {"in_1": {"key": "test_input_key.png"}}
    output_config = {"prefix": "test_output_prefix/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert result["output_target"] == "test_output_prefix/output.png"

    mock_download.assert_called_once()
    mock_upload.assert_called_once()
    mock_imread.assert_called_once()
    mock_imwrite.assert_called_once()
