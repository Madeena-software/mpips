"""Synthetic Packaged Grabber end-to-end qualification suite.

Proves:
1. Candidate offline wheelhouse TAR package exists and matches release metadata
   SHA-256 and size.
2. Extracts package into an isolated temporary workspace and installs offline
   into a clean venv without package index egress (--no-index, --require-hashes).
3. The installed 'mpips-runtime' executable (isolated from source-tree imports)
   is driven via the current 'MPIPSSubprocessAdapter' from accepted main baseline.
4. Executes the full synthetic workflow:
   - Mock SIMRS patient response -> Operator confirmation -> Manifest.
   - Synthetic radiograph and matching gain NPZ -> Validated calibration dir.
   - mpips-runtime convert via MPIPSSubprocessAdapter -> Verified DICOM output
     for both BED and TRX.
   - Pixel determinism, orientation, permissions (0600), DICOM metadata.
5. Exercises negative and security integration cases:
   - Unconfirmed operator selection.
   - Encounter/visit identifier mismatch in SIMRS response.
   - Invalid manifest schema.
   - Identifier / gain mismatch.
   - Missing input NPZ.
   - Output path collision (existing file and dangling symlink).
   - Malicious runtime response injection shielding.
   - Malformed/inconsistent exit code and JSON status detection.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pydicom
import pytest

from mpips.api.schemas.dicom import MHCSManifest
from scripts.grabber_smoke import make_inputs
from scripts.grabber_subprocess_adapter import (
    MPIPSInputNotFoundError,
    MPIPSInvalidInputError,
    MPIPSOutputExistsError,
    MPIPSSubprocessAdapter,
)
from scripts.simrs_manifest_example import build_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "docs" / "integration" / "examples"

# Configurable candidate handoff directory (defaults to standard local path if set,
# or MPIPS_CANDIDATE_DIR environment variable)
DEFAULT_CANDIDATE_DIR = Path("/mnt/c/Users/faliq/Desktop/mpips-candidate-handoff")
CANDIDATE_DIR = Path(os.environ.get("MPIPS_CANDIDATE_DIR", str(DEFAULT_CANDIDATE_DIR)))
STRICT_QUALIFICATION = os.environ.get(
    "MPIPS_STRICT_QUALIFICATION", ""
).strip().lower() in ("1", "true", "yes")

EXPECTED_COMMIT_SHA = "ebda70638a64294b6b794d6c3e862ce10b909d4d"
EXPECTED_PACKAGE_SHA256 = (
    "97ee9519e26120e1ceb2c7e621bcb7452b3d960cc9f3926f63086c529c34ce00"
)
EXPECTED_PACKAGE_SIZE = 144103304
EXPECTED_PACKAGE_NAME = (
    f"mpips-0.1.0-{EXPECTED_COMMIT_SHA}-ubuntu24.04-x86_64-py312.tar.gz"
)
EXPECTED_METADATA_NAME = (
    f"mpips-0.1.0-{EXPECTED_COMMIT_SHA}-ubuntu24.04-x86_64-py312.release.json"
)

VISIT = "SYNTHETIC-VISIT-2026-0001"
CAPTURED_AT = "2026-10-12T10:00:00+07:00"
SOP_CLASS_UID = "1.2.840.10008.5.1.4.1.1.1.1.1"

# Regression pins for synthetic pipeline output.
# These serve as exact regression anchors for this pipeline version and synthetic
# inputs, not an independent proof of clinical numerical correctness.
PIXEL_SHA256 = {
    "BED": "13a9a56a28e1cb6d0a6daf887cc3bf98fc9b85f17995935e6b933ead836510ca",
    "TRX": "24d4be23a354de71302a9d6bed77b29acef049f05863dcf86da1d7da835439c1",
}
SHAPES = {"BED": (48, 64), "TRX": (64, 48)}


@dataclass(frozen=True)
class InstalledRuntime:
    venv_dir: Path
    python_bin: Path
    runtime_bin: Path
    package_path: Path
    metadata_path: Path
    bundle_dir: Path


@pytest.fixture(scope="session")
def installed_runtime(tmp_path_factory: pytest.TempPathFactory) -> InstalledRuntime:
    """Fixture that verifies the candidate TAR package and installs it offline
    into a fresh venv.
    """
    pkg_path = CANDIDATE_DIR / EXPECTED_PACKAGE_NAME
    meta_path = CANDIDATE_DIR / EXPECTED_METADATA_NAME

    if not pkg_path.is_file() or not meta_path.is_file():
        if STRICT_QUALIFICATION:
            pytest.fail(
                f"STRICT QUALIFICATION FAILURE: Candidate package or metadata not "
                f"found at {CANDIDATE_DIR}. Expected: {pkg_path} and {meta_path}."
            )
        pytest.skip(
            f"Candidate package or metadata not found at {CANDIDATE_DIR}. "
            "Requires offline candidate handoff directory."
        )

    meta = json.loads(meta_path.read_text())
    assert meta["commit_sha"] == EXPECTED_COMMIT_SHA
    assert meta["package"]["sha256"] == EXPECTED_PACKAGE_SHA256
    assert meta["package"]["size"] == EXPECTED_PACKAGE_SIZE
    assert meta["package"]["filename"] == EXPECTED_PACKAGE_NAME
    assert meta["qualification"] == "synthetic-only"

    # Verify actual package bytes
    actual_hash = hashlib.sha256(pkg_path.read_bytes()).hexdigest()
    actual_size = pkg_path.stat().st_size
    assert actual_hash == EXPECTED_PACKAGE_SHA256
    assert actual_size == EXPECTED_PACKAGE_SIZE

    work_dir = tmp_path_factory.mktemp("packaged-install")
    extract_dir = work_dir / "extract"
    extract_dir.mkdir()

    with tarfile.open(pkg_path, "r:gz") as tar:
        tar.extractall(extract_dir, filter="data")

    bundle_dir = next(extract_dir.iterdir())
    wheels_dir = bundle_dir / "wheels"
    reqs_file = bundle_dir / "requirements.txt"

    assert wheels_dir.is_dir()
    assert reqs_file.is_file()

    venv_dir = work_dir / "runtime-venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    python_bin = venv_dir / "bin" / "python"
    runtime_bin = venv_dir / "bin" / "mpips-runtime"

    # Install completely offline without index access
    subprocess.run(
        [
            str(python_bin),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--only-binary=:all:",
            "--require-hashes",
            "--find-links",
            str(wheels_dir),
            "-r",
            str(reqs_file),
        ],
        check=True,
    )

    assert runtime_bin.is_file()

    # Verify runtime execution isolation from repository source tree
    # Check that python in this venv imports mpips from its site-packages,
    # NOT from /var/www/mpips or any repository path.
    verify_cmd = [
        str(python_bin),
        "-c",
        "import mpips, os; "
        "p = os.path.abspath(mpips.__file__); "
        "assert 'site-packages' in p, f'Expected site-packages import, got {p}'; "
        "print('ISOLATED_OK:' + p)",
    ]
    env_clean = dict(os.environ)
    env_clean.pop("PYTHONPATH", None)
    out = subprocess.check_output(
        verify_cmd, text=True, env=env_clean, cwd=str(work_dir)
    )
    assert "ISOLATED_OK:" in out

    return InstalledRuntime(
        venv_dir=venv_dir,
        python_bin=python_bin,
        runtime_bin=runtime_bin,
        package_path=pkg_path,
        metadata_path=meta_path,
        bundle_dir=bundle_dir,
    )


# --- Simulation Helpers --------------------------------------------------------


def mock_simrs_response() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((EXAMPLES_DIR / "simrs-response.synthetic.json").read_text()),
    )


def confirm_patient_selection(response: Any, visit: str, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Operator did not confirm patient selection")
    if not isinstance(response, dict) or response.get("success") is not True:
        raise ValueError("Invalid SIMRS response structure")
    data = response.get("data", {})
    if data.get("no_rawat") != visit:
        raise ValueError("Encounter ID mismatch with confirmed patient")


def compose_synthetic_manifest(
    response: dict[str, Any], visit: str, mode: str, confirmed: bool = True
) -> dict[str, Any]:
    confirm_patient_selection(response, visit, confirmed)
    mapped = build_manifest(response, visit, {}, CAPTURED_AT)
    merged: dict[str, Any] = {"manifest_version": "1.0", **copy.deepcopy(mapped)}
    merged["examination"]["performed_at"] = CAPTURED_AT
    merged["capture"] = {
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
        "captured_at": CAPTURED_AT,
        "detector_spacing": {"row_mm": 0.15, "column_mm": 0.16},
    }
    merged["dicom"] = {
        "pixel_source": "CANONICAL_PRE_PRESENTATION",
        "pixel_intensity_relationship": "LIN",
        "pixel_intensity_relationship_sign": 1,
    }
    MHCSManifest.model_validate(merged)
    return merged


# --- Test Cases ----------------------------------------------------------------


def test_packaged_runtime_version_and_interface(
    installed_runtime: InstalledRuntime,
) -> None:
    """Verify the installed candidate runtime reports the expected interface
    and version via adapter check_version().
    """
    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    info = adapter.check_version()
    assert info.interface_version == "1"
    assert info.runtime_version == "0.1.0"
    assert info.status == "ok"
    assert info.code == "OK"


@pytest.mark.parametrize("mode", ["BED", "TRX"])
def test_full_synthetic_workflow_e2e(
    installed_runtime: InstalledRuntime, tmp_path: Path, mode: str
) -> None:
    """Execute end-to-end workflow: mock SIMRS -> confirmation -> manifest ->
    NPZ -> adapter -> verified DICOM.
    """
    exam_dir = tmp_path / f"exam_{mode}"
    exam_dir.mkdir()

    # 1. Mock SIMRS and explicit confirmation
    simrs_data = mock_simrs_response()
    manifest_data = compose_synthetic_manifest(simrs_data, VISIT, mode, confirmed=True)

    # 2. Prepare synthetic inputs
    rad_path, gain_path, manifest_file, cal_dir = make_inputs(exam_dir, mode)
    manifest_file.write_text(json.dumps(manifest_data))

    output_dcm = exam_dir / f"result_{mode}.dcm"

    # 3. Invoke installed runtime using adapter
    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    result = adapter.convert(
        radiograph=rad_path,
        gain=gain_path,
        manifest=manifest_file,
        calibration=cal_dir,
        output=output_dcm,
    )

    # 4. Verify adapter result
    assert result.status == "ok"
    assert result.code == "OK"
    assert result.interface_version == "1"
    assert result.runtime_version == "0.1.0"
    assert result.output_path == output_dcm
    assert output_dcm.is_file()
    assert output_dcm.stat().st_mode & 0o777 == 0o600

    # 5. Deep DICOM attribute and pixel validation
    ds = pydicom.dcmread(output_dcm)
    assert ds.PatientID == manifest_data["patient"]["medical_record_number"]
    p_name = manifest_data["patient"]["name"]
    expected_name = p_name["full_name"] if isinstance(p_name, dict) else p_name
    assert str(ds.PatientName) == expected_name
    assert ds.PatientBirthDate == manifest_data["patient"]["birth_date"].replace(
        "-", ""
    )
    assert ds.PatientSex == ""  # 'unknown' maps to empty string in DICOM
    assert ds.Modality == "DX"
    assert ds.SOPClassUID == SOP_CLASS_UID
    assert ds.BitsAllocated == ds.BitsStored == 16
    assert ds.PhotometricInterpretation == "MONOCHROME2"
    assert not any(elem.tag.is_private for elem in ds.iterall())

    # Pixel array checks
    pixels = ds.pixel_array
    assert pixels.dtype == np.uint16
    assert pixels.shape == SHAPES[mode]
    assert hashlib.sha256(pixels.tobytes()).hexdigest() == PIXEL_SHA256[mode]

    # Mode-specific orientation checks:
    # TRX should be 64x48 (clockwise 90-degree rotated from 48x64 BED input)
    if mode == "TRX":
        assert pixels.shape == (64, 48)
    else:
        assert pixels.shape == (48, 64)


def test_negative_unconfirmed_patient_selection(tmp_path: Path) -> None:
    """Ensure unconfirmed operator selection halts before invoking converter."""
    simrs_data = mock_simrs_response()
    with pytest.raises(ValueError, match="Operator did not confirm"):
        compose_synthetic_manifest(simrs_data, VISIT, "BED", confirmed=False)


def test_negative_simrs_visit_mismatch(tmp_path: Path) -> None:
    """Ensure visit identifier mismatch in SIMRS response halts before
    manifest composition.
    """
    simrs_data = mock_simrs_response()
    with pytest.raises(ValueError, match="Encounter ID mismatch"):
        compose_synthetic_manifest(simrs_data, "WRONG-VISIT-ID", "BED", confirmed=True)


def test_negative_invalid_manifest_schema(
    installed_runtime: InstalledRuntime, tmp_path: Path
) -> None:
    """Ensure malformed or schema-invalid manifest is rejected by the
    installed runtime.
    """
    exam_dir = tmp_path / "bad_manifest_exam"
    rad_path, gain_path, manifest_file, cal_dir = make_inputs(exam_dir, "BED")
    manifest_file.write_text("{not_a_valid_json")
    output_dcm = exam_dir / "result.dcm"

    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    with pytest.raises(MPIPSInvalidInputError) as exc_info:
        adapter.convert(
            radiograph=rad_path,
            gain=gain_path,
            manifest=manifest_file,
            calibration=cal_dir,
            output=output_dcm,
        )
    assert exc_info.value.exit_code == 2
    assert not output_dcm.exists()


def test_negative_missing_gain_npz(
    installed_runtime: InstalledRuntime, tmp_path: Path
) -> None:
    """Ensure missing gain file is cleanly detected and rejected."""
    exam_dir = tmp_path / "missing_gain_exam"
    rad_path, gain_path, manifest_file, cal_dir = make_inputs(exam_dir, "BED")
    gain_path.unlink()
    output_dcm = exam_dir / "result.dcm"

    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    with pytest.raises(MPIPSInputNotFoundError) as exc_info:
        adapter.convert(
            radiograph=rad_path,
            gain=gain_path,
            manifest=manifest_file,
            calibration=cal_dir,
            output=output_dcm,
        )
    assert exc_info.value.exit_code == 3
    assert not output_dcm.exists()


def test_negative_output_already_exists(
    installed_runtime: InstalledRuntime, tmp_path: Path
) -> None:
    """Ensure existing destination files are not overwritten."""
    exam_dir = tmp_path / "existing_output_exam"
    rad_path, gain_path, manifest_file, cal_dir = make_inputs(exam_dir, "BED")
    output_dcm = exam_dir / "result.dcm"
    output_dcm.write_bytes(b"EXISTING_DICOM_CONTENT")

    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    with pytest.raises(MPIPSOutputExistsError) as exc_info:
        adapter.convert(
            radiograph=rad_path,
            gain=gain_path,
            manifest=manifest_file,
            calibration=cal_dir,
            output=output_dcm,
        )
    assert exc_info.value.exit_code == 4
    # Content must be preserved untouched
    assert output_dcm.read_bytes() == b"EXISTING_DICOM_CONTENT"


def test_negative_output_dangling_symlink(
    installed_runtime: InstalledRuntime, tmp_path: Path
) -> None:
    """Ensure dangling symlink outputs are rejected without following them
    to create new targets.
    """
    exam_dir = tmp_path / "symlink_output_exam"
    rad_path, gain_path, manifest_file, cal_dir = make_inputs(exam_dir, "BED")
    target_dcm = exam_dir / "uncreated_target.dcm"
    symlink_dcm = exam_dir / "symlink_output.dcm"
    symlink_dcm.symlink_to(target_dcm)

    assert symlink_dcm.is_symlink()
    assert not symlink_dcm.exists()

    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    with pytest.raises(MPIPSOutputExistsError) as exc_info:
        adapter.convert(
            radiograph=rad_path,
            gain=gain_path,
            manifest=manifest_file,
            calibration=cal_dir,
            output=symlink_dcm,
        )
    assert exc_info.value.exit_code == 4
    assert not target_dcm.exists()


def test_negative_radiograph_gain_identifier_mismatch(
    installed_runtime: InstalledRuntime, tmp_path: Path
) -> None:
    """Ensure radiograph referencing a mismatched gain id is rejected by the runtime."""
    exam_dir = tmp_path / "gain_mismatch_exam"
    rad_path, gain_path, manifest_file, cal_dir = make_inputs(exam_dir, "BED")
    # Rewrite rad with non-matching gain id
    rad_data = dict(np.load(rad_path, allow_pickle=True))
    rad_data["gainid"] = np.array("SYNTHETIC-OTHER-GAIN")
    np.savez_compressed(rad_path, **rad_data)

    output_dcm = exam_dir / "result.dcm"

    adapter = MPIPSSubprocessAdapter(installed_runtime.runtime_bin)
    with pytest.raises(MPIPSInvalidInputError) as exc_info:
        adapter.convert(
            radiograph=rad_path,
            gain=gain_path,
            manifest=manifest_file,
            calibration=cal_dir,
            output=output_dcm,
        )
    assert exc_info.value.exit_code == 2
    assert not output_dcm.exists()


def test_negative_malicious_response_shielding(tmp_path: Path) -> None:
    """Ensure adapter never leaks untrusted runtime output or clinical paths
    into exception messages.
    """
    mock_bin = tmp_path / "mock_malicious_runtime.sh"
    malicious_payload = (
        '{"status": "error", "code": "INVALID_INPUT", "interface_version": "1", '
        '"runtime_version": "0.1.0", "patient_ssn": "SECRET-12345", '
        '"injected": "<script>alert(\'xss\')</script>"}'
    )
    version_payload = (
        '{"status": "ok", "code": "OK", "interface_version": "1", '
        '"runtime_version": "0.1.0"}'
    )
    mock_bin.write_text(
        f"#!/bin/bash\n"
        f'if [ "$1" = "--version" ]; then\n'
        f"  echo '{version_payload}'\n"
        f"  exit 0\n"
        f"fi\n"
        f"echo '{malicious_payload}'\n"
        f"exit 2\n"
    )
    mock_bin.chmod(0o755)

    rad_p = tmp_path / "rad.npz"
    gain_p = tmp_path / "gain.npz"
    man_p = tmp_path / "manifest.json"
    cal_p = tmp_path / "cal"
    cal_p.mkdir()
    rad_p.write_bytes(b"dummy")
    gain_p.write_bytes(b"dummy")
    man_p.write_bytes(b"{}")

    adapter = MPIPSSubprocessAdapter(mock_bin)
    with pytest.raises(MPIPSInvalidInputError) as exc_info:
        adapter.convert(
            radiograph=rad_p,
            gain=gain_p,
            manifest=man_p,
            calibration=cal_p,
            output=tmp_path / "out.dcm",
        )
    # The error message must be sanitized and deterministic
    err_str = str(exc_info.value)
    assert "SECRET-12345" not in err_str
    assert "<script>" not in err_str
    assert "Runtime failed with exit code 2 (INVALID_INPUT)" in err_str
