"""Configuration and result models for the imager pipeline workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NeuralCalibrationConfig:
    """Deterministic dot-grid model training and remap configuration."""

    epochs: int = 5000
    learning_rate: float = 1e-3
    target_loss: float = 5.0
    hidden_dim: int = 64
    seed: int = 42
    smoothness_weight: float = 1e-3
    edge_balance_weight: float = 0.3
    center_marker_min_ratio: float = 1.5
    threshold: int = 128
    minimum_contour_area: float = 10.0
    row_tolerance: float = 50.0
    remap_step: int = 4
    inverse_iterations: int = 10
    batch_size: int = 262144
    device: str = "auto"
    canvas_mode: str = "fixed"
    expanded_bounds_step: int = 4
    expanded_margin: int = 16
    min_straightness_reduction: float = 50.0
    min_reprojection_reduction: float = 50.0
    min_spacing_reduction: float = 30.0
    min_diameter_reduction: float = 0.0
    force_retrain: bool = False

    def cache_dict(self) -> dict[str, Any]:
        """Return fields that affect generated calibration artifacts."""
        values = asdict(self)
        values.pop("force_retrain", None)
        return values


@dataclass(frozen=True)
class ImagerPipelineConfig:
    """Exact defaults from the research imager pipeline notebook."""

    crop_top: int = 0
    crop_bottom: int = 0
    crop_left: int = 0
    crop_right: int = 0
    use_denoise: bool = True
    wavelet: str = "sym4"
    wavelet_level: int = 3
    wavelet_method: str = "BayesShrink"
    wavelet_mode: str = "soft"
    use_normalize: bool = False
    normalize_saturated_pixels: float = 0.35
    threshold_method: str = "auto"
    use_invert: bool = True
    use_contrast_enhancement: bool = True
    contrast_saturated_pixels: float = 5.0
    contrast_normalize: bool = True
    contrast_equalize: bool = True
    contrast_classic_equalization: bool = False
    use_clahe: bool = True
    clahe_blocksize: int = 127
    clahe_histogram_bins: int = 256
    clahe_max_slope: float = 0.6
    clahe_fast: bool = False
    clahe_composite: bool = True
    use_final_denoise: bool = False
    use_median_filter: bool = True
    median_filter_type: str = "hybrid_imagej"
    median_filter_radius: int = 2
    debug: bool = False


@dataclass(frozen=True)
class GainRecord:
    id: str
    path: Path
    dark: Any
    flat: Any
    camera_params: dict[str, Any]
    detector_mode: str


@dataclass
class GainCatalog:
    records: dict[str, GainRecord]

    def require(self, gain_id: str) -> GainRecord:
        try:
            return self.records[gain_id]
        except KeyError as exc:
            raise KeyError(f"No gain NPZ found for gainid {gain_id!r}") from exc


@dataclass(frozen=True)
class CalibrationArtifacts:
    fingerprint: str
    directory: Path
    model_path: Path
    remap_path: Path
    mask_path: Path
    metrics_path: Path
    metadata_path: Path
    image_shape: tuple[int, int]
    validated: bool
    cache_hit: bool = False


@dataclass(frozen=True)
class BatchItemResult:
    source: str
    status: str
    gain_id: str | None = None
    output: str | None = None
    source_sha256: str | None = None
    elapsed_seconds: float = 0.0
    error: str | None = None


@dataclass(frozen=True)
class BatchResult:
    run_id: str
    run_directory: Path
    manifest_path: Path
    items: tuple[BatchItemResult, ...] = field(default_factory=tuple)

    @property
    def succeeded(self) -> int:
        return sum(item.status == "completed" for item in self.items)

    @property
    def failed(self) -> int:
        return sum(item.status == "failed" for item in self.items)
