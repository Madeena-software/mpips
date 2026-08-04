from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, status

from mpips.api.schemas.dicom import MHCSManifest


def run_isolated_dicom_conversion(
    radiograph_npz_path: Path,
    gain_npz_path: Path,
    manifest: MHCSManifest,
    output_dicom_path: Path,
) -> Dict[str, Any]:
    """Launches worker child process with process group cleanup and timeout."""
    try:
        timeout_seconds = int(os.getenv("MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS", "300"))
    except ValueError:
        timeout_seconds = 300

    with tempfile.TemporaryDirectory(prefix="mpips-service-ipc-") as ipc_dir:
        args_path = Path(ipc_dir) / "args.json"
        result_path = Path(ipc_dir) / "result.json"

        args_data = {
            "radiograph_npz_path": str(radiograph_npz_path),
            "gain_npz_path": str(gain_npz_path),
            "manifest": manifest.model_dump(mode="json"),
            "output_dicom_path": str(output_dicom_path),
        }

        with args_path.open("w", encoding="utf-8") as f:
            json.dump(args_data, f)

        cmd = [
            sys.executable,
            "-m",
            "mpips.conversion.worker",
            str(args_path),
            str(result_path),
        ]

        env = os.environ.copy()

        try:
            proc = subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            if proc.pid:
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except OSError:
                    pass
                try:
                    proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except OSError:
                        pass
                    proc.communicate()

            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="DICOM conversion process timed out",
            )

        if not result_path.exists():
            err_msg = stderr_bytes.decode("utf-8", errors="replace")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Conversion worker produced no result: {err_msg[:100]}",
            )

        try:
            with result_path.open("r", encoding="utf-8") as f:
                result_data = json.load(f)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to read conversion worker result",
            ) from exc

        if proc.returncode != 0 or result_data.get("status") != "success":
            err_code = result_data.get("sanitized_error_code") or "CONVERSION_FAILED"
            if err_code in ("NPZ_VALIDATION_ERROR", "MANIFEST_OR_DATA_ERROR"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validation failed during conversion: {err_code}",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"DICOM conversion worker failed: {err_code}",
            )

        return dict(result_data)
