"""Signed ELF release metadata creation and Ed25519 verification."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

SUPPORTED_CHANNEL = "staging"
SUPPORTED_PLATFORM = "ubuntu-24.04-x86_64"
INTERFACE_VERSION = "2-experimental"
ARTIFACT_FILENAME = "mpips-runtime.bin"
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024  # 512 MiB upper bound

RELEASE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
COMMIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9._-]+)?\Z")
GLIBC_RE = re.compile(r"[0-9]+(?:\.[0-9]+)+\Z")

SIGNED_METADATA_KEYS = frozenset(
    {
        "schema_version",
        "channel",
        "platform",
        "release_id",
        "version",
        "sequence",
        "source_commit",
        "interface_version",
        "artifact",
        "release_status",
        "expires_at",
        "compatibility",
    }
)


def sha256_file(path: Path) -> str:
    """Compute lowercase hex SHA-256 digest of a file."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_metadata_bytes(metadata: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 canonical JSON bytes with trailing newline."""
    subset = {k: metadata[k] for k in SIGNED_METADATA_KEYS if k in metadata}
    return (json.dumps(subset, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def default_ubuntu_2404_compatibility(glibc_min: str = "2.39") -> dict[str, str]:
    """Return canonical compatibility descriptor for Ubuntu 24.04 x86_64."""
    return {
        "os": "ubuntu",
        "os_version": "24.04",
        "architecture": "x86_64",
        "glibc_min": glibc_min,
    }


def validate_platform_compatibility(
    platform_name: str,
    compatibility: Any | None = None,
) -> None:
    """Validate target platform and optional compatibility block."""
    if platform_name != SUPPORTED_PLATFORM:
        raise ValueError(f"Unsupported platform: {platform_name!r}")
    if compatibility is None:
        return
    if not isinstance(compatibility, dict) or set(compatibility) != {
        "os",
        "os_version",
        "architecture",
        "glibc_min",
    }:
        raise ValueError("Invalid compatibility metadata")
    if (
        compatibility.get("os") != "ubuntu"
        or compatibility.get("os_version") != "24.04"
        or compatibility.get("architecture") != "x86_64"
        or not isinstance(compatibility.get("glibc_min"), str)
        or not GLIBC_RE.fullmatch(compatibility["glibc_min"])
    ):
        raise ValueError("Incompatible platform target")


def create_elf_release_metadata(
    *,
    binary_path: Path,
    release_id: str,
    version: str,
    sequence: int,
    source_commit: str,
    expires_at: datetime,
    channel: str = SUPPORTED_CHANNEL,
    platform_name: str = SUPPORTED_PLATFORM,
    interface_version: str = INTERFACE_VERSION,
    release_status: str = SUPPORTED_CHANNEL,
    compatibility: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Construct and validate canonical ELF release metadata from an artifact file."""
    if not binary_path.is_file():
        raise ValueError("Artifact file does not exist")
    size_bytes = binary_path.stat().st_size
    if size_bytes <= 0 or size_bytes > MAX_ARTIFACT_BYTES:
        raise ValueError("Invalid artifact size")
    digest = sha256_file(binary_path)
    compat = (
        dict(compatibility)
        if compatibility is not None
        else default_ubuntu_2404_compatibility()
    )
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "channel": channel,
        "platform": platform_name,
        "release_id": release_id,
        "version": version,
        "sequence": sequence,
        "source_commit": source_commit,
        "interface_version": interface_version,
        "artifact": {
            "filename": ARTIFACT_FILENAME,
            "sha256": digest,
            "size_bytes": size_bytes,
        },
        "release_status": release_status,
        "expires_at": expires_at.isoformat(),
        "compatibility": compat,
    }
    validate_elf_metadata_structure(metadata)
    return metadata


def validate_elf_metadata_structure(
    metadata: Any,
    *,
    now: datetime | None = None,
    minimum_sequence: int = 1,
) -> dict[str, Any]:
    """Validate structure, constraints, and expiration of ELF release metadata."""
    if not isinstance(metadata, dict):
        raise ValueError("Release metadata must be a JSON object")
    if set(metadata) != SIGNED_METADATA_KEYS:
        raise ValueError("Release metadata keys do not match canonical schema")
    if metadata.get("schema_version") != 1:
        raise ValueError("Unsupported schema_version")
    if metadata.get("channel") != SUPPORTED_CHANNEL:
        raise ValueError("Unsupported release channel")
    if metadata.get("release_status") != SUPPORTED_CHANNEL:
        raise ValueError("Release is not authorized for staging distribution")
    if metadata.get("interface_version") != INTERFACE_VERSION:
        raise ValueError("Unsupported interface_version")

    release_id = metadata.get("release_id")
    if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
        raise ValueError("Invalid release_id")

    version = metadata.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise ValueError("Invalid runtime version")

    sequence = metadata.get("sequence")
    if type(sequence) is not int or sequence < max(1, minimum_sequence):
        raise ValueError("Invalid or replayed release sequence")

    source_commit = metadata.get("source_commit")
    if not isinstance(source_commit, str) or not COMMIT_SHA_RE.fullmatch(source_commit):
        raise ValueError("Invalid source_commit SHA")

    platform_name = metadata.get("platform")
    if not isinstance(platform_name, str):
        raise ValueError("Invalid platform")
    validate_platform_compatibility(platform_name, metadata.get("compatibility"))

    expires_raw = metadata.get("expires_at")
    if not isinstance(expires_raw, str):
        raise ValueError("Invalid expires_at")
    try:
        expires_at = datetime.fromisoformat(expires_raw)
    except ValueError as exc:
        raise ValueError("Malformed expires_at timestamp") from exc
    if expires_at.tzinfo is None:
        raise ValueError("Timezone-aware expires_at required")
    ref_now = now or datetime.now(timezone.utc)
    if expires_at <= ref_now:
        raise ValueError("Release metadata has expired")

    artifact = metadata.get("artifact")
    if not isinstance(artifact, dict) or set(artifact) != {
        "filename",
        "sha256",
        "size_bytes",
    }:
        raise ValueError("Invalid artifact descriptor")
    if artifact.get("filename") != ARTIFACT_FILENAME:
        raise ValueError("Invalid artifact filename")
    sha256_val = artifact.get("sha256")
    if not isinstance(sha256_val, str) or not SHA256_RE.fullmatch(sha256_val):
        raise ValueError("Invalid artifact sha256")
    size_bytes = artifact.get("size_bytes")
    if (
        type(size_bytes) is not int
        or size_bytes <= 0
        or size_bytes > MAX_ARTIFACT_BYTES
    ):
        raise ValueError("Invalid artifact size_bytes")

    return metadata


def load_ed25519_private_key(pem_bytes: bytes) -> Ed25519PrivateKey:
    """Load and validate an Ed25519 private key from PEM bytes."""
    key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Ed25519 private key required")
    return key


def load_ed25519_public_key(pem_bytes: bytes) -> Ed25519PublicKey:
    """Load and validate an Ed25519 public key from PEM bytes."""
    key = serialization.load_pem_public_key(pem_bytes)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Ed25519 public key required")
    return key


def sign_metadata_bytes(metadata_bytes: bytes, private_key_pem: bytes) -> bytes:
    """Sign exact metadata bytes with an Ed25519 private key (returns 64 raw bytes)."""
    private_key = load_ed25519_private_key(private_key_pem)
    return private_key.sign(metadata_bytes)


def verify_elf_release_metadata(
    metadata_bytes: bytes,
    signature_bytes: bytes,
    public_key_pem: bytes,
    *,
    binary_path: Path | None = None,
    minimum_sequence: int = 1,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify Ed25519 detached signature over exact metadata bytes and parse schema."""
    if len(signature_bytes) != 64:
        raise ValueError("Invalid Ed25519 signature length")
    public_key = load_ed25519_public_key(public_key_pem)
    try:
        public_key.verify(signature_bytes, metadata_bytes)
    except InvalidSignature as exc:
        raise ValueError("Ed25519 signature verification failed") from exc

    try:
        parsed = json.loads(metadata_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON in signed metadata") from exc

    validated = validate_elf_metadata_structure(
        parsed,
        now=now,
        minimum_sequence=minimum_sequence,
    )
    if canonical_metadata_bytes(validated) != metadata_bytes:
        raise ValueError("Metadata bytes are not in canonical serialized form")

    if binary_path is not None:
        if not binary_path.is_file():
            raise ValueError("Artifact binary missing")
        actual_size = binary_path.stat().st_size
        actual_sha256 = sha256_file(binary_path)
        artifact = validated["artifact"]
        if actual_size != artifact["size_bytes"] or actual_sha256 != artifact["sha256"]:
            raise ValueError("Artifact binary integrity mismatch")

    return validated


def encode_signature_b64(signature_bytes: bytes) -> str:
    """Encode raw 64-byte Ed25519 signature as ASCII base64."""
    if len(signature_bytes) != 64:
        raise ValueError("Ed25519 signature must be 64 bytes")
    return base64.b64encode(signature_bytes).decode("ascii")


def decode_signature_b64(signature_b64: str) -> bytes:
    """Decode ASCII base64 Ed25519 signature into raw 64 bytes."""
    try:
        raw = base64.b64decode(signature_b64.encode("ascii"), validate=True)
    except Exception as exc:
        raise ValueError("Malformed base64 signature") from exc
    if len(raw) != 64:
        raise ValueError("Decoded Ed25519 signature must be 64 bytes")
    return raw
