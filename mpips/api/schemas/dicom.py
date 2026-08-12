from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DICOM_UID_PATTERN = re.compile(r"^[0-9](\.[0-9]+)+$")


class PersonNameSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=1, max_length=128)
    family_name: Optional[str] = Field(None, max_length=128)


class ExaminationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    examination_id: str = Field(..., min_length=1, max_length=64)
    booking_id: str = Field(..., min_length=1, max_length=64)
    service_request_id: str = Field(..., min_length=1, max_length=64)
    encounter_id: str = Field(..., min_length=1, max_length=64)
    accession_number: str = Field(..., min_length=1, max_length=16)
    study_id: str = Field(..., min_length=1, max_length=16)
    performed_at: datetime
    study_description: str = Field(..., min_length=1, max_length=64)
    protocol_name: str = Field(..., min_length=1, max_length=64)

    @field_validator("performed_at")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("performed_at must include timezone offset")
        return v


class PatientSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: UUID
    medical_record_number: str = Field(..., min_length=1, max_length=64)
    name: PersonNameSchema
    sex: Literal["male", "female", "other", "unknown"]
    birth_date: date


class OperatorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(..., min_length=1, max_length=64)
    name: PersonNameSchema


class SiteSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str = Field(..., min_length=1, max_length=64)
    site_id: str = Field(..., min_length=1, max_length=64)
    institution_name: str = Field(..., min_length=1, max_length=64)
    department_name: Optional[str] = Field(None, max_length=64)
    station_name: Optional[str] = Field(None, max_length=16)
    timezone: str = Field(..., min_length=1, max_length=64)


class FileManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., min_length=1, max_length=128)
    byte_size: int = Field(..., gt=0)
    sha256: str = Field(..., min_length=64, max_length=64)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not HEX_SHA256_PATTERN.match(v):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return v


class GainManifestSchema(FileManifestSchema):
    gain_id: str = Field(..., min_length=1, max_length=64)


class ImageSpacingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_um: float = Field(..., gt=0.0)
    column_um: float = Field(..., gt=0.0)


class CaptureSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capture_id: str = Field(..., min_length=1, max_length=64)
    protocol_version: str = Field(..., min_length=1, max_length=64)
    body_part_examined: str = Field(..., min_length=1, max_length=16)
    laterality: Literal["R", "L", "U", "B"]
    projection: str = Field(..., min_length=1, max_length=16)
    captured_at: datetime
    radiograph: FileManifestSchema
    gain: GainManifestSchema
    image_spacing: ImageSpacingSchema

    @field_validator("captured_at")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("captured_at must include timezone offset")
        return v


class DICOMManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_instance_uid: str = Field(..., min_length=1, max_length=64)
    series_instance_uid: str = Field(..., min_length=1, max_length=64)
    sop_instance_uid: str = Field(..., min_length=1, max_length=64)
    series_number: int = Field(..., gt=0)
    instance_number: int = Field(..., gt=0)
    series_description: str = Field(..., min_length=1, max_length=64)
    presentation_intent: Literal["FOR PRESENTATION"]

    @field_validator("study_instance_uid", "series_instance_uid", "sop_instance_uid")
    @classmethod
    def validate_dicom_uid(cls, v: str) -> str:
        if not DICOM_UID_PATTERN.match(v) or len(v) > 64:
            raise ValueError(f"Invalid DICOM UID format or length: {v!r}")
        return v


class MHCSManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["1.0"]
    conversion_job_id: UUID
    submission_id: UUID
    correlation_id: UUID
    examination: ExaminationSchema
    patient: PatientSchema
    operator: OperatorSchema
    site: SiteSchema
    capture: CaptureSchema
    dicom: DICOMManifestSchema
