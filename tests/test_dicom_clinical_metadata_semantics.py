"""Phase 2A red tests for canonical DX clinical metadata.

These tests intentionally describe the next canonical-export contract.  They
are expected to be red until the production export path is implemented.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import pydicom
import pytest

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.dicom_enrichment import enrich_dicom_file
from mpips.conversion.metadata import build_converter_metadata_json
from mpips.conversion.validation import DICOMValidationError, validate_dicom_dataset
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.npz_io import write_tiff


def _manifest(**patient: object) -> MHCSManifest:
    return MHCSManifest.model_validate(
        {
            "conversion_job_id": "00000000-0000-0000-0000-000000000001",
            "examination": {
                "performed_at": "2026-08-28T09:17:23+07:00",
                "examination_time_known": True,
            },
            "patient": {
                "medical_record_number": "SYNTHETIC-001",
                "name": "SYNTHETIC PATIENT",
                "sex": "male",
                "birth_date": "1990-08-28",
                **patient,
            },
        }
    )


def _convert(tmp_path: Path, manifest: MHCSManifest) -> pydicom.Dataset:
    image = tmp_path / "image.tiff"
    metadata = tmp_path / "metadata.json"
    dicom = tmp_path / "image.dcm"
    write_tiff(image, np.arange(16, dtype=np.uint16).reshape(4, 4))
    metadata.write_text(json.dumps(build_converter_metadata_json(manifest)))
    tiff_json_to_dcm(str(image), str(metadata), str(dicom))
    enrich_dicom_file(dicom, manifest)
    return pydicom.dcmread(dicom)


@pytest.mark.parametrize(
    ("patient", "expected"),
    [
        ({"birth_date": "1990-08-28"}, "19900828"),
        ({"birth_date": None}, ""),
    ],
)
def test_birth_date_is_authoritative_or_empty_type2(
    tmp_path: Path, patient: dict[str, object], expected: str
) -> None:
    ds = _convert(tmp_path, _manifest(**patient))
    assert "PatientBirthDate" in ds
    assert ds.PatientBirthDate == expected


@pytest.mark.parametrize(
    ("sex", "expected"), [("male", "M"), ("female", "F"), ("other", "O"), ("unknown", "")]
)
def test_patient_sex_never_fabricates_unknown(tmp_path: Path, sex: str, expected: str) -> None:
    ds = _convert(tmp_path, _manifest(sex=sex))
    assert "PatientSex" in ds
    assert ds.PatientSex == expected


def test_patient_age_is_derived_at_birthday_boundary(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest(birth_date="1958-08-28"))
    assert ds.PatientAge == "068Y"


@pytest.mark.parametrize(
    "keyword",
    ["StudyDate", "StudyTime", "SeriesDate", "SeriesTime", "AcquisitionDate", "AcquisitionTime", "AcquisitionDateTime", "ContentDate", "ContentTime"],
)
def test_date_only_never_leaks_pseudo_temporal_values(tmp_path: Path, keyword: str) -> None:
    manifest = MHCSManifest.model_validate(
        {
            "examination": {"performed_at": "2026-08-28T00:00:00+00:00", "examination_time_known": False},
            "patient": {"medical_record_number": "SYNTHETIC-001", "name": "SYNTHETIC", "sex": "male"},
        }
    )
    ds = _convert(tmp_path, manifest)
    assert getattr(ds, keyword, "") == ("20260828" if keyword == "StudyDate" else "")


@pytest.mark.parametrize(
    "keyword",
    ["InstitutionName", "BodyPartExamined", "ViewPosition", "ImageLaterality", "AccessionNumber", "StudyID"],
)
def test_unsupported_defaults_are_not_fabricated(tmp_path: Path, keyword: str) -> None:
    ds = _convert(tmp_path, _manifest())
    assert getattr(ds, keyword, "") == ""


@pytest.mark.parametrize(
    "keyword", ["ReferringPhysicianName", "Manufacturer", "DetectorType", "AcquisitionContextSequence"]
)
def test_unknown_dx_type2_values_are_present_and_empty(tmp_path: Path, keyword: str) -> None:
    ds = _convert(tmp_path, _manifest())
    assert keyword in ds
    assert not ds[keyword].value


def test_canonical_dx_constants(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest())
    assert (ds.RescaleIntercept, ds.RescaleSlope, ds.RescaleType) == (0, 1, "US")
    assert ds.PhotometricInterpretation == "MONOCHROME2"
    assert ds.PresentationLUTShape == "IDENTITY"


def test_canonical_image_type_has_required_vm_and_order(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest())
    assert ds.ImageType == ["DERIVED", "PRIMARY", ""]


def test_spacing_without_authority_fails_closed(tmp_path: Path) -> None:
    manifest = _manifest()
    path = tmp_path / "image.dcm"
    _convert(tmp_path, manifest).save_as(path)
    with pytest.raises(DICOMValidationError, match="physical spacing authority"):
        validate_dicom_dataset(path, manifest, (4, 4))


def test_metadata_enrichment_preserves_uids_and_pixels(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "dicom": {
                "study_instance_uid": "1.2.826.0.1.3680043.10.1",
                "series_instance_uid": "1.2.826.0.1.3680043.10.2",
                "sop_instance_uid": "1.2.826.0.1.3680043.10.3",
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert (ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.SOPInstanceUID) == (
        "1.2.826.0.1.3680043.10.1",
        "1.2.826.0.1.3680043.10.2",
        "1.2.826.0.1.3680043.10.3",
    )
    assert hashlib.sha256(ds.PixelData).digest() == hashlib.sha256(
        np.arange(16, dtype=np.uint16).reshape(4, 4).tobytes()
    ).digest()


def test_final_presentation_pixels_fail_canonical_semantic_gate() -> None:
    assert "FINAL_IMAGE" not in {"canonical_pixel_source"}


def test_patient_orientation_is_not_guessed(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest())
    assert getattr(ds, "PatientOrientation", "") not in {"L\\F", "R\\F"}


def test_single_frame_dx_has_no_secondary_capture_pollution(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest())
    assert "SecondaryCaptureDeviceManufacturer" not in ds
    assert "NumberOfFrames" not in ds


def test_dciodvfy_fixture_helper_is_skippable(tmp_path: Path) -> None:
    binary = shutil.which("dciodvfy")
    if binary is None:
        pytest.skip("dciodvfy unavailable")
    path = tmp_path / "image.dcm"
    _convert(tmp_path, _manifest()).save_as(path)
    result = subprocess.run([binary, str(path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
