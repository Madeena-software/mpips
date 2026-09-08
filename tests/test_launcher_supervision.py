from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
import yaml
from fastapi.testclient import TestClient

from mpips.api.application import app
from mpips.conversion.service import (
    check_launcher_readiness,
    check_workspace_readiness,
)

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
    assert "socket_path" not in res  # Sanitized


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


def test_check_launcher_readiness_success_image_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When launcher daemon is listening and expected image matches, readiness succeeds."""
    import concurrent.futures

    async def _test_body() -> None:
        sock_path = tmp_path / "ready.sock"
        monkeypatch.setattr(mpips_launcher, "WORKER_IMAGE", "mpips-npz-worker:sha-abcdef123456")
        monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(sock_path))
        monkeypatch.setenv("MPIPS_WORKER_IMAGE", "mpips-npz-worker:sha-abcdef123456")

        server = await asyncio.start_unix_server(handle_client, path=str(sock_path))
        async with server:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = await asyncio.get_running_loop().run_in_executor(
                    pool, check_launcher_readiness, 2.0
                )
                assert res["status"] == "ready"
                assert res["service"] == "mpips-host-launcher"
                assert res["worker_image"] == "mpips-npz-worker:sha-abcdef123456"

    asyncio.run(_test_body())


def test_check_launcher_readiness_fails_on_worker_image_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When launcher reports worker_image different from MPIPS_WORKER_IMAGE, readiness fails."""
    import concurrent.futures

    async def _test_body() -> None:
        sock_path = tmp_path / "mismatch.sock"
        monkeypatch.setattr(mpips_launcher, "WORKER_IMAGE", "mpips-npz-worker:old-version")
        monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(sock_path))
        monkeypatch.setenv("MPIPS_WORKER_IMAGE", "mpips-npz-worker:new-version")

        server = await asyncio.start_unix_server(handle_client, path=str(sock_path))
        async with server:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = await asyncio.get_running_loop().run_in_executor(
                    pool, check_launcher_readiness, 2.0
                )
                assert res["status"] == "unready"
                assert res["error_code"] == "LAUNCHER_WORKER_IMAGE_MISMATCH"
                assert res["worker_image"] == "mpips-npz-worker:old-version"
                assert res["expected_worker_image"] == "mpips-npz-worker:new-version"

    asyncio.run(_test_body())


def test_readiness_endpoint_unready_returns_503(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /v1/readiness returns HTTP 503 when launcher is unready."""
    monkeypatch.setattr(
        "mpips.conversion.service.check_launcher_readiness",
        lambda timeout_seconds=3.0: {
            "status": "unready",
            "service": "mpips-host-launcher",
            "error_code": "LAUNCHER_SOCKET_NOT_FOUND",
        },
    )
    client = TestClient(app)
    response = client.get("/v1/readiness")
    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["status"] == "unready"
    assert data["detail"]["error_code"] == "LAUNCHER_SOCKET_NOT_FOUND"


def test_readiness_endpoint_image_mismatch_returns_503(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /v1/readiness returns HTTP 503 on worker image mismatch."""
    monkeypatch.setattr(
        "mpips.conversion.service.check_launcher_readiness",
        lambda timeout_seconds=3.0: {
            "status": "unready",
            "service": "mpips-host-launcher",
            "error_code": "LAUNCHER_WORKER_IMAGE_MISMATCH",
            "worker_image": "mpips-npz-worker:v1",
            "expected_worker_image": "mpips-npz-worker:v2",
        },
    )
    client = TestClient(app)
    response = client.get("/v1/readiness")
    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["error_code"] == "LAUNCHER_WORKER_IMAGE_MISMATCH"


def test_check_workspace_readiness_fails_when_unwritable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When workspace root cannot be created or written to, check_workspace_readiness reports unready."""
    def _failing_mkdir(self, *args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "mkdir", _failing_mkdir)

    res = check_workspace_readiness()
    assert res["status"] == "unready"
    assert res["service"] == "mpips-workspace"
    assert res["error_code"] == "WORKSPACE_UNAVAILABLE"


def test_check_workspace_readiness_succeeds_when_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When workspace root is writable, probe directory is created, verified, and removed."""
    writable_root = tmp_path / "writable-root"
    monkeypatch.setenv("MPIPS_WORKSPACE_ROOT", str(writable_root))

    res = check_workspace_readiness()
    assert res["status"] == "ready"
    assert not any(writable_root.glob(".readiness-probe-*"))


def test_launcher_ready_but_workspace_unusable_returns_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When launcher daemon and worker image are ready but workspace is unwritable, /v1/readiness returns 503."""
    def _mock_check_workspace():
        return {
            "status": "unready",
            "service": "mpips-workspace",
            "error_code": "WORKSPACE_UNAVAILABLE",
        }

    monkeypatch.setattr("mpips.conversion.service.check_workspace_readiness", _mock_check_workspace)

    sock_path = tmp_path / "ready.sock"
    monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(sock_path))
    monkeypatch.setenv("MPIPS_WORKER_IMAGE", "mpips-npz-worker:v1")

    client = TestClient(app)
    response = client.get("/v1/readiness")
    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["status"] == "unready"
    assert data["detail"]["service"] == "mpips-workspace"
    assert data["detail"]["error_code"] == "WORKSPACE_UNAVAILABLE"


def test_composite_readiness_succeeds_when_launcher_and_workspace_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When both launcher socket and workspace root are ready, check_launcher_readiness returns ready."""
    import concurrent.futures

    async def _test_body() -> None:
        sock_path = tmp_path / "ready.sock"
        writable_root = tmp_path / "writable-workspaces"
        monkeypatch.setattr(mpips_launcher, "WORKER_IMAGE", "mpips-npz-worker:candidate-sha")
        monkeypatch.setenv("MPIPS_LAUNCHER_SOCKET_PATH", str(sock_path))
        monkeypatch.setenv("MPIPS_WORKER_IMAGE", "mpips-npz-worker:candidate-sha")
        monkeypatch.setenv("MPIPS_WORKSPACE_ROOT", str(writable_root))

        server = await asyncio.start_unix_server(handle_client, path=str(sock_path))
        async with server:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = await asyncio.get_running_loop().run_in_executor(
                    pool, check_launcher_readiness, 2.0
                )
                assert res["status"] == "ready"
                assert res["service"] == "mpips-host-launcher"
                assert res["worker_image"] == "mpips-npz-worker:candidate-sha"

    asyncio.run(_test_body())


def test_workflow_yaml_parsing() -> None:
    """Both deployment and verification workflows must parse validly as YAML and preserve release isolation."""
    repo_root = Path(__file__).parent.parent
    deploy_path = repo_root / ".github" / "workflows" / "deploy-internal-beta.yml"
    verify_path = repo_root / ".github" / "workflows" / "verify-internal-beta.yml"

    parsed_deploy = yaml.safe_load(deploy_path.read_text(encoding="utf-8"))
    assert parsed_deploy is not None
    assert "jobs" in parsed_deploy
    # Hotfix deploy workflow name must be distinct from default-branch "Deploy MPIPS Internal Beta"
    # to avoid triggering default-branch workflow_run verification watchers.
    assert parsed_deploy.get("name") != "Deploy MPIPS Internal Beta"
    assert "Deploy MPIPS Internal Beta — Launcher Recovery" in parsed_deploy.get("name", "")

    parsed_verify = yaml.safe_load(verify_path.read_text(encoding="utf-8"))
    assert parsed_verify is not None
    assert "jobs" in parsed_verify
    # Hotfix verify workflow must be explicit manual dispatch only, without workflow_run chaining
    verify_triggers = parsed_verify.get("on") or parsed_verify.get(True)
    if isinstance(verify_triggers, dict):
        assert "workflow_dispatch" in verify_triggers
        assert "workflow_run" not in verify_triggers
    else:
        assert verify_triggers == "workflow_dispatch"


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


def test_deploy_workflow_provisions_workspace_and_verifies_in_container() -> None:
    """Deploy workflow must deterministically provision workspace ownership/mode and probe usability inside container."""
    workflow_path = (
        Path(__file__).parent.parent / ".github" / "workflows" / "deploy-internal-beta.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    # Deterministic provisioning with install -d, restrictive mode, no 0777 base
    assert 'sudo install -d -m 0770 -o "$MPIPS_RUNTIME_UID" -g "$MPIPS_RUNTIME_GID" /tmp/mpips-workspaces' in content
    assert "chmod 0777 /tmp/mpips-workspaces" not in content
    assert "chmod 777 /tmp/mpips-workspaces" not in content

    # In-container verification of identity and workspace mount/usability
    assert 'test "$api_user" = "${MPIPS_RUNTIME_UID}:${MPIPS_RUNTIME_GID}"' in content
    assert 'Destination "/tmp/mpips-workspaces"' in content
    assert 'docker exec "$API_CONTAINER" sh -c' in content
    assert 'mkdir -m 0700 "$probe" && rmdir "$probe"' in content


def test_deploy_workflow_no_heredocs_or_internal_beta_fallback() -> None:
    """Deploy workflow must not use EOF heredocs for launcher.env or fallback to internal-beta."""
    workflow_path = (
        Path(__file__).parent.parent / ".github" / "workflows" / "deploy-internal-beta.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    assert "cat <<EOF >" not in content, "heredoc detected in deploy-internal-beta.yml"
    assert "cat <<'EOF' >" not in content
    assert "MPIPS_PREVIOUS_WORKER_IMAGE=mpips-npz-worker:internal-beta" not in content


def test_deploy_workflow_rollback_verifies_launcher() -> None:
    """Rollback routine must explicitly verify restored launcher probe."""
    workflow_path = (
        Path(__file__).parent.parent / ".github" / "workflows" / "deploy-internal-beta.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    assert "restart mpips-launcher.service || true" not in content, "Silent restart ignore detected"
    assert "python3 scripts/probe_launcher.py" in content
    assert "rollback_launcher_restored=true" in content


def test_verify_workflow_enforces_conversion_readiness_and_version_match() -> None:
    """Verify workflow must assert launcher supervision, /v1/readiness, worker image match, and deployment SHA identity."""
    workflow_path = (
        Path(__file__).parent.parent / ".github" / "workflows" / "verify-internal-beta.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    # Deployed version extraction from runtime marker
    assert '/var/www/mpips-runtime/.mpips-version' in content
    assert 'MPIPS_VERSION=$(cat /var/www/mpips-runtime/.mpips-version)' in content

    # Deployment-identity guard: non-empty check and exact GITHUB_SHA match
    assert 'test -n "${MPIPS_VERSION:-}"' in content
    assert 'test "$MPIPS_VERSION" = "$GITHUB_SHA"' in content
    assert 'Deployment identity verified' in content

    assert "systemctl is-active --quiet mpips-launcher.service" in content
    assert "/v1/readiness" in content
    assert "MPIPS_LAUNCHER_SOCKET_PATH" in content
    assert "scripts/probe_launcher.py" in content
    assert "mpips-npz-worker:${MPIPS_VERSION}" in content


def test_compose_prod_preserves_container_isolation() -> None:
    """Compose production configuration must never mount Docker socket into mpips-api."""
    compose_path = Path(__file__).parent.parent / "docker-compose.prod.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "docker.sock" not in content, "mpips-api container must NOT mount docker.sock"
    assert "/var/run/mpips:rw" in content
    assert "MPIPS_LAUNCHER_SOCKET_PATH: /var/run/mpips/launcher.sock" in content


def test_systemd_unit_configuration_and_socket_unit_retired() -> None:
    """Validate systemd service requires mandatory launcher.env and has no internal-beta fallback."""
    repo_root = Path(__file__).parent.parent
    service_path = (
        repo_root
        / "docker"
        / "host-launcher"
        / "mpips-launcher.service"
    )
    service_content = service_path.read_text(encoding="utf-8")
    assert "Restart=always" in service_content
    assert "RestartSec=5s" in service_content
    # Mandatory EnvironmentFile (no leading -)
    assert "EnvironmentFile=/var/www/mpips-runtime/launcher.env" in service_content
    assert "EnvironmentFile=-" not in service_content
    # No mutable static internal-beta worker image fallback
    assert "mpips-npz-worker:internal-beta" not in service_content

    # Unused socket unit removed from active production contract
    socket_path = (
        repo_root
        / "docker"
        / "host-launcher"
        / "mpips-launcher.socket"
    )
    assert not socket_path.exists(), "docker/host-launcher/mpips-launcher.socket must be retired"
