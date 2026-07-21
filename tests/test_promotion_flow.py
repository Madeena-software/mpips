from pathlib import Path

import cv2
import numpy as np

from mpips.engine import DAGExecutor, NODE_CATALOG, get_node_class
from mpips.engine.calibration import warp_image
from mpips.storage import LocalFileStorageBackend


def test_promoted_calibration_helper_is_importable() -> None:
    image = np.arange(9, dtype=np.uint8).reshape(3, 3)
    map_x, map_y = np.meshgrid(
        np.arange(3, dtype=np.float32),
        np.arange(3, dtype=np.float32),
    )

    result = warp_image(image, map_x, map_y)

    np.testing.assert_array_equal(result, image)


def test_promoted_calibration_node_executes_directly() -> None:
    node_cls = get_node_class("camera_calibration_warp")
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)

    outputs = node_cls().execute({"input_image": image}, {})

    np.testing.assert_array_equal(outputs["output_image"], image)


def test_promoted_calibration_node_is_registered_in_catalog() -> None:
    catalog_ids = {node.id for node in NODE_CATALOG}

    assert "camera_calibration_warp" in catalog_ids


def test_promoted_calibration_node_runs_through_dag_with_local_storage(
    tmp_path: Path,
) -> None:
    image = np.arange(256, dtype=np.uint8).reshape(16, 16)
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "outputs" / "output.png"
    assert cv2.imwrite(str(input_path), image)

    map_x, map_y = np.meshgrid(
        np.arange(16, dtype=np.float32),
        np.arange(16, dtype=np.float32),
    )
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {
                "id": "warp_1",
                "type": "camera_calibration_warp",
                "parameters": {
                    "map_x": map_x.tolist(),
                    "map_y": map_y.tolist(),
                },
            },
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "warp_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
            {
                "source": "warp_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }

    result = DAGExecutor(storage=LocalFileStorageBackend(tmp_path)).execute(
        pipeline,
        {"in_1": {"key": "input.png"}},
        {"prefix": "outputs/"},
    )

    assert result["status"] == "completed"
    assert result["output_target"] == "outputs/output.png"
    assert output_path.exists()

    written = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    np.testing.assert_array_equal(written, image)
