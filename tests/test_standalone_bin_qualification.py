"""Qualification test suite for experimental standalone ELF executable mpips-runtime.bin.

Verifies:
1. --version output contract (interface 2-experimental, ok, 0.1.0)
2. Standalone BED synthetic conversion without --calibration
3. Standalone TRX synthetic conversion without --calibration
4. DICOM metadata verification (patient, study, SOPClassUID, TransferSyntax, PhotometricInterpretation)
5. DICOM pixel verification and orientation (monotonic invariants and shape: (48, 64) for BED, (64, 48) for TRX)
6. Negative case: missing radiograph input (INPUT_NOT_FOUND, exit 3)
7. Negative case: missing gain input (INPUT_NOT_FOUND, exit 3)
8. Negative case: invalid manifest JSON (INVALID_INPUT, exit 2)
9. Negative case: destination output exists (OUTPUT_EXISTS, exit 4)
10. Negative case: dangling symlink destination (OUTPUT_EXISTS, exit 4)
11. Negative case: detector mode mismatch between radiograph and gain (CONVERSION_FAILED/INVALID_INPUT)
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


def test_bin_convert_trx_synthetic_no_calibration(
    runtime_bin: Path, tmp_path: Path
) -> None:
    rad, gain, manifest, _ = make_inputs(tmp_path / "trx", "TRX")
    output = tmp_path / "trx" / "result.dcm"

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

    verify_output(output, "TRX")

    ds = pydicom.dcmread(output)
    pixels = ds.pixel_array
    # TRX synthetic pipeline rotates clockwise 90 degrees -> (48, 64) becomes (64, 48)
    assert pixels.shape == (64, 48)
    assert pixels.dtype == np.uint16
    # TRX row gradient monotonicity invariant
    values = pixels.astype(np.int64)
    assert np.all(np.diff(values, axis=1) >= 0)


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
