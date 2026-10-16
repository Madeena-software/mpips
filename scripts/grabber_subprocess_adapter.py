"""Minimal, robust Python subprocess adapter for invoking mpips-runtime convert.

Designed for embedding in a separately developed, local Grabber application.
- Uses argument vectors (NO shell string interpolation).
- Validates exit codes and decodes single-record JSON status on stdout.
- Rejects existing outputs and dangling symlinks before path resolution.
- Enforces strict response verification and fails closed on incompatible interfaces.
- Enforces timeout limits and cleans up child processes.
- Never logs or exposes raw stdout or patient metadata in exceptions.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

DEFAULT_CONVERT_TIMEOUT_SECONDS = 300.0
SUPPORTED_INTERFACE_VERSION = "1"
SUPPORTED_EXIT_CODES = {0, 2, 3, 4, 5, 6, 7}


class MPIPSRuntimeError(RuntimeError):
    """Base exception for mpips-runtime invocation failures."""

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        response: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.response = dict(response) if response else {}


class MPIPSInvalidInputError(MPIPSRuntimeError):
    """Raised when the runtime reports INVALID_INPUT (exit code 2)."""


class MPIPSInputNotFoundError(MPIPSRuntimeError):
    """Raised when input NPZ, manifest, or calibration path is missing (exit code 3)."""


class MPIPSOutputExistsError(MPIPSRuntimeError):
    """Raised when destination DICOM path already exists or is a symlink (exit 4)."""


class MPIPSTimeoutError(MPIPSRuntimeError):
    """Raised when conversion times out (exit code 5 or subprocess timeout)."""


class MPIPSIOError(MPIPSRuntimeError):
    """Raised on storage or filesystem failure (exit code 6)."""


class MPIPSConversionFailedError(MPIPSRuntimeError):
    """Raised on algorithmic or processing failure (exit code 7)."""


@dataclass(frozen=True)
class RuntimeInfo:
    interface_version: str
    runtime_version: str
    status: str
    code: str


@dataclass(frozen=True)
class ConversionResult:
    status: str
    code: str
    interface_version: str
    runtime_version: str
    output_path: Path
    output_byte_size: int | None
    raw_response: dict[str, Any]


class MPIPSSubprocessAdapter:
    """Invokes local mpips-runtime CLI via subprocess."""

    def __init__(self, runtime_executable: Path | str) -> None:
        self.runtime_executable = Path(runtime_executable).resolve()
        if not self.runtime_executable.is_file():
            raise FileNotFoundError(
                f"Runtime executable not found: {self.runtime_executable}"
            )

    def check_version(self, timeout: float = 10.0) -> RuntimeInfo:
        """Query runtime interface and version without executing conversion."""
        cmd = [str(self.runtime_executable), "--version"]
        proc: subprocess.Popen[str] | None = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_data, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            if proc is not None:
                proc.kill()
                proc.wait()
            raise MPIPSTimeoutError(
                "Runtime check timed out",
                exit_code=5,
                response={"code": "TIMEOUT"},
            ) from exc

        data = self._parse_and_validate_response(
            stdout_data, expected_exit=proc.returncode
        )

        if proc.returncode != 0:
            raise MPIPSRuntimeError(
                f"Runtime check failed with exit code {proc.returncode}",
                exit_code=proc.returncode,
                response=data,
            )

        if data.get("interface_version") != SUPPORTED_INTERFACE_VERSION:
            raise MPIPSRuntimeError(
                f"Unsupported interface version: {data.get('interface_version')}",
                exit_code=proc.returncode,
                response=data,
            )

        return RuntimeInfo(
            interface_version=str(data["interface_version"]),
            runtime_version=str(data["runtime_version"]),
            status=str(data["status"]),
            code=str(data["code"]),
        )

    def convert(
        self,
        *,
        radiograph: Path | str,
        gain: Path | str,
        manifest: Path | str,
        calibration: Path | str,
        output: Path | str,
        timeout: float = DEFAULT_CONVERT_TIMEOUT_SECONDS,
    ) -> ConversionResult:
        """Execute mpips-runtime convert with arguments vector.

        Parameters:
            radiograph: Path to acquisition radiograph.npz
            gain: Path to matching gain.npz
            manifest: Path to MHCSManifest JSON file
            calibration: Directory of validated detector calibration
            output: Path where output DICOM should be created (must not exist or
                be symlink)
            timeout: Subprocess timeout in seconds
        """
        raw_out = Path(output)
        # Check exists and is_symlink BEFORE resolving to prevent following
        # dangling symlinks
        if raw_out.exists() or raw_out.is_symlink():
            raise MPIPSOutputExistsError(
                "Destination DICOM output already exists or is a symlink: "
                f"{raw_out.name}",
                exit_code=4,
                response={"code": "OUTPUT_EXISTS"},
            )

        rad_p = Path(radiograph).resolve()
        gain_p = Path(gain).resolve()
        man_p = Path(manifest).resolve()
        cal_p = Path(calibration).resolve()
        out_p = raw_out.resolve()

        # Re-check resolved output path as well
        if out_p.exists() or out_p.is_symlink():
            raise MPIPSOutputExistsError(
                f"Destination DICOM output already exists: {out_p.name}",
                exit_code=4,
                response={"code": "OUTPUT_EXISTS"},
            )

        if not rad_p.is_file():
            raise MPIPSInputNotFoundError("Radiograph file does not exist", exit_code=3)
        if not gain_p.is_file():
            raise MPIPSInputNotFoundError("Gain file does not exist", exit_code=3)
        if not man_p.is_file():
            raise MPIPSInputNotFoundError("Manifest file does not exist", exit_code=3)
        if not cal_p.is_dir():
            raise MPIPSInputNotFoundError(
                "Calibration directory does not exist", exit_code=3
            )

        cmd = [
            str(self.runtime_executable),
            "convert",
            "--radiograph",
            str(rad_p),
            "--gain",
            str(gain_p),
            "--manifest",
            str(man_p),
            "--calibration",
            str(cal_p),
            "--output",
            str(out_p),
        ]

        proc: subprocess.Popen[str] | None = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_data, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            if proc is not None:
                proc.kill()
                proc.wait()
            raise MPIPSTimeoutError(
                f"Conversion timed out after {timeout} seconds",
                exit_code=5,
                response={"code": "CONVERSION_TIMEOUT"},
            ) from exc

        parsed_json = self._parse_and_validate_response(
            stdout_data, expected_exit=proc.returncode
        )

        if proc.returncode == 0:
            if not out_p.is_file():
                raise MPIPSIOError(
                    "Runtime succeeded but output DICOM is not present",
                    exit_code=6,
                    response=parsed_json,
                )

            return ConversionResult(
                status=str(parsed_json["status"]),
                code=str(parsed_json["code"]),
                interface_version=str(parsed_json["interface_version"]),
                runtime_version=str(parsed_json["runtime_version"]),
                output_path=out_p,
                output_byte_size=parsed_json.get("output_byte_size"),
                raw_response=parsed_json,
            )

        # Handle specific error exit codes
        code_str = str(parsed_json.get("code", "UNKNOWN"))
        msg = f"Runtime failed with exit code {proc.returncode} (code={code_str})"

        if proc.returncode == 2:
            raise MPIPSInvalidInputError(msg, exit_code=2, response=parsed_json)
        if proc.returncode == 3:
            raise MPIPSInputNotFoundError(msg, exit_code=3, response=parsed_json)
        if proc.returncode == 4:
            raise MPIPSOutputExistsError(msg, exit_code=4, response=parsed_json)
        if proc.returncode == 5:
            raise MPIPSTimeoutError(msg, exit_code=5, response=parsed_json)
        if proc.returncode == 6:
            raise MPIPSIOError(msg, exit_code=6, response=parsed_json)
        if proc.returncode == 7:
            raise MPIPSConversionFailedError(msg, exit_code=7, response=parsed_json)

        raise MPIPSRuntimeError(msg, exit_code=proc.returncode, response=parsed_json)

    def _parse_and_validate_response(
        self, stdout_data: str, expected_exit: int
    ) -> dict[str, Any]:
        """Safely parse single-line JSON stdout and validate semantic contract."""
        stripped = stdout_data.strip()
        if not stripped:
            raise MPIPSRuntimeError(
                f"Empty response from runtime (exit {expected_exit})",
                exit_code=expected_exit,
            )

        lines = stripped.splitlines()
        if len(lines) != 1:
            raise MPIPSRuntimeError(
                f"Expected single-line JSON response, got {len(lines)} lines",
                exit_code=expected_exit,
            )

        try:
            data = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise MPIPSRuntimeError(
                "Malformed JSON response from runtime",
                exit_code=expected_exit,
            ) from exc

        if not isinstance(data, dict):
            raise MPIPSRuntimeError(
                f"Expected JSON object response, got {type(data).__name__}",
                exit_code=expected_exit,
            )

        # Validate required fields
        required_keys = {"interface_version", "runtime_version", "status", "code"}
        missing = required_keys - set(data.keys())
        if missing:
            raise MPIPSRuntimeError(
                f"Missing required response keys: {sorted(missing)}",
                exit_code=expected_exit,
            )

        if data.get("interface_version") != SUPPORTED_INTERFACE_VERSION:
            raise MPIPSRuntimeError(
                "Unsupported runtime interface version: "
                f"{data.get('interface_version')}",
                exit_code=expected_exit,
                response={"code": "INCOMPATIBLE_INTERFACE"},
            )

        status = data.get("status")
        code = data.get("code")

        if expected_exit == 0:
            if status != "ok" or code != "OK":
                raise MPIPSRuntimeError(
                    f"Inconsistent exit-0 status/code: status={status}, code={code}",
                    exit_code=0,
                )
        else:
            if status != "error":
                raise MPIPSRuntimeError(
                    f"Inconsistent error status: status={status} for exit "
                    f"{expected_exit}",
                    exit_code=expected_exit,
                )

        return data
