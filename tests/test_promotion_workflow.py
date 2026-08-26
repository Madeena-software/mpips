import hashlib
import io
import json
import tarfile
from pathlib import Path

import numpy as np
import pytest

from scripts.promote_production_calibration import (
    PromotionError,
    atomic_swap,
    build_staging,
    promote,
    validate_legacy_bed,
    verify_carrier,
)
from scripts.validate_calibration_layout import validate_calibration_layout

ROOT = Path(__file__).parents[1]
MANIFEST = (
    ROOT
    / "artifacts/promotion"
    / "trx-calibration-789adff52ed296d956f81ae8dc38247a73768d863495f91a916"
    "fc251aaf67811.json"
)
FINGERPRINT = "789adff52ed296d956f81ae8dc38247a73768d863495f91a916fc251aaf67811"


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
    assert validate_calibration_layout(stage) == []


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


def test_atomic_swap_and_failed_second_rename_restore_original(tmp_path: Path) -> None:
    active, staged, rollback = (
        tmp_path / name for name in ("active", "staged", "rollback")
    )
    _artifact(active, "BED")
    _artifact(staged, "BED", fingerprint="new")
    atomic_swap(active, staged, rollback)
    assert (active / "metadata.json").read_text().find('"new"') >= 0
    assert rollback.is_dir()

    active, staged, rollback = (
        tmp_path / name for name in ("active2", "staged2", "rollback2")
    )
    _artifact(active, "BED")
    _artifact(staged, "BED", fingerprint="new")
    calls = 0

    def rename(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected rename failure")
        source.rename(target)

    with pytest.raises(OSError):
        atomic_swap(active, staged, rollback, rename=rename)
    assert active.is_dir()
    assert staged.is_dir()
    assert '"new"' not in (active / "metadata.json").read_text()


def test_post_swap_failure_rolls_back_and_revalidates_bed(tmp_path: Path) -> None:
    active = tmp_path / "calibration"
    _artifact(active, "BED")
    original = (active / "metadata.json").read_bytes()
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier)
    result = promote(
        active,
        carrier,
        post_swap_checks=[lambda: False],
        expected_size=carrier.stat().st_size,
        expected_sha256=hashlib.sha256(carrier.read_bytes()).hexdigest(),
    )
    assert result["ROLLBACK_REQUIRED"] == "YES"
    assert result["ROLLBACK_RESULT"] == "PASS"
    assert (active / "metadata.json").read_bytes() == original


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
