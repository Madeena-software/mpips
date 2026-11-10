"""Integration and security tests for the MPIPS MinIO staging update server."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import EndpointConnectionError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from moto import mock_aws

from mpips.update_server.app import create_update_server_app
from mpips.update_server.auth import STAGING_READ_SCOPE, ClientAuthenticator
from mpips.update_server.minio_adapter import (
    ArtifactIntegrityError,
    MinIOArtifactStore,
    ReleaseConflictError,
    build_release_object_key,
)
from mpips.update_server.registry import (
    ChannelSequenceConflictError,
    ReleaseNotFoundError,
    ReleaseRegistry,
    ReleaseUnauthorizedError,
    ReleaseValidationError,
)
from mpips.update_server.release_metadata import (
    ARTIFACT_FILENAME,
    INTERFACE_VERSION,
    SUPPORTED_CHANNEL,
    SUPPORTED_PLATFORM,
    canonical_metadata_bytes,
    create_elf_release_metadata,
    decode_signature_b64,
    sign_metadata_bytes,
    verify_elf_release_metadata,
)

TEST_BUCKET = "mhcs-mpips-artifacts"
AUTHORIZED_READER_TOKEN = "staging-grabber-reader-token-synthetic"
FORBIDDEN_SCOPE_TOKEN = "other-service-token-without-staging-read"


@pytest.fixture
def ed25519_keypair() -> tuple[bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture
def synthetic_elf_binary(tmp_path: Path) -> Path:
    binary = tmp_path / ARTIFACT_FILENAME
    payload = b"\x7fELF\x02\x01\x01\x00" + (b"MPIPS-SYNTHETIC-TEST-ELF-PAYLOAD-" * 256)
    binary.write_bytes(payload)
    return binary


def _build_signed_bundle(
    binary_path: Path,
    private_pem: bytes,
    *,
    release_id: str = "0.1.0-synthetic-staging-r1",
    sequence: int = 1,
    source_commit: str = "1176a4f79bc654c88a24f62cf5793fdf653cf0e9",
    expires_delta: timedelta = timedelta(days=7),
) -> tuple[dict[str, Any], bytes, bytes]:
    metadata = create_elf_release_metadata(
        binary_path=binary_path,
        release_id=release_id,
        version="0.1.0",
        sequence=sequence,
        source_commit=source_commit,
        expires_at=datetime.now(timezone.utc) + expires_delta,
    )
    meta_bytes = canonical_metadata_bytes(metadata)
    sig_bytes = sign_metadata_bytes(meta_bytes, private_pem)
    return metadata, meta_bytes, sig_bytes


@pytest.fixture
def minio_env(
    tmp_path: Path,
    ed25519_keypair: tuple[bytes, bytes],
) -> Any:
    private_pem, public_pem = ed25519_keypair
    with mock_aws():
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="minio-test-access-key",
            aws_secret_access_key="minio-test-secret-key",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        s3.create_bucket(Bucket=TEST_BUCKET)
        s3.put_bucket_versioning(
            Bucket=TEST_BUCKET,
            VersioningConfiguration={"Status": "Enabled"},
        )
        store = MinIOArtifactStore(
            s3_client=s3,
            bucket=TEST_BUCKET,
            presign_ttl_seconds=300,
        )
        registry = ReleaseRegistry(
            state_dir=tmp_path / "state",
            public_key_pem=public_pem,
            artifact_store=store,
        )
        auth = ClientAuthenticator(
            {
                AUTHORIZED_READER_TOKEN: {STAGING_READ_SCOPE},
                FORBIDDEN_SCOPE_TOKEN: {"unrelated:scope"},
            }
        )
        app = create_update_server_app(registry=registry, authenticator=auth)
        client = TestClient(app)
        yield {
            "s3": s3,
            "store": store,
            "registry": registry,
            "client": client,
            "private_pem": private_pem,
            "public_pem": public_pem,
        }


def test_health_endpoint_contract_and_secret_hygiene(
    minio_env: dict[str, Any],
) -> None:
    client: TestClient = minio_env["client"]
    resp = client.get("/mpips/staging/health")
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "no-store"
    body = resp.json()
    assert body == {
        "status": "ok",
        "service": "mpips-update-server",
        "environment": "staging",
    }
    raw_text = resp.text
    for forbidden in (
        TEST_BUCKET,
        "minio-test-access-key",
        "minio-test-secret-key",
        AUTHORIZED_READER_TOKEN,
    ):
        assert forbidden not in raw_text


def test_latest_release_when_empty(minio_env: dict[str, Any]) -> None:
    client: TestClient = minio_env["client"]
    resp = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "no-store"
    assert resp.json() == {
        "schema_version": 1,
        "channel": "staging",
        "status": "no_release",
    }


def test_end_to_end_release_registration_discovery_presign_and_verification(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    registry: ReleaseRegistry = minio_env["registry"]
    client: TestClient = minio_env["client"]
    s3 = minio_env["s3"]
    private_pem: bytes = minio_env["private_pem"]
    public_pem: bytes = minio_env["public_pem"]

    release_id = "0.1.0-1176a4f7-ubuntu24.04-x86_64-seq1"
    metadata, meta_bytes, sig_bytes = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=release_id,
        sequence=1,
    )

    record = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta_bytes,
        signature_bytes=sig_bytes,
        authorize=True,
        promote=True,
    )
    assert record.authorization_state == "promoted"
    assert (
        record.artifact_object_key
        == f"staging/ubuntu-24.04-x86_64/releases/{release_id}/mpips-runtime.bin"
    )

    # Verify all 3 immutable objects exist in private MinIO bucket
    for fname in ("mpips-runtime.bin", "release.json", "release.sig"):
        key = f"staging/ubuntu-24.04-x86_64/releases/{release_id}/{fname}"
        head = s3.head_object(Bucket=TEST_BUCKET, Key=key)
        assert head["ContentLength"] > 0

    # Discover via GET /mpips/staging/latest.json
    latest_resp = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_resp.status_code == 200
    manifest = latest_resp.json()
    assert manifest["schema_version"] == 1
    assert manifest["channel"] == SUPPORTED_CHANNEL
    assert manifest["status"] == "available"
    assert manifest["platform"] == SUPPORTED_PLATFORM
    assert manifest["release_id"] == release_id
    assert manifest["version"] == "0.1.0"
    assert manifest["sequence"] == 1
    assert manifest["source_commit"] == "1176a4f79bc654c88a24f62cf5793fdf653cf0e9"
    assert manifest["interface_version"] == INTERFACE_VERSION
    assert manifest["release_status"] == "staging"
    assert (
        manifest["download_endpoint"]
        == f"/mpips/staging/releases/{release_id}/download"
    )
    assert "download_url" not in manifest

    expected_sha256 = hashlib.sha256(synthetic_elf_binary.read_bytes()).hexdigest()
    expected_size = synthetic_elf_binary.stat().st_size
    assert expected_size > 0
    assert manifest["artifact"] == {
        "filename": ARTIFACT_FILENAME,
        "sha256": expected_sha256,
        "size_bytes": expected_size,
    }

    # Verify Ed25519 signature over canonical metadata bytes from latest.json
    served_canonical = canonical_metadata_bytes(manifest)
    assert served_canonical == meta_bytes
    sig_raw = decode_signature_b64(manifest["signature"])
    verified = verify_elf_release_metadata(
        served_canonical,
        sig_raw,
        public_pem,
        binary_path=synthetic_elf_binary,
        minimum_sequence=1,
    )
    assert verified["release_id"] == release_id

    # Request authorized download URL
    dl_resp = client.get(
        manifest["download_endpoint"],
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_resp.status_code == 200
    dl_body = dl_resp.json()
    assert dl_body["release_id"] == release_id
    assert dl_body["expires_at"].endswith("Z")
    presigned_url = dl_body["download_url"]
    parsed_url = urlsplit(presigned_url)
    assert parsed_url.scheme == "https"
    expected_path = (
        f"/{TEST_BUCKET}/staging/ubuntu-24.04-x86_64/releases/"
        f"{release_id}/mpips-runtime.bin"
    )
    assert expected_path in parsed_url.path
    query_params = parse_qs(parsed_url.query)
    assert query_params.get("X-Amz-Expires") == ["300"]
    assert "X-Amz-Signature" in query_params
    assert "minio-test-secret-key" not in presigned_url

    # Verify downloaded object bytes from MinIO match SHA-256 and size
    s3_obj = s3.get_object(
        Bucket=TEST_BUCKET,
        Key=f"staging/ubuntu-24.04-x86_64/releases/{release_id}/mpips-runtime.bin",
    )
    downloaded_bytes = s3_obj["Body"].read()
    assert len(downloaded_bytes) == manifest["artifact"]["size_bytes"]
    assert (
        hashlib.sha256(downloaded_bytes).hexdigest() == manifest["artifact"]["sha256"]
    )


def test_unauthorized_and_forbidden_access_rejected(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    registry: ReleaseRegistry = minio_env["registry"]
    client: TestClient = minio_env["client"]
    private_pem: bytes = minio_env["private_pem"]

    release_id = "0.1.0-auth-test-seq1"
    _, meta_bytes, sig_bytes = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=release_id,
        sequence=1,
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta_bytes,
        signature_bytes=sig_bytes,
        authorize=True,
        promote=True,
    )

    for path in (
        "/mpips/staging/latest.json",
        f"/mpips/staging/releases/{release_id}/download",
    ):
        # Missing token -> 401
        r_missing = client.get(path)
        assert r_missing.status_code == 401
        assert r_missing.json()["error"]["code"] == "unauthorized"

        # Invalid token -> 401
        r_wrong = client.get(path, headers={"Authorization": "Bearer wrong-token"})
        assert r_wrong.status_code == 401
        assert r_wrong.json()["error"]["code"] == "unauthorized"

        # Authenticated token without staging:read scope -> 403
        r_forbid = client.get(
            path,
            headers={"Authorization": f"Bearer {FORBIDDEN_SCOPE_TOKEN}"},
        )
        assert r_forbid.status_code == 403
        assert r_forbid.json()["error"]["code"] == "forbidden"


def test_release_immutability_and_object_key_validation(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    registry: ReleaseRegistry = minio_env["registry"]
    private_pem: bytes = minio_env["private_pem"]

    release_id = "0.1.0-immutable-seq1"
    _, meta_bytes, sig_bytes = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=release_id,
        sequence=1,
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta_bytes,
        signature_bytes=sig_bytes,
        authorize=True,
        promote=True,
    )

    # Attempting to overwrite the same release_id must fail closed
    with pytest.raises(ReleaseConflictError):
        registry.register_and_upload_release(
            binary_path=synthetic_elf_binary,
            metadata_bytes=meta_bytes,
            signature_bytes=sig_bytes,
        )

    # Attempting to reuse sequence 1 with a different release_id must fail closed
    _, meta2, sig2 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id="0.1.0-duplicate-seq1",
        sequence=1,
    )
    with pytest.raises(ReleaseConflictError):
        registry.register_and_upload_release(
            binary_path=synthetic_elf_binary,
            metadata_bytes=meta2,
            signature_bytes=sig2,
        )

    # Strict object key validation rejects production channel, traversal, and DICOM/TRX
    for bad_args in (
        ("0.1.0-ok", "mpips-runtime.bin", "production", SUPPORTED_PLATFORM),
        ("../traversal", "mpips-runtime.bin", SUPPORTED_CHANNEL, SUPPORTED_PLATFORM),
        ("0.1.0-ok", "patient.dcm", SUPPORTED_CHANNEL, SUPPORTED_PLATFORM),
        (
            "0.1.0-ok",
            "trx-calibration-606db560.tar.gz",
            SUPPORTED_CHANNEL,
            SUPPORTED_PLATFORM,
        ),
        ("0.1.0-ok", "mpips-runtime.bin", SUPPORTED_CHANNEL, "ubuntu-20.04-x86_64"),
    ):
        with pytest.raises(ValueError):
            build_release_object_key(
                bad_args[0],
                bad_args[1],
                channel=bad_args[2],
                platform_name=bad_args[3],
            )


def test_incompatible_platform_expired_metadata_and_tampered_signature_rejected(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    registry: ReleaseRegistry = minio_env["registry"]
    client: TestClient = minio_env["client"]
    private_pem: bytes = minio_env["private_pem"]

    # Tampered signature rejected at registration
    _, meta_bytes, sig_bytes = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id="0.1.0-tampered-sig",
        sequence=1,
    )
    bad_sig = bytes([sig_bytes[0] ^ 0xFF]) + sig_bytes[1:]
    with pytest.raises(ReleaseValidationError):
        registry.register_and_upload_release(
            binary_path=synthetic_elf_binary,
            metadata_bytes=meta_bytes,
            signature_bytes=bad_sig,
        )

    # Register valid release, then test expired metadata and incompatible platform
    release_id = "0.1.0-valid-seq1"
    _, valid_meta, valid_sig = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=release_id,
        sequence=1,
        expires_delta=timedelta(hours=1),
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=valid_meta,
        signature_bytes=valid_sig,
        authorize=True,
        promote=True,
    )

    # Incompatible platform rejected with 422 on both latest.json and download
    for path in (
        "/mpips/staging/latest.json?platform=ubuntu-22.04-x86_64",
        f"/mpips/staging/releases/{release_id}/download?platform=ubuntu-24.04-arm64",
    ):
        resp = client.get(
            path,
            headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "incompatible_platform"

    # Simulated future clock past metadata expiry fails closed
    future_now = datetime.now(timezone.utc) + timedelta(hours=2)
    with pytest.raises(ReleaseValidationError):
        registry.get_latest_release(now=future_now)
    with pytest.raises(ReleaseValidationError):
        registry.get_authorized_release_for_download(release_id, now=future_now)


def test_rollback_and_replay_protection_with_monotonic_sequence(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    registry: ReleaseRegistry = minio_env["registry"]
    client: TestClient = minio_env["client"]
    private_pem: bytes = minio_env["private_pem"]

    # Register and promote sequence 2
    _, meta2, sig2 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id="0.1.0-release-seq2",
        sequence=2,
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta2,
        signature_bytes=sig2,
        authorize=True,
        promote=True,
    )

    # Register sequence 1 (older sequence) and attempt to promote -> rejected!
    _, meta1, sig1 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id="0.1.0-older-seq1",
        sequence=1,
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta1,
        signature_bytes=sig1,
        authorize=True,
        promote=False,
    )
    with pytest.raises(ChannelSequenceConflictError):
        registry.promote_release(
            release_id="0.1.0-older-seq1",
            expected_current_sequence=2,
        )

    # Attempting to download superseded sequence 1 via HTTP returns 409 Conflict
    superseded_resp = client.get(
        "/mpips/staging/releases/0.1.0-older-seq1/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert superseded_resp.status_code == 409
    assert superseded_resp.json()["error"]["code"] == "release_superseded"

    # Authorized rollback using a newly signed higher sequence (sequence 3) succeeds
    _, meta3, sig3 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id="0.1.0-rollback-to-known-good-seq3",
        sequence=3,
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta3,
        signature_bytes=sig3,
        authorize=True,
        promote=True,
    )
    latest_resp = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_resp.status_code == 200
    assert latest_resp.json()["sequence"] == 3
    assert latest_resp.json()["release_id"] == "0.1.0-rollback-to-known-good-seq3"


def test_missing_object_and_minio_unavailable_failure_modes(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry: ReleaseRegistry = minio_env["registry"]
    client: TestClient = minio_env["client"]
    s3 = minio_env["s3"]
    private_pem: bytes = minio_env["private_pem"]

    # Unknown release_id -> 404
    unknown_resp = client.get(
        "/mpips/staging/releases/0.1.0-does-not-exist/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert unknown_resp.status_code == 404
    assert unknown_resp.json()["error"]["code"] == "release_not_found"

    # Register & promote release, corrupt binary -> ArtifactIntegrityError / 422
    release_id = "0.1.0-missing-obj-seq1"
    _, meta_bytes, sig_bytes = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=release_id,
        sequence=1,
    )
    registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta_bytes,
        signature_bytes=sig_bytes,
        authorize=True,
        promote=True,
    )
    bin_key = f"staging/ubuntu-24.04-x86_64/releases/{release_id}/mpips-runtime.bin"
    s3.put_object(Bucket=TEST_BUCKET, Key=bin_key, Body=b"corrupted-size")
    with pytest.raises(ArtifactIntegrityError):
        minio_env["store"].verify_release_objects(
            release_id=release_id,
            expected_size_bytes=synthetic_elf_binary.stat().st_size,
        )
    corrupt_dl = client.get(
        f"/mpips/staging/releases/{release_id}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert corrupt_dl.status_code == 422
    assert corrupt_dl.json()["error"]["code"] == "invalid_release"

    # Delete binary from MinIO -> 404 artifact_not_found
    s3.delete_object(Bucket=TEST_BUCKET, Key=bin_key)

    missing_dl = client.get(
        f"/mpips/staging/releases/{release_id}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert missing_dl.status_code == 404
    assert missing_dl.json()["error"]["code"] == "artifact_not_found"

    # Simulate MinIO connection outage -> 503 storage_unavailable with no leaked secrets
    def _raise_outage(*_args: Any, **_kwargs: Any) -> Any:
        raise EndpointConnectionError(endpoint_url="https://s3.internal.invalid")

    monkeypatch.setattr(s3, "head_object", _raise_outage)
    outage_resp = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert outage_resp.status_code == 503
    assert outage_resp.json()["error"]["code"] == "storage_unavailable"
    assert "s3.internal.invalid" not in outage_resp.text
    assert TEST_BUCKET not in outage_resp.text


def test_presigned_url_ttl_bounds_enforced(minio_env: dict[str, Any]) -> None:
    s3 = minio_env["s3"]
    for invalid_ttl in (0, 30, 901, 86400):
        with pytest.raises(ValueError):
            MinIOArtifactStore(
                s3_client=s3,
                bucket=TEST_BUCKET,
                presign_ttl_seconds=invalid_ttl,
            )


def test_pre_promotion_binary_sha256_integrity_catches_corruption_and_truncation(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify verify_release_objects(..., verify_binary_sha256=True) & promote.

    Exercises:
    1. Same-size stored binary corruption (head_object ContentLength matches,
       but stored ELF payload bytes have a flipped bit -> SHA-256 mismatch).
    2. Truncated object stream (head_object reports expected ContentLength,
       but get_object stream yields fewer bytes).
    3. Oversized object stream (get_object stream yields more bytes than expected).
    """
    registry: ReleaseRegistry = minio_env["registry"]
    store: MinIOArtifactStore = minio_env["store"]
    s3 = minio_env["s3"]
    private_pem: bytes = minio_env["private_pem"]

    release_id = "0.1.0-sha256-integrity-seq1"
    metadata, meta_bytes, sig_bytes = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=release_id,
        sequence=1,
    )
    expected_sha256 = str(metadata["artifact"]["sha256"])
    expected_size = int(metadata["artifact"]["size_bytes"])

    # Stage release without promoting yet
    record = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta_bytes,
        signature_bytes=sig_bytes,
        authorize=True,
        promote=False,
    )
    assert record.authorization_state == "authorized"

    # Full SHA-256 check passes on intact stored binary
    verified_info = store.verify_release_objects(
        release_id=release_id,
        expected_size_bytes=expected_size,
        expected_sha256=expected_sha256,
        expected_metadata_bytes=meta_bytes,
        expected_signature_bytes=sig_bytes,
        verify_binary_sha256=True,
    )
    assert verified_info["sha256"] == expected_sha256
    assert verified_info["size_bytes"] == expected_size

    bin_key = f"staging/ubuntu-24.04-x86_64/releases/{release_id}/mpips-runtime.bin"
    original_bytes = synthetic_elf_binary.read_bytes()

    # 1. Same-size bit-flip corruption in stored MinIO object
    corrupted_same_size = bytearray(original_bytes)
    corrupted_same_size[-1] ^= 0xFF
    s3.put_object(
        Bucket=TEST_BUCKET,
        Key=bin_key,
        Body=bytes(corrupted_same_size),
    )

    # Size-only check wouldn't catch same-size corruption, verify_binary_sha256 does
    with pytest.raises(ArtifactIntegrityError, match="Stored binary SHA-256 mismatch"):
        store.verify_release_objects(
            release_id=release_id,
            expected_size_bytes=expected_size,
            expected_sha256=expected_sha256,
            verify_binary_sha256=True,
        )

    # promote_release and authorize_release enforce verify_binary_sha256=True
    with pytest.raises(ArtifactIntegrityError, match="Stored binary SHA-256 mismatch"):
        registry.promote_release(
            release_id=release_id,
            expected_current_sequence=0,
        )
    with pytest.raises(ArtifactIntegrityError, match="Stored binary SHA-256 mismatch"):
        registry.authorize_release(release_id)
    assert registry.get_current_sequence() == 0

    # Restore valid object bytes
    s3.put_object(Bucket=TEST_BUCKET, Key=bin_key, Body=original_bytes)

    # 2. Simulated truncated stream from S3 get_object (even when head_object matches)
    real_get_object = s3.get_object

    class _TruncatedStream:
        def __init__(self, data: bytes) -> None:
            self._data = data[:-16]
            self._offset = 0
            self.closed = False

        def read(self, amt: int | None = None) -> bytes:
            if self._offset >= len(self._data):
                return b""
            n = len(self._data) if amt is None else amt
            chunk = self._data[self._offset : self._offset + n]
            self._offset += len(chunk)
            return chunk

        def close(self) -> None:
            self.closed = True

    truncated_body = _TruncatedStream(original_bytes)

    def _mock_truncated_get_object(*, Bucket: str, Key: str) -> dict[str, Any]:
        if Key == bin_key:
            return {"Body": truncated_body, "ContentLength": expected_size}
        res: dict[str, Any] = real_get_object(Bucket=Bucket, Key=Key)
        return res

    monkeypatch.setattr(s3, "get_object", _mock_truncated_get_object)
    with pytest.raises(
        ArtifactIntegrityError,
        match="Stored binary stream truncated before expected size",
    ):
        store.verify_release_objects(
            release_id=release_id,
            expected_size_bytes=expected_size,
            expected_sha256=expected_sha256,
            verify_binary_sha256=True,
        )
    assert truncated_body.closed is True

    # 3. Simulated oversized stream from S3 get_object
    class _OversizedStream:
        def __init__(self, data: bytes) -> None:
            self._data = data + b"EXTRA_TRAILING_BYTES"
            self._offset = 0
            self.closed = False

        def read(self, amt: int | None = None) -> bytes:
            if self._offset >= len(self._data):
                return b""
            n = len(self._data) if amt is None else amt
            chunk = self._data[self._offset : self._offset + n]
            self._offset += len(chunk)
            return chunk

        def close(self) -> None:
            self.closed = True

    oversized_body = _OversizedStream(original_bytes)

    def _mock_oversized_get_object(*, Bucket: str, Key: str) -> dict[str, Any]:
        if Key == bin_key:
            return {"Body": oversized_body, "ContentLength": expected_size}
        res: dict[str, Any] = real_get_object(Bucket=Bucket, Key=Key)
        return res

    monkeypatch.setattr(s3, "get_object", _mock_oversized_get_object)
    with pytest.raises(
        ArtifactIntegrityError,
        match="Stored binary stream exceeded expected size bounds",
    ):
        store.verify_release_objects(
            release_id=release_id,
            expected_size_bytes=expected_size,
            expected_sha256=expected_sha256,
            verify_binary_sha256=True,
        )
    assert oversized_body.closed is True

    # Restore real get_object and confirm promotion succeeds
    monkeypatch.setattr(s3, "get_object", real_get_object)
    promoted = registry.promote_release(
        release_id=release_id,
        expected_current_sequence=0,
    )
    assert promoted.authorization_state == "promoted"
    assert registry.get_current_sequence() == 1


def test_release_revocation_and_monotonic_recovery_lifecycle(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    """Verify safe release revocation across unpromoted and promoted states.

    Distinguishes:
    1. Registered but unpromoted release revocation (blocks promotion & download,
       preserves allocated sequence so it cannot be reused).
    2. Post-promotion release revocation (causes /latest.json and /download to
       fail closed with 403 release_unauthorized while preserving monotonic
       channel sequence history).
    3. Forward recovery by registering and promoting sequence = highest_allocated + 1.
    """
    registry: ReleaseRegistry = minio_env["registry"]
    client: TestClient = minio_env["client"]
    private_pem: bytes = minio_env["private_pem"]

    # 1. Register sequence 1 without promoting, then revoke it before promotion
    rel_seq1 = "0.1.0-staged-unpromoted-seq1"
    _, meta1, sig1 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=rel_seq1,
        sequence=1,
    )
    rec1 = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta1,
        signature_bytes=sig1,
        authorize=True,
        promote=False,
    )
    assert rec1.authorization_state == "authorized"
    assert registry.get_current_sequence() == 0
    assert registry.get_highest_allocated_sequence() == 1

    revoked1 = registry.revoke_release(rel_seq1)
    assert revoked1.authorization_state == "revoked"
    # Channel pointer is still 0 (no_release), but sequence 1 remains allocated
    assert registry.get_current_sequence() == 0
    assert registry.get_highest_allocated_sequence() == 1

    with pytest.raises(ReleaseUnauthorizedError):
        registry.promote_release(release_id=rel_seq1, expected_current_sequence=0)
    with pytest.raises(ReleaseUnauthorizedError):
        registry.authorize_release(rel_seq1)

    dl_seq1 = client.get(
        f"/mpips/staging/releases/{rel_seq1}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_seq1.status_code == 403
    assert dl_seq1.json()["error"]["code"] == "release_unauthorized"

    # Attempting to reuse sequence 1 with a new release_id is rejected
    _, meta1_dup, sig1_dup = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id="0.1.0-reuse-seq1",
        sequence=1,
    )
    with pytest.raises(ReleaseConflictError):
        registry.register_and_upload_release(
            binary_path=synthetic_elf_binary,
            metadata_bytes=meta1_dup,
            signature_bytes=sig1_dup,
        )

    # 2. Register and promote sequence 2, then revoke post-promotion
    rel_seq2 = "0.1.0-promoted-then-revoked-seq2"
    _, meta2, sig2 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=rel_seq2,
        sequence=2,
    )
    rec2 = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta2,
        signature_bytes=sig2,
        authorize=True,
        promote=True,
    )
    assert rec2.authorization_state == "promoted"
    assert registry.get_current_sequence() == 2
    assert registry.get_highest_allocated_sequence() == 2

    revoked2 = registry.revoke_release(rel_seq2)
    assert revoked2.authorization_state == "revoked"
    # Monotonic channel sequence remains 2
    assert registry.get_current_sequence() == 2
    assert registry.get_highest_allocated_sequence() == 2

    # Both /latest.json and /download fail closed with 403 release_unauthorized
    latest_after_revoke = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_after_revoke.status_code == 403
    assert latest_after_revoke.json()["error"]["code"] == "release_unauthorized"

    dl_after_revoke = client.get(
        f"/mpips/staging/releases/{rel_seq2}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_after_revoke.status_code == 403
    assert dl_after_revoke.json()["error"]["code"] == "release_unauthorized"

    # 3. Forward recovery with sequence 3 (highest_allocated + 1)
    rel_seq3 = "0.1.0-recovery-seq3"
    _, meta3, sig3 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=rel_seq3,
        sequence=3,
    )
    rec3 = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta3,
        signature_bytes=sig3,
        authorize=True,
        promote=False,
    )
    assert rec3.authorization_state == "authorized"
    assert registry.get_highest_allocated_sequence() == 3

    promoted3 = registry.promote_release(
        release_id=rel_seq3,
        expected_current_sequence=2,
    )
    assert promoted3.authorization_state == "promoted"
    assert registry.get_current_sequence() == 3

    latest_recovered = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_recovered.status_code == 200
    assert latest_recovered.json()["release_id"] == rel_seq3
    assert latest_recovered.json()["sequence"] == 3

    all_releases = registry.list_releases()
    assert [
        (r.release_id, r.sequence, r.authorization_state) for r in all_releases
    ] == [
        (rel_seq1, 1, "revoked"),
        (rel_seq2, 2, "revoked"),
        (rel_seq3, 3, "promoted"),
    ]

    with pytest.raises(ReleaseNotFoundError):
        registry.revoke_release("0.1.0-unknown-release")


def test_staging_workflow_enforces_dedicated_reader_token_no_fallback() -> None:
    """Static regression check on .github/workflows/deploy-staging-update-server.yml."""
    repo_root = Path(__file__).resolve().parents[1]
    workflow_path = (
        repo_root / ".github" / "workflows" / "deploy-staging-update-server.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    # 1. Must not reference secrets.MPIPS_API_KEY anywhere in staging update workflow
    assert "MPIPS_API_KEY" not in content
    # 2. Must require secrets.MPIPS_UPDATE_STAGING_READER_TOKEN
    assert "secrets.MPIPS_UPDATE_STAGING_READER_TOKEN" in content
    # 3. Validate dedicated credentials step runs before writing .env.staging
    validate_idx = content.index(
        "name: Validate dedicated staging credentials and environment"
    )
    setup_idx = content.index("name: Set up deployment environment")
    compose_env_idx = content.index('COMPOSE_ENV="$BASE_DIR/.env.staging"')
    deploy_idx = content.index("name: Deploy Staging Update Server via Compose")
    assert validate_idx < setup_idx < compose_env_idx < deploy_idx
    # 4. Preserves Ed25519 key lifecycle and bootstrap marker checks
    assert 'BOOTSTRAP_MARKER="$STATE_DIR/.bootstrapped"' in content
    expected_guard = (
        "Refusing implicit key regeneration to prevent replacing "
        "deployed trust identity."
    )
    assert expected_guard in content


def test_download_gate_permits_only_currently_promoted_non_revoked_release(
    minio_env: dict[str, Any],
    synthetic_elf_binary: Path,
) -> None:
    """Verify strict Grabber download gate across release states.

    - Registered/authorized but unpromoted release (when channel has no release or
      when a lower sequence is currently promoted) -> rejected on /download (403
      release_unauthorized), not exposed on /latest.json, but inspectable via
      administrative registry/storage APIs (list_releases / verify_release_objects).
    - Currently promoted release -> permitted on /latest.json and /download (200 OK).
    - Superseded previously promoted release -> rejected on /download (409
      release_superseded).
    - Revoked release -> rejected on /latest.json and /download (403
      release_unauthorized).
    """
    registry: ReleaseRegistry = minio_env["registry"]
    store: MinIOArtifactStore = minio_env["store"]
    client: TestClient = minio_env["client"]
    private_pem: bytes = minio_env["private_pem"]

    # 1. Register & authorize sequence 1 WITHOUT promoting (promote=False)
    rel_seq1 = "0.1.0-authorized-unpromoted-seq1"
    meta1_dict, meta1, sig1 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=rel_seq1,
        sequence=1,
    )
    rec1 = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta1,
        signature_bytes=sig1,
        authorize=True,
        promote=False,
    )
    assert rec1.authorization_state == "authorized"

    # Inspectable through administrative registry/storage operations
    assert [r.release_id for r in registry.list_releases()] == [rel_seq1]
    verified1 = store.verify_release_objects(
        release_id=rel_seq1,
        expected_size_bytes=int(meta1_dict["artifact"]["size_bytes"]),
        expected_sha256=str(meta1_dict["artifact"]["sha256"]),
        expected_metadata_bytes=meta1,
        expected_signature_bytes=sig1,
        verify_binary_sha256=True,
    )
    assert verified1["sha256"] == meta1_dict["artifact"]["sha256"]

    # Not exposed on /mpips/staging/latest.json
    latest_unpromoted = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_unpromoted.status_code == 200
    assert latest_unpromoted.json()["status"] == "no_release"

    # Direct Grabber download of authorized-but-unpromoted release is rejected (403)
    with pytest.raises(ReleaseUnauthorizedError):
        registry.get_authorized_release_for_download(rel_seq1)

    dl_unpromoted = client.get(
        f"/mpips/staging/releases/{rel_seq1}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_unpromoted.status_code == 403
    assert dl_unpromoted.json()["error"]["code"] == "release_unauthorized"

    # 2. Promote sequence 1 -> now active on /latest.json and permitted on /download
    promoted1 = registry.promote_release(
        release_id=rel_seq1,
        expected_current_sequence=0,
    )
    assert promoted1.authorization_state == "promoted"

    latest_promoted1 = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_promoted1.status_code == 200
    assert latest_promoted1.json()["status"] == "available"
    assert latest_promoted1.json()["release_id"] == rel_seq1

    dl_promoted1 = client.get(
        f"/mpips/staging/releases/{rel_seq1}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_promoted1.status_code == 200
    assert dl_promoted1.json()["release_id"] == rel_seq1

    # 3. Stage sequence 2 as authorized-but-unpromoted while sequence 1 is promoted
    rel_seq2 = "0.1.0-staged-next-seq2"
    _, meta2, sig2 = _build_signed_bundle(
        synthetic_elf_binary,
        private_pem,
        release_id=rel_seq2,
        sequence=2,
    )
    rec2 = registry.register_and_upload_release(
        binary_path=synthetic_elf_binary,
        metadata_bytes=meta2,
        signature_bytes=sig2,
        authorize=True,
        promote=False,
    )
    assert rec2.authorization_state == "authorized"

    # /latest.json still serves seq 1; direct /download of unpromoted seq 2 fails (403)
    latest_still_1 = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_still_1.status_code == 200
    assert latest_still_1.json()["release_id"] == rel_seq1

    dl_unpromoted2 = client.get(
        f"/mpips/staging/releases/{rel_seq2}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_unpromoted2.status_code == 403
    assert dl_unpromoted2.json()["error"]["code"] == "release_unauthorized"

    # 4. Promote seq 2 -> seq 2 succeeds (200), superseded seq 1 fails (409)
    registry.promote_release(
        release_id=rel_seq2,
        expected_current_sequence=1,
    )
    dl_promoted2 = client.get(
        f"/mpips/staging/releases/{rel_seq2}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_promoted2.status_code == 200
    assert dl_promoted2.json()["release_id"] == rel_seq2

    dl_superseded1 = client.get(
        f"/mpips/staging/releases/{rel_seq1}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_superseded1.status_code == 409
    assert dl_superseded1.json()["error"]["code"] == "release_superseded"

    # 5. Revoke promoted seq 2 -> both /latest.json and /download fail (403)
    registry.revoke_release(rel_seq2)
    latest_revoked2 = client.get(
        "/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert latest_revoked2.status_code == 403
    assert latest_revoked2.json()["error"]["code"] == "release_unauthorized"

    dl_revoked2 = client.get(
        f"/mpips/staging/releases/{rel_seq2}/download",
        headers={"Authorization": f"Bearer {AUTHORIZED_READER_TOKEN}"},
    )
    assert dl_revoked2.status_code == 403
    assert dl_revoked2.json()["error"]["code"] == "release_unauthorized"
