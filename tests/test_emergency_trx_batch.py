import json
from pathlib import Path

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


def _write_radiograph(path: Path, *, gain_id: str = "gain-trx") -> None:
    np.savez_compressed(
        path,
        id="synthetic-radio",
        gainid=gain_id,
        xrayparams=np.asarray({"detectorMode": "TRX"}, dtype=object),
        rawimage=np.arange(16, dtype=np.uint16).reshape(4, 4),
        processedimage=np.full((4, 4), 0.25, dtype=np.float32),
    )


def _write_gain(path: Path) -> None:
    np.savez_compressed(
        path,
        id="gain-trx",
        xrayparams=np.asarray({"detectorMode": "TRX"}, dtype=object),
        darkimage=np.zeros((4, 4), dtype=np.uint16),
        rawimage=np.full((4, 4), 1000, dtype=np.uint16),
    )


def _write_calibration(path: Path) -> None:
    path.mkdir()
    np.savez_compressed(
        path / "remap.npz",
        map_x=np.indices((4, 4), dtype=np.float32)[1],
        map_y=np.indices((4, 4), dtype=np.float32)[0],
    )
    (path / "metadata.json").write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "synthetic-trx",
                "image_shape": [4, 4],
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
    assert second["counts"] == result["counts"]
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
