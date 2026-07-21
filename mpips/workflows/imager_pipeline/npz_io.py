"""Strict readers and lossless TIFF conversion for Madeena NPZ files.

Madeena NPZ files store dictionaries in NumPy object arrays. Loading them
therefore requires ``allow_pickle=True`` and callers must only use trusted
files.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from mpips.workflows.imager_pipeline.models import GainCatalog, GainRecord


class NPZValidationError(ValueError):
    """Raised when a radiography NPZ violates the expected schema."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scalar(data: Any, key: str, *, required: bool = True) -> Any:
    if key not in data.files:
        if required:
            raise NPZValidationError(f"Missing required NPZ key: {key}")
        return None
    value = data[key]
    if value.ndim != 0:
        raise NPZValidationError(f"NPZ key {key!r} must be a scalar")
    return value.item()


def _mapping(data: Any, key: str) -> dict[str, Any]:
    value = _scalar(data, key)
    if not isinstance(value, dict):
        raise NPZValidationError(f"NPZ key {key!r} must contain a dictionary")
    return value


def _image(data: Any, key: str) -> np.ndarray:
    if key not in data.files:
        raise NPZValidationError(f"Missing required NPZ image: {key}")
    image = np.asarray(data[key])
    if image.ndim != 2 or image.size == 0:
        raise NPZValidationError(
            f"NPZ image {key!r} must be a non-empty 2D array, got {image.shape}"
        )
    if not np.issubdtype(image.dtype, np.number):
        raise NPZValidationError(f"NPZ image {key!r} must be numeric")
    if not np.all(np.isfinite(image)):
        raise NPZValidationError(f"NPZ image {key!r} contains NaN or infinity")
    return image


def detector_mode(xray_params: dict[str, Any]) -> str:
    mode = str(xray_params.get("detectorMode", "")).upper()
    if mode not in {"BED", "TRX"}:
        raise NPZValidationError(f"Unsupported detector mode: {mode!r}")
    return mode


def load_gain_catalog(paths: Iterable[str | Path]) -> GainCatalog:
    records: dict[str, GainRecord] = {}
    for raw_path in paths:
        path = Path(raw_path)
        try:
            with np.load(path, allow_pickle=True) as data:
                gain_id = str(_scalar(data, "id"))
                if not gain_id:
                    raise NPZValidationError("Gain id cannot be empty")
                if gain_id in records:
                    raise NPZValidationError(
                        f"Duplicate gain id {gain_id!r}: "
                        f"{records[gain_id].path} and {path}"
                    )
                dark = _image(data, "darkimage")
                flat = _image(data, "rawimage")
                if dark.shape != flat.shape:
                    raise NPZValidationError(
                        f"Gain dark/flat shapes differ: {dark.shape} != {flat.shape}"
                    )
                xray_params = _mapping(data, "xrayparams")
                camera_params = _mapping(data, "cameraparams")
                records[gain_id] = GainRecord(
                    id=gain_id,
                    path=path,
                    dark=dark.copy(),
                    flat=flat.copy(),
                    camera_params=camera_params,
                    detector_mode=detector_mode(xray_params),
                )
        except (OSError, ValueError) as exc:
            if isinstance(exc, NPZValidationError):
                raise
            raise NPZValidationError(f"Could not load gain NPZ {path}: {exc}") from exc
    if not records:
        raise NPZValidationError("Gain catalog contains no NPZ files")
    return GainCatalog(records)


def load_radiograph(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        with np.load(source, allow_pickle=True) as data:
            gain_id = _scalar(data, "gainid")
            if gain_id is None or not str(gain_id):
                raise NPZValidationError("Radiograph gainid cannot be empty")
            xray_params = _mapping(data, "xrayparams")
            return {
                "path": source,
                "id": str(_scalar(data, "id")),
                "gain_id": str(gain_id),
                "raw": _image(data, "rawimage").copy(),
                "camera_params": _mapping(data, "cameraparams"),
                "detector_mode": detector_mode(xray_params),
            }
    except (OSError, ValueError) as exc:
        if isinstance(exc, NPZValidationError):
            raise
        raise NPZValidationError(
            f"Could not load radiograph NPZ {source}: {exc}"
        ) from exc


def load_calibration_processed_image(
    path: str | Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    source = Path(path)
    try:
        with np.load(source, allow_pickle=True) as data:
            image = _image(data, "processedimage").astype(np.float64)
            if image.min() < 0.0 or image.max() > 1.0:
                raise NPZValidationError(
                    "Calibration processedimage must be normalized to [0, 1]"
                )
            metadata = {
                "id": str(_scalar(data, "id")),
                "gain_id": str(_scalar(data, "gainid")),
                "camera_params": _mapping(data, "cameraparams"),
                "detector_mode": detector_mode(_mapping(data, "xrayparams")),
            }
            return image.astype(np.float32), metadata
    except (OSError, ValueError) as exc:
        if isinstance(exc, NPZValidationError):
            raise
        raise NPZValidationError(
            f"Could not load calibration NPZ {source}: {exc}"
        ) from exc


def to_uint16(image: np.ndarray, name: str = "image") -> np.ndarray:
    values = np.asarray(image)
    if values.ndim != 2 or not np.issubdtype(values.dtype, np.number):
        raise NPZValidationError(f"{name} must be a numeric 2D array")
    if not np.all(np.isfinite(values)):
        raise NPZValidationError(f"{name} contains NaN or infinity")
    minimum = float(values.min())
    maximum = float(values.max())
    if minimum < 0 or maximum > np.iinfo(np.uint16).max:
        raise NPZValidationError(
            f"{name} range [{minimum}, {maximum}] cannot be represented as uint16"
        )
    return values.astype(np.uint16)


def write_tiff(path: str | Path, image: np.ndarray) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(target), image):
        raise OSError(f"Could not write TIFF: {target}")
    return target
