"""Entrypoint for standalone mpips-runtime ELF executable / frozen directory.

Features:
- Exposes `convert` without requiring `--calibration` (resolves embedded
  calibration profile).
- Also supports `--calibration` if provided.
- Dispatches `_internal_worker` sub-process invocation in frozen mode.
- Preserves exact JSON status response format.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Never, Sequence

from mpips import __version__

# Interface version for standalone binary without required calibration argument
INTERFACE_VERSION = "2-experimental"


class RuntimeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ValueError("INVALID_INPUT")


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Handle internal worker dispatch first (for frozen execution)
    if argv and argv[0] == "_internal_worker":
        if len(argv) != 3:
            return 1
        from mpips.conversion.worker import (
            _apply_startup_resource_limits,
            execute_conversion_worker,
        )

        try:
            _apply_startup_resource_limits()
        except Exception:
            pass
        execute_conversion_worker(argv[1], argv[2])
        return 0

    parser = RuntimeParser(description=__doc__)
    parser.add_argument("--version", action="store_true")
    commands = parser.add_subparsers(dest="command")
    convert = commands.add_parser("convert")
    for name in ("radiograph", "gain", "manifest", "output"):
        convert.add_argument(f"--{name}", required=True, type=Path)
    # --calibration is OPTIONAL in standalone binary
    convert.add_argument("--calibration", required=False, type=Path, default=None)

    report: dict[str, object] = {
        "interface_version": INTERFACE_VERSION,
        "runtime_version": __version__,
        "status": "ok",
        "code": "OK",
    }
    exit_code = 0
    try:
        args = parser.parse_args(argv)
        if args.version and args.command is None:
            pass
        elif args.command != "convert" or args.version:
            raise ValueError("INVALID_INPUT")
        else:
            output = args.output.absolute()
            if output.exists() or output.is_symlink():
                raise FileExistsError
            for path in (args.radiograph, args.gain, args.manifest):
                if not path.is_file():
                    raise FileNotFoundError
            if args.calibration is not None and not args.calibration.is_dir():
                raise FileNotFoundError

            output.parent.mkdir(parents=True, exist_ok=True)
            with (
                tempfile.TemporaryDirectory(
                    prefix=".mpips-", dir=output.parent
                ) as stage,
                open(os.devnull, "w") as quiet,
            ):
                old_env = {
                    key: os.environ.get(key)
                    for key in ("MPIPS_ENVIRONMENT", "MPIPS_WORKSPACE_ROOT")
                }
                old_logging = logging.root.manager.disable
                old_umask = os.umask(0o077)
                try:
                    os.environ["MPIPS_ENVIRONMENT"] = "development"
                    os.environ["MPIPS_WORKSPACE_ROOT"] = str(Path(stage) / "workers")
                    logging.disable(logging.CRITICAL)
                    with (
                        contextlib.redirect_stdout(quiet),
                        contextlib.redirect_stderr(quiet),
                    ):
                        from mpips import convert_npz_to_dicom

                        staged = convert_npz_to_dicom(
                            args.radiograph,
                            args.gain,
                            args.manifest,
                            Path(stage) / "result.dcm",
                            calibration_dir=args.calibration,
                        )
                    os.chmod(staged, 0o600)
                    os.link(staged, output)
                finally:
                    os.umask(old_umask)
                    logging.disable(old_logging)
                    for key, value in old_env.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value
            report["output_byte_size"] = output.stat().st_size
    except ValueError:
        exit_code, report["code"] = 2, "INVALID_INPUT"
    except FileNotFoundError:
        exit_code, report["code"] = 3, "INPUT_NOT_FOUND"
    except FileExistsError:
        exit_code, report["code"] = 4, "OUTPUT_EXISTS"
    except TimeoutError:
        exit_code, report["code"] = 5, "CONVERSION_TIMEOUT"
    except OSError:
        exit_code, report["code"] = 6, "IO_ERROR"
    except Exception:
        exit_code, report["code"] = 7, "CONVERSION_FAILED"

    if exit_code:
        report["status"] = "error"
    print(json.dumps(report, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
