"""Typed CLI entrypoint for MHCS Core Grabber round-trip workflow.

Accepts references to radiograph NPZ, gain NPZ, output/work directory,
and locator supplied via protected local configuration or arguments.

Outputs only sanitized operational results — never exposes credentials,
patient identity fields, DICOM bytes, or raw response bodies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from mpips.integrations.mhcs_core.workflow import (
    GrabberWorkflowResult,
    run_grabber_roundtrip,
)


def load_protected_environment(
    env_file: Path | str | None = None,
    token_file: Path | str | None = None,
    override: bool = False,
) -> None:
    """Load configuration from environment and optional protected files safely.

    Does not print, log, or expose secret values.
    """
    if env_file:
        p = Path(env_file).resolve()
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    if key and (override or key not in os.environ):
                        os.environ[key] = value.strip()

    if token_file:
        tp = Path(token_file).resolve()
        if tp.is_file():
            raw_token = tp.read_text(encoding="utf-8").strip()
            if raw_token:
                os.environ["MHCS_GRABBER_TOKEN"] = raw_token


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute the MHCS Core Grabber round-trip workflow.",
        prog="mpips-grabber",
    )
    parser.add_argument(
        "--radiograph",
        "-r",
        type=Path,
        required=True,
        help="Path to the radiograph NPZ file.",
    )
    parser.add_argument(
        "--gain",
        "-g",
        type=Path,
        required=True,
        help="Path to the gain calibration NPZ file.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        required=True,
        help="Directory to store generated Part 10 DICOM file.",
    )
    parser.add_argument(
        "--work-dir",
        "-w",
        type=Path,
        default=None,
        help="Private work directory for sidecars (defaults to <output_dir>/work).",
    )
    parser.add_argument(
        "--locator",
        "-l",
        type=str,
        default=None,
        help="Four-digit session locator (defaults to MHCS_GRABBER_REHEARSAL_LOCATOR).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional path to protected environment file.",
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=None,
        help="Optional path to protected token file.",
    )
    parser.add_argument(
        "--calibration-dir",
        type=Path,
        default=None,
        help="Optional calibration directory for the converter.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="MHCS Core base URL (defaults to MHCS_GRABBER_BASE_URL).",
    )

    resume_group = parser.add_mutually_exclusive_group()
    resume_group.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        default=None,
        help="Require resume from existing verified DICOM and sidecar.",
    )
    resume_group.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Force fresh manifest lookup and conversion without resuming.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output sanitized result in JSON format.",
    )

    return parser.parse_args(argv)


def _format_sanitized_result(
    result: GrabberWorkflowResult, as_json: bool = False
) -> str:
    """Format operational result without patient data or credentials."""
    payload = {
        "status": "success",
        "terminal_state": result.terminal_state,
        "replayed": result.replayed,
        "bytes": result.bytes,
        "checksum": result.checksum,
        "locator_code": result.locator_code,
    }
    if as_json:
        return json.dumps(payload, indent=2)

    lines = [
        "MHCS Core Grabber Round-Trip: SUCCESS",
        f"  status: {payload['status']}",
        f"  terminal_state: {payload['terminal_state']}",
        f"  replayed: {payload['replayed']}",
        f"  bytes: {payload['bytes']}",
        f"  checksum: {payload['checksum']}",
        f"  locator_code: {payload['locator_code']}",
    ]
    return "\n".join(lines)


def _format_sanitized_error(exc: Exception, as_json: bool = False) -> str:
    """Format sanitized error without leaking sensitive context."""
    error_class = type(exc).__name__
    payload = {
        "status": "error",
        "error_class": error_class,
    }
    if as_json:
        return json.dumps(payload, indent=2)
    return (
        f"MHCS Core Grabber Round-Trip: ERROR\n"
        f"  status: {payload['status']}\n"
        f"  error_class: {payload['error_class']}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        load_protected_environment(
            env_file=args.env_file,
            token_file=args.token_file,
        )

        if args.base_url:
            os.environ["MHCS_GRABBER_BASE_URL"] = args.base_url

        locator = args.locator or os.environ.get("MHCS_GRABBER_REHEARSAL_LOCATOR")
        if not locator:
            raise ValueError(
                "Locator code must be specified via --locator or "
                "MHCS_GRABBER_REHEARSAL_LOCATOR environment variable."
            )

        if not os.environ.get("MHCS_GRABBER_BASE_URL"):
            raise ValueError("MHCS_GRABBER_BASE_URL environment variable is not set.")

        if not os.environ.get("MHCS_GRABBER_TOKEN"):
            raise ValueError("MHCS_GRABBER_TOKEN environment variable is not set.")

        output_dir = Path(args.output_dir).resolve()
        work_dir = (
            Path(args.work_dir).resolve() if args.work_dir else output_dir / "work"
        )

        result = run_grabber_roundtrip(
            locator_code=locator,
            radiograph_npz_path=args.radiograph,
            gain_npz_path=args.gain,
            output_dicom_dir=output_dir,
            work_dir=work_dir,
            calibration_dir=args.calibration_dir,
            resume=args.resume,
        )

        print(_format_sanitized_result(result, as_json=args.json))
        return 0

    except Exception as exc:
        print(_format_sanitized_error(exc, as_json=args.json), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
