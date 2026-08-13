"""Comprehensive tests for consolidated canonical image processing configuration."""

import json
import pytest

from mpips.engine.imager_pipeline.config import (
    ImagerPipelineConfig,
    ContrastMode,
)


def test_config_serialization_roundtrip_structured() -> None:
    """Test canonical config -> JSON -> canonical config roundtrip equality."""
    original = ImagerPipelineConfig(
        use_denoise=True,
        wavelet="sym4",
        wavelet_level=2,
        wavelet_method="VisuShrink",
        wavelet_mode="hard",
        use_normalize=True,
        normalize_saturated_pixels=0.5,
        threshold_method="otsu",
        use_invert=False,
        use_contrast_enhancement=True,
        contrast_mode="stretch",
        contrast_saturated_pixels=2.5,
        contrast_normalize=True,
        contrast_equalize=False,
        use_clahe=True,
        clahe_blocksize=63,
        clahe_histogram_bins=128,
        clahe_max_slope=1.2,
        clahe_fast=True,
        clahe_composite=False,
        use_final_denoise=True,
        use_median_filter=True,
        median_filter_type="standard",
        median_filter_radius=3,
        debug=True,
    )
    serialized = original.to_dict()
    json_str = json.dumps(serialized)
    deserialized_data = json.loads(json_str)
    reconstructed = ImagerPipelineConfig.from_dict(deserialized_data)

    assert reconstructed.use_denoise == original.use_denoise
    assert reconstructed.wavelet_level == original.wavelet_level
    assert reconstructed.wavelet_method == original.wavelet_method
    assert reconstructed.wavelet_mode == original.wavelet_mode
    assert reconstructed.use_normalize == original.use_normalize
    assert (
        reconstructed.normalize_saturated_pixels == original.normalize_saturated_pixels
    )
    assert reconstructed.threshold_method == original.threshold_method
    assert reconstructed.use_invert == original.use_invert
    assert reconstructed.contrast_mode == ContrastMode.STRETCH.value
    assert reconstructed.contrast_saturated_pixels == original.contrast_saturated_pixels
    assert reconstructed.clahe_blocksize == original.clahe_blocksize
    assert reconstructed.clahe_histogram_bins == original.clahe_histogram_bins
    assert reconstructed.clahe_max_slope == original.clahe_max_slope
    assert reconstructed.median_filter_type == original.median_filter_type
    assert reconstructed.median_filter_radius == original.median_filter_radius
    assert reconstructed.debug == original.debug


def test_config_to_legacy_engine_dict() -> None:
    """Test canonical config -> legacy engine mapping populates expected variables."""  # noqa: E501
    config = ImagerPipelineConfig(
        wavelet_level=4,
        median_filter_radius=3,
        use_median_filter=True,
    )
    engine_dict = config.to_legacy_engine_dict()
    assert engine_dict["WAVELET_LEVEL"] == 4
    assert engine_dict["MEDIAN_FILTER_RADIUS"] == 3
    assert engine_dict["USE_MEDIAN_FILTER"] is True
    assert engine_dict["USE_DENOISE"] is True
    assert engine_dict["THRESHOLD_METHOD"] == "auto"


def test_legacy_env_loading_defaults_and_overrides() -> None:
    """Test env resolution for default and customized environment variables."""
    default_cfg = ImagerPipelineConfig.from_env({})
    assert default_cfg.use_median_filter is True
    assert default_cfg.wavelet_level == 3

    custom_env = {
        "USE_MEDIAN_FILTER": "false",
        "WAVELET_LEVEL": "5",
        "CLAHE_BLOCKSIZE": "63",
        "CONTRAST_EQUALIZE": "false",
        "CONTRAST_NORMALIZE": "true",
        "CONTRAST_SATURATED_PIXELS": "3.5",
        "THRESHOLD_METHOD": "valley",
    }
    custom_cfg = ImagerPipelineConfig.from_env(custom_env)
    assert custom_cfg.use_median_filter is False
    assert custom_cfg.wavelet_level == 5
    assert custom_cfg.clahe_blocksize == 63
    assert custom_cfg.contrast_mode == "stretch"
    assert custom_cfg.contrast_saturated_pixels == 3.5
    assert custom_cfg.threshold_method == "valley"


def test_invalid_enum_validation_raises_error() -> None:
    """Test that invalid enum string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid threshold_method"):
        ImagerPipelineConfig(threshold_method="invalid_method_xyz")

    with pytest.raises(ValueError, match="Invalid wavelet_mode"):
        ImagerPipelineConfig(wavelet_mode="invalid_mode")

    with pytest.raises(ValueError, match="Invalid median_filter_type"):
        ImagerPipelineConfig(median_filter_type="magic_filter")


def test_invalid_numerical_bounds_validation_raises_error() -> None:
    """Test that out-of-bounds numerical values raise ValueError."""
    with pytest.raises(ValueError, match="wavelet_level must be > 0"):
        ImagerPipelineConfig(wavelet_level=0)

    with pytest.raises(ValueError, match="contrast_saturated_pixels must be in"):
        ImagerPipelineConfig(contrast_saturated_pixels=150.0)

    with pytest.raises(ValueError, match="clahe_blocksize must be > 0"):
        ImagerPipelineConfig(clahe_blocksize=-5)

    with pytest.raises(ValueError, match="median_filter_radius must be > 0"):
        ImagerPipelineConfig(median_filter_radius=0)


def test_contrast_confusion_equalize_shadows_stretch_params() -> None:
    """Explicit regression test proving contrast_equalize=True shadows stretch settings."""  # noqa: E501
    cfg_equalize = ImagerPipelineConfig(
        use_contrast_enhancement=True,
        contrast_equalize=True,
        contrast_saturated_pixels=10.0,
    )
    assert cfg_equalize.contrast_mode == "equalize"
    legacy_dict = cfg_equalize.to_legacy_engine_dict()
    assert legacy_dict["CONTRAST_EQUALIZE"] is True

    cfg_stretch = ImagerPipelineConfig(
        use_contrast_enhancement=True,
        contrast_equalize=False,
        contrast_normalize=True,
        contrast_saturated_pixels=5.0,
    )
    assert cfg_stretch.contrast_mode == "stretch"
