"""Tests for Gate B tag routing, transaction config, and upload client."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
import pytest
import yaml

from mpips.update_server.gate_b import (
    APPROVED_BUCKET,
    APPROVED_CANDIDATE_SHA256,
    APPROVED_CANDIDATE_SIZE_BYTES,
    APPROVED_SOURCE_COMMIT,
    GateBTransactionError,
    load_transaction_config,
    parse_and_validate_transaction_config,
    resolve_operation_from_git_tag,
    seal_presigned_upload_handoff,
    unseal_and_validate_upload_handoff,
    validate_x25519_pubkey_b64,
    verify_live_sequence_expectations,
)
from scripts.gate_b_upload_client import (
    decrypt_and_upload_candidate_elf,
    generate_ephemeral_keypair,
    load_ephemeral_private_key,
    main as upload_client_main,
    parse_sealed_handoff_text,
)


def _valid_base_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "operation": "preflight_inspect",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "bucket": APPROVED_BUCKET,
        "upload_id": "",
        "handoff_recipient_pubkey_b64": "",
        "target_release_id": "",
        "version": "0.1.0",
        "expected_current_sequence": None,
        "target_sequence": None,
        "expected_sha256": APPROVED_CANDIDATE_SHA256,
        "expected_size_bytes": APPROVED_CANDIDATE_SIZE_BYTES,
        "source_commit": APPROVED_SOURCE_COMMIT,
    }


def _make_x25519_pair() -> tuple[X25519PrivateKey, str]:
    priv = X25519PrivateKey.generate()
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv, base64.b64encode(pub_raw).decode("ascii")


def test_gate_b_tag_routing_strict_mapping() -> None:
    """Each Gate B tag pattern maps to exactly one operation; invalid tags fail."""
    assert (
        resolve_operation_from_git_tag("gate-b-preflight-20261110-0001")
        == "preflight_inspect"
    )
    assert (
        resolve_operation_from_git_tag("refs/tags/gate-b-preflight-20261110-0001")
        == "preflight_inspect"
    )
    assert (
        resolve_operation_from_git_tag("gate-b-prepare-upload-20261110-0002")
        == "prepare_elf_upload"
    )
    assert (
        resolve_operation_from_git_tag("gate-b-publish-20261110-0003")
        == "publish_staged_elf"
    )

    for bad_tag in [
        "",
        "v0.1.0",
        "gate-b-preflight-2026111-0001",
        "gate-b-preflight-20261110-001",
        "gate-b-preflight-20261110-0001-extra",
        "gate-b-unknown-20261110-0001",
        "refs/heads/gate-b-preflight-20261110-0001",
    ]:
        with pytest.raises(GateBTransactionError):
            resolve_operation_from_git_tag(bad_tag)


def test_committed_transaction_config_and_workflows_valid() -> None:
    """Verify committed gate-b-transaction.json and workflow YAML files."""
    repo_root = Path(__file__).resolve().parents[1]
    tx_path = repo_root / ".agents" / "evidence" / "gate-b-transaction.json"
    cfg = load_transaction_config(
        tx_path,
        git_tag="gate-b-preflight-20261110-0001",
    )
    assert cfg.operation == "preflight_inspect"
    assert cfg.expected_sha256 == APPROVED_CANDIDATE_SHA256
    assert cfg.expected_size_bytes == APPROVED_CANDIDATE_SIZE_BYTES
    assert cfg.source_commit == APPROVED_SOURCE_COMMIT

    # Preflight tag must reject prepare_elf_upload or publish_staged_elf tags
    with pytest.raises(GateBTransactionError, match="does not match"):
        load_transaction_config(
            tx_path,
            git_tag="gate-b-publish-20261110-0001",
        )

    # Validate Gate A workflow is strictly unchanged from its deployment triggers
    gate_a_wf = yaml.safe_load(
        (
            repo_root / ".github" / "workflows" / "deploy-staging-update-server.yml"
        ).read_text(encoding="utf-8")
    )
    on_block_a = gate_a_wf.get("on") or gate_a_wf.get(True)
    assert "tags" not in on_block_a.get("push", {})

    # Validate Gate B workflow triggers only on the 3 explicit tag patterns
    gate_b_wf = yaml.safe_load(
        (
            repo_root / ".github" / "workflows" / "mpips-gate-b-publication.yml"
        ).read_text(encoding="utf-8")
    )
    on_block_b = gate_b_wf.get("on") or gate_b_wf.get(True)
    assert set(on_block_b.keys()) == {"push"}
    assert set(on_block_b["push"].keys()) == {"tags"}
    assert len(on_block_b["push"]["tags"]) == 3


def test_transaction_config_validation_rejects_malformed_or_inconsistent_fields() -> (
    None
):
    """Verify strict rejection of missing, unexpected, or inconsistent config values."""
    _, pub_b64 = _make_x25519_pair()

    # 1. Unknown key rejected
    bad_extra = {**_valid_base_config(), "secret_token": "forbidden"}
    with pytest.raises(GateBTransactionError, match="Unexpected keys"):
        parse_and_validate_transaction_config(bad_extra)

    # 2. Missing key rejected
    bad_missing = _valid_base_config()
    del bad_missing["source_commit"]
    with pytest.raises(GateBTransactionError, match="Missing required keys"):
        parse_and_validate_transaction_config(bad_missing)

    # 3. Wrong SHA-256, size, or source_commit rejected
    with pytest.raises(GateBTransactionError, match="expected_sha256"):
        parse_and_validate_transaction_config(
            {**_valid_base_config(), "expected_sha256": "a" * 64}
        )
    with pytest.raises(GateBTransactionError, match="expected_size_bytes"):
        parse_and_validate_transaction_config(
            {**_valid_base_config(), "expected_size_bytes": 12345}
        )
    with pytest.raises(GateBTransactionError, match="source_commit"):
        parse_and_validate_transaction_config(
            {**_valid_base_config(), "source_commit": "b" * 40}
        )

    # 4. prepare_elf_upload requires upload_id and valid X25519 pubkey
    with pytest.raises(GateBTransactionError, match="upload_id is required"):
        parse_and_validate_transaction_config(
            {**_valid_base_config(), "operation": "prepare_elf_upload"}
        )
    with pytest.raises(
        GateBTransactionError, match="handoff_recipient_pubkey_b64 is required"
    ):
        parse_and_validate_transaction_config(
            {
                **_valid_base_config(),
                "operation": "prepare_elf_upload",
                "upload_id": "gate-b-upload-20261110-0001",
            }
        )

    valid_prep = parse_and_validate_transaction_config(
        {
            **_valid_base_config(),
            "operation": "prepare_elf_upload",
            "upload_id": "gate-b-upload-20261110-0001",
            "handoff_recipient_pubkey_b64": pub_b64,
        },
        git_tag="gate-b-prepare-upload-20261110-0001",
    )
    assert valid_prep.operation == "prepare_elf_upload"

    # 5. All-zero X25519 public key rejected
    zero_pub = base64.b64encode(b"\x00" * 32).decode("ascii")
    with pytest.raises(GateBTransactionError, match="All-zero X25519"):
        validate_x25519_pubkey_b64(zero_pub)

    # 6. publish_staged_elf requires upload_id, release_id, and target > current
    with pytest.raises(GateBTransactionError, match="strictly exceed"):
        parse_and_validate_transaction_config(
            {
                **_valid_base_config(),
                "operation": "publish_staged_elf",
                "upload_id": "gate-b-upload-20261110-0001",
                "target_release_id": "0.1.0-20261110-seq1",
                "expected_current_sequence": 1,
                "target_sequence": 1,
            }
        )

    valid_pub = parse_and_validate_transaction_config(
        {
            **_valid_base_config(),
            "operation": "publish_staged_elf",
            "upload_id": "gate-b-upload-20261110-0001",
            "target_release_id": "0.1.0-20261110-seq1",
            "expected_current_sequence": 0,
            "target_sequence": 1,
        },
        git_tag="gate-b-publish-20261110-0001",
    )
    assert valid_pub.target_sequence == 1


def test_verify_live_sequence_expectations_rejects_stale_state() -> None:
    """Verify pre-publication live sequence check rejects stale or duplicate state."""
    cfg = parse_and_validate_transaction_config(
        {
            **_valid_base_config(),
            "operation": "publish_staged_elf",
            "upload_id": "gate-b-upload-20261110-0001",
            "target_release_id": "0.1.0-20261110-seq2",
            "expected_current_sequence": 0,
            "target_sequence": 2,
        }
    )

    # Matching live state (seq 1 allocated/revoked while current promoted is 0)
    verify_live_sequence_expectations(
        cfg,
        live_current_sequence=0,
        live_highest_allocated_sequence=1,
        registered_release_ids={"0.1.0-20261110-seq1"},
        candidate_sha256_already_promoted=False,
    )

    # Stale expected_current_sequence rejected
    with pytest.raises(GateBTransactionError, match="Stale expected_current_sequence"):
        verify_live_sequence_expectations(
            cfg,
            live_current_sequence=1,
            live_highest_allocated_sequence=1,
            registered_release_ids=set(),
        )

    # Stale target_sequence rejected
    with pytest.raises(GateBTransactionError, match="Stale target_sequence"):
        verify_live_sequence_expectations(
            cfg,
            live_current_sequence=0,
            live_highest_allocated_sequence=2,
            registered_release_ids=set(),
        )

    # Duplicate release_id rejected
    with pytest.raises(GateBTransactionError, match="already registered"):
        verify_live_sequence_expectations(
            cfg,
            live_current_sequence=0,
            live_highest_allocated_sequence=1,
            registered_release_ids={"0.1.0-20261110-seq2"},
        )

    # Duplicate promoted SHA-256 rejected
    with pytest.raises(GateBTransactionError, match="already promoted"):
        verify_live_sequence_expectations(
            cfg,
            live_current_sequence=0,
            live_highest_allocated_sequence=1,
            registered_release_ids=set(),
            candidate_sha256_already_promoted=True,
        )


def test_sealed_handoff_and_upload_client_security_controls(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test decryption failure, tampering, invalid URL, expiry, and bad hash."""
    priv_path = tmp_path / "keys" / "ephemeral-x25519.pem"
    keygen_res = generate_ephemeral_keypair(priv_path)
    pub_b64 = keygen_res["handoff_recipient_pubkey_b64"]
    priv_key = load_ephemeral_private_key(priv_path)
    assert (priv_path.stat().st_mode & 0o777) == 0o600

    # Refuses to overwrite existing keypair
    with pytest.raises(GateBTransactionError, match="Refusing to overwrite"):
        generate_ephemeral_keypair(priv_path)

    upload_id = "gate-b-upload-20261110-0001"
    object_key = f"staging/ubuntu-24.04-x86_64/incoming/{upload_id}/mpips-runtime.bin"
    secret_presigned_url = (
        f"https://s3.mhcsgo.cloud/mpips-dev-bucket/{object_key}"
        "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=supersecretpresignedsig"
    )
    now = datetime(2026, 11, 10, 8, 0, 0, tzinfo=timezone.utc)
    expires_at = (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")

    sealed = seal_presigned_upload_handoff(
        upload_id=upload_id,
        object_key=object_key,
        upload_url=secret_presigned_url,
        expires_at=expires_at,
        recipient_pubkey_b64=pub_b64,
    )

    # 1. Wrong recipient private key fails closed
    wrong_priv, _ = _make_x25519_pair()
    with pytest.raises(GateBTransactionError, match="decryption failed"):
        unseal_and_validate_upload_handoff(
            sealed,
            recipient_private_key=wrong_priv,
            expected_upload_id=upload_id,
            now=now,
        )

    # 2. Tampered ciphertext fails closed
    raw_ct = bytearray(base64.b64decode(sealed["ciphertext_b64"]))
    raw_ct[-1] ^= 0xFF
    tampered = {
        **sealed,
        "ciphertext_b64": base64.b64encode(bytes(raw_ct)).decode("ascii"),
    }
    with pytest.raises(GateBTransactionError, match="decryption failed"):
        unseal_and_validate_upload_handoff(
            tampered,
            recipient_private_key=priv_key,
            expected_upload_id=upload_id,
            now=now,
        )

    # 3. Wrong expected_upload_id fails closed
    with pytest.raises(GateBTransactionError, match="upload_id does not match"):
        unseal_and_validate_upload_handoff(
            sealed,
            recipient_private_key=priv_key,
            expected_upload_id="gate-b-upload-20261110-9999",
            now=now,
        )

    # 4. Expired presigned handoff fails closed
    expired_now = now + timedelta(minutes=11)
    with pytest.raises(GateBTransactionError, match="already expired"):
        unseal_and_validate_upload_handoff(
            sealed,
            recipient_private_key=priv_key,
            expected_upload_id=upload_id,
            now=expired_now,
        )

    # 5. Invalid URL (non-HTTPS or untrusted host or missing query) fails closed
    for bad_url in [
        f"http://s3.mhcsgo.cloud/mpips-dev-bucket/{object_key}?X-Amz-Signature=1",
        f"https://evil.example.com/mpips-dev-bucket/{object_key}?X-Amz-Signature=1",
        f"https://s3.mhcsgo.cloud/mpips-dev-bucket/{object_key}",
        "https://s3.mhcsgo.cloud/mpips-dev-bucket/wrong/path?X-Amz-Signature=1",
    ]:
        bad_sealed = seal_presigned_upload_handoff(
            upload_id=upload_id,
            object_key=object_key,
            upload_url=bad_url,
            expires_at=expires_at,
            recipient_pubkey_b64=pub_b64,
        )
        with pytest.raises(GateBTransactionError, match="upload_url failed"):
            unseal_and_validate_upload_handoff(
                bad_sealed,
                recipient_private_key=priv_key,
                expected_upload_id=upload_id,
                now=now,
            )

    # 6. Local binary hash mismatch or size mismatch fails before PUT upload
    synthetic_bin = tmp_path / "mpips-runtime.bin"
    payload = b"\x7fELF" + b"SYNTHETIC-GATE-B-TEST-PAYLOAD" * 32
    synthetic_bin.write_bytes(payload)
    actual_sha = hashlib.sha256(payload).hexdigest()
    actual_size = len(payload)

    put_calls: list[tuple[str, int]] = []

    def mock_put_uploader(
        url: str, path: Path, size: int, timeout: float
    ) -> tuple[int, str]:
        put_calls.append((url, size))
        return 200, ""

    with pytest.raises(GateBTransactionError, match="SHA-256 mismatch"):
        decrypt_and_upload_candidate_elf(
            sealed_handoff=sealed,
            recipient_private_key=priv_key,
            expected_upload_id=upload_id,
            binary_path=synthetic_bin,
            expected_sha256="f" * 64,
            expected_size_bytes=actual_size,
            now=now,
            put_uploader=mock_put_uploader,
        )
    assert put_calls == []

    # 7. Valid decryption + hash check + PUT succeeds without printing query
    res = decrypt_and_upload_candidate_elf(
        sealed_handoff=sealed,
        recipient_private_key=priv_key,
        expected_upload_id=upload_id,
        binary_path=synthetic_bin,
        expected_sha256=actual_sha,
        expected_size_bytes=actual_size,
        now=now,
        put_uploader=mock_put_uploader,
    )
    assert len(put_calls) == 1
    assert put_calls[0] == (secret_presigned_url, actual_size)
    assert res["http_status"] == 200
    assert "supersecretpresignedsig" not in json.dumps(res)
    assert res["sanitized_endpoint"] == (
        f"https://s3.mhcsgo.cloud/mpips-dev-bucket/{object_key}"
    )

    # Verify log-line extraction helper and CLI error redaction
    log_wrapped = "2026-11-10T08:00:00Z SEALED_UPLOAD_HANDOFF_JSON=" + json.dumps(
        sealed
    )
    assert parse_sealed_handoff_text(log_wrapped) == sealed

    handoff_file = tmp_path / "sealed.txt"
    handoff_file.write_text(log_wrapped, encoding="utf-8")
    exit_code = upload_client_main(
        [
            "upload",
            "--private-key",
            str(priv_path),
            "--sealed-handoff-file",
            str(handoff_file),
            "--upload-id",
            upload_id,
            "--binary",
            str(synthetic_bin),
            "--expected-sha256",
            "0" * 64,
            "--expected-size-bytes",
            str(actual_size),
        ]
    )
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "supersecretpresignedsig" not in captured.out
    assert "supersecretpresignedsig" not in captured.err
