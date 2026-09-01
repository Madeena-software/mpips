from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pydicom
import pytest

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.dicom_enrichment import enrich_dicom_file
from mpips.conversion.metadata import build_converter_metadata_json
from mpips.conversion.validation import DICOMValidationError, validate_dicom_dataset
from mpips.engine.imager_pipeline.tiff_json_to_dcm import tiff_json_to_dcm
from mpips.workflows.imager_pipeline.emergency_batch import _build_case
from mpips.workflows.imager_pipeline.npz_io import write_tiff


def _manifest(
    *,
    performed_at: str,
    captured_at: str | None = None,
    conversion_job_id: str | None = None,
    examination_time_known: bool = True,
) -> MHCSManifest:
    return MHCSManifest.model_validate(
        {
            "conversion_job_id": conversion_job_id,
            "examination": {
                "performed_at": performed_at,
                "examination_time_known": examination_time_known,
            },
            "patient": {
                "medical_record_number": "SYNTHETIC-001",
                "name": "SYNTHETIC PATIENT",
            },
            "capture": {"captured_at": captured_at},
        }
    )


def _convert(tmp_path: Path, manifest: MHCSManifest) -> pydicom.Dataset:
    tmp_path.mkdir(parents=True, exist_ok=True)
    tiff_path = tmp_path / "image.tiff"
    json_path = tmp_path / "metadata.json"
    dcm_path = tmp_path / f"{manifest.patient.medical_record_number}.dcm"
    write_tiff(tiff_path, np.arange(16, dtype=np.uint16).reshape(4, 4))
    json_path.write_text(json.dumps(build_converter_metadata_json(manifest)))
    cast(Any, tiff_json_to_dcm)(str(tiff_path), str(json_path), str(dcm_path))
    enrich_dicom_file(dcm_path, manifest)
    return pydicom.dcmread(dcm_path)


def test_authoritative_date_and_time_populate_study_tags(tmp_path: Path) -> None:
    ds = _convert(tmp_path, _manifest(performed_at="2026-08-28T09:17:23+07:00"))

    assert ds.StudyDate == "20260828"
    assert ds.StudyTime == "091723"


def test_date_only_does_not_claim_midnight_as_study_time(tmp_path: Path) -> None:
    ds = _convert(
        tmp_path,
        _manifest(
            performed_at="2026-08-28T00:00:00+07:00",
            examination_time_known=False,
        ),
    )

    assert ds.StudyDate == "20260828"
    assert ds.StudyTime == ""


def test_capture_time_populates_content_tags_without_mirroring_study(
    tmp_path: Path,
) -> None:
    ds = _convert(
        tmp_path,
        _manifest(
            performed_at="2026-08-28T09:17:23+07:00",
            captured_at="2026-08-28T09:18:01+07:00",
        ),
    )

    assert (ds.StudyDate, ds.StudyTime) == ("20260828", "091723")
    assert (ds.ContentDate, ds.ContentTime) == ("20260828", "091801")


def test_job_identifier_does_not_change_authoritative_study_date(
    tmp_path: Path,
) -> None:
    first = _convert(
        tmp_path / "first",
        _manifest(
            performed_at="2026-08-28T09:17:23+07:00",
            conversion_job_id="00000000-0000-0000-0000-000000000001",
        ),
    )
    second = _convert(
        tmp_path / "second",
        _manifest(
            performed_at="2026-08-28T09:17:23+07:00",
            conversion_job_id="00000000-0000-0000-0000-000000000002",
        ),
    )

    assert first.StudyDate == second.StudyDate == "20260828"


def test_emergency_date_only_input_is_marked_without_time_precision(
    tmp_path: Path,
) -> None:
    source = tmp_path / "TRX_123.npz"
    source.write_bytes(b"synthetic")

    _, manifest, _ = _build_case(
        {
            "source": source.name,
            "patient_name": "SYNTHETIC",
            "performed_at": "2026-08-28",
        },
        tmp_path,
        1,
    )

    assert manifest.examination is not None
    assert manifest.examination.performed_at is not None
    assert manifest.examination.performed_at.date().isoformat() == "2026-08-28"
    assert manifest.examination.examination_time_known is False


def test_temporal_metadata_does_not_change_pixel_data(tmp_path: Path) -> None:
    first = _convert(
        tmp_path / "first",
        _manifest(performed_at="2026-08-28T09:17:23+07:00"),
    )
    second = _convert(
        tmp_path / "second",
        _manifest(performed_at="2026-08-29T10:20:30+07:00"),
    )

    assert first.PixelData == second.PixelData


def test_validator_rejects_inconsistent_authoritative_study_date(
    tmp_path: Path,
) -> None:
    manifest = _manifest(performed_at="2026-08-28T09:17:23+07:00")
    ds = _convert(tmp_path, manifest)
    ds.StudyDate = "20260829"
    dcm_path = tmp_path / "SYNTHETIC-001.dcm"
    ds.save_as(dcm_path)

    with pytest.raises(DICOMValidationError, match="StudyDate"):
        validate_dicom_dataset(dcm_path, manifest, (4, 4))
