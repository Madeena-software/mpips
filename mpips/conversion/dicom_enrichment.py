from __future__ import annotations

from pathlib import Path
import pydicom
from pydicom.uid import UID, generate_uid

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.metadata import format_person_name


def enrich_dicom_file(dicom_path: str | Path, manifest: MHCSManifest) -> None:
    """Enriches and synchronizes DICOM dataset with signed MHCS manifest fields."""
    target_path = Path(dicom_path)
    ds = pydicom.dcmread(str(target_path))

    # Patient details
    ds.PatientName = format_person_name(manifest.patient.name)
    ds.PatientID = manifest.patient.medical_record_number
    if manifest.patient.birth_date:
        ds.PatientBirthDate = manifest.patient.birth_date.strftime("%Y%m%d")

    sex_map = {"male": "M", "female": "F", "other": "O", "unknown": "O"}
    ds.PatientSex = sex_map.get(manifest.patient.sex.lower(), "O")

    # Operator details
    if manifest.operator and manifest.operator.name:
        ds.OperatorsName = format_person_name(manifest.operator.name)
    else:
        ds.OperatorsName = "SYSTEM OPERATOR"

    # Examination & Study
    if manifest.examination.accession_number:
        ds.AccessionNumber = manifest.examination.accession_number
    else:
        ds.AccessionNumber = f"ACC-{manifest.conversion_job_id.hex[:10].upper()}"

    if manifest.examination.study_id:
        ds.StudyID = manifest.examination.study_id

    ds.StudyDescription = manifest.examination.study_description or "CHEST RADIOGRAPH"
    if manifest.examination.protocol_name:
        ds.ProtocolName = manifest.examination.protocol_name

    # Site details
    ds.InstitutionName = manifest.site.institution_name or "MADEENA MEDICAL CENTER"
    if manifest.site.department_name:
        ds.InstitutionalDepartmentName = manifest.site.department_name
    if manifest.site.station_name:
        ds.StationName = manifest.site.station_name[:16]

    # Anatomy & Projection
    ds.BodyPartExamined = manifest.capture.body_part_examined or "CHEST"
    ds.ImageLaterality = manifest.capture.laterality or "U"
    ds.ViewPosition = manifest.capture.projection or "PA"

    # Series & Instance
    ds.SeriesDescription = (
        manifest.dicom.series_description
        or manifest.examination.study_description
        or "CHEST RADIOGRAPH"
    )
    ds.SeriesNumber = manifest.dicom.series_number or 1
    ds.InstanceNumber = manifest.dicom.instance_number or 1
    ds.PresentationIntentType = "FOR PRESENTATION"

    # UIDs & File Meta sync
    study_uid = manifest.dicom.study_instance_uid or generate_uid()
    series_uid = manifest.dicom.series_instance_uid or generate_uid()
    sop_uid = manifest.dicom.sop_instance_uid or generate_uid()

    ds.StudyInstanceUID = UID(study_uid)
    ds.SeriesInstanceUID = UID(series_uid)
    ds.SOPInstanceUID = UID(sop_uid)

    if hasattr(ds, "file_meta") and ds.file_meta:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID

    # Pixel Spacing in row_mm, column_mm order
    if hasattr(manifest.capture, "image_spacing") and getattr(manifest.capture, "image_spacing", None):
        row_mm = manifest.capture.image_spacing.row_um / 1000.0
        col_mm = manifest.capture.image_spacing.column_um / 1000.0
    else:
        row_mm = 0.140
        col_mm = 0.140
    ds.PixelSpacing = [f"{row_mm:.6f}", f"{col_mm:.6f}"]

    # Remove PlanarConfiguration for monochrome images
    if getattr(ds, "SamplesPerPixel", 1) == 1 and hasattr(ds, "PlanarConfiguration"):
        del ds.PlanarConfiguration

    # Non-speculative safety flags
    ds.BurnedInAnnotation = "NO"
    ds.LossyImageCompression = "00"

    # Save enriched DICOM
    try:
        ds.save_as(str(target_path), enforce_file_format=True)
    except TypeError:
        ds.save_as(str(target_path), write_like_original=False)
