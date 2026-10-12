"""Synthetic reference mapping only; the separate Grabber owns the HTTP client."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from mpips.api.schemas.dicom import MHCSManifest


def build_manifest(
    response: object,
    requested_visit: str,
    confirmed_sex_codes: dict[str, str],
    captured_at: str,
) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("success") is not True:
        raise ValueError("SIMRS response rejected")
    data = response.get("data")
    if not isinstance(data, dict):
        raise ValueError("SIMRS patient object required")
    for field in ("no_rawat", "no_rkm_medis", "nm_pasien", "tgl_lahir"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError("SIMRS identity fields required")
    if data["no_rawat"] != requested_visit or not requested_visit.strip():
        raise ValueError("SIMRS visit does not match request")
    birth = data["tgl_lahir"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth):
        raise ValueError("Confirmed ISO birth date format required")
    try:
        birth_date = date.fromisoformat(birth)
        capture_time = datetime.fromisoformat(captured_at)
    except (ValueError, TypeError):
        raise ValueError("Invalid clinical dates") from None
    if capture_time.tzinfo is None or birth_date > capture_time.date():
        raise ValueError("Invalid clinical dates")
    sex = "unknown"
    if confirmed_sex_codes:
        code = data.get("jk")
        if not isinstance(code, str):
            raise ValueError("Hospital sex code must be a string")
        sex = confirmed_sex_codes.get(code, "")
        if sex not in ("male", "female", "other", "unknown"):
            raise ValueError("Unrecognized hospital sex code")
    try:
        manifest = MHCSManifest.model_validate(
            {
                "patient": {
                    "medical_record_number": data["no_rkm_medis"].strip(),
                    "name": data["nm_pasien"].strip(),
                    "sex": sex,
                    "birth_date": birth,
                },
                "examination": {"encounter_id": requested_visit},
                "capture": {"captured_at": captured_at},
            }
        )
    except ValueError:
        raise ValueError("SIMRS identity schema rejected") from None
    return manifest.model_dump(mode="json", exclude_none=True)
