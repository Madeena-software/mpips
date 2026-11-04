"""End-to-end verification script for the MPIPS staging update server."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELEASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"^[0-9a-f]{64}\Z")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9._-]+)?\Z")

SUPPORTED_PLATFORM = "ubuntu-24.04-x86_64"
SUPPORTED_CHANNEL = "staging"
EXPECTED_INTERFACE_VERSION = "2-experimental"
EXPECTED_ARTIFACT_FILENAME = "mpips-runtime.bin"

REQUIRED_AVAILABLE_KEYS = frozenset(
    {
        "schema_version",
        "channel",
        "status",
        "platform",
        "release_id",
        "version",
        "sequence",
        "source_commit",
        "interface_version",
        "artifact",
        "download_endpoint",
        "signature",
        "release_status",
        "expires_at",
        "compatibility",
        "signed_metadata_b64",
    }
)

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
    subset = {k: metadata[k] for k in SIGNED_METADATA_KEYS if k in metadata}
    return (json.dumps(subset, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _verify_ed25519_signature(
    metadata_bytes: bytes,
    signature_bytes: bytes,
    public_key_pem: bytes,
) -> bool:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            return False
        key.verify(signature_bytes, metadata_bytes)
        return True
    except (InvalidSignature, Exception):
        return False


def _request(
    url: str,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    timeout: float = 10.0,
) -> tuple[int, dict[str, Any] | None, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            resp_headers = dict(resp.headers.items())
            try:
                data = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                data = None
            return resp.status, data, resp_headers, body
    except urllib.error.HTTPError as err:
        body = err.read()
        resp_headers = dict(err.headers.items())
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            data = None
        return err.code, data, resp_headers, body
    except urllib.error.URLError as err:
        return 0, None, {}, str(err).encode("utf-8")
    except Exception as err:
        return 0, None, {}, str(err).encode("utf-8")


def run_checks(
    base_url: str,
    token: str,
    *,
    mode: str = "infra",
    platform: str = SUPPORTED_PLATFORM,
    public_key_pem: bytes | None = None,
    timeout: float = 10.0,
    download_timeout: float = 60.0,
) -> bool:
    base = base_url.rstrip("/")
    all_ok = True

    if mode not in ("infra", "distribution"):
        raise ValueError(
            f"Invalid verification mode: {mode!r} (expected 'infra' or 'distribution')"
        )

    print(f"=== MPIPS Staging Update Server Verification: {base} (mode={mode}) ===")

    # 1. Health check
    status, data, _, body = _request(f"{base}/mpips/staging/health", timeout=timeout)
    if (
        status == 200
        and isinstance(data, dict)
        and data.get("status") == "ok"
        and data.get("environment") == "staging"
    ):
        print(f"  [PASS] 1. Health endpoint (200 OK): {data}")
    else:
        err_msg = data or body.decode("utf-8", errors="replace")
        print(f"  [FAIL] 1. Health endpoint returned {status}: {err_msg}")
        all_ok = False

    # 2. Unauthenticated latest.json check (must return 401)
    status, data, _, _ = _request(f"{base}/mpips/staging/latest.json", timeout=timeout)
    if (
        status == 401
        and isinstance(data, dict)
        and data.get("error", {}).get("code") == "unauthorized"
    ):
        print("  [PASS] 2. Unauthenticated latest.json rejected (401 Unauthorized)")
    else:
        print(f"  [FAIL] 2. Unauthenticated latest.json returned {status}: {data}")
        all_ok = False

    # 3. Invalid token latest.json check (must return 401)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/latest.json",
        headers={"Authorization": "Bearer invalid-token-xyz"},
        timeout=timeout,
    )
    if (
        status == 401
        and isinstance(data, dict)
        and data.get("error", {}).get("code") == "unauthorized"
    ):
        print("  [PASS] 3. Invalid token rejected (401 Unauthorized)")
    else:
        print(f"  [FAIL] 3. Invalid token returned {status}: {data}")
        all_ok = False

    # 4. Incompatible platform (must return 422)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/latest.json?platform=windows-x86_64",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if (
        status == 422
        and isinstance(data, dict)
        and data.get("error", {}).get("code") == "incompatible_platform"
    ):
        print("  [PASS] 4. Incompatible platform rejected (422 Unprocessable Content)")
    else:
        print(f"  [FAIL] 4. Incompatible platform returned {status}: {data}")
        all_ok = False

    # 5. Authenticated latest.json check (200 OK, no_release or available)
    status, data, _, body = _request(
        f"{base}/mpips/staging/latest.json?platform={platform}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    manifest: dict[str, Any] = {}
    if status != 200 or not isinstance(data, dict) or data.get("schema_version") != 1:
        err_msg = data or body.decode("utf-8", errors="replace")
        print(f"  [FAIL] 5. Authenticated latest.json returned {status}: {err_msg}")
        all_ok = False
        release_status = None
    else:
        manifest = data
        release_status = manifest.get("status")

    if release_status == "no_release":
        ch = manifest.get("channel")
        print(f"  [INFO] Channel status is 'no_release' (channel={ch})")
        if mode == "distribution":
            print(
                "  [FAIL] 5. Binary distribution readiness failed: "
                "channel reports 'no_release'. CI cannot claim complete "
                "binary-distribution acceptance without verifying a real artifact."
            )
            all_ok = False
        else:
            print(
                "  [PASS] 5. Infrastructure readiness verified "
                "(status: no_release, G10 NOT RELEASED)"
            )

    elif release_status == "available":
        ch = manifest.get("channel")
        print(f"  [INFO] Channel status is 'available' (channel={ch})")
        manifest_valid = True

        # Check required schema keys
        missing_keys = REQUIRED_AVAILABLE_KEYS - set(manifest.keys())
        if missing_keys:
            sorted_keys = sorted(missing_keys)
            print(f"  [FAIL] 5. Malformed manifest: missing keys {sorted_keys}")
            manifest_valid = False

        release_id = manifest.get("release_id", "")
        version = manifest.get("version", "")
        sequence = manifest.get("sequence")
        source_commit = manifest.get("source_commit", "")
        interface_version = manifest.get("interface_version", "")
        signature_b64 = manifest.get("signature", "")
        signed_metadata_b64 = manifest.get("signed_metadata_b64", "")
        expires_at_str = manifest.get("expires_at", "")
        download_endpoint = manifest.get("download_endpoint", "")
        artifact = manifest.get("artifact")

        if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
            print(f"  [FAIL] 5. Invalid release_id format: {release_id!r}")
            manifest_valid = False

        if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
            print(f"  [FAIL] 5. Invalid version format: {version!r}")
            manifest_valid = False

        if type(sequence) is not int or sequence < 1:
            print(f"  [FAIL] 5. Invalid sequence: {sequence!r}")
            manifest_valid = False

        if not isinstance(source_commit, str) or not COMMIT_SHA_RE.fullmatch(
            source_commit
        ):
            print(f"  [FAIL] 5. Invalid source_commit SHA: {source_commit!r}")
            manifest_valid = False

        if interface_version != EXPECTED_INTERFACE_VERSION:
            print(
                f"  [FAIL] 5. Unexpected interface_version: {interface_version!r} "
                f"(expected {EXPECTED_INTERFACE_VERSION!r})"
            )
            manifest_valid = False

        # Validate artifact structure and extract sha256 and size_bytes
        expected_sha: str | None = None
        expected_size: int | None = None
        if not isinstance(artifact, dict):
            print(f"  [FAIL] 5. Manifest 'artifact' must be an object: {artifact!r}")
            manifest_valid = False
        else:
            filename = artifact.get("filename")
            expected_sha = artifact.get("sha256")
            expected_size = artifact.get("size_bytes")

            if filename != EXPECTED_ARTIFACT_FILENAME:
                print(
                    f"  [FAIL] 5. Unexpected artifact filename: {filename!r} "
                    f"(expected {EXPECTED_ARTIFACT_FILENAME!r})"
                )
                manifest_valid = False

            if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(
                expected_sha
            ):
                print(f"  [FAIL] 5. Invalid artifact sha256: {expected_sha!r}")
                manifest_valid = False

            if type(expected_size) is not int or expected_size <= 0:
                print(f"  [FAIL] 5. Invalid artifact size_bytes: {expected_size!r}")
                manifest_valid = False

        # Validate expiry timestamp
        if not isinstance(expires_at_str, str):
            print(
                f"  [FAIL] 5. Missing or invalid expires_at string: {expires_at_str!r}"
            )
            manifest_valid = False
        else:
            try:
                expires_dt = datetime.fromisoformat(expires_at_str)
                if expires_dt.tzinfo is None:
                    print(
                        "  [FAIL] 5. Malformed expires_at: timezone-aware required"
                    )
                    manifest_valid = False
                elif expires_dt <= datetime.now(timezone.utc):
                    print(
                        f"  [FAIL] 5. Release metadata has expired at {expires_at_str}"
                    )
                    manifest_valid = False
            except ValueError as exc:
                print(f"  [FAIL] 5. Malformed expires_at ISO string: {exc}")
                manifest_valid = False

        # Validate signed metadata and signature
        if not isinstance(signature_b64, str) or not isinstance(
            signed_metadata_b64, str
        ):
            print("  [FAIL] 5. Missing signature or signed_metadata_b64")
            manifest_valid = False
        else:
            try:
                sig_bytes = base64.b64decode(
                    signature_b64.encode("ascii"), validate=True
                )
                if len(sig_bytes) != 64:
                    print(
                        f"  [FAIL] 5. Ed25519 signature is {len(sig_bytes)} bytes, "
                        "expected 64"
                    )
                    manifest_valid = False
            except Exception as exc:
                print(f"  [FAIL] 5. Malformed base64 signature: {exc}")
                manifest_valid = False
                sig_bytes = b""

            try:
                meta_bytes = base64.b64decode(
                    signed_metadata_b64.encode("ascii"), validate=True
                )
                parsed_meta = json.loads(meta_bytes.decode("utf-8"))
                canonical_meta = _canonical_metadata_bytes(parsed_meta)
                if canonical_meta != meta_bytes:
                    print(
                        "  [FAIL] 5. signed_metadata_b64 bytes do not match "
                        "canonical JSON serialization"
                    )
                    manifest_valid = False

                # Cross-check embedded fields with manifest top-level fields
                if (
                    parsed_meta.get("release_id") != release_id
                    or parsed_meta.get("sequence") != sequence
                    or parsed_meta.get("artifact", {}).get("sha256") != expected_sha
                    or parsed_meta.get("artifact", {}).get("size_bytes")
                    != expected_size
                    or parsed_meta.get("interface_version") != interface_version
                ):
                    print(
                        "  [FAIL] 5. Embedded signed metadata fields do not "
                        "match outer manifest fields"
                    )
                    manifest_valid = False

                if public_key_pem is not None and sig_bytes:
                    if not _verify_ed25519_signature(
                        meta_bytes, sig_bytes, public_key_pem
                    ):
                        print(
                            "  [FAIL] 5. Ed25519 signature verification failed "
                            "against configured public key"
                        )
                        manifest_valid = False
                    else:
                        print(
                            "  [PASS] 5. Ed25519 detached signature verified "
                            "against configured public key"
                        )
            except Exception as exc:
                print(f"  [FAIL] 5. Malformed signed_metadata_b64 payload: {exc}")
                manifest_valid = False

        if not manifest_valid:
            all_ok = False
        else:
            print(
                f"  [PASS] 5. Authenticated latest.json manifest verified "
                f"(release_id={release_id}, sequence={sequence})"
            )

        # 6. Authenticated download URL check
        dl_url_path = (
            download_endpoint
            if download_endpoint.startswith("/")
            else f"/mpips/staging/releases/{release_id}/download"
        )
        dl_status, dl_data, _, dl_body = _request(
            f"{base}{dl_url_path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        if dl_status == 200 and isinstance(dl_data, dict) and "download_url" in dl_data:
            dl_url = dl_data["download_url"]
            print(
                f"  [PASS] 6. Presigned download URL issued for {release_id}"
            )

            # 7. Download binary from presigned URL and verify real hash and size
            if expected_sha and expected_size:
                try:
                    with urllib.request.urlopen(
                        dl_url, timeout=download_timeout
                    ) as dl_resp:
                        bin_bytes = dl_resp.read()
                    actual_sha = hashlib.sha256(bin_bytes).hexdigest()
                    actual_size = len(bin_bytes)

                    if actual_sha == expected_sha and actual_size == expected_size:
                        print(
                            "  [PASS] 7. Downloaded binary integrity verified "
                            f"(SHA-256: {actual_sha}, size={actual_size} bytes)"
                        )
                    else:
                        print(
                            "  [FAIL] 7. Binary integrity mismatch: "
                            f"expected_sha={expected_sha}, actual_sha={actual_sha}, "
                            f"expected_size={expected_size}, actual_size={actual_size}"
                        )
                        all_ok = False
                except Exception as exc:
                    print(f"  [FAIL] 7. Presigned URL download failed: {exc}")
                    all_ok = False
            else:
                print(
                    "  [FAIL] 7. Skipped binary verification: missing artifact metadata"
                )
                all_ok = False
        else:
            err_msg = dl_data or dl_body.decode("utf-8", errors="replace")
            print(f"  [FAIL] 6. Download endpoint returned {dl_status}: {err_msg}")
            all_ok = False

    elif release_status is not None:
        print(
            f"  [FAIL] 5. Unexpected release status: {release_status!r} "
            "(expected 'no_release' or 'available')"
        )
        all_ok = False

    # 8. Unauthenticated download endpoint rejected (401)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/releases/test-release/download",
        timeout=timeout,
    )
    if (
        status == 401
        and isinstance(data, dict)
        and data.get("error", {}).get("code") == "unauthorized"
    ):
        print("  [PASS] 8. Unauthenticated download rejected (401 Unauthorized)")
    else:
        print(f"  [FAIL] 8. Unauthenticated download returned {status}: {data}")
        all_ok = False

    # 9. Nonexistent release download returns 404
    status, data, _, _ = _request(
        f"{base}/mpips/staging/releases/nonexistent-release-xyz/download",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if (
        status == 404
        and isinstance(data, dict)
        and data.get("error", {}).get("code") == "release_not_found"
    ):
        print("  [PASS] 9. Nonexistent release download rejected (404 Not Found)")
    else:
        print(f"  [FAIL] 9. Nonexistent release returned {status}: {data}")
        all_ok = False

    if all_ok:
        if mode == "distribution":
            print("=== VERIFICATION RESULT: DISTRIBUTION READINESS ACCEPTED ===")
        else:
            print("=== VERIFICATION RESULT: INFRASTRUCTURE READINESS ACCEPTED ===")
    else:
        print("=== VERIFICATION RESULT: FAILED ===")

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="https://ip.mhcsgo.cloud",
        help="Base URL of the update server (default: https://ip.mhcsgo.cloud)",
    )
    token_env = os.getenv("MPIPS_UPDATE_STAGING_READER_TOKEN") or os.getenv(
        "MPIPS_API_KEY", ""
    )
    parser.add_argument(
        "--token",
        default=token_env,
        help=(
            "Staging reader authentication token (defaults to "
            "MPIPS_UPDATE_STAGING_READER_TOKEN or MPIPS_API_KEY env vars)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["infra", "distribution"],
        default="infra",
        help=(
            "Verification mode: 'infra' accepts 'no_release'; 'distribution' "
            "strictly requires a promoted real artifact (default: infra)"
        ),
    )
    parser.add_argument(
        "--require-artifact",
        action="store_true",
        help="Alias to enforce distribution mode (fails if status == 'no_release')",
    )
    parser.add_argument(
        "--platform",
        default=SUPPORTED_PLATFORM,
        help=f"Target platform to verify (default: {SUPPORTED_PLATFORM})",
    )
    parser.add_argument(
        "--public-key",
        help="Optional path to trusted Ed25519 public key PEM for signature check",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="API request timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--download-timeout",
        type=float,
        default=60.0,
        help="Binary artifact download timeout in seconds (default: 60.0)",
    )

    args = parser.parse_args()

    token = args.token.strip()
    if not token:
        print(
            "ERROR: Authentication token is required via --token or "
            "MPIPS_UPDATE_STAGING_READER_TOKEN / MPIPS_API_KEY",
            file=sys.stderr,
        )
        return 1

    mode = "distribution" if args.require_artifact else args.mode

    pub_pem: bytes | None = None
    if args.public_key:
        pub_path = Path(args.public_key)
        if not pub_path.is_file():
            print(
                f"ERROR: Public key file not found: {args.public_key}", file=sys.stderr
            )
            return 1
        pub_pem = pub_path.read_bytes()

    success = run_checks(
        args.base_url,
        token,
        mode=mode,
        platform=args.platform,
        public_key_pem=pub_pem,
        timeout=args.timeout,
        download_timeout=args.download_timeout,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
