#!/usr/bin/env python3
"""Validate the read-only calibration layout used by deployment preflight."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np


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
                    if expected_shape is not None and map_x.shape != expected_shape:
                        errors.append(
                            f"{expected_mode}: metadata.image_shape does not match "
                            "remap maps"
                        )
                    if not np.all(np.isfinite(map_x)) or not np.all(np.isfinite(map_y)):
                        errors.append(
                            f"{expected_mode}: remap maps contain non-finite values"
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
