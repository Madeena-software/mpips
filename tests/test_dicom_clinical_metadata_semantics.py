"""Phase 2A red tests for canonical DX clinical metadata.

These tests intentionally describe the next canonical-export contract.  They
are expected to be red until the production export path is implemented.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pydicom
import pytest
from pydicom.sequence import Sequence

from mpips.api.schemas.dicom import MHCSManifest, resolve_mhcs_manifest
from mpips.conversion.dicom_enrichment import enrich_dicom_file
from mpips.conversion.metadata import build_converter_metadata_json
from mpips.conversion.validation import DICOMValidationError, validate_dicom_dataset
from mpips.conversion.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.processing.filtering import apply_advanced_median_filter
from mpips.processing.imagej import ImageJReplicator
from mpips.workflows.imager_pipeline.npz_io import write_tiff

KNOWN_STALE_DCIODVFY_ERROR = (
    "Error - Unrecognized enumerated value <FOR PRESENTATION> for value 1 of "
    "attribute <Presentation Intent Type>"
)


def run_dciodvfy(path: Path) -> dict[str, object]:
    binary = shutil.which("dciodvfy")
    if binary is None:
        return {"status": "INDEPENDENT_VALIDATOR_UNAVAILABLE"}
    result = subprocess.run(
        [binary, str(path)], capture_output=True, text=True, check=False
    )
    lines = (result.stdout + result.stderr).splitlines()
    errors = [line for line in lines if line.startswith("Error -")]
    stale = [line for line in errors if line == KNOWN_STALE_DCIODVFY_ERROR]
    current = [line for line in errors if line != KNOWN_STALE_DCIODVFY_ERROR]
    warnings = [line for line in lines if line.startswith("Warning")]
    process_failure = result.returncode < 0
    accepted = (
        not process_failure
        and not current
        and (result.returncode == 0 or (bool(stale) and not current))
    )
    return {
        "status": "PASS" if accepted else "FAIL",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "errors": errors,
        "current_standard_errors": current,
        "warnings": warnings,
        "stale_diagnostic_count": len(stale),
        "unexpected_tool_failure": process_failure,
    }


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


def _convert(
    tmp_path: Path, manifest: MHCSManifest, shape: tuple[int, int] = (4, 4)
) -> pydicom.Dataset:
    image = tmp_path / "image.tiff"
    metadata = tmp_path / "metadata.json"
    dicom = tmp_path / "image.dcm"
    write_tiff(image, np.arange(np.prod(shape), dtype=np.uint16).reshape(shape))
    metadata.write_text(json.dumps(build_converter_metadata_json(manifest)))
    cast(Any, tiff_json_to_dcm)(str(image), str(metadata), str(dicom))
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
    ("sex", "expected"),
    [("male", "M"), ("female", "F"), ("other", "O"), ("unknown", "")],
)
def test_patient_sex_never_fabricates_unknown(
    tmp_path: Path, sex: str, expected: str
) -> None:
    ds = _convert(tmp_path, _manifest(sex=sex))
    assert "PatientSex" in ds
    assert ds.PatientSex == expected


def test_authoritative_xray_parameters_reach_dicom(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "capture": {
                "xrayparams": {
                    "expEnergy": "80",
                    "expCurrent": "50",
                    "expTimeMs": 500.0,
                    "expMas": 25.0,
                }
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert (ds.KVP, ds.XRayTubeCurrent, ds.ExposureTime, ds.Exposure) == (
        80,
        50,
        500,
        25,
    )
    assert "ExposureInuAs" not in ds


def test_xray_parameters_are_absent_without_authority(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest())
    assert not any(
        keyword in ds
        for keyword in (
            "KVP",
            "XRayTubeCurrent",
            "ExposureTime",
            "Exposure",
            "ExposureInuAs",
        )
    )


def test_xray_parameters_reject_inconsistent_mas(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "capture": {
                "xrayparams": {
                    "expEnergy": "80",
                    "expCurrent": "50",
                    "expTimeMs": 500.0,
                    "expMas": 24.0,
                }
            },
        }
    )
    with pytest.raises(ValueError, match="mAs"):
        _convert(tmp_path, manifest)


def test_ambiguous_xray_units_are_rejected() -> None:
    with pytest.raises(ValueError, match="extra_forbidden"):
        MHCSManifest.model_validate(
            {
                **_manifest().model_dump(mode="json"),
                "capture": {"xrayparams": {"expTimeSeconds": 0.5}},
            }
        )


def test_patient_age_is_derived_at_birthday_boundary(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest(birth_date="1958-08-28"))
    assert ds.PatientAge == "068Y"


@pytest.mark.parametrize(
    "keyword",
    [
        "StudyDate",
        "StudyTime",
        "SeriesDate",
        "SeriesTime",
        "AcquisitionDate",
        "AcquisitionTime",
        "AcquisitionDateTime",
        "ContentDate",
        "ContentTime",
    ],
)
def test_date_only_never_leaks_pseudo_temporal_values(
    tmp_path: Path, keyword: str
) -> None:
    manifest = MHCSManifest.model_validate(
        {
            "examination": {
                "performed_at": "2026-08-28T00:00:00+00:00",
                "examination_time_known": False,
            },
            "patient": {
                "medical_record_number": "SYNTHETIC-001",
                "name": "SYNTHETIC",
                "sex": "male",
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert getattr(ds, keyword, "") == ("20260828" if keyword == "StudyDate" else "")


@pytest.mark.parametrize(
    "keyword",
    ["InstitutionName", "BodyPartExamined", "ViewPosition", "ImageLaterality"],
)
def test_unsupported_defaults_are_not_fabricated(tmp_path: Path, keyword: str) -> None:
    ds = _convert(tmp_path, _manifest())
    assert getattr(ds, keyword, "") == ""


@pytest.mark.parametrize(
    "keyword",
    [
        "ReferringPhysicianName",
        "Manufacturer",
        "DetectorType",
        "AcquisitionContextSequence",
        "AnatomicRegionSequence",
        "PositionerType",
    ],
)
def test_unknown_dx_type2_values_are_present_and_empty(
    tmp_path: Path, keyword: str
) -> None:
    ds = _convert(tmp_path, _manifest())
    assert keyword in ds
    assert not ds[keyword].value


@pytest.mark.parametrize(
    "keyword", ["StudyTime", "ReferringPhysicianName", "StudyID", "AccessionNumber"]
)
def test_unknown_general_study_type2_is_present_and_empty(
    tmp_path: Path, keyword: str
) -> None:
    manifest = _manifest().model_copy(update={"examination": None})
    ds = _convert(tmp_path, manifest)
    assert keyword in ds
    assert ds[keyword].value == ""


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


def test_authoritative_spacing_populates_imager_spacing_only(tmp_path: Path) -> None:
    """Future contract: detector-plane spacing is distinct from PixelSpacing."""
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "capture": {
                **_manifest().model_dump(mode="json")["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert ds.ImagerPixelSpacing == ["0.150000", "0.160000"]
    assert "PixelSpacing" not in ds


def test_patient_plane_spacing_has_independent_authority(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "capture": {
                **_manifest().model_dump(mode="json")["capture"],
                "patient_pixel_spacing": {"row_mm": 0.150, "column_mm": 0.160},
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert ds.PixelSpacing == ["0.150000", "0.160000"]
    assert "ImagerPixelSpacing" not in ds


@pytest.mark.parametrize("shape", [(4, 4), (2, 8)])
def test_rows_and_columns_do_not_establish_physical_spacing(
    tmp_path: Path, shape: tuple[int, int]
) -> None:
    manifest = _manifest()
    path = tmp_path / "image.dcm"
    _convert(tmp_path, manifest, shape=shape).save_as(path)
    with pytest.raises(DICOMValidationError, match="physical spacing authority"):
        validate_dicom_dataset(path, manifest, shape)


def test_old_pixel_spacing_fallback_is_not_authority(tmp_path: Path) -> None:
    manifest = _manifest()
    path = tmp_path / "image.dcm"
    ds = _convert(tmp_path, manifest)
    assert "PixelSpacing" not in ds
    ds.save_as(path)
    with pytest.raises(DICOMValidationError, match="physical spacing authority"):
        validate_dicom_dataset(path, manifest, (4, 4))


def test_age_only_contract_is_examination_anchored(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest(birth_date=None).model_dump(mode="json"),
            "examination": {
                "performed_at": "2026-08-28T00:00:00+00:00",
                "patient_age_years": 68,
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert "PatientBirthDate" in ds and ds.PatientBirthDate == ""
    assert ds.PatientAge == "068Y"


def test_resolved_manifest_preserves_authoritative_age() -> None:
    manifest = MHCSManifest.model_validate(
        {
            "examination": {
                "performed_at": "2026-08-28T00:00:00+00:00",
                "patient_age_years": 68,
            },
            "patient": {
                "medical_record_number": "SYNTHETIC-001",
                "name": "SYNTHETIC",
                "sex": "male",
            },
        }
    )
    resolved = resolve_mhcs_manifest("{}", manifest, 1, "a" * 64, 1, "b" * 64)
    assert resolved.examination.patient_age_years == 68


def test_conflicting_authoritative_age_fails_closed() -> None:
    manifest = MHCSManifest.model_validate(
        {
            "examination": {
                "performed_at": "2026-08-28T00:00:00+00:00",
                "patient_age_years": 67,
            },
            "patient": {
                "medical_record_number": "SYNTHETIC-001",
                "name": "SYNTHETIC",
                "sex": "male",
                "birth_date": "1958-08-28",
            },
        }
    )
    with pytest.raises(ValueError, match="age"):
        resolve_mhcs_manifest("{}", manifest, 1, "a" * 64, 1, "b" * 64)


def test_no_authoritative_age_omits_patient_age(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest(birth_date=None))
    assert "PatientBirthDate" in ds and ds.PatientBirthDate == ""
    assert "PatientAge" not in ds


@pytest.mark.parametrize(
    ("examination_date", "expected"),
    [("2026-08-27T00:00:00+00:00", "067Y"), ("2026-08-28T00:00:00+00:00", "068Y")],
)
def test_dob_age_uses_examination_date_boundary(
    tmp_path: Path, examination_date: str, expected: str
) -> None:
    manifest = _manifest(birth_date="1958-08-28")
    assert manifest.examination is not None
    manifest.examination = manifest.examination.model_copy(
        update={"performed_at": datetime.fromisoformat(examination_date)}
    )
    ds = _convert(tmp_path, manifest)
    assert ds.PatientAge == expected


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
    assert (
        hashlib.sha256(ds.PixelData).digest()
        == hashlib.sha256(
            np.arange(16, dtype=np.uint16).reshape(4, 4).tobytes()
        ).digest()
    )


def test_final_presentation_pixels_fail_canonical_semantic_gate(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "dicom": {
                **_manifest().model_dump(mode="json")["dicom"],
                "pixel_source": "FINAL_IMAGE",
            },
        }
    )
    path = tmp_path / "image.dcm"
    fixture = _convert(tmp_path, manifest)
    # dciodvfy requires these conditional/Type-1 values; they are explicit
    # synthetic fixture authority, not production defaults.
    fixture.PatientOrientation = ["P", "F"]
    fixture.ImageLaterality = "R"
    fixture.save_as(path)
    with pytest.raises(
        DICOMValidationError, match="canonical|pixel|presentation|ImageLaterality"
    ):
        validate_dicom_dataset(path, manifest, (4, 4))


def test_canonical_pre_presentation_requires_and_exports_pixel_relationship(
    tmp_path: Path,
) -> None:
    base = _manifest().model_dump(mode="json")
    manifest = MHCSManifest.model_validate(
        {
            **base,
            "capture": {
                **base["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
                "projection": "PA",
                "view_code_sequence": [
                    {
                        "code_value": "272479007",
                        "coding_scheme_designator": "SCT",
                        "code_meaning": "postero-anterior",
                    }
                ],
            },
            "dicom": {
                **base["dicom"],
                "pixel_source": "CANONICAL_PRE_PRESENTATION",
                "pixel_intensity_relationship": "LIN",
                "pixel_intensity_relationship_sign": 1,
            },
        }
    )
    path = tmp_path / "image.dcm"
    _convert(tmp_path, manifest).save_as(path)
    ds = pydicom.dcmread(path)
    assert ds.PixelIntensityRelationship == "LIN"
    assert ds.PixelIntensityRelationshipSign == 1
    validate_dicom_dataset(path, manifest, (4, 4))


def test_canonical_pre_presentation_missing_relationship_fails_closed(
    tmp_path: Path,
) -> None:
    base = _manifest().model_dump(mode="json")
    manifest = MHCSManifest.model_validate(
        {
            **base,
            "capture": {
                **base["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
                "projection": "PA",
                "view_code_sequence": [
                    {
                        "code_value": "272479007",
                        "coding_scheme_designator": "SCT",
                        "code_meaning": "postero-anterior",
                    }
                ],
            },
            "dicom": {
                **base["dicom"],
                "pixel_source": "CANONICAL_PRE_PRESENTATION",
            },
        }
    )
    path = tmp_path / "image.dcm"
    _convert(tmp_path, manifest).save_as(path)
    with pytest.raises(DICOMValidationError, match="relationship|sign"):
        validate_dicom_dataset(path, manifest, (4, 4))


def test_patient_orientation_is_not_guessed(tmp_path: Path) -> None:
    base = _manifest().model_dump(mode="json")
    manifest = MHCSManifest.model_validate(
        {
            **base,
            "capture": {
                **base["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
            },
            "dicom": {
                **base["dicom"],
                "pixel_source": "CANONICAL_PRE_PRESENTATION",
                "pixel_intensity_relationship": "LIN",
                "pixel_intensity_relationship_sign": 1,
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert "PatientOrientation" not in ds
    assert "ViewCodeSequence" not in ds
    path = tmp_path / "image.dcm"
    ds.save_as(path)
    with pytest.raises(DICOMValidationError, match="orientation|ViewCodeSequence"):
        validate_dicom_dataset(path, manifest, (4, 4))


def test_canonical_projection_without_orientation_authority_fails(
    tmp_path: Path,
) -> None:
    base = _manifest().model_dump(mode="json")
    manifest = MHCSManifest.model_validate(
        {
            **base,
            "capture": {
                **base["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
                "projection": "PA",
            },
            "dicom": {
                **base["dicom"],
                "pixel_source": "CANONICAL_PRE_PRESENTATION",
                "pixel_intensity_relationship": "LIN",
                "pixel_intensity_relationship_sign": 1,
            },
        }
    )
    path = tmp_path / "image.dcm"
    _convert(tmp_path, manifest).save_as(path)
    with pytest.raises(DICOMValidationError, match="orientation|ViewCodeSequence"):
        validate_dicom_dataset(path, manifest, (4, 4))


@pytest.mark.parametrize("pixel_source", [None, "FINAL_IMAGE"])
def test_noncanonical_pixel_source_fails_canonical_dx_gate(
    tmp_path: Path, pixel_source: str | None
) -> None:
    base = _manifest().model_dump(mode="json")
    manifest = MHCSManifest.model_validate(
        {
            **base,
            "capture": {
                **base["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
                "view_code_sequence": [
                    {
                        "code_value": "272479007",
                        "coding_scheme_designator": "SCT",
                        "code_meaning": "postero-anterior",
                    }
                ],
            },
            "dicom": {**base["dicom"], "pixel_source": pixel_source},
        }
    )
    path = tmp_path / "image.dcm"
    _convert(tmp_path, manifest).save_as(path)
    with pytest.raises(DICOMValidationError, match="pixel|canonical|presentation"):
        validate_dicom_dataset(path, manifest, (4, 4))


def test_verified_pa_view_code_future_contract(tmp_path: Path) -> None:
    manifest = MHCSManifest.model_validate(
        {
            **_manifest().model_dump(mode="json"),
            "capture": {
                **_manifest().model_dump(mode="json")["capture"],
                "projection": "PA",
                "view_code_sequence": [
                    {
                        "code_value": "272479007",
                        "coding_scheme_designator": "SCT",
                        "code_meaning": "postero-anterior",
                    }
                ],
            },
        }
    )
    ds = _convert(tmp_path, manifest)
    assert ds.ViewPosition == "PA"
    assert len(ds.ViewCodeSequence) == 1
    assert ds.ViewCodeSequence[0].CodeValue == "272479007"
    assert ds.ViewCodeSequence[0].CodingSchemeDesignator == "SCT"
    assert ds.ViewCodeSequence[0].CodeMeaning == "postero-anterior"
    assert "PatientOrientation" not in ds


def test_explicit_authoritative_pa_is_allowed(tmp_path: Path) -> None:
    manifest = _manifest()
    assert manifest.capture is not None
    manifest.capture = manifest.capture.model_copy(update={"projection": "PA"})
    assert _convert(tmp_path, manifest).ViewPosition == "PA"


def test_imagej_contrast_is_input_distribution_dependent() -> None:
    first = np.arange(256, dtype=np.uint16).reshape(16, 16) * 257
    second = np.concatenate([np.zeros((8, 16), dtype=np.uint16), first[:8]], axis=0)
    out_first = ImageJReplicator.enhance_contrast(first, equalize=True, normalize=True)
    out_second = ImageJReplicator.enhance_contrast(
        second, equalize=True, normalize=True
    )
    assert out_first[4, 4] != out_second[4, 4]


def test_clahe_is_local_and_context_dependent() -> None:
    first = np.full((64, 64), 1000, dtype=np.uint16)
    first[32, 32] = 2000
    second = first.copy()
    second[:32, :32] = 60000
    out_first = ImageJReplicator.apply_clahe(
        first, blocksize=15, histogram_bins=256, max_slope=0.6, fast=False
    )
    out_second = ImageJReplicator.apply_clahe(
        second, blocksize=15, histogram_bins=256, max_slope=0.6, fast=False
    )
    assert np.any(out_first != out_second)


def test_active_median_depends_on_neighborhood() -> None:
    image = np.full((7, 7), 1000, dtype=np.uint16)
    image[3, 3] = 60000
    result = cast(Any, apply_advanced_median_filter)(image, "standard", 1)
    assert result[3, 3] != image[3, 3]


def test_uint16_quantization_is_many_to_one() -> None:
    values = (np.array([0.0, 0.000001], dtype=np.float32) * 65535).astype(np.uint16)
    assert len(np.unique(values)) == 1


def test_single_frame_dx_has_no_secondary_capture_pollution(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest())
    assert "SecondaryCaptureDeviceManufacturer" not in ds
    assert "NumberOfFrames" not in ds


def test_dciodvfy_fixture_helper_is_skippable(tmp_path: Path) -> None:
    result = run_dciodvfy(tmp_path / "missing.dcm")
    if result["status"] == "INDEPENDENT_VALIDATOR_UNAVAILABLE":
        pytest.skip("dciodvfy unavailable")
    base = _manifest().model_dump(mode="json")
    manifest = MHCSManifest.model_validate(
        {
            **base,
            "capture": {
                **base["capture"],
                "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
                "projection": "PA",
                "view_code_sequence": [
                    {
                        "code_value": "272479007",
                        "coding_scheme_designator": "SCT",
                        "code_meaning": "postero-anterior",
                    }
                ],
            },
            "dicom": {
                **base["dicom"],
                "pixel_source": "CANONICAL_PRE_PRESENTATION",
                "pixel_intensity_relationship": "LIN",
                "pixel_intensity_relationship_sign": 1,
            },
        }
    )
    path = tmp_path / "image.dcm"
    fixture = _convert(tmp_path, manifest)
    # Explicit synthetic fixture authority for dciodvfy conditional checks.
    fixture.PatientOrientation = ["P", "F"]
    fixture.ImageLaterality = "R"
    anatomic_region = pydicom.Dataset()
    anatomic_region.CodeValue = "51185008"
    anatomic_region.CodingSchemeDesignator = "SCT"
    anatomic_region.CodeMeaning = "Thorax"
    fixture.AnatomicRegionSequence = Sequence([anatomic_region])
    fixture.save_as(path)
    result = run_dciodvfy(path)
    assert result["status"] == "PASS", result
    assert result["current_standard_errors"] == []
