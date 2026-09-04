"""Thin array adapters over the canonical imager pipeline engine."""

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from mpips.pipelines.config import ImagerPipelineConfig
from mpips.pipelines.radiography import RadiographyPipeline
import mpips.processing as processing
from mpips.processing.thresholding import detect_threshold

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


def process_radiography_arrays(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    detector_mode: str,
    config: ImagerPipelineConfig | None = None,
    *,
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
    imagej_available: bool = True,
    stage_observer=None,
    threshold_method_override: str | None = None,
) -> np.ndarray:
    """Run arrays through the canonical array-only radiography pipeline."""
    config = config or ImagerPipelineConfig()
    extra_kwargs: dict[str, Any] = {}
    if stage_observer is not None:
        extra_kwargs["stage_observer"] = stage_observer
    if threshold_method_override is not None:
        extra_kwargs["threshold_method_override"] = threshold_method_override
    return RadiographyPipeline(
        config,
        imagej_available=imagej_available,
    ).process(
        raw,
        dark,
        flat,
        detector_mode,
        map_x=map_x,
        map_y=map_y,
        **extra_kwargs,
    )


CONFIG: dict[str, Any] = {
    "THRESHOLD_METHOD": "auto",
    "USE_DENOISE": True,
    "USE_CROP_ROTATE": True,
    "USE_NORMALIZE": False,
    "USE_THRESHOLD": True,
    "USE_INVERT": True,
    "USE_CONTRAST_ENHANCEMENT": True,
    "USE_CLAHE": True,
    "USE_MEDIAN_FILTER": True,
    "USE_FINAL_DENOISE": False,
}


def threshold_method_for_detector(
    detector_type: str, configured_method: str, diagnostic_override: str | None = None
) -> str:
    """Bypass destructive threshold separation for supported radiography modes."""
    if diagnostic_override is not None:
        return diagnostic_override
    return "none" if str(detector_type).upper() in {"BED", "TRX"} else configured_method


def auto_threshold_detection(image: np.ndarray) -> float:
    method = CONFIG.get("THRESHOLD_METHOD", "auto")
    return detect_threshold(image, method=method)


def process_single_image(
    raw_path: str | Path,
    dark_path: str | Path,
    flat_path: str | Path,
    output_path: str | Path,
    detector_type: str | None = None,
    map_x: np.ndarray | None = None,
    map_y: np.ndarray | None = None,
    stage_observer: Any = None,
    threshold_method_override: str | None = None,
) -> bool:
    raw = cv2.imread(str(raw_path), cv2.IMREAD_UNCHANGED)
    dark = cv2.imread(str(dark_path), cv2.IMREAD_UNCHANGED)
    flat = cv2.imread(str(flat_path), cv2.IMREAD_UNCHANGED)
    if raw is None or dark is None or flat is None:
        return False

    if threshold_method_override is None:
        configured = CONFIG.get("THRESHOLD_METHOD", "auto")
        threshold_method_override = threshold_method_for_detector(
            detector_type or "BED", configured
        )

    import mpips.pipelines.radiography as rad_mod

    saved_apply = None
    current_apply = globals().get("apply_threshold_separation")
    if (
        current_apply is not None
        and current_apply is not rad_mod.apply_threshold_separation
    ):
        saved_apply = rad_mod.apply_threshold_separation
        rad_mod.apply_threshold_separation = current_apply
    saved_auto = None
    current_auto = globals().get("auto_threshold_detection")
    if current_auto is not None and current_auto is not auto_threshold_detection:
        saved_auto = rad_mod.detect_threshold
        rad_mod.detect_threshold = lambda img, method=None: current_auto(img)
    try:
        config = ImagerPipelineConfig(
            use_denoise=CONFIG.get("USE_DENOISE", True),
            use_crop_rotate=CONFIG.get("USE_CROP_ROTATE", True),
            use_contrast_enhancement=CONFIG.get("USE_CONTRAST_ENHANCEMENT", True),
            use_clahe=CONFIG.get("USE_CLAHE", True),
            use_median_filter=CONFIG.get("USE_MEDIAN_FILTER", True),
        )
        out = process_radiography_arrays(
            raw,
            dark,
            flat,
            detector_mode=detector_type or "BED",
            config=config,
            map_x=map_x,
            map_y=map_y,
            stage_observer=stage_observer,
            threshold_method_override=threshold_method_override,
        )
        cv2.imwrite(str(output_path), out)
        return True
    finally:
        if saved_apply is not None:
            rad_mod.apply_threshold_separation = saved_apply
        if saved_auto is not None:
            rad_mod.detect_threshold = saved_auto
