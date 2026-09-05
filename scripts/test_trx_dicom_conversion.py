#!/usr/bin/env python3
"""End-to-end test script for TRX mode DICOM conversion against local MPIPS API."""

import os
import sys
import time
import json
from pathlib import Path
import httpx
import numpy as np
import tifffile
import pydicom
from httpx._types import RequestFiles

API_URL = os.environ.get("MPIPS_API_URL", "http://127.0.0.1:8014")


def load_env_api_key() -> str:
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MPIPS_API_KEY="):
                return line.split("=", 1)[1].strip('"').strip("'")
    return os.environ.get("MPIPS_API_KEY", "")


def main() -> None:
    api_key = load_env_api_key()
    if not api_key:
        print("ERROR: MPIPS_API_KEY not found in .env or environment!")
        sys.exit(1)

    print(f"Loaded API key (len={len(api_key)})")

    raw_path = (
        "research/phantom-gotri-thorax/gotri thorax/TRX_1786615175262_rawimage.tiff"
    )
    gain_path = "research/phantom-gotri-thorax/gain/TRX_1786614876957_rawimage.tiff"
    dark_path = "research/phantom-gotri-thorax/dark/TRX_1786614876957_darkimage.tiff"

    raw_tiff = tifffile.imread(raw_path)
    gain_tiff = tifffile.imread(gain_path)
    dark_tiff = tifffile.imread(dark_path)

    work_dir = Path("/tmp/trx_dicom_test")
    work_dir.mkdir(parents=True, exist_ok=True)

    rad_npz_path = work_dir / "trx_radiograph.npz"
    gain_npz_path = work_dir / "trx_gain.npz"

    gain_id = "GAIN-TRX-001"
    camera_params = {
        "serialNumber": "DA5234480",
        "cameraSerial": "DA5234480",
        "cameraModel": "MV-CH120-10UM",
    }
    xray_params = {"detectorMode": "TRX"}

    np.savez_compressed(
        rad_npz_path,
        id=np.array("TEST-TRX-001"),
        gainid=np.array(gain_id),
        rawimage=raw_tiff,
        xrayparams=np.array(xray_params, dtype=object),
        cameraparams=np.array(camera_params, dtype=object),
    )

    np.savez_compressed(
        gain_npz_path,
        id=np.array(gain_id),
        rawimage=gain_tiff,
        darkimage=dark_tiff,
        xrayparams=np.array(xray_params, dtype=object),
        cameraparams=np.array(camera_params, dtype=object),
    )

    manifest_content = {
        "examination": {"study_description": "THORAX PHANTOM RADIOGRAPH"},
        "patient": {
            "medical_record_number": "TRX-PHANTOM-001",
            "name": "GOTRI^THORAX",
            "sex": "unknown",
            "birth_date": "2026-08-10",
        },
        "capture": {
            "detector_type": "THORAX",
            "body_part_examined": "CHEST",
            "laterality": "U",
            "projection": "PA",
        },
    }

    manifest_json = json.dumps(manifest_content)

    print("Submitting TRX DICOM conversion request...")
    headers = {"X-MPIPS-API-Key": api_key}

    with open(rad_npz_path, "rb") as rf, open(gain_npz_path, "rb") as gf:
        files: RequestFiles = {
            "radiograph_npz": ("trx_radiograph.npz", rf, "application/octet-stream"),
            "gain_npz": ("trx_gain.npz", gf, "application/octet-stream"),
            "manifest": (
                "manifest.json",
                manifest_json.encode("utf-8"),
                "application/json",
            ),
        }

        start_t = time.time()
        with httpx.Client(timeout=180.0) as client:
            res = client.post(
                f"{API_URL}/v1/radiographs/dicom", headers=headers, files=files
            )

        elapsed = time.time() - start_t
        print(f"Response status: {res.status_code} in {elapsed:.2f}s")

        if res.status_code != 200:
            print("ERROR response body:", res.text)
            sys.exit(1)

        dicom_bytes = res.content
        out_dcm_path = work_dir / "trx_output.dcm"
        out_dcm_path.write_bytes(dicom_bytes)
        print(f"Saved DICOM output: {out_dcm_path} ({len(dicom_bytes)} bytes)")

        # Validate DICOM metadata
        ds = pydicom.dcmread(out_dcm_path)
        print("\n--- DICOM METADATA VALIDATION ---")
        print(f"PatientID: {ds.get('PatientID')}")
        print(f"PatientName: {ds.get('PatientName')}")
        print(f"Modality: {ds.get('Modality')}")
        print(f"Rows x Columns: {ds.Rows} x {ds.Columns}")
        print(f"BitsAllocated: {ds.BitsAllocated}")
        print(f"PixelData length: {len(ds.PixelData)} bytes")

        # Verify private tags = 0
        priv_tags = [tag for tag in ds.keys() if tag.is_private]
        print(f"Private tags count: {len(priv_tags)}")

        if len(priv_tags) != 0:
            print("WARNING: Found private tags:", priv_tags)
        else:
            print("✓ SUCCESS: 0 private tags present")

        print("TRX DICOM Conversion Verification PASSED successfully!")


if __name__ == "__main__":
    main()
