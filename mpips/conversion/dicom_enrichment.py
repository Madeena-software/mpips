from __future__ import annotations

from pathlib import Path
import pydicom
from pydicom.uid import UID, generate_uid

from mpips.api.schemas.dicom import MHCSManifest, ResolvedMHCSManifest
from mpips.conversion.metadata import build_converter_metadata_json, format_person_name


def enrich_dicom_file(
    dicom_path: str | Path, manifest: MHCSManifest | ResolvedMHCSManifest
) -> None:
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

    dicom = getattr(manifest, "dicom", None)
    examination = getattr(manifest, "examination", None)
    site = getattr(manifest, "site", None)
    capture = getattr(manifest, "capture", None)

    temporal = build_converter_metadata_json(manifest)
    ds.StudyDate = temporal["StudyDate"]
    ds.StudyTime = temporal["StudyTime"]
    ds.ContentDate = temporal["ContentDate"]
    ds.ContentTime = temporal["ContentTime"]

    # Examination & Study
    accession_number = (
        getattr(examination, "accession_number", None) if examination else None
    )
    if accession_number:
        ds.AccessionNumber = accession_number
    else:
        job_id = getattr(manifest, "conversion_job_id", None)
        job_hex = str(getattr(job_id, "hex", job_id or ""))
        ds.AccessionNumber = f"ACC-{job_hex[:10].upper()}"

    study_id = getattr(examination, "study_id", None) if examination else None
    if study_id:
        ds.StudyID = study_id

    study_desc = (
        getattr(examination, "study_description", None) if examination else None
    ) or "CHEST RADIOGRAPH"
    ds.StudyDescription = study_desc

    protocol_name = getattr(examination, "protocol_name", None) if examination else None
    if protocol_name:
        ds.ProtocolName = protocol_name

    # Site details
    institution_name = getattr(site, "institution_name", None) if site else None
    ds.InstitutionName = institution_name or "MADEENA MEDICAL CENTER"

    dept_name = getattr(site, "department_name", None) if site else None
    if dept_name:
        ds.InstitutionalDepartmentName = dept_name

    station_name = getattr(site, "station_name", None) if site else None
    if station_name:
        ds.StationName = station_name[:16]

    # Anatomy & Projection
    body_part = getattr(capture, "body_part_examined", None) if capture else None
    laterality = getattr(capture, "laterality", None) if capture else None
    projection = getattr(capture, "projection", None) if capture else None

    ds.BodyPartExamined = body_part or "CHEST"
    ds.ImageLaterality = laterality or "U"
    ds.ViewPosition = projection or "PA"

    # Series & Instance
    series_desc = (
        getattr(dicom, "series_description", None) if dicom else None
    ) or study_desc
    series_number = getattr(dicom, "series_number", None) if dicom else None
    instance_number = getattr(dicom, "instance_number", None) if dicom else None

    ds.SeriesDescription = series_desc
    ds.SeriesNumber = series_number or 1
    ds.InstanceNumber = instance_number or 1
    ds.PresentationIntentType = "FOR PRESENTATION"

    # UIDs & File Meta sync
    study_uid = (
        getattr(dicom, "study_instance_uid", None) if dicom else None
    ) or generate_uid()
    series_uid = (
        getattr(dicom, "series_instance_uid", None) if dicom else None
    ) or generate_uid()
    sop_uid = (
        getattr(dicom, "sop_instance_uid", None) if dicom else None
    ) or generate_uid()

    ds.StudyInstanceUID = UID(study_uid)
    ds.SeriesInstanceUID = UID(series_uid)
    ds.SOPInstanceUID = UID(sop_uid)

    if hasattr(ds, "file_meta") and ds.file_meta:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID

    # Pixel Spacing in row_mm, column_mm order
    image_spacing = getattr(capture, "image_spacing", None) if capture else None
    if image_spacing is not None:
        row_mm = image_spacing.row_um / 1000.0
        col_mm = image_spacing.column_um / 1000.0
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
