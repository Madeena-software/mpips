"""Tests for scripts/grabber_subprocess_adapter.py against mpips-runtime and
mock scenarios.
"""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

import pytest

from scripts.grabber_smoke import make_inputs
from scripts.grabber_subprocess_adapter import (
    MPIPSInputNotFoundError,
    MPIPSInvalidInputError,
    MPIPSOutputExistsError,
    MPIPSRuntimeError,
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
    assert res.output_byte_size == output.stat().st_size


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


def test_adapter_output_dangling_symlink_error(
    runtime_path: Path, tmp_path: Path
) -> None:
    rad, gain, manifest, cal = make_inputs(tmp_path / "dangling_test", "BED")
    non_existent_target = tmp_path / "dangling_test" / "target.dcm"
    symlink_output = tmp_path / "dangling_test" / "symlink_output.dcm"
    symlink_output.symlink_to(non_existent_target)

    assert symlink_output.is_symlink()
    assert not symlink_output.exists()

    adapter = MPIPSSubprocessAdapter(runtime_path)
    with pytest.raises(MPIPSOutputExistsError) as exc_info:
        adapter.convert(
            radiograph=rad,
            gain=gain,
            manifest=manifest,
            calibration=cal,
            output=symlink_output,
        )
    assert exc_info.value.exit_code == 4
    assert not non_existent_target.exists()


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


def _create_mock_script(tmp_path: Path, content: str) -> Path:
    script = tmp_path / "mock_runtime.sh"
    script.write_text(f"#!/bin/bash\n{content}\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_adapter_rejects_malformed_json_response(tmp_path: Path) -> None:
    script = _create_mock_script(tmp_path, "echo 'not valid json'")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    assert "Malformed JSON" in str(exc.value)


def test_adapter_rejects_multi_line_response(tmp_path: Path) -> None:
    line1 = (
        'echo \'{"status": "ok", "code": "OK", "interface_version": "1", '
        '"runtime_version": "0.1.0"}\''
    )
    script = _create_mock_script(tmp_path, f"{line1}\necho 'Unexpected debug line'")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    assert "single-line" in str(exc.value)


def test_adapter_rejects_missing_required_keys(tmp_path: Path) -> None:
    script = _create_mock_script(
        tmp_path,
        'echo \'{"status": "ok", "code": "OK"}\'',
    )
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    assert "Missing required response keys" in str(exc.value)


def test_adapter_rejects_incompatible_interface_version(tmp_path: Path) -> None:
    json_str = (
        '{"status": "ok", "code": "OK", "interface_version": "999", '
        '"runtime_version": "0.1.0"}'
    )
    script = _create_mock_script(tmp_path, f"echo '{json_str}'")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    assert "Unsupported" in str(exc.value)


def test_adapter_rejects_inconsistent_exit_code_and_status(tmp_path: Path) -> None:
    # Exit 0 but status error
    json0 = (
        '{"status": "error", "code": "INVALID_INPUT", "interface_version": "1", '
        '"runtime_version": "0.1.0"}'
    )
    script0 = _create_mock_script(tmp_path, f"echo '{json0}'\nexit 0")
    adapter0 = MPIPSSubprocessAdapter(script0)
    with pytest.raises(MPIPSRuntimeError) as exc0:
        adapter0.check_version()
    assert "Inconsistent" in str(exc0.value)

    # Exit 2 but status ok
    json2 = (
        '{"status": "ok", "code": "OK", "interface_version": "1", '
        '"runtime_version": "0.1.0"}'
    )
    script2 = _create_mock_script(tmp_path, f"echo '{json2}'\nexit 2")
    adapter2 = MPIPSSubprocessAdapter(script2)
    with pytest.raises(MPIPSRuntimeError) as exc2:
        adapter2.check_version()
    assert "Inconsistent" in str(exc2.value)


def test_adapter_timeout_enforcement_and_cleanup(tmp_path: Path) -> None:
    # Simulates a hang/sleep
    json_ok = (
        '{"status": "ok", "code": "OK", "interface_version": "1", '
        '"runtime_version": "0.1.0"}'
    )
    script = _create_mock_script(tmp_path, f"sleep 10\necho '{json_ok}'")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSTimeoutError) as exc_info:
        adapter.check_version(timeout=0.2)
    assert exc_info.value.exit_code == 5


def test_adapter_rejects_malicious_or_leaking_response(tmp_path: Path) -> None:
    # Malicious response attempting to inject arbitrary strings or paths
    malicious_json = (
        '{"status": "error", "code": "<script>alert(1)</script>", '
        '"interface_version": "1", "runtime_version": "0.1.0", '
        '"private_path": "/var/data/patient_001.npz"}'
    )
    script = _create_mock_script(tmp_path, f"echo '{malicious_json}'\nexit 2")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    # Ensure error message does not reflect malicious string or path
    err_str = str(exc.value)
    assert "<script>" not in err_str
    assert "patient_001" not in err_str
    assert "expected status=error, code=INVALID_INPUT" in err_str


@pytest.mark.parametrize(
    ("exit_code", "wrong_code"),
    [
        (2, "IO_ERROR"),
        (3, "INVALID_INPUT"),
        (4, "CONVERSION_FAILED"),
        (5, "OK"),
        (6, "INPUT_NOT_FOUND"),
        (7, "OUTPUT_EXISTS"),
    ],
)
def test_adapter_validates_all_supported_exit_code_mappings(
    tmp_path: Path, exit_code: int, wrong_code: str
) -> None:
    json_wrong = (
        f'{{"status": "error", "code": "{wrong_code}", '
        f'"interface_version": "1", "runtime_version": "0.1.0"}}'
    )
    script = _create_mock_script(tmp_path, f"echo '{json_wrong}'\nexit {exit_code}")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    assert "Inconsistent response for exit" in str(exc.value)


def test_adapter_accepts_experimental_interface_version(tmp_path: Path) -> None:
    json_str = (
        '{"status": "ok", "code": "OK", "interface_version": "2-experimental", '
        '"runtime_version": "0.1.0"}'
    )
    script = _create_mock_script(tmp_path, f"echo '{json_str}'")
    adapter = MPIPSSubprocessAdapter(script)
    info = adapter.check_version()
    assert info.interface_version == "2-experimental"
    assert info.status == "ok"
    assert info.code == "OK"


def test_adapter_convert_experimental_without_calibration_arg(tmp_path: Path) -> None:
    # Verifies that convert() without calibration argument emits exactly 4 flags
    # and handles 2-experimental response correctly
    script_record = tmp_path / "cmd.txt"
    json_resp = (
        '{"status": "ok", "code": "OK", "interface_version": "2-experimental", '
        '"runtime_version": "0.1.0", "output_byte_size": 1234}'
    )
    mock_body = f"""if [ "$1" = "--version" ]; then
    echo '{json_resp}'
else
    echo "$@" > "{script_record}"
    touch "${{@: -1}}"
    echo '{json_resp}'
fi
"""
    script = _create_mock_script(tmp_path, mock_body)
    rad = tmp_path / "rad.npz"
    gain = tmp_path / "gain.npz"
    manifest = tmp_path / "man.json"
    out = tmp_path / "out.dcm"
    rad.write_bytes(b"dummy")
    gain.write_bytes(b"dummy")
    manifest.write_bytes(b"dummy")

    adapter = MPIPSSubprocessAdapter(script)
    res = adapter.convert(
        radiograph=rad,
        gain=gain,
        manifest=manifest,
        output=out,
    )
    assert res.status == "ok"
    assert res.interface_version == "2-experimental"
    recorded_args = script_record.read_text()
    assert "--calibration" not in recorded_args
    assert "--radiograph" in recorded_args
    assert "--gain" in recorded_args
    assert "--manifest" in recorded_args
    assert "--output" in recorded_args


def test_adapter_convert_interface_1_rejects_missing_calibration(
    tmp_path: Path,
) -> None:
    rad = tmp_path / "rad.npz"
    gain = tmp_path / "gain.npz"
    manifest = tmp_path / "man.json"
    out = tmp_path / "out.dcm"
    rad.write_bytes(b"dummy")
    gain.write_bytes(b"dummy")
    manifest.write_bytes(b"dummy")

    script = _create_mock_script(tmp_path, 'echo \'{"status":"ok"}\'')
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSInvalidInputError) as exc_info:
        adapter.convert(
            radiograph=rad,
            gain=gain,
            manifest=manifest,
            output=out,
            expected_interface_version="1",
        )
    assert "Interface 1 requires explicit calibration directory" in str(exc_info.value)


def test_adapter_rejects_untrusted_interface_version_without_reflection(
    tmp_path: Path,
) -> None:
    malicious_ver = "<script>alert('pwned')</script>"
    json_str = (
        f'{{"status": "ok", "code": "OK", "interface_version": "{malicious_ver}", '
        f'"runtime_version": "0.1.0"}}'
    )
    script = _create_mock_script(tmp_path, f"echo '{json_str}'")
    adapter = MPIPSSubprocessAdapter(script)
    with pytest.raises(MPIPSRuntimeError) as exc:
        adapter.check_version()
    # Ensure raw string was not reflected in error
    assert "<script>" not in str(exc.value)
    assert "Unsupported" in str(exc.value)


def test_resource_limits_fallback_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    from mpips.conversion.worker import _apply_startup_resource_limits

    # On Linux, verify that an OSError in setrlimit raises RuntimeError
    monkeypatch.setattr("sys.platform", "linux")
    try:
        import resource

        def mock_setrlimit(res: int, limits: tuple[int, int]) -> None:
            raise OSError("Operation not permitted")

        monkeypatch.setattr(resource, "setrlimit", mock_setrlimit)
        with pytest.raises(RuntimeError) as exc:
            _apply_startup_resource_limits()
        assert "Failed to set RLIMIT_CPU on Linux" in str(exc.value)
    except ImportError:
        pass
