from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from mpips.api.application import app
from mpips.conversion.service import check_launcher_readiness

# Dynamically import mpips-launcher.py
launcher_file_path = (
    Path(__file__).parent.parent / "docker" / "host-launcher" / "mpips-launcher.py"
)
spec = importlib.util.spec_from_file_location("mpips_launcher", launcher_file_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load launcher spec from {launcher_file_path}")
mpips_launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mpips_launcher)

handle_client = mpips_launcher.handle_client


def test_launcher_ping_handler_returns_pong_and_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that handle_client responds immediately to ping without launching Docker."""
    async def _test_body() -> None:
        sock_path = tmp_path / "ping-test.sock"
        monkeypatch.setattr(mpips_launcher, "WORKER_IMAGE", "mpips-npz-worker:test-tag-123")

        server = await asyncio.start_unix_server(handle_client, path=str(sock_path))
        async with server:
            reader, writer = await asyncio.open_unix_connection(str(sock_path))
            payload = json.dumps({"action": "ping"}).encode("utf-8") + b"\n"
            writer.write(payload)
            await writer.drain()

            data = await reader.read(4096)
            writer.close()
            await writer.wait_closed()

            resp = json.loads(data.decode("utf-8"))
            assert resp.get("status") == "success"
            assert resp.get("action") == "pong"
            assert resp.get("worker_image") == "mpips-npz-worker:test-tag-123"

    asyncio.run(_test_body())


def test_check_launcher_readiness_socket_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When launcher socket does not exist, check_launcher_readiness reports unready."""
    missing_sock = tmp_path / "absent.sock"
    monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(missing_sock))

    res = check_launcher_readiness(timeout_seconds=0.5)
    assert res["status"] == "unready"
    assert res["error_code"] == "LAUNCHER_SOCKET_NOT_FOUND"
    assert res["socket_path"] == str(missing_sock)


def test_check_launcher_readiness_connection_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When socket file exists but nothing is listening, check_launcher_readiness reports error."""
    dead_sock = tmp_path / "dead.sock"
    # Create dead socket
    import socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(str(dead_sock))
    s.close()

    monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(dead_sock))

    res = check_launcher_readiness(timeout_seconds=0.5)
    assert res["status"] == "unready"
    assert res["error_code"] == "LAUNCHER_CONNECTION_FAILED"


def test_check_launcher_readiness_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When launcher daemon is listening and returns pong, readiness succeeds."""
    import concurrent.futures

    async def _test_body() -> None:
        sock_path = tmp_path / "ready.sock"
        monkeypatch.setattr(mpips_launcher, "WORKER_IMAGE", "mpips-npz-worker:sha-abcdef123456")
        monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(sock_path))

        server = await asyncio.start_unix_server(handle_client, path=str(sock_path))
        async with server:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = await asyncio.get_running_loop().run_in_executor(
                    pool, check_launcher_readiness, 2.0
                )
                assert res["status"] == "ready"
                assert res["service"] == "mpips-host-launcher"
                assert res["worker_image"] == "mpips-npz-worker:sha-abcdef123456"
                assert res["socket_path"] == str(sock_path)

    asyncio.run(_test_body())


def test_readiness_endpoint_unready_returns_503(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /v1/readiness returns HTTP 503 when launcher is unready."""
    monkeypatch.setattr(
        "mpips.conversion.service.check_launcher_readiness",
        lambda timeout_seconds=3.0: {
            "status": "unready",
            "error_code": "LAUNCHER_SOCKET_NOT_FOUND",
            "socket_path": "/var/run/mpips/launcher.sock",
        },
    )
    client = TestClient(app)
    response = client.get("/v1/readiness")
    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["status"] == "unready"
    assert data["detail"]["error_code"] == "LAUNCHER_SOCKET_NOT_FOUND"


def test_readiness_endpoint_ready_returns_200(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /v1/readiness returns HTTP 200 when launcher is ready."""
    monkeypatch.setattr(
        "mpips.conversion.service.check_launcher_readiness",
        lambda timeout_seconds=3.0: {
            "status": "ready",
            "service": "mpips-host-launcher",
            "worker_image": "mpips-npz-worker:prod-v1",
            "socket_path": "/var/run/mpips/launcher.sock",
        },
    )
    client = TestClient(app)
    response = client.get("/v1/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["worker_image"] == "mpips-npz-worker:prod-v1"


def test_deploy_workflow_has_no_nohup_and_enforces_supervision() -> None:
    """Deployment workflow must never invoke nohup for host launcher."""
    workflow_path = (
        Path(__file__).parent.parent / ".github" / "workflows" / "deploy-internal-beta.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    assert "nohup" not in content, "nohup invocation detected in deploy-internal-beta.yml"
    assert "systemctl restart mpips-launcher.service" in content
    assert "systemctl is-active --quiet mpips-launcher.service" in content
    assert "/v1/readiness" in content
    assert "mpips-npz-worker:$MPIPS_VERSION" in content


def test_verify_workflow_enforces_conversion_readiness() -> None:
    """Verify workflow must assert launcher supervision and /v1/readiness."""
    workflow_path = (
        Path(__file__).parent.parent / ".github" / "workflows" / "verify-internal-beta.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    assert "systemctl is-active --quiet mpips-launcher.service" in content
    assert "/v1/readiness" in content
    assert "MPIPS_LAUNCHER_SOCKET_PATH" in content


def test_compose_prod_preserves_container_isolation() -> None:
    """Compose production configuration must never mount Docker socket into mpips-api."""
    compose_path = Path(__file__).parent.parent / "docker-compose.prod.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "docker.sock" not in content, "mpips-api container must NOT mount docker.sock"
    assert "/var/run/mpips:rw" in content
    assert "MPIPS_LAUNCHER_SOCKET_PATH: /var/run/mpips/launcher.sock" in content


def test_systemd_unit_configuration() -> None:
    """Validate systemd service and socket units."""
    service_path = (
        Path(__file__).parent.parent
        / "docker"
        / "host-launcher"
        / "mpips-launcher.service"
    )
    service_content = service_path.read_text(encoding="utf-8")
    assert "Restart=always" in service_content
    assert "RestartSec=5s" in service_content
    assert "EnvironmentFile=-/var/www/mpips-runtime/launcher.env" in service_content

    socket_path = (
        Path(__file__).parent.parent
        / "docker"
        / "host-launcher"
        / "mpips-launcher.socket"
    )
    socket_content = socket_path.read_text(encoding="utf-8")
    assert "/var/www/mpips-runtime/launcher/launcher.sock" in socket_content
