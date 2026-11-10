"""Unit and integration tests for scripts/verify_staging_update_server.py."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
import urllib.request
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
from scripts.verify_staging_update_server import (
    MAX_PERMITTED_ARTIFACT_BYTES,
    main as verifier_main,
    run_checks,
)

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
        self.download_url_override: str | None = None
        self.binary_payload: bytes = b""
        self.presigned_path = "/presigned/mpips-runtime.bin"
        self.redirect_target: str | None = None
        self.download_endpoint_requests: list[str] = []
        self.binary_download_requests: list[str] = []


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
                state.download_endpoint_requests.append(path)
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

                # Issue presigned URL pointing to local server or override
                if state.download_url_override is not None:
                    download_url = state.download_url_override
                else:
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
                state.binary_download_requests.append(path)
                if state.redirect_target is not None:
                    self.send_response(302)
                    self.send_header("Location", state.redirect_target)
                    self.end_headers()
                    return

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


def test_infra_mode_succeeds_when_valid_no_release(mock_server: Any) -> None:
    base_url, state = mock_server
    state.release_status = "no_release"

    assert run_checks(base_url, TEST_TOKEN, mode="infra") is True


def test_distribution_mode_fails_when_no_release(mock_server: Any) -> None:
    base_url, state = mock_server
    state.release_status = "no_release"

    # In distribution readiness mode, 'no_release' is not sufficient
    # and must fail closed.
    assert run_checks(base_url, TEST_TOKEN, mode="distribution") is False


def test_fails_closed_when_no_release_has_extraneous_or_invalid_fields(
    mock_server: Any,
) -> None:
    base_url, state = mock_server
    # Extra unexpected key in no_release
    state.latest_override = {
        "schema_version": 1,
        "channel": "staging",
        "status": "no_release",
        "unexpected_extra_key": "malformed",
    }
    assert run_checks(base_url, TEST_TOKEN, mode="infra") is False

    # Wrong channel in no_release
    state.latest_override = {
        "schema_version": 1,
        "channel": "production",
        "status": "no_release",
    }
    assert run_checks(base_url, TEST_TOKEN, mode="infra") is False


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

    # Test infra mode with valid public key
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is True
    )

    # Test distribution mode with valid public key
    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is True
    )


def test_fails_closed_when_available_without_public_key(
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
    state.latest_override = manifest

    # Available release without public key must strictly fail closed in both modes
    assert run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=None) is False
    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=None)
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
    # Corrupt the signature bytes
    corrupt_sig = b"\x00" * 64
    manifest["signature"] = base64.b64encode(corrupt_sig).decode("ascii")
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )


def test_fails_closed_when_outer_metadata_tampered_against_inner_signed(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes

    # 1. Tampered sequence
    manifest1 = _build_manifest(bin_path, priv_pem)
    manifest1["sequence"] = 999  # Does not match inner sequence 1
    state.latest_override = manifest1
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )

    # 2. Tampered version
    manifest2 = _build_manifest(bin_path, priv_pem)
    manifest2["version"] = "9.9.9"
    state.latest_override = manifest2
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )

    # 3. Tampered source commit
    manifest3 = _build_manifest(bin_path, priv_pem)
    manifest3["source_commit"] = "0" * 40
    state.latest_override = manifest3
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )

    # 4. Tampered artifact SHA in outer manifest
    manifest4 = _build_manifest(bin_path, priv_pem)
    manifest4["artifact"]["sha256"] = "a" * 64
    state.latest_override = manifest4
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )


def test_fails_closed_when_wrong_channel_or_platform(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes

    # Wrong platform
    manifest = _build_manifest(bin_path, priv_pem)
    manifest["platform"] = "windows-x86_64"
    state.latest_override = manifest
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )

    # Wrong channel
    manifest_ch = _build_manifest(bin_path, priv_pem)
    manifest_ch["channel"] = "production"
    state.latest_override = manifest_ch
    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )


def test_fails_closed_when_malformed_download_endpoint(
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
    # Malformed download endpoint path
    manifest["download_endpoint"] = "/unauthorized/download/path"
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )


def test_fails_closed_when_download_redirects(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    state.redirect_target = "http://127.0.0.1/redirected-target"
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    # StrictNoRedirectHandler must block any HTTP redirect
    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )


def test_fails_closed_when_download_host_insecure_non_loopback(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    # Presigned URL points to insecure HTTP non-loopback destination
    state.download_url_override = (
        "http://insecure-external-server.example.com/mpips-runtime.bin"
    )
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )


def test_fails_closed_when_artifact_oversized(
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
    # Manifest declares size exceeding MAX_PERMITTED_ARTIFACT_BYTES
    manifest["artifact"]["size_bytes"] = MAX_PERMITTED_ARTIFACT_BYTES + 1
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="infra", public_key_pem=pub_pem) is False
    )


def test_fails_closed_when_stream_exceeds_declared_size(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    # Actual binary payload is longer than declared in manifest
    state.binary_payload = bin_bytes + (b"EXTRA_APPENDED_BYTES" * 1024)
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
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
    # Tamper with byte content without changing length
    corrupted_payload = bytearray(bin_bytes)
    corrupted_payload[0] = 0x00
    state.binary_payload = bytes(corrupted_payload)
    manifest = _build_manifest(bin_path, priv_pem)
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


def test_invalid_manifest_causes_zero_artifact_download_requests(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes

    # 1. Invalid signature
    manifest = _build_manifest(bin_path, priv_pem)
    manifest["signature"] = base64.b64encode(b"0" * 64).decode("ascii")
    state.latest_override = manifest
    state.download_endpoint_requests.clear()
    state.binary_download_requests.clear()

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )
    assert len(state.download_endpoint_requests) == 0
    assert len(state.binary_download_requests) == 0

    # 2. Tampered outer field
    manifest = _build_manifest(bin_path, priv_pem)
    manifest["version"] = "9.9.9"
    state.latest_override = manifest
    state.download_endpoint_requests.clear()
    state.binary_download_requests.clear()

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )
    assert len(state.download_endpoint_requests) == 0
    assert len(state.binary_download_requests) == 0

    # 3. Expired metadata
    manifest = _build_manifest(bin_path, priv_pem)
    manifest["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()
    state.latest_override = manifest
    state.download_endpoint_requests.clear()
    state.binary_download_requests.clear()

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )
    assert len(state.download_endpoint_requests) == 0
    assert len(state.binary_download_requests) == 0

    # 4. Malformed download endpoint path
    manifest = _build_manifest(bin_path, priv_pem)
    manifest["download_endpoint"] = "/unexpected/malformed/download/path"
    state.latest_override = manifest
    state.download_endpoint_requests.clear()
    state.binary_download_requests.clear()

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )
    assert len(state.download_endpoint_requests) == 0
    assert len(state.binary_download_requests) == 0


def test_fails_closed_when_download_host_unauthorized_https(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    # HTTPS destination that is not in the trusted storage allowlist
    state.download_url_override = (
        "https://unauthorized-s3.malicious.com/mpips-runtime.bin"
    )
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is False
    )


def test_accepts_explicitly_trusted_storage_host(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    trusted_host = "custom-test-storage.example.com"
    state.download_url_override = f"https://{trusted_host}/mpips-runtime.bin"
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    class MockStreamingResponse:
        def __init__(self, data: bytes):
            self._bio = io.BytesIO(data)

        def read(self, size: int = -1) -> bytes:
            return self._bio.read(size)

        def __enter__(self) -> MockStreamingResponse:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    original_open = urllib.request.OpenerDirector.open

    def custom_open(self: Any, *args: Any, **kwargs: Any) -> Any:
        req = args[0] if args else kwargs.get("fullurl")
        url = str(getattr(req, "full_url", req))
        if "mpips-runtime.bin" in url:
            return MockStreamingResponse(bin_bytes)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr("urllib.request.OpenerDirector.open", custom_open)

    # Rejection when trusted_host is not provided in trusted_storage_hosts
    assert (
        run_checks(
            base_url,
            TEST_TOKEN,
            mode="distribution",
            public_key_pem=pub_pem,
            trusted_storage_hosts=["other-host.example.com"],
        )
        is False
    )

    # Acceptance when trusted_host is explicitly passed
    assert (
        run_checks(
            base_url,
            TEST_TOKEN,
            mode="distribution",
            public_key_pem=pub_pem,
            trusted_storage_hosts=[trusted_host],
        )
        is True
    )


def test_accepts_default_trusted_storage_host(
    mock_server: Any,
    ed25519_keys: tuple[bytes, bytes],
    synthetic_binary: tuple[Path, bytes, str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url, state = mock_server
    priv_pem, pub_pem = ed25519_keys
    bin_path, bin_bytes, _, _ = synthetic_binary

    state.release_status = "available"
    state.binary_payload = bin_bytes
    state.download_url_override = "https://s3.mhcsgo.cloud/mpips-runtime.bin"
    manifest = _build_manifest(bin_path, priv_pem)
    state.latest_override = manifest

    class MockStreamingResponse:
        def __init__(self, data: bytes):
            self._bio = io.BytesIO(data)

        def read(self, size: int = -1) -> bytes:
            return self._bio.read(size)

        def __enter__(self) -> MockStreamingResponse:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    original_open = urllib.request.OpenerDirector.open

    def custom_open(self: Any, *args: Any, **kwargs: Any) -> Any:
        req = args[0] if args else kwargs.get("fullurl")
        url = str(getattr(req, "full_url", req))
        if "mpips-runtime.bin" in url:
            return MockStreamingResponse(bin_bytes)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr("urllib.request.OpenerDirector.open", custom_open)

    # Acceptance of default s3.mhcsgo.cloud without explicit argument
    assert (
        run_checks(base_url, TEST_TOKEN, mode="distribution", public_key_pem=pub_pem)
        is True
    )


def test_verifier_main_does_not_fallback_to_mpips_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure verify_staging_update_server.main requires dedicated reader token."""
    monkeypatch.delenv("MPIPS_UPDATE_STAGING_READER_TOKEN", raising=False)
    monkeypatch.setenv("MPIPS_API_KEY", "clinical-api-key-must-not-be-used")
    monkeypatch.setattr("sys.argv", ["verify_staging_update_server.py"])

    assert verifier_main() == 1
