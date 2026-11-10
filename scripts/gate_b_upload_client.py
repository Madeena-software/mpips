"""WSL operator client for Gate B ephemeral X25519 handoff and ELF PUT upload."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
import http.client
import json
import os
from pathlib import Path
import ssl
import sys
from typing import Any, Callable
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mpips.update_server.gate_b import (
    APPROVED_CANDIDATE_SHA256,
    APPROVED_CANDIDATE_SIZE_BYTES,
    DEFAULT_TRUSTED_STORAGE_HOSTS,
    DecryptedUploadHandoff,
    GateBTransactionError,
    unseal_and_validate_upload_handoff,
)
from mpips.update_server.release_metadata import SHA256_RE, sha256_file

SEALED_PREFIX = "SEALED_UPLOAD_HANDOFF_JSON="


def _sanitize_endpoint(url_str: str) -> str:
    """Return scheme, host, and path without query parameters or credentials."""
    try:
        parsed = urlsplit(url_str)
        if not parsed.scheme or not parsed.hostname:
            return "[invalid-url]"
        port_part = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{parsed.hostname}{port_part}{parsed.path}"
    except Exception:
        return "[invalid-url]"


def generate_ephemeral_keypair(private_key_path: Path) -> dict[str, str]:
    """Generate a fresh X25519 keypair, saving the private key with 0600 mode."""
    private_key_path = private_key_path.resolve()
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    if private_key_path.exists():
        raise GateBTransactionError(
            f"Refusing to overwrite existing private key file: {private_key_path}"
        )

    priv = X25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(pub_raw).decode("ascii")

    fd = os.open(
        str(private_key_path),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(fd, "wb") as stream:
        stream.write(priv_pem)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(private_key_path, 0o600)

    return {
        "action": "generated_ephemeral_x25519_keypair",
        "private_key_path": str(private_key_path),
        "handoff_recipient_pubkey_b64": pub_b64,
    }


def load_ephemeral_private_key(private_key_path: Path) -> X25519PrivateKey:
    """Load an X25519 private key from a local 0600 PEM file."""
    if not private_key_path.is_file():
        raise GateBTransactionError(
            f"Ephemeral private key file does not exist: {private_key_path}"
        )
    mode = private_key_path.stat().st_mode & 0o777
    if mode & 0o077:
        raise GateBTransactionError(
            f"Private key file {private_key_path} has insecure permissions "
            f"({oct(mode)}); expected 0o600"
        )
    try:
        loaded = serialization.load_pem_private_key(
            private_key_path.read_bytes(),
            password=None,
        )
    except Exception as exc:
        raise GateBTransactionError("Failed to load X25519 private key PEM") from exc
    if not isinstance(loaded, X25519PrivateKey):
        raise GateBTransactionError("Loaded private key is not an X25519PrivateKey")
    return loaded


def parse_sealed_handoff_text(raw_text: str) -> dict[str, Any]:
    """Extract and parse a sealed handoff JSON object from text or log output."""
    text = raw_text.strip()
    if not text:
        raise GateBTransactionError("Sealed handoff input is empty")

    candidate = text
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if SEALED_PREFIX in stripped:
            idx = stripped.index(SEALED_PREFIX) + len(SEALED_PREFIX)
            candidate = stripped[idx:].strip()
            break

    try:
        parsed = json.loads(candidate)
    except Exception as exc:
        raise GateBTransactionError("Invalid JSON in sealed handoff input") from exc
    if not isinstance(parsed, dict):
        raise GateBTransactionError("Sealed handoff must decode to a JSON object")
    return parsed


def verify_local_candidate_binary(
    binary_path: Path,
    *,
    expected_sha256: str = APPROVED_CANDIDATE_SHA256,
    expected_size_bytes: int = APPROVED_CANDIDATE_SIZE_BYTES,
) -> dict[str, Any]:
    """Verify local ELF binary existence, exact byte size, and full SHA-256."""
    if not binary_path.is_file():
        raise GateBTransactionError(f"Candidate binary does not exist: {binary_path}")
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256):
        raise GateBTransactionError("Invalid expected_sha256 format")
    if type(expected_size_bytes) is not int or expected_size_bytes <= 0:
        raise GateBTransactionError("Invalid expected_size_bytes")

    actual_size = binary_path.stat().st_size
    if actual_size != expected_size_bytes:
        raise GateBTransactionError(
            f"Candidate binary size mismatch: expected {expected_size_bytes}, "
            f"observed {actual_size}"
        )

    actual_sha256 = sha256_file(binary_path)
    if actual_sha256 != expected_sha256:
        raise GateBTransactionError(
            f"Candidate binary SHA-256 mismatch: expected {expected_sha256}, "
            f"observed {actual_sha256}"
        )

    return {
        "binary_path": str(binary_path),
        "size_bytes": actual_size,
        "sha256": actual_sha256,
    }


def _default_https_put_Upload(
    upload_url: str,
    binary_path: Path,
    expected_size_bytes: int,
    timeout: float,
) -> tuple[int, str]:
    """Stream binary over HTTPS PUT using stdlib http.client without logging URL."""
    parsed = urlsplit(upload_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise GateBTransactionError("Upload URL must use HTTPS with a valid hostname")

    port = parsed.port or 443
    request_target = parsed.path
    if parsed.query:
        request_target = f"{parsed.path}?{parsed.query}"

    context = ssl.create_default_context()
    conn = http.client.HTTPSConnection(
        parsed.hostname,
        port=port,
        timeout=timeout,
        context=context,
    )
    try:
        conn.putrequest("PUT", request_target)
        conn.putheader("Content-Type", "application/octet-stream")
        conn.putheader("Content-Length", str(expected_size_bytes))
        conn.endheaders()

        bytes_sent = 0
        with binary_path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                conn.send(chunk)
                bytes_sent += len(chunk)

        if bytes_sent != expected_size_bytes:
            raise GateBTransactionError(
                f"Incomplete local stream read during upload: sent {bytes_sent} "
                f"of {expected_size_bytes} bytes"
            )

        response = conn.getresponse()
        body_preview = response.read(512).decode("utf-8", errors="replace")
        return response.status, body_preview
    except GateBTransactionError:
        raise
    except Exception as exc:
        sanitized = _sanitize_endpoint(upload_url)
        raise GateBTransactionError(
            f"HTTPS PUT transfer to {sanitized} failed: {type(exc).__name__}"
        ) from exc
    finally:
        conn.close()


def decrypt_and_upload_candidate_elf(
    *,
    sealed_handoff: dict[str, Any],
    recipient_private_key: X25519PrivateKey,
    expected_upload_id: str,
    binary_path: Path,
    expected_sha256: str = APPROVED_CANDIDATE_SHA256,
    expected_size_bytes: int = APPROVED_CANDIDATE_SIZE_BYTES,
    trusted_storage_hosts: set[str] | frozenset[str] | None = None,
    now: datetime | None = None,
    timeout: float = 300.0,
    put_uploader: Callable[[str, Path, int, float], tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """Decrypt sealed handoff, verify local ELF, and stream PUT to MinIO."""
    decrypted: DecryptedUploadHandoff = unseal_and_validate_upload_handoff(
        sealed_handoff,
        recipient_private_key=recipient_private_key,
        expected_upload_id=expected_upload_id,
        trusted_storage_hosts=trusted_storage_hosts,
        now=now,
    )

    verified_bin = verify_local_candidate_binary(
        binary_path,
        expected_sha256=expected_sha256,
        expected_size_bytes=expected_size_bytes,
    )

    uploader = put_uploader or _default_https_put_Upload
    status_code, _ = uploader(
        decrypted.upload_url,
        binary_path,
        expected_size_bytes,
        timeout,
    )
    if status_code not in {200, 201, 204}:
        sanitized = _sanitize_endpoint(decrypted.upload_url)
        raise GateBTransactionError(
            f"MinIO presigned PUT to {sanitized} failed with HTTP {status_code}"
        )

    return {
        "action": "uploaded_candidate_elf_to_staging_prefix",
        "upload_id": decrypted.upload_id,
        "object_key": decrypted.object_key,
        "sanitized_endpoint": _sanitize_endpoint(decrypted.upload_url),
        "expires_at": decrypted.expires_at,
        "size_bytes": verified_bin["size_bytes"],
        "sha256": verified_bin["sha256"],
        "http_status": status_code,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    keygen_p = subparsers.add_parser(
        "keygen",
        help="Generate ephemeral X25519 keypair for Gate B presigned PUT handoff",
    )
    keygen_p.add_argument(
        "--private-key-out",
        type=Path,
        required=True,
        help="Local path to write 0600 X25519 private key PEM (keep outside repo)",
    )

    upload_p = subparsers.add_parser(
        "upload",
        help="Decrypt sealed presigned PUT handoff, verify local ELF, and upload",
    )
    upload_p.add_argument(
        "--private-key",
        type=Path,
        required=True,
        help="Local 0600 X25519 private key PEM path",
    )
    upload_p.add_argument(
        "--sealed-handoff-file",
        type=Path,
        required=True,
        help="File containing SEALED_UPLOAD_HANDOFF_JSON (or '-' for stdin)",
    )
    upload_p.add_argument(
        "--upload-id",
        required=True,
        help="Expected upload_id matching gate-b-transaction.json",
    )
    upload_p.add_argument(
        "--binary",
        type=Path,
        default=Path("/home/faliq/projects/mpips/dist-experimental/mpips-runtime.bin"),
        help="Path to candidate mpips-runtime.bin",
    )
    upload_p.add_argument(
        "--expected-sha256",
        default=APPROVED_CANDIDATE_SHA256,
        help="Expected SHA-256 hex digest of candidate ELF",
    )
    upload_p.add_argument(
        "--expected-size-bytes",
        type=int,
        default=APPROVED_CANDIDATE_SIZE_BYTES,
        help="Expected size in bytes of candidate ELF",
    )
    upload_p.add_argument(
        "--trusted-storage-host",
        action="append",
        dest="trusted_storage_hosts",
        help="Trusted storage hostname (default: s3.mhcsgo.cloud)",
    )
    upload_p.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="HTTPS PUT upload timeout in seconds (default: 300)",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            result = generate_ephemeral_keypair(args.private_key_out)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        priv_key = load_ephemeral_private_key(args.private_key)
        if str(args.sealed_handoff_file) == "-":
            raw_handoff_text = sys.stdin.read()
        else:
            if not args.sealed_handoff_file.is_file():
                raise GateBTransactionError(
                    f"Sealed handoff file not found: {args.sealed_handoff_file}"
                )
            raw_handoff_text = args.sealed_handoff_file.read_text(encoding="utf-8")

        sealed = parse_sealed_handoff_text(raw_handoff_text)
        hosts = (
            frozenset(args.trusted_storage_hosts)
            if args.trusted_storage_hosts
            else DEFAULT_TRUSTED_STORAGE_HOSTS
        )
        upload_result = decrypt_and_upload_candidate_elf(
            sealed_handoff=sealed,
            recipient_private_key=priv_key,
            expected_upload_id=args.upload_id,
            binary_path=args.binary,
            expected_sha256=args.expected_sha256,
            expected_size_bytes=args.expected_size_bytes,
            trusted_storage_hosts=hosts,
            timeout=args.timeout,
        )
        print(json.dumps(upload_result, indent=2, sort_keys=True))
        return 0
    except GateBTransactionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
