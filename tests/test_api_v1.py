import os
import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Any
from fastapi import status
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_bypass_token() -> None:
    # Set environment variables for developer bypass during tests
    os.environ["DEV_AUTH_BYPASS"] = "true"
    os.environ["DEV_BEARER_TOKEN"] = "test_developer_token"


@pytest.fixture(autouse=True)
def mock_external_services() -> Any:
    with (
        patch("celery_tasks.tasks.get_redis_client") as mock_redis,
        patch("celery_tasks.tasks.run_pipeline") as mock_run_pipeline,
        patch("celery_tasks.worker.app.control.revoke") as mock_revoke,
    ):

        redis_client = MagicMock()
        mock_redis.return_value = redis_client

        mock_job_state = {
            "job_id": "job_123456",
            "tenant_id": "11111111-1111-4111-8111-111111111111",
            "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
            "status": "queued",
            "progress": 0.0,
            "current_node": None,
            "started_at": None,
            "finished_at": None,
            "outputs": {},
            "error": None,
            "callback_url": "https://mipc.madeena.com/api/v1/callbacks/jobs",
        }
        redis_client.get.return_value = json.dumps(mock_job_state)

        task_mock = MagicMock()
        task_mock.id = "job_123456"
        mock_run_pipeline.apply_async.return_value = task_mock

        yield {
            "redis": redis_client,
            "apply": mock_run_pipeline.apply_async,
            "revoke": mock_revoke,
        }


def test_get_nodes_no_auth() -> None:
    # Remove bypass to simulate no authentication header
    os.environ["DEV_AUTH_BYPASS"] = "false"
    response = client.get("/v1/nodes")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_nodes_success() -> None:
    response = client.get(
        "/v1/nodes",
        headers={"Authorization": "Bearer test_developer_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "nodes" in data
    assert len(data["nodes"]) == 24

    # Verify a couple of specific nodes from the catalog
    nodes_map = {node["id"]: node for node in data["nodes"]}
    assert "input" in nodes_map
    assert "output" in nodes_map
    assert "resize" in nodes_map
    assert "grayscale" in nodes_map

    # Check resize parameters
    resize_node = nodes_map["resize"]
    assert resize_node["category"] == "geometry"
    assert len(resize_node["parameters"]) == 3
    params_map = {param["name"]: param for param in resize_node["parameters"]}
    assert "width" in params_map
    assert params_map["width"]["type"] == "integer"
    assert params_map["width"]["default"] == 800


def test_submit_job_no_auth() -> None:
    os.environ["DEV_AUTH_BYPASS"] = "false"
    response = client.post("/v1/jobs", json={})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_submit_job_validation_error() -> None:
    # Missing required fields
    response = client.post(
        "/v1/jobs",
        json={
            "external_execution_id": "not-a-uuid",
        },
        headers={"Authorization": "Bearer test_developer_token"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_submit_job_success() -> None:
    payload = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {
            "nodes": [
                {"id": "input_1", "type": "input"},
                {"id": "output_1", "type": "output"},
            ],
            "edges": [
                {
                    "source": "input_1",
                    "target": "output_1",
                    "source_handle": "output_image",
                    "target_handle": "input_image",
                }
            ],
        },
        "inputs": {
            "input_1": {
                "source_type": "s3",
                "bucket": "madeena-media",
                "key": "11111111-1111-4111-8111-111111111111/media/image.png",
            }
        },
        "output": {
            "destination_type": "s3",
            "bucket": "madeena-media",
            "prefix": ("11111111-1111-4111-8111-111111111111/" "outputs/8fa3b7e4/"),
        },
        "callback_url": "https://mipc.madeena.com/api/v1/callbacks/jobs",
    }
    response = client.post(
        "/v1/jobs",
        json=payload,
        headers={"Authorization": "Bearer test_developer_token"},
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert "submitted_at" in data


def test_submit_job_rejects_cross_tenant_input_key() -> None:
    payload = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {"nodes": [], "edges": []},
        "inputs": {
            "input_1": {
                "source_type": "s3",
                "bucket": "madeena-media",
                "key": "22222222-2222-4222-8222-222222222222/media/image.png",
            }
        },
        "output": {
            "destination_type": "s3",
            "bucket": "madeena-media",
            "prefix": ("11111111-1111-4111-8111-111111111111/" "outputs/8fa3b7e4/"),
        },
    }

    response = client.post(
        "/v1/jobs",
        json=payload,
        headers={"Authorization": "Bearer test_developer_token"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "cross-tenant" in str(response.json())


def test_submit_job_rejects_cross_tenant_output_prefix() -> None:
    payload = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
        "pipeline": {"nodes": [], "edges": []},
        "inputs": {
            "input_1": {
                "source_type": "s3",
                "bucket": "madeena-media",
                "key": "11111111-1111-4111-8111-111111111111/media/image.png",
            }
        },
        "output": {
            "destination_type": "s3",
            "bucket": "madeena-media",
            "prefix": ("22222222-2222-4222-8222-222222222222/" "outputs/8fa3b7e4/"),
        },
    }

    response = client.post(
        "/v1/jobs",
        json=payload,
        headers={"Authorization": "Bearer test_developer_token"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Output prefix" in str(response.json())


def test_get_job_status_success() -> None:
    job_id = "job_123456"
    response = client.get(
        f"/v1/jobs/{job_id}",
        headers={"Authorization": "Bearer test_developer_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["job_id"] == job_id
    assert data["tenant_id"] == "11111111-1111-4111-8111-111111111111"
    assert data["status"] == "queued"
    assert data["progress"] == 0.0
    assert data["external_execution_id"] == "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851"


def test_cancel_job_success() -> None:
    job_id = "job_123456"
    response = client.delete(
        f"/v1/jobs/{job_id}",
        headers={"Authorization": "Bearer test_developer_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "cancelled"
    assert "cancelled_at" in data
