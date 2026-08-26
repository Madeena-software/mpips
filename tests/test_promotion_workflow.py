import hashlib
import io
import json
import tarfile
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

import scripts.promote_production_calibration as promotion
from scripts.promote_production_calibration import (
    PromotionError,
    build_staging,
    promote,
    runtime_preflight,
    validate_legacy_bed,
    validate_carrier_identity,
    validate_real_thorax_inputs,
    verify_carrier,
)

ROOT = Path(__file__).parents[1]
MANIFEST = (
    ROOT
    / "artifacts/promotion"
    / "trx-calibration-1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492"
    ".json"
)
FINGERPRINT = "1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492"
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
                f"REAL_THORAX_{case}_IMAGE_ACCEPTANCE",
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
    canvas_mode: str = "expanded",
    remap_shape: list[int] | None = None,
) -> None:
    remap_shape = remap_shape or [3045, 4114]
    payload = {
        "validated": True,
        "fingerprint": fingerprint,
        "image_shape": [3000, 4096],
        "grid_shape": [18, 25],
        "config": {"canvas_mode": canvas_mode},
        "CANVAS_MODE": canvas_mode,
        "expanded_origin_xy": [42, -73],
        "REMAP_OUTPUT_SHAPE": remap_shape,
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
            x = np.broadcast_to(
                np.linspace(0, 4095, 4114, dtype=np.float32), (3045, 4114)
            )
            y = np.broadcast_to(
                np.linspace(0, 2999, 3045, dtype=np.float32)[:, None], (3045, 4114)
            )
            np.savez(remap, map_x=x, map_y=y)
            info = tarfile.TarInfo("trx-calibration/remap.npz")
            info.size = remap.tell()
            remap.seek(0)
            archive.addfile(info, remap)


def _valid_dicom(path: Path) -> None:
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1.1"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    ds = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID, ds.SeriesInstanceUID = generate_uid(), generate_uid()
    ds.Rows, ds.Columns = 2, 2
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 0
    ds.PixelData = np.zeros((2, 2), dtype=np.uint16).tobytes()
    ds.save_as(path)


def test_manifest_pins_exact_carrier() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["carrier"] == {
        "provider": "google-drive",
        "file_id": "1TpiHJfM0EHEKvZ1rZ2VqSV0-k0ycrzCG",
        "filename": (
            "trx-calibration-1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c"
            "089381af3e7dd1492"
            ".tar.gz"
        ),
        "size": 73915583,
        "sha256": "b0d645233eb598c549a1b04fc24a1364f68b79cc0d0e0db51ac1936d7e11f90f",
    }
    assert manifest["archive_size"] == 73915583
    assert (
        manifest["archive_sha256"]
        == "b0d645233eb598c549a1b04fc24a1364f68b79cc0d0e0db51ac1936d7e11f90f"
    )
    assert manifest["fingerprint"] == FINGERPRINT
    assert manifest["canvas_mode"] == "expanded"
    assert manifest["expanded_origin"] == [42, -73]
    assert manifest["remap_shape"] == [3045, 4114]
    assert manifest["expected_final_dicom_shape"] == [4114, 3045]
    assert manifest["grid_shape"] == [18, 25]
    assert manifest["geometry_validated"] is True
    assert manifest["real_trx_pipeline_validated"] is True
    assert manifest["validated"] is True
    assert manifest["validation_status"] == "REAL_TRX_EXPANDED_VALIDATED"


def test_historical_manifest_remains_unchanged() -> None:
    historical = json.loads(
        (
            ROOT
            / (
                "artifacts/promotion/trx-calibration-606db560c391764b24fa6257a01a8afb"
                "38380b83bf83ea7bd6a30b299861547d.json"
            )
        ).read_text()
    )
    assert historical["fingerprint"].startswith("606db560")


def test_real_thorax_manifest_pins_all_three_cases() -> None:
    manifest = json.loads(
        (ROOT / "artifacts/test-data/real-thorax-trx-da5277082.json").read_text()
    )
    assert manifest["gain"] == {
        "file_id": "1kI99se2CjzCgo4qInMEGUuJ-ZJZE3iQY",
        "filename": "TRX_1787726609597.npz",
        "size": 17190412,
        "sha256": "38918e436e5329e28b08c844e8df3766a1ab83a1fc3135c83df56370c480b2a9",
    }
    assert [item["file_id"] for item in manifest["radiographs"]] == [
        "1ocIGsYS6RHIurhRuOwJCzSHTv-6STc_m",
        "1G9HTPyJzYFHwbAfZ3SU0sL84k9A6i5BD",
        "1Ft3OALtx_d3ua-z0DSS34jJmywaXjLu2",
    ]
    assert manifest["expected"] == {
        "detector_mode": "TRX",
        "external_detector_type": "THORAX",
        "image_shape": [3000, 4096],
        "gain_id": "1787726609597",
    }


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
    assert "TRX_CARRIER_ID_MISMATCH" in text
    assert "approved_carrier_id=" in text


def test_carrier_identity_gate_fails_closed() -> None:
    with pytest.raises(PromotionError, match="TRX_CARRIER_NOT_PUBLISHED"):
        validate_carrier_identity(None)
    with pytest.raises(PromotionError, match="TRX_CARRIER_ID_MISMATCH"):
        validate_carrier_identity("1ou8lFZlSlO7V-3mLQtzKFz6vyDVX3WQr")
    assert (
        validate_carrier_identity("1TpiHJfM0EHEKvZ1rZ2VqSV0-k0ycrzCG")
        == "1TpiHJfM0EHEKvZ1rZ2VqSV0-k0ycrzCG"
    )


def test_hash_mismatch_fails_before_extraction(tmp_path: Path) -> None:
    carrier = tmp_path / "carrier.part"
    carrier.write_bytes(b"wrong")
    with pytest.raises(PromotionError, match="carrier SHA-256"):
        verify_carrier(carrier, 5, "0" * 64)
    assert not (tmp_path / "trx-calibration").exists()


def test_historical_trx_fingerprint_is_rejected(tmp_path: Path) -> None:
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(
        carrier,
        fingerprint="606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d",
    )
    with pytest.raises(PromotionError, match="TRX fingerprint mismatch"):
        promotion._validate_trx(promotion._extract_carrier(carrier, tmp_path / "stage"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("CANVAS_MODE", "fixed", "canvas mode"),
        ("REMAP_OUTPUT_SHAPE", [3000, 4096], "remap shape"),
    ],
)
def test_expanded_trx_semantics_are_required(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    carrier = tmp_path / "carrier.tar.gz"
    _carrier(carrier, **{"canvas_mode": value} if field == "CANVAS_MODE" else {})
    if field != "CANVAS_MODE":
        extracted = promotion._extract_carrier(carrier, tmp_path / "stage")
        metadata = json.loads((extracted / "metadata.json").read_text())
        metadata[field] = value
        (extracted / "metadata.json").write_text(json.dumps(metadata))
        with pytest.raises(PromotionError, match=message):
            promotion._validate_trx(extracted)
        return
    extracted = promotion._extract_carrier(carrier, tmp_path / "stage")
    with pytest.raises(PromotionError, match=message):
        promotion._validate_trx(extracted)


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
    assert result["TRX_PIPELINE_RUNTIME"] == "PASS"


def test_runtime_preflight_accepts_required_trx_baseline_with_matching_images(
    tmp_path: Path,
) -> None:
    sha = promotion.REQUIRED_TRX_PIPELINE_BASELINE
    (tmp_path / ".mpips-version").write_text(sha)
    (tmp_path / ".mpips-worker-image").write_text(f"mpips-npz-worker:{sha}")
    result = runtime_preflight(
        runtime_dir=tmp_path,
        run=lambda *args, **kwargs: SimpleNamespace(
            stdout="api\n" if args[0][1] == "ps" else f"mpips-api:{sha}",
            returncode=0,
        ),
        merge_base=lambda _baseline, _sha: True,
    )
    assert result["CAMERA_INDEPENDENT_RUNTIME"] == "PASS"
    assert result["TRX_PIPELINE_RUNTIME"] == "PASS"


def test_runtime_preflight_rejects_camera_independent_runtime_before_trx_baseline(
    tmp_path: Path,
) -> None:
    sha = "a" * 40
    (tmp_path / ".mpips-version").write_text(sha)
    (tmp_path / ".mpips-worker-image").write_text(f"mpips-npz-worker:{sha}")
    result = runtime_preflight(
        runtime_dir=tmp_path,
        run=lambda *args, **kwargs: SimpleNamespace(
            stdout="api\n" if args[0][1] == "ps" else f"mpips-api:{sha}",
            returncode=0,
        ),
        merge_base=lambda baseline, _sha: baseline
        == promotion.CAMERA_INDEPENDENT_BASELINE,
    )
    assert result["CAMERA_INDEPENDENT_RUNTIME"] == "PASS"
    assert result["TRX_PIPELINE_RUNTIME"] == "FAIL"
    assert (
        result["FINAL_PROMOTION_CLASSIFICATION"]
        == "PRODUCTION_RUNTIME_TRX_PIPELINE_CODE_REQUIRED"
    )


def test_real_dicom_structure_requires_canonical_trx_dimensions(tmp_path: Path) -> None:
    path = tmp_path / "trx.dcm"
    _valid_dicom(path)
    ds = pydicom.dcmread(path)
    ds.Rows, ds.Columns = 4114, 3045
    ds.PixelData = np.ones((4114, 3045), dtype=np.uint16).tobytes()
    ds.save_as(path)
    assert promotion._real_dicom_structure(path)


def test_real_dicom_structure_rejects_stale_transposed_dimensions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trx.dcm"
    _valid_dicom(path)
    ds = pydicom.dcmread(path)
    ds.Rows, ds.Columns = 3000, 4096
    ds.PixelData = np.ones((3000, 4096), dtype=np.uint16).tobytes()
    ds.save_as(path)
    assert not promotion._real_dicom_structure(path)


@pytest.mark.parametrize("case", [2, 3])
def test_real_dicom_image_acceptance_rejects_catastrophic_black_cases(
    tmp_path: Path, case: int
) -> None:
    path = tmp_path / f"case-{case}.dcm"
    _valid_dicom(path)
    ds = pydicom.dcmread(path)
    ds.Rows, ds.Columns = 4114, 3045
    ds.PixelData = np.zeros((4114, 3045), dtype=np.uint16).tobytes()
    ds.save_as(path)
    assert not promotion._real_dicom_image_acceptance(path)


def test_real_dicom_image_acceptance_rejects_zero_ratio_at_fifty_percent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "half-black.dcm"
    _valid_dicom(path)
    ds = pydicom.dcmread(path)
    ds.Rows, ds.Columns = 4114, 3045
    pixels = np.zeros((4114, 3045), dtype=np.uint16)
    pixels[:2057, :] = 1
    ds.PixelData = pixels.tobytes()
    ds.save_as(path)
    assert not promotion._real_dicom_image_acceptance(path)


def test_workflow_fails_closed_without_current_carrier() -> None:
    text = (ROOT / ".github/workflows/promote-production-calibration.yml").read_text()
    assert "1ou8lFZlSlO7V-3mLQtzKFz6vyDVX3WQr" not in text
    assert "NOT_PUBLISHED" in text


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
