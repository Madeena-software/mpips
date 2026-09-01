from __future__ import annotations

from pathlib import Path
import pydicom
from pydicom.sequence import Sequence
from pydicom.uid import UID, generate_uid

from mpips.api.schemas.dicom import MHCSManifest, ResolvedMHCSManifest, age_at
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
    ds.PatientBirthDate = (
        manifest.patient.birth_date.strftime("%Y%m%d")
        if manifest.patient.birth_date
        else ""
    )

    sex_map = {"male": "M", "female": "F", "other": "O", "unknown": ""}
    ds.PatientSex = sex_map[manifest.patient.sex.lower()]

    # Operator details
    if manifest.operator and manifest.operator.name:
        ds.OperatorsName = format_person_name(manifest.operator.name)
    else:
        ds.OperatorsName = "SYSTEM OPERATOR"

    dicom = getattr(manifest, "dicom", None)
    examination = getattr(manifest, "examination", None)
    site = getattr(manifest, "site", None)
    capture = getattr(manifest, "capture", None)

    if (
        examination
        and manifest.patient.birth_date is not None
        and examination.patient_age_years is not None
        and examination.performed_at is not None
        and age_at(manifest.patient.birth_date, examination.performed_at.date())
        != examination.patient_age_years
    ):
        raise ValueError("patient age conflicts with birth date and examination date")

    temporal = build_converter_metadata_json(manifest)
    ds.StudyDate = temporal["StudyDate"]
    ds.StudyTime = temporal["StudyTime"]
    ds.ContentDate = temporal["ContentDate"]
    ds.ContentTime = temporal["ContentTime"]

    for keyword in (
        "KVP",
        "ExposureTime",
        "XRayTubeCurrent",
        "Exposure",
        "ExposureInuAs",
    ):
        if keyword in ds:
            del ds[keyword]
        if keyword in temporal:
            setattr(ds, keyword, temporal[keyword])

    # Examination & Study
    accession_number = (
        getattr(examination, "accession_number", None) if examination else None
    )
    ds.AccessionNumber = accession_number or ""

    study_id = getattr(examination, "study_id", None) if examination else None
    if study_id:
        ds.StudyID = study_id

    study_desc = (
        getattr(examination, "study_description", None) if examination else None
    )
    ds.StudyDescription = study_desc or ""

    protocol_name = getattr(examination, "protocol_name", None) if examination else None
    if protocol_name:
        ds.ProtocolName = protocol_name

    # Site details
    institution_name = getattr(site, "institution_name", None) if site else None
    ds.InstitutionName = institution_name or ""

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

    ds.BodyPartExamined = body_part or ""
    ds.ImageLaterality = laterality or ""
    ds.ViewPosition = projection or ""
    if getattr(capture, "view_code_sequence", None):
        items = []
        for item in capture.view_code_sequence:
            code = pydicom.Dataset()
            code.CodeValue = item.code_value
            code.CodingSchemeDesignator = item.coding_scheme_designator
            code.CodeMeaning = item.code_meaning
            items.append(code)
        ds.ViewCodeSequence = Sequence(items)

    # Series & Instance
    series_desc = (
        (getattr(dicom, "series_description", None) if dicom else None)
        or study_desc
        or ""
    )
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
    detector_spacing = getattr(capture, "detector_spacing", None) if capture else None
    patient_spacing = (
        getattr(capture, "patient_pixel_spacing", None) if capture else None
    )
    for keyword in ("ImagerPixelSpacing", "PixelSpacing"):
        if hasattr(ds, keyword):
            del ds[keyword]
    if detector_spacing:
        ds.ImagerPixelSpacing = [
            f"{detector_spacing.row_mm:.6f}",
            f"{detector_spacing.column_mm:.6f}",
        ]
    if patient_spacing:
        ds.PixelSpacing = [
            f"{patient_spacing.row_mm:.6f}",
            f"{patient_spacing.column_mm:.6f}",
        ]

    ds.ImageType = ["DERIVED", "PRIMARY", ""]
    ds.RescaleIntercept = "0"
    ds.RescaleSlope = "1"
    ds.RescaleType = "US"
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PresentationLUTShape = "IDENTITY"
    relationship = (
        getattr(dicom, "pixel_intensity_relationship", None) if dicom else None
    )
    relationship_sign = (
        getattr(dicom, "pixel_intensity_relationship_sign", None) if dicom else None
    )
    if relationship is not None:
        ds.PixelIntensityRelationship = relationship
    if relationship_sign is not None:
        ds.PixelIntensityRelationshipSign = relationship_sign
    for keyword, value in {
        "ReferringPhysicianName": "",
        "Manufacturer": "",
        "DetectorType": "",
        "PositionerType": "",
        "StudyID": study_id or "",
        "StudyTime": ds.StudyTime or "",
    }.items():
        setattr(ds, keyword, value)
    ds.AcquisitionContextSequence = Sequence([])
    ds.AnatomicRegionSequence = Sequence([])
    if hasattr(ds, "SecondaryCaptureDeviceManufacturer"):
        del ds.SecondaryCaptureDeviceManufacturer
    if hasattr(ds, "NumberOfFrames"):
        del ds.NumberOfFrames

    exam_date = getattr(examination, "performed_at", None) if examination else None
    if manifest.patient.birth_date and exam_date:
        years = age_at(manifest.patient.birth_date, exam_date.date())
        ds.PatientAge = f"{years:03d}Y"
    elif examination and getattr(examination, "patient_age_years", None) is not None:
        ds.PatientAge = f"{examination.patient_age_years:03d}Y"
    elif hasattr(ds, "PatientAge"):
        del ds.PatientAge

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
