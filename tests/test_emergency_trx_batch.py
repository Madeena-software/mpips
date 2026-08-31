import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
import pytest

from mpips.api.schemas.dicom import MHCSManifest
from mpips.workflows.imager_pipeline.emergency_batch import (
    DuplicateCaptureError,
    ManifestValidationError,
    derive_mrn,
    parse_trx_filename,
    run_emergency_batch,
)
from mpips.workflows.imager_pipeline.npz_io import load_radiograph


def _write_radiograph(
    path: Path,
    *,
    gain_id: str = "gain-trx",
    shape: tuple[int, int] = (4, 4),
    detector_mode: str = "TRX",
) -> None:
    np.savez_compressed(
        path,
        id="synthetic-radio",
        gainid=gain_id,
        xrayparams=np.asarray({"detectorMode": detector_mode}, dtype=object),
        rawimage=np.arange(np.prod(shape), dtype=np.uint16).reshape(shape),
        processedimage=np.full(shape, 0.25, dtype=np.float32),
    )


def _write_gain(
    path: Path, *, shape: tuple[int, int] = (4, 4), detector_mode: str = "TRX"
) -> None:
    np.savez_compressed(
        path,
        id="gain-trx",
        xrayparams=np.asarray({"detectorMode": detector_mode}, dtype=object),
        darkimage=np.zeros(shape, dtype=np.uint16),
        rawimage=np.full(shape, 1000, dtype=np.uint16),
    )


def _write_calibration(path: Path, *, shape: tuple[int, int] = (4, 4)) -> None:
    path.mkdir()
    np.savez_compressed(
        path / "remap.npz",
        map_x=np.indices(shape, dtype=np.float32)[1],
        map_y=np.indices(shape, dtype=np.float32)[0],
    )
    (path / "metadata.json").write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "synthetic-trx",
                "image_shape": list(shape),
                "source_metadata": {"detector_mode": "TRX"},
            }
        )
    )


def _manifest(
    path: Path, rows: list[dict[str, str]], gain: Path, calibration: Path
) -> None:
    path.write_text(
        json.dumps(
            {
                "gain_path": str(gain),
                "calibration_dir": str(calibration),
                "cases": rows,
            }
        )
    )


def test_trx_filename_derives_hyphenated_mrn_and_normalizes_copy_suffix() -> None:
    assert parse_trx_filename("TRX_123456789.npz") == "123456789"
    assert parse_trx_filename("TRX_123456789 (1).npz") == "123456789"
    assert derive_mrn("123456789") == "MRN-123456789"


def test_canonical_radiograph_boundary_ignores_processedimage(tmp_path: Path) -> None:
    source = tmp_path / "TRX_123456789.npz"
    _write_radiograph(source)

    loaded = load_radiograph(source)

    assert set(loaded) == {
        "path",
        "id",
        "gain_id",
        "raw",
        "camera_params",
        "detector_mode",
    }
    np.testing.assert_array_equal(
        loaded["raw"], np.arange(16, dtype=np.uint16).reshape(4, 4)
    )


def test_dry_run_passes_for_valid_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "TRX_123456789.npz"
    _write_radiograph(source)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest, [{"source": source.name, "patient_name": "ALPHA"}], gain, calibration
    )
    monkeypatch.setattr(
        sys, "argv", ["emergency_batch", str(manifest), "out", "--dry-run"]
    )

    from mpips.workflows.imager_pipeline.emergency_batch import main

    main()
    assert capsys.readouterr().out == "preflight passed: 1 cases\n"


@pytest.mark.parametrize(
    "case_kwargs",
    [
        {"corrupt": True},
        {"gain_id": "unknown-gain"},
        {"detector_mode": "BED"},
        {"shape": (8, 8)},
    ],
)
def test_dry_run_fails_for_invalid_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    case_kwargs: dict[str, Any],
) -> None:
    source = tmp_path / "TRX_123456789.npz"
    if case_kwargs.pop("corrupt", False):
        source.write_bytes(b"bad")
    else:
        _write_radiograph(source, **case_kwargs)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest, [{"source": source.name, "patient_name": "ALPHA"}], gain, calibration
    )
    monkeypatch.setattr(
        sys, "argv", ["emergency_batch", str(manifest), "out", "--dry-run"]
    )

    from mpips.workflows.imager_pipeline.emergency_batch import main

    with pytest.raises(SystemExit, match="1"):
        main()
    captured = capsys.readouterr()
    assert "preflight failed" in captured.err
    assert "123456789" in captured.err


@pytest.mark.parametrize(
    "name", ["radio.npz", "TRX_.npz", "TRX_12x.npz", "TRX_1.npz.bak"]
)
def test_trx_filename_rejects_noncanonical_names(name: str) -> None:
    with pytest.raises(ManifestValidationError):
        parse_trx_filename(name)


def test_duplicate_capture_id_fails_before_conversion(tmp_path: Path) -> None:
    first = tmp_path / "TRX_123456789.npz"
    second = tmp_path / "TRX_123456789 (1).npz"
    _write_radiograph(first)
    _write_radiograph(second)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest,
        [
            {"source": first.name, "patient_name": "ALPHA"},
            {"source": second.name, "patient_name": "ALPHA"},
        ],
        gain,
        calibration,
    )

    with pytest.raises(DuplicateCaptureError, match="123456789"):
        run_emergency_batch(manifest, tmp_path / "out", converter=lambda *args: None)


def test_batch_isolates_failure_and_rerun_is_idempotent(tmp_path: Path) -> None:
    first = tmp_path / "TRX_123456789.npz"
    broken = tmp_path / "TRX_987654321.npz"
    third = tmp_path / "TRX_555555555.npz"
    _write_radiograph(first)
    broken.write_bytes(b"not-an-npz")
    _write_radiograph(third)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest,
        [
            {"source": first.name, "patient_name": "ALPHA"},
            {"source": broken.name, "patient_name": "BROKEN"},
            {"source": third.name, "patient_name": "CHARLIE"},
        ],
        gain,
        calibration,
    )

    calls: list[str] = []

    def convert(manifest: MHCSManifest, _gain: Path, output: Path) -> None:
        calls.append(manifest.patient.medical_record_number)
        output.write_bytes(manifest.patient.medical_record_number.encode())

    result = run_emergency_batch(manifest, tmp_path / "out", converter=convert)

    assert result["counts"] == {"total": 3, "succeeded": 2, "failed": 1}
    assert calls == ["MRN-123456789", "MRN-555555555"]
    assert (tmp_path / "out" / "MRN-123456789.dcm").read_bytes() == b"MRN-123456789"
    assert not (tmp_path / "out" / "MRN-987654321.dcm").exists()
    assert "ALPHA" not in json.dumps(result)

    second = run_emergency_batch(manifest, tmp_path / "out", converter=convert)
    assert second["counts"] == {"total": 3, "succeeded": 0, "failed": 3}
    assert calls == ["MRN-123456789", "MRN-555555555"]


def test_synthetic_batch_uses_canonical_dicom_path(tmp_path: Path) -> None:
    source = tmp_path / "TRX_123456789.npz"
    _write_radiograph(source)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest, [{"source": source.name, "patient_name": "ALPHA"}], gain, calibration
    )

    result = run_emergency_batch(manifest, tmp_path / "out")
    output = tmp_path / "out" / "MRN-123456789.dcm"
    dataset = pydicom.dcmread(output)

    assert result["counts"] == {"total": 1, "succeeded": 1, "failed": 0}
    assert dataset.PatientName == "ALPHA"
    assert dataset.PatientID == "MRN-123456789"
    assert dataset.Rows == 4
    assert dataset.Columns == 4
    assert "completed: 123456789" in (tmp_path / "out" / "summary.txt").read_text()


def _canonical_manifest(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "TRX_123456789.npz"
    _write_radiograph(source)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest, [{"source": source.name, "patient_name": "ALPHA"}], gain, calibration
    )
    return manifest, gain, calibration


def test_valid_existing_dicom_is_verified_before_skip(tmp_path: Path) -> None:
    manifest, _, _ = _canonical_manifest(tmp_path)
    output_dir = tmp_path / "out"
    first = run_emergency_batch(manifest, output_dir)

    def fail_if_called(*_args: object) -> None:
        raise AssertionError("valid output should be skipped")

    second = run_emergency_batch(manifest, output_dir, converter=fail_if_called)

    assert first["counts"] == {"total": 1, "succeeded": 1, "failed": 0}
    assert second["items"][0]["status"] == "skipped"


@pytest.mark.parametrize("mutation", ["zero", "arbitrary", "wrong-patient"])
def test_invalid_existing_output_fails_safe(tmp_path: Path, mutation: str) -> None:
    manifest, _, _ = _canonical_manifest(tmp_path)
    output_dir = tmp_path / "out"
    run_emergency_batch(manifest, output_dir)
    output = output_dir / "MRN-123456789.dcm"
    if mutation == "zero":
        output.write_bytes(b"")
    elif mutation == "arbitrary":
        output.write_bytes(b"not-a-dicom")
    else:
        dataset = pydicom.dcmread(output)
        dataset.PatientID = "MRN-999999999"
        dataset.save_as(output)

    result = run_emergency_batch(manifest, output_dir, converter=lambda *_args: None)

    assert result["items"][0]["status"] == "failed"
    assert result["items"][0]["error"]


def test_canonical_multi_case_outputs_are_identity_isolated(tmp_path: Path) -> None:
    first = tmp_path / "TRX_123456789.npz"
    second = tmp_path / "TRX_987654321.npz"
    _write_radiograph(first)
    _write_radiograph(second)
    gain = tmp_path / "gain.npz"
    _write_gain(gain)
    calibration = tmp_path / "calibration"
    _write_calibration(calibration)
    manifest = tmp_path / "manifest.json"
    _manifest(
        manifest,
        [
            {"source": first.name, "patient_name": "ALPHA"},
            {"source": second.name, "patient_name": "BRAVO"},
        ],
        gain,
        calibration,
    )

    result = run_emergency_batch(manifest, tmp_path / "out")
    alpha = pydicom.dcmread(tmp_path / "out" / "MRN-123456789.dcm")
    bravo = pydicom.dcmread(tmp_path / "out" / "MRN-987654321.dcm")

    assert result["counts"] == {"total": 2, "succeeded": 2, "failed": 0}
    assert (alpha.PatientID, str(alpha.PatientName)) == ("MRN-123456789", "ALPHA")
    assert (bravo.PatientID, str(bravo.PatientName)) == ("MRN-987654321", "BRAVO")
    assert "BRAVO" not in str(alpha)
    assert "ALPHA" not in str(bravo)


def test_gain_shape_mismatch_is_reported_before_conversion(tmp_path: Path) -> None:
    manifest, _, calibration = _canonical_manifest(tmp_path)
    _write_gain(tmp_path / "gain.npz", shape=(8, 8))

    result = run_emergency_batch(
        manifest, tmp_path / "out", converter=lambda *_args: None
    )

    assert result["items"][0]["status"] == "failed"
    assert result["items"][0]["error"] == "ManifestValidationError"


def test_calibration_remap_shape_mismatch_fails_shared_preflight(
    tmp_path: Path,
) -> None:
    manifest, _, calibration = _canonical_manifest(tmp_path)
    np.savez_compressed(
        calibration / "remap.npz",
        map_x=np.zeros((4, 4), dtype=np.float32),
        map_y=np.zeros((8, 8), dtype=np.float32),
    )

    with pytest.raises(ManifestValidationError, match="remap shapes differ"):
        run_emergency_batch(manifest, tmp_path / "out", converter=lambda *_args: None)


def test_calibration_image_shape_mismatch_fails_shared_preflight(
    tmp_path: Path,
) -> None:
    manifest, _, calibration = _canonical_manifest(tmp_path)
    metadata = json.loads((calibration / "metadata.json").read_text())
    metadata["image_shape"] = [8, 8]
    (calibration / "metadata.json").write_text(json.dumps(metadata))

    with pytest.raises(ManifestValidationError, match="does not match image_shape"):
        run_emergency_batch(manifest, tmp_path / "out", converter=lambda *_args: None)
