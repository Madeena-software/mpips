from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pydicom

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.metadata import format_person_name


class DICOMValidationError(ValueError):
    """Raised when DICOM validation checks fail."""


def validate_dicom_dataset(
    dicom_path: str | Path,
    manifest: MHCSManifest,
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

    sop_instance = str(getattr(ds, "SOPInstanceUID", ""))
    if sop_instance != manifest.dicom.sop_instance_uid:
        raise DICOMValidationError(
            f"SOPInstanceUID {sop_instance!r} != {manifest.dicom.sop_instance_uid!r}"
        )

    file_meta_sop_inst = str(getattr(ds.file_meta, "MediaStorageSOPInstanceUID", ""))
    if sop_instance != file_meta_sop_inst:
        raise DICOMValidationError(
            "SOPInstanceUID mismatch with MediaStorageSOPInstanceUID"
        )

    if str(getattr(ds, "StudyInstanceUID", "")) != manifest.dicom.study_instance_uid:
        raise DICOMValidationError("StudyInstanceUID mismatch")

    if str(getattr(ds, "SeriesInstanceUID", "")) != manifest.dicom.series_instance_uid:
        raise DICOMValidationError("SeriesInstanceUID mismatch")

    if str(getattr(ds, "AccessionNumber", "")) != manifest.examination.accession_number:
        raise DICOMValidationError("AccessionNumber mismatch")

    if str(getattr(ds, "StudyID", "")) != manifest.examination.study_id:
        raise DICOMValidationError("StudyID mismatch")

    if str(getattr(ds, "PatientID", "")) != manifest.patient.medical_record_number:
        raise DICOMValidationError("PatientID != medical_record_number")

    expected_patient_pn = format_person_name(manifest.patient.name)
    if str(getattr(ds, "PatientName", "")) != expected_patient_pn:
        raise DICOMValidationError("PatientName mismatch")

    expected_operator_pn = format_person_name(manifest.operator.name)
    if str(getattr(ds, "OperatorsName", "")) != expected_operator_pn:
        raise DICOMValidationError("OperatorsName mismatch")

    if str(getattr(ds, "InstitutionName", "")) != manifest.site.institution_name:
        raise DICOMValidationError("InstitutionName mismatch")

    if str(getattr(ds, "BodyPartExamined", "")) != manifest.capture.body_part_examined:
        raise DICOMValidationError("BodyPartExamined mismatch")

    if str(getattr(ds, "ImageLaterality", "")) != manifest.capture.laterality:
        raise DICOMValidationError("ImageLaterality mismatch")

    if str(getattr(ds, "ViewPosition", "")) != manifest.capture.projection:
        raise DICOMValidationError("ViewPosition mismatch")

    if str(getattr(ds, "PresentationIntentType", "")) != "FOR PRESENTATION":
        raise DICOMValidationError("PresentationIntentType != FOR PRESENTATION")

    if str(getattr(ds, "BurnedInAnnotation", "")) != "NO":
        raise DICOMValidationError("BurnedInAnnotation != NO")

    if str(getattr(ds, "LossyImageCompression", "")) != "00":
        raise DICOMValidationError("LossyImageCompression != 00")

    if getattr(ds, "SamplesPerPixel", 1) == 1 and hasattr(ds, "PlanarConfiguration"):
        raise DICOMValidationError("PlanarConfiguration present on monochrome image")

    expected_row_mm = manifest.capture.image_spacing.row_um / 1000.0
    expected_col_mm = manifest.capture.image_spacing.column_um / 1000.0
    spacing = [float(x) for x in getattr(ds, "PixelSpacing", [0, 0])]
    if (
        len(spacing) != 2
        or abs(spacing[0] - expected_row_mm) > 1e-4
        or abs(spacing[1] - expected_col_mm) > 1e-4
    ):
        raise DICOMValidationError(
            f"PixelSpacing {spacing} != [{expected_row_mm}, {expected_col_mm}]"
        )

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
