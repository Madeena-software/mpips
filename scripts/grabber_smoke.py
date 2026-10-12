"""Synthetic BED/TRX qualification using an installed local runtime executable."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pydicom


def make_inputs(root: Path, mode: str) -> tuple[Path, Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    shape = (48, 64)
    image = (np.arange(shape[0] * shape[1]).reshape(shape) + 200).astype(np.uint16)
    camera = {"serialNumber": "SYNTHETIC-CAMERA"}
    params = {"detectorMode": mode}
    rad, gain = root / "radiograph.npz", root / "gain.npz"
    np.savez_compressed(
        rad,
        id=np.array("SYNTHETIC-RAD"),
        gainid=np.array("SYNTHETIC-GAIN"),
        rawimage=image,
        cameraparams=np.array(camera),
        xrayparams=np.array(params),
    )
    np.savez_compressed(
        gain,
        id=np.array("SYNTHETIC-GAIN"),
        rawimage=np.full(shape, 5000, np.uint16),
        darkimage=np.full(shape, 50, np.uint16),
        cameraparams=np.array(camera),
        xrayparams=np.array(params),
    )
    cal = root / "calibration"
    cal.mkdir()
    y, x = np.indices(shape, dtype=np.float32)
    np.savez_compressed(cal / "remap.npz", map_x=x, map_y=y)
    (cal / "metadata.json").write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "SYNTHETIC-IDENTITY-REMAP",
                "image_shape": list(shape),
                "source_metadata": {"detector_mode": mode, "camera_params": camera},
            }
        )
    )
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "patient": {
                    "medical_record_number": "SYNTHETIC-001",
                    "name": "SYNTHETIC PATIENT",
                    "sex": "unknown",
                    "birth_date": "2000-01-02",
                },
                "examination": {
                    "encounter_id": "SYNTHETIC-VISIT-2026-0001",
                    "performed_at": "2026-10-12T10:00:00+07:00",
                },
                "capture": {
                    "detector_type": mode,
                    "body_part_examined": "CHEST",
                    "projection": "PA",
                    "view_code_sequence": [
                        {
                            "code_value": "272479007",
                            "coding_scheme_designator": "SCT",
                            "code_meaning": "postero-anterior",
                        }
                    ],
                    "captured_at": "2026-10-12T10:00:00+07:00",
                    "detector_spacing": {"row_mm": 0.15, "column_mm": 0.16},
                },
                "dicom": {
                    "pixel_source": "CANONICAL_PRE_PRESENTATION",
                    "pixel_intensity_relationship": "LIN",
                    "pixel_intensity_relationship_sign": 1,
                },
            }
        )
    )
    return rad, gain, manifest, cal


def verify_output(output: Path, mode: str) -> None:
    ds = pydicom.dcmread(output)
    assert ds.PatientID == "SYNTHETIC-001"
    assert ds.PatientName == "SYNTHETIC PATIENT"
    assert ds.PatientSex == ""
    assert ds.PatientBirthDate == "20000102"
    assert ds.AccessionNumber == ""
    assert ds.Modality == "DX"
    assert ds.SOPClassUID == "1.2.840.10008.5.1.4.1.1.1.1.1"
    assert ds.BitsAllocated == ds.BitsStored == 16
    assert ds.PixelRepresentation == 0
    assert ds.PhotometricInterpretation == "MONOCHROME2"
    assert ds.pixel_array.shape == ((64, 48) if mode == "TRX" else (48, 64))
    assert not any(element.tag.is_private for element in ds.iterall())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    with tempfile.TemporaryDirectory(prefix="mpips-synthetic-") as scratch:
        root = Path(scratch)
        for mode in ("BED", "TRX"):
            rad, gain, manifest, cal = make_inputs(root / mode, mode)
            output = root / mode / "result.dcm"
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [
                    str(runtime),
                    "convert",
                    "--radiograph",
                    str(rad),
                    "--gain",
                    str(gain),
                    "--manifest",
                    str(manifest),
                    "--calibration",
                    str(cal),
                    "--output",
                    str(output),
                ],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            assert json.loads(result.stdout)["status"] == "ok"
            assert not result.stderr
            verify_output(output, mode)
            assert output.stat().st_mode & 0o777 == 0o600
    print("Synthetic installed CLI: BED and TRX passed")


if __name__ == "__main__":
    main()
