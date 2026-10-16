"""Tests for scripts/grabber_subprocess_adapter.py against mpips-runtime."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from scripts.grabber_smoke import make_inputs
from scripts.grabber_subprocess_adapter import (
    MPIPSConversionFailedError,
    MPIPSInputNotFoundError,
    MPIPSInvalidInputError,
    MPIPSOutputExistsError,
    MPIPSSubprocessAdapter,
    MPIPSTimeoutError,
)


@pytest.fixture
def runtime_path() -> Path:
    exe = shutil.which("mpips-runtime")
    if exe is None:
        venv_exe = Path(__file__).resolve().parents[1] / ".venv/bin/mpips-runtime"
        if venv_exe.exists():
            return venv_exe
        pytest.skip("mpips-runtime executable not found in PATH or .venv")
    return Path(exe)


def test_adapter_check_version(runtime_path: Path) -> None:
    adapter = MPIPSSubprocessAdapter(runtime_path)
    info = adapter.check_version()
    assert info.interface_version == "1"
    assert info.runtime_version == "0.1.0"
    assert info.status == "ok"
    assert info.code == "OK"


def test_adapter_convert_bed_synthetic(runtime_path: Path, tmp_path: Path) -> None:
    rad, gain, manifest, cal = make_inputs(tmp_path / "bed_test", "BED")
    output = tmp_path / "bed_test" / "result.dcm"

    adapter = MPIPSSubprocessAdapter(runtime_path)
    res = adapter.convert(
        radiograph=rad,
        gain=gain,
        manifest=manifest,
        calibration=cal,
        output=output,
    )
    assert res.status == "ok"
    assert res.code == "OK"
    assert res.output_path == output
    assert output.is_file()
    assert output.stat().st_size > 0


def test_adapter_convert_trx_synthetic(runtime_path: Path, tmp_path: Path) -> None:
    rad, gain, manifest, cal = make_inputs(tmp_path / "trx_test", "TRX")
    output = tmp_path / "trx_test" / "result.dcm"

    adapter = MPIPSSubprocessAdapter(runtime_path)
    res = adapter.convert(
        radiograph=rad,
        gain=gain,
        manifest=manifest,
        calibration=cal,
        output=output,
    )
    assert res.status == "ok"
    assert res.code == "OK"
    assert res.output_path == output
    assert output.is_file()
    assert output.stat().st_size > 0


def test_adapter_output_exists_error(runtime_path: Path, tmp_path: Path) -> None:
    rad, gain, manifest, cal = make_inputs(tmp_path / "out_exists", "BED")
    output = tmp_path / "out_exists" / "existing.dcm"
    output.write_bytes(b"dummy")

    adapter = MPIPSSubprocessAdapter(runtime_path)
    with pytest.raises(MPIPSOutputExistsError) as exc_info:
        adapter.convert(
            radiograph=rad,
            gain=gain,
            manifest=manifest,
            calibration=cal,
            output=output,
        )
    assert exc_info.value.exit_code == 4


def test_adapter_missing_input_error(runtime_path: Path, tmp_path: Path) -> None:
    cal = tmp_path / "cal"
    cal.mkdir()
    adapter = MPIPSSubprocessAdapter(runtime_path)
    with pytest.raises(MPIPSInputNotFoundError) as exc_info:
        adapter.convert(
            radiograph=tmp_path / "missing_rad.npz",
            gain=tmp_path / "missing_gain.npz",
            manifest=tmp_path / "missing_manifest.json",
            calibration=cal,
            output=tmp_path / "out.dcm",
        )
    assert exc_info.value.exit_code == 3


def test_adapter_invalid_input_error(runtime_path: Path, tmp_path: Path) -> None:
    rad, gain, manifest, cal = make_inputs(tmp_path / "bad_man", "BED")
    manifest.write_text("{invalid-json-content")
    output = tmp_path / "bad_man" / "out.dcm"

    adapter = MPIPSSubprocessAdapter(runtime_path)
    with pytest.raises(MPIPSInvalidInputError) as exc_info:
        adapter.convert(
            radiograph=rad,
            gain=gain,
            manifest=manifest,
            calibration=cal,
            output=output,
        )
    assert exc_info.value.exit_code == 2
