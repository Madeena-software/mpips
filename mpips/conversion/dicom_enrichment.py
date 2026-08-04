from __future__ import annotations

from pathlib import Path
import pydicom
from pydicom.uid import UID

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.metadata import format_person_name


def enrich_dicom_file(dicom_path: str | Path, manifest: MHCSManifest) -> None:
    """Enriches and synchronizes DICOM dataset with signed MHCS manifest fields."""
    target_path = Path(dicom_path)
    ds = pydicom.dcmread(str(target_path))

    # Patient details
    ds.PatientName = format_person_name(manifest.patient.name)
    ds.PatientID = manifest.patient.medical_record_number
    ds.PatientBirthDate = manifest.patient.birth_date.strftime("%Y%m%d")

    sex_map = {"male": "M", "female": "F", "other": "O", "unknown": "O"}
    ds.PatientSex = sex_map.get(manifest.patient.sex.lower(), "O")

    # Operator details
    ds.OperatorsName = format_person_name(manifest.operator.name)

    # Examination & Study
    ds.AccessionNumber = manifest.examination.accession_number
    ds.StudyID = manifest.examination.study_id
    ds.StudyDescription = manifest.examination.study_description
    ds.ProtocolName = manifest.examination.protocol_name

    # Site details
    ds.InstitutionName = manifest.site.institution_name
    if manifest.site.department_name:
        ds.InstitutionalDepartmentName = manifest.site.department_name
    if manifest.site.station_name:
        ds.StationName = manifest.site.station_name

    # Anatomy & Projection
    ds.BodyPartExamined = manifest.capture.body_part_examined
    ds.ImageLaterality = manifest.capture.laterality
    ds.ViewPosition = manifest.capture.projection

    # Series & Instance
    ds.SeriesDescription = manifest.dicom.series_description
    ds.SeriesNumber = manifest.dicom.series_number
    ds.InstanceNumber = manifest.dicom.instance_number
    ds.PresentationIntentType = "FOR PRESENTATION"

    # UIDs & File Meta sync
    ds.StudyInstanceUID = UID(manifest.dicom.study_instance_uid)
    ds.SeriesInstanceUID = UID(manifest.dicom.series_instance_uid)
    ds.SOPInstanceUID = UID(manifest.dicom.sop_instance_uid)

    if hasattr(ds, "file_meta") and ds.file_meta:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID

    # Pixel Spacing in row_mm, column_mm order
    row_mm = manifest.capture.image_spacing.row_um / 1000.0
    col_mm = manifest.capture.image_spacing.column_um / 1000.0
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
