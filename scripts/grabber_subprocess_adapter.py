"""Minimal, robust Python subprocess adapter for invoking mpips-runtime convert.

Designed for embedding in a separately developed, local Grabber application.
- Uses argument vectors (NO shell string interpolation).
- Validates exit codes and decodes single-record JSON status on stdout.
- Enforces timeout limits and cleans up child processes.
- Never logs or exposes patient metadata in error messages.
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
        self.response = response or {}


class MPIPSInvalidInputError(MPIPSRuntimeError):
    """Raised when the runtime reports INVALID_INPUT (exit code 2)."""


class MPIPSInputNotFoundError(MPIPSRuntimeError):
    """Raised when input NPZ, manifest, or calibration path is missing (exit code 3)."""


class MPIPSOutputExistsError(MPIPSRuntimeError):
    """Raised when the requested destination DICOM path already exists (exit code 4)."""


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
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MPIPSTimeoutError(
                "Runtime check timed out", response={"error": str(exc)}
            ) from exc

        if res.returncode != 0:
            raise MPIPSRuntimeError(
                f"Runtime check failed with exit code {res.returncode}",
                exit_code=res.returncode,
            )

        try:
            data = json.loads(res.stdout.strip())
        except json.JSONDecodeError as exc:
            raise MPIPSRuntimeError(
                "Malformed JSON response from runtime", exit_code=res.returncode
            ) from exc

        return RuntimeInfo(
            interface_version=str(data.get("interface_version", "")),
            runtime_version=str(data.get("runtime_version", "")),
            status=str(data.get("status", "")),
            code=str(data.get("code", "")),
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
            output: Path where output DICOM should be created (must not exist)
            timeout: Subprocess timeout in seconds
        """
        rad_p = Path(radiograph).resolve()
        gain_p = Path(gain).resolve()
        man_p = Path(manifest).resolve()
        cal_p = Path(calibration).resolve()
        out_p = Path(output).resolve()

        # Pre-flight sanity checks to fail fast without leaking private paths
        if out_p.exists():
            raise MPIPSOutputExistsError(
                f"Destination DICOM output already exists: {out_p.name}", exit_code=4
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

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MPIPSTimeoutError(
                f"Conversion timed out after {timeout} seconds",
                exit_code=5,
                response={"error": "subprocess_timeout"},
            ) from exc

        parsed_json: dict[str, Any] = {}
        if res.stdout.strip():
            try:
                parsed_json = json.loads(res.stdout.strip())
            except json.JSONDecodeError:
                parsed_json = {"raw_stdout": res.stdout.strip()}

        if res.returncode == 0:
            if parsed_json.get("status") != "ok":
                raise MPIPSRuntimeError(
                    "Unexpected status in exit-0 response: "
                    f"{parsed_json.get('status')}",
                    exit_code=0,
                    response=parsed_json,
                )
            if not out_p.is_file():
                raise MPIPSIOError(
                    "Runtime succeeded but output DICOM is not present", exit_code=6
                )

            return ConversionResult(
                status=str(parsed_json.get("status")),
                code=str(parsed_json.get("code")),
                interface_version=str(parsed_json.get("interface_version")),
                runtime_version=str(parsed_json.get("runtime_version")),
                output_path=out_p,
                raw_response=parsed_json,
            )

        # Handle specific error exit codes
        code_str = parsed_json.get("code", "")
        msg = f"Runtime failed with exit code {res.returncode} (code={code_str})"

        if res.returncode == 2:
            raise MPIPSInvalidInputError(msg, exit_code=2, response=parsed_json)
        if res.returncode == 3:
            raise MPIPSInputNotFoundError(msg, exit_code=3, response=parsed_json)
        if res.returncode == 4:
            raise MPIPSOutputExistsError(msg, exit_code=4, response=parsed_json)
        if res.returncode == 5:
            raise MPIPSTimeoutError(msg, exit_code=5, response=parsed_json)
        if res.returncode == 6:
            raise MPIPSIOError(msg, exit_code=6, response=parsed_json)
        if res.returncode == 7:
            raise MPIPSConversionFailedError(msg, exit_code=7, response=parsed_json)

        raise MPIPSRuntimeError(msg, exit_code=res.returncode, response=parsed_json)
