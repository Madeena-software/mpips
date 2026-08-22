"""Contract tests for the canonical file-oriented imager adapter."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from mpips.pipelines.config import ImagerPipelineConfig
from mpips.workflows.imager_pipeline.file_runner import (
    _detect_detector_type,
    process_tiff_triplet,
)


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


def _write_triplet(
    directory: Path, *, raw_name: str = "BED_fixture.tiff"
) -> tuple[Path, Path, Path]:
    raw, dark, flat = _recipe_fixture()
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / raw_name
    dark_path = directory / "dark.tiff"
    flat_path = directory / "flat.tiff"
    assert cv2.imwrite(str(raw_path), raw)
    assert cv2.imwrite(str(dark_path), dark)
    assert cv2.imwrite(str(flat_path), flat)
    return raw_path, dark_path, flat_path


def _maps(kind: str) -> tuple[np.ndarray | None, np.ndarray | None]:
    if kind == "none":
        return None, None
    if kind == "identity":
        coordinates = np.indices((24, 24), dtype=np.float32)
        return coordinates[1], coordinates[0]
    if kind == "expanded":
        coordinates = np.indices((28, 28), dtype=np.float32)
        return coordinates[1], coordinates[0]
    if kind == "out_of_bounds":
        coordinates = np.indices((24, 24), dtype=np.float32)
        map_x = coordinates[1]
        map_y = coordinates[0]
        map_x[0, 0] = -1
        map_y[-1, -1] = 24
        return map_x, map_y
    raise AssertionError(f"unknown map kind: {kind}")


@pytest.mark.parametrize(
    "keyword", ("THORAX", "HUMERI", "HUMERUS", "CERVICAL", "CLAVIKULA", "CLAVICULA")
)
def test_detector_keywords_preserve_legacy_mapping(keyword: str) -> None:
    assert _detect_detector_type(f"{keyword}_fixture.tiff") == "TRX"
    assert _detect_detector_type("BED_fixture.tiff") == "BED"


_PARITY_CASES = (
    ("default", ImagerPipelineConfig(), "BED", "BED_fixture.tiff", "none", True),
    (
        "use_denoise_false",
        _minimal_config(use_denoise=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "use_crop_rotate_false",
        _minimal_config(use_crop_rotate=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "threshold_disabled",
        _minimal_config(use_threshold=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "use_invert_false",
        _minimal_config(use_invert=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "contrast_disabled",
        _minimal_config(use_contrast_enhancement=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "contrast_stretch",
        _minimal_config(use_contrast_enhancement=True, contrast_mode="stretch"),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "clahe_disabled",
        _minimal_config(use_clahe=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "final_denoise_true",
        _minimal_config(use_final_denoise=True),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "median_disabled",
        _minimal_config(use_median_filter=False),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "median_standard",
        _minimal_config(
            use_median_filter=True,
            median_filter_type="standard",
            median_filter_radius=1,
        ),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "normalize_true",
        _minimal_config(use_normalize=True),
        "BED",
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "detector_bed_fallback",
        _minimal_config(),
        None,
        "BED_fixture.tiff",
        "none",
        True,
    ),
    (
        "detector_trx_nonzero_crop",
        _minimal_config(crop_top=1, crop_bottom=2, crop_left=2, crop_right=1),
        None,
        "THORAX_fixture.tiff",
        "none",
        True,
    ),
    (
        "identity_remap",
        _minimal_config(),
        "BED",
        "BED_fixture.tiff",
        "identity",
        True,
    ),
    (
        "expanded_remap",
        _minimal_config(),
        "BED",
        "BED_fixture.tiff",
        "expanded",
        True,
    ),
    (
        "out_of_bounds_remap",
        _minimal_config(),
        "BED",
        "BED_fixture.tiff",
        "out_of_bounds",
        True,
    ),
    (
        "imagej_unavailable",
        _minimal_config(
            use_contrast_enhancement=True,
            contrast_mode="equalize",
            use_clahe=True,
            use_median_filter=True,
            median_filter_type="hybrid_imagej",
        ),
        "BED",
        "BED_fixture.tiff",
        "none",
        False,
    ),
)


_FROZEN_PARITY = {
    "default": (
        (24, 24),
        "f176b16a29fc3a37fee76a133f88bc0018514210cccb461218008933186e18b7",
    ),
    "use_denoise_false": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "use_crop_rotate_false": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "threshold_disabled": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "use_invert_false": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "contrast_disabled": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "contrast_stretch": (
        (24, 24),
        "a00dab9dee778043443e5e692be5745b89451138f3266a27bdfd6e89d779603e",
    ),
    "clahe_disabled": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "final_denoise_true": (
        (24, 24),
        "5ab54e4f25b171a9d5ce1c1c5890233e9efad9d3a99424e653bdb62aacbfae7f",
    ),
    "median_disabled": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "median_standard": (
        (24, 24),
        "5107e851189513eb1011f27da6076add9eaaf1390c9c416e2252a4bc2e5ed739",
    ),
    "normalize_true": (
        (24, 24),
        "4cf9816ed1062189ff0c8d427fba5e912cc68fc9af76cf7f08fd255977de3b33",
    ),
    "detector_bed_fallback": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "detector_trx_nonzero_crop": (
        (21, 21),
        "086deda818b953e06b2e8fcc44c8d977f99cc8c433992022661cc8f1a32dba80",
    ),
    "identity_remap": (
        (24, 24),
        "03e987307af29fa98842a2915b56586c7cf75d59fec3ef4aff43201751fa9919",
    ),
    "expanded_remap": (
        (28, 28),
        "c164cd38dbf8cf6b9d26a0b85ec9da81eeba25238d6e227497ecc42abcddf293",
    ),
    "out_of_bounds_remap": (
        (24, 24),
        "5645c5db0c6c675ac079e3b2e88cfaeb3ab8bf1ab97d2224ba4422844cc90a07",
    ),
    "imagej_unavailable": (
        (24, 24),
        "d29e8c4fb31ee995ccdca95c12c3ab380b58674cdcb4096043e2970bb8c25a09",
    ),
}


@pytest.mark.parametrize(
    "name,config,detector_type,raw_name,map_kind,imagej_available",
    _PARITY_CASES,
    ids=[case[0] for case in _PARITY_CASES],
)
def test_file_runner_matches_frozen_stage_6e2a_parity(
    tmp_path: Path,
    name: str,
    config: ImagerPipelineConfig,
    detector_type: str | None,
    raw_name: str,
    map_kind: str,
    imagej_available: bool,
) -> None:
    raw_path, dark_path, flat_path = _write_triplet(
        tmp_path / "inputs", raw_name=raw_name
    )
    map_x, map_y = _maps(map_kind)
    original_maps: tuple[np.ndarray, np.ndarray] | None = None
    if map_x is not None and map_y is not None:
        original_maps = (map_x.copy(), map_y.copy())
    canonical_output = tmp_path / "canonical" / f"{name}.tiff"

    assert process_tiff_triplet(
        raw_path,
        dark_path,
        flat_path,
        canonical_output,
        detector_type=detector_type,
        config=config,
        map_x=map_x,
        map_y=map_y,
        imagej_available=imagej_available,
    )

    actual = cv2.imread(str(canonical_output), cv2.IMREAD_UNCHANGED)
    assert actual is not None
    assert actual.dtype == np.uint16
    expected_shape, expected_hash = _FROZEN_PARITY[name]
    assert actual.shape == expected_shape
    output_hash = hashlib.sha256(actual.tobytes()).hexdigest()
    assert output_hash == expected_hash
    print(f"{name}: {actual.shape} {actual.dtype} {output_hash}")

    if original_maps is not None:
        np.testing.assert_array_equal(map_x, original_maps[0])
        np.testing.assert_array_equal(map_y, original_maps[1])


def test_file_runner_missing_input_returns_false(tmp_path: Path) -> None:
    assert not process_tiff_triplet(
        tmp_path / "missing.tiff",
        tmp_path / "dark.tiff",
        tmp_path / "flat.tiff",
        tmp_path / "output" / "result.tiff",
    )


def test_file_runner_handles_imread_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_path, dark_path, flat_path = _write_triplet(tmp_path / "inputs")

    monkeypatch.setattr(cv2, "imread", lambda *_args: None)

    assert not process_tiff_triplet(
        raw_path,
        dark_path,
        flat_path,
        tmp_path / "output" / "result.tiff",
    )


def test_file_runner_reports_tiff_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_path, dark_path, flat_path = _write_triplet(tmp_path / "inputs")

    monkeypatch.setattr(cv2, "imwrite", lambda *_args: False)

    assert not process_tiff_triplet(
        raw_path,
        dark_path,
        flat_path,
        tmp_path / "output" / "result.tiff",
        config=_minimal_config(),
    )


def test_file_runner_import_is_service_and_engine_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script = """
import sys

from mpips.workflows.imager_pipeline.file_runner import process_tiff_triplet

assert callable(process_tiff_triplet)
forbidden = (
    "mpips.engine",
    "mpips.api",
    "mpips.worker",
    "mpips.conversion",
    "fastapi",
    "celery",
    "boto3",
    "torch",
    "matplotlib",
)
loaded = sorted(
    name
    for name in sys.modules
    if any(name == item or name.startswith(item + ".") for item in forbidden)
)
assert not loaded, loaded
assert "mpips.pipelines.radiography" in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
