import os
import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Any, Dict

from mpips.worker.tasks import (
    run_pipeline,
    dispatch_webhook,
    compute_signature,
)
from celery.app.task import Context


@pytest.fixture
def mock_redis() -> Any:
    with patch("mpips.worker.tasks.get_redis_client") as mock:
        client = MagicMock()
        client.get.return_value = None
        mock.return_value = client
        yield client


def test_compute_signature() -> None:
    secret = "my_secret"
    payload = b'{"status": "completed"}'
    sig = compute_signature(payload, secret)
    assert len(sig) == 64


@patch("httpx.Client")
def test_dispatch_webhook(mock_httpx_client: Any) -> None:
    client_instance = mock_httpx_client.return_value.__enter__.return_value
    client_instance.post.return_value = MagicMock(status_code=200)

    os.environ["WEBHOOK_SECRET"] = "webhook_secret_key"
    callback_url = "https://mipc.example.com/callback"
    payload = {"status": "completed"}

    dispatch_webhook(callback_url, payload)

    # Verify signature generation and POST request
    client_instance.post.assert_called_once()
    args, kwargs = client_instance.post.call_args
    assert args[0] == callback_url
    assert "X-Madeena-Signature" in kwargs["headers"]
    assert "X-Madeena-Timestamp" in kwargs["headers"]
    assert kwargs["headers"]["Content-Type"] == "application/json"


@patch("mpips.worker.tasks.dispatch_webhook")
@patch("mpips.engine.dag.DAGExecutor.execute")
def test_run_pipeline_success(
    mock_execute: Any, mock_dispatch: Any, mock_redis: Any
) -> None:
    # Set up mock execute return
    mock_execute.return_value = {
        "status": "completed",
        "outputs": {
            "output_1": {
                "storage_disk": "s3",
                "checksum": "abc123xyz",
            }
        },
    }

    # Configure mock task details
    task_self = MagicMock()
    task_self.request.id = "test-job-id"
    task_self.request.called_directly = False

    # Initial job data
    job_data = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {"nodes": [], "edges": []},
        "inputs": {},
        "output": {},
        "callback_url": "https://mipc.example.com/callback",
    }

    # Run the task directly
    ctx = Context(id="test-job-id", called_directly=False)
    run_pipeline.request_stack.push(ctx)
    try:
        res = run_pipeline.run(job_data)
    finally:
        run_pipeline.request_stack.pop()

    # Verify outputs
    assert res["status"] == "completed"
    assert res["progress"] == 100.0
    assert res["tenant_id"] == "11111111-1111-4111-8111-111111111111"
    assert "output_1" in res["outputs"]

    # Verify Redis interactions
    assert mock_redis.set.call_count >= 2
    mock_dispatch.assert_called_once_with("https://mipc.example.com/callback", res)


@patch("mpips.worker.tasks.dispatch_webhook")
@patch("mpips.engine.dag.DAGExecutor.execute")
def test_run_pipeline_dispatches_progress_webhook(
    mock_execute: Any, mock_dispatch: Any, mock_redis: Any
) -> None:
    def execute_with_progress(
        pipeline: Dict[str, Any],
        inputs: Dict[str, Any],
        output: Dict[str, Any],
        on_progress: Any,
    ) -> Dict[str, Any]:
        on_progress("resize_1", 50.0)

        return {
            "status": "completed",
            "outputs": {
                "output_1": {
                    "storage_disk": "s3",
                    "checksum": "abc123xyz",
                }
            },
        }

    mock_execute.side_effect = execute_with_progress

    job_data = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {"nodes": [], "edges": []},
        "inputs": {},
        "output": {},
        "callback_url": "https://mipc.example.com/callback",
    }

    ctx = Context(id="test-job-id", called_directly=False)
    run_pipeline.request_stack.push(ctx)
    try:
        res = run_pipeline.run(job_data)
    finally:
        run_pipeline.request_stack.pop()

    assert res["status"] == "completed"
    assert mock_dispatch.call_count == 2

    progress_payload = mock_dispatch.call_args_list[0].args[1]
    assert progress_payload["status"] == "running"
    assert progress_payload["progress"] == 50.0
    assert progress_payload["current_node"] == "resize_1"

    final_payload = mock_dispatch.call_args_list[1].args[1]
    assert final_payload["status"] == "completed"
    assert final_payload["progress"] == 100.0


@patch("mpips.worker.tasks.dispatch_webhook")
@patch("mpips.engine.dag.DAGExecutor.execute")
def test_run_pipeline_failure(
    mock_execute: Any, mock_dispatch: Any, mock_redis: Any
) -> None:
    # Set up mock execute to raise exception
    mock_execute.side_effect = ValueError("Invalid inputs")

    task_self = MagicMock()
    task_self.request.id = "test-job-id"
    task_self.request.called_directly = False

    job_data = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {"nodes": [], "edges": []},
        "inputs": {},
        "output": {},
        "callback_url": "https://mipc.example.com/callback",
    }

    ctx = Context(id="test-job-id", called_directly=False)
    run_pipeline.request_stack.push(ctx)
    try:
        with pytest.raises(ValueError):
            run_pipeline.run(job_data)
    finally:
        run_pipeline.request_stack.pop()

    # Verify Redis status is failed
    called_args = mock_redis.set.call_args_list
    last_call = called_args[-1]
    saved_state = json.loads(last_call[0][1])
    assert saved_state["status"] == "failed"
    assert saved_state["error"] == "Invalid inputs"

    # Verify webhook dispatch
    mock_dispatch.assert_called_once()


def test_run_pipeline_rejects_cross_tenant_paths(mock_redis: Any) -> None:
    job_data: Dict[str, Any] = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {"nodes": [], "edges": []},
        "inputs": {
            "input_1": {"key": "22222222-2222-4222-8222-222222222222/media/image.png"}
        },
        "output": {
            "prefix": ("11111111-1111-4111-8111-111111111111/" "outputs/8fa3b7e4/")
        },
        "callback_url": None,
    }

    ctx = Context(id="test-job-id", called_directly=False)
    run_pipeline.request_stack.push(ctx)
    try:
        with pytest.raises(ValueError, match="cross-tenant"):
            run_pipeline.run(job_data)
    finally:
        run_pipeline.request_stack.pop()

    last_call = mock_redis.set.call_args_list[-1]
    saved_state = json.loads(last_call[0][1])
    assert saved_state["status"] == "failed"
    assert saved_state["tenant_id"] == "11111111-1111-4111-8111-111111111111"
