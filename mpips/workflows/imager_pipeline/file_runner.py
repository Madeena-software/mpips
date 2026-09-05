"""File-oriented adapter for the canonical radiography pipeline."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mpips.pipelines.config import ImagerPipelineConfig
from mpips.pipelines.radiography import RadiographyPipeline

_TRX_KEYWORDS = (
    "THORAX",
    "HUMERI",
    "HUMERUS",
    "CERVICAL",
    "CLAVIKULA",
    "CLAVICULA",
)


def _detect_detector_type(filename: str) -> str:
    name = filename.upper()
    return "TRX" if any(keyword in name for keyword in _TRX_KEYWORDS) else "BED"


def process_tiff_triplet(
    raw_path: str | Path,
    dark_path: str | Path,
    flat_path: str | Path,
    output_path: str | Path,
    detector_type: str | None = None,
    config: ImagerPipelineConfig | None = None,
    *,
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
    imagej_available: bool = True,
) -> bool:
    """Process a raw/dark/flat TIFF triplet and write one uint16 TIFF."""
    try:
        raw = cv2.imread(str(raw_path), cv2.IMREAD_UNCHANGED)
        dark = cv2.imread(str(dark_path), cv2.IMREAD_UNCHANGED)
        flat = cv2.imread(str(flat_path), cv2.IMREAD_UNCHANGED)
        if raw is None or dark is None or flat is None:
            return False
        if raw.ndim != 2 or dark.ndim != 2 or flat.ndim != 2:
            return False

        detector = detector_type or _detect_detector_type(Path(raw_path).name)
        result = RadiographyPipeline(
            config or ImagerPipelineConfig(),
            imagej_available=imagej_available,
        ).process(
            raw,
            dark,
            flat,
            detector,
            map_x=map_x,
            map_y=map_y,
        )
        result = np.asarray(result, dtype=np.uint16)
        if result.ndim != 2:
            return False

        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(target), result))
    except Exception:
        return False
