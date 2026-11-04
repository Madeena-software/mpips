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


def test_reference_error_does_not_disclose_simrs_values() -> None:
    from scripts.simrs_manifest_example import build_manifest

    value = json.loads((EXAMPLES / "simrs-response.synthetic.json").read_text())
    value["data"]["no_rkm_medis"] = "SYNTHETIC_PRIVATE_IDENTIFIER" * 4
    with pytest.raises(ValueError) as error:
        build_manifest(
            value, "SYNTHETIC-VISIT-2026-0001", {}, "2026-10-12T10:00:00+07:00"
        )
    assert "SYNTHETIC_PRIVATE" not in str(error.value)


def test_simrs_contract_success_with_explicit_confirmation() -> None:
    from scripts.simrs_manifest_example import (
        SIMRSConfirmationRequiredError,
        build_manifest,
        parse_simrs_http_response,
    )

    response = {
        "success": True,
        "data": {
            "no_rawat": "SYNTHETIC-VISIT-2026-9999",
            "no_rkm_medis": "SYNTHETIC-MRN-9999",
            "nm_pasien": "SYNTHETIC PATIENT NAME",
            "jk": "L",
            "tgl_lahir": "1990-05-15",
            "tgl_daftar": "2026-10-12",
        },
    }
    # 1. Without operator confirmation -> MUST fail
    with pytest.raises(SIMRSConfirmationRequiredError):
        build_manifest(
            response,
            "SYNTHETIC-VISIT-2026-9999",
            {"L": "male"},
            "2026-10-12T10:00:00+07:00",
            confirmed=False,
        )

    # 2. With explicit operator confirmation -> succeeds
    manifest = build_manifest(
        response,
        "SYNTHETIC-VISIT-2026-9999",
        {"L": "male"},
        "2026-10-12T10:00:00+07:00",
        confirmed=True,
    )
    assert manifest["patient"]["medical_record_number"] == "SYNTHETIC-MRN-9999"
    assert manifest["patient"]["name"] == {"full_name": "SYNTHETIC PATIENT NAME"}
    assert manifest["patient"]["sex"] == "male"
    assert manifest["patient"]["birth_date"] == "1990-05-15"
    assert manifest["examination"]["encounter_id"] == "SYNTHETIC-VISIT-2026-9999"

    # 3. Via HTTP response parser simulation (GET /api/api_reg.php?id=...)
    http_manifest = parse_simrs_http_response(
        200,
        json.dumps(response),
        "SYNTHETIC-VISIT-2026-9999",
        confirmed_sex_codes={"L": "male"},
        captured_at="2026-10-12T10:00:00+07:00",
        confirmed=True,
    )
    assert http_manifest == manifest


def test_simrs_contract_success_with_null_data() -> None:
    from scripts.simrs_manifest_example import (
        SIMRSPatientNotFoundError,
        build_manifest,
        parse_simrs_http_response,
    )

    response = {"success": True, "data": None}
    with pytest.raises(SIMRSPatientNotFoundError):
        build_manifest(
            response,
            "SYNTHETIC-NONEXISTENT-VISIT",
            {},
            "2026-10-12T10:00:00+07:00",
        )

    with pytest.raises(SIMRSPatientNotFoundError):
        parse_simrs_http_response(
            200,
            json.dumps(response),
            "SYNTHETIC-NONEXISTENT-VISIT",
            confirmed_sex_codes={},
            captured_at="2026-10-12T10:00:00+07:00",
        )


def test_simrs_contract_rejected_or_malformed_response() -> None:
    from scripts.simrs_manifest_example import (
        SIMRSResponseError,
        build_manifest,
        parse_simrs_http_response,
    )

    # 1. success: false
    with pytest.raises(SIMRSResponseError):
        build_manifest(
            {"success": False, "message": "Hospital DB Error"},
            "SYNTHETIC-VISIT-001",
            {},
            "2026-10-12T10:00:00+07:00",
        )

    # 2. HTTP error status 500
    with pytest.raises(SIMRSResponseError):
        parse_simrs_http_response(
            500,
            "Internal Server Error",
            "SYNTHETIC-VISIT-001",
            confirmed_sex_codes={},
            captured_at="2026-10-12T10:00:00+07:00",
        )

    # 3. Malformed JSON body
    with pytest.raises(SIMRSResponseError):
        parse_simrs_http_response(
            200,
            "<html>Not JSON</html>",
            "SYNTHETIC-VISIT-001",
            confirmed_sex_codes={},
            captured_at="2026-10-12T10:00:00+07:00",
        )


def test_simrs_contract_visit_id_mismatch() -> None:
    from scripts.simrs_manifest_example import build_manifest

    response = {
        "success": True,
        "data": {
            "no_rawat": "SYNTHETIC-VISIT-EXPECTED",
            "no_rkm_medis": "SYNTHETIC-MRN",
            "nm_pasien": "SYNTHETIC PATIENT",
            "jk": "L",
            "tgl_lahir": "1990-01-01",
        },
    }
    with pytest.raises(ValueError) as exc:
        build_manifest(
            response,
            "SYNTHETIC-DIFFERENT-VISIT",
            {},
            "2026-10-12T10:00:00+07:00",
        )
    assert "visit" in str(exc.value).lower()


def test_simrs_contract_unconfirmed_hospital_sex_code_mapping() -> None:
    from scripts.simrs_manifest_example import build_manifest

    response = {
        "success": True,
        "data": {
            "no_rawat": "SYNTHETIC-VISIT-001",
            "no_rkm_medis": "SYNTHETIC-MRN",
            "nm_pasien": "SYNTHETIC PATIENT",
            "jk": "L",
            "tgl_lahir": "1990-01-01",
        },
    }

    # When no mapping is confirmed, sex must default to 'unknown' without guessing
    manifest_unmapped = build_manifest(
        response, "SYNTHETIC-VISIT-001", {}, "2026-10-12T10:00:00+07:00"
    )
    assert manifest_unmapped["patient"]["sex"] == "unknown"

    # When a mapping is configured but does not contain the returned code, fail closed
    with pytest.raises(ValueError) as exc:
        build_manifest(
            response,
            "SYNTHETIC-VISIT-001",
            {"P": "female"},  # 'L' is not in confirmed mapping
            "2026-10-12T10:00:00+07:00",
        )
    assert "sex" in str(exc.value).lower()
