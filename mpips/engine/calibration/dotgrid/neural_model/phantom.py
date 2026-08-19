"""Compatibility exports for canonical neural phantom helpers."""

from mpips.calibration.dotgrid.neural_model import phantom as _canonical_phantom

CENTER_MARKER_MODES = _canonical_phantom.CENTER_MARKER_MODES
_as_numpy_diameters = _canonical_phantom._as_numpy_diameters
center_candidate_indices = _canonical_phantom.center_candidate_indices
detect_center_marker = _canonical_phantom.detect_center_marker

__all__ = ["CENTER_MARKER_MODES", "center_candidate_indices", "detect_center_marker"]
