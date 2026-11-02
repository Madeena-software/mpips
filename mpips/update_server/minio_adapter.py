"""MinIO S3-compatible storage adapter for immutable MPIPS ELF releases."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from mpips.storage import get_s3_client
from mpips.update_server.release_metadata import (
    ARTIFACT_FILENAME,
    RELEASE_ID_RE,
    SUPPORTED_CHANNEL,
    SUPPORTED_PLATFORM,
    sha256_file,
)

DEFAULT_ARTIFACT_BUCKET = "mhcs-mpips-artifacts"
ALLOWED_RELEASE_FILENAMES = frozenset(
    {ARTIFACT_FILENAME, "release.json", "release.sig"}
)
DEFAULT_PRESIGN_TTL_SECONDS = 300
MIN_PRESIGN_TTL_SECONDS = 60
MAX_PRESIGN_TTL_SECONDS = 900


class UpdateStorageError(RuntimeError):
    """Sanitized base error for update server storage operations."""


class ArtifactNotFoundError(UpdateStorageError):
    """Requested release artifact does not exist in storage."""


class ArtifactIntegrityError(UpdateStorageError):
    """Stored artifact metadata or size does not match registered expectations."""


class ReleaseConflictError(UpdateStorageError):
    """Release artifact already exists and is immutable."""


class StorageUnavailableError(UpdateStorageError):
    """Underlying S3/MinIO storage is unreachable or returned an error."""


@dataclass(frozen=True)
class PresignedDownload:
    """Short-lived presigned download URL descriptor."""

    release_id: str
    download_url: str
    expires_at: str


def resolve_artifact_bucket(explicit_bucket: str | None = None) -> str:
    """Resolve configured MinIO bucket name."""
    bucket = (
        explicit_bucket
        or os.getenv("MPIPS_UPDATE_S3_BUCKET")
        or os.getenv("AWS_BUCKET")
        or DEFAULT_ARTIFACT_BUCKET
    ).strip()
    if not bucket:
        raise ValueError("Artifact storage bucket name must not be empty")
    return bucket


def build_release_object_key(
    release_id: str,
    filename: str,
    *,
    channel: str = SUPPORTED_CHANNEL,
    platform_name: str = SUPPORTED_PLATFORM,
) -> str:
    """Build and strictly validate a fixed server-side MinIO object key."""
    if channel != SUPPORTED_CHANNEL:
        raise ValueError("Only staging namespace is permitted")
    if platform_name != SUPPORTED_PLATFORM:
        raise ValueError("Unsupported target platform")
    if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
        raise ValueError("Invalid release_id for object key")
    if filename not in ALLOWED_RELEASE_FILENAMES:
        raise ValueError("Disallowed release artifact filename")
    return f"{channel}/{platform_name}/releases/{release_id}/{filename}"


class MinIOArtifactStore:
    """Private MinIO storage adapter enforcing immutable staging release keys."""

    def __init__(
        self,
        s3_client: Any | None = None,
        bucket: str | None = None,
        presign_ttl_seconds: int | None = None,
    ) -> None:
        self._s3 = s3_client if s3_client is not None else get_s3_client()
        self._bucket = resolve_artifact_bucket(bucket)
        raw_ttl = (
            presign_ttl_seconds
            if presign_ttl_seconds is not None
            else int(
                os.getenv(
                    "MPIPS_UPDATE_PRESIGN_TTL_SECONDS",
                    str(DEFAULT_PRESIGN_TTL_SECONDS),
                )
            )
        )
        if not (MIN_PRESIGN_TTL_SECONDS <= raw_ttl <= MAX_PRESIGN_TTL_SECONDS):
            raise ValueError("Presigned URL TTL outside permitted bounds")
        self._presign_ttl_seconds = raw_ttl

    @property
    def presign_ttl_seconds(self) -> int:
        return self._presign_ttl_seconds

    def _head_object_Or_none(self, key: str) -> dict[str, Any] | None:
        try:
            resp: dict[str, Any] = self._s3.head_object(Bucket=self._bucket, Key=key)
            return resp
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise StorageUnavailableError(
                "Artifact storage verification failed"
            ) from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError("Artifact storage unreachable") from exc

    def ensure_release_not_present(
        self,
        release_id: str,
        *,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
    ) -> None:
        """Verify that none of the immutable release components already exist."""
        for filename in sorted(ALLOWED_RELEASE_FILENAMES):
            key = build_release_object_key(
                release_id,
                filename,
                channel=channel,
                platform_name=platform_name,
            )
            if self._head_object_Or_none(key) is not None:
                raise ReleaseConflictError(
                    "Immutable release artifact already exists in storage"
                )

    def upload_release_bundle(
        self,
        *,
        release_id: str,
        binary_path: Path,
        metadata_bytes: bytes,
        signature_bytes: bytes,
        expected_sha256: str,
        expected_size_bytes: int,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
    ) -> str:
        """Upload immutable binary, release.json, and release.sig to staging prefix."""
        if not binary_path.is_file():
            raise ArtifactIntegrityError("Local release binary file does not exist")
        actual_size = binary_path.stat().st_size
        actual_sha256 = sha256_file(binary_path)
        if actual_size != expected_size_bytes or actual_sha256 != expected_sha256:
            raise ArtifactIntegrityError(
                "Local release binary size or SHA-256 mismatch"
            )
        if len(signature_bytes) != 64:
            raise ArtifactIntegrityError("Detached signature must be 64 bytes")

        self.ensure_release_not_present(
            release_id,
            channel=channel,
            platform_name=platform_name,
        )

        bin_key = build_release_object_key(
            release_id,
            ARTIFACT_FILENAME,
            channel=channel,
            platform_name=platform_name,
        )
        meta_key = build_release_object_key(
            release_id,
            "release.json",
            channel=channel,
            platform_name=platform_name,
        )
        sig_key = build_release_object_key(
            release_id,
            "release.sig",
            channel=channel,
            platform_name=platform_name,
        )

        try:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=meta_key,
                Body=metadata_bytes,
                ContentType="application/json",
            )
            self._s3.put_object(
                Bucket=self._bucket,
                Key=sig_key,
                Body=signature_bytes,
                ContentType="application/octet-stream",
            )
            with binary_path.open("rb") as stream:
                self._s3.put_object(
                    Bucket=self._bucket,
                    Key=bin_key,
                    Body=stream,
                    ContentLength=expected_size_bytes,
                    ContentType="application/octet-stream",
                )
        except (ClientError, BotoCoreError, OSError) as exc:
            raise StorageUnavailableError("Failed to upload release bundle") from exc

        self.verify_release_objects(
            release_id=release_id,
            expected_size_bytes=expected_size_bytes,
            expected_metadata_bytes=metadata_bytes,
            expected_signature_bytes=signature_bytes,
            channel=channel,
            platform_name=platform_name,
        )
        return bin_key

    def verify_release_objects(
        self,
        *,
        release_id: str,
        expected_size_bytes: int,
        expected_metadata_bytes: bytes | None = None,
        expected_signature_bytes: bytes | None = None,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
    ) -> dict[str, Any]:
        """Verify binary existence/size and optional metadata/signature bytes."""
        bin_key = build_release_object_key(
            release_id,
            ARTIFACT_FILENAME,
            channel=channel,
            platform_name=platform_name,
        )
        meta_key = build_release_object_key(
            release_id,
            "release.json",
            channel=channel,
            platform_name=platform_name,
        )
        sig_key = build_release_object_key(
            release_id,
            "release.sig",
            channel=channel,
            platform_name=platform_name,
        )

        bin_head = self._head_object_Or_none(bin_key)
        meta_head = self._head_object_Or_none(meta_key)
        sig_head = self._head_object_Or_none(sig_key)
        if bin_head is None or meta_head is None or sig_head is None:
            raise ArtifactNotFoundError("Release artifact object missing in storage")

        content_length = int(bin_head.get("ContentLength", -1))
        if content_length != expected_size_bytes or content_length <= 0:
            raise ArtifactIntegrityError("Stored binary size mismatch")
        if int(sig_head.get("ContentLength", -1)) != 64:
            raise ArtifactIntegrityError("Stored signature size mismatch")

        if expected_metadata_bytes is not None or expected_signature_bytes is not None:
            try:
                if expected_metadata_bytes is not None:
                    meta_obj = self._s3.get_object(Bucket=self._bucket, Key=meta_key)
                    if meta_obj["Body"].read() != expected_metadata_bytes:
                        raise ArtifactIntegrityError(
                            "Stored release.json bytes mismatch"
                        )
                if expected_signature_bytes is not None:
                    sig_obj = self._s3.get_object(Bucket=self._bucket, Key=sig_key)
                    if sig_obj["Body"].read() != expected_signature_bytes:
                        raise ArtifactIntegrityError(
                            "Stored release.sig bytes mismatch"
                        )
            except (ClientError, BotoCoreError) as exc:
                raise StorageUnavailableError(
                    "Failed to read release metadata from storage"
                ) from exc

        return {
            "binary_key": bin_key,
            "size_bytes": content_length,
        }

    def generate_presigned_download(
        self,
        *,
        release_id: str,
        expected_size_bytes: int,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
        ttl_seconds: int | None = None,
        now: datetime | None = None,
    ) -> PresignedDownload:
        """Verify artifact existence and generate a short-lived presigned GET URL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._presign_ttl_seconds
        if not (MIN_PRESIGN_TTL_SECONDS <= ttl <= MAX_PRESIGN_TTL_SECONDS):
            raise ValueError("Presigned URL TTL outside permitted bounds")

        self.verify_release_objects(
            release_id=release_id,
            expected_size_bytes=expected_size_bytes,
            channel=channel,
            platform_name=platform_name,
        )
        bin_key = build_release_object_key(
            release_id,
            ARTIFACT_FILENAME,
            channel=channel,
            platform_name=platform_name,
        )
        ref_now = now or datetime.now(timezone.utc)
        expires_at = (ref_now + timedelta(seconds=ttl)).astimezone(timezone.utc)
        try:
            url = str(
                self._s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": bin_key},
                    ExpiresIn=ttl,
                )
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageUnavailableError(
                "Failed to generate presigned download URL"
            ) from exc

        return PresignedDownload(
            release_id=release_id,
            download_url=url,
            expires_at=expires_at.isoformat().replace("+00:00", "Z"),
        )

