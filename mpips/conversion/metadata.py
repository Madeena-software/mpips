from __future__ import annotations

from typing import Any, Dict

from mpips.api.schemas.dicom import MHCSManifest, PersonNameSchema, ResolvedMHCSManifest


def format_person_name(name_input: PersonNameSchema | Dict[str, Any] | Any) -> str:
    """Formats person name into standard DICOM PN or unchanged full_name.

    Rules:
    - If family_name is None or empty, return full_name.
    - If full_name ends with exact suffix family_name, return
      family_name^remaining_name.
    - Otherwise, return full_name unchanged.
    """
    if isinstance(name_input, PersonNameSchema):
        full_name = name_input.full_name
        family_name = name_input.family_name
    elif isinstance(name_input, dict):
        full_name = str(name_input.get("full_name", ""))
        family_name = name_input.get("family_name")
    else:
        full_name = getattr(name_input, "full_name", str(name_input))
        family_name = getattr(name_input, "family_name", None)

    full_name = (full_name or "").strip()
    if family_name is not None:
        family_name = str(family_name).strip()

    if not family_name:
        return full_name

    if full_name.endswith(family_name):
        remaining = full_name[: -len(family_name)].strip()
        if remaining:
            return f"{family_name}^{remaining}"

    return full_name


def build_converter_metadata_json(
    manifest: MHCSManifest | ResolvedMHCSManifest,
) -> Dict[str, Any]:
    """Builds Pak Andre's approved converter metadata JSON dictionary."""
    patient_pn = format_person_name(manifest.patient.name)
    birthdate_str = (
        manifest.patient.birth_date.strftime("%Y%m%d")
        if manifest.patient.birth_date
        else ""
    )

    capture = getattr(manifest, "capture", None)
    if capture and capture.captured_at:
        time_str = capture.captured_at.strftime("%y%m%d%H%M%S")
    else:
        from datetime import datetime, timezone

        time_str = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")

    image_spacing = getattr(capture, "image_spacing", None)
    if image_spacing is not None:
        scale_x = float(image_spacing.column_um)
        scale_y = float(image_spacing.row_um)
    else:
        scale_x = 140.0
        scale_y = 140.0

    examination = getattr(manifest, "examination", None)
    dicom = getattr(manifest, "dicom", None)
    study_desc = (
        getattr(examination, "study_description", None) if examination else None
    ) or "CHEST RADIOGRAPH"
    series_desc = (
        getattr(dicom, "series_description", None) if dicom else None
    ) or study_desc

    return {
        "Patient Name": patient_pn,
        "NIK": manifest.patient.medical_record_number,
        "Gender": manifest.patient.sex,
        "Birthdate": birthdate_str,
        "Scale X": scale_x,
        "Scale Y": scale_y,
        "Time": time_str,
        "StudyDescription": study_desc,
        "SeriesDescription": series_desc,
    }
