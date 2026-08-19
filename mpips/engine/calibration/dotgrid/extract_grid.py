"""Compatibility export for the canonical dot-grid extractor."""

from mpips.calibration.dotgrid.extract_grid import _main, extract_grid

__all__ = ["extract_grid"]


if __name__ == "__main__":
    _main()
