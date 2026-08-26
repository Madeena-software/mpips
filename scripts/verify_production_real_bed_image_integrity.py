#!/usr/bin/env python3
"""Verify the real BED image path on the production self-hosted runner."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pydicom

EXPECTED_RUNTIME_SHA = "dd7c21eead66a2c5396522a2310f5dd9cbd85b85"
EXPECTED_API_IMAGE = f"mpips-api:{EXPECTED_RUNTIME_SHA}"
EXPECTED_WORKER_IMAGE = f"mpips-npz-worker:{EXPECTED_RUNTIME_SHA}"
API_URL = "http://127.0.0.1:8014"
CALIBRATION_ROOT = Path("/var/www/mpips-runtime/calibration")
EXPECTED_FILES = {
    "BED_1785646321389.npz": (
        "1EwG5WPLcR30vSTHaOAybTVg6S9P4GSMB",
        89908075,
        "eb489cc28c61816d2527718df2ed41c9c5fcf53f76d928e927d26d2865ab4319",
    ),
    "BED_1785642964117.npz": (
        "1R6o53hMVBy3B__cAqJBUhwcoTn14VGWF",
        17713052,
        "44673a19ebeba1b66546e1a85dede4de9b2a730a97128c6460fb3b5239070821",
    ),
}


class RuntimeProvenanceError(RuntimeError):
    pass


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeProvenance:
    runtime_sha: str
    worker_image: str
    api_image: str
    api_port: str


@dataclass(frozen=True)
class CalibrationSnapshot:
    directory: Path
    fingerprint: str
    validated: bool
    detector_mode: str
    image_shape: tuple[int, int]
    canvas_mode: str
    remap_shape: tuple[int, int]
    metadata_sha256: str
    remap_sha256: str

    @classmethod
    def from_directory(cls, directory: Path) -> "CalibrationSnapshot":
        metadata_path = directory / "metadata.json"
        remap_path = directory / "remap.npz"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        source = metadata.get("source_metadata", {})
        config = metadata.get("config", {})
        with np.load(remap_path, allow_pickle=False) as remap:
            if set(remap.files) < {"map_x", "map_y"}:
                raise VerificationError("calibration remap is incomplete")
            if remap["map_x"].shape != remap["map_y"].shape:
                raise VerificationError("calibration remap shapes differ")
            remap_shape = tuple(int(value) for value in remap["map_x"].shape)
        image_shape = tuple(int(value) for value in metadata["image_shape"])
        return cls(
            directory=directory,
            fingerprint=str(metadata["fingerprint"]),
            validated=metadata.get("validated") is True,
            detector_mode=str(source.get("detector_mode", "")),
            image_shape=image_shape,
            canvas_mode=str(config.get("canvas_mode", "fixed")),
            remap_shape=remap_shape,
            metadata_sha256=sha256(metadata_path),
            remap_sha256=sha256(remap_path),
        )


@dataclass(frozen=True)
class ImageMetrics:
    shape: tuple[int, int]
    dtype: str
    minimum: int
    maximum: int
    mean: float
    p01: float
    p05: float
    p50: float
    p95: float
    p99: float
    zero_ratio: float
    nonzero_ratio: float
    nonzero_bbox: tuple[int, int, int, int] | None
    support_width_ratio: float
    support_height_ratio: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_runtime_provenance(
    runtime_root: Path, api_image: str, api_port: str
) -> RuntimeProvenance:
    version_path = runtime_root / ".mpips-version"
    worker_path = runtime_root / ".mpips-worker-image"
    try:
        version = version_path.read_text().strip()
        worker = worker_path.read_text().strip()
    except OSError as exc:
        raise RuntimeProvenanceError("runtime markers are missing") from exc
    if version != EXPECTED_RUNTIME_SHA:
        raise RuntimeProvenanceError("runtime SHA marker mismatch")
    if worker != EXPECTED_WORKER_IMAGE:
        raise RuntimeProvenanceError("worker image marker mismatch")
    if api_image != EXPECTED_API_IMAGE:
        raise RuntimeProvenanceError("API image mismatch")
    if api_port not in {"127.0.0.1:8014", "127.0.0.1:8014->8000/tcp"}:
        raise RuntimeProvenanceError("API port binding mismatch")
    return RuntimeProvenance(
        EXPECTED_RUNTIME_SHA, EXPECTED_WORKER_IMAGE, api_image, api_port
    )


def calculate_metrics(image: np.ndarray) -> ImageMetrics:
    if image.ndim != 2 or image.dtype != np.uint16 or image.size == 0:
        raise VerificationError("DICOM pixel array must be non-empty 2-D uint16")
    nonzero = image != 0
    if nonzero.any():
        ys, xs = np.where(nonzero)
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        width_ratio = (bbox[2] - bbox[0] + 1) / image.shape[1]
        height_ratio = (bbox[3] - bbox[1] + 1) / image.shape[0]
    else:
        bbox = None
        width_ratio = height_ratio = 0.0
    percentiles = np.percentile(image, [1, 5, 50, 95, 99])
    return ImageMetrics(
        shape=tuple(int(value) for value in image.shape),
        dtype=str(image.dtype),
        minimum=int(image.min()),
        maximum=int(image.max()),
        mean=float(image.mean()),
        p01=float(percentiles[0]),
        p05=float(percentiles[1]),
        p50=float(percentiles[2]),
        p95=float(percentiles[3]),
        p99=float(percentiles[4]),
        zero_ratio=float(np.mean(~nonzero)),
        nonzero_ratio=float(np.mean(nonzero)),
        nonzero_bbox=bbox,
        support_width_ratio=width_ratio,
        support_height_ratio=height_ratio,
    )


def evaluate_image_integrity(metrics: ImageMetrics) -> bool:
    return (
        metrics.maximum > metrics.minimum
        and metrics.zero_ratio < 0.5
        and metrics.support_width_ratio > 0.80
        and metrics.support_height_ratio > 0.80
    )


def validate_bed_inputs(radiograph: dict[str, Any], gain: Any) -> None:
    if radiograph["detector_mode"] != "BED" or gain.detector_mode != "BED":
        raise VerificationError("BED detector compatibility check failed")
    if radiograph["gain_id"] != gain.id:
        raise VerificationError("radiograph gain id does not match gain id")
    if tuple(radiograph["raw"].shape) != (3000, 4096) or tuple(gain.flat.shape) != (
        3000,
        4096,
    ):
        raise VerificationError("BED source shape compatibility check failed")


def validate_download(path: Path, expected_size: int, expected_sha: str) -> None:
    if path.stat().st_size != expected_size or sha256(path) != expected_sha:
        raise VerificationError(f"integrity check failed for {path.name}")
    try:
        with zipfile.ZipFile(path) as archive:
            if not archive.namelist() or archive.testzip() is not None:
                raise VerificationError(f"invalid NPZ structure for {path.name}")
    except (OSError, zipfile.BadZipFile) as exc:
        raise VerificationError(f"invalid NPZ structure for {path.name}") from exc


def download_drive_file(file_id: str, destination: Path) -> None:
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download"
    request = urllib.request.Request(url, headers={"User-Agent": "mpips-verifier"})
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        destination.open("wb") as output,
    ):
        shutil.copyfileobj(response, output, length=1024 * 1024)
    if destination.read_bytes()[:100].lstrip().startswith(b"<"):
        text = destination.read_text(errors="ignore")
        token = re.search(r"confirm=([0-9A-Za-z_-]+)", text)
        if not token:
            raise VerificationError(
                f"Google Drive download did not return NPZ: {destination.name}"
            )
        destination.unlink()
        confirm_url = f"{url}&confirm={token.group(1)}"
        request = urllib.request.Request(
            confirm_url, headers={"User-Agent": "mpips-verifier"}
        )
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            destination.open("wb") as output,
        ):
            shutil.copyfileobj(response, output, length=1024 * 1024)


def select_calibration(root: Path, detector_mode: str) -> Path:
    if (root / "metadata.json").is_file():
        return root
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and (directory / "metadata.json").is_file():
            metadata = json.loads((directory / "metadata.json").read_text())
            if (
                metadata.get("source_metadata", {}).get("detector_mode")
                == detector_mode
            ):
                return directory
    raise VerificationError("BED calibration was not found")


def make_manifest(
    radiograph: dict[str, Any], radiograph_path: Path, gain_path: Path
) -> bytes:
    return json.dumps(
        {
            "manifest_version": "1.0",
            "patient": {
                "medical_record_number": "BED-VERIFICATION",
                "name": "BED Verification",
            },
            "capture": {
                "detector_type": "BED",
                "radiograph": {
                    "filename": radiograph_path.name,
                    "byte_size": radiograph_path.stat().st_size,
                    "sha256": sha256(radiograph_path),
                },
                "gain": {
                    "filename": gain_path.name,
                    "byte_size": gain_path.stat().st_size,
                    "sha256": sha256(gain_path),
                    "gain_id": radiograph["gain_id"],
                },
            },
        }
    ).encode()


def main() -> int:
    temporary = Path(tempfile.mkdtemp(prefix="mpips-real-bed-"))
    try:
        runtime_root = Path("/var/www/mpips-runtime")
        if (
            not (runtime_root / ".mpips-version").is_file()
            or not (runtime_root / ".mpips-worker-image").is_file()
        ):
            raise RuntimeProvenanceError("runtime markers are missing")
        compose = [
            "docker",
            "compose",
            "--project-name",
            "mpips-internal-beta",
            "--env-file",
            "/dev/null",
            "-f",
            "/var/www/mpips-runtime/docker-compose.prod.yml",
        ]
        api_container = subprocess.check_output(
            [*compose, "ps", "-q", "mpips-api"], text=True
        ).strip()
        if not api_container or "\n" in api_container:
            raise RuntimeProvenanceError(
                "expected exactly one running production API container"
            )
        image = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.Config.Image}}", api_container],
            text=True,
        ).strip()
        port = subprocess.check_output(
            ["docker", "port", api_container, "8000/tcp"], text=True
        ).strip()
        provenance = read_runtime_provenance(runtime_root, image, port)
        with httpx.Client(timeout=20) as client:
            if client.get(f"{API_URL}/health").status_code != 200:
                raise VerificationError("production health check failed")
        paths = {}
        for filename, (file_id, size, digest) in EXPECTED_FILES.items():
            path = temporary / filename
            download_drive_file(file_id, path)
            validate_download(path, size, digest)
            paths[filename] = path
        from mpips.workflows.imager_pipeline.npz_io import (
            load_gain_catalog,
            load_radiograph,
        )

        radiograph = load_radiograph(paths["BED_1785646321389.npz"])
        gain = load_gain_catalog([paths["BED_1785642964117.npz"]]).records.get(
            radiograph["gain_id"]
        )
        if gain is None:
            raise VerificationError("radiograph gain id is absent from gain NPZ")
        validate_bed_inputs(radiograph, gain)
        calibration = CalibrationSnapshot.from_directory(
            select_calibration(CALIBRATION_ROOT, "BED")
        )
        if not calibration.validated or calibration.detector_mode != "BED":
            raise VerificationError("BED calibration is not validated")
        manifest = temporary / "manifest.json"
        manifest.write_bytes(
            make_manifest(
                radiograph,
                paths["BED_1785646321389.npz"],
                paths["BED_1785642964117.npz"],
            )
        )
        key = os.environ["MPIPS_API_KEY"]
        with (
            httpx.Client(timeout=360) as client,
            paths["BED_1785646321389.npz"].open("rb") as rad,
            paths["BED_1785642964117.npz"].open("rb") as gain,
            manifest.open("rb") as form,
        ):
            response = client.post(
                f"{API_URL}/v1/radiographs/dicom",
                headers={"X-MPIPS-API-Key": key},
                files={
                    "radiograph_npz": (
                        paths["BED_1785646321389.npz"].name,
                        rad,
                        "application/octet-stream",
                    ),
                    "gain_npz": (
                        paths["BED_1785642964117.npz"].name,
                        gain,
                        "application/octet-stream",
                    ),
                    "manifest": ("manifest.json", form, "application/json"),
                },
            )
        if (
            response.status_code != 200
            or response.headers.get("content-type", "").split(";")[0]
            != "application/dicom"
        ):
            raise VerificationError(f"BED API failed with HTTP {response.status_code}")
        dicom_path = temporary / "result.dcm"
        dicom_path.write_bytes(response.content)
        dataset = pydicom.dcmread(dicom_path)
        if (
            dataset.file_meta.TransferSyntaxUID != pydicom.uid.ExplicitVRLittleEndian
            or dataset.BitsAllocated != 16
            or dataset.PixelRepresentation != 0
            or any(tag.is_private for tag in dataset)
        ):
            raise VerificationError("DICOM structure failed")
        for name in ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"):
            if not pydicom.uid.UID(str(getattr(dataset, name, ""))).is_valid:
                raise VerificationError(f"invalid DICOM {name}")
        metrics = calculate_metrics(dataset.pixel_array)
        after = CalibrationSnapshot.from_directory(calibration.directory)
        if (
            calibration.metadata_sha256 != after.metadata_sha256
            or calibration.remap_sha256 != after.remap_sha256
        ):
            raise VerificationError(
                "PRODUCTION_CALIBRATION_MUTATED_DURING_VERIFICATION"
            )
        summary = "\n".join(
            [
                "REAL_BED_PRODUCTION_IMAGE_INTEGRITY_PASS",
                f"Runtime SHA: {provenance.runtime_sha}",
                f"API image: {provenance.api_image}",
                f"Worker image: {provenance.worker_image}",
                "Health HTTP: 200",
                "Radiograph integrity: PASS",
                "Gain integrity: PASS",
                "BED compatibility: PASS",
                f"BED calibration canvas: {calibration.canvas_mode}",
                f"BED calibration source shape: {calibration.image_shape}",
                f"BED calibration remap shape: {calibration.remap_shape}",
                "BED HTTP status: 200",
                "BED content type: application/dicom",
                f"BED shape: {metrics.shape}",
                f"BED dtype: {metrics.dtype}",
                f"BED min/max: {metrics.minimum}/{metrics.maximum}",
                f"BED mean: {metrics.mean:.6f}",
                f"BED p01/p05/p50/p95/p99: {metrics.p01:.6f}/"
                f"{metrics.p05:.6f}/{metrics.p50:.6f}/{metrics.p95:.6f}/"
                f"{metrics.p99:.6f}",
                f"BED zero ratio: {metrics.zero_ratio:.10f}",
                f"BED nonzero ratio: {metrics.nonzero_ratio:.10f}",
                f"BED nonzero bbox: {metrics.nonzero_bbox}",
                f"BED support: {metrics.support_width_ratio:.6f} x "
                f"{metrics.support_height_ratio:.6f}",
                f"BED calibration: {calibration.fingerprint}",
                "BED_CALIBRATION_MUTATED=NO",
            ]
        )
        print(summary)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(summary + "\n")
        return 0 if evaluate_image_integrity(metrics) else 1
    except (
        KeyError,
        OSError,
        RuntimeError,
        VerificationError,
        RuntimeProvenanceError,
    ) as exc:
        classification = (
            "PRODUCTION_RUNTIME_PROVENANCE_FAILED"
            if isinstance(exc, RuntimeProvenanceError)
            else str(exc)
        )
        print(classification)
        return 1
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
