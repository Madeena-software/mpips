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
    assert parsed_manifest.capture.radiograph.byte_size > 0
    assert len(parsed_manifest.capture.radiograph.sha256) == 64
    assert len(parsed_manifest.capture.gain.sha256) == 64
    assert parsed_manifest.dicom.presentation_intent == "FOR PRESENTATION"


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
    assert "MHCS_HTTP_TIMEOUT_UNKNOWN=true" in content
    assert "NPZ_UNTRUSTED_INPUT_SECURITY_POSTURE=OPEN" in content
    assert "SUCCEEDED_SAME" in content
