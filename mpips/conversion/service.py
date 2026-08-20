from __future__ import annotations

import cv2
import hashlib
import json
import logging
import numpy as np
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile

from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, status

from mpips.api.schemas.dicom import (
    MHCSManifest,
    ResolvedMHCSManifest,
    resolve_mhcs_manifest,
)
from mpips.conversion.dicom_enrichment import enrich_dicom_file
from mpips.conversion.metadata import build_converter_metadata_json
from mpips.conversion.validation import validate_dicom_dataset
from mpips.conversion.tiff_json_to_dcm import tiff_json_to_dcm

logger = logging.getLogger(__name__)


def _validate_tiff_descriptor(
    output_dir: Path,
    max_tiff_bytes: int,
    max_rows: int = 16384,
    max_cols: int = 16384,
    max_pixels: int = 268435456,
) -> tuple[np.ndarray, tuple[int, int]]:
    """TOCTOU-safe TIFF validation reading from opened file descriptor."""
    if not hasattr(os, "O_DIRECTORY"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TIFF_VALIDATION_ERROR",
        )

    # 1. Open directory descriptor
    try:
        dir_flags = os.O_RDONLY | os.O_DIRECTORY
        if hasattr(os, "O_CLOEXEC"):
            dir_flags |= os.O_CLOEXEC
        dir_fd = os.open(str(output_dir), dir_flags)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TIFF_VALIDATION_ERROR",
        ) from exc

    try:
        # Check unexpected extra files in output directory
        entries = os.listdir(dir_fd)
        allowed = {"processed.tiff", "worker-result.json"}
        if not set(entries).issubset(allowed):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TIFF_VALIDATION_ERROR",
            )

        # 2. Open processed.tiff relative to directory descriptor with O_NOFOLLOW
        file_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            file_flags |= os.O_NOFOLLOW
        else:
            if sys.platform.startswith("linux"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TIFF_VALIDATION_ERROR",
                )
        if hasattr(os, "O_CLOEXEC"):
            file_flags |= os.O_CLOEXEC

        try:
            file_fd = os.open("processed.tiff", file_flags, dir_fd=dir_fd)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TIFF_VALIDATION_ERROR",
            ) from exc

        try:
            # 3. First fstat
            st1 = os.fstat(file_fd)
            if not stat.S_ISREG(st1.st_mode):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TIFF_VALIDATION_ERROR",
                )

            if st1.st_size <= 0 or st1.st_size > max_tiff_bytes:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TIFF_VALIDATION_ERROR",
                )

            # 4. Bounded loop read until exactly st1.st_size bytes obtained
            chunks = []
            bytes_read = 0
            target_size = st1.st_size
            while bytes_read < target_size:
                chunk = os.read(file_fd, min(65536, target_size - bytes_read))
                if not chunk:
                    break
                chunks.append(chunk)
                bytes_read += len(chunk)

            if bytes_read != target_size:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TIFF_VALIDATION_ERROR",
                )

            # Check EOF
            if len(os.read(file_fd, 1)) != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TIFF_VALIDATION_ERROR",
                )

            # 5. Second fstat for inode/size consistency
            st2 = os.fstat(file_fd)
            if st2.st_size != st1.st_size or st2.st_ino != st1.st_ino:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TIFF_VALIDATION_ERROR",
                )

        finally:
            os.close(file_fd)

    finally:
        os.close(dir_fd)

    # 6. Decode bytes with OpenCV
    raw_bytes = b"".join(chunks)
    img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None or img.ndim != 2 or img.dtype != np.uint16:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TIFF_VALIDATION_ERROR",
        )

    rows, cols = img.shape
    if rows > max_rows or cols > max_cols or (rows * cols) > max_pixels:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TIFF_VALIDATION_ERROR",
        )

    return img, (rows, cols)


def _is_valid_calibration_dir(p: Path) -> bool:
    """Checks if path is a valid calibration directory."""
    if not p.is_dir():
        return False
    if (p / "metadata.json").is_file():
        return True
    try:
        return any(
            sub.is_dir() and (sub / "metadata.json").is_file() for sub in p.iterdir()
        )
    except OSError:
        return False


def resolve_calibration_artifact_dir() -> Path:
    """Resolves the pre-generated, validated calibration artifact directory."""
    env_dir = os.getenv("MPIPS_CALIBRATION_ARTIFACT_DIR")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if _is_valid_calibration_dir(p):
            return p

    artifact_root_env = os.getenv("MPIPS_ARTIFACT_ROOT")
    if artifact_root_env:
        root = Path(artifact_root_env).expanduser().resolve()
        candidates = [
            root / "camera-calibration-dotgrid" / "output" / "neural_model",
            root / "output" / "neural_model",
            root,
        ]
        for candidate in candidates:
            if _is_valid_calibration_dir(candidate):
                return candidate

    default_dir = Path(
        "/var/www/mpips/artifacts/camera-calibration-dotgrid/output/neural_model"
    )
    if _is_valid_calibration_dir(default_dir):
        return default_dir

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="CALIBRATION_ARTIFACT_MISSING",
    )


def _cleanup_workspace(workspace_dir: Path) -> None:
    """Remove a workspace after restoring owner write permission."""
    if not workspace_dir.exists():
        return
    for root, directories, files in os.walk(workspace_dir, topdown=False):
        for name in files:
            try:
                os.chmod(Path(root) / name, 0o600)
            except OSError:
                pass
        for name in directories:
            try:
                os.chmod(Path(root) / name, 0o700)
            except OSError:
                pass
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
    shutil.rmtree(str(workspace_dir), ignore_errors=True)


def run_isolated_dicom_conversion(
    radiograph_npz_path: Path,
    gain_npz_path: Path,
    manifest: MHCSManifest | ResolvedMHCSManifest,
    output_dicom_path: Path,
) -> Dict[str, Any]:
    """Launches worker child process with isolation and descriptor verification."""
    if not isinstance(manifest, ResolvedMHCSManifest):
        rad_bytes = radiograph_npz_path.read_bytes()
        gain_bytes = gain_npz_path.read_bytes()
        rad_sha = hashlib.sha256(rad_bytes).hexdigest()
        gain_sha = hashlib.sha256(gain_bytes).hexdigest()
        manifest = resolve_mhcs_manifest(
            raw_manifest_text=manifest.model_dump_json(),
            input_manifest=manifest,
            rad_bytes_len=len(rad_bytes),
            rad_sha256_hex=rad_sha,
            gain_bytes_len=len(gain_bytes),
            gain_sha256_hex=gain_sha,
        )
    env_mode = os.getenv("MPIPS_ENVIRONMENT", "development").lower()

    try:
        timeout_seconds = int(os.getenv("MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS", "300"))
    except ValueError:
        timeout_seconds = 300

    try:
        max_tiff_bytes = int(
            os.getenv("MPIPS_DICOM_MAX_TIFF_BYTES", str(100 * 1024 * 1024))
        )
    except ValueError:
        max_tiff_bytes = 100 * 1024 * 1024

    cal_src_dir = resolve_calibration_artifact_dir()

    root_str = os.getenv("MPIPS_WORKSPACE_ROOT", "/tmp/mpips-workspaces")
    workspace_base = Path(root_str)
    try:
        workspace_base.mkdir(parents=True, exist_ok=True)
        os.chmod(workspace_base, 0o755)
    except PermissionError as exc:
        if env_mode == "production":
            raise RuntimeError(
                f"Configured workspace root {workspace_base} is unwritable: {exc}"
            ) from exc
        workspace_base = Path(tempfile.gettempdir()) / f"mpips-workspaces-{os.getuid()}"
        workspace_base.mkdir(parents=True, exist_ok=True)

    workspace_dir = Path(
        tempfile.mkdtemp(
            prefix=f"job-{manifest.conversion_job_id}-",
            dir=workspace_base,
        )
    )
    os.chmod(workspace_dir, 0o777)

    output_dir = workspace_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(output_dir, 0o777)

    try:
        # Copy input files to private workspace with fixed names
        input_rad = workspace_dir / "radiograph.npz"
        input_gain = workspace_dir / "gain.npz"
        shutil.copyfile(radiograph_npz_path, input_rad)
        shutil.copyfile(gain_npz_path, input_gain)
        os.chmod(input_rad, 0o444)
        os.chmod(input_gain, 0o444)

        # Stage calibration artifact into worker workspace read-only
        staged_cal_dir = workspace_dir / "calibration"
        staged_cal_dir.mkdir(parents=True, exist_ok=True)
        for item in cal_src_dir.iterdir():
            if item.is_file():
                dest = staged_cal_dir / item.name
                shutil.copyfile(item, dest)
                os.chmod(dest, 0o444)
            elif item.is_dir():
                dest_dir = staged_cal_dir / item.name
                shutil.copytree(item, dest_dir)
                for root, dirs, files in os.walk(dest_dir):
                    for d in dirs:
                        os.chmod(Path(root) / d, 0o555)
                    for f in files:
                        os.chmod(Path(root) / f, 0o444)
                os.chmod(dest_dir, 0o555)
        os.chmod(staged_cal_dir, 0o555)

        output_tiff = output_dir / "processed.tiff"
        result_path = output_dir / "worker-result.json"

        # Technical worker arguments
        args_data = {
            "radiograph_npz_path": str(input_rad),
            "gain_npz_path": str(input_gain),
            "calibration_dir": str(staged_cal_dir),
            "expected_gain_id": None,
            "expected_detector_mode": (
                manifest.capture.detector_type if manifest.capture else None
            ),
            "expected_camera_serial": None,
            "max_rows": 16384,
            "max_cols": 16384,
            "max_pixels": 268435456,
            "output_tiff_path": str(output_tiff),
            "result_path": str(result_path),
        }

        args_path = workspace_dir / "args.json"
        with args_path.open("w", encoding="utf-8") as f_args:
            json.dump(args_data, f_args)
        os.chmod(args_path, 0o444)

        stderr_str = ""
        # Launch worker
        if env_mode == "production":
            # Production host supervisor container launcher via narrow Unix socket
            launcher_sock_path = os.getenv(
                "MPIPS_LAUNCHER_SOCKET_PATH", "/var/run/mpips-launcher.sock"
            )
            launcher_sock = Path(launcher_sock_path)
            if not launcher_sock.exists():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="CONVERSION_WORKER_FAILURE",
                )

            request_payload = (
                json.dumps(
                    {
                        "job_id": str(manifest.conversion_job_id),
                        "workspace_dir": str(workspace_dir),
                    }
                ).encode("utf-8")
                + b"\n"
            )

            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(timeout_seconds + 10)
                    sock.connect(str(launcher_sock))
                    sock.sendall(request_payload)
                    sock.shutdown(socket.SHUT_WR)

                    resp_bytes = bytearray()
                    while True:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        resp_bytes.extend(chunk)

                if not resp_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="CONVERSION_WORKER_FAILURE",
                    )

                resp_data = json.loads(resp_bytes.decode("utf-8"))
                stderr_str = resp_data.get("stderr", "")
                if resp_data.get("status") != "success":
                    if resp_data.get("exit_code") == 124:
                        raise HTTPException(
                            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                            detail="CONVERSION_TIMEOUT",
                        )
                    if not result_path.exists():
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="CONVERSION_WORKER_FAILURE",
                        )
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="CONVERSION_WORKER_FAILURE",
                ) from exc
        else:
            # Development/test adapter inheriting environment
            clean_env = dict(os.environ)
            clean_env.update(
                {
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "MPIPS_DICOM_WORKER_CPU_SECONDS": os.getenv(
                        "MPIPS_DICOM_WORKER_CPU_SECONDS", "120"
                    ),
                    "MPIPS_DICOM_WORKER_MEMORY_BYTES": os.getenv(
                        "MPIPS_DICOM_WORKER_MEMORY_BYTES",
                        str(2 * 1024 * 1024 * 1024),
                    ),
                }
            )

            venv_python = Path(sys.prefix) / "bin" / "python"
            python_bin = str(venv_python) if venv_python.exists() else sys.executable

            cmd = [
                python_bin,
                "-m",
                "mpips.conversion.worker",
                str(args_path),
                str(result_path),
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=clean_env,
                )
                _, stderr = proc.communicate(timeout=timeout_seconds)
                stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
                if stderr_str and not result_path.exists():
                    sys.stderr.write(f"Worker process stderr: {stderr_str}\n")
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
                    detail="CONVERSION_TIMEOUT",
                )

        if not result_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CONVERSION_WORKER_FAILURE",
            )

        try:
            with result_path.open("r", encoding="utf-8") as f_res:
                result_data = json.load(f_res)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CONVERSION_WORKER_FAILURE",
            ) from exc

        if result_data.get("status") != "success":
            err_code = (
                result_data.get("sanitized_error_code") or "CONVERSION_WORKER_FAILURE"
            )
            err_detail = result_data.get("error_detail")
            if err_detail or stderr_str:
                logger.error(
                    "Worker process failed [%s]: detail=%s | stderr=%s",
                    err_code,
                    err_detail,
                    stderr_str,
                )
            if err_code in ("NPZ_VALIDATION_ERROR", "MANIFEST_OR_DATA_ERROR"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=err_code,
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=err_code,
            )

        # TOCTOU-safe Parent TIFF descriptor validation & shape derivation
        _, parent_shape = _validate_tiff_descriptor(
            output_dir=output_dir,
            max_tiff_bytes=max_tiff_bytes,
        )

        # Parent DICOM conversion, enrichment, and validation
        with tempfile.TemporaryDirectory(prefix="mpips-parent-stage-") as parent_stage:
            stage_tiff = Path(parent_stage) / "processed.tiff"
            stage_json = Path(parent_stage) / "adapter.json"

            shutil.copyfile(output_tiff, stage_tiff)

            converter_dict = build_converter_metadata_json(manifest)
            with stage_json.open("w", encoding="utf-8") as f_stage:
                json.dump(converter_dict, f_stage)

            tiff_json_to_dcm(
                str(stage_tiff), str(stage_json), str(output_dicom_path)
            )  # type: ignore[no-untyped-call]
            enrich_dicom_file(output_dicom_path, manifest)

        val_res = validate_dicom_dataset(output_dicom_path, manifest, parent_shape)

        out_size = Path(output_dicom_path).stat().st_size
        return {
            "status": "success",
            "sanitized_error_code": None,
            "output_byte_size": out_size,
            "validation_flags": {
                "valid": True,
                "pixel_bytes": val_res.get("pixel_bytes", 0),
            },
        }

    finally:
        if workspace_dir.exists():
            _cleanup_workspace(workspace_dir)
