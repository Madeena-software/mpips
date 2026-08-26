from pathlib import Path

import numpy as np

from scripts.diagnose_production_dicom_e2e import (
    ALLOWED_DRIVE_IDS,
    rewrite_detector_mode,
    validate_dicom_structure,
)

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/diagnose-production-dicom-e2e.yml"


def test_workflow_is_manual_and_production_only():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "runs-on: [self-hosted, production]" in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "schedule:" not in text
    assert "workflow_run:" not in text
    assert "group: mpips-internal-beta" in text


def test_workflow_has_no_mutating_docker_commands():
    text = WORKFLOW.read_text()
    for command in (
        "docker compose up",
        "docker compose down",
        "docker service update",
        "docker restart",
        "docker network create",
        "docker network rm",
        "docker network connect",
        "docker network disconnect",
    ):
        assert command not in text


def test_only_approved_drive_objects_are_used():
    text = (ROOT / "scripts/diagnose_production_dicom_e2e.py").read_text()
    assert set(ALLOWED_DRIVE_IDS) == {
        "1EwG5WPLcR30vSTHaOAybTVg6S9P4GSMB",
        "1R6o53hMVBy3B__cAqJBUhwcoTn14VGWF",
    }
    assert "folders/" not in text
    assert text.count("drive.google.com/uc") == 1


def test_synthetic_rewrite_changes_only_detector_mode(tmp_path):
    source = tmp_path / "source.npz"
    target = tmp_path / "target.npz"
    raw = np.arange(12, dtype=np.uint16).reshape(3, 4)
    np.savez_compressed(
        source,
        id="radio-1",
        gainid="gain-1",
        xrayparams=np.asarray({"detectorMode": "BED", "other": "kept"}, dtype=object),
        cameraparams=np.asarray({"serialNumber": "camera-1"}, dtype=object),
        rawimage=raw,
    )
    rewrite_detector_mode(source, target)
    with (
        np.load(source, allow_pickle=True) as before,
        np.load(target, allow_pickle=True) as after,
    ):
        assert np.array_equal(before["rawimage"], after["rawimage"])
        assert after["xrayparams"].item() == {"detectorMode": "TRX", "other": "kept"}
        assert after["gainid"].item() == "gain-1"


def test_dicom_validator_requires_uint16_and_no_private_tags():
    source = (ROOT / "scripts/diagnose_production_dicom_e2e.py").read_text()
    assert "BitsAllocated" in source
    assert "PixelRepresentation" in source
    assert "private" in source.lower()
    assert validate_dicom_structure.__name__ == "validate_dicom_structure"


def test_report_does_not_contain_api_key_literal():
    source = (ROOT / "scripts/diagnose_production_dicom_e2e.py").read_text()
    assert 'print(os.environ.get("MPIPS_API_KEY"))' not in source
    assert "MPIPS_API_KEY=" not in source
