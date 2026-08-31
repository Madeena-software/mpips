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
    examination = getattr(manifest, "examination", None)
    resolved = hasattr(examination, "performed_at_is_authoritative")
    study_authoritative = (
        getattr(examination, "performed_at_is_authoritative", False)
        if resolved
        else getattr(examination, "performed_at", None) is not None
        or getattr(capture, "captured_at", None) is not None
    )
    study_dt = (
        getattr(examination, "performed_at", None)
        if getattr(examination, "performed_at", None) is not None
        else getattr(capture, "captured_at", None)
    )
    study_time_known = (
        getattr(examination, "examination_time_known", True)
        if resolved
        else getattr(examination, "examination_time_known", None) is not False
    )
    content_authoritative = (
        getattr(capture, "captured_at_is_authoritative", False)
        if resolved
        else getattr(capture, "captured_at", None) is not None
    )
    content_dt = getattr(capture, "captured_at", None)

    study_date = study_dt.strftime("%Y%m%d") if study_authoritative and study_dt else ""
    study_time = (
        study_dt.strftime("%H%M%S")
        if study_authoritative and study_dt and study_time_known
        else ""
    )
    content_date = (
        content_dt.strftime("%Y%m%d") if content_authoritative and content_dt else ""
    )
    content_time = (
        content_dt.strftime("%H%M%S") if content_authoritative and content_dt else ""
    )
    time_str = (
        study_dt.strftime("%y%m%d%H%M%S")
        if study_authoritative and study_dt and study_time_known
        else ""
    )

    image_spacing = getattr(capture, "image_spacing", None)
    if image_spacing is not None:
        scale_x = float(image_spacing.column_um)
        scale_y = float(image_spacing.row_um)
    else:
        scale_x = 140.0
        scale_y = 140.0

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
        "StudyDate": study_date,
        "StudyTime": study_time,
        "ContentDate": content_date,
        "ContentTime": content_time,
        "StudyDescription": study_desc,
        "SeriesDescription": series_desc,
    }
