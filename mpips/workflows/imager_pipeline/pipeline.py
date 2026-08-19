"""Thin array adapters over the canonical imager pipeline engine."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from mpips.engine.imager_pipeline import complete_pipeline as engine
import mpips.processing as processing
from mpips.workflows.imager_pipeline.models import ImagerPipelineConfig

MAX_UINT16 = 65535

apply_calibration_remap = processing.apply_calibration_remap
apply_clahe = processing.apply_clahe
apply_median_filter = processing.apply_median_filter
apply_threshold_separation = processing.apply_threshold_separation
auto_threshold = processing.auto_threshold
denoise_wavelet = processing.denoise_wavelet
flat_field_correction = processing.flat_field_correction
hybrid_median_filter = processing.hybrid_median_filter
imagej_equalize = processing.imagej_equalize
imagej_stretch = processing.imagej_stretch


@contextmanager
def _configured_engine(config: ImagerPipelineConfig) -> Iterator[None]:
    updates = config.to_legacy_engine_dict()
    previous = {key: engine.CONFIG.get(key) for key in updates}
    engine.CONFIG.update(updates)
    try:
        yield
    finally:
        engine.CONFIG.update(previous)


def crop_and_rotate(
    image: np.ndarray, detector_mode: str, config: ImagerPipelineConfig
) -> np.ndarray:
    return processing.crop_and_rotate(
        image,
        detector_mode,
        crop_top=config.crop_top,
        crop_bottom=config.crop_bottom,
        crop_left=config.crop_left,
        crop_right=config.crop_right,
    )


def _write_tiff(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Unable to write temporary TIFF: {path}")


def process_radiography_arrays(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    detector_mode: str,
    config: ImagerPipelineConfig | None = None,
    *,
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
) -> np.ndarray:
    """Run arrays through the promoted research pipeline without reimplementing it."""
    config = config or ImagerPipelineConfig()
    if raw.shape != dark.shape or raw.shape != flat.shape:
        raise ValueError(
            f"Raw/dark/flat shapes differ: {raw.shape}, {dark.shape}, {flat.shape}"
        )
    if map_x is not None or map_y is not None:
        if map_x is None or map_y is None:
            raise ValueError("Both map_x and map_y are required")

    with tempfile.TemporaryDirectory(prefix="mpips-engine-radiography-") as temporary:
        workspace = Path(temporary)
        raw_path = workspace / "raw.tiff"
        dark_path = workspace / "dark.tiff"
        flat_path = workspace / "flat.tiff"
        output_path = workspace / "processed.tiff"
        _write_tiff(raw_path, raw)
        _write_tiff(dark_path, dark)
        _write_tiff(flat_path, flat)
        with _configured_engine(config):
            succeeded = engine.process_single_image(
                str(raw_path),
                str(dark_path),
                str(flat_path),
                str(output_path),
                detector_type=detector_mode,
                map_x=map_x,
                map_y=map_y,
            )
        if not succeeded:
            raise RuntimeError("The canonical radiography pipeline failed")
        result = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
        if result is None:
            raise OSError("The canonical radiography pipeline produced no TIFF")
        return np.asarray(result, dtype=np.uint16)
