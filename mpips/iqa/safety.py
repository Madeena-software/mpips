"""Pure reference-based structural-preservation measurements."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class StructuralSafetyMetrics:
    """Measurements describing how much reference structure survives."""

    edge_recall: float
    gradient_energy_retention: float
    informative_tile_count: int
    lost_informative_tile_fraction: float
    low_percentile_tile_retention: float
    informative_extreme_fraction: float

    def as_tuple(self) -> tuple[float, ...]:
        """Return the numeric measurements, excluding the tile count."""
        return (
            self.edge_recall,
            self.gradient_energy_retention,
            self.lost_informative_tile_fraction,
            self.low_percentile_tile_retention,
            self.informative_extreme_fraction,
        )


def _validate_inputs(
    reference: np.ndarray, candidate: np.ndarray, valid_mask: np.ndarray | None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reference_array = np.asarray(reference)
    candidate_array = np.asarray(candidate)
    if reference_array.ndim != 2 or candidate_array.ndim != 2:
        raise ValueError("reference and candidate must be grayscale 2D arrays")
    if reference_array.shape != candidate_array.shape:
        raise ValueError("reference and candidate must have the same shape")
    if not np.issubdtype(reference_array.dtype, np.number) or not np.issubdtype(
        candidate_array.dtype, np.number
    ):
        raise ValueError("reference and candidate must be numeric arrays")
    if not np.all(np.isfinite(reference_array)) or not np.all(
        np.isfinite(candidate_array)
    ):
        raise ValueError("reference and candidate must contain only finite values")

    if valid_mask is None:
        mask = np.ones(reference_array.shape, dtype=bool)
    else:
        mask = np.asarray(valid_mask)
        if mask.shape != reference_array.shape:
            raise ValueError("valid_mask shape must match reference and candidate")
        mask = mask.astype(bool, copy=False)
    return reference_array.astype(np.float64), candidate_array.astype(np.float64), mask


def _normalize(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = image[mask]
    if values.size == 0:
        return np.zeros(image.shape, dtype=np.float64)
    low, high = np.percentile(values, (1.0, 99.0))
    if high <= low:
        low = float(np.min(values))
        high = float(np.max(values))
    if high <= low:
        return np.zeros(image.shape, dtype=np.float64)
    return np.asarray(np.clip((image - low) / (high - low), 0.0, 1.0))


def _gradient(image: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    working = image.copy()
    working[~mask] = 0.0
    gx = cv2.Sobel(working, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(working, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.hypot(gx, gy)
    safe_mask = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    magnitude[~safe_mask] = 0.0
    return magnitude, safe_mask


def _informative_edges(gradient: np.ndarray, mask: np.ndarray) -> np.ndarray:
    positive = gradient[mask & (gradient > 0)]
    if positive.size == 0:
        return np.zeros(gradient.shape, dtype=bool)
    threshold = max(float(np.percentile(positive, 60.0)), float(np.max(positive)) * 0.1)
    return np.asarray((gradient >= threshold) & mask)


def _tile_retentions(
    reference_gradient: np.ndarray,
    candidate_gradient: np.ndarray,
    reference_edges: np.ndarray,
    mask: np.ndarray,
    tile_size: int = 16,
) -> list[float]:
    height, width = reference_gradient.shape
    reference_energies: list[float] = []
    tiles: list[tuple[float, float, float]] = []
    for row in range(0, height, tile_size):
        for column in range(0, width, tile_size):
            tile_mask = mask[row : row + tile_size, column : column + tile_size]
            if tile_mask.mean() < 0.5:
                continue
            reference_tile = reference_gradient[
                row : row + tile_size, column : column + tile_size
            ][tile_mask]
            candidate_tile = candidate_gradient[
                row : row + tile_size, column : column + tile_size
            ][tile_mask]
            reference_energy = float(np.mean(reference_tile))
            candidate_energy = float(np.mean(candidate_tile))
            reference_energies.append(reference_energy)
            reference_edge_tile = reference_edges[
                row : row + tile_size, column : column + tile_size
            ][tile_mask]
            if np.any(reference_edge_tile):
                ref_vector = reference_tile[reference_edge_tile]
                cand_vector = candidate_tile[reference_edge_tile]
                cosine = float(
                    np.dot(ref_vector, cand_vector)
                    / (np.linalg.norm(ref_vector) * np.linalg.norm(cand_vector) + 1e-12)
                )
            else:
                cosine = 1.0
            energy_ratio = candidate_energy / (reference_energy + 1e-12)
            tiles.append((reference_energy, min(1.0, max(0.0, energy_ratio)), cosine))

    if not reference_energies:
        return []
    informative_floor = max(float(np.max(reference_energies)) * 0.1, 1e-12)
    return [
        min(1.0, max(0.0, min(energy_ratio, cosine)))
        for reference_energy, energy_ratio, cosine in tiles
        if reference_energy >= informative_floor
    ]


def analyze_structural_preservation(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
) -> StructuralSafetyMetrics:
    """Measure reference structure retained by a same-geometry candidate.

    Images are robust-normalized independently, making measurements tolerant
    of monotonic brightness, contrast, and inversion changes. This function
    reports measurements only; it does not apply safety decisions.
    """
    reference_array, candidate_array, mask = _validate_inputs(
        reference, candidate, valid_mask
    )
    if not np.any(mask):
        return StructuralSafetyMetrics(0.0, 0.0, 0, 1.0, 0.0, 1.0)

    reference_normalized = _normalize(reference_array, mask)
    candidate_normalized = _normalize(candidate_array, mask)
    reference_gradient, safe_mask = _gradient(reference_normalized, mask)
    candidate_gradient, _ = _gradient(candidate_normalized, mask)
    reference_edges = _informative_edges(reference_gradient, safe_mask)
    candidate_edges = _informative_edges(candidate_gradient, safe_mask)

    if not np.any(reference_edges):
        return StructuralSafetyMetrics(0.0, 0.0, 0, 1.0, 0.0, 1.0)

    reference_edges_u8 = reference_edges.astype(np.uint8)
    candidate_edges_dilated = cv2.dilate(
        candidate_edges.astype(np.uint8), np.ones((3, 3), np.uint8)
    )
    edge_recall = float(np.mean(candidate_edges_dilated[reference_edges] > 0))
    reference_energy = float(np.sum(reference_gradient[reference_edges]))
    candidate_energy = float(np.sum(candidate_gradient[reference_edges]))
    gradient_energy_retention = min(
        1.0, max(0.0, candidate_energy / (reference_energy + 1e-12))
    )

    retentions = _tile_retentions(
        reference_gradient, candidate_gradient, reference_edges, safe_mask
    )
    if retentions:
        low_percentile = float(np.percentile(retentions, 10.0))
        lost_fraction = float(np.mean(np.asarray(retentions) < 0.5))
    else:
        low_percentile = 0.0
        lost_fraction = 1.0

    informative_region = cv2.dilate(
        reference_edges_u8, np.ones((5, 5), np.uint8)
    ).astype(bool)
    informative_region &= safe_mask
    reference_values = reference_normalized[informative_region]
    candidate_values = candidate_normalized[informative_region]
    non_extreme_reference = (reference_values > 0.05) & (reference_values < 0.95)
    if np.any(non_extreme_reference):
        candidate_informative = candidate_values[non_extreme_reference]
        candidate_extreme = (candidate_informative <= 0.01) | (
            candidate_informative >= 0.99
        )
        informative_extreme_fraction = float(np.mean(candidate_extreme))
    else:
        informative_extreme_fraction = 1.0

    return StructuralSafetyMetrics(
        edge_recall=edge_recall,
        gradient_energy_retention=gradient_energy_retention,
        informative_tile_count=len(retentions),
        lost_informative_tile_fraction=lost_fraction,
        low_percentile_tile_retention=low_percentile,
        informative_extreme_fraction=informative_extreme_fraction,
    )


__all__ = ["StructuralSafetyMetrics", "analyze_structural_preservation"]
