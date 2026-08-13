#!/usr/bin/env python3
"""
MPIPS Root-Owned Host Systemd Worker Launcher Service Daemon
Listens on a narrow Unix domain socket (/var/run/mpips-launcher.sock)
and launches locked-down NPZ conversion worker containers on the host.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Configure structured audit logging without PHI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AUDIT] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("mpips-host-launcher")

SOCKET_PATH = Path(
    os.getenv("MPIPS_LAUNCHER_SOCKET_PATH", "/var/run/mpips-launcher.sock")
)
WORKSPACE_ROOT = Path(
    os.getenv("MPIPS_WORKSPACE_ROOT", "/tmp/mpips-workspaces")
).resolve()
WORKER_IMAGE = os.getenv("MPIPS_WORKER_IMAGE", "mpips-npz-worker:internal-beta")
WORKER_USER = os.getenv("MPIPS_WORKER_USER", "10001:10001")
WORKER_MEMORY = os.getenv("MPIPS_WORKER_MEMORY", "4g")
WORKER_TMPFS_SIZE = os.getenv("MPIPS_WORKER_TMPFS_SIZE", "512m")
TIMEOUT_SECONDS = int(os.getenv("MPIPS_WORKER_TIMEOUT_SECONDS", "300"))
JOB_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def validate_workspace(workspace_dir_str: str) -> Path:
    """Validate that workspace_dir is canonical and within WORKSPACE_ROOT."""
    if not workspace_dir_str:
        raise ValueError("INVALID_WORKSPACE_PATH")

    target_path = Path(workspace_dir_str).resolve()

    # Path traversal check: target must be inside WORKSPACE_ROOT
    try:
        target_path.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError("PATH_TRAVERSAL_REJECTED") from exc

    if target_path == WORKSPACE_ROOT:
        raise ValueError("ROOT_WORKSPACE_REJECTED")

    # Directory name check
    folder_name = target_path.name
    if not folder_name.startswith("job-"):
        raise ValueError("INVALID_WORKSPACE_PREFIX")

    if not target_path.is_dir():
        raise ValueError("WORKSPACE_DIRECTORY_NOT_FOUND")

    # Must contain args.json
    args_file = target_path / "args.json"
    if not args_file.is_file():
        raise ValueError("ARGS_JSON_NOT_FOUND")

    return target_path


def build_docker_cmd(job_id: str, workspace_dir: Path) -> list[str]:
    """Builds a fixed, locked-down Docker command with no arbitrary client arguments."""
    container_name = f"mpips-worker-{job_id}"
    args_path_in_container = workspace_dir / "args.json"
    result_path_in_container = workspace_dir / "output" / "worker-result.json"

    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--network=none",
        "-e",
        "MPLCONFIGDIR=/tmp",
        f"--memory={WORKER_MEMORY}",
        "--cpus=2",
        f"--user={WORKER_USER}",
        "--tmpfs",
        f"/tmp:rw,noexec,nosuid,size={WORKER_TMPFS_SIZE}",
        "-v",
        f"{workspace_dir}:{workspace_dir}:rw",
        WORKER_IMAGE,
        str(args_path_in_container),
        str(result_path_in_container),
    ]
    return cmd


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Handles an incoming socket request from mpips-api."""
    start_time = time.monotonic()
    job_id = "unknown"

    try:
        raw_data = await asyncio.wait_for(reader.readline(), timeout=10.0)
        if not raw_data:
            writer.close()
            await writer.wait_closed()
            return

        payload: Dict[str, Any] = json.loads(raw_data.decode("utf-8").strip())
        job_id = str(payload.get("job_id", "unknown"))

        if not JOB_ID_REGEX.match(job_id):
            raise ValueError("INVALID_JOB_ID")

        validated_workspace = validate_workspace(str(payload.get("workspace_dir", "")))

        docker_cmd = build_docker_cmd(job_id, validated_workspace)

        logger.info(
            "Launching NPZ worker container job_id=%s container_name=mpips-worker-%s "
            "workspace=%s",
            job_id,
            job_id,
            validated_workspace,
        )

        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            res = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
            if res and isinstance(res, (tuple, list)) and len(res) == 2:
                _, stderr_bytes = res
            else:
                stderr_bytes = b""
            exit_code = proc.returncode if isinstance(proc.returncode, int) else 0
        except asyncio.TimeoutError:
            logger.warning(
                "Worker job_id=%s timed out after %ds, forcing removal",
                job_id,
                TIMEOUT_SECONDS,
            )
            kill_proc = await asyncio.create_subprocess_exec(
                "docker",
                "rm",
                "-f",
                f"mpips-worker-{job_id}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await kill_proc.wait()
            exit_code = 124
            stderr_bytes = b""

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if exit_code == 0:
            response = {"status": "success", "exit_code": 0, "job_id": job_id}
            logger.info(
                "Worker job_id=%s completed successfully status=0 duration_ms=%d",
                job_id,
                elapsed_ms,
            )
        else:
            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
            response = {
                "status": "error",
                "error_code": "CONVERSION_WORKER_FAILURE",
                "exit_code": exit_code,
                "job_id": job_id,
            }
            logger.error(
                "Worker job_id=%s failed exit_code=%d duration_ms=%d stderr=%s",
                job_id,
                exit_code,
                elapsed_ms,
                stderr_text,
            )

        writer.write(json.dumps(response).encode("utf-8") + b"\n")
        await writer.drain()

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        err_msg = str(exc)
        logger.error(
            "Request failed job_id=%s error=%s duration_ms=%d",
            job_id,
            err_msg,
            elapsed_ms,
        )
        err_response = {
            "status": "error",
            "error_code": "CONVERSION_WORKER_FAILURE",
            "job_id": job_id,
        }
        try:
            writer.write(json.dumps(err_response).encode("utf-8") + b"\n")
            await writer.drain()
        except Exception:
            pass
    finally:
        writer.close()
        await writer.wait_closed()


async def run_server() -> None:
    """Starts the Unix domain socket server."""
    if SOCKET_PATH.exists():
        try:
            SOCKET_PATH.unlink()
        except OSError:
            pass

    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)

    server = await asyncio.start_unix_server(handle_client, path=str(SOCKET_PATH))
    os.chmod(str(SOCKET_PATH), 0o660)

    logger.info("MPIPS host worker launcher daemon listening on %s", SOCKET_PATH)
    async with server:
        await server.serve_forever()


def main() -> None:
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Host launcher shutting down.")


if __name__ == "__main__":
    main()
