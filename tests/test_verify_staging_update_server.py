"""Unit and integration tests for scripts/verify_staging_update_server.py."""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mpips.update_server.release_metadata import (
    canonical_metadata_bytes,
    create_elf_release_metadata,
    encode_signature_b64,
    sign_metadata_bytes,
)
from scripts.verify_staging_update_server import run_checks

TEST_TOKEN = "valid-staging-test-token"


@pytest.fixture
def ed25519_keys() -> tuple[bytes, bytes]:
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_pem, pub_pem


@pytest.fixture
def synthetic_binary(tmp_path: Path) -> tuple[Path, bytes, str, int]:
    bin_path = tmp_path / "mpips-runtime.bin"
    payload = b"\x7fELF\x02\x01\x01\x00" + (b"TEST-STANDALONE-ELF-DATA-" * 64)
    bin_path.write_bytes(payload)
    sha256_digest = hashlib.sha256(payload).hexdigest()
    size_bytes = len(payload)
    return bin_path, payload, sha256_digest, size_bytes


class MockServerState:
    def __init__(self) -> None:
        self.health_status = 200
        self.health_data = {
            "status": "ok",
            "service": "mpips-update-server",
            "environment": "staging",
        }
        self.release_status = "no_release"
        self.latest_override: dict[str, Any] | None = None
        self.download_override_status: int | None = None
        self.binary_payload: bytes = b""
        self.presigned_path = "/presigned/mpips-runtime.bin"


def make_mock_handler(state: MockServerState) -> type[BaseHTTPRequestHandler]:
    class MockUpdateHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            # Silence server request logging during tests
            pass

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            auth = self.headers.get("Authorization", "")

            # 1. Health
            if path == "/mpips/staging/health":
                self.send_response(state.health_status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(state.health_data).encode("utf-8"))
                return

            # 2. Latest
            if path == "/mpips/staging/latest.json":
                if not auth or not auth.startswith("Bearer "):
                    self._send_json(
                        401, {"schema_version": 1, "error": {"code": "unauthorized"}}
                    )
                    return
                token = auth[7:].strip()
                if token != TEST_TOKEN:
                    self._send_json(
                        401, {"schema_version": 1, "error": {"code": "unauthorized"}}
                    )
                    return

                platform = query.get("platform", ["ubuntu-24.04-x86_64"])[0]
                if platform != "ubuntu-24.04-x86_64":
                    self._send_json(
                        422,
                        {
                            "schema_version": 1,
                            "error": {"code": "incompatible_platform"},
                        },
                    )
                    return

                if state.latest_override is not None:
                    self._send_json(200, state.latest_override)
                    return

                if state.release_status == "no_release":
                    self._send_json(
                        200,
                        {
                            "schema_version": 1,
                            "channel": "staging",
                            "status": "no_release",
                        },
                    )
                    return

            # 3. Download endpoint
            if path.startswith("/mpips/staging/releases/") and path.endswith(
                "/download"
            ):
                parts = path.split("/")
                release_id = parts[4] if len(parts) >= 5 else ""
                if not auth or not auth.startswith("Bearer "):
                    self._send_json(
                        401, {"schema_version": 1, "error": {"code": "unauthorized"}}
                    )
                    return
                token = auth[7:].strip()
                if token != TEST_TOKEN:
                    self._send_json(
                        401, {"schema_version": 1, "error": {"code": "unauthorized"}}
                    )
                    return

                if state.download_override_status is not None:
                    self._send_json(
                        state.download_override_status,
                        {"schema_version": 1, "error": {"code": "download_error"}},
                    )
                    return

                if release_id == "nonexistent-release-xyz":
                    self._send_json(
                        404,
                        {"schema_version": 1, "error": {"code": "release_not_found"}},
                    )
                    return

                # Issue presigned URL pointing to local server
                server_addr = self.server.server_address
                host = str(server_addr[0])  # type: ignore[index]
                port = int(server_addr[1])  # type: ignore[index]
                download_url = f"http://{host}:{port}{state.presigned_path}"
                self._send_json(
                    200,
                    {
                        "release_id": release_id,
                        "download_url": download_url,
                        "expires_at": (
                            datetime.now(timezone.utc) + timedelta(minutes=5)
                        ).isoformat(),
                    },
                )
                return

            # 4. Presigned binary download
            if path == state.presigned_path:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(state.binary_payload)))
                self.end_headers()
                self.wfile.write(state.binary_payload)
                return

            self._send_json(404, {"error": "not_found"})

        def _send_json(self, status: int, data: dict[str, Any]) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

    return MockUpdateHandler


@pytest.fixture
def mock_server() -> Any:
    state = MockServerState()
    handler = make_mock_handler(state)
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url, state
    server.shutdown()


def _build_manifest(
    bin_path: Path,
    priv_pem: bytes,
    *,
    release_id: str = "0.1.0-20261102-1",
    sequence: int = 1,
    source_commit: str = "6976961e9bf6a3e1631180bc56a6e9de1da4840b",
    expires_delta: timedelta = timedelta(days=7),
) -> dict[str, Any]:
    metadata = create_elf_release_metadata(
        binary_path=bin_path,
        release_id=release_id,
        version="0.1.0",
        sequence=sequence,
        source_commit=source_commit,
        expires_at=datetime.now(timezone.utc) + expires_delta,
    )
    meta_bytes = canonical_metadata_bytes(metadata)
    sig_bytes = sign_metadata_bytes(meta_bytes, priv_pem)
    sig_b64 = encode_signature_b64(sig_bytes)
    meta_b64 = base64.b64encode(meta_bytes).decode("ascii")

    return {
        "schema_version": 1,
        "channel": "staging",
        "status": "available",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": release_id,
        "version": "0.1.0",
        "sequence": sequence,
        "source_commit": source_commit,
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": metadata["artifact"]["sha256"],
            "size_bytes": metadata["artifact"]["size_bytes"],
        },
        "download_endpoint": f"/mpips/staging/releases/{release_id}/download",
        "signature": sig_b64,
        "release_status": "staging",
        "expires_at": metadata["expires_at"],
        "compatibility": metadata["compatibility"],
        "signed_metadata_b64": meta_b64,
    }


def test_infra_mode_succeeds_when_no_release(mock_server: Any) -> None:
    base_url, state = mock_server
    state.release_status = "no_release"

    assert run_checks(base_url, TEST_TOKEN, mode="infra") is True


def test_distribution_mode_fails_when_no_release(mock_server: Any) -> None:
    base_url, state = mock_server
    state.release_status = "no_release"

    # In distribution readiness mode, 'no_release' is not sufficient
    # and must fail closed.
    assert run_checks(base_url, TEST_TOKEN, mode="distribution") is False


def test_available_release_with_valid_binary_succeeds_in_both_modes(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, sha256_val, size_val = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    # Test infra mode with public key
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is True
    )

    # Test distribution mode with public key
    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is True
    )


def test_fails_closed_when_sha256_corrupted(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    # Tamper with the binary payload by appending extra byte
    state.binary_payload = bin_bytes + b"\x00"
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )


def test_fails_closed_when_signature_invalid(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    manifest = _build_manifest(bin_path, priv_pem)
    # Corrupt the signature
    corrupt_sig = b"\x00" * 64
    manifest["signature"] = base64.b64encode(corrupt_sig).decode("ascii")
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )


def test_fails_closed_when_metadata_expired(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    manifest = _build_manifest(bin_path, priv_pem)
    # Set expires_at to the past
    manifest["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).isoformat()
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )


def test_fails_closed_when_unexpected_status(mock_server: Any) -> None:
    base_url, state = mock_server
    state.latest_override = {
        "schema_version": 1,
        "channel": "staging",
        "status": "unexpected_status_xyz",
    }

    assert run_checks(base_url, TEST_TOKEN, mode="infra") is False


def test_fails_closed_when_health_endpoint_fails(mock_server: Any) -> None:
    base_url, state = mock_server
    state.health_status = 503
    state.health_data = {"status": "error", "error": "database_down"}

    assert run_checks(base_url, TEST_TOKEN, mode="infra") is False


def test_fails_closed_when_missing_artifact_structure(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, _ = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    manifest = _build_manifest(bin_path, priv_pem)
    # Remove 'artifact' object
    del manifest["artifact"]
    state.latest_override = manifest

    assert run_checks(base_url, TEST_TOKEN, mode="infra") is False
