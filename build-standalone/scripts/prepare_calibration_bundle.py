"""Pre-build calibration preparation and validation gate.

Validates that all required calibration assets for mpips-runtime are verified
and present prior to executing PyInstaller.

Key Responsibilities:
1. Locate source calibration archive:
   - Check CLI argument if provided, or
   - Check MPIPS_TRX_CALIBRATION_ARCHIVE env var, or
   - Look in canonical research publication package directory.
2. Verify archive SHA-256 matches exact designated hash:
   2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556
3. Safely inspect and extract archive members into:
   mpips/resources/calibration/trx_mode/
   - metadata.json
   - remap.npz
4. Verify extracted metadata:
   - id: GOTRI-TRX-001
   - detector_mode: TRX
   - camera_params.serialNumber: DA5234480
   - image_shape: [3000, 4096]
   - fingerprint: 606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d
   - validated: True
5. Verify extracted remap.npz:
   - Contains map_x and map_y arrays of shape (3000, 4096)
   - SHA-256 digest: 32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893
6. Verify synthetic BED calibration fixture:
   - metadata.json and remap.npz present and valid in calibration/bed_mode/
7. Write an auditable calibration manifest:
   build-standalone/embedded_calibration_manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TRX_ARCHIVE_SHA256 = (
    "2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556"
)
EXPECTED_TRX_REMAP_SHA256 = (
    "32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893"
)
EXPECTED_TRX_FINGERPRINT = (
    "606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d"
)
EXPECTED_TRX_CAMERA_SERIAL = "DA5234480"
EXPECTED_TRX_IMAGE_SHAPE = (3000, 4096)
EXPECTED_TRX_PROFILE_ID = "GOTRI-TRX-001"

DEFAULT_RESEARCH_ARCHIVE = (
    REPO_ROOT
    / "research"
    / "real-thorax-dicom"
    / "publication"
    / "606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d"
    / "publication-package"
    / (
        "trx-calibration-"
        "606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz"
    )
)


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def prepare_and_validate_calibration(
    archive_path: Path | None = None,
    output_dir: Path | None = None,
    manifest_output: Path | None = None,
) -> dict[str, Any]:
    """Prepares and validates calibration assets for build.

    Raises RuntimeError on any validation failure.
    """
    cal_base = output_dir or (REPO_ROOT / "mpips" / "resources" / "calibration")
    trx_dir = cal_base / "trx_mode"
    bed_dir = cal_base / "bed_mode"
    trx_dir.mkdir(parents=True, exist_ok=True)
    bed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve source archive
    source_archive = archive_path
    if source_archive is None:
        env_val = os.getenv("MPIPS_TRX_CALIBRATION_ARCHIVE")
        if env_val:
            source_archive = Path(env_val).resolve()
        elif DEFAULT_RESEARCH_ARCHIVE.is_file():
            source_archive = DEFAULT_RESEARCH_ARCHIVE

    trx_remap_file = trx_dir / "remap.npz"
    trx_meta_file = trx_dir / "metadata.json"

    # Strictly require authorized, hash-verified TRX archive
    if not source_archive or not source_archive.is_file():
        raise RuntimeError(
            "Authorized TRX calibration archive not found. "
            "Please provide --archive or set MPIPS_TRX_CALIBRATION_ARCHIVE."
        )

    archive_sha = compute_sha256(source_archive)
    if archive_sha != EXPECTED_TRX_ARCHIVE_SHA256:
        raise RuntimeError(
            f"TRX calibration archive SHA-256 mismatch: {archive_sha} != "
            f"{EXPECTED_TRX_ARCHIVE_SHA256}"
        )

    # Inspect and extract safely
    with tarfile.open(source_archive, "r:gz") as tar:
        members = tar.getmembers()
        # Path traversal safety check
        for m in members:
            if m.name.startswith("/") or ".." in m.name or m.islnk() or m.issym():
                raise RuntimeError(f"Unsafe path in calibration tar: {m.name}")

        meta_member = tar.getmember("trx-calibration/metadata.json")
        remap_member = tar.getmember("trx-calibration/remap.npz")

        extracted_meta = tar.extractfile(meta_member)
        if extracted_meta is None:
            raise RuntimeError("Failed to extract trx-calibration/metadata.json")
        trx_meta_file.write_bytes(extracted_meta.read())

        extracted_remap = tar.extractfile(remap_member)
        if extracted_remap is None:
            raise RuntimeError("Failed to extract trx-calibration/remap.npz")
        trx_remap_file.write_bytes(extracted_remap.read())

    # 2. Verify TRX metadata
    if not trx_meta_file.is_file():
        raise RuntimeError(f"TRX metadata file not found at {trx_meta_file}")

    try:
        trx_meta = json.loads(trx_meta_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse TRX metadata: {exc}") from exc

    if trx_meta.get("validated") is not True:
        raise RuntimeError("TRX calibration metadata 'validated' is not True")

    if trx_meta.get("fingerprint") != EXPECTED_TRX_FINGERPRINT:
        raise RuntimeError(
            f"TRX fingerprint mismatch: {trx_meta.get('fingerprint')} != "
            f"{EXPECTED_TRX_FINGERPRINT}"
        )

    src_meta = trx_meta.get("source_metadata", {})
    if src_meta.get("detector_mode") != "TRX":
        raise RuntimeError(
            f"TRX metadata detector_mode mismatch: {src_meta.get('detector_mode')}"
        )

    if src_meta.get("id") != EXPECTED_TRX_PROFILE_ID:
        raise RuntimeError(
            f"TRX profile id mismatch: {src_meta.get('id')} != "
            f"{EXPECTED_TRX_PROFILE_ID}"
        )

    cam_params = src_meta.get("camera_params", {})
    if cam_params.get("serialNumber") != EXPECTED_TRX_CAMERA_SERIAL:
        raise RuntimeError(
            f"TRX camera serial mismatch: {cam_params.get('serialNumber')} != "
            f"{EXPECTED_TRX_CAMERA_SERIAL}"
        )

    meta_shape = tuple(trx_meta.get("image_shape", []))
    if meta_shape != EXPECTED_TRX_IMAGE_SHAPE:
        raise RuntimeError(
            f"TRX image shape mismatch: {meta_shape} != {EXPECTED_TRX_IMAGE_SHAPE}"
        )

    # 3. Verify TRX remap.npz
    if not trx_remap_file.is_file():
        raise RuntimeError(
            f"TRX remap.npz not found at {trx_remap_file}. Supply authorized archive."
        )

    remap_sha = compute_sha256(trx_remap_file)
    if remap_sha != EXPECTED_TRX_REMAP_SHA256:
        raise RuntimeError(
            f"TRX remap.npz SHA-256 mismatch: {remap_sha} != "
            f"{EXPECTED_TRX_REMAP_SHA256}"
        )

    import numpy as np

    try:
        with np.load(trx_remap_file) as remap_data:
            if "map_x" not in remap_data or "map_y" not in remap_data:
                raise RuntimeError("remap.npz missing map_x or map_y arrays")
            mx = remap_data["map_x"]
            my = remap_data["map_y"]
            if (
                mx.shape != EXPECTED_TRX_IMAGE_SHAPE
                or my.shape != EXPECTED_TRX_IMAGE_SHAPE
            ):
                raise RuntimeError(
                    f"remap map_x/map_y shape mismatch: {mx.shape} != "
                    f"{EXPECTED_TRX_IMAGE_SHAPE}"
                )
    except Exception as exc:
        raise RuntimeError(f"Failed to inspect remap.npz: {exc}") from exc

    # 4. Generate and verify synthetic BED calibration fixture deterministically
    bed_meta_file = bed_dir / "metadata.json"
    bed_remap_file = bed_dir / "remap.npz"

    # Ensure metadata.json exists
    if not bed_meta_file.is_file():
        bed_meta_data = {
            "validated": True,
            "fingerprint": "SYNTHETIC-EMBEDDED-BED-CALIBRATION-V1",
            "image_shape": [48, 64],
            "source_metadata": {
                "detector_mode": "BED",
                "camera_params": {"serialNumber": "SYNTHETIC-CAMERA"},
            },
            "classification": "SYNTHETIC_DEVELOPMENT_ONLY",
            "notice": (
                "Synthetic identity calibration profile for development and CI "
                "testing only. NOT FOR CLINICAL USE."
            ),
        }
        bed_meta_file.write_text(json.dumps(bed_meta_data, indent=2), encoding="utf-8")

    # Ensure remap.npz exists deterministically (identity coordinate grid)
    if not bed_remap_file.is_file():
        y_grid, x_grid = np.indices((48, 64), dtype=np.float32)
        np.savez_compressed(bed_remap_file, map_x=x_grid, map_y=y_grid)

    try:
        bed_meta = json.loads(bed_meta_file.read_text(encoding="utf-8"))
        if bed_meta.get("validated") is not True:
            raise RuntimeError("BED metadata 'validated' is not True")
        with np.load(bed_remap_file) as bed_data:
            if "map_x" not in bed_data or "map_y" not in bed_data:
                raise RuntimeError("BED remap.npz missing map_x/map_y")
            b_mx = bed_data["map_x"]
            b_my = bed_data["map_y"]
            if b_mx.shape != (48, 64) or b_my.shape != (48, 64):
                raise RuntimeError(f"BED remap array shape mismatch: {b_mx.shape}")
    except Exception as exc:
        raise RuntimeError(f"Failed to validate BED fixture: {exc}") from exc

    bed_remap_sha = compute_sha256(bed_remap_file)

    manifest_record = {
        "status": "VALIDATED",
        "archive_provenance": {
            "source_archive": str(source_archive) if source_archive else None,
            "sha256": archive_sha,
        },
        "profiles": {
            "trx_mode": {
                "profile_id": EXPECTED_TRX_PROFILE_ID,
                "detector_mode": "TRX",
                "camera_serial": EXPECTED_TRX_CAMERA_SERIAL,
                "fingerprint": EXPECTED_TRX_FINGERPRINT,
                "image_shape": list(EXPECTED_TRX_IMAGE_SHAPE),
                "remap_sha256": remap_sha,
                "remap_size_bytes": trx_remap_file.stat().st_size,
                "classification": "REAL_GEOMETRIC_CALIBRATION",
            },
            "bed_mode": {
                "detector_mode": "BED",
                "fingerprint": bed_meta.get("fingerprint"),
                "image_shape": bed_meta.get("image_shape"),
                "remap_sha256": bed_remap_sha,
                "classification": bed_meta.get("classification"),
            },
        },
    }

    manifest_path = manifest_output or (
        REPO_ROOT / "build-standalone" / "embedded_calibration_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_record, indent=2), encoding="utf-8")

    return manifest_record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-build calibration verification gate for mpips-runtime."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="Path to trx-calibration tar.gz archive.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Target calibration directory (defaults to mpips/resources/calibration).",
    )
    args = parser.parse_args()

    try:
        manifest = prepare_and_validate_calibration(
            archive_path=args.archive,
            output_dir=args.output_dir,
        )
        print("Pre-build calibration preparation and validation SUCCESSFUL.")
        print(f"TRX Remap SHA-256: {manifest['profiles']['trx_mode']['remap_sha256']}")
        manifest_loc = (
            REPO_ROOT / "build-standalone" / "embedded_calibration_manifest.json"
        )
        print(f"Manifest: {manifest_loc}")
        return 0
    except Exception as exc:
        sys.stderr.write(f"CALIBRATION BUILD GATE FAILURE: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
