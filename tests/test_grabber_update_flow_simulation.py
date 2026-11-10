"""Tests for Grabber update-flow simulation (protocol-only simulation).

Simulates the 8-step Grabber update workflow against an isolated mock update server
with signed Ed25519 metadata:
1. Check latest release metadata with staging-reader bearer authentication.
2. Compare sequence against installed sequence.
3. Validate Ed25519 signature, integer schema_version=1 & platform compatibility
   before requesting download.
4. Request download endpoint with staging-reader bearer authentication.
5. Bounded chunk download from presigned storage URL (without MPIPS auth header)
   with SHA-256 and size verification.
6. Local runtime self-check (check_version / --version).
7. Synthetic conversion verification with MPIPSSubprocessAdapter.
8. Atomic promotion to installed executable, preserving existing runtime on failure.

NOTE: These tests use mock executables and an isolated loopback HTTP server.
Per project requirements, they are explicitly labeled as protocol-only simulation.
No live MinIO, production server, or hospital SIMRS network calls are made.
The mock converter output is explicitly labeled as mock data, not a genuine DICOM.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pydicom
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from fastapi.testclient import TestClient

from mpips.update_server.app import create_update_server_app
from mpips.update_server.auth import STAGING_READ_SCOPE, ClientAuthenticator
from mpips.update_server.minio_adapter import MinIOArtifactStore
from mpips.update_server.registry import ReleaseRegistry
from mpips.update_server.release_metadata import (
    canonical_metadata_bytes,
    create_elf_release_metadata,
    sign_metadata_bytes,
)
from scripts.grabber_smoke import make_inputs
from scripts.grabber_subprocess_adapter import MPIPSSubprocessAdapter
from scripts.simrs_manifest_example import (
    SIMRSConfirmationRequiredError,
    parse_simrs_http_response,
)
from scripts.verify_staging_update_server import (
    DEFAULT_TRUSTED_STORAGE_HOSTS,
    LOOPBACK_HOSTS,
    StrictNoRedirectHandler,
    run_checks,
)

DEFAULT_STAGING_READER_TOKEN = "synthetic-staging-reader-token-xyz123"
REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_ELF_PATH = REPO_ROOT / "dist-experimental" / "mpips-runtime.bin"
EXPECTED_REAL_ELF_SHA256 = (
    "189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937"
)
EXPECTED_REAL_ELF_SIZE = 241288024

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
    tag: str = "protocol-only-mock-runtime",
) -> Path:
    """Create a mock executable script supporting --version and convert.

    Explicitly labeled as protocol simulation mock; output is NOT a genuine DICOM.
    """
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
        mock_payload_len = 54
        resp_template = json.dumps(
            {
                "status": "ok",
                "code": "OK",
                "interface_version": interface_version,
                "runtime_version": runtime_version,
                "output_byte_size": mock_payload_len,
                "tag": tag,
            }
        )
        c_fmt = (
            'if "convert" in sys.argv:\n'
            '    out_idx = sys.argv.index("--output") + 1\n'
            "    out_path = sys.argv[out_idx]\n"
            '    payload = b"PROTOCOL_MOCK_CONVERTER_OUTPUT_NOT_A_GENUINE_DICOM_54B"\n'
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

        # Enforce required staging reader bearer authentication on API endpoints
        if path.startswith("/mpips/staging/"):
            expected_token = self.server_state.get(
                "staging_token", DEFAULT_STAGING_READER_TOKEN
            )
            auth_header = self.headers.get("Authorization", "")
            if auth_header != f"Bearer {expected_token}":
                self.server_state["auth_failures"] = (
                    self.server_state.get("auth_failures", 0) + 1
                )
                body = json.dumps(
                    {
                        "status": "error",
                        "code": "UNAUTHORIZED",
                        "message": "Invalid or missing staging bearer token",
                    }
                ).encode("utf-8")
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

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

        # 3. Artifact storage endpoint (simulates presigned MinIO URL - NO auth header)
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
                "auth_failures": 0,
                "staging_token": DEFAULT_STAGING_READER_TOKEN,
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
    staging_token: str | None = DEFAULT_STAGING_READER_TOKEN,
    perform_synthetic_conversion: bool = True,
    trusted_storage_hosts: Iterable[str] | None = None,
    require_available_for_bootstrap: bool = False,
    download_timeout: float = 60.0,
    self_check_timeout: float = 30.0,
) -> dict[str, Any]:
    """Execute the 8-step Grabber update workflow simulation.

    Steps:
    1. Query latest release metadata with staging bearer token.
    2. Validate Ed25519 signature, integer schema_version=1, outer-vs-inner equality,
       expiry, and platform compatibility BEFORE trusting sequence or downloading.
    3. Compare authenticated candidate sequence against installed sequence.
    4. Request download endpoint with staging bearer token.
    5. Validate storage host & no-redirect policy; stream candidate artifact
       (without forwarding MPIPS auth header) with bounded size & SHA-256 checks.
    6. Run local runtime self-check (--version).
    7. Invoke candidate for a synthetic conversion when enabled.
    8. Atomically promote candidate, preserving existing runtime on any failure.
    """
    history: list[str] = []
    auth_headers = {}
    if staging_token:
        auth_headers["Authorization"] = f"Bearer {staging_token}"

    effective_storage_hosts = (
        frozenset(h.strip().lower() for h in trusted_storage_hosts if h.strip())
        if trusted_storage_hosts is not None
        else DEFAULT_TRUSTED_STORAGE_HOSTS
    )

    # Step 1: Query latest release metadata
    history.append("1_CHECK_METADATA")
    discovery_url = (
        f"{server_base_url}/mpips/staging/latest.json?platform=ubuntu-24.04-x86_64"
    )
    try:
        req = urllib.request.Request(discovery_url, headers=auth_headers)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                raise GrabberUpdateError(f"Discovery returned HTTP {resp.status}")
            manifest = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise GrabberUpdateError("Authentication failed: HTTP 401 Unauthorized")
        raise GrabberUpdateError(
            f"Failed to query latest release: HTTP {exc.code}"
        ) from exc
    except Exception as exc:
        raise GrabberUpdateError(f"Failed to query latest release: {exc}") from exc

    # Verify integer schema_version: 1 (contract requirement)
    schema_ver = manifest.get("schema_version")
    if type(schema_ver) is not int or schema_ver != 1:
        raise GrabberUpdateError(
            f"Invalid schema_version: {schema_ver!r}, expected integer 1"
        )

    if manifest.get("status") == "no_release":
        if set(manifest.keys()) != {"schema_version", "channel", "status"} or (
            manifest.get("channel") != "staging"
        ):
            raise GrabberUpdateError("Malformed no_release manifest envelope")
        if require_available_for_bootstrap or installed_sequence <= 0:
            raise GrabberUpdateError(
                "First-bootstrap requires an available release; channel reports "
                "no_release"
            )
        return {
            "status": "no_release",
            "active_executable": installed_executable,
            "current_sequence": installed_sequence,
            "steps_completed": history,
        }

    if manifest.get("status") != "available":
        raise GrabberUpdateError(
            f"Unexpected manifest status: {manifest.get('status')!r}"
        )

    # Step 2: Validate Ed25519 signature, outer-vs-inner manifest, expiry, and
    # compatibility BEFORE trusting sequence or requesting download endpoint!
    history.append("2_VALIDATE_SIGNATURE_AND_COMPATIBILITY")
    sig_b64 = manifest.get("signature")
    signed_meta_b64 = manifest.get("signed_metadata_b64")
    if not isinstance(sig_b64, str) or not isinstance(signed_meta_b64, str):
        raise GrabberUpdateError("Missing signature or signed_metadata_b64")

    try:
        sig_bytes = base64.b64decode(sig_b64.encode("ascii"), validate=True)
        meta_bytes = base64.b64decode(signed_meta_b64.encode("ascii"), validate=True)
    except Exception as exc:
        raise GrabberUpdateError(f"Malformed base64 signature/metadata: {exc}") from exc

    if len(sig_bytes) != 64:
        raise GrabberUpdateError(
            f"Ed25519 signature verification failed: expected 64 bytes, got "
            f"{len(sig_bytes)}"
        )

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

    # Match ALL signed metadata keys between outer manifest and inner metadata
    for key in SIGNED_METADATA_KEYS:
        if manifest.get(key) != parsed_inner.get(key):
            raise GrabberUpdateError(
                f"Outer manifest mismatch for {key}: "
                f"{manifest.get(key)} != {parsed_inner.get(key)}"
            )

    if (
        manifest.get("channel") != "staging"
        or manifest.get("platform") != "ubuntu-24.04-x86_64"
        or manifest.get("interface_version") != "2-experimental"
        or manifest.get("release_status") != "staging"
    ):
        raise GrabberUpdateError("Incompatible channel, platform, or interface")

    expires_at_str = manifest.get("expires_at")
    if not isinstance(expires_at_str, str):
        raise GrabberUpdateError("Missing expires_at in manifest")
    try:
        expires_dt = datetime.fromisoformat(expires_at_str)
    except ValueError as exc:
        raise GrabberUpdateError(f"Malformed expires_at: {exc}") from exc
    if expires_dt.tzinfo is None or expires_dt <= datetime.now(timezone.utc):
        raise GrabberUpdateError(f"Release metadata expired at {expires_at_str}")

    compat = manifest.get("compatibility", {})
    if (
        not isinstance(compat, dict)
        or compat.get("os") != "ubuntu"
        or compat.get("os_version") != "24.04"
        or compat.get("architecture") != "x86_64"
    ):
        raise GrabberUpdateError(f"Incompatible target platform: {compat}")

    artifact_info = manifest.get("artifact", {})
    expected_sha = artifact_info.get("sha256")
    expected_size = artifact_info.get("size_bytes")
    if (
        artifact_info.get("filename") != "mpips-runtime.bin"
        or not isinstance(expected_sha, str)
        or len(expected_sha) != 64
        or type(expected_size) is not int
        or expected_size <= 0
        or expected_size > 512 * 1024 * 1024
    ):
        raise GrabberUpdateError("Manifest artifact metadata missing or invalid")

    release_id = manifest.get("release_id")
    download_endpoint = manifest.get("download_endpoint")
    expected_dl_endpoint = f"/mpips/staging/releases/{release_id}/download"
    if not isinstance(download_endpoint, str) or (
        download_endpoint != expected_dl_endpoint
    ):
        raise GrabberUpdateError(f"Invalid download_endpoint path: {download_endpoint}")

    # Step 3: Compare verified release sequence against installed sequence
    history.append("3_COMPARE_SEQUENCE")
    candidate_seq = manifest.get("sequence")
    if type(candidate_seq) is not int or candidate_seq < 1:
        raise GrabberUpdateError(f"Invalid sequence: {candidate_seq!r}")
    if candidate_seq <= installed_sequence:
        return {
            "status": "up_to_date",
            "active_executable": installed_executable,
            "current_sequence": installed_sequence,
            "steps_completed": history,
        }

    # Step 4: Request download endpoint to obtain presigned storage URL
    history.append("4_REQUEST_DOWNLOAD_ENDPOINT")
    dl_url_endpoint = f"{server_base_url}{download_endpoint}"
    try:
        req = urllib.request.Request(dl_url_endpoint, headers=auth_headers)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                raise GrabberUpdateError(f"Download endpoint error {resp.status}")
            dl_data = json.loads(resp.read().decode("utf-8"))
            storage_url = dl_data.get("download_url")
            if not isinstance(storage_url, str) or not storage_url:
                raise GrabberUpdateError("Missing download_url in download response")
            if "release_id" in dl_data and dl_data["release_id"] != release_id:
                raise GrabberUpdateError("Download response release_id mismatch")
            if "expires_at" in dl_data:
                dl_exp = datetime.fromisoformat(str(dl_data["expires_at"]))
                if dl_exp.tzinfo is None or dl_exp <= datetime.now(timezone.utc):
                    raise GrabberUpdateError("Presigned download_url already expired")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise GrabberUpdateError(
                "Download endpoint authentication failed: HTTP 401 Unauthorized"
            )
        raise GrabberUpdateError(
            f"Failed download endpoint request: HTTP {exc.code}"
        ) from exc
    except Exception as exc:
        raise GrabberUpdateError(f"Failed download endpoint request: {exc}") from exc

    # Validate presigned storage URL host & scheme before downloading
    parsed_storage = urllib.parse.urlsplit(storage_url)
    storage_host = (parsed_storage.hostname or "").lower()
    if parsed_storage.scheme == "http":
        if storage_host not in LOOPBACK_HOSTS:
            raise GrabberUpdateError(
                f"Insecure non-loopback HTTP storage host rejected: {storage_host}"
            )
    elif parsed_storage.scheme == "https":
        if (
            storage_host not in effective_storage_hosts
            and storage_host not in LOOPBACK_HOSTS
        ):
            raise GrabberUpdateError(
                f"Untrusted HTTPS storage host rejected: {storage_host}"
            )
    else:
        raise GrabberUpdateError(
            f"Unsupported storage URL scheme: {parsed_storage.scheme}"
        )

    # Step 5: Bounded chunk download and verify SHA-256 + size
    # NOTE: Presigned storage download does NOT forward MPIPS Authorization headers
    # and strictly rejects all HTTP redirects.
    history.append("5_DOWNLOAD_AND_VERIFY_ARTIFACT")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    staging_file = workspace_dir / "candidate_runtime.tmp"
    hasher = hashlib.sha256()
    bytes_downloaded = 0
    max_bytes = 512 * 1024 * 1024  # 512 MiB
    opener = urllib.request.build_opener(StrictNoRedirectHandler())

    try:
        req = urllib.request.Request(storage_url, headers={})
        with (
            opener.open(req, timeout=download_timeout) as resp,
            open(staging_file, "wb") as out_f,
        ):
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                bytes_downloaded += len(chunk)
                if bytes_downloaded > max_bytes or bytes_downloaded > expected_size:
                    raise GrabberUpdateError("Artifact exceeded declared size limit")
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
        info = adapter.check_version(timeout=self_check_timeout)
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
        rad, gain, man, _ = make_inputs(workspace_dir / "smoke_bed", "BED")

        try:
            res = adapter.convert(
                radiograph=rad,
                gain=gain,
                manifest=man,
                output=convert_out,
                timeout=max(self_check_timeout, 60.0),
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

    # Prepare server response with integer schema_version: 1
    release_id = "rel-2026-0011"
    metadata = {
        "schema_version": 1,
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

    # Execute simulation with valid staging reader authentication
    result = simulate_grabber_update_flow(
        server_base_url=mock_server.base_url,
        trusted_public_key_pem=pub_pem,
        installed_executable=installed_bin,
        installed_sequence=10,
        workspace_dir=tmp_path / "work",
        staging_token=DEFAULT_STAGING_READER_TOKEN,
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
    assert mock_server.state["auth_failures"] == 0


def test_protocol_simulation_rejects_unauthenticated_request(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: unauthenticated request returns 401 and halts."""
    _, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
            staging_token=None,  # No authentication token
        )

    assert "401 unauthorized" in str(exc_info.value).lower()
    assert mock_server.state["auth_failures"] >= 1
    assert mock_server.state["download_requests"] == 0
    assert mock_server.state["artifact_downloads"] == 0
    assert installed_bin.read_bytes() == initial_bytes


def test_protocol_simulation_rejects_invalid_token(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: invalid bearer token returns 401 and halts."""
    _, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    with pytest.raises(GrabberUpdateError) as exc_info:
        simulate_grabber_update_flow(
            server_base_url=mock_server.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work",
            staging_token="WRONG-OR-MALICIOUS-TOKEN",
        )

    assert "401 unauthorized" in str(exc_info.value).lower()
    assert mock_server.state["auth_failures"] >= 1
    assert mock_server.state["download_requests"] == 0
    assert mock_server.state["artifact_downloads"] == 0
    assert installed_bin.read_bytes() == initial_bytes


def test_protocol_simulation_rejects_older_or_equal_sequence(
    mock_server: MockServerFixture,
    ed25519_keypair: tuple[Ed25519PrivateKey, bytes],
    tmp_path: Path,
) -> None:
    """Protocol-only simulation: sequence <= installed halts before download."""
    priv_key, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")
    initial_bytes = installed_bin.read_bytes()

    metadata = {
        "schema_version": 1,
        "channel": "staging",
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
        "download_endpoint": "/mpips/staging/releases/rel-0010/download",
        "signature": sig_b64,
        "signed_metadata_b64": signed_b64,
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
        "schema_version": 1,
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
        "schema_version": 1,
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
        "schema_version": 1,
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
        "schema_version": 1,
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
        "schema_version": 1,
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protocol-only simulation: enforces Python-level socket loopback guard.

    NOTE: This installs a Python-level `socket.create_connection` guard that
    records and allows only loopback (`127.0.0.1` / `localhost` / `::1`)
    targets and raises ` RuntimeError` on any non-loopback connection attempt.
    It distinguishes requested loopback endpoints + Python-level egress
    restriction from kernel-level network namespace isolation.
    """
    _, pub_pem = ed25519_keypair

    installed_bin = tmp_path / "installed_runtime.bin"
    _create_mock_runtime_script(installed_bin, tag="v10-existing")

    # Mock no_release response with integer schema_version: 1
    manifest = {
        "schema_version": 1,
        "channel": "staging",
        "status": "no_release",
    }
    mock_server.state["manifest_response"] = manifest

    observed_targets: list[tuple[str, int]] = []
    real_create_connection = socket.create_connection

    def _loopback_only_create_connection(
        address: tuple[str, int],
        *args: Any,
        **kwargs: Any,
    ) -> socket.socket:
        host, port = address[0], int(address[1])
        observed_targets.append((host, port))
        if host not in LOOPBACK_HOSTS:
            raise RuntimeError(
                f"Python socket guard blocked non-loopback egress to {host}:{port}"
            )
        return real_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", _loopback_only_create_connection)

    # Verify the Python socket guard actively blocks non-loopback egress
    with pytest.raises(
        RuntimeError,
        match="Python socket guard blocked non-loopback egress",
    ):
        socket.create_connection(("198.51.100.1", 443), timeout=0.1)

    observed_targets.clear()

    result = simulate_grabber_update_flow(
        server_base_url=mock_server.base_url,
        trusted_public_key_pem=pub_pem,
        installed_executable=installed_bin,
        installed_sequence=10,
        workspace_dir=tmp_path / "work",
    )

    assert result["status"] == "no_release"
    assert result["current_sequence"] == 10
    assert observed_targets == [("127.0.0.1", mock_server.port)]
    # Calls logged exclusively on local loopback server
    assert len(mock_server.state["calls"]) == 1
    assert mock_server.state["calls"][0] == "/mpips/staging/latest.json"


# ---------------------------------------------------------------------------
# Offline Integrated Acceptance with Real Update Server & Real ELF Binary
# ---------------------------------------------------------------------------


class LocalIsolatedS3Client:
    """Isolated local-disk S3 client double for MinIOArtifactStore."""

    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.base_url = "http://127.0.0.1:0"

    def _obj_path(self, bucket: str, key: str) -> Path:
        return self.storage_root / bucket / key

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        target = self._obj_path(Bucket, Key)
        if not target.is_file():
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadObject",
            )
        return {"ContentLength": target.stat().st_size}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: Any,
        ContentLength: int | None = None,
        ContentType: str | None = None,
    ) -> dict[str, Any]:
        _ = (ContentLength, ContentType)
        target = self._obj_path(Bucket, Key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(Body, (bytes, bytearray)):
            target.write_bytes(bytes(Body))
        elif hasattr(Body, "name") and isinstance(Body.name, str):
            src = Path(Body.name)
            try:
                os.link(src, target)
            except OSError:
                shutil.copyfile(src, target)
        else:
            with target.open("wb") as out_f:
                shutil.copyfileobj(Body, out_f, length=1024 * 1024)
        return {"ETag": '"isolated-local-etag"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        target = self._obj_path(Bucket, Key)
        if not target.is_file():
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
                "GetObject",
            )
        return {
            "Body": target.open("rb"),
            "ContentLength": target.stat().st_size,
        }

    def generate_presigned_url(
        self,
        ClientMethod: str,
        *,
        Params: dict[str, Any],
        ExpiresIn: int,
    ) -> str:
        if ClientMethod != "get_object":
            raise ValueError(f"Unsupported ClientMethod: {ClientMethod}")
        bucket = Params["Bucket"]
        key = Params["Key"]
        return (
            f"{self.base_url}/storage/{bucket}/{key}"
            f"?X-Amz-Expires={ExpiresIn}&X-Amz-Signature=synthetic-local-sig"
        )


class RealUpdateServerLoopbackFixture:
    """Hosts the real FastAPI create_update_server_app + isolated local storage."""

    def __init__(
        self,
        tmp_dir: Path,
        public_key_pem: bytes,
        staging_token: str = DEFAULT_STAGING_READER_TOKEN,
    ) -> None:
        self.storage_root = tmp_dir / "isolated_s3"
        self.state_dir = tmp_dir / "registry_state"
        self.s3_client = LocalIsolatedS3Client(self.storage_root)
        self.store = MinIOArtifactStore(
            s3_client=self.s3_client,
            bucket="mhcs-mpips-artifacts",
            presign_ttl_seconds=300,
        )
        self.registry = ReleaseRegistry(
            state_dir=self.state_dir,
            public_key_pem=public_key_pem,
            artifact_store=self.store,
        )
        self.authenticator = ClientAuthenticator({staging_token: {STAGING_READ_SCOPE}})
        self.fastapi_app = create_update_server_app(
            registry=self.registry,
            authenticator=self.authenticator,
        )
        self.test_client = TestClient(self.fastapi_app)
        self.storage_downloads = 0
        self.storage_auth_leaks = 0
        self.corrupt_storage_stream = False

        fixture_ref = self

        class BridgeHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                parsed = urllib.parse.urlsplit(self.path)
                if parsed.path.startswith("/storage/"):
                    if self.headers.get("Authorization"):
                        fixture_ref.storage_auth_leaks += 1
                        self.send_response(403)
                        self.end_headers()
                        return
                    rel_key = parsed.path[len("/storage/") :]
                    file_path = fixture_ref.storage_root / rel_key
                    if not file_path.is_file():
                        self.send_response(404)
                        self.end_headers()
                        return
                    fixture_ref.storage_downloads += 1
                    file_size = file_path.stat().st_size
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(file_size))
                    self.end_headers()
                    with file_path.open("rb") as f_in:
                        first_chunk = True
                        while True:
                            chunk = f_in.read(65536)
                            if not chunk:
                                break
                            if first_chunk and fixture_ref.corrupt_storage_stream:
                                mutated = bytearray(chunk)
                                mutated[0] ^= 0xFF
                                chunk = bytes(mutated)
                            first_chunk = False
                            self.wfile.write(chunk)
                    return

                req_headers: dict[str, str] = {}
                for hdr_name in (
                    "Authorization",
                    "X-MPIPS-API-Key",
                    "X-MPIPS-Client-Platform",
                ):
                    hdr_val = self.headers.get(hdr_name)
                    if hdr_val is not None:
                        req_headers[hdr_name] = hdr_val
                resp = fixture_ref.test_client.get(self.path, headers=req_headers)
                body = resp.content
                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    if k.lower() not in {"content-length", "transfer-encoding"}:
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = HTTPServer(("127.0.0.1", 0), BridgeHandler)
        self.port = self.server.server_port
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.s3_client.base_url = self.base_url
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)


def test_real_update_server_and_real_elf_offline_integrated_acceptance(
    tmp_path: Path,
) -> None:
    """Offline integrated acceptance using real update-server and real ELF binary."""
    if not REAL_ELF_PATH.is_file():
        if os.getenv("MPIPS_STRICT_QUALIFICATION") == "1":
            pytest.fail(f"Real ELF binary missing at {REAL_ELF_PATH}")
        pytest.skip(f"Real ELF binary not present at {REAL_ELF_PATH}")

    # Verify candidate binary identity before publishing to local fixture
    assert REAL_ELF_PATH.stat().st_size == EXPECTED_REAL_ELF_SIZE
    with REAL_ELF_PATH.open("rb") as f_elf:
        actual_elf_sha = hashlib.file_digest(f_elf, "sha256").hexdigest()
    assert actual_elf_sha == EXPECTED_REAL_ELF_SHA256

    # Generate disposable Ed25519 signing keypair
    priv_key = Ed25519PrivateKey.generate()
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    srv = RealUpdateServerLoopbackFixture(tmp_path / "server", pub_pem)
    try:
        # 1. Verify initial 'no_release' state & first-bootstrap guard
        assert (
            run_checks(srv.base_url, DEFAULT_STAGING_READER_TOKEN, mode="infra") is True
        )
        assert (
            run_checks(
                srv.base_url,
                DEFAULT_STAGING_READER_TOKEN,
                mode="distribution",
                public_key_pem=pub_pem,
            )
            is False
        )

        installed_bin = tmp_path / "grabber_install" / "mpips-runtime.bin"
        installed_bin.parent.mkdir(parents=True, exist_ok=True)
        _create_mock_runtime_script(installed_bin, tag="v10-preexisting")

        with pytest.raises(GrabberUpdateError, match="First-bootstrap requires"):
            simulate_grabber_update_flow(
                server_base_url=srv.base_url,
                trusted_public_key_pem=pub_pem,
                installed_executable=installed_bin,
                installed_sequence=0,
                workspace_dir=tmp_path / "work_bootstrap",
                staging_token=DEFAULT_STAGING_READER_TOKEN,
                require_available_for_bootstrap=True,
            )

        # 2. Publish and promote the real ELF (sequence 11) in the real ReleaseRegistry
        release_id = "0.1.0-real-elf-staging-r11"
        metadata = create_elf_release_metadata(
            binary_path=REAL_ELF_PATH,
            release_id=release_id,
            version="0.1.0",
            sequence=11,
            source_commit="cbf2b24ba4fb8f2b5fc25b6a86f381ba7cf5f4b1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        meta_bytes = canonical_metadata_bytes(metadata)
        sig_bytes = sign_metadata_bytes(meta_bytes, priv_pem)

        srv.registry.register_and_upload_release(
            binary_path=REAL_ELF_PATH,
            metadata_bytes=meta_bytes,
            signature_bytes=sig_bytes,
            authorize=True,
            promote=True,
        )

        # 3. Verify server distribution readiness via canonical verifier
        assert (
            run_checks(
                srv.base_url,
                DEFAULT_STAGING_READER_TOKEN,
                mode="distribution",
                public_key_pem=pub_pem,
                download_timeout=120.0,
            )
            is True
        )

        # 4. Run full Grabber update flow to download, verify, self-check, smoke-test,
        # and atomically promote the genuine 241,288,024-byte ELF
        update_res = simulate_grabber_update_flow(
            server_base_url=srv.base_url,
            trusted_public_key_pem=pub_pem,
            installed_executable=installed_bin,
            installed_sequence=10,
            workspace_dir=tmp_path / "work_promote",
            staging_token=DEFAULT_STAGING_READER_TOKEN,
            perform_synthetic_conversion=True,
            download_timeout=120.0,
            self_check_timeout=30.0,
        )
        assert update_res["status"] == "promoted"
        assert update_res["current_sequence"] == 11
        assert srv.storage_auth_leaks == 0
        assert installed_bin.stat().st_size == EXPECTED_REAL_ELF_SIZE
        with installed_bin.open("rb") as f_inst:
            assert (
                hashlib.file_digest(f_inst, "sha256").hexdigest()
                == EXPECTED_REAL_ELF_SHA256
            )

        # 5. Execute downloaded ELF's --version with scrubbed env (no Python runtime)
        ver_proc = subprocess.run(
            [
                "/usr/bin/env",
                "-i",
                "PATH=/usr/bin:/bin",
                str(installed_bin),
                "--version",
            ],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=True,
        )
        ver_json = json.loads(ver_proc.stdout.strip())
        assert ver_json == {
            "code": "OK",
            "interface_version": "2-experimental",
            "runtime_version": "0.1.0",
            "status": "ok",
        }

        # 6. Generate synthetic SIMRS HTTP response and enforce operator confirmation
        visit_id = "SYNTHETIC-VISIT-2026-0777"
        simrs_payload = json.dumps(
            {
                "success": True,
                "data": {
                    "no_rawat": visit_id,
                    "no_rkm_medis": "SYNTHETIC-MRN-0777",
                    "nm_pasien": "SYNTHETIC INTEGRATED PATIENT",
                    "jk": "L",
                    "tgl_lahir": "1988-04-12",
                    "tgl_daftar": "2026-11-10",
                },
            }
        )
        with pytest.raises(SIMRSConfirmationRequiredError):
            parse_simrs_http_response(
                200,
                simrs_payload,
                visit_id,
                confirmed_sex_codes={"L": "male", "P": "female"},
                captured_at="2026-11-10T09:00:00+07:00",
                confirmed=False,
            )

        simrs_manifest = parse_simrs_http_response(
            200,
            simrs_payload,
            visit_id,
            confirmed_sex_codes={"L": "male", "P": "female"},
            captured_at="2026-11-10T09:00:00+07:00",
            confirmed=True,
        )

        # 7. Invoke promoted real ELF to produce BED DICOM from SIMRS-derived manifest
        bed_dir = tmp_path / "exam_bed"
        bed_rad, bed_gain, bed_man_path, bed_cal_dir = make_inputs(bed_dir, "BED")
        bed_man_data = json.loads(bed_man_path.read_text(encoding="utf-8"))
        bed_man_data["patient"] = simrs_manifest["patient"]
        bed_man_data["examination"]["encounter_id"] = visit_id
        bed_man_path.write_text(json.dumps(bed_man_data), encoding="utf-8")
        bed_out = bed_dir / "bed_result.dcm"

        adapter = MPIPSSubprocessAdapter(installed_bin)
        bed_conv = adapter.convert(
            radiograph=bed_rad,
            gain=bed_gain,
            manifest=bed_man_path,
            output=bed_out,
            timeout=120.0,
        )
        assert bed_conv.status == "ok"
        assert bed_conv.code == "OK"
        assert bed_conv.interface_version == "2-experimental"
        assert bed_out.is_file()
        assert bed_out.stat().st_size == bed_conv.output_byte_size
        assert (bed_out.stat().st_mode & 0o777) == 0o600

        ds_bed = pydicom.dcmread(bed_out)
        assert ds_bed.Modality == "DX"
        assert ds_bed.SOPClassUID == "1.2.840.10008.5.1.4.1.1.1.1.1"
        assert ds_bed.PhotometricInterpretation == "MONOCHROME2"
        assert ds_bed.BitsAllocated == 16
        assert ds_bed.PixelRepresentation == 0
        assert ds_bed.PatientID == "SYNTHETIC-MRN-0777"
        assert ds_bed.PatientSex == "M"
        assert ds_bed.PatientBirthDate == "19880412"
        assert ds_bed.pixel_array.shape == (48, 64)
        assert ds_bed.pixel_array.dtype == np.uint16

        # 8. Invoke promoted real ELF to produce full-resolution (3000x4096) TRX DICOM
        trx_dir = tmp_path / "exam_trx"
        trx_dir.mkdir(parents=True, exist_ok=True)
        trx_rad = trx_dir / "radiograph.npz"
        trx_gain = trx_dir / "gain.npz"
        trx_man = trx_dir / "manifest.json"
        trx_out = trx_dir / "trx_result.dcm"
        shape = (3000, 4096)
        camera = {
            "serialNumber": "DA5234480",
            "cameraSerial": "DA5234480",
            "cameraModel": "MV-CH120-10UM",
        }
        xray = {"detectorMode": "TRX"}
        raw_img = np.linspace(
            1000, 30000, shape[0] * shape[1], dtype=np.uint16
        ).reshape(shape)
        np.savez_compressed(
            trx_rad,
            id=np.array("INTEGRATED-TRX-RAD-001"),
            gainid=np.array("INTEGRATED-TRX-GAIN-001"),
            rawimage=raw_img,
            cameraparams=np.array(camera),
            xrayparams=np.array(xray),
        )
        np.savez_compressed(
            trx_gain,
            id=np.array("INTEGRATED-TRX-GAIN-001"),
            rawimage=np.full(shape, 35000, dtype=np.uint16),
            darkimage=np.full(shape, 50, dtype=np.uint16),
            cameraparams=np.array(camera),
            xrayparams=np.array(xray),
        )
        trx_manifest_payload = {
            "manifest_version": "1.0",
            "patient": simrs_manifest["patient"],
            "examination": {
                "encounter_id": visit_id,
                "performed_at": "2026-11-10T09:00:00+07:00",
            },
            "capture": {
                "detector_type": "TRX",
                "body_part_examined": "CHEST",
                "projection": "PA",
                "view_code_sequence": [
                    {
                        "code_value": "272479007",
                        "coding_scheme_designator": "SCT",
                        "code_meaning": "postero-anterior",
                    }
                ],
                "captured_at": "2026-11-10T09:00:00+07:00",
                "detector_spacing": {"row_mm": 0.15, "column_mm": 0.16},
            },
            "dicom": {
                "pixel_source": "CANONICAL_PRE_PRESENTATION",
                "pixel_intensity_relationship": "LIN",
                "pixel_intensity_relationship_sign": 1,
            },
        }
        trx_man.write_text(json.dumps(trx_manifest_payload), encoding="utf-8")

        trx_conv = adapter.convert(
            radiograph=trx_rad,
            gain=trx_gain,
            manifest=trx_man,
            output=trx_out,
            timeout=180.0,
        )
        assert trx_conv.status == "ok"
        assert trx_conv.code == "OK"
        assert trx_out.is_file()
        assert trx_out.stat().st_size == trx_conv.output_byte_size
        assert (trx_out.stat().st_mode & 0o777) == 0o600

        ds_trx = pydicom.dcmread(trx_out)
        assert ds_trx.Modality == "DX"
        assert ds_trx.SOPClassUID == "1.2.840.10008.5.1.4.1.1.1.1.1"
        assert ds_trx.PatientID == "SYNTHETIC-MRN-0777"
        assert ds_trx.PatientSex == "M"
        assert ds_trx.pixel_array.shape == (4096, 3000)
        assert ds_trx.pixel_array.dtype == np.uint16

        # 9. Validate deterministic failure behavior of downloaded real ELF
        # 9a. Reject external --calibration override in 2-experimental (exit 2)
        cal_override_proc = subprocess.run(
            [
                str(installed_bin),
                "convert",
                "--radiograph",
                str(bed_rad),
                "--gain",
                str(bed_gain),
                "--manifest",
                str(bed_man_path),
                "--calibration",
                str(bed_cal_dir),
                "--output",
                str(bed_dir / "never_created.dcm"),
            ],
            capture_output=True,
            text=True,
        )
        assert cal_override_proc.returncode == 2
        assert json.loads(cal_override_proc.stdout)["code"] == "INVALID_INPUT"

        # 9b. Reject existing destination DICOM file (exit 4 OUTPUT_EXISTS)
        exists_proc = subprocess.run(
            [
                str(installed_bin),
                "convert",
                "--radiograph",
                str(bed_rad),
                "--gain",
                str(bed_gain),
                "--manifest",
                str(bed_man_path),
                "--output",
                str(bed_out),
            ],
            capture_output=True,
            text=True,
        )
        assert exists_proc.returncode == 4
        assert json.loads(exists_proc.stdout)["code"] == "OUTPUT_EXISTS"

        # 9c. Reject missing input file (exit 3 INPUT_NOT_FOUND)
        missing_proc = subprocess.run(
            [
                str(installed_bin),
                "convert",
                "--radiograph",
                str(bed_dir / "nonexistent_rad.npz"),
                "--gain",
                str(bed_gain),
                "--manifest",
                str(bed_man_path),
                "--output",
                str(bed_dir / "never_created_2.dcm"),
            ],
            capture_output=True,
            text=True,
        )
        assert missing_proc.returncode == 3
        assert json.loads(missing_proc.stdout)["code"] == "INPUT_NOT_FOUND"

        # 10. Test preservation of promoted real ELF after deliberately failed update
        release_id_12 = "0.1.0-real-elf-staging-r12"
        meta_12 = create_elf_release_metadata(
            binary_path=REAL_ELF_PATH,
            release_id=release_id_12,
            version="0.1.0",
            sequence=12,
            source_commit="cbf2b24ba4fb8f2b5fc25b6a86f381ba7cf5f4b1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        meta_12_bytes = canonical_metadata_bytes(meta_12)
        sig_12_bytes = sign_metadata_bytes(meta_12_bytes, priv_pem)
        srv.registry.register_and_upload_release(
            binary_path=REAL_ELF_PATH,
            metadata_bytes=meta_12_bytes,
            signature_bytes=sig_12_bytes,
            authorize=True,
            promote=True,
        )

        # Deliberately corrupt streamed artifact bytes during download
        srv.corrupt_storage_stream = True
        with pytest.raises(GrabberUpdateError, match="SHA-256 mismatch"):
            simulate_grabber_update_flow(
                server_base_url=srv.base_url,
                trusted_public_key_pem=pub_pem,
                installed_executable=installed_bin,
                installed_sequence=11,
                workspace_dir=tmp_path / "work_failed_r12",
                staging_token=DEFAULT_STAGING_READER_TOKEN,
                perform_synthetic_conversion=True,
                download_timeout=120.0,
                self_check_timeout=30.0,
            )

        # Verify staging file was cleaned up and installed real ELF is untouched
        assert not (tmp_path / "work_failed_r12" / "candidate_runtime.tmp").exists()
        assert installed_bin.stat().st_size == EXPECTED_REAL_ELF_SIZE
        with installed_bin.open("rb") as f_after:
            assert (
                hashlib.file_digest(f_after, "sha256").hexdigest()
                == EXPECTED_REAL_ELF_SHA256
            )
        assert adapter.check_version().status == "ok"
    finally:
        srv.shutdown()
