"""Sequential NPZ batch execution with durable manifests."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from mpips.workflows.imager_pipeline.calibration import load_remap
from mpips.workflows.imager_pipeline.models import (
    BatchItemResult,
    BatchResult,
    CalibrationArtifacts,
    GainCatalog,
    GainRecord,
    ImagerPipelineConfig,
)
from mpips.workflows.imager_pipeline.npz_io import (
    load_radiograph,
    sha256_file,
    to_uint16,
    write_tiff,
)
from mpips.workflows.imager_pipeline.pipeline import process_radiography_arrays


def _camera_serial(params: dict[str, object]) -> str:
    return str(params.get("cameraSerial", ""))


def _validate_compatibility(
    radiograph: dict[str, Any],
    gain: GainRecord,
    calibration_metadata: dict[str, Any],
    expected_shape: tuple[int, int],
) -> None:
    raw = radiograph["raw"]
    if raw.shape != expected_shape:
        raise ValueError(
            f"Radiograph shape {raw.shape} does not match calibration {expected_shape}"
        )
    if gain.dark.shape != expected_shape or gain.flat.shape != expected_shape:
        raise ValueError("Gain dark/flat shape does not match calibration geometry")
    if radiograph["detector_mode"] != gain.detector_mode:
        raise ValueError("Radiograph and gain detector modes differ")
    calibration_source = calibration_metadata.get("source_metadata", {})
    if not isinstance(calibration_source, dict):
        raise ValueError("Calibration source metadata is invalid")
    if radiograph["detector_mode"] != calibration_source.get("detector_mode"):
        raise ValueError("Radiograph and calibration detector modes differ")
    serials = {
        _camera_serial(radiograph["camera_params"]),
        _camera_serial(gain.camera_params),
        _camera_serial(calibration_source.get("camera_params", {})),
    }
    serials.discard("")
    if len(serials) > 1:
        raise ValueError(f"Camera serial mismatch: {sorted(serials)}")


def process_npz_batch(
    radiographs: Iterable[str | Path],
    gains: GainCatalog,
    calibration: CalibrationArtifacts,
    output_dir: str | Path,
    config: ImagerPipelineConfig | None = None,
    *,
    on_progress: Callable[[int, int, BatchItemResult], None] | None = None,
) -> BatchResult:
    """Process radiographs sequentially, continuing after per-file failures."""
    if not calibration.validated:
        raise ValueError("Batch processing requires validated calibration artifacts")
    config = config or ImagerPipelineConfig()
    sources = [Path(path) for path in radiographs]
    if not sources:
        raise ValueError("Radiograph batch cannot be empty")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    durable_run_directory = Path(output_dir) / "runs" / run_id
    staging = tempfile.TemporaryDirectory(prefix="mpips-run-")
    run_directory = Path(staging.name) / "runs" / run_id
    processed_directory = run_directory / "processed"
    processed_directory.mkdir(parents=True, exist_ok=False)
    manifest_path = run_directory / "manifest.json"
    map_x, map_y = load_remap(calibration)
    calibration_metadata = json.loads(calibration.metadata_path.read_text())
    results: list[BatchItemResult] = []
    used_names: set[str] = set()

    for index, source in enumerate(sources, start=1):
        started = time.monotonic()
        gain_id: str | None = None
        source_digest: str | None = None
        try:
            source_digest = sha256_file(source)
            radiograph = load_radiograph(source)
            gain_id = str(radiograph["gain_id"])
            gain = gains.require(gain_id)
            _validate_compatibility(
                radiograph, gain, calibration_metadata, calibration.image_shape
            )
            raw = to_uint16(radiograph["raw"], "radiograph raw")
            dark = to_uint16(gain.dark, "gain dark")
            flat = to_uint16(gain.flat, "gain flat")
            output = process_radiography_arrays(
                raw,
                dark,
                flat,
                str(radiograph["detector_mode"]),
                config,
                map_x=map_x,
                map_y=map_y,
            )
            base_name = f"{source.stem}_processed.tiff"
            if base_name in used_names:
                base_name = f"{source.stem}_{source_digest[:8]}_processed.tiff"
            collision_index = 2
            while base_name in used_names:
                base_name = (
                    f"{source.stem}_{source_digest[:8]}_"
                    f"{collision_index}_processed.tiff"
                )
                collision_index += 1
            used_names.add(base_name)
            write_tiff(processed_directory / base_name, output)
            destination = durable_run_directory / "processed" / base_name
            item = BatchItemResult(
                source=str(source),
                status="completed",
                gain_id=gain_id,
                output=str(destination),
                source_sha256=source_digest,
                elapsed_seconds=round(time.monotonic() - started, 3),
            )
        except Exception as exc:
            item = BatchItemResult(
                source=str(source),
                status="failed",
                gain_id=gain_id,
                source_sha256=source_digest,
                elapsed_seconds=round(time.monotonic() - started, 3),
                error=f"{type(exc).__name__}: {exc}",
            )
        results.append(item)
        if on_progress is not None:
            on_progress(index, len(sources), item)

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "calibration": {
            "fingerprint": calibration.fingerprint,
            "directory": str(calibration.directory),
            "validated": calibration.validated,
        },
        "pipeline_config": asdict(config),
        "counts": {
            "total": len(results),
            "succeeded": sum(item.status == "completed" for item in results),
            "failed": sum(item.status == "failed" for item in results),
        },
        "items": [asdict(item) for item in results],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    durable_run_directory.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_directory, durable_run_directory)
    staging.cleanup()
    return BatchResult(
        run_id=run_id,
        run_directory=durable_run_directory,
        manifest_path=durable_run_directory / "manifest.json",
        items=tuple(results),
    )
