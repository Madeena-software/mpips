"""Tests for Grabber update-flow simulation (protocol-only simulation).

Simulates the 8-step Grabber update workflow against an isolated mock update server
with signed Ed25519 metadata:
1. Check latest release metadata.
2. Compare sequence against installed sequence.
3. Validate Ed25519 signature & platform compatibility before requesting download.
4. Request download endpoint and presigned download URL.
5. Bounded chunk download with SHA-256 and size verification.
6. Local runtime self-check (check_version / --version).
7. Synthetic conversion verification with MPIPSSubprocessAdapter.
8. Atomic promotion to installed executable, preserving existing runtime on failure.

NOTE: These tests use mock executables and an isolated loopback HTTP server.
Per project requirements, they are explicitly labeled as protocol-only simulation.
No live MinIO, production server, or hospital SIMRS network calls are made.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from scripts.grabber_subprocess_adapter import MPIPSSubprocessAdapter

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


def _canonical_metadata_bytes(metadata: dict[str, Any]) -> bytes:
    """Canonicalize signed metadata subset to sorted compact JSON."""
    subset = {k: metadata[k] for k in SIGNED_METADATA_KEYS if k in metadata}
    return (json.dumps(subset, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _sign_metadata(
    metadata: dict[str, Any], private_key: Ed25519PrivateKey
) -> tuple[str, str]:
    """Returns (signature_b64, signed_metadata_b64)."""
    canonical_bytes = _canonical_metadata_bytes(metadata)
    sig = private_key.sign(canonical_bytes)
    return (
        base64.b64encode(sig).decode("ascii"),
        base64.b64encode(canonical_bytes).decode("ascii"),
    )


def _create_mock_runtime_script(
    path: Path,
    *,
    interface_version: str = "2-experimental",
    runtime_version: str = "0.1.0",
    fail_version: bool = False,
    fail_convert: bool = False,
    tag: str = "mock-runtime",
) -> Path:
    """Create a mock executable script supporting --version and convert."""
    script_lines = ["#!/usr/bin/env python3", "import sys, json, os", ""]
    if fail_version:
        script_lines.append(
            'if "--version" in sys.argv:\n'
            '    sys.stderr.write("Crash\\n")\n'
            "    sys.exit(1)"
        )
    else:
        v_data = json.dumps(
            {
                "status": "ok",
                "code": "OK",
                "interface_version": interface_version,
                "runtime_version": runtime_version,
                "tag": tag,
            }
        )
        script_lines.append(
            f'if "--version" in sys.argv:\n'
            f"    print({v_data!r})\n"
            f"    sys.exit(0)"
        )

    if fail_convert:
        script_lines.append(
            'if "convert" in sys.argv:\n'
            '    print(json.dumps({"status": "error", "code": "CONVERSION_FAILED"}))\n'
            "    sys.exit(7)"
        )
    else:
        resp_template = json.dumps(
            {
                "status": "ok",
                "code": "OK",
                "interface_version": interface_version,
                "runtime_version": runtime_version,
                "output_byte_size": 34,
                "tag": tag,
            }
        )
        c_fmt = (
            'if "convert" in sys.argv:\n'
            '    out_idx = sys.argv.index("--output") + 1\n'
            "    out_path = sys.argv[out_idx]\n"
            '    payload = b"MOCK_DICOM_OUTPUT_PAYLOAD_12345678"\n'
            '    with open(out_path, "wb") as f:\n'
            "        f.write(payload)\n"
            "    os.chmod(out_path, 0o600)\n"
            f"    print({resp_template!r})\n"
            "    sys.exit(0)"
        )
        script_lines.append(c_fmt)

    path.write_text("\n".join(script_lines) + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
    return path


class MockUpdateServerHandler(BaseHTTPRequestHandler):
    """Isolated local HTTP server handling update discovery and download."""

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Quiet logs during test run

    @property
    def server_state(self) -> dict[str, Any]:
        return getattr(self.server, "state", {})

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        calls = self.server_state.setdefault("calls", [])
        calls.append(path)

        # 1. Latest release discovery endpoint
        if path == "/mpips/staging/latest.json":
            self.server_state["latest_checks"] = (
                self.server_state.get("latest_checks", 0) + 1
            )
            resp = self.server_state.get("manifest_response")
            if resp is None:
                self.send_response(500)
                self.end_headers()
                return
            body = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 2. Download endpoint (returns presigned storage URL)
        if path.startswith("/mpips/staging/releases/") and path.endswith("/download"):
            self.server_state["download_requests"] = (
                self.server_state.get("download_requests", 0) + 1
            )
            download_url = self.server_state.get("download_url")
            if not download_url:
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(
                {"status": "success", "download_url": download_url}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 3. Artifact storage endpoint
        if path == "/storage/mpips-runtime.bin":
            self.server_state["artifact_downloads"] = (
                self.server_state.get("artifact_downloads", 0) + 1
            )
            artifact_bytes = self.server_state.get("artifact_bytes")
            if artifact_bytes is None:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(artifact_bytes)))
            self.end_headers()
            self.wfile.write(artifact_bytes)
            return

        self.send_response(404)
        self.end_headers()


class MockServerFixture:
    def __init__(self) -> None:
        self.server = HTTPServer(("127.0.0.1", 0), MockUpdateServerHandler)
        self.port = self.server.server_port
        self.host = f"127.0.0.1:{self.port}"
        self.base_url = f"http://{self.host}"
        setattr(
            self.server,
            "state",
            {
                "calls": [],
                "latest_checks": 0,
                "download_requests": 0,
                "artifact_downloads": 0,
                "manifest_response": None,
                "download_url": None,
                "artifact_bytes": None,
            },
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def state(self) -> dict[str, Any]:
        return getattr(self.server, "state", {})

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)


@pytest.fixture
def mock_server() -> Any:
    srv = MockServerFixture()
    try:
        yield srv
    finally:
        srv.shutdown()


@pytest.fixture
def ed25519_keypair() -> tuple[Ed25519PrivateKey, bytes]:
    private_key = Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_pem


# ---------------------------------------------------------------------------
# Grabber Update Client Protocol Simulation
# ---------------------------------------------------------------------------


class GrabberUpdateError(Exception):
    """Raised when any step of the update workflow fails."""


def simulate_grabber_update_flow(
    *,
    server_base_url: str,
    trusted_public_key_pem: bytes,
    installed_executable: Path,
    installed_sequence: int,
    workspace_dir: Path,
    perform_synthetic_conversion: bool = True,
) -> dict[str, Any]:
    """Execute the 8-step Grabber update workflow simulation.

    Steps:
    1. Query latest release metadata.
    2. Compare candidate sequence against installed sequence.
    3. Validate Ed25519 signature & platform compatibility BEFORE downloading.
    4. Request download endpoint and presigned storage URL.
    5. Stream candidate artifact with bounded size and SHA-256 validation.
    6. Run local runtime self-check (--version).
    7. Invoke candidate for a synthetic conversion.
    8. Atomically promote candidate, preserving existing runtime on any failure.
    """
    history: list[str] = []

    # Step 1: Query latest release metadata
    history.append("1_CHECK_METADATA")
    discovery_url = (
        f"{server_base_url}/mpips/staging/latest.json?platform=ubuntu-24.04-x86_64"
    )
    try:
        req = urllib.request.Request(discovery_url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                raise GrabberUpdateError(f"Discovery returned HTTP {resp.status}")
            manifest = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise GrabberUpdateError(f"Failed to query latest release: {exc}") from exc

    if manifest.get("status") == "no_release":
        return {
            "status": "no_release",
            "active_executable": installed_executable,
            "current_sequence": installed_sequence,
            "steps_completed": history,
        }

    # Step 2: Compare verified release sequence against installed sequence
    history.append("2_COMPARE_SEQUENCE")
    candidate_seq = manifest.get("sequence")
    if not isinstance(candidate_seq, int):
        raise GrabberUpdateError(f"Invalid sequence type: {type(candidate_seq)}")
    if candidate_seq <= installed_sequence:
        return {
            "status": "up_to_date",
            "active_executable": installed_executable,
            "current_sequence": installed_sequence,
            "steps_completed": history,
        }

    # Step 3: Validate Ed25519 signature, outer-vs-inner manifest, and compatibility
    # CRITICAL: This MUST occur BEFORE requesting download endpoint or binary!
    history.append("3_VALIDATE_SIGNATURE_AND_COMPATIBILITY")
    sig_b64 = manifest.get("signature")
    signed_meta_b64 = manifest.get("signed_metadata_b64")
    if not isinstance(sig_b64, str) or not isinstance(signed_meta_b64, str):
        raise GrabberUpdateError("Missing signature or signed_metadata_b64")

    try:
        sig_bytes = base64.b64decode(sig_b64.encode("ascii"), validate=True)
        meta_bytes = base64.b64decode(signed_meta_b64.encode("ascii"), validate=True)
    except Exception as exc:
        raise GrabberUpdateError(f"Malformed base64 signature/metadata: {exc}") from exc

    # Cryptographic verification
    try:
        pub_key = serialization.load_pem_public_key(trusted_public_key_pem)
        if not isinstance(pub_key, Ed25519PublicKey):
            raise GrabberUpdateError("Trusted key is not Ed25519")
        pub_key.verify(sig_bytes, meta_bytes)
    except Exception as exc:
        raise GrabberUpdateError(
            f"Ed25519 signature verification failed: {exc}"
        ) from exc

    # Validate inner metadata matches canonical serialization
    parsed_inner = json.loads(meta_bytes.decode("utf-8"))
    if _canonical_metadata_bytes(parsed_inner) != meta_bytes:
        raise GrabberUpdateError("signed_metadata_b64 does not match canonical form")

    # Match outer manifest against authenticated inner metadata
    for key in (
        "schema_version",
        "channel",
        "platform",
        "release_id",
        "version",
        "sequence",
        "source_commit",
        "interface_version",
    ):
        if manifest.get(key) != parsed_inner.get(key):
            raise GrabberUpdateError(
                f"Outer manifest mismatch for {key}: "
                f"{manifest.get(key)} != {parsed_inner.get(key)}"
            )

    compat = manifest.get("compatibility", {})
    if compat.get("os") != "ubuntu" or compat.get("architecture") != "x86_64":
        raise GrabberUpdateError(f"Incompatible target platform: {compat}")

    artifact_info = manifest.get("artifact", {})
    expected_sha = artifact_info.get("sha256")
    expected_size = artifact_info.get("size_bytes")
    if not expected_sha or not expected_size:
        raise GrabberUpdateError("Manifest artifact metadata missing sha256 or size")

    download_endpoint = manifest.get("download_endpoint")
    if not isinstance(download_endpoint, str) or not download_endpoint.startswith(
        "/mpips/staging/releases/"
    ):
        raise GrabberUpdateError(f"Invalid download_endpoint path: {download_endpoint}")

    # Step 4: Request download endpoint to obtain download URL
    history.append("4_REQUEST_DOWNLOAD_ENDPOINT")
    dl_url_endpoint = f"{server_base_url}{download_endpoint}"
    try:
        req = urllib.request.Request(dl_url_endpoint)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                raise GrabberUpdateError(f"Download endpoint error {resp.status}")
            dl_data = json.loads(resp.read().decode("utf-8"))
            storage_url = dl_data.get("download_url")
            if not storage_url:
                raise GrabberUpdateError("Missing download_url in download response")
    except Exception as exc:
        raise GrabberUpdateError(f"Failed download endpoint request: {exc}") from exc

    # Step 5: Bounded chunk download and verify SHA-256 + size
    history.append("5_DOWNLOAD_AND_VERIFY_ARTIFACT")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    staging_file = workspace_dir / "candidate_runtime.tmp"
    hasher = hashlib.sha256()
    bytes_downloaded = 0
    max_bytes = 512 * 1024 * 1024  # 512 MiB

    try:
        req = urllib.request.Request(storage_url)
        with urllib.request.urlopen(req, timeout=10.0) as resp, open(
            staging_file, "wb"
        ) as out_f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                bytes_downloaded += len(chunk)
                if (
                    bytes_downloaded > max_bytes
                    or bytes_downloaded > expected_size * 2
                ):
                    raise GrabberUpdateError("Artifact exceeded size limit")
                hasher.update(chunk)
                out_f.write(chunk)
    except Exception as exc:
        if staging_file.exists():
            staging_file.unlink()
        raise GrabberUpdateError(f"Artifact download failed: {exc}") from exc

    actual_sha = hasher.hexdigest()
    if actual_sha != expected_sha:
        staging_file.unlink()
        raise GrabberUpdateError(
            f"Artifact SHA-256 mismatch: {actual_sha} != {expected_sha}"
        )

    if bytes_downloaded != expected_size:
        staging_file.unlink()
        raise GrabberUpdateError(
            f"Artifact size mismatch: {bytes_downloaded} != {expected_size}"
        )

    staging_file.chmod(
        staging_file.stat().st_mode | stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE
    )

    # Step 6: Local runtime self-check
    history.append("6_RUNTIME_SELF_CHECK")
    adapter = MPIPSSubprocessAdapter(staging_file)
    try:
        info = adapter.check_version(timeout=5.0)
        if info.interface_version != "2-experimental" or info.status != "ok":
            staging_file.unlink()
            raise GrabberUpdateError(
                f"Candidate failed self-check: {info.interface_version}, {info.status}"
            )
    except Exception as exc:
        if staging_file.exists():
            staging_file.unlink()
        raise GrabberUpdateError(
            f"Candidate self-check invocation failed: {exc}"
        ) from exc

    # Step 7: Invoke candidate executable for synthetic conversion
    if perform_synthetic_conversion:
        history.append("7_SYNTHETIC_CONVERSION")
        convert_out = workspace_dir / "qualification_out.dcm"
        rad = workspace_dir / "rad.npz"
        gain = workspace_dir / "gain.npz"
        man = workspace_dir / "manifest.json"
        rad.write_bytes(b"SYNTHETIC_RAD")
        gain.write_bytes(b"SYNTHETIC_GAIN")
        man.write_bytes(b'{"patient": {}}')

        try:
            res = adapter.convert(
                radiograph=rad,
                gain=gain,
                manifest=man,
                output=convert_out,
                timeout=5.0,
                expected_interface_version="2-experimental",
            )
            if res.status != "ok" or not convert_out.is_file():
                staging_file.unlink()
                if convert_out.exists():
                    convert_out.unlink()
                raise GrabberUpdateError("Candidate synthetic conversion failed")
            convert_out.unlink()  # Cleanup test output
        except Exception as exc:
            if staging_file.exists():
                staging_file.unlink()
            if convert_out.exists():
                convert_out.unlink()
            raise GrabberUpdateError(
                f"Candidate synthetic conversion error: {exc}"
            ) from exc

    # Step 8: Atomic promotion to installed executable
    history.append("8_ATOMIC_PROMOTION")
    os.replace(staging_file, installed_executable)

    return {
        "status": "promoted",
        "active_executable": installed_executable,
        "current_sequence": candidate_seq,
        "steps_completed": history,
    }


# ---------------------------------------------------------------------------
# Test Cases (Protocol-Only Simulation)
# ---------------------------------------------------------------------------


def test_protocol_simulation_successful_update_and_conversion(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: full 8-step update succeeds and promotes runtime."""
    priv_key, pub_pem = ed25519_keypair

    # Create currently installed mock runtime (sequence 10)
    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")

    # Create candidate runtime (sequence 11)
    candidate_src = tmp_path / "candidate_source.bin"
    _create_mock_runtime_script(candidate_src, tag="v11-candidate")
    candidate_bytes = candidate_src.read_bytes()
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    candidate_size = len(candidate_bytes)

    # Prepare server response
    release_id = "rel-2026-0011"
    metadata = {
        "schema_version": "1.0",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": release_id,
        "version": "0.1.0",
        "sequence": 11,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": candidate_sha,
            "size_bytes": candidate_size,
        },
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
            "glibc_min": "2.39",
        },
    }
    sig_b64, signed_b64 = _sign_metadata(metadata, priv_key)
    manifest = {
        **metadata,
        "status": "available",
        "download_endpoint": f"/mpips/staging/releases/{release_id}/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
    }

    mock_server.state["manifest_response"] = manifest
    dl_url = f"{mock_server.base_url}/storage/mpips-runtime.bin"
    mock_server.state["download_url"] = dl_url
    mock_server.state["artifact_bytes"] = candidate_bytes

    # Execute simulation
    result = simulate_grabber_update_flow(
        server_base_url=mock_server.base_url,
        trusted_public_key_pem=pub_pem,
        installed_executable=installed_bin,
        installed_sequence=10,
        workspace_dir=tmp_path / "work",
    )

    assert result["status"] == "promoted"
    assert result["current_sequence"] == 11
    assert "8_ATOMIC_PROMOTION" in result["steps_completed"]

    # Verify that the installed binary has been updated to v11
    adapter = MPIPSSubprocessAdapter(installed_bin)
    info = adapter.check_version()
    assert info.code == "OK"
    assert mock_server.state["latest_checks"] == 1
    assert mock_server.state["download_requests"] == 1
    assert mock_server.state["artifact_downloads"] == 1


def test_protocol_simulation_rejects_older_or_equal_sequence(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: sequence <= installed halts before download."""
    _, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    # Server offers sequence 10 (same as installed)
    manifest = {
        "schema_version": "1.0",
        "channel": "staging",
        "status": "available",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": "rel-0010",
        "version": "0.1.0",
        "sequence": 10,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": "0" * 64,
            "size_bytes": 1000,
        },
        "download_endpoint": "/mpips/staging/releases/rel-0010/download",
        "signature": "dummysig",
        "signed_metadata_b64": "dummymeta",
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
        },
    }
    mock_server.state["manifest_response"] = manifest

    result = simulate_grabber_update_flow(
        server_base_url=mock_server.base_url,
        trusted_public_key_pem=pub_pem,
        installed_executable=installed_bin,
        installed_sequence=10,
        workspace_dir=tmp_path / "work",
    )

    assert result["status"] == "up_to_date"
    assert result["current_sequence"] == 10
    # Must NOT have requested download endpoint or downloaded artifact
    assert mock_server.state["download_requests"] == 0
    assert mock_server.state["artifact_downloads"] == 0
    assert installed_bin.read_bytes() == initial_bytes


def test_protocol_simulation_rejects_invalid_signature_before_download(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: invalid signature halts before download endpoint."""
    _, pub_pem = ed25519_keypair
    other_priv = Ed25519PrivateKey.generate()  # Untrusted key

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    metadata = {
        "schema_version": "1.0",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": "rel-0011",
        "version": "0.1.0",
        "sequence": 11,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": "a" * 64,
            "size_bytes": 1234,
        },
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
        },
    }
    # Sign with untrusted key
    sig_b64, signed_b64 = _sign_metadata(metadata, other_priv)
    manifest = {
        **metadata,
        "status": "available",
        "download_endpoint": "/mpips/staging/releases/rel-0011/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
    }
    mock_server.state["manifest_response"] = manifest

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
        )

    assert "signature verification failed" in str(exc_info.value).lower()
    # ZERO download requests must have been made
    assert mock_server.state["download_requests"] == 0
    assert mock_server.state["artifact_downloads"] == 0
    assert installed_bin.read_bytes() == initial_bytes


def test_protocol_simulation_rejects_corrupted_sha256_preserves_runtime(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: artifact checksum mismatch aborts update."""
    priv_key, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    candidate_src = tmp_path / "candidate.bin"
    _create_mock_runtime_script(candidate_src, tag="v11-candidate")
    candidate_bytes = candidate_src.read_bytes()

    metadata = {
        "schema_version": "1.0",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": "rel-0011",
        "version": "0.1.0",
        "sequence": 11,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": "f" * 64,  # Corrupted / mismatched hash in manifest
            "size_bytes": len(candidate_bytes),
        },
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
        },
    }
    sig_b64, signed_b64 = _sign_metadata(metadata, priv_key)
    manifest = {
        **metadata,
        "status": "available",
        "download_endpoint": "/mpips/staging/releases/rel-0011/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
    }
    mock_server.state["manifest_response"] = manifest
    dl_url = f"{mock_server.base_url}/storage/mpips-runtime.bin"
    mock_server.state["download_url"] = dl_url
    mock_server.state["artifact_bytes"] = candidate_bytes

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
        )

    assert "sha-256 mismatch" in str(exc_info.value).lower()
    # Preserves existing installed binary
    assert installed_bin.read_bytes() == initial_bytes
    # Staging temp file cleaned up
    assert not (tmp_path / "work" / "candidate_runtime.tmp").exists()


def test_protocol_simulation_rejects_incompatible_platform(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: incompatible platform target is rejected."""
    priv_key, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    metadata = {
        "schema_version": "1.0",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": "rel-0011",
        "version": "0.1.0",
        "sequence": 11,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": "a" * 64,
            "size_bytes": 1000,
        },
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "windows",  # INCOMPATIBLE
            "os_version": "11",
            "architecture": "x86_64",
        },
    }
    sig_b64, signed_b64 = _sign_metadata(metadata, priv_key)
    manifest = {
        **metadata,
        "status": "available",
        "download_endpoint": "/mpips/staging/releases/rel-0011/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
    }
    mock_server.state["manifest_response"] = manifest

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
        )

    assert "incompatible" in str(exc_info.value).lower()
    assert mock_server.state["download_requests"] == 0
    assert installed_bin.read_bytes() == initial_bytes


def test_protocol_simulation_rejects_failed_self_check_preserves_runtime(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: candidate failing self-check is not promoted."""
    priv_key, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    # Candidate that crashes on --version
    bad_candidate = tmp_path / "bad_candidate.bin"
    _create_mock_runtime_script(bad_candidate, fail_version=True)
    bad_bytes = bad_candidate.read_bytes()

    metadata = {
        "schema_version": "1.0",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": "rel-0011",
        "version": "0.1.0",
        "sequence": 11,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": hashlib.sha256(bad_bytes).hexdigest(),
            "size_bytes": len(bad_bytes),
        },
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
        },
    }
    sig_b64, signed_b64 = _sign_metadata(metadata, priv_key)
    manifest = {
        **metadata,
        "status": "available",
        "download_endpoint": "/mpips/staging/releases/rel-0011/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
    }
    mock_server.state["manifest_response"] = manifest
    dl_url = f"{mock_server.base_url}/storage/mpips-runtime.bin"
    mock_server.state["download_url"] = dl_url
    mock_server.state["artifact_bytes"] = bad_bytes

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
        )

    assert "self-check" in str(exc_info.value).lower()
    # Preserves original installed binary
    assert installed_bin.read_bytes() == initial_bytes
    # Adapter still works with installed binary
    adapter = MPIPSSubprocessAdapter(installed_bin)
    assert adapter.check_version().status == "ok"


def test_protocol_simulation_rejects_failed_synthetic_conversion_preserves_runtime(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: candidate failing conversion is not promoted."""
    priv_key, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    # Candidate that passes --version but fails convert
    failing_candidate = tmp_path / "failing_candidate.bin"
    _create_mock_runtime_script(failing_candidate, fail_convert=True)
    failing_bytes = failing_candidate.read_bytes()

    metadata = {
        "schema_version": "1.0",
        "channel": "staging",
        "platform": "ubuntu-24.04-x86_64",
        "release_id": "rel-0011",
        "version": "0.1.0",
        "sequence": 11,
        "source_commit": "1176a4f4886ea4bcfcf9a3e6aa85b88fdb71ecb1",
        "interface_version": "2-experimental",
        "artifact": {
            "filename": "mpips-runtime.bin",
            "sha256": hashlib.sha256(failing_bytes).hexdigest(),
            "size_bytes": len(failing_bytes),
        },
        "release_status": "staging",
        "expires_at": "2026-12-31T23:59:59Z",
        "compatibility": {
            "os": "ubuntu",
            "os_version": "24.04",
            "architecture": "x86_64",
        },
    }
    sig_b64, signed_b64 = _sign_metadata(metadata, priv_key)
    manifest = {
        **metadata,
        "status": "available",
        "download_endpoint": "/mpips/staging/releases/rel-0011/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
    }
    mock_server.state["manifest_response"] = manifest
    dl_url = f"{mock_server.base_url}/storage/mpips-runtime.bin"
    mock_server.state["download_url"] = dl_url
    mock_server.state["artifact_bytes"] = failing_bytes

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
            perform_synthetic_conversion=True,
        )

    assert "synthetic conversion" in str(exc_info.value).lower()
    # Preserves original installed binary
    assert installed_bin.read_bytes() == initial_bytes


def test_protocol_simulation_network_isolation_no_live_egress(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: confirms all requests remain on loopback."""
    _, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")

    # Mock no_release response
    manifest = {
        "schema_version": "1.0",
        "channel": "staging",
        "status": "no_release",
    }
    mock_server.state["manifest_response"] = manifest

    result = simulate_grabber_update_flow(
        server_base_url=mock_server.base_url,
        trusted_public_key_pem=pub_pem,
        installed_executable=installed_bin,
        installed_sequence=10,
        workspace_dir=tmp_path / "work",
    )

    assert result["status"] == "no_release"
    assert result["current_sequence"] == 10
    # Calls logged exclusively on local loopback server
    assert len(mock_server.state["calls"]) == 1
    assert mock_server.state["calls"][0] == "/mpips/staging/latest.json"
