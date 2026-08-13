from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

# Dynamically import mpips-launcher.py from docker/host-launcher/
launcher_file_path = (
    Path(__file__).parent.parent / "docker" / "host-launcher" / "mpips-launcher.py"
)
spec = importlib.util.spec_from_file_location("mpips_launcher", launcher_file_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load launcher spec from {launcher_file_path}")
mpips_launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mpips_launcher)

validate_workspace = mpips_launcher.validate_workspace
build_docker_cmd = mpips_launcher.build_docker_cmd
handle_client = mpips_launcher.handle_client


def test_validate_workspace_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_root = tmp_path / "mpips-workspaces"
    ws_root.mkdir()
    monkeypatch.setattr(mpips_launcher, "WORKSPACE_ROOT", ws_root.resolve())

    job_ws = ws_root / "job-test-123"
    job_ws.mkdir()
    (job_ws / "args.json").write_text("{}")

    validated = validate_workspace(str(job_ws))
    assert validated == job_ws.resolve()


def test_validate_workspace_rejects_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_root = tmp_path / "mpips-workspaces"
    ws_root.mkdir()
    monkeypatch.setattr(mpips_launcher, "WORKSPACE_ROOT", ws_root.resolve())

    outside = tmp_path / "outside-dir"
    outside.mkdir()

    with pytest.raises(ValueError) as exc:
        validate_workspace(str(outside))
    assert "PATH_TRAVERSAL_REJECTED" in str(
        exc.value
    ) or "INVALID_WORKSPACE_PREFIX" in str(exc.value)


def test_validate_workspace_rejects_non_job_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_root = tmp_path / "mpips-workspaces"
    ws_root.mkdir()
    monkeypatch.setattr(mpips_launcher, "WORKSPACE_ROOT", ws_root.resolve())

    bad_ws = ws_root / "custom-prefix-dir"
    bad_ws.mkdir()

    with pytest.raises(ValueError) as exc:
        validate_workspace(str(bad_ws))
    assert "INVALID_WORKSPACE_PREFIX" in str(exc.value)


def test_validate_workspace_rejects_missing_args_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws_root = tmp_path / "mpips-workspaces"
    ws_root.mkdir()
    monkeypatch.setattr(mpips_launcher, "WORKSPACE_ROOT", ws_root.resolve())

    job_ws = ws_root / "job-missing-args"
    job_ws.mkdir()

    with pytest.raises(ValueError) as exc:
        validate_workspace(str(job_ws))
    assert "ARGS_JSON_NOT_FOUND" in str(exc.value)


def test_build_docker_cmd_security_flags(tmp_path: Path) -> None:
    job_id = "test-job-999"
    ws = tmp_path / "job-test-job-999"

    cmd = build_docker_cmd(job_id, ws)

    cmd_str = " ".join(cmd)
    assert "--read-only" in cmd
    assert "--cap-drop=ALL" in cmd
    assert "--security-opt=no-new-privileges:true" in cmd
    assert "--network=none" in cmd
    assert "--memory=4g" in cmd
    assert "--cpus=2" in cmd
    assert "--user=10001:10001" in cmd
    assert f"mpips-worker-{job_id}" in cmd
    assert f"{ws}:{ws}:rw" in cmd_str


def test_socket_launcher_client_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _test_body() -> None:
        ws_root = tmp_path / "mpips-workspaces"
        ws_root.mkdir()
        monkeypatch.setattr(mpips_launcher, "WORKSPACE_ROOT", ws_root.resolve())

        job_id = "test-job-async"
        job_ws = ws_root / f"job-{job_id}"
        job_ws.mkdir()
        (job_ws / "args.json").write_text("{}")
        (job_ws / "output").mkdir()

        sock_path = tmp_path / "test-launcher.sock"
        monkeypatch.setattr(mpips_launcher, "SOCKET_PATH", sock_path)

        # Mock subprocess execution to simulate successful container run
        mock_proc = AsyncMock()
        mock_proc.wait.return_value = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            server = await asyncio.start_unix_server(handle_client, path=str(sock_path))
            async with server:
                # Client connects to socket
                reader, writer = await asyncio.open_unix_connection(str(sock_path))
                payload = (
                    json.dumps({"job_id": job_id, "workspace_dir": str(job_ws)}) + "\n"
                ).encode("utf-8")
                writer.write(payload)
                await writer.drain()

                response_data = await reader.read(4096)
                writer.close()
                await writer.wait_closed()

                resp = json.loads(response_data.decode("utf-8"))

                assert resp["status"] == "success"
                assert resp["exit_code"] == 0
                assert resp["job_id"] == job_id
                assert mock_exec.called

    asyncio.run(_test_body())
