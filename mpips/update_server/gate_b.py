"""Gate B non-secret transaction configuration, tag routing, and sealed handoff."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from mpips.update_server.minio_adapter import build_staging_upload_object_key
from mpips.update_server.release_metadata import (
    COMMIT_SHA_RE,
    MAX_ARTIFACT_BYTES,
    RELEASE_ID_RE,
    SHA256_RE,
    SUPPORTED_CHANNEL,
    SUPPORTED_PLATFORM,
    VERSION_RE,
)

GATE_B_OPERATIONS = frozenset(
    {
        "preflight_inspect",
        "prepare_elf_upload",
        "publish_staged_elf",
    }
)

TAG_PREFIX_TO_OPERATION: dict[str, str] = {
    "gate-b-preflight-": "preflight_inspect",
    "gate-b-prepare-upload-": "prepare_elf_upload",
    "gate-b-publish-": "publish_staged_elf",
}

GATE_B_TAG_RE = re.compile(
    r"^(?:refs/tags/)?"
    r"(?P<prefix>gate-b-(?:preflight|prepare-upload|publish)-)"
    r"(?P<suffix>[0-9]{8}-[0-9]{4})\Z"
)

HANDOFF_HKDF_INFO = b"mpips-gate-b-presigned-put-handoff-v1"
DEFAULT_TRUSTED_STORAGE_HOSTS = frozenset({"s3.mhcsgo.cloud"})
APPROVED_CANDIDATE_SHA256 = (
    "189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937"
)
APPROVED_CANDIDATE_SIZE_BYTES = 241288024
APPROVED_SOURCE_COMMIT = "cbf2b24ba4fb8f2b5fc25b6a86f381ba7cf5f4b1"
APPROVED_BUCKET = "mpips-dev-bucket"

ALLOWED_TRANSACTION_KEYS = frozenset(
    {
        "schema_version",
        "operation",
        "channel",
        "platform",
        "bucket",
        "upload_id",
        "handoff_recipient_pubkey_b64",
        "target_release_id",
        "version",
        "expected_current_sequence",
        "target_sequence",
        "expected_sha256",
        "expected_size_bytes",
        "source_commit",
    }
)

ALLOWED_SEALED_HANDOFF_KEYS = frozenset(
    {
        "schema_version",
        "upload_id",
        "object_key",
        "expires_at",
        "ephemeral_pubkey_b64",
        "nonce_b64",
        "ciphertext_b64",
    }
)

ALLOWED_DECRYPTED_HANDOFF_KEYS = frozenset(
    {
        "upload_id",
        "object_key",
        "upload_url",
        "expires_at",
    }
)


class GateBTransactionError(ValueError):
    """Validation failure for Gate B transaction config, tag routing, or handoff."""


@dataclass(frozen=True)
class GateBTransactionConfig:
    """Validated non-secret Gate B transaction configuration."""

    schema_version: int
    operation: str
    channel: str
    platform: str
    bucket: str
    upload_id: str
    handoff_recipient_pubkey_b64: str
    target_release_id: str
    version: str
    expected_current_sequence: int | None
    target_sequence: int | None
    expected_sha256: str
    expected_size_bytes: int
    source_commit: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation,
            "channel": self.channel,
            "platform": self.platform,
            "bucket": self.bucket,
            "upload_id": self.upload_id,
            "handoff_recipient_pubkey_b64": self.handoff_recipient_pubkey_b64,
            "target_release_id": self.target_release_id,
            "version": self.version,
            "expected_current_sequence": self.expected_current_sequence,
            "target_sequence": self.target_sequence,
            "expected_sha256": self.expected_sha256,
            "expected_size_bytes": self.expected_size_bytes,
            "source_commit": self.source_commit,
        }


@dataclass(frozen=True)
class DecryptedUploadHandoff:
    """Validated decrypted presigned PUT descriptor."""

    upload_id: str
    object_key: str
    upload_url: str
    expires_at: str


def resolve_operation_from_git_tag(tag_or_ref: str) -> str:
    """Strictly map a Gate B Git tag or ref to its single permitted operation."""
    if not isinstance(tag_or_ref, str):
        raise GateBTransactionError("Git tag or ref must be a string")
    match = GATE_B_TAG_RE.fullmatch(tag_or_ref.strip())
    if match is None:
        raise GateBTransactionError(
            f"Unsupported or malformed Gate B tag: {tag_or_ref!r}"
        )
    prefix = match.group("prefix")
    return TAG_PREFIX_TO_OPERATION[prefix]


def validate_x25519_pubkey_b64(pubkey_b64: str) -> bytes:
    """Decode and validate a base64-encoded 32-byte raw X25519 public key."""
    if not isinstance(pubkey_b64, str) or not pubkey_b64.strip():
        raise GateBTransactionError("X25519 public key base64 must be non-empty")
    token = pubkey_b64.strip()
    try:
        raw = base64.b64decode(token.encode("ascii"), validate=True)
    except Exception as exc:
        raise GateBTransactionError("Malformed base64 for X25519 public key") from exc
    if len(raw) != 32 or base64.b64encode(raw).decode("ascii") != token:
        raise GateBTransactionError(
            "X25519 public key must be canonical base64 of 32 raw bytes"
        )
    if raw == b"\x00" * 32:
        raise GateBTransactionError("All-zero X25519 public key is forbidden")
    try:
        X25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        raise GateBTransactionError("Invalid X25519 public key bytes") from exc
    return raw


def parse_and_validate_transaction_config(
    raw: dict[str, Any],
    *,
    git_tag: str | None = None,
) -> GateBTransactionConfig:
    """Validate non-secret Gate B transaction config and optional tag consistency."""
    if not isinstance(raw, dict):
        raise GateBTransactionError("Transaction configuration must be a JSON object")

    unknown_keys = set(raw) - ALLOWED_TRANSACTION_KEYS
    if unknown_keys:
        raise GateBTransactionError(
            f"Unexpected keys in transaction configuration: {sorted(unknown_keys)}"
        )
    missing_keys = ALLOWED_TRANSACTION_KEYS - set(raw)
    if missing_keys:
        raise GateBTransactionError(
            "Missing required keys in transaction configuration: "
            f"{sorted(missing_keys)}"
        )

    schema_version = raw.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise GateBTransactionError("schema_version must be integer 1")

    operation = raw.get("operation")
    if not isinstance(operation, str) or operation not in GATE_B_OPERATIONS:
        raise GateBTransactionError(f"Invalid Gate B operation: {operation!r}")

    if git_tag is not None:
        tag_operation = resolve_operation_from_git_tag(git_tag)
        if tag_operation != operation:
            raise GateBTransactionError(
                f"Git tag operation ({tag_operation!r}) does not match "
                f"transaction config operation ({operation!r})"
            )

    channel = raw.get("channel")
    if channel != SUPPORTED_CHANNEL:
        raise GateBTransactionError(f"Unsupported channel: {channel!r}")

    platform_name = raw.get("platform")
    if platform_name != SUPPORTED_PLATFORM:
        raise GateBTransactionError(f"Unsupported platform: {platform_name!r}")

    bucket = raw.get("bucket")
    if bucket != APPROVED_BUCKET:
        raise GateBTransactionError(f"Unsupported bucket: {bucket!r}")

    version = raw.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise GateBTransactionError("Invalid semantic version in transaction config")

    expected_sha256 = raw.get("expected_sha256")
    if (
        not isinstance(expected_sha256, str)
        or not SHA256_RE.fullmatch(expected_sha256)
        or expected_sha256 != APPROVED_CANDIDATE_SHA256
    ):
        raise GateBTransactionError(
            "expected_sha256 must match the approved Gate B ELF digest"
        )

    expected_size_bytes = raw.get("expected_size_bytes")
    if (
        type(expected_size_bytes) is not int
        or expected_size_bytes <= 0
        or expected_size_bytes > MAX_ARTIFACT_BYTES
        or expected_size_bytes != APPROVED_CANDIDATE_SIZE_BYTES
    ):
        raise GateBTransactionError(
            "expected_size_bytes must match the approved Gate B ELF byte size"
        )

    source_commit = raw.get("source_commit")
    if (
        not isinstance(source_commit, str)
        or not COMMIT_SHA_RE.fullmatch(source_commit)
        or source_commit != APPROVED_SOURCE_COMMIT
    ):
        raise GateBTransactionError(
            "source_commit must match the approved Gate B source artifact commit"
        )

    upload_id = raw.get("upload_id")
    if not isinstance(upload_id, str):
        raise GateBTransactionError("upload_id must be a string")
    upload_id = upload_id.strip()

    pubkey_b64 = raw.get("handoff_recipient_pubkey_b64")
    if not isinstance(pubkey_b64, str):
        raise GateBTransactionError("handoff_recipient_pubkey_b64 must be a string")
    pubkey_b64 = pubkey_b64.strip()

    target_release_id = raw.get("target_release_id")
    if not isinstance(target_release_id, str):
        raise GateBTransactionError("target_release_id must be a string")
    target_release_id = target_release_id.strip()

    exp_cur_seq = raw.get("expected_current_sequence")
    if exp_cur_seq is not None and (type(exp_cur_seq) is not int or exp_cur_seq < 0):
        raise GateBTransactionError(
            "expected_current_sequence must be null or a non-negative integer"
        )

    target_seq = raw.get("target_sequence")
    if target_seq is not None and (type(target_seq) is not int or target_seq < 1):
        raise GateBTransactionError(
            "target_sequence must be null or a positive integer >= 1"
        )

    if upload_id and not RELEASE_ID_RE.fullmatch(upload_id):
        raise GateBTransactionError("Malformed upload_id")
    if target_release_id and not RELEASE_ID_RE.fullmatch(target_release_id):
        raise GateBTransactionError("Malformed target_release_id")
    if pubkey_b64:
        validate_x25519_pubkey_b64(pubkey_b64)

    if exp_cur_seq is not None and target_seq is not None:
        if target_seq <= exp_cur_seq:
            raise GateBTransactionError(
                "target_sequence must strictly exceed expected_current_sequence"
            )

    if operation == "prepare_elf_upload":
        if not upload_id:
            raise GateBTransactionError(
                "upload_id is required when operation is 'prepare_elf_upload'"
            )
        if not pubkey_b64:
            raise GateBTransactionError(
                "handoff_recipient_pubkey_b64 is required when operation is "
                "'prepare_elf_upload'"
            )

    if operation == "publish_staged_elf":
        if not upload_id:
            raise GateBTransactionError(
                "upload_id is required when operation is 'publish_staged_elf'"
            )
        if not target_release_id:
            raise GateBTransactionError(
                "target_release_id is required when operation is 'publish_staged_elf'"
            )
        if exp_cur_seq is None or target_seq is None:
            raise GateBTransactionError(
                "expected_current_sequence and target_sequence are required "
                "when operation is 'publish_staged_elf'"
            )

    return GateBTransactionConfig(
        schema_version=schema_version,
        operation=operation,
        channel=channel,
        platform=platform_name,
        bucket=bucket,
        upload_id=upload_id,
        handoff_recipient_pubkey_b64=pubkey_b64,
        target_release_id=target_release_id,
        version=version,
        expected_current_sequence=exp_cur_seq,
        target_sequence=target_seq,
        expected_sha256=expected_sha256,
        expected_size_bytes=expected_size_bytes,
        source_commit=source_commit,
    )


def load_transaction_config(
    path: Path,
    *,
    git_tag: str | None = None,
) -> GateBTransactionConfig:
    """Load and validate Gate B transaction config from a JSON file."""
    if not path.is_file():
        raise GateBTransactionError(f"Transaction config file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateBTransactionError("Invalid JSON in transaction config file") from exc
    return parse_and_validate_transaction_config(raw, git_tag=git_tag)


def verify_live_sequence_expectations(
    config: GateBTransactionConfig,
    *,
    live_current_sequence: int,
    live_highest_allocated_sequence: int,
    registered_release_ids: set[str] | frozenset[str],
    candidate_sha256_already_promoted: bool = False,
) -> None:
    """Verify live registry sequence state matches publish_staged_elf expectations."""
    if config.operation != "publish_staged_elf":
        raise GateBTransactionError(
            "Live sequence publication check requires operation='publish_staged_elf'"
        )
    if candidate_sha256_already_promoted:
        raise GateBTransactionError(
            "Candidate ELF SHA-256 is already promoted on staging channel; "
            "refusing duplicate publication"
        )
    if config.target_release_id in registered_release_ids:
        raise GateBTransactionError(
            f"target_release_id {config.target_release_id!r} is already registered"
        )
    if config.expected_current_sequence != live_current_sequence:
        raise GateBTransactionError(
            f"Stale expected_current_sequence={config.expected_current_sequence} "
            f"(live current_promoted_sequence={live_current_sequence})"
        )
    expected_next_seq = live_highest_allocated_sequence + 1
    if config.target_sequence != expected_next_seq:
        raise GateBTransactionError(
            f"Stale target_sequence={config.target_sequence} "
            f"(expected highest_allocated_sequence + 1 = {expected_next_seq})"
        )


def seal_presigned_upload_handoff(
    *,
    upload_id: str,
    object_key: str,
    upload_url: str,
    expires_at: str,
    recipient_pubkey_b64: str,
    ephemeral_private_key: X25519PrivateKey | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    """Seal a presigned PUT URL using X25519 + HKDF-SHA256 + ChaCha20Poly1305."""
    if not isinstance(upload_id, str) or not RELEASE_ID_RE.fullmatch(upload_id):
        raise GateBTransactionError("Invalid upload_id for sealed handoff")
    expected_key = build_staging_upload_object_key(upload_id)
    if object_key != expected_key:
        raise GateBTransactionError("object_key does not match upload_id")

    peer_pub_raw = validate_x25519_pubkey_b64(recipient_pubkey_b64)
    peer_pub = X25519PublicKey.from_public_bytes(peer_pub_raw)

    eph_priv = ephemeral_private_key or X25519PrivateKey.generate()
    eph_pub_raw = eph_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    shared_secret = eph_priv.exchange(peer_pub)
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=eph_pub_raw + peer_pub_raw,
        info=HANDOFF_HKDF_INFO,
    ).derive(shared_secret)

    iv = nonce if nonce is not None else os.urandom(12)
    if len(iv) != 12:
        raise GateBTransactionError("ChaCha20Poly1305 nonce must be 12 bytes")

    plaintext = json.dumps(
        {
            "upload_id": upload_id,
            "object_key": object_key,
            "upload_url": upload_url,
            "expires_at": expires_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    ciphertext = ChaCha20Poly1305(derived_key).encrypt(
        iv,
        plaintext,
        upload_id.encode("utf-8"),
    )
    return {
        "schema_version": 1,
        "upload_id": upload_id,
        "object_key": object_key,
        "expires_at": expires_at,
        "ephemeral_pubkey_b64": base64.b64encode(eph_pub_raw).decode("ascii"),
        "nonce_b64": base64.b64encode(iv).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }


def unseal_and_validate_upload_handoff(
    sealed: dict[str, Any],
    *,
    recipient_private_key: X25519PrivateKey,
    expected_upload_id: str,
    trusted_storage_hosts: set[str] | frozenset[str] | None = None,
    now: datetime | None = None,
) -> DecryptedUploadHandoff:
    """Decrypt and validate a sealed presigned PUT handoff."""
    if not isinstance(sealed, dict) or set(sealed) != ALLOWED_SEALED_HANDOFF_KEYS:
        raise GateBTransactionError("Invalid sealed handoff structure")
    if type(sealed.get("schema_version")) is not int or sealed["schema_version"] != 1:
        raise GateBTransactionError("Unsupported sealed handoff schema_version")
    if not isinstance(expected_upload_id, str) or not RELEASE_ID_RE.fullmatch(
        expected_upload_id
    ):
        raise GateBTransactionError("Invalid expected_upload_id")

    outer_upload_id = sealed.get("upload_id")
    if outer_upload_id != expected_upload_id:
        raise GateBTransactionError(
            "Sealed handoff upload_id does not match expected_upload_id"
        )
    expected_object_key = build_staging_upload_object_key(expected_upload_id)
    if sealed.get("object_key") != expected_object_key:
        raise GateBTransactionError(
            "Sealed handoff object_key does not match expected staging upload prefix"
        )

    eph_pub_raw = validate_x25519_pubkey_b64(
        str(sealed.get("ephemeral_pubkey_b64", ""))
    )
    eph_pub = X25519PublicKey.from_public_bytes(eph_pub_raw)

    try:
        nonce = base64.b64decode(
            str(sealed.get("nonce_b64", "")).encode("ascii"), validate=True
        )
        ciphertext = base64.b64decode(
            str(sealed.get("ciphertext_b64", "")).encode("ascii"), validate=True
        )
    except Exception as exc:
        raise GateBTransactionError("Invalid base64 in sealed handoff") from exc

    if len(nonce) != 12 or len(ciphertext) < 16:
        raise GateBTransactionError("Malformed nonce or ciphertext in sealed handoff")

    recip_pub_raw = recipient_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    shared_secret = recipient_private_key.exchange(eph_pub)
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=eph_pub_raw + recip_pub_raw,
        info=HANDOFF_HKDF_INFO,
    ).derive(shared_secret)

    try:
        plaintext = ChaCha20Poly1305(derived_key).decrypt(
            nonce,
            ciphertext,
            expected_upload_id.encode("utf-8"),
        )
    except InvalidTag as exc:
        raise GateBTransactionError(
            "Sealed handoff decryption failed (key mismatch or tampered ciphertext)"
        ) from exc

    try:
        inner = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:
        raise GateBTransactionError(
            "Decrypted handoff payload is not valid JSON"
        ) from exc

    if not isinstance(inner, dict) or set(inner) != ALLOWED_DECRYPTED_HANDOFF_KEYS:
        raise GateBTransactionError("Decrypted handoff payload has invalid keys")
    if inner.get("upload_id") != expected_upload_id:
        raise GateBTransactionError("Decrypted upload_id mismatch")
    if inner.get("object_key") != expected_object_key:
        raise GateBTransactionError("Decrypted object_key mismatch")
    if inner.get("expires_at") != sealed.get("expires_at"):
        raise GateBTransactionError("Decrypted expires_at mismatch with outer envelope")

    expires_at_str = str(inner["expires_at"])
    try:
        expires_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateBTransactionError("Invalid expires_at timestamp in handoff") from exc
    if expires_dt.tzinfo is None:
        raise GateBTransactionError("expires_at timestamp must be timezone-aware")

    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if expires_dt <= ref_now:
        raise GateBTransactionError("Presigned upload URL has already expired")

    upload_url = str(inner["upload_url"])
    parsed = urlsplit(upload_url)
    allowed_hosts = trusted_storage_hosts or DEFAULT_TRUSTED_STORAGE_HOSTS
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or hostname not in {h.lower() for h in allowed_hosts}
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.query
        or not parsed.path.endswith(f"/{expected_object_key}")
    ):
        raise GateBTransactionError(
            "Decrypted upload_url failed HTTPS/host/path/query validation"
        )

    return DecryptedUploadHandoff(
        upload_id=expected_upload_id,
        object_key=expected_object_key,
        upload_url=upload_url,
        expires_at=expires_at_str,
    )
