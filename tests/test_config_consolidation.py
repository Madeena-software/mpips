"""Comprehensive correctness tests for canonical image processing configuration."""

import json
import pytest

from mpips.pipelines.config import (
    ImagerPipelineConfig,
    get_default_config,
)


def test_direct_construction_contrast_mode() -> None:
    """Test direct construction with contrast_mode parameter without legacy boolean args."""  # noqa: E501

    cfg_eq = ImagerPipelineConfig(contrast_mode="equalize")
    assert cfg_eq.contrast_mode == "equalize"
    assert cfg_eq.use_contrast_enhancement is True
    assert cfg_eq.contrast_equalize is True
    assert cfg_eq.contrast_normalize is False

    cfg_str = ImagerPipelineConfig(contrast_mode="stretch")
    assert cfg_str.contrast_mode == "stretch"
    assert cfg_str.use_contrast_enhancement is True
    assert cfg_str.contrast_equalize is False
    assert cfg_str.contrast_normalize is True

    cfg_dis = ImagerPipelineConfig(contrast_mode="disabled")
    assert cfg_dis.contrast_mode == "disabled"
    assert cfg_dis.use_contrast_enhancement is False
    assert cfg_dis.contrast_equalize is False
    assert cfg_dis.contrast_normalize is False


def test_threshold_enabled_semantics() -> None:
    """Test threshold enabled=False maps to THRESHOLD_METHOD='none' in engine dict."""
    cfg = ImagerPipelineConfig(use_threshold=False, threshold_method="auto")
    assert cfg.use_threshold is False
    engine_dict = cfg.to_legacy_engine_dict()
    assert engine_dict["THRESHOLD_METHOD"] == "none"

    serialized = cfg.to_dict()
    assert serialized["threshold"]["enabled"] is False
    assert serialized["threshold"]["method"] == "none"

    reconstructed = ImagerPipelineConfig.from_dict(serialized)
    assert reconstructed.use_threshold is False
    assert reconstructed.to_legacy_engine_dict()["THRESHOLD_METHOD"] == "none"


def test_crop_rotate_enabled_semantics() -> None:
    """Test crop_rotate enabled toggle maps to USE_CROP_ROTATE in engine dict."""
    cfg_off = ImagerPipelineConfig(use_crop_rotate=False)
    assert cfg_off.use_crop_rotate is False
    assert cfg_off.to_legacy_engine_dict()["USE_CROP_ROTATE"] is False

    cfg_on = ImagerPipelineConfig(use_crop_rotate=True)
    assert cfg_on.use_crop_rotate is True
    assert cfg_on.to_legacy_engine_dict()["USE_CROP_ROTATE"] is True


def test_contrast_disabled_roundtrip_semantics() -> None:
    """Test deterministic resolution of contradictory or disabled JSON contrast inputs."""  # noqa: E501
    # enabled=true + mode=disabled -> disabled
    json_data1 = {"contrast": {"enabled": True, "mode": "disabled"}}
    cfg1 = ImagerPipelineConfig.from_dict(json_data1)
    assert cfg1.contrast_mode == "disabled"
    assert cfg1.use_contrast_enhancement is False

    # enabled=false + mode=equalize -> disabled
    json_data2 = {"contrast": {"enabled": False, "mode": "equalize"}}
    cfg2 = ImagerPipelineConfig.from_dict(json_data2)
    assert cfg2.contrast_mode == "disabled"
    assert cfg2.use_contrast_enhancement is False


def test_roundtrip_matrix() -> None:
    """Test config -> to_dict() -> JSON -> from_dict() for all canonical matrix states."""  # noqa: E501

    matrix_configs = {
        "DEFAULT": get_default_config(),
        "EQUALIZE": ImagerPipelineConfig(contrast_mode="equalize"),
        "STRETCH": ImagerPipelineConfig(contrast_mode="stretch"),
        "DISABLED": ImagerPipelineConfig(contrast_mode="disabled"),
        "THRESHOLD_DISABLED": ImagerPipelineConfig(use_threshold=False),
        "CLAHE_DISABLED": ImagerPipelineConfig(use_clahe=False),
        "MEDIAN_DISABLED": ImagerPipelineConfig(use_median_filter=False),
    }

    for name, cfg in matrix_configs.items():
        dict_rep = cfg.to_dict()
        json_str = json.dumps(dict_rep)
        data = json.loads(json_str)
        reconstructed = ImagerPipelineConfig.from_dict(data)

        assert (
            reconstructed.use_denoise == cfg.use_denoise
        ), f"{name} use_denoise mismatch"
        assert (
            reconstructed.use_crop_rotate == cfg.use_crop_rotate
        ), f"{name} use_crop_rotate mismatch"
        assert (
            reconstructed.use_threshold == cfg.use_threshold
        ), f"{name} use_threshold mismatch"
        assert (
            reconstructed.contrast_mode == cfg.contrast_mode
        ), f"{name} contrast_mode mismatch"
        assert (
            reconstructed.use_contrast_enhancement == cfg.use_contrast_enhancement
        ), f"{name} use_contrast_enhancement mismatch"
        assert reconstructed.use_clahe == cfg.use_clahe, f"{name} use_clahe mismatch"
        assert (
            reconstructed.use_median_filter == cfg.use_median_filter
        ), f"{name} use_median_filter mismatch"


def test_legacy_env_matrix() -> None:
    """Test resolution of legacy environment variables into canonical ContrastMode."""
    # USE_CONTRAST_ENHANCEMENT=false -> disabled
    cfg1 = ImagerPipelineConfig.from_env({"USE_CONTRAST_ENHANCEMENT": "false"})
    assert cfg1.contrast_mode == "disabled"
    assert cfg1.use_contrast_enhancement is False

    # CONTRAST_EQUALIZE=true -> equalize
    cfg2 = ImagerPipelineConfig.from_env({"CONTRAST_EQUALIZE": "true"})
    assert cfg2.contrast_mode == "equalize"
    assert cfg2.use_contrast_enhancement is True

    # CONTRAST_EQUALIZE=false + CONTRAST_NORMALIZE=true -> stretch
    cfg3 = ImagerPipelineConfig.from_env(
        {
            "CONTRAST_EQUALIZE": "false",
            "CONTRAST_NORMALIZE": "true",
        }
    )
    assert cfg3.contrast_mode == "stretch"
    assert cfg3.use_contrast_enhancement is True

    # CONTRAST_EQUALIZE=false + CONTRAST_NORMALIZE=false -> disabled
    cfg4 = ImagerPipelineConfig.from_env(
        {
            "CONTRAST_EQUALIZE": "false",
            "CONTRAST_NORMALIZE": "false",
        }
    )
    assert cfg4.contrast_mode == "disabled"
    assert cfg4.use_contrast_enhancement is False


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
