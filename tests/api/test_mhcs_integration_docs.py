from __future__ import annotations

from pathlib import Path

from mpips.api.schemas.dicom import MHCSManifest


def test_mhcs_example_manifest_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    example_path = (
        repo_root
        / "docs"
        / "integration"
        / "examples"
        / "mhcs-dicom-manifest.example.json"
    )
    assert example_path.exists(), f"Example manifest missing at {example_path}"

    manifest_text = example_path.read_text(encoding="utf-8")
    parsed_manifest = MHCSManifest.model_validate_json(manifest_text)

    assert str(parsed_manifest.manifest_version) == "1.0"
    assert parsed_manifest.capture is not None
    assert parsed_manifest.capture.radiograph is not None
    assert parsed_manifest.capture.radiograph.byte_size is not None
    assert parsed_manifest.capture.radiograph.byte_size > 0
    assert parsed_manifest.capture.radiograph.sha256 is not None
    assert len(parsed_manifest.capture.radiograph.sha256) == 64
    assert parsed_manifest.capture.gain is not None
    assert parsed_manifest.capture.gain.sha256 is not None
    assert len(parsed_manifest.capture.gain.sha256) == 64
    assert parsed_manifest.dicom is not None
    assert parsed_manifest.dicom.presentation_intent == "FOR PRESENTATION"


def test_mhcs_minimal_example_manifest_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    example_path = (
        repo_root
        / "docs"
        / "integration"
        / "examples"
        / "mhcs-dicom-manifest.minimal.example.json"
    )
    assert example_path.exists(), f"Minimal example manifest missing at {example_path}"

    manifest_text = example_path.read_text(encoding="utf-8")
    parsed_manifest = MHCSManifest.model_validate_json(manifest_text)

    assert str(parsed_manifest.manifest_version) == "1.0"
    assert parsed_manifest.patient.medical_record_number == "MRN-90214810"
    assert parsed_manifest.patient.name.full_name == "JANE DOE"
    assert parsed_manifest.capture is not None
    assert parsed_manifest.capture.detector_type == "THORAX"
    assert parsed_manifest.capture.body_part_examined == "CHEST"


def test_mhcs_integration_doc_exists_and_is_populated() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    doc_path = repo_root / "docs" / "integration" / "mhcs-dicom-api.md"
    assert doc_path.exists(), f"Integration doc missing at {doc_path}"

    content = doc_path.read_text(encoding="utf-8")
    assert len(content) > 1000, "Integration documentation is too short or empty"
    assert "MHCS INTEGRATION CONTRACT & IMPLEMENTATION GUIDE" in content
    assert "POST /v1/radiographs/dicom" in content
    assert "CONCURRENCY_LIMIT_EXCEEDED" in content
    assert "PROPOSED_MHCS_RETRY_POLICY" in content
    assert "MINIMAL MANIFEST" in content
    assert "ResolvedMHCSManifest" in content
    assert "SERVER COMPUTED" in content
    assert "SERVER DERIVED" in content
    assert "deterministic conversion_job_id" in content.lower()
    assert "dicom uids" in content.lower()
    assert "X-Conversion-Job-ID" in content
    assert "X-Correlation-ID" in content
    assert "MHCS_HTTP_TIMEOUT_UNKNOWN=true" in content
    assert "NPZ_UNTRUSTED_INPUT_SECURITY_POSTURE=OPEN" in content
    assert "CLINICAL_TIMESTAMP_FALLBACK_POLICY" in content
