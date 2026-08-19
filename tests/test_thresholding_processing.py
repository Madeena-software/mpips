import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from mpips.engine.imager_pipeline import complete_pipeline as legacy_engine
from mpips.processing import auto_threshold
from mpips.processing.thresholding import detect_threshold

EXPECTED_THRESHOLDS = {
    "auto": np.float32(0.21826171875),
    "valley": np.float32(0.21826171875),
    "otsu": 0.0,
    "knee": np.float32(0.18681641),
    "percentile_25": np.float32(0.175),
    "secondary_peak": np.float32(0.118457034),
}


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

        from mpips.processing.thresholding import detect_threshold

        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine.imager_pipeline.complete_pipeline",
            "mpips.pipelines",
            "mpips.worker",
            "mpips.workflows",
        }
        loaded = forbidden.intersection(sys.modules)
        assert not loaded, sorted(loaded)
        assert callable(detect_threshold)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


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
