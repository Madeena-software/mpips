from __future__ import annotations

import hashlib
import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from mpips.dag.registry import get_node_class as registry_get_node_class
from mpips.dag.executor import (
    DAGExecutor as BaselineDAGExecutor,
    _resolve_output_config as baseline_resolve_output_config,
)

EXECUTOR_MODULE = "mpips.dag.executor"


class RecordingStorage:
    def __init__(
        self,
        *,
        download_writer: Callable[[str, str, bool], None] | None = None,
        fail_download: bool = False,
        fail_upload: bool = False,
    ) -> None:
        self.download_writer = download_writer
        self.fail_download = fail_download
        self.fail_upload = fail_upload
        self.downloads: list[tuple[str, str, bool, str | None]] = []
        self.uploads: list[tuple[str, str, bool, str, str | None]] = []
        self.paths: list[str] = []
        self.uploaded_bytes = b""

    def download_image(
        self,
        source: str,
        local_path: str,
        is_presigned_url: bool = False,
    ) -> None:
        self.downloads.append(
            (source, local_path, is_presigned_url, os.getenv("AWS_BUCKET"))
        )
        self.paths.append(local_path)
        if self.fail_download:
            raise RuntimeError("download failure")
        if self.download_writer is not None:
            self.download_writer(source, local_path, is_presigned_url)
        else:
            Path(local_path).write_bytes(b"input")

    def upload_image(
        self,
        local_path: str,
        target: str,
        is_presigned_url: bool = False,
        mime_type: str = "image/png",
    ) -> None:
        self.uploads.append(
            (
                local_path,
                target,
                is_presigned_url,
                mime_type,
                os.getenv("AWS_BUCKET"),
            )
        )
        self.paths.append(local_path)
        if self.fail_upload:
            raise RuntimeError("upload failure")
        self.uploaded_bytes = Path(local_path).read_bytes()


def _edge(
    source: str,
    target: str,
    source_handle: str = "output_image",
    target_handle: str = "input_image",
) -> dict[str, str]:
    return {
        "source": source,
        "target": target,
        "source_handle": source_handle,
        "target_handle": target_handle,
    }


def _pipeline(*, input_type: str = "input", middle: bool = False) -> dict[str, Any]:
    if middle:
        return {
            "nodes": [
                {"id": "in_1", "type": input_type},
                {"id": "resize_1", "type": "resize"},
                {"id": "out_1", "type": "output"},
            ],
            "edges": [
                _edge("in_1", "resize_1"),
                _edge("resize_1", "out_1"),
            ],
        }
    return {
        "nodes": [
            {"id": "in_1", "type": input_type},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [_edge("in_1", "out_1")],
    }


def _write_output(path: str, image: np.ndarray) -> bool:
    del image
    Path(path).write_bytes(b"deterministic-output")
    return True


def test_baseline_resolve_output_config_contract() -> None:
    shared = {"prefix": "shared/", "bucket": "shared-bucket"}
    assert baseline_resolve_output_config(shared, "out") is shared

    missing = {**shared, "nodes": {"other": {"prefix": "other/"}}}
    assert baseline_resolve_output_config(missing, "out") is missing

    invalid = {**shared, "nodes": {"out": "not-a-dict"}}
    assert baseline_resolve_output_config(invalid, "out") is invalid

    override = {
        **shared,
        "nodes": {"out": {"prefix": "branch/", "bucket": "branch-bucket"}},
    }
    merged = baseline_resolve_output_config(override, "out")
    assert merged is not override
    assert merged == {
        "prefix": "branch/",
        "bucket": "branch-bucket",
        "nodes": override["nodes"],
    }
    assert merged["nodes"] is override["nodes"]


def test_baseline_constructor_preserves_storage_identity_and_default() -> None:
    explicit = RecordingStorage()
    assert BaselineDAGExecutor(explicit).storage is explicit

    with patch(f"{EXECUTOR_MODULE}.S3StorageBackend") as backend:
        default_storage = MagicMock()
        backend.return_value = default_storage
        executor = BaselineDAGExecutor()

    backend.assert_called_once_with()
    assert executor.storage is default_storage


def test_baseline_progress_sequence_and_return_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AWS_BUCKET", raising=False)
    storage = RecordingStorage()
    progress: list[tuple[str, float]] = []
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=image),
        patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
        patch(
            "mpips.iqa.calculate_all_metrics",
            return_value={"quality": 1.0},
        ),
    ):
        result = BaselineDAGExecutor(storage).execute(
            _pipeline(middle=True),
            {"in_1": {"key": "input.png"}},
            {"prefix": "outputs/"},
            on_progress=lambda node_id, percentage: progress.append(
                (node_id, percentage)
            ),
        )

    assert progress == [
        ("in_1", 0.0),
        ("resize_1", 33.33),
        ("out_1", 66.67),
    ]
    assert set(result) == {"status", "output_target", "outputs"}
    assert result["status"] == "completed"
    assert result["output_target"] == "outputs/output.png"
    output = result["outputs"]["out_1"]
    assert set(output) == {
        "storage_disk",
        "bucket",
        "key",
        "url",
        "mime_type",
        "size_bytes",
        "checksum",
        "quality_assessment",
    }
    assert output["storage_disk"] == "s3"
    assert output["bucket"] == "madeena-media"
    assert output["key"] == "outputs/output.png"
    assert output["url"] is None
    assert output["mime_type"] == "image/png"
    assert output["size_bytes"] == len(b"deterministic-output")
    assert output["checksum"] == hashlib.md5(b"deterministic-output").hexdigest()
    assert output["quality_assessment"] == {"quality": 1.0}


@pytest.mark.parametrize(
    ("initial_bucket", "input_bucket", "fail_download"),
    [(None, "input-bucket", False), ("original", "input-bucket", True)],
)
def test_baseline_input_bucket_restores_after_success_or_failure(
    monkeypatch: pytest.MonkeyPatch,
    initial_bucket: str | None,
    input_bucket: str,
    fail_download: bool,
) -> None:
    if initial_bucket is None:
        monkeypatch.delenv("AWS_BUCKET", raising=False)
    else:
        monkeypatch.setenv("AWS_BUCKET", initial_bucket)
    storage = RecordingStorage(fail_download=fail_download)

    with patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=np.zeros((2, 2))):
        if fail_download:
            with pytest.raises(RuntimeError, match="download failure"):
                BaselineDAGExecutor(storage).execute(
                    _pipeline(),
                    {"in_1": {"key": "input.png", "bucket": input_bucket}},
                    {"prefix": "outputs/"},
                )
        else:
            with (
                patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
                patch("mpips.iqa.calculate_all_metrics", return_value={}),
            ):
                BaselineDAGExecutor(storage).execute(
                    _pipeline(),
                    {"in_1": {"key": "input.png", "bucket": input_bucket}},
                    {"prefix": "outputs/"},
                )

    assert storage.downloads[0][3] == input_bucket
    assert os.getenv("AWS_BUCKET") == initial_bucket
    assert storage.paths
    assert all(not Path(path).exists() for path in storage.paths)


@pytest.mark.parametrize("fail_upload", [False, True])
def test_baseline_output_bucket_restores_after_success_or_failure(
    monkeypatch: pytest.MonkeyPatch, fail_upload: bool
) -> None:
    monkeypatch.setenv("AWS_BUCKET", "original-bucket")
    storage = RecordingStorage(fail_upload=fail_upload)
    image = np.zeros((2, 2), dtype=np.uint8)

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=image),
        patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
        patch("mpips.iqa.calculate_all_metrics", return_value={}),
    ):
        if fail_upload:
            with pytest.raises(RuntimeError, match="upload failure"):
                BaselineDAGExecutor(storage).execute(
                    _pipeline(),
                    {"in_1": {"key": "input.png"}},
                    {"prefix": "outputs/", "bucket": "output-bucket"},
                )
        else:
            BaselineDAGExecutor(storage).execute(
                _pipeline(),
                {"in_1": {"key": "input.png"}},
                {"prefix": "outputs/", "bucket": "output-bucket"},
            )

    assert storage.uploads[0][4] == "output-bucket"
    assert os.getenv("AWS_BUCKET") == "original-bucket"
    assert all(not Path(path).exists() for path in storage.paths)


def test_baseline_input_errors_and_missing_connection() -> None:
    storage = RecordingStorage()
    executor = BaselineDAGExecutor(storage)

    with pytest.raises(ValueError) as missing_config:
        executor.execute(_pipeline(), {}, {"prefix": "outputs/"})
    assert str(missing_config.value) == "Missing input configuration for node 'in_1'."

    with pytest.raises(ValueError) as missing_source:
        executor.execute(_pipeline(), {"in_1": {}}, {"prefix": "outputs/"})
    assert str(missing_source.value) == (
        "Input config for 'in_1' must specify 'key' or 'url'."
    )

    broken_storage = RecordingStorage()
    with patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=None):
        with pytest.raises(
            ValueError, match=r"Failed to read downloaded image at '.*'"
        ):
            executor = BaselineDAGExecutor(broken_storage)
            executor.execute(
                _pipeline(), {"in_1": {"key": "input.png"}}, {"prefix": "outputs/"}
            )
    assert all(not Path(path).exists() for path in broken_storage.paths)

    missing_edge = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [_edge("in_1", "out_1", source_handle="missing")],
    }
    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=np.zeros((2, 2))),
        pytest.raises(ValueError) as missing_connection,
    ):
        BaselineDAGExecutor(RecordingStorage()).execute(
            missing_edge,
            {"in_1": {"key": "input.png"}},
            {"prefix": "outputs/"},
        )
    assert str(missing_connection.value) == "Missing connection for out_1:input_image"


@pytest.mark.parametrize(
    ("source", "expected_input_suffix", "expected_output_suffix", "url"),
    [
        ("asset.tiff", ".tiff", ".tiff", False),
        ("asset.tif?signature=1", ".tif", ".tif", True),
        ("asset.jpg", ".jpg", ".png", False),
        ("asset.jpeg", ".jpeg", ".png", False),
        ("asset.webp", ".webp", ".png", False),
        ("asset.gif", ".gif", ".png", False),
        ("asset.svg", ".svg", ".png", False),
        ("asset.bmp", ".bmp", ".png", False),
        ("asset.npz", ".npz", ".npz", False),
        ("asset.unknown", ".png", ".png", False),
    ],
)
def test_baseline_extension_url_and_mime_contract(
    source: str,
    expected_input_suffix: str,
    expected_output_suffix: str,
    url: bool,
) -> None:
    image = np.arange(4, dtype=np.uint8).reshape(2, 2)

    def write_npz(_source: str, path: str, _is_presigned: bool) -> None:
        np.savez(path, image=image)

    storage = RecordingStorage(
        download_writer=write_npz if source.endswith(".npz") else None
    )
    input_config = (
        {"in_1": {"url": f"https://example.test/{source}"}}
        if url
        else {"in_1": {"key": source}}
    )

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=image),
        patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
        patch("mpips.iqa.calculate_all_metrics", return_value={}),
    ):
        result = BaselineDAGExecutor(storage).execute(
            _pipeline(), input_config, {"prefix": "outputs/"}
        )

    assert Path(storage.downloads[0][1]).suffix == expected_input_suffix
    assert storage.downloads[0][2] is url
    assert result["output_target"] == f"outputs/output{expected_output_suffix}"
    output = result["outputs"]["out_1"]
    expected_mime = {
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".npz": "application/octet-stream",
    }.get(expected_output_suffix, "image/png")
    assert output["mime_type"] == expected_mime


def test_baseline_url_output_and_iqa_uses_first_input_reference() -> None:
    image_a = np.full((2, 2), 1, dtype=np.uint8)
    image_b = np.full((2, 2), 9, dtype=np.uint8)
    storage = RecordingStorage()
    references: list[tuple[np.ndarray, np.ndarray]] = []
    pipeline = {
        "nodes": [
            {"id": "in_a", "type": "input"},
            {"id": "in_b", "type": "input"},
            {"id": "out_a", "type": "output"},
            {"id": "out_b", "type": "output"},
        ],
        "edges": [
            _edge("in_a", "out_a"),
            _edge("in_b", "out_b"),
        ],
    }

    def metrics(output: np.ndarray, reference: np.ndarray) -> dict[str, float]:
        references.append((output.copy(), reference.copy()))
        return {"quality": 1.0}

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", side_effect=[image_a, image_b]),
        patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
        patch("mpips.iqa.calculate_all_metrics", side_effect=metrics),
    ):
        result = BaselineDAGExecutor(storage).execute(
            pipeline,
            {
                "in_a": {"key": "a.png"},
                "in_b": {"key": "b.png"},
            },
            {"destination_type": "url", "url": "https://example.test/output.png"},
        )

    assert result["output_target"] == "https://example.test/output.png"
    assert len(references) == 2
    assert [int(reference.mean()) for _, reference in references] == [1, 1]
    assert all(int(output.mean()) in {1, 9} for output, _ in references)
    assert all(upload[2] is True for upload in storage.uploads)
    assert all(
        upload[1] == "https://example.test/output.png" for upload in storage.uploads
    )
    assert all(not Path(path).exists() for path in storage.paths)


def test_baseline_gain_url_and_npz_routing() -> None:
    raw = np.zeros((2, 2), dtype=np.uint16)
    gain_flat = np.full((2, 2), 42, dtype=np.uint16)

    def write_npz(source: str, path: str, _is_presigned: bool) -> None:
        if "gain" in source:
            np.savez(path, rawimage=gain_flat, darkimage=np.ones((2, 2)))
        else:
            np.savez(
                path,
                id="capture",
                gainid="gain",
                rawimage=raw,
                processedimage=np.ones((2, 2)),
            )

    storage = RecordingStorage(download_writer=write_npz)
    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input_npz"},
            {"id": "out_1", "type": "output"},
        ],
        "edges": [_edge("in_1", "out_1", "gain_flat_image")],
    }
    inputs = {
        "in_1": {
            "url": "https://example.test/capture.npz",
            "gain_url": "https://example.test/gain.npz",
        }
    }

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
        patch("mpips.iqa.calculate_all_metrics", return_value={}),
    ):
        result = BaselineDAGExecutor(storage).execute(
            pipeline, inputs, {"prefix": "outputs/"}
        )

    assert result["status"] == "completed"
    assert len(storage.downloads) == 2
    assert storage.downloads[0][2] is True
    assert storage.downloads[1][2] is True
    assert Path(storage.downloads[1][1]).suffix == ".npz"
    assert all(not Path(path).exists() for path in storage.paths)


def test_baseline_iqa_executor_local_normalization_is_preserved() -> None:
    image = np.array([[0.0, 1.0], [0.5, 0.75]], dtype=np.float32)
    captured: list[tuple[np.ndarray, np.ndarray]] = []

    def metrics(output: np.ndarray, reference: np.ndarray) -> dict[str, float]:
        captured.append((output.copy(), reference.copy()))
        return {}

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=image),
        patch(f"{EXECUTOR_MODULE}.cv2.imwrite", side_effect=_write_output),
        patch("mpips.iqa.calculate_all_metrics", side_effect=metrics),
    ):
        BaselineDAGExecutor(RecordingStorage()).execute(
            _pipeline(), {"in_1": {"key": "image.tiff"}}, {"prefix": "outputs/"}
        )

    assert len(captured) == 1
    output, reference = captured[0]
    assert output.dtype == np.uint8
    assert reference.dtype == np.uint8
    np.testing.assert_array_equal(
        output, np.array([[0, 255], [127, 191]], dtype=np.uint8)
    )
    np.testing.assert_array_equal(reference, output)


def test_baseline_temp_cleanup_on_node_failure() -> None:
    class FailingNode:
        def execute(
            self, inputs: dict[str, Any], params: dict[str, Any]
        ) -> dict[str, Any]:
            del inputs, params
            raise RuntimeError("node failure")

    storage = RecordingStorage()
    original_get_node_class = registry_get_node_class

    def resolve(node_type: str) -> Any:
        if node_type == "failing":
            return FailingNode
        return original_get_node_class(node_type)

    pipeline = {
        "nodes": [
            {"id": "in_1", "type": "input"},
            {"id": "fail_1", "type": "failing"},
        ],
        "edges": [_edge("in_1", "fail_1")],
    }

    with (
        patch(f"{EXECUTOR_MODULE}.cv2.imread", return_value=np.zeros((2, 2))),
        patch(f"{EXECUTOR_MODULE}.get_node_class", side_effect=resolve),
        pytest.raises(RuntimeError, match="node failure"),
    ):
        BaselineDAGExecutor(storage).execute(
            pipeline, {"in_1": {"key": "input.png"}}, {"prefix": "outputs/"}
        )

    assert storage.paths
    assert all(not Path(path).exists() for path in storage.paths)


def test_canonical_executor_ownership_and_public_identity() -> None:
    canonical_module = importlib.import_module("mpips.dag.executor")
    from mpips.dag import DAGExecutor

    assert canonical_module.DAGExecutor.__module__ == "mpips.dag.executor"
    assert DAGExecutor is canonical_module.DAGExecutor


def test_worker_resolves_canonical_executor_without_engine_dag() -> None:
    script = """
import sys

from mpips.dag.executor import DAGExecutor
from mpips.worker.tasks import DAGExecutor as WorkerDAGExecutor

assert WorkerDAGExecutor is DAGExecutor
assert "mpips.engine.dag" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", script], check=True)
