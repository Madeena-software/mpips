"""Unit tests for the typed MHCS Core Grabber CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mpips.integrations.mhcs_core.cli import (
    _format_sanitized_error,
    _format_sanitized_result,
    load_protected_environment,
    main,
    parse_args,
)
from mpips.integrations.mhcs_core.client import GrabberAuthError
from mpips.integrations.mhcs_core.workflow import GrabberWorkflowResult


def test_parse_args_required(tmp_path: Path) -> None:
    rad = tmp_path / "rad.npz"
    gain = tmp_path / "gain.npz"
    out = tmp_path / "out"

    args = parse_args(
        [
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--output-dir",
            str(out),
        ]
    )
    assert args.radiograph == rad
    assert args.gain == gain
    assert args.output_dir == out
    assert args.locator is None
    assert args.resume is None
    assert args.json is False


def test_parse_args_all_options(tmp_path: Path) -> None:
    rad = tmp_path / "rad.npz"
    gain = tmp_path / "gain.npz"
    out = tmp_path / "out"
    work = tmp_path / "work"
    env_file = tmp_path / "test.env"
    token_file = tmp_path / "test.token"
    cal = tmp_path / "cal"

    args = parse_args(
        [
            "-r",
            str(rad),
            "-g",
            str(gain),
            "-o",
            str(out),
            "-w",
            str(work),
            "-l",
            "1234",
            "--env-file",
            str(env_file),
            "--token-file",
            str(token_file),
            "--calibration-dir",
            str(cal),
            "--base-url",
            "http://127.0.0.1:8023",
            "--resume",
            "--json",
        ]
    )
    assert args.radiograph == rad
    assert args.gain == gain
    assert args.output_dir == out
    assert args.work_dir == work
    assert args.locator == "1234"
    assert args.env_file == env_file
    assert args.token_file == token_file
    assert args.calibration_dir == cal
    assert args.base_url == "http://127.0.0.1:8023"
    assert args.resume is True
    assert args.json is True


def test_load_protected_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MHCS_GRABBER_BASE_URL", raising=False)
    monkeypatch.delenv("MHCS_GRABBER_TOKEN", raising=False)
    monkeypatch.delenv("MHCS_GRABBER_REHEARSAL_LOCATOR", raising=False)

    env_file = tmp_path / "protected.env"
    env_file.write_text(
        "MHCS_GRABBER_BASE_URL=http://127.0.0.1:8023\n"
        "MHCS_GRABBER_REHEARSAL_LOCATOR=5678\n",
        encoding="utf-8",
    )
    token_file = tmp_path / "protected.token"
    token_file.write_text("secret-test-token\n", encoding="utf-8")

    load_protected_environment(env_file=env_file, token_file=token_file)

    assert os_environ_get("MHCS_GRABBER_BASE_URL") == "http://127.0.0.1:8023"
    assert os_environ_get("MHCS_GRABBER_REHEARSAL_LOCATOR") == "5678"
    assert os_environ_get("MHCS_GRABBER_TOKEN") == "secret-test-token"


def os_environ_get(key: str) -> str | None:
    import os

    return os.environ.get(key)


def test_sanitized_result_formatting() -> None:
    result = GrabberWorkflowResult(
        study_id="STUDY-123",
        display_reference="REF-123",
        terminal_state="awaiting_ai",
        replayed=False,
        locator_code="9999",
        checksum="a" * 64,
        bytes=1024,
    )

    text_out = _format_sanitized_result(result, as_json=False)
    assert "replayed: False" in text_out
    assert "terminal_state: awaiting_ai" in text_out
    assert "bytes: 1024" in text_out
    assert "checksum: " + "a" * 64 in text_out
    # No patient identifiers or private fields
    assert "STUDY-123" not in text_out
    assert "REF-123" not in text_out

    json_out = json.loads(_format_sanitized_result(result, as_json=True))
    assert json_out["status"] == "success"
    assert json_out["terminal_state"] == "awaiting_ai"
    assert json_out["replayed"] is False
    assert json_out["bytes"] == 1024


def test_sanitized_error_formatting() -> None:
    exc = GrabberAuthError("Sensitive token leak attempt rejected")
    text_err = _format_sanitized_error(exc, as_json=False)
    assert "status: error" in text_err
    assert "error_class: GrabberAuthError" in text_err
    assert "Sensitive token" not in text_err

    json_err = json.loads(_format_sanitized_error(exc, as_json=True))
    assert json_err["status"] == "error"
    assert json_err["error_class"] == "GrabberAuthError"


def test_main_successful_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MHCS_GRABBER_BASE_URL", "http://127.0.0.1:8023")
    monkeypatch.setenv("MHCS_GRABBER_TOKEN", "test-token")

    rad = tmp_path / "rad.npz"
    gain = tmp_path / "gain.npz"
    out = tmp_path / "out"
    rad.touch()
    gain.touch()

    mock_result = GrabberWorkflowResult(
        study_id="STU-001",
        display_reference="REF-001",
        terminal_state="awaiting_ai",
        replayed=False,
        locator_code="4321",
        checksum="b" * 64,
        bytes=2048,
    )

    with patch(
        "mpips.integrations.mhcs_core.cli.run_grabber_roundtrip",
        return_value=mock_result,
    ) as mock_run:
        exit_code = main(
            [
                "-r",
                str(rad),
                "-g",
                str(gain),
                "-o",
                str(out),
                "-l",
                "4321",
                "--json",
            ]
        )

    assert exit_code == 0
    mock_run.assert_called_once()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "success"
    assert data["terminal_state"] == "awaiting_ai"
    assert data["replayed"] is False
    assert data["locator_code"] == "4321"


def test_main_error_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MHCS_GRABBER_BASE_URL", "http://127.0.0.1:8023")
    monkeypatch.setenv("MHCS_GRABBER_TOKEN", "test-token")

    rad = tmp_path / "rad.npz"
    gain = tmp_path / "gain.npz"
    out = tmp_path / "out"

    with patch(
        "mpips.integrations.mhcs_core.cli.run_grabber_roundtrip",
        side_effect=GrabberAuthError("Unauthorized"),
    ):
        exit_code = main(
            [
                "-r",
                str(rad),
                "-g",
                str(gain),
                "-o",
                str(out),
                "-l",
                "4321",
            ]
        )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "status: error" in captured.err
    assert "error_class: GrabberAuthError" in captured.err
    assert "Unauthorized" not in captured.err
