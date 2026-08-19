import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

import mpips.processing.radiography as radiography
from mpips.engine.imager_pipeline import complete_pipeline as legacy_engine
from mpips.processing import apply_threshold_separation, auto_threshold
from mpips.processing.thresholding import (
    apply_threshold_separation as canonical_apply_threshold_separation,
    detect_threshold,
)

radiography_apply_threshold_separation = cast(
    Any, getattr(radiography, "apply_threshold_separation")
)

EXPECTED_THRESHOLDS = {
    "auto": np.float32(0.21826171875),
    "valley": np.float32(0.21826171875),
    "otsu": 0.0,
    "knee": np.float32(0.18681641),
    "percentile_25": np.float32(0.175),
    "secondary_peak": np.float32(0.118457034),
}

EXPECTED_CPU_SEPARATION_CASES = (
    (
        "representative_normal",
        np.array([[0.10, 0.20, 0.40], [0.60, 0.80, 1.00]], dtype=np.float32),
        0.40,
        np.array([[0.0, 0.3333333, 1.0], [1.0, 1.0, 1.0]], dtype=np.float32),
    ),
    (
        "exact_threshold",
        np.array([[0.10, 0.20, 0.30]], dtype=np.float32),
        0.20,
        np.array([[0.0, 1.0, 1.0]], dtype=np.float32),
    ),
    (
        "all_above_threshold",
        np.array([[0.75, 0.80], [0.90, 1.00]], dtype=np.float32),
        0.50,
        np.ones((2, 2), dtype=np.float32),
    ),
    (
        "constant_content",
        np.array([[0.25, 0.25, 0.75, 0.75]], dtype=np.float32),
        0.25,
        np.array([[0.25, 0.25, 1.0, 1.0]], dtype=np.float32),
    ),
    (
        "mixed_around_zero_one",
        np.array([[-1.00, -0.50, 0.00, 0.50, 1.00]], dtype=np.float32),
        0.00,
        np.array([[0.0, 0.5, 1.0, 1.0, 1.0]], dtype=np.float32),
    ),
)


def _threshold_fixture() -> np.ndarray:
    return cast(
        np.ndarray,
        np.array(
            [0.10] * 32 + [0.20] * 32 + [0.70] * 32 + [0.80] * 32,
            dtype=np.float32,
        ).reshape(8, 16),
    )


def test_thresholding_import_is_service_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.thresholding import (
            apply_threshold_separation,
            detect_threshold,
        )

        forbidden = {
            "boto3",
            "celery",
            "cupy",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.engine.imager_pipeline.complete_pipeline",
            "mpips.pipelines",
            "mpips.worker",
            "mpips.workflows",
        }
        loaded = forbidden.intersection(sys.modules)
        assert not loaded, sorted(loaded)
        assert callable(apply_threshold_separation)
        assert callable(detect_threshold)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_threshold_separation_has_processing_ownership() -> None:
    assert canonical_apply_threshold_separation.__module__ == (
        "mpips.processing.thresholding"
    )
    assert apply_threshold_separation is canonical_apply_threshold_separation
    assert (
        radiography_apply_threshold_separation is canonical_apply_threshold_separation
    )


@pytest.mark.parametrize(
    "name,image,threshold,expected",
    EXPECTED_CPU_SEPARATION_CASES,
    ids=[case[0] for case in EXPECTED_CPU_SEPARATION_CASES],
)
def test_threshold_separation_matches_historical_cpu_goldens(
    name: str,
    image: np.ndarray,
    threshold: float,
    expected: np.ndarray,
) -> None:
    del name

    output = canonical_apply_threshold_separation(image, threshold)

    assert output.dtype == np.float32
    assert output.shape == image.shape
    np.testing.assert_array_equal(output, expected)


@pytest.mark.parametrize(
    "name,image,threshold,expected",
    EXPECTED_CPU_SEPARATION_CASES,
    ids=[case[0] for case in EXPECTED_CPU_SEPARATION_CASES],
)
def test_legacy_cpu_threshold_separation_matches_canonical(
    name: str,
    image: np.ndarray,
    threshold: float,
    expected: np.ndarray,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del name, expected
    monkeypatch.setattr(legacy_engine, "GPU_AVAILABLE", False)

    legacy_apply = cast(Any, legacy_engine.apply_threshold_separation)
    legacy_output = legacy_apply(image, threshold)
    canonical_output = canonical_apply_threshold_separation(image, threshold)

    np.testing.assert_array_equal(legacy_output, canonical_output)


@pytest.mark.parametrize("method", tuple(EXPECTED_THRESHOLDS))
def test_threshold_methods_match_historical_goldens(method: str) -> None:
    result = detect_threshold(_threshold_fixture(), method=method)

    np.testing.assert_equal(result, EXPECTED_THRESHOLDS[method])


@pytest.mark.parametrize("method", tuple(EXPECTED_THRESHOLDS))
def test_legacy_engine_adapter_matches_canonical_threshold(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = _threshold_fixture()
    monkeypatch.setitem(legacy_engine.CONFIG, "THRESHOLD_METHOD", method)

    legacy_result = cast(Any, legacy_engine.auto_threshold_detection)(image)
    canonical_result = detect_threshold(image, method=method)

    np.testing.assert_equal(legacy_result, canonical_result)


def test_existing_auto_threshold_wrapper_keeps_its_contract() -> None:
    image = _threshold_fixture()

    assert auto_threshold(image, method="auto") == 0.21826171875
    with pytest.raises(ValueError, match="only 'auto'"):
        auto_threshold(image, method="valley")


def test_debug_output_is_opt_in_and_keeps_threshold_value(tmp_path: Path) -> None:
    image = _threshold_fixture()

    result = detect_threshold(
        image,
        method="auto",
        debug=True,
        filename="fixture",
        output_dir=str(tmp_path),
    )

    np.testing.assert_equal(result, EXPECTED_THRESHOLDS["auto"])
    assert (tmp_path / "debug_histogram_thresholds_fixture.png").is_file()
