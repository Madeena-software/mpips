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
def test_dag_executor_multiple_output_nodes_get_distinct_keys(
    mock_imwrite: MagicMock,
    mock_imread: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    mock_imread.return_value = np.zeros((10, 10, 3), dtype=np.uint8)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {"id": "out_1", "type": "output"},
            {"id": "out_2", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
            {
                "source": "in_1",
                "target": "out_2",
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
    outputs = result["outputs"]
    assert set(outputs.keys()) == {"out_1", "out_2"}
    assert (
        outputs["out_1"]["key"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/out_1.png"
    )
    assert (
        outputs["out_2"]["key"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/out_2.png"
    )
    assert mock_upload.call_count == 2


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.cv2.imread")
@patch("mpips.engine.dag.cv2.imwrite")
def test_dag_executor_multiple_output_nodes_per_node_override(
    mock_imwrite: MagicMock,
    mock_imread: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    mock_imread.return_value = np.zeros((10, 10, 3), dtype=np.uint8)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {"id": "out_1", "type": "output"},
            {"id": "out_2", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
            {
                "source": "in_1",
                "target": "out_2",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.png"}
    }
    output_config = {
        "prefix": "11111111-1111-4111-8111-111111111111/outputs/test/",
        "nodes": {
            "out_2": {
                "prefix": "11111111-1111-4111-8111-111111111111/outputs/branch-b/"
            },
        },
    }

    result = executor.execute(pipeline, inputs_config, output_config)

    outputs = result["outputs"]
    assert (
        outputs["out_1"]["key"]
        == "11111111-1111-4111-8111-111111111111/outputs/test/out_1.png"
    )
    assert (
        outputs["out_2"]["key"]
        == "11111111-1111-4111-8111-111111111111/outputs/branch-b/out_2.png"
    )


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.cv2.imread")
@patch("mpips.engine.dag.cv2.imwrite")
def test_dag_executor_multiple_input_nodes_route_independently(
    mock_imwrite: MagicMock,
    mock_imread: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    image_a = np.full((10, 10, 3), 5, dtype=np.uint8)
    image_b = np.full((10, 10, 3), 9, dtype=np.uint8)
    mock_imread.side_effect = [image_a, image_b]

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_a", "type": "input"},
            {"id": "in_b", "type": "input"},
            {"id": "out_a", "type": "output"},
            {"id": "out_b", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_a",
                "target": "out_a",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
            {
                "source": "in_b",
                "target": "out_b",
                "source_handle": "output_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_a": {"key": "11111111-1111-4111-8111-111111111111/media/a.png"},
        "in_b": {"key": "11111111-1111-4111-8111-111111111111/media/b.png"},
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert mock_download.call_count == 2
    downloaded_sources = [call.args[0] for call in mock_download.call_args_list]
    assert downloaded_sources == [
        "11111111-1111-4111-8111-111111111111/media/a.png",
        "11111111-1111-4111-8111-111111111111/media/b.png",
    ]

    written_means = [call.args[1].mean() for call in mock_imwrite.call_args_list]
    assert written_means == [5.0, 9.0]


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


def test_load_npz_image_radiograph_capture_uses_rawimage() -> None:
    raw = np.arange(12, dtype=np.uint16).reshape(3, 4)
    with tempfile.NamedTemporaryFile(suffix=".npz") as f:
        np.savez(
            f.name,
            id="abc123",
            gainid="gain1",
            darkid="dark1",
            xrayparams=np.zeros((1,)),
            frameusedcount=5,
            cameraparams=np.zeros((1,)),
            darkimage=np.ones((3, 4)),
            rawimage=raw,
            processedimage=np.full((3, 4), 2.0),
            description="test capture",
        )
        loaded = load_npz_image(f.name)
    np.testing.assert_array_equal(loaded, raw)


def test_load_npz_image_radiograph_capture_falls_back_when_rawimage_missing() -> None:
    processed = np.full((3, 4), 2.0)
    with tempfile.NamedTemporaryFile(suffix=".npz") as f:
        np.savez(
            f.name,
            id="abc123",
            gainid="gain1",
            darkid="dark1",
            xrayparams=np.zeros((1,)),
            frameusedcount=5,
            cameraparams=np.zeros((1,)),
            darkimage=np.ones((3, 4)),
            processedimage=processed,
            description="test capture",
        )
        loaded = load_npz_image(f.name)
    np.testing.assert_array_equal(loaded, processed)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
@patch("mpips.engine.dag.load_npz_named_images")
@patch("mpips.engine.dag.load_npz_image")
@patch("mpips.engine.dag.save_npz_image")
def test_dag_executor_npz_round_trip(
    mock_save_npz: MagicMock,
    mock_load_npz: MagicMock,
    mock_load_npz_named: MagicMock,
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    mock_load_npz.return_value = np.zeros((100, 100), dtype=np.uint16)
    mock_load_npz_named.return_value = {}

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


MADEENA_XRAYPARAMS = {"detectorMode": "BED", "kv": 90}
MADEENA_CAMERAPARAMS = {"exposure_ms": 12}


def _madeena_npz_writer(raw: np.ndarray, dark: np.ndarray, processed: np.ndarray):
    def fake_download(source: str, dest: str, is_presigned_url: bool = False) -> None:
        np.savez(
            dest,
            id="abc123",
            gainid="gain1",
            darkid="dark1",
            xrayparams=MADEENA_XRAYPARAMS,
            frameusedcount=5,
            cameraparams=MADEENA_CAMERAPARAMS,
            darkimage=dark,
            rawimage=raw,
            processedimage=processed,
            description="test capture",
        )

    return fake_download


def _gain_npz_writer(flat: np.ndarray, dark: np.ndarray):
    def fake_download(source: str, dest: str, is_presigned_url: bool = False) -> None:
        np.savez(
            dest,
            id="gain1",
            xrayparams=MADEENA_XRAYPARAMS,
            cameraparams=MADEENA_CAMERAPARAMS,
            darkimage=dark,
            rawimage=flat,
        )

    return fake_download


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
def test_dag_executor_input_npz_node_routes_named_npz_slot(
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # A Madeena capture NPZ carrying three distinct images: the input_npz
    # node should expose each by name so an edge can target one specifically,
    # instead of the pipeline always getting the auto-picked "output_image".
    raw = np.zeros((10, 10), dtype=np.uint16)
    dark = np.full((10, 10), 7, dtype=np.uint16)
    processed = np.full((10, 10), 3.0, dtype=np.float32)

    mock_download.side_effect = _madeena_npz_writer(raw, dark, processed)

    captured_output: dict[str, np.ndarray] = {}

    def fake_upload(local_path: str, *args: object, **kwargs: object) -> None:
        with np.load(local_path) as data:
            captured_output["image"] = data["image"]

    mock_upload.side_effect = fake_upload

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input_npz"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "darkimage",
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
    np.testing.assert_array_equal(captured_output["image"], dark)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
def test_dag_executor_plain_input_node_does_not_expose_npz_named_slots(
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # A plain "input" node pointed at a Madeena-shaped NPZ must still only
    # surface output_image — rawimage/darkimage/processedimage are exclusive
    # to the "input_npz" node type, even when the source file happens to
    # carry those keys.
    raw = np.zeros((10, 10), dtype=np.uint16)
    dark = np.full((10, 10), 7, dtype=np.uint16)
    processed = np.full((10, 10), 3.0, dtype=np.float32)

    mock_download.side_effect = _madeena_npz_writer(raw, dark, processed)

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
                "source_handle": "darkimage",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.npz"}
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    with pytest.raises(ValueError, match="Missing connection"):
        executor.execute(pipeline, inputs_config, output_config)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
def test_dag_executor_plain_input_node_still_exposes_output_image_from_npz(
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # The generic single-array load (load_npz_image) is unaffected by the
    # split: a plain "input" node against a Madeena-shaped NPZ still resolves
    # output_image (via the rawimage/processedimage/darkimage preference
    # order in load_npz_image), it just doesn't expose the extra slots.
    raw = np.zeros((10, 10), dtype=np.uint16)
    dark = np.full((10, 10), 7, dtype=np.uint16)
    processed = np.full((10, 10), 3.0, dtype=np.float32)

    mock_download.side_effect = _madeena_npz_writer(raw, dark, processed)

    captured_output: dict[str, np.ndarray] = {}

    def fake_upload(local_path: str, *args: object, **kwargs: object) -> None:
        with np.load(local_path) as data:
            captured_output["image"] = data["image"]

    mock_upload.side_effect = fake_upload

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
    np.testing.assert_array_equal(captured_output["image"], raw)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
def test_dag_executor_input_npz_to_output_npz_round_trip(
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # An input_npz node wired straight into an output_npz node: only the
    # slots actually wired (processedimage + npz_metadata) should end up in
    # the written file - rawimage/darkimage are absent since they were never
    # connected, proving output_npz only writes what got wired in.
    raw = np.zeros((10, 10), dtype=np.uint16)
    dark = np.full((10, 10), 7, dtype=np.uint16)
    processed = np.full((10, 10), 3.0, dtype=np.float32)

    mock_download.side_effect = _madeena_npz_writer(raw, dark, processed)

    captured_bytes: dict[str, bytes] = {}

    def fake_upload(local_path: str, *args: object, **kwargs: object) -> None:
        with open(local_path, "rb") as f:
            captured_bytes["npz"] = f.read()

    mock_upload.side_effect = fake_upload

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input_npz"},
            {"id": "out_1", "type": "output_npz"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "processedimage",
                "target_handle": "processedimage",
            },
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "npz_metadata",
                "target_handle": "npz_metadata",
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

    with tempfile.NamedTemporaryFile(suffix=".npz") as f:
        f.write(captured_bytes["npz"])
        f.flush()
        with np.load(f.name, allow_pickle=True) as data:
            assert set(data.files) == {
                "processedimage",
                "id",
                "gainid",
                "darkid",
                "xrayparams",
                "cameraparams",
                "frameusedcount",
                "description",
            }
            np.testing.assert_array_equal(data["processedimage"], processed)
            assert data["id"].item() == "abc123"
            assert data["gainid"].item() == "gain1"
            assert data["darkid"].item() == "dark1"
            assert data["xrayparams"].item() == MADEENA_XRAYPARAMS
            assert data["cameraparams"].item() == MADEENA_CAMERAPARAMS
            assert data["frameusedcount"].item() == 5
            assert data["description"].item() == "test capture"


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
def test_dag_executor_input_npz_node_resolves_gain_images_when_configured(
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # A separate gain/flat-field calibration NPZ, configured via gain_key
    # alongside the capture's own key: gain_flat_image/gain_dark_image
    # should come from the gain file's rawimage/darkimage, distinct from
    # (and not overwriting) the capture's own rawimage/darkimage slots.
    raw = np.zeros((10, 10), dtype=np.uint16)
    dark = np.full((10, 10), 7, dtype=np.uint16)
    processed = np.full((10, 10), 3.0, dtype=np.float32)
    gain_flat = np.full((10, 10), 42, dtype=np.uint16)
    gain_dark = np.full((10, 10), 11, dtype=np.uint16)

    capture_writer = _madeena_npz_writer(raw, dark, processed)
    gain_writer = _gain_npz_writer(gain_flat, gain_dark)

    def dispatch_download(
        source: str, dest: str, is_presigned_url: bool = False
    ) -> None:
        if "gain" in source:
            gain_writer(source, dest, is_presigned_url)
        else:
            capture_writer(source, dest, is_presigned_url)

    mock_download.side_effect = dispatch_download

    captured_output: dict[str, np.ndarray] = {}

    def fake_upload(local_path: str, *args: object, **kwargs: object) -> None:
        with np.load(local_path) as data:
            captured_output["image"] = data["image"]

    mock_upload.side_effect = fake_upload

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input_npz"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "gain_flat_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {
            "key": "11111111-1111-4111-8111-111111111111/media/capture.npz",
            "gain_key": "11111111-1111-4111-8111-111111111111/media/gain.npz",
        }
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    result = executor.execute(pipeline, inputs_config, output_config)

    assert result["status"] == "completed"
    assert mock_download.call_count == 2
    # gain_flat_image resolves to the gain file's flat image, not the
    # capture's own rawimage (which is all-zero in this fixture).
    np.testing.assert_array_equal(captured_output["image"], gain_flat)


@patch("mpips.storage.S3StorageBackend.download_image")
@patch("mpips.storage.S3StorageBackend.upload_image")
def test_dag_executor_input_npz_node_leaves_gain_slots_unset_without_gain_source(
    mock_upload: MagicMock,
    mock_download: MagicMock,
) -> None:
    # No gain_key/gain_url configured: gain_flat_image/gain_dark_image stay
    # unconnected (same "leave unconnected" pattern as any other unwired
    # slot), and no second download is attempted at all.
    raw = np.zeros((10, 10), dtype=np.uint16)
    dark = np.full((10, 10), 7, dtype=np.uint16)
    processed = np.full((10, 10), 3.0, dtype=np.float32)

    mock_download.side_effect = _madeena_npz_writer(raw, dark, processed)

    executor = DAGExecutor()
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input_npz"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [
            {
                "source": "in_1",
                "target": "out_1",
                "source_handle": "gain_flat_image",
                "target_handle": "input_image",
            },
        ],
    }
    inputs_config = {
        "in_1": {"key": "11111111-1111-4111-8111-111111111111/media/input.npz"}
    }
    output_config = {"prefix": "11111111-1111-4111-8111-111111111111/outputs/test/"}

    with pytest.raises(ValueError, match="Missing connection"):
        executor.execute(pipeline, inputs_config, output_config)

    mock_download.assert_called_once()
