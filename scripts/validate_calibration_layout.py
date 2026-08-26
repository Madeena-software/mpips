#!/usr/bin/env python3
"""Validate the read-only calibration layout used by deployment preflight."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np

MIN_REMAP_VALID_FRACTION = 0.85
MIN_REMAP_WIDTH_RATIO = 0.75
MIN_REMAP_HEIGHT_RATIO = 0.75
MIN_EXPANDED_VALID_FRACTION = 0.80
MIN_EXPANDED_OUTPUT_WIDTH_RATIO = 0.80
MIN_EXPANDED_OUTPUT_HEIGHT_RATIO = 0.80
MIN_EXPANDED_SOURCE_WIDTH_COVERAGE = 0.80
MIN_EXPANDED_SOURCE_HEIGHT_COVERAGE = 0.80


def _validate_artifact(directory: Path, expected_mode: str) -> list[str]:
    errors: list[str] = []
    if directory.is_symlink() or not directory.is_dir():
        return [f"{expected_mode}: artifact directory is not a regular directory"]

    metadata_path = directory / "metadata.json"
    remap_path = directory / "remap.npz"
    metadata_is_regular = (
        not metadata_path.is_symlink()
        and metadata_path.is_file()
        and metadata_path.stat().st_size > 0
    )
    if not metadata_is_regular:
        errors.append(
            f"{expected_mode}: metadata.json is missing or not a regular file"
        )
    remap_is_regular = (
        not remap_path.is_symlink()
        and remap_path.is_file()
        and remap_path.stat().st_size > 0
    )
    if not remap_is_regular:
        errors.append(f"{expected_mode}: remap.npz is missing or not a regular file")

    metadata: dict[str, object] = {}
    if metadata_is_regular:
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("metadata is not an object")
            metadata = loaded
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{expected_mode}: invalid metadata.json ({exc})")

    if metadata.get("validated") is not True:
        errors.append(f"{expected_mode}: metadata.validated is not true")
    if not isinstance(metadata.get("fingerprint"), str) or not metadata["fingerprint"]:
        errors.append(f"{expected_mode}: metadata.fingerprint is empty")
    source_metadata = metadata.get("source_metadata")
    if (
        not isinstance(source_metadata, dict)
        or source_metadata.get("detector_mode") != expected_mode
    ):
        errors.append(f"{expected_mode}: source_metadata.detector_mode mismatch")

    image_shape = metadata.get("image_shape")
    if (
        not isinstance(image_shape, (list, tuple))
        or len(image_shape) != 2
        or any(
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            for dimension in image_shape
        )
    ):
        errors.append(f"{expected_mode}: metadata.image_shape is invalid")
        expected_shape = None
    else:
        expected_shape = tuple(image_shape)

    config = metadata.get("config")
    canvas_mode = (
        config.get("canvas_mode", "fixed") if isinstance(config, dict) else "fixed"
    )
    if canvas_mode not in {"fixed", "expanded"}:
        errors.append(f"{expected_mode}: config.canvas_mode is invalid")
        canvas_mode = "fixed"

    if remap_is_regular:
        try:
            with np.load(remap_path, allow_pickle=False) as remap:
                if "map_x" not in remap or "map_y" not in remap:
                    errors.append(
                        f"{expected_mode}: remap.npz must contain map_x and map_y"
                    )
                else:
                    map_x, map_y = remap["map_x"], remap["map_y"]
                    if map_x.shape != map_y.shape:
                        errors.append(f"{expected_mode}: remap map shapes differ")
                    if (
                        canvas_mode == "fixed"
                        and expected_shape is not None
                        and map_x.shape != expected_shape
                    ):
                        errors.append(
                            f"{expected_mode}: metadata.image_shape does not match "
                            "remap maps"
                        )
                    if map_x.ndim != 2 or not map_x.size:
                        errors.append(
                            f"{expected_mode}: remap maps must be non-empty 2-D arrays"
                        )
                    elif not np.all(np.isfinite(map_x)) or not np.all(
                        np.isfinite(map_y)
                    ):
                        errors.append(
                            f"{expected_mode}: remap maps contain non-finite values"
                        )
                    elif expected_shape is not None:
                        valid = (
                            (map_x >= 0)
                            & (map_x <= expected_shape[1] - 1)
                            & (map_y >= 0)
                            & (map_y <= expected_shape[0] - 1)
                        )
                        ys, xs = np.where(valid)
                        valid_fraction = float(np.mean(valid))
                        bbox = (
                            [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
                            if xs.size
                            else None
                        )
                        width_ratio = (
                            (bbox[2] - bbox[0] + 1) / map_x.shape[1] if bbox else 0.0
                        )
                        height_ratio = (
                            (bbox[3] - bbox[1] + 1) / map_x.shape[0] if bbox else 0.0
                        )
                        source_width_coverage = (
                            (float(map_x[valid].max()) - float(map_x[valid].min()) + 1)
                            / expected_shape[1]
                            if xs.size
                            else 0.0
                        )
                        source_height_coverage = (
                            (float(map_y[valid].max()) - float(map_y[valid].min()) + 1)
                            / expected_shape[0]
                            if xs.size
                            else 0.0
                        )
                        if canvas_mode == "fixed" and (
                            valid_fraction < MIN_REMAP_VALID_FRACTION
                            or width_ratio < MIN_REMAP_WIDTH_RATIO
                            or height_ratio < MIN_REMAP_HEIGHT_RATIO
                        ):
                            errors.append(
                                f"{expected_mode}: fixed-canvas remap coverage "
                                "is unsafe (REMAP_VALID_FRACTION="
                                f"{valid_fraction:.6f}, "
                                "REMAP_OUT_OF_BOUNDS_FRACTION="
                                f"{1 - valid_fraction:.6f}, "
                                f"VALID_REMAP_BBOX={bbox}, "
                                f"VALID_REMAP_WIDTH_RATIO={width_ratio:.6f}, "
                                f"VALID_REMAP_HEIGHT_RATIO={height_ratio:.6f})"
                            )
                        elif canvas_mode == "expanded" and (
                            not np.any(valid)
                            or bbox is None
                            or valid_fraction < MIN_EXPANDED_VALID_FRACTION
                            or width_ratio < MIN_EXPANDED_OUTPUT_WIDTH_RATIO
                            or height_ratio < MIN_EXPANDED_OUTPUT_HEIGHT_RATIO
                            or source_width_coverage
                            < MIN_EXPANDED_SOURCE_WIDTH_COVERAGE
                            or source_height_coverage
                            < MIN_EXPANDED_SOURCE_HEIGHT_COVERAGE
                        ):
                            errors.append(
                                f"{expected_mode}: expanded remap is empty "
                                "or degenerate"
                            )
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            errors.append(f"{expected_mode}: invalid remap.npz ({exc})")
    return errors


def validate_calibration_layout(root: str | Path) -> list[str]:
    """Return deterministic validation errors for a legacy or multi-mode layout."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return ["calibration root is not a regular directory"]

    root_metadata = root / "metadata.json"
    root_remap = root / "remap.npz"
    if root_metadata.exists() or root_remap.exists():
        errors = _validate_artifact(root, "BED")
        if any(child.is_dir() for child in root.iterdir()):
            errors.append("legacy layout must not contain mode directories")
        return errors

    mode_directories = [
        child for child in root.iterdir() if child.is_dir() or child.is_symlink()
    ]
    if not any(child.name == "BED" for child in mode_directories):
        return ["multi-mode layout is missing BED"]
    errors: list[str] = []
    for directory in sorted(mode_directories, key=lambda path: path.name):
        errors.extend(_validate_artifact(directory, directory.name))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    errors = validate_calibration_layout(args.root)
    if errors:
        for error in errors:
            print(f"CALIBRATION_LAYOUT_INVALID: {error}")
        return 1
    print("CALIBRATION_LAYOUT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
