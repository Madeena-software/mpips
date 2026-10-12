import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mpips.runtime", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "MPIPS_ENVIRONMENT": "production"},
    )


def test_version_is_machine_readable() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["interface_version"] == "1"
    assert report["runtime_version"]
    assert result.stderr == ""


def test_arguments_are_sanitized() -> None:
    result = run_cli("convert", "--patient-secret")
    assert result.returncode == 2
    assert json.loads(result.stdout)["code"] == "INVALID_INPUT"
    assert "patient-secret" not in result.stdout + result.stderr


def test_missing_input_preserves_destination(tmp_path: Path) -> None:
    output = tmp_path / "result.dcm"
    result = run_cli(
        "convert",
        "--radiograph",
        str(tmp_path / "missing"),
        "--gain",
        str(tmp_path / "gain"),
        "--manifest",
        str(tmp_path / "manifest"),
        "--calibration",
        str(tmp_path / "calibration"),
        "--output",
        str(output),
    )
    assert result.returncode == 3
    assert json.loads(result.stdout)["code"] == "INPUT_NOT_FOUND"
    assert not output.exists()
    assert result.stderr == ""
    output.write_bytes(b"existing examination")
    result = run_cli(
        "convert",
        "--radiograph",
        "missing",
        "--gain",
        "missing",
        "--manifest",
        "missing",
        "--calibration",
        "missing",
        "--output",
        str(output),
    )
    assert result.returncode == 4
    assert output.read_bytes() == b"existing examination"


@pytest.mark.parametrize("mode", ["BED", "TRX"])
def test_real_cli_synthetic_conversion(tmp_path: Path, mode: str) -> None:
    from scripts.grabber_smoke import make_inputs, verify_output

    rad, gain, manifest, calibration = make_inputs(tmp_path, mode)
    output = tmp_path / "image.dcm"
    result = run_cli(
        "convert",
        "--radiograph",
        str(rad),
        "--gain",
        str(gain),
        "--manifest",
        str(manifest),
        "--calibration",
        str(calibration),
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "ok"
    assert result.stderr == ""
    verify_output(output, mode)
    assert not list(tmp_path.glob(".mpips-*"))


def test_manifest_error_does_not_leak_patient_data(tmp_path: Path) -> None:
    from scripts.grabber_smoke import make_inputs

    rad, gain, manifest, calibration = make_inputs(tmp_path, "BED")
    data = json.loads(manifest.read_text())
    data["patient"]["sex"] = "SENSITIVE_INVALID_VALUE"
    manifest.write_text(json.dumps(data))
    result = run_cli(
        "convert",
        "--radiograph",
        str(rad),
        "--gain",
        str(gain),
        "--manifest",
        str(manifest),
        "--calibration",
        str(calibration),
        "--output",
        str(tmp_path / "bad.dcm"),
    )
    assert result.returncode == 2
    assert "SENSITIVE" not in result.stdout + result.stderr
    assert not (tmp_path / "bad.dcm").exists()


@pytest.mark.parametrize(
    "failure,exit_code,code",
    [
        (TimeoutError, 5, "CONVERSION_TIMEOUT"),
        (PermissionError, 6, "IO_ERROR"),
        (RuntimeError, 7, "CONVERSION_FAILED"),
    ],
)
def test_runtime_failure_codes_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: type[Exception],
    exit_code: int,
    code: str,
) -> None:
    import mpips
    from mpips.runtime import main
    from scripts.grabber_smoke import make_inputs

    rad, gain, manifest, cal = make_inputs(tmp_path, "BED")
    output = tmp_path / "result.dcm"

    def fail(*args: object, **kwargs: object) -> None:
        raise failure("SENSITIVE FAILURE")

    monkeypatch.setattr(mpips, "convert_npz_to_dicom", fail)
    assert (
        main(
            [
                "convert",
                "--radiograph",
                str(rad),
                "--gain",
                str(gain),
                "--manifest",
                str(manifest),
                "--calibration",
                str(cal),
                "--output",
                str(output),
            ]
        )
        == exit_code
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["code"] == code
    assert "SENSITIVE" not in captured.out + captured.err
    assert not output.exists()
    assert not list(tmp_path.glob(".mpips-*"))


def test_destination_created_during_conversion_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from mpips.runtime import main
    from scripts.grabber_smoke import make_inputs

    rad, gain, manifest, cal = make_inputs(tmp_path, "BED")
    output = tmp_path / "result.dcm"
    real_link = os.link

    def race(source: str, destination: str) -> None:
        output.write_bytes(b"another completed examination")
        real_link(source, destination)

    monkeypatch.setattr(os, "link", race)
    assert (
        main(
            [
                "convert",
                "--radiograph",
                str(rad),
                "--gain",
                str(gain),
                "--manifest",
                str(manifest),
                "--calibration",
                str(cal),
                "--output",
                str(output),
            ]
        )
        == 4
    )
    assert json.loads(capsys.readouterr().out)["code"] == "OUTPUT_EXISTS"
    assert output.read_bytes() == b"another completed examination"
