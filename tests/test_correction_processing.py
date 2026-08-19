import hashlib
import subprocess
import sys
import textwrap
from typing import Any, cast

import numpy as np
import pytest

import mpips.processing.radiography as radiography
from mpips.engine.imager_pipeline import complete_pipeline as legacy_engine
from mpips.processing import flat_field_correction
from mpips.processing.correction import (
    flat_field_correction as canonical_flat_field_correction,
)

radiography_flat_field_correction = cast(
    Any, getattr(radiography, "flat_field_correction")
)

HISTORICAL_FFC_CASES = (
    (
        "uint16_representative",
        np.array([[10, 20, 30], [40, 50, 60]], dtype=np.uint16),
        np.full((2, 3), 5, dtype=np.uint16),
        np.array([[5, 15, 25], [35, 45, 55]], dtype=np.uint16),
        np.array([[0, 37, 31], [29, 28, 27]], dtype=np.uint16),
        "ac3c5d0668a6c609e7909832ef6e221fbfb5878acb424b80e22ecd4367fc2a13",
    ),
    (
        "uint8_representative",
        np.array([[10, 20], [30, 40]], dtype=np.uint8),
        np.zeros((2, 2), dtype=np.uint8),
        np.full((2, 2), 100, dtype=np.uint8),
        np.array([[10, 20], [30, 40]], dtype=np.uint8),
        "5f53c0ff07ba5d9a330e68c95dabb1a9bc49e29f9ed53f6fa7c6d99abb000050",
    ),
    (
        "float32_representative",
        np.array([[0.25, 0.5], [0.75, 1.0]], dtype=np.float32),
        np.zeros((2, 2), dtype=np.float32),
        np.full((2, 2), 2.0, dtype=np.float32),
        np.array([[0.25, 0.5], [0.75, 1.0]], dtype=np.float32),
        "bb5f01878113000f16ce91be1275eda29f7ca5e04fb3e13f652a94ed5b480b5d",
    ),
    (
        "zero_denominator_pixel",
        np.array([[10, 20], [30, 40]], dtype=np.uint16),
        np.full((2, 2), 5, dtype=np.uint16),
        np.array([[5, 15], [25, 35]], dtype=np.uint16),
        np.array([[0, 22], [18, 17]], dtype=np.uint16),
        "a40b6c95cbef92bb9c75b577b1f9ff4b97281d88f633e349775b97d488fc0d63",
    ),
    (
        "raw_below_dark",
        np.array([[4, 6], [8, 10]], dtype=np.uint16),
        np.full((2, 2), 5, dtype=np.uint16),
        np.full((2, 2), 15, dtype=np.uint16),
        np.array([[0, 1], [3, 5]], dtype=np.uint16),
        "d02df5b4d982e1758366c137a7ca4fa95d7616575ab190487be7194e43489afc",
    ),
    (
        "flat_below_dark",
        np.array([[10, 20], [30, 40]], dtype=np.uint16),
        np.full((2, 2), 10, dtype=np.uint16),
        np.array([[5, 15], [5, 15]], dtype=np.uint16),
        np.array([[0, 5], [0, 15]], dtype=np.uint16),
        "32faf7886ce88c7a053f6f8b4aec0f8fe94405d3dd38ce48233ee52a9ee5f7d2",
    ),
    (
        "all_zero_denominator",
        np.array([[10, 20], [30, 40]], dtype=np.float32),
        np.full((2, 2), 5, dtype=np.float32),
        np.full((2, 2), 5, dtype=np.float32),
        np.zeros((2, 2), dtype=np.float32),
        "374708fff7719dd5979ec875d56cd2286f6d3cf7ec317a3b25632aab28ec37bb",
    ),
)


def test_correction_import_is_scientific_and_service_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.correction import flat_field_correction

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
        assert callable(flat_field_correction)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_flat_field_correction_has_one_processing_owner() -> None:
    legacy_flat_field = cast(Any, legacy_engine.flat_field_correction)
    workflow_flat_field = cast(
        Any,
        __import__(
            "mpips.workflows.imager_pipeline.pipeline",
            fromlist=["flat_field_correction"],
        ).flat_field_correction,
    )

    assert canonical_flat_field_correction.__module__ == "mpips.processing.correction"
    assert flat_field_correction is canonical_flat_field_correction
    assert radiography_flat_field_correction is canonical_flat_field_correction
    assert (
        legacy_flat_field.__module__ == "mpips.engine.imager_pipeline.complete_pipeline"
    )
    assert workflow_flat_field is flat_field_correction


@pytest.mark.parametrize(
    "name,raw,dark,flat,expected,expected_hash",
    HISTORICAL_FFC_CASES,
    ids=[case[0] for case in HISTORICAL_FFC_CASES],
)
def test_flat_field_correction_matches_historical_cpu_goldens(
    name: str,
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    expected: np.ndarray,
    expected_hash: str,
) -> None:
    del name

    output = canonical_flat_field_correction(raw, dark, flat)

    assert output.shape == raw.shape
    assert output.dtype == expected.dtype
    np.testing.assert_array_equal(output, expected)
    assert hashlib.sha256(output.tobytes()).hexdigest() == expected_hash


@pytest.mark.parametrize(
    "name,raw,dark,flat,expected,_expected_hash",
    HISTORICAL_FFC_CASES,
    ids=[case[0] for case in HISTORICAL_FFC_CASES],
)
def test_legacy_cpu_flat_field_correction_matches_canonical(
    name: str,
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    expected: np.ndarray,
    _expected_hash: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del name, expected, _expected_hash
    monkeypatch.setattr(legacy_engine, "GPU_AVAILABLE", False)

    legacy_output = cast(Any, legacy_engine.flat_field_correction)(raw, dark, flat)
    canonical_output = canonical_flat_field_correction(raw, dark, flat)

    np.testing.assert_array_equal(legacy_output, canonical_output)
