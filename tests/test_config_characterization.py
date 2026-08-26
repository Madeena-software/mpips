"""Characterization tests for imager pipeline configuration prior to refactor."""

import hashlib
import numpy as np

from mpips.workflows.imager_pipeline.models import ImagerPipelineConfig
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays


def _create_test_arrays(
    shape: tuple[int, int] = (24, 24)
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y_values, x_values = np.indices(shape)
    raw = (
        800 + x_values * 27 + y_values * 19 + ((x_values * y_values) % 11) * 13
    ).astype(np.uint16)
    dark = (40 + ((x_values + y_values) % 7)).astype(np.uint16)
    flat = (3100 + x_values * 3 + y_values * 5).astype(np.uint16)
    return raw, dark, flat


def test_characterize_imager_pipeline_config_defaults() -> None:
    """Verify default values on workflow ImagerPipelineConfig model."""
    config = ImagerPipelineConfig()
    assert config.crop_top == 0
    assert config.crop_bottom == 0
    assert config.crop_left == 0
    assert config.crop_right == 0
    assert config.use_denoise is True
    assert config.wavelet == "sym4"
    assert config.wavelet_level == 3
    assert config.wavelet_method == "BayesShrink"
    assert config.wavelet_mode == "soft"
    assert config.use_normalize is False
    assert config.normalize_saturated_pixels == 0.35
    assert config.threshold_method == "auto"
    assert config.use_invert is True
    assert config.use_contrast_enhancement is True
    assert config.contrast_saturated_pixels == 5.0
    assert config.contrast_mode == "equalize"
    assert config.contrast_equalize is True
    assert config.contrast_normalize is False
    assert config.contrast_classic_equalization is False

    assert config.use_clahe is True
    assert config.clahe_blocksize == 127
    assert config.clahe_histogram_bins == 256
    assert config.clahe_max_slope == 0.6
    assert config.clahe_fast is False
    assert config.clahe_composite is True
    assert config.use_final_denoise is False
    assert config.use_median_filter is True
    assert config.median_filter_type == "hybrid_imagej"
    assert config.median_filter_radius == 2
    assert config.debug is False


def test_characterize_process_radiography_arrays_config_none_vs_explicit() -> None:
    """Verify process_radiography_arrays(config=None) matches explicit ImagerPipelineConfig()."""  # noqa: E501
    raw, dark, flat = _create_test_arrays()
    out_none = process_radiography_arrays(raw, dark, flat, "BED", config=None)
    out_explicit = process_radiography_arrays(
        raw, dark, flat, "BED", config=ImagerPipelineConfig()
    )
    np.testing.assert_array_equal(out_none, out_explicit)


def test_characterize_bed_golden_output_hash() -> None:
    """Verify BED processing produces expected deterministic hash."""
    raw, dark, flat = _create_test_arrays()
    out = process_radiography_arrays(raw, dark, flat, "BED", config=None)
    assert out.dtype == np.uint16
    assert out.shape == (24, 24)
    out_hash = hashlib.sha256(out.tobytes()).hexdigest()
    assert (
        out_hash == "a5dc3a5c98b8f9bb5acfcd3b61974c70b0a3b637e7e792343c97f904d73f92e4"
    )


def test_characterize_trx_golden_output_hash() -> None:
    """Verify TRX processing produces expected deterministic hash."""
    raw, dark, flat = _create_test_arrays()
    out = process_radiography_arrays(raw, dark, flat, "TRX", config=None)
    assert out.dtype == np.uint16
    assert out.shape == (24, 24)
    out_hash = hashlib.sha256(out.tobytes()).hexdigest()
    assert (
        out_hash == "ce90a4139b90a9d6bcb7f78b5a431ef549f0b11c34e2389c4c85b6f9c2cfb046"
    )


def test_characterize_contrast_branch_equalize_shadows_stretch() -> None:
    """Verify that contrast_equalize=True branch ignores stretch parameters."""
    raw, dark, flat = _create_test_arrays()
    config1 = ImagerPipelineConfig(
        use_contrast_enhancement=True,
        contrast_equalize=True,
        contrast_saturated_pixels=5.0,
        contrast_normalize=True,
    )
    config2 = ImagerPipelineConfig(
        use_contrast_enhancement=True,
        contrast_equalize=True,
        contrast_saturated_pixels=25.0,
        contrast_normalize=False,
    )
    out1 = process_radiography_arrays(raw, dark, flat, "BED", config=config1)
    out2 = process_radiography_arrays(raw, dark, flat, "BED", config=config2)
    np.testing.assert_array_equal(out1, out2)


def test_characterize_median_filter_default_on() -> None:
    """Verify that the effective runtime default has median filter enabled."""
    config = ImagerPipelineConfig()
    assert config.use_median_filter is True
