# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import numpy as np

CENTER_MARKER_MODES = ("auto", "none")


def _as_numpy_diameters(diams):
    if hasattr(diams, "detach"):
        diams = diams.detach().cpu().numpy()
    arr = np.asarray(diams, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(
            f"Expected diameter grid with shape (rows, cols), got {arr.shape}"
        )
    return arr


def center_candidate_indices(shape):
    rows, cols = shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"Invalid grid shape: {shape}")

    row_indices = [rows // 2] if rows % 2 else [rows // 2 - 1, rows // 2]
    col_indices = [cols // 2] if cols % 2 else [cols // 2 - 1, cols // 2]
    return [(r, c) for r in row_indices for c in col_indices]


def detect_center_marker(diams, mode="auto", min_ratio=1.5):
    """
    Return a metal-ball mask and metadata for the oversized center nut marker.

    The marker is only excluded from diameter statistics/losses. Its coordinate
    remains part of the grid geometry.
    """
    if mode not in CENTER_MARKER_MODES:
        raise ValueError(f"Unsupported center marker mode: {mode}")
    if min_ratio <= 0:
        raise ValueError("center marker min_ratio must be positive")

    arr = _as_numpy_diameters(diams)
    finite_values = arr[np.isfinite(arr)]
    if finite_values.size == 0:
        raise ValueError("Diameter grid contains no finite values")

    candidates = center_candidate_indices(arr.shape)
    median_diameter = float(np.median(finite_values))
    mask = np.ones(arr.shape, dtype=bool)

    metadata = {
        "mode": mode,
        "min_ratio": float(min_ratio),
        "detected_marker_count": 0,
        "marker_index_0based": None,
        "marker_index_1based": None,
        "raw_marker_diameter": None,
        "median_all_diameter": median_diameter,
        "median_metal_ball_diameter": median_diameter,
        "metal_ball_count": int(mask.size),
        "center_candidate_indices_0based": [[int(r), int(c)] for r, c in candidates],
        "candidate_max_to_median_ratio": None,
    }

    if mode == "none":
        return mask, metadata

    valid_candidates = [
        (float(arr[r, c]), r, c) for r, c in candidates if np.isfinite(arr[r, c])
    ]
    if not valid_candidates:
        return mask, metadata

    marker_diameter, marker_row, marker_col = max(valid_candidates)
    ratio = marker_diameter / median_diameter if median_diameter != 0 else np.inf
    metadata["candidate_max_to_median_ratio"] = float(ratio)

    if ratio >= min_ratio:
        mask[marker_row, marker_col] = False
        metal_values = arr[mask & np.isfinite(arr)]
        metadata.update(
            {
                "detected_marker_count": 1,
                "marker_index_0based": [int(marker_row), int(marker_col)],
                "marker_index_1based": [int(marker_row + 1), int(marker_col + 1)],
                "raw_marker_diameter": float(marker_diameter),
                "median_metal_ball_diameter": float(np.median(metal_values)),
                "metal_ball_count": int(mask.sum()),
            }
        )

    return mask, metadata
