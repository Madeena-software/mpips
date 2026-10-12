import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

EXAMPLES = Path("docs/integration/examples")


def test_synthetic_mapping_preserves_identifiers() -> None:
    from scripts.simrs_manifest_example import build_manifest
    from mpips.api.schemas.dicom import MHCSManifest

    response = json.loads((EXAMPLES / "simrs-response.synthetic.json").read_text())
    request = "SYNTHETIC-VISIT-2026-0001"
    data = build_manifest(response, request, {}, "2026-10-12T10:00:00+07:00")
    model = MHCSManifest.model_validate(data)
    assert model.patient.medical_record_number == "SYNTHETIC-001"
    assert model.patient.sex == "unknown"
    assert model.examination is not None
    assert model.examination.encounter_id == request
    assert model.examination.accession_number is None
    assert "tgl_daftar" not in json.dumps(data)
    assert model.capture is not None
    assert model.capture.captured_at is not None


@pytest.mark.parametrize(
    "mutation", ["envelope", "success", "list", "visit", "id", "name", "date", "sex"]
)
def test_bad_hospital_response_rejected(mutation: str) -> None:
    from scripts.simrs_manifest_example import build_manifest

    value = json.loads((EXAMPLES / "simrs-response.synthetic.json").read_text())
    if mutation == "envelope":
        value = []
    elif mutation == "success":
        value["success"] = "true"
    elif mutation == "list":
        value["data"] = [value["data"]]
    elif mutation == "visit":
        value["data"]["no_rawat"] = "ANOTHER-VISIT"
    elif mutation == "id":
        value["data"]["no_rkm_medis"] = " "
    elif mutation == "name":
        value["data"].pop("nm_pasien")
    elif mutation == "date":
        value["data"]["tgl_lahir"] = "2000-02-30"
    else:
        value["data"]["jk"] = "UNCONFIRMED"
    with pytest.raises(ValueError):
        build_manifest(
            value,
            "SYNTHETIC-VISIT-2026-0001",
            {"L": "male"},
            "2026-10-12T10:00:00+07:00",
        )


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("patient", "medical_record_number", ""),
        ("patient", "name", ""),
        ("patient", "birth_date", "2000-02-30"),
        ("examination", "accession_number", "SYNTHETIC-VISIT-2026-0001"),
        ("dicom", "study_instance_uid", "NOT-A-UID"),
        ("capture", "captured_at", "2026-10-12T10:00:00"),
    ],
)
def test_documented_manifest_schema_rejects_bad_fields(
    section: str, field: str, value: str
) -> None:
    from mpips.api.schemas.dicom import MHCSManifest

    data = copy.deepcopy(
        json.loads((EXAMPLES / "grabber-manifest.synthetic.json").read_text())
    )
    data.setdefault(section, {})[field] = value
    with pytest.raises(ValidationError):
        MHCSManifest.model_validate(data)
