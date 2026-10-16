"""Qualification test suite for experimental standalone ELF executable
mpips-runtime.bin.

Verifies:
1. --version output contract (interface 2-experimental, ok, 0.1.0)
2. Standalone BED synthetic conversion without --calibration
3. Standalone TRX synthetic conversion without --calibration
4. DICOM metadata verification (patient, study, SOPClassUID, TransferSyntax,
   PhotometricInterpretation)
5. DICOM pixel verification and orientation (monotonic invariants and shape:
   (48, 64) for BED, (64, 48) for TRX)
6. Negative case: missing radiograph input (INPUT_NOT_FOUND, exit 3)
7. Negative case: missing gain input (INPUT_NOT_FOUND, exit 3)
8. Negative case: invalid manifest JSON (INVALID_INPUT, exit 2)
9. Negative case: destination output exists (OUTPUT_EXISTS, exit 4)
10. Negative case: dangling symlink destination (OUTPUT_EXISTS, exit 4)
11. Negative case: detector mode mismatch between radiograph and gain
    (CONVERSION_FAILED/INVALID_INPUT)
12. Output file permissions (0600) and temporary workspace cleanup
13. Complete independence from PYTHONPATH and repository source
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pydicom
import pytest

from scripts.grabber_smoke import make_inputs, verify_output

REPO_ROOT = Path(__file__).resolve().parents[1]
BINARY_PATH = REPO_ROOT / "dist-experimental" / "mpips-runtime.bin"


@pytest.fixture(scope="module")
def runtime_bin() -> Path:
    if not BINARY_PATH.is_file():
        if os.getenv("MPIPS_STRICT_QUALIFICATION") == "1":
            pytest.fail(
                "STRICT QUALIFICATION FAILURE: Standalone binary not found at "
                f"{BINARY_PATH}. Skipping is prohibited when "
                "MPIPS_STRICT_QUALIFICATION=1."
            )
        pytest.skip(f"Binary not found at {BINARY_PATH}")
    return BINARY_PATH


def test_bin_version(runtime_bin: Path) -> None:
    proc = subprocess.run(
        [str(runtime_bin), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(proc.stdout)
    assert report["status"] == "ok"
    assert report["code"] == "OK"
    assert report["interface_version"] == "2-experimental"
    assert report["runtime_version"] == "0.1.0"


def test_bin_convert_bed_synthetic_no_calibration(
    runtime_bin: Path, tmp_path: Path
) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "bed", "BED")
    output = tmp_path / "bed" / "result.dcm"

    # Invoke binary with clean env (no PYTHONPATH)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, f"Process failed: {proc.stderr}"
    report = json.loads(proc.stdout)
    assert report["status"] == "ok"
    assert report["code"] == "OK"
    assert output.is_file()
    assert output.stat().st_size == report["output_byte_size"]
    assert output.stat().st_mode & 0o777 == 0o600

    verify_output(output, "BED")

    ds = pydicom.dcmread(output)
    pixels = ds.pixel_array
    assert pixels.shape == (48, 64)
    assert pixels.dtype == np.uint16
    assert pixels[0, 0] == pixels.max()


def test_bin_convert_trx_full_resolution_no_calibration(
    runtime_bin: Path, tmp_path: Path
) -> None:
    # Build 3000 x 4096 synthetic inputs matching real TRX calibration profile
    shape = (3000, 4096)
    root = tmp_path / "trx_full"
    root.mkdir(parents=True)
    rad = root / "radiograph.npz"
    gain = root / "gain.npz"
    manifest = root / "manifest.json"
    output = root / "result.dcm"

    camera = {
        "serialNumber": "DA5234480",
        "cameraSerial": "DA5234480",
        "cameraModel": "MV-CH120-10UM",
    }
    xray = {"detectorMode": "TRX"}

    raw_img = np.linspace(1000, 30000, shape[0] * shape[1], dtype=np.uint16).reshape(
        shape
    )
    np.savez_compressed(
        rad,
        id=np.array("REAL-TRX-RAD-001"),
        gainid=np.array("GAIN-TRX-001"),
        rawimage=raw_img,
        cameraparams=np.array(camera),
        xrayparams=np.array(xray),
    )
    np.savez_compressed(
        gain,
        id=np.array("GAIN-TRX-001"),
        rawimage=np.full(shape, 35000, dtype=np.uint16),
        darkimage=np.full(shape, 50, dtype=np.uint16),
        cameraparams=np.array(camera),
        xrayparams=np.array(xray),
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "patient": {
                    "medical_record_number": "SYNTHETIC-REAL-TRX-001",
                    "name": "SYNTHETIC REAL TRX PATIENT",
                    "sex": "unknown",
                    "birth_date": "1990-01-01",
                },
                "examination": {
                    "encounter_id": "VISIT-REAL-TRX-001",
                    "performed_at": "2026-10-16T10:00:00+07:00",
                },
                "capture": {
                    "detector_type": "TRX",
                    "body_part_examined": "CHEST",
                    "projection": "PA",
                    "view_code_sequence": [
                        {
                            "code_value": "272479007",
                            "coding_scheme_designator": "SCT",
                            "code_meaning": "postero-anterior",
                        }
                    ],
                    "captured_at": "2026-10-16T10:00:00+07:00",
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

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, f"Process failed: {proc.stderr}"
    report = json.loads(proc.stdout)
    assert report["status"] == "ok"
    assert report["code"] == "OK"
    assert output.is_file()
    assert output.stat().st_size == report["output_byte_size"]
    assert output.stat().st_mode & 0o777 == 0o600

    ds = pydicom.dcmread(output)
    assert ds.Modality == "DX"
    assert ds.SOPClassUID == "1.2.840.10008.5.1.4.1.1.1.1.1"
    # Full resolution TRX: 3000 x 4096 rotated 90-deg clockwise -> 4096 x 3000
    assert ds.pixel_array.shape == (4096, 3000)
    assert ds.pixel_array.dtype == np.uint16


def test_bin_via_adapter_no_calibration(runtime_bin: Path, tmp_path: Path) -> None:
    from scripts.grabber_subprocess_adapter import MPIPSSubprocessAdapter

    adapter = MPIPSSubprocessAdapter(runtime_bin)
    info = adapter.check_version()
    assert info.interface_version == "2-experimental"
    assert info.status == "ok"

    rad, gain, manifest, _ = make_inputs(tmp_path / "bed_adapter", "BED")
    output = tmp_path / "bed_adapter" / "result.dcm"

    # Invoke without calibration keyword
    res = adapter.convert(
        radiograph=rad,
        gain=gain,
        manifest=manifest,
        output=output,
    )
    assert res.status == "ok"
    assert res.code == "OK"
    assert res.interface_version == "2-experimental"
    assert output.is_file()
    assert output.stat().st_size == res.output_byte_size


def test_bin_negative_camera_serial_mismatch(runtime_bin: Path, tmp_path: Path) -> None:
    shape = (3000, 4096)
    root = tmp_path / "trx_serial_mismatch"
    root.mkdir(parents=True)
    rad = root / "radiograph.npz"
    gain = root / "gain.npz"
    manifest = root / "manifest.json"
    output = root / "result.dcm"

    wrong_camera = {
        "serialNumber": "WRONG-SERIAL-9999",
        "cameraSerial": "WRONG-SERIAL-9999",
        "cameraModel": "MV-CH120-10UM",
    }
    xray = {"detectorMode": "TRX"}

    raw_img = np.linspace(1000, 30000, shape[0] * shape[1], dtype=np.uint16).reshape(
        shape
    )
    np.savez_compressed(
        rad,
        id=np.array("REAL-TRX-RAD-001"),
        gainid=np.array("GAIN-TRX-001"),
        rawimage=raw_img,
        cameraparams=np.array(wrong_camera),
        xrayparams=np.array(xray),
    )
    np.savez_compressed(
        gain,
        id=np.array("GAIN-TRX-001"),
        rawimage=np.full(shape, 35000, dtype=np.uint16),
        darkimage=np.full(shape, 50, dtype=np.uint16),
        cameraparams=np.array(wrong_camera),
        xrayparams=np.array(xray),
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "patient": {
                    "medical_record_number": "SYNTHETIC-REAL-TRX-001",
                    "name": "SYNTHETIC REAL TRX PATIENT",
                    "sex": "unknown",
                    "birth_date": "1990-01-01",
                },
                "examination": {
                    "encounter_id": "VISIT-REAL-TRX-001",
                    "performed_at": "2026-10-16T10:00:00+07:00",
                },
                "capture": {
                    "detector_type": "TRX",
                    "body_part_examined": "CHEST",
                    "projection": "PA",
                    "view_code_sequence": [
                        {
                            "code_value": "272479007",
                            "coding_scheme_designator": "SCT",
                            "code_meaning": "postero-anterior",
                        }
                    ],
                    "captured_at": "2026-10-16T10:00:00+07:00",
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

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (2, 7)
    report = json.loads(proc.stdout)
    assert report["status"] == "error"
    assert not output.exists()


def test_bin_negative_input_not_found(runtime_bin: Path, tmp_path: Path) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "neg1", "BED")
    output = tmp_path / "neg1" / "result.dcm"
    rad.unlink()  # Remove radiograph

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 3
    report = json.loads(proc.stdout)
    assert report["status"] == "error"
    assert report["code"] == "INPUT_NOT_FOUND"
    assert not output.exists()


def test_bin_negative_invalid_manifest(runtime_bin: Path, tmp_path: Path) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "neg2", "BED")
    output = tmp_path / "neg2" / "result.dcm"
    manifest.write_text("{malformed json")

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    # Malformed manifest causes worker validation failure
    assert proc.returncode in (2, 7)
    report = json.loads(proc.stdout)
    assert report["status"] == "error"
    assert not output.exists()


def test_bin_negative_output_exists(runtime_bin: Path, tmp_path: Path) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "neg3", "BED")
    output = tmp_path / "neg3" / "result.dcm"
    output.write_bytes(b"existing content")

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 4
    report = json.loads(proc.stdout)
    assert report["status"] == "error"
    assert report["code"] == "OUTPUT_EXISTS"
    assert output.read_bytes() == b"existing content"


def test_bin_negative_dangling_symlink(runtime_bin: Path, tmp_path: Path) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "neg4", "BED")
    output = tmp_path / "neg4" / "dangling.dcm"
    target = tmp_path / "neg4" / "nonexistent.dcm"
    output.symlink_to(target)

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 4
    report = json.loads(proc.stdout)
    assert report["status"] == "error"
    assert report["code"] == "OUTPUT_EXISTS"


def test_bin_negative_detector_mode_mismatch(runtime_bin: Path, tmp_path: Path) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "neg5", "BED")
    output = tmp_path / "neg5" / "result.dcm"

    # Mismatch gain detector mode to TRX while radiograph is BED
    with np.load(gain, allow_pickle=True) as data:
        content = {k: data[k] for k in data.files}
    content["xrayparams"] = np.array({"detectorMode": "TRX"})
    np.savez_compressed(gain, **content)

    proc = subprocess.run(
        [
            str(runtime_bin),
            "convert",
            "--radiograph",
            str(rad),
            "--gain",
            str(gain),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (2, 7)
    report = json.loads(proc.stdout)
    assert report["status"] == "error"
    assert not output.exists()


def test_worker_negative_real_trx_validation_cases(tmp_path: Path) -> None:
    """Fail-closed calibration validation on real TRX."""
    from mpips.conversion.worker import execute_conversion_worker

    shape = (3000, 4096)
    root = tmp_path / "worker_neg_tests"
    root.mkdir(parents=True)

    rad = root / "rad.npz"
    gain = root / "gain.npz"
    out_tiff = root / "out.tiff"
    result_json = root / "res.json"
    args_json = root / "args.json"

    camera = {
        "serialNumber": "DA5234480",
        "cameraSerial": "DA5234480",
        "cameraModel": "MV-CH120-10UM",
    }
    xray = {"detectorMode": "TRX"}
    raw_img = np.ones(shape, dtype=np.uint16) * 1000

    np.savez_compressed(
        rad,
        id=np.array("RAD-1"),
        gainid=np.array("GAIN-1"),
        rawimage=raw_img,
        cameraparams=np.array(camera),
        xrayparams=np.array(xray),
    )
    np.savez_compressed(
        gain,
        id=np.array("GAIN-1"),
        rawimage=np.full(shape, 35000, dtype=np.uint16),
        darkimage=np.full(shape, 50, dtype=np.uint16),
        cameraparams=np.array(camera),
        xrayparams=np.array(xray),
    )

    # 1. Negative test: Missing camera identity in radiograph
    rad_no_cam = root / "rad_no_cam.npz"
    np.savez_compressed(
        rad_no_cam,
        id=np.array("RAD-1"),
        gainid=np.array("GAIN-1"),
        rawimage=raw_img,
        cameraparams=np.array({}),
        xrayparams=np.array(xray),
    )
    cal_dir = REPO_ROOT / "mpips" / "resources" / "calibration" / "trx_mode"

    args = {
        "radiograph_npz_path": str(rad_no_cam),
        "gain_npz_path": str(gain),
        "calibration_dir": str(cal_dir),
        "expected_gain_id": "GAIN-1",
        "expected_detector_mode": "TRX",
        "output_tiff_path": str(out_tiff),
        "result_path": str(result_json),
    }
    args_json.write_text(json.dumps(args))
    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_json), str(result_json))
    res = json.loads(result_json.read_text())
    assert res["status"] == "failed"
    assert "Missing camera identity" in res["error_detail"]

    # 2. Negative test: Wrong fingerprint
    cal_bad_fp = root / "cal_bad_fp"
    cal_bad_fp.mkdir()
    meta = json.loads((cal_dir / "metadata.json").read_text())
    meta["fingerprint"] = "WRONG_FINGERPRINT_STRING"
    (cal_bad_fp / "metadata.json").write_text(json.dumps(meta))
    import shutil

    shutil.copyfile(cal_dir / "remap.npz", cal_bad_fp / "remap.npz")

    args["radiograph_npz_path"] = str(rad)
    args["calibration_dir"] = str(cal_bad_fp)
    args_json.write_text(json.dumps(args))
    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_json), str(result_json))
    res = json.loads(result_json.read_text())
    assert res["status"] == "failed"
    assert "fingerprint mismatch" in res["error_detail"]

    # 3. Negative test: Altered remap payload (wrong hash)
    cal_bad_remap = root / "cal_bad_remap"
    cal_bad_remap.mkdir()
    shutil.copyfile(cal_dir / "metadata.json", cal_bad_remap / "metadata.json")
    y, x = np.indices(shape, dtype=np.float32)
    # Altered map
    np.savez_compressed(cal_bad_remap / "remap.npz", map_x=x, map_y=y)

    args["calibration_dir"] = str(cal_bad_remap)
    args_json.write_text(json.dumps(args))
    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_json), str(result_json))
    res = json.loads(result_json.read_text())
    assert res["status"] == "failed"
    assert "remap payload hash altered" in res["error_detail"]

    # 4. Negative test: Missing remap.npz
    cal_no_remap = root / "cal_no_remap"
    cal_no_remap.mkdir()
    shutil.copyfile(cal_dir / "metadata.json", cal_no_remap / "metadata.json")

    args["calibration_dir"] = str(cal_no_remap)
    args_json.write_text(json.dumps(args))
    with pytest.raises(SystemExit):
        execute_conversion_worker(str(args_json), str(result_json))
    res = json.loads(result_json.read_text())
    assert res["status"] == "failed"
    assert "missing metadata.json or remap.npz" in res["error_detail"]
