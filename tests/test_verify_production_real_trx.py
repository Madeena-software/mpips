from pathlib import Path

import pytest

from scripts.verify_production_real_trx import (
    EXPECTED_RUNTIME_SHA,
    EXPECTED_TRX_FINGERPRINT,
    FINAL_CLASSIFICATION,
    load_manifest,
    validate_runtime_markers,
)

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/verify-production-real-trx.yml"


def test_canonical_manifest_is_the_only_four_input_authority() -> None:
    manifest = load_manifest()

    assert len(manifest["radiographs"]) == 3
    assert manifest["gain"]["file_id"] == "1kI99se2CjzCgo4qInMEGUuJ-ZJZE3iQY"
    assert [item["case"] for item in manifest["radiographs"]] == [1, 2, 3]
    assert manifest["expected"] == {
        "detector_mode": "TRX",
        "external_detector_type": "THORAX",
        "image_shape": [3000, 4096],
        "gain_id": "1787726609597",
    }


def test_runtime_markers_require_exact_stage_c_runtime(tmp_path: Path) -> None:
    (tmp_path / ".mpips-version").write_text(EXPECTED_RUNTIME_SHA)
    (tmp_path / ".mpips-worker-image").write_text(
        f"mpips-npz-worker:{EXPECTED_RUNTIME_SHA}"
    )

    assert (
        validate_runtime_markers(tmp_path, f"mpips-api:{EXPECTED_RUNTIME_SHA}")[
            "TRX_PIPELINE_RUNTIME"
        ]
        == "PASS"
    )

    (tmp_path / ".mpips-version").write_text("wrong")
    with pytest.raises(RuntimeError):
        validate_runtime_markers(tmp_path, f"mpips-api:{EXPECTED_RUNTIME_SHA}")


def test_workflow_is_manual_production_only_and_has_no_mutation_paths() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "runs-on: [self-hosted, production]" in workflow
    assert "uses: actions/checkout@v4" in workflow
    assert "ref: main" not in workflow
    assert "actions/checkout@v4\n        with:" not in workflow
    assert '--summary "$GITHUB_STEP_SUMMARY"' in workflow
    assert "deploy" not in workflow.lower()
    assert "promote" not in workflow.lower()
    assert "docker compose" not in workflow.lower()
    assert "docker restart" not in workflow.lower()
    assert "gdown==6.1.0" in workflow


def test_stage_c_constants_pin_fingerprint_and_classification() -> None:
    assert EXPECTED_TRX_FINGERPRINT == (
        "1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492"
    )
    assert FINAL_CLASSIFICATION == "PRODUCTION_REAL_TRX_ACCEPTANCE_PASS"


def test_download_validation_precedes_pickle_bearing_load_and_has_four_inputs() -> None:
    source = (ROOT / "scripts/verify_production_real_trx.py").read_text()

    assert source.index("_verify_npz_archive") < source.index(
        "validate_real_thorax_inputs"
    )
    assert source.count('manifest["radiographs"]') >= 2
    assert ".part" in source
    assert "TemporaryDirectory" in source


def test_verifier_does_not_contain_mutating_production_operations() -> None:
    source = (ROOT / "scripts/verify_production_real_trx.py").read_text()

    for forbidden in (
        "promotion.promote",
        "prepare_root_staging",
        "_switch_to_multimode",
        "promotion._rollback",
        "docker compose",
        "docker restart",
    ):
        assert forbidden not in source


def test_dicom_acceptance_geometry_and_collapse_checks_are_retained() -> None:
    source = (ROOT / "scripts/promote_production_calibration.py").read_text()

    assert "EXPECTED_FINAL_DICOM_SHAPE = (4114, 3045)" in source
    assert "REAL_THORAX_ALL_PASS" in source
    assert "_real_dicom_image_acceptance" in source
    assert ">= 0.5" in source
