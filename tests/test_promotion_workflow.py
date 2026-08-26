import hashlib
import io
import json
import tarfile
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest

import scripts.promote_production_calibration as promotion
from scripts.promote_production_calibration import (
    PromotionError,
    build_staging,
    promote,
    runtime_preflight,
    validate_legacy_bed,
    validate_real_thorax_inputs,
    verify_carrier,
)

ROOT = Path(__file__).parents[1]
MANIFEST = (
    ROOT
    / "artifacts/promotion"
    / "trx-calibration-789adff52ed296d956f81ae8dc38247a73768d863495f91a916"
    "fc251aaf67811.json"
)
FINGERPRINT = "789adff52ed296d956f81ae8dc38247a73768d863495f91a916fc251aaf67811"
FUNCTIONAL_PASS = {
    field: "PASS"
    for field in (
        "BED_FUNCTIONAL_CONVERSION",
        "BED_DICOM_STRUCTURE",
        "SYNTHETIC_THORAX_PIXEL_IDENTITY",
        "SYNTHETIC_THORAX_CONVERSION",
        "SYNTHETIC_THORAX_DICOM_STRUCTURE",
    )
}
FUNCTIONAL_PASS.update(
    {
        "REAL_THORAX_ALL_PASS": "PASS",
        **{
            field: "PASS"
            for case in (1, 2, 3)
            for field in (
                f"REAL_THORAX_{case}_INPUT_COMPATIBILITY",
                f"REAL_THORAX_{case}_CONVERSION",
                f"REAL_THORAX_{case}_DICOM_STRUCTURE",
            )
        },
    }
)
ROLLBACK_PASS = {
    "ROLLBACK_BED_FUNCTIONAL_CONVERSION": "PASS",
    "ROLLBACK_BED_DICOM_STRUCTURE": "PASS",
}


def _artifact(directory: Path, mode: str, *, fingerprint: str = "fp") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    shape = (2, 3)
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": fingerprint,
                "image_shape": list(shape),
                "source_metadata": {"detector_mode": mode},
            }
        )
    )
    np.savez(directory / "remap.npz", map_x=np.zeros(shape), map_y=np.zeros(shape))


def _carrier(
    path: Path,
    *,
    member_name: str = "trx-calibration/metadata.json",
    fingerprint: str = FINGERPRINT,
) -> None:
    payload = {
        "validated": True,
        "fingerprint": fingerprint,
        "image_shape": [3000, 4096],
        "source_metadata": {
            "detector_mode": "TRX",
            "camera_params": {"serialNumber": "old"},
        },
    }
    with tarfile.open(path, "w:gz") as archive:
        directory = tarfile.TarInfo("trx-calibration/")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        data = json.dumps(payload).encode()
        info = tarfile.TarInfo(member_name)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
        if member_name.endswith("metadata.json"):
            remap = io.BytesIO()
            np.savez(remap, map_x=np.zeros((3000, 4096)), map_y=np.zeros((3000, 4096)))
            info = tarfile.TarInfo("trx-calibration/remap.npz")
            info.size = remap.tell()
            remap.seek(0)
            archive.addfile(info, remap)


def test_manifest_pins_exact_carrier() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["carrier"] == {
        "type": "google-drive",
        "file_id": "1ou8lFZlSlO7V-3mLQtzKFz6vyDVX3WQr",
    }
    assert manifest["archive_size"] == 70488061
    assert (
        manifest["archive_sha256"]
        == "39ead140fded085377ca52e9e7cf152549224e0816ccc3e73ed9a3ba7b0cdc61"
    )
    assert manifest["fingerprint"] == FINGERPRINT


def test_workflow_is_guarded_manual_production_workflow() -> None:
    text = (ROOT / ".github/workflows/promote-production-calibration.yml").read_text()
    assert "workflow_dispatch:" in text
    assert "runs-on: [self-hosted, production]" in text
    assert "group: mpips-internal-beta" in text
    assert "timeout-minutes:" in text
    for forbidden in (
        "push:",
        "pull_request:",
        "schedule:",
        "workflow_run:",
        "docker restart",
        "docker compose restart",
    ):
        assert forbidden not in text


def test_hash_mismatch_fails_before_extraction(tmp_path: Path) -> None:
    carrier = tmp_path / "carrier.part"
    carrier.write_bytes(b"wrong")
    with pytest.raises(PromotionError, match="carrier SHA-256"):
        verify_carrier(carrier, 5, "0" * 64)
    assert not (tmp_path / "trx-calibration").exists()


def test_runtime_preflight_rejects_old_runtime_before_mutation(tmp_path: Path) -> None:
    (tmp_path / ".mpips-version").write_text("0" * 40)
    (tmp_path / ".mpips-worker-image").write_text(f"mpips-npz-worker:{'0' * 40}")
    result = runtime_preflight(
        runtime_dir=tmp_path,
        run=lambda *args, **kwargs: SimpleNamespace(
            stdout="api\n" if args[0][1] == "ps" else "mpips-api:" + "0" * 40,
            returncode=0,
        ),
        merge_base=lambda *_: False,
    )
    assert result["CAMERA_INDEPENDENT_RUNTIME"] == "FAIL"
    assert (
        result["FINAL_PROMOTION_CLASSIFICATION"]
        == "PRODUCTION_RUNTIME_CAMERA_INDEPENDENT_CODE_REQUIRED"
    )


def test_runtime_preflight_accepts_descendant_with_matching_images(
    tmp_path: Path,
) -> None:
    sha = "a" * 40
    (tmp_path / ".mpips-version").write_text(sha)
    (tmp_path / ".mpips-worker-image").write_text(f"mpips-npz-worker:{sha}")
    result = runtime_preflight(
        runtime_dir=tmp_path,
        run=lambda *args, **kwargs: SimpleNamespace(
            stdout="api\n" if args[0][1] == "ps" else f"mpips-api:{sha}", returncode=0
        ),
        merge_base=lambda *_: True,
    )
    assert result["CAMERA_INDEPENDENT_RUNTIME"] == "PASS"


def test_runtime_preflight_rejects_image_mismatch(tmp_path: Path) -> None:
    sha = "a" * 40
    (tmp_path / ".mpips-version").write_text(sha)
    (tmp_path / ".mpips-worker-image").write_text("mpips-npz-worker:" + "b" * 40)
    result = runtime_preflight(
        runtime_dir=tmp_path,
        run=lambda *args, **kwargs: SimpleNamespace(
            stdout="api\n" if args[0][1] == "ps" else f"mpips-api:{sha}", returncode=0
        ),
        merge_base=lambda *_: True,
    )
    assert result["CAMERA_INDEPENDENT_RUNTIME"] == "FAIL"


def test_real_input_integrity_gate_precedes_pickle_npz_load(
    tmp_path: Path, monkeypatch
) -> None:
    for filename in (
        "TRX_1787726609597.npz",
        "TRX_1787727857802.npz",
        "TRX_1787727066011.npz",
        "TRX_1787726886830.npz",
    ):
        (tmp_path / filename).write_bytes(b"not-a-reviewed-npz")

    def forbidden_load(*args, **kwargs):
        raise AssertionError("pickle-bearing NPZ load happened before integrity gate")

    monkeypatch.setattr(promotion.np, "load", forbidden_load)
    evidence = validate_real_thorax_inputs(tmp_path)
    assert evidence["REAL_THORAX_GAIN_DOWNLOAD"] == "FAIL"
    assert evidence["REAL_THORAX_INPUTS_ALL_PASS"] == "FAIL"
    assert evidence["REAL_THORAX_ALL_PASS"] == "NOT_RUN"


@pytest.mark.parametrize(
    "member",
    [
        "/absolute",
        "trx-calibration/../escape",
        "other.txt",
        "trx-calibration/link",
    ],
)
def test_unsafe_or_unexpected_archive_members_fail(tmp_path: Path, member: str) -> None:
    carrier = tmp_path / "carrier.tar.gz"
    with tarfile.open(carrier, "w:gz") as archive:
        info = tarfile.TarInfo(member)
        info.size = 0
        info.type = tarfile.SYMTYPE if member.endswith("link") else tarfile.REGTYPE
        archive.addfile(info)
    with pytest.raises(PromotionError):
        verify_carrier(
            carrier,
            carrier.stat().st_size,
            hashlib.sha256(carrier.read_bytes()).hexdigest(),
        )


@pytest.mark.parametrize(
    "member_type", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE]
)
def test_archive_link_and_special_files_fail(
    tmp_path: Path, member_type: bytes
) -> None:
    carrier = tmp_path / "carrier.tar.gz"
    with tarfile.open(carrier, "w:gz") as archive:
        info = tarfile.TarInfo("trx-calibration/remap.npz")
        info.type = member_type
        info.linkname = "metadata.json"
        archive.addfile(info)
    with pytest.raises(PromotionError):
        verify_carrier(
            carrier,
            carrier.stat().st_size,
            hashlib.sha256(carrier.read_bytes()).hexdigest(),
        )


def test_legacy_bed_is_validated_and_multimode_stops(tmp_path: Path) -> None:
    _artifact(tmp_path, "BED")
    assert validate_legacy_bed(tmp_path)["detector_mode"] == "BED"
    _artifact(tmp_path / "TRX", "TRX")
    with pytest.raises(PromotionError, match="ALREADY_MULTI_MODE"):
        validate_legacy_bed(tmp_path)


def test_staging_preserves_bed_bytes_and_validates_complete_layout(
    tmp_path: Path,
) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    stage = build_staging(
        active,
        carrier,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert (
        hashlib.sha256((stage / "BED/metadata.json").read_bytes()).hexdigest()
        == hashlib.sha256((active / "metadata.json").read_bytes()).hexdigest()
    )
    assert (
        hashlib.sha256((stage / "BED/remap.npz").read_bytes()).hexdigest()
        == hashlib.sha256((active / "remap.npz").read_bytes()).hexdigest()
    )
    assert (stage / "metadata.json").is_file()
    assert (stage / "remap.npz").is_file()
    assert (stage / "TRX/metadata.json").is_file()


def test_invalid_trx_stops_before_active_swap(tmp_path: Path) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier, fingerprint="wrong")
    before = (active / "metadata.json").read_bytes()
    with pytest.raises(PromotionError):
        promote(
            active,
            carrier,
            expected_size=carrier.stat().st_size,
            expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
        )
    assert (active / "metadata.json").read_bytes() == before


def test_post_swap_failure_rolls_back_and_revalidates_bed(tmp_path: Path) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    original = (active / "metadata.json").read_bytes()
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    result = promote(
        active,
        carrier,
        functional_check=lambda: {**FUNCTIONAL_PASS, "BED_DICOM_STRUCTURE": "FAIL"},
        container_check=lambda: "PASS",
        rollback_bed_check=lambda: ROLLBACK_PASS,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["ROLLBACK_REQUIRED"] == "YES"
    assert result["ROLLBACK_RESULT"] == "PASS"
    assert (active / "metadata.json").read_bytes() == original


def test_success_requires_explicit_functional_and_container_evidence(
    tmp_path: Path,
) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    inode = active.stat().st_ino
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    result = promote(
        active,
        carrier,
        functional_check=lambda: FUNCTIONAL_PASS,
        container_check=lambda: "PASS",
        rollback_bed_check=lambda: ROLLBACK_PASS,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["POST_SWAP_BED_BYTE_PRESERVATION"] == "PASS"
    assert result["POST_SWAP_BED_METADATA_SHA256"] == result["BED_PRE_METADATA_SHA256"]
    assert result["POST_SWAP_BED_REMAP_SHA256"] == result["BED_PRE_REMAP_SHA256"]
    assert result["CONTAINER_CALIBRATION_VIEW"] == "PASS"
    assert active.stat().st_ino == inode
    assert not (active / "metadata.json").exists()
    assert not (active / "remap.npz").exists()
    assert (
        result["FINAL_PROMOTION_CLASSIFICATION"]
        == "PRODUCTION_CALIBRATION_BED_TRX_PROMOTION_PASS"
    )


def test_real_thorax_failure_triggers_rollback(tmp_path: Path) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    failed_real = {
        **FUNCTIONAL_PASS,
        "REAL_THORAX_1_CONVERSION": "FAIL",
        "REAL_THORAX_ALL_PASS": "FAIL",
    }
    result = promote(
        active,
        carrier,
        functional_check=lambda: failed_real,
        container_check=lambda: "PASS",
        rollback_bed_check=lambda: ROLLBACK_PASS,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["REAL_THORAX_1_CONVERSION"] == "FAIL"
    assert result["ROLLBACK_REQUIRED"] == "YES"
    assert result["ROLLBACK_RESULT"] == "PASS"


def test_container_calibration_view_passes_for_new_layout() -> None:
    def run(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="")

    assert promotion.container_calibration_view(run=run, container="api") == "PASS"


def test_container_calibration_view_detects_legacy_stale_mount() -> None:
    def run(args, **kwargs):
        command = args[-1]
        return SimpleNamespace(
            returncode=0 if command.startswith("test -f") else 1, stdout=""
        )

    assert promotion.container_calibration_view(run=run, container="api") == "STALE"


def test_real_thorax_runs_before_bed_regression(tmp_path: Path, monkeypatch) -> None:
    order = []

    def real_checks(data_dir):
        order.append("real")
        return {**FUNCTIONAL_PASS}

    def bed_check(summary):
        order.append("bed")
        return {
            field: "PASS" for field in FUNCTIONAL_PASS if not field.startswith("REAL_")
        }

    monkeypatch.setattr(promotion, "run_real_thorax_checks", real_checks)
    monkeypatch.setattr(promotion, "_run_diagnostic", bed_check)
    evidence = promotion._run_priority_functional_checks(tmp_path, tmp_path / "summary")
    assert order == ["real", "bed"]
    assert evidence["REAL_THORAX_ALL_PASS"] == "PASS"


def test_real_thorax_failure_skips_bed_regression(tmp_path: Path, monkeypatch) -> None:
    order = []
    failed = {**FUNCTIONAL_PASS, "REAL_THORAX_ALL_PASS": "FAIL"}
    monkeypatch.setattr(
        promotion,
        "run_real_thorax_checks",
        lambda data_dir: order.append("real") or failed,
    )
    monkeypatch.setattr(
        promotion,
        "_run_diagnostic",
        lambda summary: order.append("bed") or FUNCTIONAL_PASS,
    )
    evidence = promotion._run_priority_functional_checks(tmp_path, tmp_path / "summary")
    assert order == ["real"]
    assert evidence["REAL_THORAX_ALL_PASS"] == "FAIL"


def test_stale_bind_mount_rolls_back_with_specific_classification(
    tmp_path: Path,
) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    rollback_called = []
    result = promote(
        active,
        carrier,
        functional_check=lambda: FUNCTIONAL_PASS,
        container_check=lambda: "STALE",
        rollback_bed_check=lambda: rollback_called.append(True) or ROLLBACK_PASS,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["CONTAINER_CALIBRATION_VIEW"] == "STALE"
    assert (
        result["FINAL_PROMOTION_CLASSIFICATION"]
        == "CALIBRATION_BIND_MOUNT_REFRESH_REQUIRED"
    )
    assert result["ROLLBACK_RESULT"] == "PASS"
    assert rollback_called == [True]


@pytest.mark.parametrize(
    "failed_field",
    [
        "ROLLBACK_BED_FUNCTIONAL_CONVERSION",
        "ROLLBACK_BED_DICOM_STRUCTURE",
    ],
)
def test_rollback_requires_real_bed_functional_evidence(
    tmp_path: Path, failed_field: str
) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    rollback = {**ROLLBACK_PASS, failed_field: "FAIL"}
    result = promote(
        active,
        carrier,
        functional_check=lambda: FUNCTIONAL_PASS,
        container_check=lambda: "STALE",
        rollback_bed_check=lambda: rollback,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["ROLLBACK_RESULT"] == "FAIL"
    assert (
        result["FINAL_PROMOTION_CLASSIFICATION"]
        == "PRODUCTION_CALIBRATION_ROLLBACK_FAILED"
    )


def test_rollback_failure_evidence_is_explicit(tmp_path: Path, monkeypatch) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    monkeypatch.setattr(
        promotion,
        "_rollback",
        lambda active, rollback, bed_check: {
            "ROLLBACK_BED_LAYOUT": "FAIL",
            "ROLLBACK_BED_FUNCTIONAL_CONVERSION": "FAIL",
            "ROLLBACK_BED_DICOM_STRUCTURE": "FAIL",
            "ROLLBACK_RESULT": "FAIL",
        },
    )
    result = promote(
        active,
        carrier,
        functional_check=lambda: FUNCTIONAL_PASS,
        container_check=lambda: "STALE",
        rollback_bed_check=lambda: ROLLBACK_PASS,
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["ROLLBACK_REQUIRED"] == "YES"
    assert result["ROLLBACK_RESULT"] == "FAIL"
    assert (
        result["FINAL_PROMOTION_CLASSIFICATION"]
        == "PRODUCTION_CALIBRATION_ROLLBACK_FAILED"
    )


def test_rollback_failure_evidence_is_written_to_summary(tmp_path: Path) -> None:
    summary = tmp_path / "summary.txt"
    result = {
        "ROLLBACK_REQUIRED": "YES",
        "ROLLBACK_RESULT": "FAIL",
        "FINAL_PROMOTION_CLASSIFICATION": "PRODUCTION_CALIBRATION_ROLLBACK_FAILED",
    }
    promotion._append_summary(summary, result)
    text = summary.read_text()
    assert "ROLLBACK_REQUIRED=YES" in text
    assert "ROLLBACK_RESULT=FAIL" in text
    assert (
        "FINAL_PROMOTION_CLASSIFICATION=PRODUCTION_CALIBRATION_ROLLBACK_FAILED" in text
    )


def test_no_production_mutation_commands_are_present() -> None:
    text = (ROOT / ".github/workflows/promote-production-calibration.yml").read_text()
    for forbidden in (
        "docker restart",
        "docker compose restart",
        "docker service update",
        "docker compose up",
        "docker network",
    ):
        assert forbidden not in text
