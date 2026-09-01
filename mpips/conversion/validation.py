from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pydicom

from mpips.api.schemas.dicom import MHCSManifest, ResolvedMHCSManifest
from mpips.conversion.metadata import format_person_name


class DICOMValidationError(ValueError):
    """Raised when DICOM validation checks fail."""


def validate_dicom_dataset(
    dicom_path: str | Path,
    manifest: MHCSManifest | ResolvedMHCSManifest,
    expected_shape: Tuple[int, int],
) -> Dict[str, Any]:
    """Validates generated DICOM dataset against specifications and signed manifest."""
    target_path = Path(dicom_path)
    try:
        ds = pydicom.dcmread(str(target_path))
    except Exception as exc:
        raise DICOMValidationError(f"Could not parse DICOM file: {exc}") from exc

    if not hasattr(ds, "file_meta") or ds.file_meta is None:
        raise DICOMValidationError("DICOM file meta header is missing")

    sop_class = str(getattr(ds, "SOPClassUID", ""))
    if sop_class != "1.2.840.10008.5.1.4.1.1.1.1.1":
        raise DICOMValidationError(
            f"Expected SOPClassUID '1.2.840.10008.5.1.4.1.1.1.1.1', got {sop_class!r}"
        )

    file_meta_sop_class = str(getattr(ds.file_meta, "MediaStorageSOPClassUID", ""))
    if sop_class != file_meta_sop_class:
        raise DICOMValidationError(
            f"SOPClassUID mismatch with MediaStorageSOPClassUID: {sop_class!r}"
        )

    dicom = getattr(manifest, "dicom", None)
    examination = getattr(manifest, "examination", None)
    site = getattr(manifest, "site", None)
    capture = getattr(manifest, "capture", None)
    operator = getattr(manifest, "operator", None)

    sop_instance = str(getattr(ds, "SOPInstanceUID", ""))
    sop_instance_uid = getattr(dicom, "sop_instance_uid", None) if dicom else None
    if sop_instance_uid and sop_instance != sop_instance_uid:
        raise DICOMValidationError(
            f"SOPInstanceUID {sop_instance!r} != {sop_instance_uid!r}"
        )
    elif not sop_instance:
        raise DICOMValidationError("SOPInstanceUID is missing")

    file_meta_sop_inst = str(getattr(ds.file_meta, "MediaStorageSOPInstanceUID", ""))
    if sop_instance != file_meta_sop_inst:
        raise DICOMValidationError(
            "SOPInstanceUID mismatch with MediaStorageSOPInstanceUID"
        )

    study_instance_uid = getattr(dicom, "study_instance_uid", None) if dicom else None
    if (
        study_instance_uid
        and str(getattr(ds, "StudyInstanceUID", "")) != study_instance_uid
    ):
        raise DICOMValidationError("StudyInstanceUID mismatch")

    series_instance_uid = getattr(dicom, "series_instance_uid", None) if dicom else None
    if (
        series_instance_uid
        and str(getattr(ds, "SeriesInstanceUID", "")) != series_instance_uid
    ):
        raise DICOMValidationError("SeriesInstanceUID mismatch")

    resolved = hasattr(examination, "performed_at_is_authoritative")
    study_authoritative = (
        getattr(examination, "performed_at_is_authoritative", False)
        if resolved
        else getattr(examination, "performed_at", None) is not None
        or getattr(capture, "captured_at", None) is not None
    )
    study_dt = (
        getattr(examination, "performed_at", None)
        if getattr(examination, "performed_at", None) is not None
        else getattr(capture, "captured_at", None)
    )
    study_time_known = (
        getattr(examination, "examination_time_known", True)
        if resolved
        else getattr(examination, "examination_time_known", None) is not False
    )
    content_authoritative = (
        getattr(capture, "captured_at_is_authoritative", False)
        if resolved
        else getattr(capture, "captured_at", None) is not None
    )
    content_dt = getattr(capture, "captured_at", None)
    expected_temporal = {
        "StudyDate": (
            study_dt.strftime("%Y%m%d") if study_authoritative and study_dt else ""
        ),
        "StudyTime": (
            study_dt.strftime("%H%M%S")
            if study_authoritative and study_dt and study_time_known
            else ""
        ),
        "ContentDate": (
            content_dt.strftime("%Y%m%d")
            if content_authoritative and content_dt
            else ""
        ),
        "ContentTime": (
            content_dt.strftime("%H%M%S")
            if content_authoritative and content_dt
            else ""
        ),
    }
    for keyword, expected in expected_temporal.items():
        if str(getattr(ds, keyword, "")) != expected:
            raise DICOMValidationError(f"{keyword} does not match authoritative source")

    accession_number = (
        getattr(examination, "accession_number", None) if examination else None
    )
    if accession_number and str(getattr(ds, "AccessionNumber", "")) != accession_number:
        raise DICOMValidationError("AccessionNumber mismatch")

    study_id = getattr(examination, "study_id", None) if examination else None
    if study_id and str(getattr(ds, "StudyID", "")) != study_id:
        raise DICOMValidationError("StudyID mismatch")

    if str(getattr(ds, "PatientID", "")) != manifest.patient.medical_record_number:
        raise DICOMValidationError("PatientID != medical_record_number")

    expected_patient_pn = format_person_name(manifest.patient.name)
    if str(getattr(ds, "PatientName", "")) != expected_patient_pn:
        raise DICOMValidationError("PatientName mismatch")

    if operator and getattr(operator, "name", None):
        expected_operator_pn = format_person_name(operator.name)
        if str(getattr(ds, "OperatorsName", "")) != expected_operator_pn:
            raise DICOMValidationError("OperatorsName mismatch")

    institution_name = getattr(site, "institution_name", None) if site else None
    if institution_name and str(getattr(ds, "InstitutionName", "")) != institution_name:
        raise DICOMValidationError("InstitutionName mismatch")

    body_part_examined = (
        getattr(capture, "body_part_examined", None) if capture else None
    )
    if (
        body_part_examined
        and str(getattr(ds, "BodyPartExamined", "")) != body_part_examined
    ):
        raise DICOMValidationError("BodyPartExamined mismatch")

    laterality = getattr(capture, "laterality", None) if capture else None
    if laterality and str(getattr(ds, "ImageLaterality", "")) != laterality:
        raise DICOMValidationError("ImageLaterality mismatch")

    projection = getattr(capture, "projection", None) if capture else None
    if projection and str(getattr(ds, "ViewPosition", "")) != projection:
        raise DICOMValidationError("ViewPosition mismatch")

    pixel_source = getattr(dicom, "pixel_source", None) if dicom else None
    legacy_emergency = getattr(capture, "detector_type", None) == "TRX"
    relationship = getattr(dicom, "pixel_intensity_relationship", None) if dicom else None
    relationship_sign = getattr(dicom, "pixel_intensity_relationship_sign", None) if dicom else None
    if pixel_source == "FINAL_IMAGE":
        raise DICOMValidationError("FINAL_IMAGE is not canonical presentation pixels")
    if pixel_source == "CANONICAL_PRE_PRESENTATION":
        if relationship not in ("LIN", "LOG") or relationship_sign not in (-1, 1):
            raise DICOMValidationError("canonical pixel relationship/sign is required")
        if str(getattr(ds, "PixelIntensityRelationship", "")) != relationship:
            raise DICOMValidationError("PixelIntensityRelationship mismatch")
        if int(getattr(ds, "PixelIntensityRelationshipSign", 0)) != relationship_sign:
            raise DICOMValidationError("PixelIntensityRelationshipSign mismatch")
        if not getattr(capture, "detector_spacing", None):
            raise DICOMValidationError("canonical physical spacing authority is missing")
        if not getattr(capture, "projection", None) and not getattr(capture, "view_code_sequence", None):
            raise DICOMValidationError("canonical orientation/ViewCodeSequence authority is missing")
    if getattr(capture, "view_code_sequence", None):
        if "ViewCodeSequence" not in ds or not ds.ViewCodeSequence:
            raise DICOMValidationError("ViewCodeSequence is missing")
        item = ds.ViewCodeSequence[0]
        expected = capture.view_code_sequence[0]
        if (str(item.CodeValue), str(item.CodingSchemeDesignator), str(item.CodeMeaning)) != (
            expected.code_value, expected.coding_scheme_designator, expected.code_meaning
        ):
            raise DICOMValidationError("ViewCodeSequence mismatch")

    if str(getattr(ds, "PresentationIntentType", "")) != "FOR PRESENTATION":
        raise DICOMValidationError("PresentationIntentType != FOR PRESENTATION")

    if str(getattr(ds, "BurnedInAnnotation", "")) != "NO":
        raise DICOMValidationError("BurnedInAnnotation != NO")

    if str(getattr(ds, "LossyImageCompression", "")) != "00":
        raise DICOMValidationError("LossyImageCompression != 00")

    if getattr(ds, "SamplesPerPixel", 1) == 1 and hasattr(ds, "PlanarConfiguration"):
        raise DICOMValidationError("PlanarConfiguration present on monochrome image")

    detector_spacing = getattr(capture, "detector_spacing", None) if capture else None
    patient_spacing = getattr(capture, "patient_pixel_spacing", None) if capture else None
    if not detector_spacing and ((not resolved and not legacy_emergency) or pixel_source == "CANONICAL_PRE_PRESENTATION"):
        raise DICOMValidationError("canonical physical spacing authority is missing")
    if pixel_source == "CANONICAL_PRE_PRESENTATION" and detector_spacing:
        spacing = [float(x) for x in getattr(ds, "ImagerPixelSpacing", [0, 0])]
        expected = [detector_spacing.row_mm, detector_spacing.column_mm]
        if len(spacing) != 2 or any(abs(a - b) > 1e-4 for a, b in zip(spacing, expected)):
            raise DICOMValidationError("ImagerPixelSpacing does not match detector authority")
    if patient_spacing:
        spacing = [float(x) for x in getattr(ds, "PixelSpacing", [0, 0])]
        expected = [patient_spacing.row_mm, patient_spacing.column_mm]
        if len(spacing) != 2 or any(abs(a - b) > 1e-4 for a, b in zip(spacing, expected)):
            raise DICOMValidationError("PixelSpacing does not match patient-plane authority")
    elif "PixelSpacing" in ds and pixel_source == "CANONICAL_PRE_PRESENTATION":
        raise DICOMValidationError("PixelSpacing has no patient-plane authority")
    if (
        ((not resolved and not legacy_emergency) or pixel_source == "CANONICAL_PRE_PRESENTATION")
        and not getattr(capture, "projection", None)
        and not getattr(capture, "view_code_sequence", None)
        and "PatientOrientation" not in ds
    ):
        raise DICOMValidationError("canonical orientation/ViewCodeSequence authority is missing")

    rows = int(getattr(ds, "Rows", 0))
    cols = int(getattr(ds, "Columns", 0))
    if (rows, cols) != expected_shape:
        raise DICOMValidationError(
            f"DICOM Rows/Columns ({rows}, {cols}) != expected {expected_shape}"
        )

    try:
        pixel_array = ds.pixel_array
    except Exception as exc:
        raise DICOMValidationError(f"Could not decode pixel_array: {exc}") from exc

    if pixel_array.ndim != 2 or pixel_array.shape != expected_shape:
        raise DICOMValidationError(
            f"pixel_array shape {pixel_array.shape} != expected {expected_shape}"
        )

    if pixel_array.dtype != np.uint16:
        raise DICOMValidationError(f"pixel_array dtype {pixel_array.dtype} != uint16")

    # Audit for embedded local file paths in string element values
    for elem in ds:
        if elem.VR in ("LO", "LT", "PN", "SH", "ST", "UT") and elem.value:
            val_str = str(elem.value)
            if "/tmp/" in val_str or "/var/" in val_str or "\\tmp\\" in val_str:
                raise DICOMValidationError(
                    f"Local file path detected in DICOM tag {elem.tag}: {val_str!r}"
                )

    return {
        "valid": True,
        "rows": rows,
        "columns": cols,
        "pixel_bytes": len(ds.PixelData),
    }
