from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DICOM_UID_PATTERN = re.compile(r"^[0-9](\.[0-9]+)+$")


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
    study_description: str = Field("CHEST RADIOGRAPH", min_length=1, max_length=64)
    protocol_name: Optional[str] = Field(None, max_length=64)

    @field_validator("performed_at")
    @classmethod
    def validate_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and (v.tzinfo is None or v.tzinfo.utcoffset(v) is None):
            raise ValueError("performed_at must include timezone offset")
        return v


class PatientSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: Optional[UUID] = Field(default_factory=uuid4)
    medical_record_number: str = Field("MRN-UNKNOWN", min_length=1, max_length=64)
    name: PersonNameSchema
    sex: Literal["male", "female", "other", "unknown"] = "unknown"
    birth_date: Optional[date] = None

    @field_validator("name", mode="before")
    @classmethod
    def parse_name(cls, v: Union[str, dict, PersonNameSchema]) -> PersonNameSchema | dict:
        if isinstance(v, str):
            return PersonNameSchema(full_name=v)
        return v


class OperatorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: Optional[str] = Field("OP-SYSTEM", max_length=64)
    name: PersonNameSchema = Field(default_factory=lambda: PersonNameSchema(full_name="SYSTEM OPERATOR"))


class SiteSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: Optional[str] = Field("ORG-MADEENA", max_length=64)
    site_id: Optional[str] = Field("SITE-DEFAULT", max_length=64)
    institution_name: str = Field("MADEENA MEDICAL CENTER", min_length=1, max_length=64)
    department_name: Optional[str] = Field(None, max_length=64)
    station_name: Optional[str] = Field(None, max_length=16)
    timezone: str = Field("Asia/Jakarta", min_length=1, max_length=64)


class FileManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Optional[str] = Field(None, max_length=128)
    byte_size: Optional[int] = Field(None, gt=0)
    sha256: Optional[str] = Field(None, max_length=64)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_SHA256_PATTERN.match(v):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return v


class CaptureSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capture_id: Optional[str] = Field(None, max_length=64)
    protocol_version: str = Field("1.0.0", min_length=1, max_length=64)
    detector_type: Optional[str] = Field(None, max_length=16)
    body_part_examined: str = Field("CHEST", min_length=1, max_length=16)
    laterality: Literal["R", "L", "U", "B"] = "U"
    projection: str = Field("PA", min_length=1, max_length=16)
    captured_at: Optional[datetime] = None
    radiograph: Optional[FileManifestSchema] = Field(default_factory=FileManifestSchema)
    gain: Optional[FileManifestSchema] = Field(default_factory=FileManifestSchema)

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
    series_number: int = Field(1, gt=0)
    instance_number: int = Field(1, gt=0)
    series_description: Optional[str] = Field(None, max_length=64)
    presentation_intent: Literal["FOR PRESENTATION"] = "FOR PRESENTATION"

    @field_validator("study_instance_uid", "series_instance_uid", "sop_instance_uid")
    @classmethod
    def validate_dicom_uid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not DICOM_UID_PATTERN.match(v) or len(v) > 64):
            raise ValueError(f"Invalid DICOM UID format or length: {v!r}")
        return v


class MHCSManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["1.0"] = "1.0"
    conversion_job_id: UUID = Field(default_factory=uuid4)
    submission_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)
    examination: ExaminationSchema = Field(default_factory=ExaminationSchema)
    patient: PatientSchema
    operator: Optional[OperatorSchema] = None
    site: SiteSchema = Field(default_factory=SiteSchema)
    capture: CaptureSchema = Field(default_factory=CaptureSchema)
    dicom: DICOMManifestSchema = Field(default_factory=DICOMManifestSchema)
