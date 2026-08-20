"""Ownership contracts for the canonical wavelet denoiser."""

import importlib
import subprocess
import sys
import textwrap

import pytest


def test_wavelet_denoiser_has_processing_owner() -> None:
    from mpips.processing.wavelet import WaveletDenoiser

    assert WaveletDenoiser.__module__ == "mpips.processing.wavelet"


def test_retired_imager_engine_modules_are_absent() -> None:
    for module in (
        "mpips.engine.imager_pipeline.complete_pipeline",
        "mpips.engine.imager_pipeline.wavelet_denoising",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)


def test_processing_wavelet_import_does_not_load_service_or_pipeline_modules() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.wavelet import WaveletDenoiser

        assert WaveletDenoiser.__module__ == "mpips.processing.wavelet"
        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.engine",
            "mpips.worker",
            "mpips.workflows",
        }
        assert forbidden.isdisjoint(sys.modules)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
