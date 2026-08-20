"""Contracts for the canonical ``mpips-imager`` console adapter."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

import mpips.cli as cli
from mpips.pipelines.config import ImagerPipelineConfig


def _invoke(
    monkeypatch: pytest.MonkeyPatch,
    *,
    result: bool = True,
) -> tuple[list[tuple[Any, ...]], dict[str, Any]]:
    from mpips.workflows.imager_pipeline import file_runner

    calls: list[tuple[Any, ...]] = []
    keyword_args: dict[str, Any] = {}

    def fake_process(*args: Any, **kwargs: Any) -> bool:
        calls.append(args)
        keyword_args.update(kwargs)
        return result

    monkeypatch.setattr(file_runner, "process_tiff_triplet", fake_process)
    assert cli.run_imager() is None  # type: ignore[func-returns-value]
    return calls, keyword_args


def _clear_imager_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MPIPS_RADIOGRAPHY_ENV",
        "RAW_PATH",
        "DARK_PATH",
        "FLAT_PATH",
        "OUTPUT_DIR",
        "USE_IMAGEJ",
        "USE_DENOISE",
        "THRESHOLD_METHOD",
    ):
        monkeypatch.delenv(name, raising=False)


def test_project_scripts_keep_existing_ownership_except_imager() -> None:
    with Path("pyproject.toml").open("rb") as stream:
        scripts = tomllib.load(stream)["project"]["scripts"]

    assert scripts == {
        "mpips-api": "mpips.cli:run_api",
        "mpips-dotgrid": "mpips.calibration.dotgrid.neural_model.run_pipeline:cli",
        "mpips-imager": "mpips.cli:run_imager",
        "mpips-worker": "mpips.cli:run_worker",
    }


def test_run_imager_uses_explicit_environment_and_canonical_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.setenv("RAW_PATH", "/inputs/BED_fixture.tiff")
    monkeypatch.setenv("DARK_PATH", "/inputs/dark.tiff")
    monkeypatch.setenv("FLAT_PATH", "/inputs/flat.tiff")
    monkeypatch.setenv("OUTPUT_DIR", "/outputs")
    monkeypatch.setenv("USE_DENOISE", "false")
    monkeypatch.setenv("THRESHOLD_METHOD", "none")
    monkeypatch.setenv("USE_IMAGEJ", "false")

    calls, kwargs = _invoke(monkeypatch)

    assert calls == [
        (
            "/inputs/BED_fixture.tiff",
            "/inputs/dark.tiff",
            "/inputs/flat.tiff",
            Path("/outputs/BED_fixture_processed.tiff"),
        )
    ]
    assert isinstance(kwargs["config"], ImagerPipelineConfig)
    assert kwargs["config"].use_denoise is False
    assert kwargs["config"].threshold_method == "none"
    assert kwargs["imagej_available"] is False


def test_run_imager_reads_cwd_env_with_legacy_parser(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text(
        "\n"
        "# ignored\n"
        "RAW_PATH = /inputs/raw=fixture.tiff\n"
        "DARK_PATH=/inputs/dark.tiff\n"
        "FLAT_PATH=/inputs/flat.tiff\n"
        "OUTPUT_DIR = /outputs\n"
        "USE_IMAGEJ = YeS\n",
        encoding="utf-8",
    )

    calls, kwargs = _invoke(monkeypatch)

    assert calls[0][:3] == (
        "/inputs/raw=fixture.tiff",
        "/inputs/dark.tiff",
        "/inputs/flat.tiff",
    )
    assert calls[0][3] == Path("/outputs/raw=fixture_processed.tiff")
    assert kwargs["imagej_available"] is True


def test_explicit_env_file_precedes_cwd_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("RAW_PATH=cwd.tiff\n", encoding="utf-8")
    selected = tmp_path / "selected.env"
    selected.write_text(
        "RAW_PATH=selected.tiff\nOUTPUT_DIR=selected-output\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MPIPS_RADIOGRAPHY_ENV", str(selected))

    calls, _ = _invoke(monkeypatch)

    assert calls[0][0] == "selected.tiff"
    assert calls[0][3] == Path("selected-output/selected_processed.tiff")


def test_env_file_values_override_process_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAW_PATH", "from-process.tiff")
    Path(".env").write_text("RAW_PATH=from-file.tiff\n", encoding="utf-8")

    calls, _ = _invoke(monkeypatch)

    assert calls[0][0] == "from-file.tiff"


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("1", True),
        ("true", True),
        ("YES", True),
        ("On", True),
        ("false", False),
        ("off", False),
    ),
)
def test_use_imagej_legacy_boolean_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    expected: bool,
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.setenv("USE_IMAGEJ", value)

    _, kwargs = _invoke(monkeypatch)

    assert kwargs["imagej_available"] is expected


def test_run_imager_uses_historical_fallback_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    calls, _ = _invoke(monkeypatch)

    assert calls[0][:3] == (
        r"test\BED_1765259553954_rad.tiff",
        r"test\BED_1765259553954_dark.tiff",
        r"test\BED_1765259553954_gain.tiff",
    )
    assert (
        calls[0][3]
        == Path(r"test\output") / r"test\BED_1765259553954_rad_processed.tiff"
    )


def test_run_imager_does_not_use_module_local_env_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_imager_env(monkeypatch)
    module_dir = tmp_path / "module"
    module_dir.mkdir()
    (module_dir / ".env").write_text("RAW_PATH=module-local.tiff\n", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(cli, "__file__", str(module_dir / "cli.py"))

    calls, _ = _invoke(monkeypatch)

    assert calls[0][0] == r"test\BED_1765259553954_rad.tiff"


@pytest.mark.parametrize("result,word", ((True, "succeeded"), (False, "failed")))
def test_run_imager_reports_result_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    result: bool,
    word: str,
) -> None:
    _clear_imager_env(monkeypatch)

    assert _invoke(monkeypatch, result=result)[0]
    assert word in capsys.readouterr().out.lower()


def test_run_imager_uses_one_canonical_file_runner_without_gpu_or_batch_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_imager_env(monkeypatch)
    monkeypatch.setenv("USE_GPU", "true")

    calls, kwargs = _invoke(monkeypatch)

    assert len(calls) == 1
    assert not hasattr(kwargs["config"], "use_gpu")


def test_importing_cli_does_not_load_heavy_runtime_modules() -> None:
    script = """
import sys
import mpips.cli

for forbidden in (
    "mpips.engine",
    "cv2",
    "numpy",
    "scipy",
    "skimage",
    "matplotlib",
    "pydicom",
    "fastapi",
    "celery",
    "boto3",
):
    assert not any(
        name == forbidden or name.startswith(forbidden + ".")
        for name in sys.modules
    ), forbidden
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
