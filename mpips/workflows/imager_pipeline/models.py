"""Configuration and result models for the imager pipeline workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from mpips.engine.imager_pipeline.config import (  # noqa: F401
    ImagerPipelineConfig as ImagerPipelineConfig,
)


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
