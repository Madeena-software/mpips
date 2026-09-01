from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DICOM_UID_PATTERN = re.compile(r"^[0-9](\.[0-9]+)+$")
MPIPS_STABLE_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class PersonNameSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=1, max_length=128)
    family_name: Optional[str] = Field(None, max_length=128)


class ExaminationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    examination_id: Optional[str] = Field(None, max_length=64)
    booking_id: Optional[str] = Field(None, max_length=64)
    service_request_id: Optional[str] = Field(None, max_length=64)
    encounter_id: Optional[str] = Field(None, max_length=64)
    accession_number: Optional[str] = Field(None, max_length=16)
    study_id: Optional[str] = Field(None, max_length=16)
    performed_at: Optional[datetime] = None
    examination_time_known: Optional[bool] = None
    study_description: Optional[str] = Field(None, min_length=1, max_length=64)
    protocol_name: Optional[str] = Field(None, max_length=64)
    patient_age_years: Optional[int] = Field(None, ge=0, le=999)

    @field_validator("performed_at")
    @classmethod
    def validate_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and (v.tzinfo is None or v.tzinfo.utcoffset(v) is None):
            raise ValueError("performed_at must include timezone offset")
        return v


class PatientSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: Optional[UUID] = None
    medical_record_number: str = Field(..., min_length=1, max_length=64)
    name: PersonNameSchema
    sex: Literal["male", "female", "other", "unknown"] = "unknown"
    birth_date: Optional[date] = None

    @field_validator("name", mode="before")
    @classmethod
    def parse_name(
        cls, v: Union[str, Dict[str, Any], PersonNameSchema]
    ) -> PersonNameSchema | Dict[str, Any]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                raise ValueError("patient name cannot be empty")
            return PersonNameSchema(full_name=v_str)
        return v


class OperatorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: Optional[str] = Field(None, max_length=64)
    name: Optional[PersonNameSchema] = None

    @field_validator("name", mode="before")
    @classmethod
    def parse_operator_name(
        cls, v: Union[str, Dict[str, Any], PersonNameSchema, None]
    ) -> Optional[PersonNameSchema | Dict[str, Any]]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return None
            return PersonNameSchema(full_name=v_str)
        return v


class SiteSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: Optional[str] = Field(None, max_length=64)
    site_id: Optional[str] = Field(None, max_length=64)
    institution_name: Optional[str] = Field(None, max_length=64)
    department_name: Optional[str] = Field(None, max_length=64)
    station_name: Optional[str] = Field(None, max_length=16)
    timezone: Optional[str] = Field(None, max_length=64)


class ImageSpacingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_um: float = Field(..., gt=0.0)
    column_um: float = Field(..., gt=0.0)


class PixelSpacingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_mm: float = Field(..., gt=0.0)
    column_mm: float = Field(..., gt=0.0)


class ViewCodeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_value: str = Field(..., min_length=1, max_length=16)
    coding_scheme_designator: str = Field(..., min_length=1, max_length=16)
    code_meaning: str = Field(..., min_length=1, max_length=64)


class FileManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Optional[str] = Field(None, max_length=128)
    byte_size: Optional[int] = Field(None, gt=0)
    sha256: Optional[str] = Field(None, max_length=64)
    gain_id: Optional[str] = Field(None, max_length=64)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_SHA256_PATTERN.match(v):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return v


class CaptureSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capture_id: Optional[str] = Field(None, max_length=64)
    protocol_version: Optional[str] = Field(None, max_length=64)
    detector_type: Optional[Literal["BED", "THORAX", "TRX"]] = None
    body_part_examined: Optional[str] = Field(None, min_length=1, max_length=16)
    laterality: Optional[Literal["R", "L", "U", "B"]] = None
    projection: Optional[str] = Field(None, min_length=1, max_length=16)
    captured_at: Optional[datetime] = None
    radiograph: Optional[FileManifestSchema] = Field(default_factory=FileManifestSchema)
    gain: Optional[FileManifestSchema] = Field(default_factory=FileManifestSchema)
    image_spacing: Optional[ImageSpacingSchema] = None
    detector_spacing: Optional[PixelSpacingSchema] = None
    patient_pixel_spacing: Optional[PixelSpacingSchema] = None
    view_code_sequence: Optional[list[ViewCodeSchema]] = None

    @field_validator("captured_at")
    @classmethod
    def validate_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and (v.tzinfo is None or v.tzinfo.utcoffset(v) is None):
            raise ValueError("captured_at must include timezone offset")
        return v


class DICOMManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_instance_uid: Optional[str] = Field(None, max_length=64)
    series_instance_uid: Optional[str] = Field(None, max_length=64)
    sop_instance_uid: Optional[str] = Field(None, max_length=64)
    series_number: Optional[int] = Field(None, gt=0)
    instance_number: Optional[int] = Field(None, gt=0)
    series_description: Optional[str] = Field(None, max_length=64)
    presentation_intent: Literal["FOR PRESENTATION"] = "FOR PRESENTATION"
    pixel_source: Optional[Literal["CANONICAL_PRE_PRESENTATION", "FINAL_IMAGE"]] = None
    pixel_intensity_relationship: Optional[Literal["LIN", "LOG"]] = None
    pixel_intensity_relationship_sign: Optional[Literal[-1, 1]] = None

    @field_validator("study_instance_uid", "series_instance_uid", "sop_instance_uid")
    @classmethod
    def validate_dicom_uid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not DICOM_UID_PATTERN.match(v) or len(v) > 64):
            raise ValueError(f"Invalid DICOM UID format or length: {v!r}")
        return v


class MHCSManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["1.0"] = "1.0"
    conversion_job_id: Optional[UUID] = None
    submission_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    examination: Optional[ExaminationSchema] = Field(default_factory=ExaminationSchema)
    patient: PatientSchema
    operator: Optional[OperatorSchema] = None
    site: Optional[SiteSchema] = Field(default_factory=SiteSchema)
    capture: Optional[CaptureSchema] = Field(default_factory=CaptureSchema)
    dicom: Optional[DICOMManifestSchema] = Field(default_factory=DICOMManifestSchema)


# Fully Resolved Models (Materialized Boundary)


class ResolvedFileManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., min_length=1, max_length=128)
    byte_size: int = Field(..., gt=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    gain_id: Optional[str] = Field(None, max_length=64)


class ResolvedExaminationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    examination_id: str = Field(..., min_length=1, max_length=64)
    booking_id: Optional[str] = Field(None, max_length=64)
    service_request_id: Optional[str] = Field(None, max_length=64)
    encounter_id: Optional[str] = Field(None, max_length=64)
    accession_number: Optional[str] = Field(None, max_length=16)
    study_id: Optional[str] = Field(None, max_length=16)
    performed_at: datetime
    performed_at_is_authoritative: bool
    examination_time_known: bool
    study_description: Optional[str] = Field(None, min_length=1, max_length=64)
    protocol_name: Optional[str] = Field(None, max_length=64)
    patient_age_years: Optional[int] = Field(None, ge=0, le=999)


class ResolvedPatientSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: Optional[UUID] = None
    medical_record_number: str = Field(..., min_length=1, max_length=64)
    name: PersonNameSchema
    sex: Literal["male", "female", "other", "unknown"]
    birth_date: Optional[date] = None


class ResolvedOperatorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(..., min_length=1, max_length=64)
    name: PersonNameSchema


class ResolvedSiteSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str = Field(..., min_length=1, max_length=64)
    site_id: str = Field(..., min_length=1, max_length=64)
    institution_name: Optional[str] = Field(None, max_length=64)
    department_name: Optional[str] = Field(None, max_length=64)
    station_name: Optional[str] = Field(None, max_length=16)
    timezone: str = Field(..., min_length=1, max_length=64)


class ResolvedCaptureSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capture_id: str = Field(..., min_length=1, max_length=64)
    protocol_version: str = Field(..., min_length=1, max_length=64)
    detector_type: Optional[Literal["BED", "THORAX", "TRX"]] = None
    body_part_examined: Optional[str] = Field(None, min_length=1, max_length=16)
    laterality: Optional[Literal["R", "L", "U", "B"]]
    projection: Optional[str] = Field(None, min_length=1, max_length=16)
    captured_at: datetime
    captured_at_is_authoritative: bool
    radiograph: ResolvedFileManifestSchema
    gain: ResolvedFileManifestSchema
    image_spacing: Optional[ImageSpacingSchema] = None
    detector_spacing: Optional[PixelSpacingSchema] = None
    patient_pixel_spacing: Optional[PixelSpacingSchema] = None
    view_code_sequence: Optional[list[ViewCodeSchema]] = None


class ResolvedDICOMManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_instance_uid: str = Field(..., min_length=1, max_length=64)
    series_instance_uid: str = Field(..., min_length=1, max_length=64)
    sop_instance_uid: str = Field(..., min_length=1, max_length=64)
    series_number: int = Field(..., gt=0)
    instance_number: int = Field(..., gt=0)
    series_description: Optional[str] = Field(None, max_length=64)
    presentation_intent: Literal["FOR PRESENTATION"]
    pixel_source: Optional[Literal["CANONICAL_PRE_PRESENTATION", "FINAL_IMAGE"]]
    pixel_intensity_relationship: Optional[Literal["LIN", "LOG"]]
    pixel_intensity_relationship_sign: Optional[Literal[-1, 1]]


class ResolvedMHCSManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["1.0"] = "1.0"
    conversion_job_id: UUID
    submission_id: UUID
    correlation_id: UUID
    examination: ResolvedExaminationSchema
    patient: ResolvedPatientSchema
    operator: ResolvedOperatorSchema
    site: ResolvedSiteSchema
    capture: ResolvedCaptureSchema
    dicom: ResolvedDICOMManifestSchema


def age_at(birth_date: date, examination_date: date) -> int:
    years = examination_date.year - birth_date.year
    if (examination_date.month, examination_date.day) < (
        birth_date.month,
        birth_date.day,
    ):
        years -= 1
    return years


def resolve_mhcs_manifest(
    raw_manifest_text: str,
    input_manifest: MHCSManifest,
    rad_bytes_len: int,
    rad_sha256_hex: str,
    gain_bytes_len: int,
    gain_sha256_hex: str,
) -> ResolvedMHCSManifest:
    """Materializes external client MHCSManifest into internal ResolvedMHCSManifest."""
    rad_sha256 = rad_sha256_hex.lower()
    gain_sha256 = gain_sha256_hex.lower()

    capture_in = input_manifest.capture or CaptureSchema()
    rad_in = capture_in.radiograph or FileManifestSchema()
    gain_in = capture_in.gain or FileManifestSchema()

    # 1. File Integrity Verification & Materialization
    if rad_in.byte_size is not None and rad_in.byte_size != rad_bytes_len:
        raise ValueError("NPZ_VALIDATION_ERROR: Radiograph byte size mismatch")
    if rad_in.sha256 is not None and rad_in.sha256.lower() != rad_sha256:
        raise ValueError("NPZ_VALIDATION_ERROR: Radiograph SHA-256 hash mismatch")

    if gain_in.byte_size is not None and gain_in.byte_size != gain_bytes_len:
        raise ValueError("NPZ_VALIDATION_ERROR: Gain byte size mismatch")
    if gain_in.sha256 is not None and gain_in.sha256.lower() != gain_sha256:
        raise ValueError("NPZ_VALIDATION_ERROR: Gain SHA-256 hash mismatch")

    resolved_rad = ResolvedFileManifestSchema(
        filename=rad_in.filename or "radiograph.npz",
        byte_size=rad_bytes_len,
        sha256=rad_sha256,
        gain_id=rad_in.gain_id,
    )
    resolved_gain = ResolvedFileManifestSchema(
        filename=gain_in.filename or "gain.npz",
        byte_size=gain_bytes_len,
        sha256=gain_sha256,
        gain_id=gain_in.gain_id,
    )

    # 2. Deterministic conversion_job_id
    if input_manifest.conversion_job_id is not None:
        conversion_job_id = input_manifest.conversion_job_id
    else:
        try:
            raw_dict = json.loads(raw_manifest_text)
        except Exception:
            raw_dict = input_manifest.model_dump(mode="json", exclude_none=True)
        canonical_input = json.dumps(raw_dict, sort_keys=True, separators=(",", ":"))
        hasher = hashlib.sha256()
        hasher.update(canonical_input.encode("utf-8"))
        hasher.update(rad_sha256.encode("utf-8"))
        hasher.update(gain_sha256.encode("utf-8"))
        request_digest = hasher.hexdigest()
        conversion_job_id = uuid.uuid5(
            MPIPS_STABLE_NAMESPACE, f"mpips:conversion:{request_digest}"
        )

    # 3. Deterministic submission_id & correlation_id
    submission_id = input_manifest.submission_id or uuid.uuid5(
        MPIPS_STABLE_NAMESPACE, f"mpips:submission:{conversion_job_id}"
    )
    correlation_id = input_manifest.correlation_id or uuid.uuid5(
        MPIPS_STABLE_NAMESPACE, f"mpips:correlation:{conversion_job_id}"
    )

    # 4. Deterministic Capture ID
    capture_id = capture_in.capture_id or f"CAP-{conversion_job_id.hex[:12].upper()}"

    # 5. Deterministic DICOM UIDs
    dicom_in = input_manifest.dicom or DICOMManifestSchema()
    if dicom_in.study_instance_uid:
        study_uid = dicom_in.study_instance_uid
    else:
        u = uuid.uuid5(MPIPS_STABLE_NAMESPACE, f"mpips:study:{conversion_job_id}")
        study_uid = f"2.25.{u.int}"

    if dicom_in.series_instance_uid:
        series_uid = dicom_in.series_instance_uid
    else:
        u = uuid.uuid5(MPIPS_STABLE_NAMESPACE, f"mpips:series:{conversion_job_id}")
        series_uid = f"2.25.{u.int}"

    if dicom_in.sop_instance_uid:
        sop_uid = dicom_in.sop_instance_uid
    else:
        u = uuid.uuid5(MPIPS_STABLE_NAMESPACE, f"mpips:sop:{conversion_job_id}")
        sop_uid = f"2.25.{u.int}"

    # 6. Accession Number & Timestamps
    exam_in = input_manifest.examination or ExaminationSchema()
    if (
        input_manifest.patient.birth_date is not None
        and exam_in.patient_age_years is not None
        and exam_in.performed_at is not None
        and age_at(input_manifest.patient.birth_date, exam_in.performed_at.date())
        != exam_in.patient_age_years
    ):
        raise ValueError("patient age conflicts with birth date and examination date")
    accession_number = exam_in.accession_number or ""
    capture_is_authoritative = capture_in.captured_at is not None
    examination_is_authoritative = exam_in.performed_at is not None
    if capture_is_authoritative:
        captured_at = capture_in.captured_at
    else:
        # Deterministic fallback timestamp derived from conversion_job_id
        ts_offset = conversion_job_id.int % (365 * 86400)
        captured_at = datetime.fromtimestamp(1770000000 + ts_offset, tz=timezone.utc)
    performed_at = exam_in.performed_at or captured_at
    examination_time_known = (
        exam_in.examination_time_known
        if exam_in.examination_time_known is not None
        else examination_is_authoritative or capture_is_authoritative
    )

    # 7. Construct Resolved Sub-models
    resolved_exam = ResolvedExaminationSchema(
        examination_id=exam_in.examination_id
        or f"EXAM-{conversion_job_id.hex[:8].upper()}",
        booking_id=exam_in.booking_id,
        service_request_id=exam_in.service_request_id,
        encounter_id=exam_in.encounter_id,
        accession_number=accession_number,
        study_id=exam_in.study_id or "",
        performed_at=performed_at,
        performed_at_is_authoritative=(
            examination_is_authoritative or capture_is_authoritative
        ),
        examination_time_known=examination_time_known,
        study_description=exam_in.study_description,
        protocol_name=exam_in.protocol_name,
        patient_age_years=exam_in.patient_age_years,
    )

    pat_in = input_manifest.patient
    resolved_patient = ResolvedPatientSchema(
        member_id=pat_in.member_id,
        medical_record_number=pat_in.medical_record_number,
        name=pat_in.name,
        sex=pat_in.sex,
        birth_date=pat_in.birth_date,
    )

    op_in = input_manifest.operator
    if op_in and op_in.name:
        resolved_operator = ResolvedOperatorSchema(
            operator_id=op_in.operator_id or "OP-SYSTEM",
            name=op_in.name,
        )
    else:
        resolved_operator = ResolvedOperatorSchema(
            operator_id="OP-SYSTEM",
            name=PersonNameSchema(full_name="SYSTEM OPERATOR"),
        )

    site_in = input_manifest.site or SiteSchema()
    resolved_site = ResolvedSiteSchema(
        organization_id=site_in.organization_id or "ORG-MADEENA",
        site_id=site_in.site_id or "SITE-DEFAULT",
        institution_name=site_in.institution_name or "",
        department_name=site_in.department_name,
        station_name=site_in.station_name,
        timezone=site_in.timezone or "Asia/Jakarta",
    )

    resolved_capture = ResolvedCaptureSchema(
        capture_id=capture_id,
        protocol_version=capture_in.protocol_version or "1.0.0",
        detector_type=capture_in.detector_type,
        body_part_examined=capture_in.body_part_examined,
        laterality=capture_in.laterality,
        projection=capture_in.projection,
        captured_at=captured_at,
        captured_at_is_authoritative=capture_is_authoritative,
        radiograph=resolved_rad,
        gain=resolved_gain,
        image_spacing=capture_in.image_spacing,
        detector_spacing=capture_in.detector_spacing,
        patient_pixel_spacing=capture_in.patient_pixel_spacing,
        view_code_sequence=capture_in.view_code_sequence,
    )

    resolved_dicom = ResolvedDICOMManifestSchema(
        study_instance_uid=study_uid,
        series_instance_uid=series_uid,
        sop_instance_uid=sop_uid,
        series_number=dicom_in.series_number or 1,
        instance_number=dicom_in.instance_number or 1,
        series_description=dicom_in.series_description
        or exam_in.study_description
        or "",
        presentation_intent="FOR PRESENTATION",
        pixel_source=dicom_in.pixel_source,
        pixel_intensity_relationship=dicom_in.pixel_intensity_relationship,
        pixel_intensity_relationship_sign=dicom_in.pixel_intensity_relationship_sign,
    )

    return ResolvedMHCSManifest(
        manifest_version="1.0",
        conversion_job_id=conversion_job_id,
        submission_id=submission_id,
        correlation_id=correlation_id,
        examination=resolved_exam,
        patient=resolved_patient,
        operator=resolved_operator,
        site=resolved_site,
        capture=resolved_capture,
        dicom=resolved_dicom,
    )
