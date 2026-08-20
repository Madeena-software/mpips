"""Ownership contracts for the canonical wavelet denoiser."""

import importlib
import subprocess
import sys
import textwrap

import pytest


def test_wavelet_denoiser_has_processing_owner() -> None:
    from mpips.processing.wavelet import WaveletDenoiser

    assert WaveletDenoiser.__module__ == "mpips.processing.wavelet"


def test_complete_pipeline_imports_the_canonical_class_directly() -> None:
    import mpips.engine.imager_pipeline.complete_pipeline as pipeline

    from mpips.processing.wavelet import WaveletDenoiser

    pipeline_wavelet_denoiser = getattr(pipeline, "WaveletDenoiser")
    assert pipeline_wavelet_denoiser is WaveletDenoiser
    assert pipeline_wavelet_denoiser.__module__ == "mpips.processing.wavelet"


def test_legacy_wavelet_module_is_retired() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("mpips.engine.imager_pipeline.wavelet_denoising")


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
            "mpips.engine.imager_pipeline.complete_pipeline",
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
