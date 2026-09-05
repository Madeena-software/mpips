"""Canonical typed config model for MPIPS imager pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ContrastMode(str, Enum):
    EQUALIZE = "equalize"
    STRETCH = "stretch"
    DISABLED = "disabled"


class ThresholdMethod(str, Enum):
    AUTO = "auto"
    VALLEY = "valley"
    OTSU = "otsu"
    KNEE = "knee"
    PERCENTILE_25 = "percentile_25"
    SECONDARY_PEAK = "secondary_peak"
    NONE = "none"


class WaveletMode(str, Enum):
    SOFT = "soft"
    HARD = "hard"


class WaveletMethod(str, Enum):
    BAYES_SHRINK = "BayesShrink"
    VISU_SHRINK = "VisuShrink"


class MedianFilterType(str, Enum):
    HYBRID_IMAGEJ = "hybrid_imagej"
    CIRCULAR_IMAGEJ = "circular_imagej"
    STANDARD = "standard"
    BILATERAL = "bilateral"
    ADAPTIVE = "adaptive"
    NLM = "nlm"
    MORPHOLOGICAL = "morphological"


VALID_THRESHOLD_METHODS = {
    "auto",
    "valley",
    "otsu",
    "knee",
    "percentile_25",
    "secondary_peak",
    "none",
    "off",
    "skip",
    "no",
}

VALID_WAVELET_MODES = {"soft", "hard"}
VALID_WAVELET_METHODS = {"BayesShrink", "VisuShrink"}
VALID_MEDIAN_FILTER_TYPES = {
    "hybrid_imagej",
    "circular_imagej",
    "standard",
    "bilateral",
    "adaptive",
    "nlm",
    "morphological",
}
VALID_CONTRAST_MODES = {"equalize", "stretch", "disabled"}


@dataclass
class ImagerPipelineConfig:
    """Authoritative single source of truth for radiograph image processing config."""

    # Cropping & rotation parameters
    crop_top: int = 0
    crop_bottom: int = 0
    crop_left: int = 0
    crop_right: int = 0
    use_crop_rotate: bool = True

    # Wavelet denoise parameters
    use_denoise: bool = True
    wavelet: str = "sym4"
    wavelet_level: int = 3
    wavelet_method: str = "BayesShrink"
    wavelet_mode: str = "soft"

    # Early dynamic-range histogram normalization parameters
    use_normalize: bool = False
    normalize_saturated_pixels: float = 0.35

    # Auto threshold parameters
    use_threshold: bool = True
    threshold_method: str = "auto"

    # Invert parameter
    use_invert: bool = True

    # ImageJ Contrast enhancement parameters
    use_contrast_enhancement: bool = True
    contrast_mode: str = "equalize"
    contrast_saturated_pixels: float = 5.0
    contrast_classic_equalization: bool = False

    # CLAHE parameters
    use_clahe: bool = True
    clahe_blocksize: int = 127
    clahe_histogram_bins: int = 256
    clahe_max_slope: float = 0.6
    clahe_fast: bool = False
    clahe_composite: bool = True

    # Optional final denoise
    use_final_denoise: bool = False

    # Median filter parameters (Effective runtime default is True)
    use_median_filter: bool = True
    median_filter_type: str = "hybrid_imagej"
    median_filter_radius: int = 2

    # Debug flag
    debug: bool = False

    def __init__(
        self,
        *,
        crop_top: int = 0,
        crop_bottom: int = 0,
        crop_left: int = 0,
        crop_right: int = 0,
        use_crop_rotate: bool = True,
        use_denoise: bool = True,
        wavelet: str = "sym4",
        wavelet_level: int = 3,
        wavelet_method: str = "BayesShrink",
        wavelet_mode: str = "soft",
        use_normalize: bool = False,
        normalize_saturated_pixels: float = 0.35,
        use_threshold: bool = True,
        threshold_method: str = "auto",
        use_invert: bool = True,
        use_contrast_enhancement: bool = True,
        contrast_mode: str | ContrastMode | None = None,
        contrast_saturated_pixels: float = 5.0,
        contrast_classic_equalization: bool = False,
        use_clahe: bool = True,
        clahe_blocksize: int = 127,
        clahe_histogram_bins: int = 256,
        clahe_max_slope: float = 0.6,
        clahe_fast: bool = False,
        clahe_composite: bool = True,
        use_final_denoise: bool = False,
        use_median_filter: bool = True,
        median_filter_type: str = "hybrid_imagej",
        median_filter_radius: int = 2,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        self.crop_top = crop_top
        self.crop_bottom = crop_bottom
        self.crop_left = crop_left
        self.crop_right = crop_right
        self.use_crop_rotate = use_crop_rotate
        self.use_denoise = use_denoise
        self.wavelet = wavelet
        self.wavelet_level = wavelet_level
        self.wavelet_method = wavelet_method
        self.wavelet_mode = wavelet_mode
        self.use_normalize = use_normalize
        self.normalize_saturated_pixels = normalize_saturated_pixels
        self.use_threshold = use_threshold
        self.threshold_method = threshold_method
        self.use_invert = use_invert
        self.contrast_saturated_pixels = contrast_saturated_pixels
        self.contrast_classic_equalization = contrast_classic_equalization
        self.use_clahe = use_clahe
        self.clahe_blocksize = clahe_blocksize
        self.clahe_histogram_bins = clahe_histogram_bins
        self.clahe_max_slope = clahe_max_slope
        self.clahe_fast = clahe_fast
        self.clahe_composite = clahe_composite
        self.use_final_denoise = use_final_denoise
        self.use_median_filter = use_median_filter
        self.median_filter_type = median_filter_type
        self.median_filter_radius = median_filter_radius
        self.debug = debug

        # Resolve threshold method vs enabled
        if threshold_method.lower() in ("none", "off", "skip", "no"):
            self.use_threshold = False
        elif "use_threshold" in kwargs:
            self.use_threshold = bool(kwargs["use_threshold"])

        # Determine contrast_mode authority
        if contrast_mode is not None:
            mode_str = (
                contrast_mode.value
                if isinstance(contrast_mode, ContrastMode)
                else str(contrast_mode)
            )
            if mode_str == ContrastMode.DISABLED.value or not use_contrast_enhancement:
                self.contrast_mode = ContrastMode.DISABLED.value
                self.use_contrast_enhancement = False
            else:
                self.contrast_mode = mode_str
                self.use_contrast_enhancement = True
        else:
            # Check legacy boolean keyword arguments if contrast_mode was not
            # explicitly provided
            has_eq = kwargs.get("contrast_equalize")

            has_norm = kwargs.get("contrast_normalize")
            if not use_contrast_enhancement:
                self.contrast_mode = ContrastMode.DISABLED.value
                self.use_contrast_enhancement = False
            elif has_eq is True:
                self.contrast_mode = ContrastMode.EQUALIZE.value
                self.use_contrast_enhancement = True
            elif has_eq is False and has_norm is True:
                self.contrast_mode = ContrastMode.STRETCH.value
                self.use_contrast_enhancement = True
            elif has_eq is False and has_norm is False:
                self.contrast_mode = ContrastMode.DISABLED.value
                self.use_contrast_enhancement = False
            else:
                self.contrast_mode = ContrastMode.EQUALIZE.value
                self.use_contrast_enhancement = use_contrast_enhancement

        self._validate()

    @property
    def contrast_equalize(self) -> bool:
        """Derived property indicating if equalization branch is active."""  # noqa: E501
        return (
            self.use_contrast_enhancement
            and self.contrast_mode == ContrastMode.EQUALIZE.value
        )

    @property
    def contrast_normalize(self) -> bool:
        """Derived property indicating if contrast stretch branch is active."""
        return (
            self.use_contrast_enhancement
            and self.contrast_mode == ContrastMode.STRETCH.value
        )

    def _validate(self) -> None:
        if (
            self.crop_top < 0
            or self.crop_bottom < 0
            or self.crop_left < 0
            or self.crop_right < 0
        ):
            raise ValueError(
                f"Crop parameters must be >= 0: "
                f"({self.crop_top}, {self.crop_bottom}, "
                f"{self.crop_left}, {self.crop_right})"
            )

        if self.wavelet_level <= 0:
            raise ValueError(f"wavelet_level must be > 0, got {self.wavelet_level}")

        if not (0.0 <= self.contrast_saturated_pixels <= 100.0):
            raise ValueError(
                f"contrast_saturated_pixels must be in [0, 100], "
                f"got {self.contrast_saturated_pixels}"
            )

        if not (0.0 <= self.normalize_saturated_pixels <= 100.0):
            raise ValueError(
                f"normalize_saturated_pixels must be in [0, 100], "
                f"got {self.normalize_saturated_pixels}"
            )

        if self.clahe_blocksize <= 0:
            raise ValueError(f"clahe_blocksize must be > 0, got {self.clahe_blocksize}")

        if self.clahe_histogram_bins <= 0:
            raise ValueError(
                f"clahe_histogram_bins must be > 0, got {self.clahe_histogram_bins}"
            )

        if self.clahe_max_slope <= 0.0:
            raise ValueError(
                f"clahe_max_slope must be > 0.0, got {self.clahe_max_slope}"
            )

        if self.median_filter_radius <= 0:
            raise ValueError(
                f"median_filter_radius must be > 0, got {self.median_filter_radius}"
            )

        thresh_lower = self.threshold_method.lower()
        if thresh_lower not in VALID_THRESHOLD_METHODS:
            raise ValueError(
                f"Invalid threshold_method {self.threshold_method!r}. "
                f"Must be one of {sorted(VALID_THRESHOLD_METHODS)}"
            )

        if self.wavelet_mode not in VALID_WAVELET_MODES:
            raise ValueError(
                f"Invalid wavelet_mode {self.wavelet_mode!r}. "
                f"Must be one of {sorted(VALID_WAVELET_MODES)}"
            )

        if self.wavelet_method not in VALID_WAVELET_METHODS:
            raise ValueError(
                f"Invalid wavelet_method {self.wavelet_method!r}. "
                f"Must be one of {sorted(VALID_WAVELET_METHODS)}"
            )

        if self.median_filter_type not in VALID_MEDIAN_FILTER_TYPES:
            raise ValueError(
                f"Invalid median_filter_type {self.median_filter_type!r}. "
                f"Must be one of {sorted(VALID_MEDIAN_FILTER_TYPES)}"
            )

        if self.contrast_mode not in VALID_CONTRAST_MODES:
            raise ValueError(
                f"Invalid contrast_mode {self.contrast_mode!r}. "
                f"Must be one of {sorted(VALID_CONTRAST_MODES)}"
            )

    def to_legacy_engine_dict(self) -> dict[str, Any]:
        """Convert canonical config into flat legacy engine CONFIG dictionary."""
        return {
            "DEBUG": self.debug,
            "USE_GPU": False,
            "USE_IMAGEJ": True,
            "USE_DENOISE": self.use_denoise,
            "USE_CROP_ROTATE": self.use_crop_rotate,
            "USE_CLAHE": self.use_clahe,
            "USE_CONTRAST_ENHANCEMENT": self.use_contrast_enhancement,
            "USE_NORMALIZE": self.use_normalize,
            "USE_INVERT": self.use_invert,
            "USE_FINAL_DENOISE": self.use_final_denoise,
            "USE_MEDIAN_FILTER": self.use_median_filter,
            "MEDIAN_FILTER_RADIUS": self.median_filter_radius,
            "MEDIAN_FILTER_TYPE": self.median_filter_type,
            "THRESHOLD_METHOD": self.threshold_method if self.use_threshold else "none",
            "WAVELET_TYPE": self.wavelet,
            "WAVELET_LEVEL": self.wavelet_level,
            "WAVELET_METHOD": self.wavelet_method,
            "WAVELET_MODE": self.wavelet_mode,
            "CROP_TOP": self.crop_top,
            "CROP_BOTTOM": self.crop_bottom,
            "CROP_LEFT": self.crop_left,
            "CROP_RIGHT": self.crop_right,
            "CONTRAST_SATURATED_PIXELS": self.contrast_saturated_pixels,
            "CONTRAST_NORMALIZE": self.contrast_normalize,
            "CONTRAST_EQUALIZE": self.contrast_equalize,
            "CONTRAST_CLASSIC_EQUALIZATION": self.contrast_classic_equalization,
            "CLAHE_BLOCKSIZE": self.clahe_blocksize,
            "CLAHE_HISTOGRAM_BINS": self.clahe_histogram_bins,
            "CLAHE_MAX_SLOPE": self.clahe_max_slope,
            "CLAHE_FAST": self.clahe_fast,
            "CLAHE_COMPOSITE": self.clahe_composite,
            "NORMALIZE_SATURATED_PIXELS": self.normalize_saturated_pixels,
            "NUM_WORKERS": None,
            "RAW_PATH": "",
            "DARK_PATH": "",
            "FLAT_PATH": "",
            "OUTPUT_DIR": "",
            "USE_CALIBRATION": False,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert canonical config into structured, unambiguous JSON representation."""
        return {
            "schema_version": "2.0.0",
            "denoise": {
                "enabled": self.use_denoise,
                "wavelet": {
                    "type": self.wavelet,
                    "level": self.wavelet_level,
                    "method": self.wavelet_method,
                    "mode": self.wavelet_mode,
                },
            },
            "crop_rotate": {
                "enabled": self.use_crop_rotate,
                "crop": {
                    "top": self.crop_top,
                    "bottom": self.crop_bottom,
                    "left": self.crop_left,
                    "right": self.crop_right,
                },
            },
            "early_normalize": {
                "enabled": self.use_normalize,
                "saturated_pixels": self.normalize_saturated_pixels,
            },
            "threshold": {
                "enabled": self.use_threshold
                and self.threshold_method.lower() not in ("none", "off", "skip", "no"),
                "method": self.threshold_method if self.use_threshold else "none",
            },
            "invert": {
                "enabled": self.use_invert,
            },
            "contrast": {
                "enabled": self.use_contrast_enhancement,
                "mode": self.contrast_mode,
                "equalize": {
                    "classic": self.contrast_classic_equalization,
                },
                "stretch": {
                    "saturated_pixels": self.contrast_saturated_pixels,
                    "normalize": self.contrast_normalize,
                },
            },
            "clahe": {
                "enabled": self.use_clahe,
                "blocksize": self.clahe_blocksize,
                "histogram_bins": self.clahe_histogram_bins,
                "max_slope": self.clahe_max_slope,
                "fast": self.clahe_fast,
                "composite": self.clahe_composite,
            },
            "final_denoise": {
                "enabled": self.use_final_denoise,
            },
            "median_filter": {
                "enabled": self.use_median_filter,
                "type": self.median_filter_type,
                "radius": self.median_filter_radius,
            },
            "debug": self.debug,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImagerPipelineConfig:
        """Construct ImagerPipelineConfig from a structured dict or flat dict."""
        structured_sections = {
            "schema_version",
            "denoise",
            "crop_rotate",
            "early_normalize",
            "threshold",
            "invert",
            "contrast",
            "clahe",
            "final_denoise",
            "median_filter",
        }
        if any(k in data for k in structured_sections):

            denoise = data.get("denoise", {})
            wavelet = denoise.get("wavelet", {})
            crop_rotate = data.get("crop_rotate", {})
            crop = crop_rotate.get("crop", {})
            early_norm = data.get("early_normalize", {})
            threshold = data.get("threshold", {})
            contrast = data.get("contrast", {})
            eq = contrast.get("equalize", {})
            stretch = contrast.get("stretch", {})
            clahe = data.get("clahe", {})
            median = data.get("median_filter", {})

            c_enabled = contrast.get("enabled", True)
            c_mode = contrast.get("mode", "equalize")
            if not c_enabled or c_mode == "disabled":
                resolved_c_mode = "disabled"
                resolved_c_enabled = False
            else:
                resolved_c_mode = c_mode
                resolved_c_enabled = True

            t_enabled = threshold.get("enabled", True)
            t_method = threshold.get("method", "auto")
            if not t_enabled:
                resolved_t_method = "none"
                resolved_use_t = False
            else:
                resolved_t_method = t_method
                resolved_use_t = t_method.lower() not in ("none", "off", "skip", "no")

            return cls(
                crop_top=crop.get("top", 0),
                crop_bottom=crop.get("bottom", 0),
                crop_left=crop.get("left", 0),
                crop_right=crop.get("right", 0),
                use_crop_rotate=crop_rotate.get("enabled", True),
                use_denoise=denoise.get("enabled", True),
                wavelet=wavelet.get("type", "sym4"),
                wavelet_level=wavelet.get("level", 3),
                wavelet_method=wavelet.get("method", "BayesShrink"),
                wavelet_mode=wavelet.get("mode", "soft"),
                use_normalize=early_norm.get("enabled", False),
                normalize_saturated_pixels=early_norm.get("saturated_pixels", 0.35),
                use_threshold=resolved_use_t,
                threshold_method=resolved_t_method,
                use_invert=data.get("invert", {}).get("enabled", True),
                use_contrast_enhancement=resolved_c_enabled,
                contrast_mode=resolved_c_mode,
                contrast_saturated_pixels=stretch.get("saturated_pixels", 5.0),
                contrast_classic_equalization=eq.get("classic", False),
                use_clahe=clahe.get("enabled", True),
                clahe_blocksize=clahe.get("blocksize", 127),
                clahe_histogram_bins=clahe.get("histogram_bins", 256),
                clahe_max_slope=clahe.get("max_slope", 0.6),
                clahe_fast=clahe.get("fast", False),
                clahe_composite=clahe.get("composite", True),
                use_final_denoise=data.get("final_denoise", {}).get("enabled", False),
                use_median_filter=median.get("enabled", True),
                median_filter_type=median.get("type", "hybrid_imagej"),
                median_filter_radius=median.get("radius", 2),
                debug=data.get("debug", False),
            )
        else:
            return cls(**data)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ImagerPipelineConfig:
        """Resolve config from environment overrides overlaid on canonical defaults."""
        if env is None:
            env = os.environ

        parsed: dict[str, Any] = {}

        def parse_bool(val: str) -> bool:
            return val.lower() in ("1", "true", "yes", "on")

        env_mappings: dict[str, tuple[str, str]] = {
            "DEBUG": ("debug", "bool"),
            "USE_DENOISE": ("use_denoise", "bool"),
            "USE_CROP_ROTATE": ("use_crop_rotate", "bool"),
            "WAVELET_TYPE": ("wavelet", "str"),
            "WAVELET_LEVEL": ("wavelet_level", "int"),
            "WAVELET_METHOD": ("wavelet_method", "str"),
            "WAVELET_MODE": ("wavelet_mode", "str"),
            "CROP_TOP": ("crop_top", "int"),
            "CROP_BOTTOM": ("crop_bottom", "int"),
            "CROP_LEFT": ("crop_left", "int"),
            "CROP_RIGHT": ("crop_right", "int"),
            "USE_NORMALIZE": ("use_normalize", "bool"),
            "NORMALIZE_SATURATED_PIXELS": ("normalize_saturated_pixels", "float"),
            "THRESHOLD_METHOD": ("threshold_method", "str"),
            "USE_INVERT": ("use_invert", "bool"),
            "CONTRAST_SATURATED_PIXELS": ("contrast_saturated_pixels", "float"),
            "CONTRAST_CLASSIC_EQUALIZATION": ("contrast_classic_equalization", "bool"),
            "USE_CLAHE": ("use_clahe", "bool"),
            "CLAHE_BLOCKSIZE": ("clahe_blocksize", "int"),
            "CLAHE_HISTOGRAM_BINS": ("clahe_histogram_bins", "int"),
            "CLAHE_MAX_SLOPE": ("clahe_max_slope", "float"),
            "CLAHE_FAST": ("clahe_fast", "bool"),
            "CLAHE_COMPOSITE": ("clahe_composite", "bool"),
            "USE_FINAL_DENOISE": ("use_final_denoise", "bool"),
            "USE_MEDIAN_FILTER": ("use_median_filter", "bool"),
            "MEDIAN_FILTER_TYPE": ("median_filter_type", "str"),
            "MEDIAN_FILTER_RADIUS": ("median_filter_radius", "int"),
        }

        for env_key, (field_name, field_type) in env_mappings.items():
            if env_key in env and env[env_key] != "":
                raw_val = env[env_key]
                if field_type == "bool":
                    parsed[field_name] = parse_bool(raw_val)
                elif field_type == "int":
                    parsed[field_name] = int(raw_val)
                elif field_type == "float":
                    parsed[field_name] = float(raw_val)
                else:
                    parsed[field_name] = raw_val

        # Handle contrast legacy env variables deterministically
        has_c_enh = "USE_CONTRAST_ENHANCEMENT" in env
        c_enh = parse_bool(env["USE_CONTRAST_ENHANCEMENT"]) if has_c_enh else True
        has_eq = "CONTRAST_EQUALIZE" in env
        eq_val = parse_bool(env["CONTRAST_EQUALIZE"]) if has_eq else True
        has_norm = "CONTRAST_NORMALIZE" in env
        norm_val = parse_bool(env["CONTRAST_NORMALIZE"]) if has_norm else True

        if has_c_enh and not c_enh:
            parsed["contrast_mode"] = ContrastMode.DISABLED.value
            parsed["use_contrast_enhancement"] = False
        elif has_eq and eq_val:
            parsed["contrast_mode"] = ContrastMode.EQUALIZE.value
            parsed["use_contrast_enhancement"] = True
        elif has_eq and not eq_val and norm_val:
            parsed["contrast_mode"] = ContrastMode.STRETCH.value
            parsed["use_contrast_enhancement"] = True
        elif has_eq and not eq_val and not norm_val:
            parsed["contrast_mode"] = ContrastMode.DISABLED.value
            parsed["use_contrast_enhancement"] = False

        return cls(**parsed)


def get_default_config() -> ImagerPipelineConfig:
    """Return a fresh instance of the canonical default configuration."""
    return ImagerPipelineConfig()
