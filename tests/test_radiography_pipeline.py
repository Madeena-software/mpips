"""Contract tests for the canonical array-only radiography pipeline."""

from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

import mpips.pipelines.radiography as radiography_pipeline
from mpips.pipelines import ImagerPipelineConfig, RadiographyPipeline
import mpips.workflows.imager_pipeline.pipeline as workflow_pipeline
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays


def _recipe_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    shape = (24, 24)
    y, x = np.indices(shape)
    raw = (800 + x * 27 + y * 19 + ((x * y) % 11) * 13).astype(np.uint16)
    dark = (40 + ((x + y) % 7)).astype(np.uint16)
    flat = (3100 + x * 3 + y * 5).astype(np.uint16)
    return raw, dark, flat


def _minimal_config(**overrides: object) -> ImagerPipelineConfig:
    values: dict[str, Any] = {
        "use_denoise": False,
        "threshold_method": "none",
        "use_invert": False,
        "use_contrast_enhancement": False,
        "use_clahe": False,
        "use_median_filter": False,
    }
    values.update(overrides)
    return ImagerPipelineConfig(**values)


def _legacy_result(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    config: ImagerPipelineConfig,
    *,
    detector_mode: str = "BED",
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
    imagej_available: bool = True,
) -> np.ndarray:
    return process_radiography_arrays(
        raw,
        dark,
        flat,
        detector_mode,
        config,
        map_x=map_x,
        map_y=map_y,
        imagej_available=imagej_available,
    )


def test_default_recipe_matches_legacy_pixels_and_hash() -> None:
    raw, dark, flat = _recipe_fixture()
    config = ImagerPipelineConfig()

    result = RadiographyPipeline(config).process(raw, dark, flat, "BED")

    assert result.dtype == np.uint16
    assert result.shape == (24, 24)
    assert int(result.min()) == 0
    assert int(result.max()) == 65535
    assert result[(0, 0)] == 65535
    assert result[(0, 4)] == 47802
    assert result[(4, 0)] == 43690
    assert result[(8, 0)] == 0
    assert result[(23, 23)] == 0
    assert hashlib.sha256(result.tobytes()).hexdigest() == (
        "f176b16a29fc3a37fee76a133f88bc0018514210cccb461218008933186e18b7"
    )


def test_default_recipe_matches_legacy_array_result() -> None:
    raw, dark, flat = _recipe_fixture()
    config = ImagerPipelineConfig()

    direct = RadiographyPipeline(config).process(raw, dark, flat, "BED")
    legacy = _legacy_result(raw, dark, flat, config)

    np.testing.assert_array_equal(direct, legacy)


def test_trx_bypasses_threshold_and_preserves_config() -> None:
    raw, dark, flat = _recipe_fixture()
    active = _minimal_config(
        threshold_method="auto",
        use_threshold=True,
        use_clahe=True,
        clahe_blocksize=17,
        median_filter_radius=3,
    )
    skipped = _minimal_config(
        threshold_method="none",
        use_threshold=True,
        use_clahe=True,
        clahe_blocksize=17,
        median_filter_radius=3,
    )

    active_result = RadiographyPipeline(active).process(raw, dark, flat, "TRX")
    skipped_result = RadiographyPipeline(skipped).process(raw, dark, flat, "TRX")

    np.testing.assert_array_equal(active_result, skipped_result)
    assert active.use_threshold is True
    assert active.threshold_method == "auto"
    assert active.use_clahe is True
    assert active.clahe_blocksize == 17
    assert active.median_filter_radius == 3


def test_bed_preserves_configured_threshold_and_skip_behavior(monkeypatch) -> None:
    raw, dark, flat = _recipe_fixture()
    config = _minimal_config(threshold_method="auto", use_threshold=True)
    calls = 0
    original = radiography_pipeline.detect_threshold

    def count_detect(*args: object, **kwargs: object) -> float:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(radiography_pipeline, "detect_threshold", count_detect)
    result = RadiographyPipeline(config).process(raw, dark, flat, "BED")
    assert result.dtype == np.uint16
    assert calls == 1

    skipped = _minimal_config(threshold_method="none", use_threshold=True)
    skipped_result = RadiographyPipeline(skipped).process(raw, dark, flat, "BED")
    assert not np.array_equal(result, skipped_result)
    assert config.threshold_method == "auto"
    assert config.use_threshold is True

    disabled = _minimal_config(threshold_method="auto", use_threshold=False)
    disabled_result = RadiographyPipeline(disabled).process(raw, dark, flat, "BED")
    np.testing.assert_array_equal(disabled_result, skipped_result)


_BRANCH_CASES = (
    ("use_denoise_false", {"use_denoise": False}),
    ("use_crop_rotate_false", {"use_crop_rotate": False}),
    ("threshold_disabled", {"use_threshold": False}),
    ("invert_false", {"use_invert": False}),
    ("contrast_disabled", {"use_contrast_enhancement": False}),
    (
        "contrast_stretch",
        {"use_contrast_enhancement": True, "contrast_mode": "stretch"},
    ),
    ("clahe_false", {"use_clahe": False}),
    ("final_denoise_true", {"use_final_denoise": True}),
    ("median_false", {"use_median_filter": False}),
    (
        "median_standard",
        {
            "use_median_filter": True,
            "median_filter_type": "standard",
            "median_filter_radius": 1,
        },
    ),
    ("normalize_true", {"use_normalize": True}),
)


@pytest.mark.parametrize(
    "name,overrides", _BRANCH_CASES, ids=[case[0] for case in _BRANCH_CASES]
)
def test_config_branch_matches_legacy(name: str, overrides: dict[str, object]) -> None:
    del name
    raw, dark, flat = _recipe_fixture()
    config = _minimal_config(**overrides)

    direct = RadiographyPipeline(config).process(raw, dark, flat, "BED")
    legacy = _legacy_result(raw, dark, flat, config)

    np.testing.assert_array_equal(direct, legacy)


def test_imagej_unavailable_branch_matches_legacy() -> None:
    raw, dark, flat = _recipe_fixture()
    config = _minimal_config(
        use_contrast_enhancement=True,
        contrast_mode="equalize",
        use_clahe=True,
        use_median_filter=True,
        median_filter_type="hybrid_imagej",
    )
    direct = RadiographyPipeline(config, imagej_available=False).process(
        raw, dark, flat, "BED"
    )
    legacy = _legacy_result(raw, dark, flat, config, imagej_available=False)

    np.testing.assert_array_equal(direct, legacy)


@pytest.mark.parametrize("detector_mode", ["BED", "TRX"])
def test_nonzero_crop_matches_legacy(detector_mode: str) -> None:
    raw, dark, flat = _recipe_fixture()
    config = _minimal_config(
        crop_top=1,
        crop_bottom=2,
        crop_left=2,
        crop_right=1,
    )

    direct = RadiographyPipeline(config).process(raw, dark, flat, detector_mode)
    legacy = _legacy_result(raw, dark, flat, config, detector_mode=detector_mode)

    np.testing.assert_array_equal(direct, legacy)
    assert direct.shape == (21, 21)


def test_identity_remap_matches_legacy() -> None:
    raw, dark, flat = _recipe_fixture()
    coords = np.indices(raw.shape, dtype=np.float32)
    x: np.ndarray = np.asarray(coords[1], dtype=np.float32)
    y: np.ndarray = np.asarray(coords[0], dtype=np.float32)
    config = _minimal_config()

    direct = RadiographyPipeline(config).process(
        raw, dark, flat, "BED", map_x=x, map_y=y
    )
    legacy = _legacy_result(raw, dark, flat, config, map_x=x, map_y=y)

    np.testing.assert_array_equal(direct, legacy)


def test_expanded_remap_canvas_matches_legacy() -> None:
    raw = np.arange(64, dtype=np.uint16).reshape(8, 8) + 100
    dark = np.zeros((8, 8), dtype=np.uint16)
    flat = np.full((8, 8), 1000, dtype=np.uint16)
    coords = np.indices((12, 12), dtype=np.float32)
    x: np.ndarray = np.asarray(coords[1], dtype=np.float32)
    y: np.ndarray = np.asarray(coords[0], dtype=np.float32)
    config = _minimal_config()

    direct = RadiographyPipeline(config).process(
        raw, dark, flat, "BED", map_x=x, map_y=y
    )
    legacy = _legacy_result(raw, dark, flat, config, map_x=x, map_y=y)

    np.testing.assert_array_equal(direct, legacy)
    assert direct.shape == (12, 12)
    assert not direct[8:, :].any()
    assert not direct[:, 8:].any()


def test_out_of_bounds_remap_pixels_are_zero() -> None:
    raw, dark, flat = _recipe_fixture()
    coords = np.indices(raw.shape, dtype=np.float32)
    x: np.ndarray = np.asarray(coords[1], dtype=np.float32)
    y: np.ndarray = np.asarray(coords[0], dtype=np.float32)
    x[0, 0] = -1
    y[-1, -1] = raw.shape[0]
    config = _minimal_config()

    result = RadiographyPipeline(config).process(
        raw, dark, flat, "BED", map_x=x, map_y=y
    )

    assert result[0, 0] == 0
    assert result[-1, -1] == 0
    assert np.any(result[1:-1, 1:-1] != 0)


def test_pipeline_does_not_mutate_inputs_or_maps() -> None:
    raw, dark, flat = _recipe_fixture()
    coords = np.indices(raw.shape, dtype=np.float32)
    x: np.ndarray = np.asarray(coords[1], dtype=np.float32)
    y: np.ndarray = np.asarray(coords[0], dtype=np.float32)
    inputs = (raw.copy(), dark.copy(), flat.copy(), x.copy(), y.copy())
    config = _minimal_config()

    RadiographyPipeline(config).process(raw, dark, flat, "BED", map_x=x, map_y=y)

    for actual, expected in zip((raw, dark, flat, x, y), inputs):
        np.testing.assert_array_equal(actual, expected)


def test_canonical_pipeline_import_is_service_and_engine_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script = """
from mpips.pipelines import RadiographyPipeline
import sys

assert RadiographyPipeline.__module__ == "mpips.pipelines.radiography"
for forbidden in (
    "mpips.engine",
    "mpips.workflows",
    "mpips.api",
    "mpips.worker",
    "mpips.conversion",
    "fastapi",
    "celery",
    "boto3",
):
    assert not any(
        name == forbidden or name.startswith(forbidden + ".")
        for name in sys.modules
    )
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_pipeline_source_has_no_legacy_engine_bridge_or_file_io() -> None:
    from mpips.pipelines.radiography import RadiographyPipeline

    source = inspect.getsource(RadiographyPipeline)
    assert "to_legacy_engine_dict" not in source
    assert "process_single_image" not in source
    assert "cv2.imwrite" not in source
    assert "cv2.imread" not in source


def test_invalid_shapes_and_partial_remap_are_rejected() -> None:
    raw, dark, flat = _recipe_fixture()
    config = _minimal_config()
    pipeline = RadiographyPipeline(config)

    with pytest.raises(ValueError, match="Raw/dark/flat shapes differ"):
        pipeline.process(raw, dark[:-1], flat, "BED")
    with pytest.raises(ValueError, match="Both map_x and map_y are required"):
        pipeline.process(raw, dark, flat, "BED", map_x=np.zeros(raw.shape))


def test_workflow_pipeline_import_is_engine_and_service_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script = """
import importlib
import sys

importlib.import_module("mpips.workflows.imager_pipeline.pipeline")
for forbidden in (
    "mpips.engine",
    "mpips.api",
    "mpips.worker",
    "mpips.conversion",
    "fastapi",
    "celery",
    "boto3",
):
    assert not any(
        name == forbidden or name.startswith(forbidden + ".")
        for name in sys.modules
    )
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_workflow_process_delegates_without_tiff_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = np.ones((2, 2), dtype=np.uint16)
    dark = np.zeros_like(raw)
    flat = np.full_like(raw, 1000)
    map_x = np.zeros((1, 1), dtype=np.float32)
    map_y = np.zeros((1, 1), dtype=np.float32)
    config = ImagerPipelineConfig(use_denoise=False)
    sentinel = np.array([[123]], dtype=np.uint16)
    calls: dict[str, object] = {}

    class SpyPipeline:
        def __init__(
            self,
            received_config: ImagerPipelineConfig,
            *,
            imagej_available: bool,
        ) -> None:
            calls["config"] = received_config
            calls["imagej_available"] = imagej_available

        def process(
            self,
            received_raw: np.ndarray,
            received_dark: np.ndarray,
            received_flat: np.ndarray,
            received_detector_mode: str,
            *,
            map_x: np.ndarray | None,
            map_y: np.ndarray | None,
        ) -> np.ndarray:
            calls["arrays"] = (received_raw, received_dark, received_flat)
            calls["detector_mode"] = received_detector_mode
            calls["maps"] = (map_x, map_y)
            return sentinel

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("workflow pipeline performed file I/O")

    monkeypatch.setattr(
        workflow_pipeline, "RadiographyPipeline", SpyPipeline, raising=False
    )
    monkeypatch.setattr(
        workflow_pipeline,
        "tempfile",
        SimpleNamespace(TemporaryDirectory=fail_if_called),
        raising=False,
    )
    monkeypatch.setattr(
        workflow_pipeline,
        "cv2",
        SimpleNamespace(imread=fail_if_called, imwrite=fail_if_called),
        raising=False,
    )

    result = process_radiography_arrays(
        raw,
        dark,
        flat,
        "TRX",
        config,
        map_x=map_x,
        map_y=map_y,
        imagej_available=False,
    )

    assert result is sentinel
    assert calls["config"] is config
    assert calls["imagej_available"] is False
    assert calls["arrays"] == (raw, dark, flat)
    assert calls["detector_mode"] == "TRX"
    assert calls["maps"] == (map_x, map_y)


def test_workflow_process_signature_preserves_legacy_order() -> None:
    parameters = inspect.signature(process_radiography_arrays).parameters
    assert list(parameters)[:5] == [
        "raw",
        "dark",
        "flat",
        "detector_mode",
        "config",
    ]
    imagej_parameter = parameters["imagej_available"]
    assert imagej_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert imagej_parameter.default is True
