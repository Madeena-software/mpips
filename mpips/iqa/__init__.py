"""Public image-quality-assessment helpers."""

from importlib import import_module
from typing import Any

__all__ = [
    "calculate_entropy",
    "calculate_eme",
    "calculate_local_contrast",
    "calculate_cii",
    "calculate_brisque",
    "calculate_all_metrics",
    "StructuralSafetyMetrics",
    "analyze_structural_preservation",
]


def __getattr__(name: str) -> Any:
    if name in {
        "StructuralSafetyMetrics",
        "analyze_structural_preservation",
    }:
        return getattr(import_module("mpips.iqa.safety"), name)
    if name in __all__:
        return getattr(import_module("mpips.iqa.metrics"), name)
    raise AttributeError(f"module 'mpips.iqa' has no attribute {name!r}")
