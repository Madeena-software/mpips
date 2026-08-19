"""Ownership and compatibility contracts for the canonical wavelet denoiser."""

# The legacy modules are intentionally outside the typed processing boundary.
# mypy: disable-error-code=attr-defined

import subprocess
import sys
import textwrap


def test_wavelet_denoiser_has_processing_owner() -> None:
    from mpips.processing.wavelet import WaveletDenoiser

    assert WaveletDenoiser.__module__ == "mpips.processing.wavelet"


def test_legacy_wavelet_denoiser_is_the_canonical_class() -> None:
    from mpips.engine.imager_pipeline.wavelet_denoising import (
        WaveletDenoiser as LegacyWaveletDenoiser,
    )
    from mpips.processing.wavelet import WaveletDenoiser

    assert LegacyWaveletDenoiser is WaveletDenoiser


def test_complete_pipeline_uses_the_canonical_class_through_compatibility_import() -> (
    None
):
    from mpips.engine.imager_pipeline.complete_pipeline import (
        WaveletDenoiser as PipelineWaveletDenoiser,
    )
    from mpips.processing.wavelet import WaveletDenoiser

    assert PipelineWaveletDenoiser is WaveletDenoiser


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


def test_legacy_wavelet_research_utilities_remain_importable() -> None:
    from mpips.engine.imager_pipeline.wavelet_denoising import (
        PYWT_AVAILABLE,
        WaveletBackgroundRemover,
        process_with_wavelet,
    )

    assert isinstance(PYWT_AVAILABLE, bool)
    assert callable(process_with_wavelet)
    assert WaveletBackgroundRemover.__module__ == (
        "mpips.engine.imager_pipeline.wavelet_denoising"
    )
