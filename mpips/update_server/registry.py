"""Durable atomic release registry and channel pointer management."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mpips.update_server.minio_adapter import (
    MinIOArtifactStore,
    ReleaseConflictError,
    build_release_object_key,
)
from mpips.update_server.release_metadata import (
    ARTIFACT_FILENAME,
    RELEASE_ID_RE,
    SUPPORTED_CHANNEL,
    SUPPORTED_PLATFORM,
    decode_signature_b64,
    encode_signature_b64,
    validate_platform_compatibility,
    verify_elf_release_metadata,
)


class ReleaseRegistryError(RuntimeError):
    """Base error for release registry operations."""


class ReleaseNotFoundError(ReleaseRegistryError):
    """Requested release ID is unknown."""


class ReleaseUnauthorizedError(ReleaseRegistryError):
    """Release exists but is not authorized for distribution."""


class ReleaseValidationError(ReleaseRegistryError):
    """Release metadata, signature, compatibility, or sequence is invalid."""


class ChannelSequenceConflictError(ReleaseRegistryError):
    """Channel promotion sequence mismatch or replay/rollback attempt."""


@dataclass(frozen=True)
class RegisteredRelease:
    """Immutable registered release record."""

    channel: str
    platform: str
    release_id: str
    version: str
    sequence: int
    source_commit: str
    interface_version: str
    artifact_filename: str
    sha256: str
    size_bytes: int
    artifact_object_key: str
    signed_metadata_b64: str
    signature_b64: str
    release_status: str
    authorization_state: str
    expires_at: str
    compatibility: dict[str, str]
    registered_at: str

    @property
    def metadata_bytes(self) -> bytes:
        return base64.b64decode(self.signed_metadata_b64.encode("ascii"))

    @property
    def signature_bytes(self) -> bytes:
        return decode_signature_b64(self.signature_b64)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "platform": self.platform,
            "release_id": self.release_id,
            "version": self.version,
            "sequence": self.sequence,
            "source_commit": self.source_commit,
            "interface_version": self.interface_version,
            "artifact_filename": self.artifact_filename,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "artifact_object_key": self.artifact_object_key,
            "signed_metadata_b64": self.signed_metadata_b64,
            "signature_b64": self.signature_b64,
            "release_status": self.release_status,
            "authorization_state": self.authorization_state,
            "expires_at": self.expires_at,
            "compatibility": dict(self.compatibility),
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegisteredRelease:
        return cls(
            channel=str(data["channel"]),
            platform=str(data["platform"]),
            release_id=str(data["release_id"]),
            version=str(data["version"]),
            sequence=int(data["sequence"]),
            source_commit=str(data["source_commit"]),
            interface_version=str(data["interface_version"]),
            artifact_filename=str(data["artifact_filename"]),
            sha256=str(data["sha256"]),
            size_bytes=int(data["size_bytes"]),
            artifact_object_key=str(data["artifact_object_key"]),
            signed_metadata_b64=str(data["signed_metadata_b64"]),
            signature_b64=str(data["signature_b64"]),
            release_status=str(data["release_status"]),
            authorization_state=str(data["authorization_state"]),
            expires_at=str(data["expires_at"]),
            compatibility=dict(data["compatibility"]),
            registered_at=str(data["registered_at"]),
        )


class ReleaseRegistry:
    """Thread-safe, atomically persisted release registry with Ed25519 verification."""

    def __init__(
        self,
        state_dir: Path,
        public_key_pem: bytes,
        artifact_store: MinIOArtifactStore,
    ) -> None:
        self._state_dir = Path(state_dir).resolve()
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._state_dir / "registry.json"
        self._public_key_pem = public_key_pem
        self._store = artifact_store
        self._lock = threading.RLock()

    @property
    def artifact_store(self) -> MinIOArtifactStore:
        return self._store

    def _load_state(self) -> dict[str, Any]:
        if not self._state_file.exists():
            return {"schema_version": 1, "releases": {}, "channels": {}}
        raw = json.loads(self._state_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ReleaseRegistryError("Corrupted registry state")
        return raw

    def _save_state(self, state: dict[str, Any]) -> None:
        fd, temp_path = tempfile.mkstemp(prefix=".registry-", dir=self._state_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(state, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self._state_file)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def register_and_upload_release(
        self,
        *,
        binary_path: Path,
        metadata_bytes: bytes,
        signature_bytes: bytes,
        authorize: bool = True,
        promote: bool = False,
        now: datetime | None = None,
    ) -> RegisteredRelease:
        """Verify signed ELF metadata + binary, upload to MinIO, and register."""
        try:
            validated = verify_elf_release_metadata(
                metadata_bytes,
                signature_bytes,
                self._public_key_pem,
                binary_path=binary_path,
                minimum_sequence=1,
                now=now,
            )
        except ValueError as exc:
            raise ReleaseValidationError(str(exc)) from exc

        release_id = str(validated["release_id"])
        channel = str(validated["channel"])
        platform_name = str(validated["platform"])
        sequence = int(validated["sequence"])
        artifact = validated["artifact"]
        sha256_val = str(artifact["sha256"])
        size_bytes = int(artifact["size_bytes"])

        with self._lock:
            state = self._load_state()
            releases = state.setdefault("releases", {})
            if release_id in releases:
                raise ReleaseConflictError("Release ID is already registered")
            for existing in releases.values():
                if (
                    existing.get("channel") == channel
                    and existing.get("platform") == platform_name
                    and int(existing.get("sequence", 0)) == sequence
                ):
                    raise ReleaseConflictError(
                        "Release sequence already allocated for channel/platform"
                    )

            object_key = self._store.upload_release_bundle(
                release_id=release_id,
                binary_path=binary_path,
                metadata_bytes=metadata_bytes,
                signature_bytes=signature_bytes,
                expected_sha256=sha256_val,
                expected_size_bytes=size_bytes,
                channel=channel,
                platform_name=platform_name,
            )

            ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            auth_state = "authorized" if authorize else "staged"
            record = RegisteredRelease(
                channel=channel,
                platform=platform_name,
                release_id=release_id,
                version=str(validated["version"]),
                sequence=sequence,
                source_commit=str(validated["source_commit"]),
                interface_version=str(validated["interface_version"]),
                artifact_filename=str(artifact["filename"]),
                sha256=sha256_val,
                size_bytes=size_bytes,
                artifact_object_key=object_key,
                signed_metadata_b64=base64.b64encode(metadata_bytes).decode("ascii"),
                signature_b64=encode_signature_b64(signature_bytes),
                release_status=str(validated["release_status"]),
                authorization_state=auth_state,
                expires_at=str(validated["expires_at"]),
                compatibility=dict(validated["compatibility"]),
                registered_at=ref_now.isoformat(),
            )
            releases[release_id] = record.to_dict()
            self._save_state(state)

            if promote:
                current_seq = self.get_current_sequence(
                    channel=channel, platform_name=platform_name
                )
                return self.promote_release(
                    release_id=release_id,
                    expected_current_sequence=current_seq,
                    channel=channel,
                    platform_name=platform_name,
                    now=now,
                )
            return record

    def authorize_release(self, release_id: str) -> RegisteredRelease:
        """Mark a staged release as authorized after verification."""
        if not RELEASE_ID_RE.fullmatch(release_id):
            raise ReleaseValidationError("Invalid release_id")
        with self._lock:
            state = self._load_state()
            releases = state.get("releases", {})
            if release_id not in releases:
                raise ReleaseNotFoundError("Release not found")
            record = RegisteredRelease.from_dict(releases[release_id])
            if record.authorization_state == "revoked":
                raise ReleaseUnauthorizedError("Revoked release cannot be authorized")
            self._verify_registered_release(record)
            updated = RegisteredRelease(
                **{
                    **record.to_dict(),
                    "authorization_state": "authorized",
                }
            )
            releases[release_id] = updated.to_dict()
            self._save_state(state)
            return updated

    def get_current_sequence(
        self,
        *,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
    ) -> int:
        with self._lock:
            state = self._load_state()
            channel_key = f"{channel}/{platform_name}"
            pointer = state.get("channels", {}).get(channel_key)
            if not pointer or not pointer.get("current"):
                return 0
            return int(pointer["current"]["sequence"])

    def promote_release(
        self,
        *,
        release_id: str,
        expected_current_sequence: int,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
        now: datetime | None = None,
    ) -> RegisteredRelease:
        """Atomically promote an authorized release to the channel pointer."""
        if channel != SUPPORTED_CHANNEL:
            raise ReleaseValidationError("Only staging channel promotion is permitted")
        try:
            validate_platform_compatibility(platform_name)
        except ValueError as exc:
            raise ReleaseValidationError(str(exc)) from exc
        if not RELEASE_ID_RE.fullmatch(release_id):
            raise ReleaseValidationError("Invalid release_id")
        if type(expected_current_sequence) is not int or expected_current_sequence < 0:
            raise ReleaseValidationError("Invalid expected_current_sequence")

        with self._lock:
            state = self._load_state()
            releases = state.get("releases", {})
            if release_id not in releases:
                raise ReleaseNotFoundError("Release not found")
            record = RegisteredRelease.from_dict(releases[release_id])
            if record.channel != channel or record.platform != platform_name:
                raise ReleaseValidationError("Release channel/platform mismatch")
            if record.authorization_state not in {"authorized", "promoted"}:
                raise ReleaseUnauthorizedError(
                    "Release is not authorized for promotion"
                )

            channel_key = f"{channel}/{platform_name}"
            channels = state.setdefault("channels", {})
            pointer = channels.get(channel_key, {"current": None, "history": []})
            current = pointer.get("current")
            current_seq = int(current["sequence"]) if current else 0
            if expected_current_sequence != current_seq:
                raise ChannelSequenceConflictError(
                    "Expected channel sequence does not match current sequence"
                )
            if record.sequence <= current_seq:
                raise ChannelSequenceConflictError(
                    "Release sequence must strictly exceed current channel sequence"
                )

            self._verify_registered_release(
                record,
                minimum_sequence=current_seq + 1,
                now=now,
            )

            ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            promoted_record = RegisteredRelease(
                **{
                    **record.to_dict(),
                    "authorization_state": "promoted",
                }
            )
            releases[release_id] = promoted_record.to_dict()
            entry = {
                "release_id": release_id,
                "sequence": record.sequence,
                "previous_sequence": current_seq,
                "promoted_at": ref_now.isoformat(),
            }
            history = list(pointer.get("history", []))
            history.append(entry)
            channels[channel_key] = {"current": entry, "history": history}
            self._save_state(state)
            return promoted_record

    def _verify_registered_release(
        self,
        record: RegisteredRelease,
        *,
        minimum_sequence: int = 1,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        try:
            validated = verify_elf_release_metadata(
                record.metadata_bytes,
                record.signature_bytes,
                self._public_key_pem,
                minimum_sequence=minimum_sequence,
                now=now,
            )
        except ValueError as exc:
            raise ReleaseValidationError(str(exc)) from exc

        expected_key = build_release_object_key(
            record.release_id,
            ARTIFACT_FILENAME,
            channel=record.channel,
            platform_name=record.platform,
        )
        if (
            validated["release_id"] != record.release_id
            or int(validated["sequence"]) != record.sequence
            or validated["artifact"]["sha256"] != record.sha256
            or int(validated["artifact"]["size_bytes"]) != record.size_bytes
            or record.artifact_object_key != expected_key
        ):
            raise ReleaseValidationError("Registered release record integrity mismatch")

        self._store.verify_release_objects(
            release_id=record.release_id,
            expected_size_bytes=record.size_bytes,
            expected_metadata_bytes=record.metadata_bytes,
            expected_signature_bytes=record.signature_bytes,
            channel=record.channel,
            platform_name=record.platform,
        )
        return validated

    def get_latest_release(
        self,
        *,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return the latest promoted and verified release manifest for the channel."""
        if channel != SUPPORTED_CHANNEL:
            raise ReleaseValidationError("Unsupported release channel")
        try:
            validate_platform_compatibility(platform_name)
        except ValueError as exc:
            raise ReleaseValidationError(str(exc)) from exc

        with self._lock:
            state = self._load_state()
            channel_key = f"{channel}/{platform_name}"
            pointer = state.get("channels", {}).get(channel_key)
            if not pointer or not pointer.get("current"):
                return {
                    "schema_version": 1,
                    "channel": channel,
                    "status": "no_release",
                }
            current_release_id = str(pointer["current"]["release_id"])
            current_seq = int(pointer["current"]["sequence"])
            releases = state.get("releases", {})
            if current_release_id not in releases:
                raise ReleaseNotFoundError("Promoted release record missing")
            record = RegisteredRelease.from_dict(releases[current_release_id])
            if record.authorization_state != "promoted":
                raise ReleaseUnauthorizedError("Channel release is not promoted")

            self._verify_registered_release(
                record,
                minimum_sequence=current_seq,
                now=now,
            )
            return {
                "schema_version": 1,
                "channel": record.channel,
                "status": "available",
                "platform": record.platform,
                "release_id": record.release_id,
                "version": record.version,
                "sequence": record.sequence,
                "source_commit": record.source_commit,
                "interface_version": record.interface_version,
                "artifact": {
                    "filename": record.artifact_filename,
                    "sha256": record.sha256,
                    "size_bytes": record.size_bytes,
                },
                "download_endpoint": (
                    f"/mpips/{record.channel}/releases/{record.release_id}/download"
                ),
                "signature": record.signature_b64,
                "release_status": record.release_status,
                "expires_at": record.expires_at,
                "compatibility": dict(record.compatibility),
                "signed_metadata_b64": record.signed_metadata_b64,
            }

    def get_authorized_release_for_download(
        self,
        release_id: str,
        *,
        channel: str = SUPPORTED_CHANNEL,
        platform_name: str = SUPPORTED_PLATFORM,
        now: datetime | None = None,
    ) -> RegisteredRelease:
        """Validate release_id, compatibility, authorization, and storage integrity."""
        if channel != SUPPORTED_CHANNEL:
            raise ReleaseValidationError("Unsupported release channel")
        try:
            validate_platform_compatibility(platform_name)
        except ValueError as exc:
            raise ReleaseValidationError(str(exc)) from exc
        if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
            raise ReleaseValidationError("Invalid release_id")

        with self._lock:
            state = self._load_state()
            releases = state.get("releases", {})
            if release_id not in releases:
                raise ReleaseNotFoundError("Release not found")
            record = RegisteredRelease.from_dict(releases[release_id])
            if record.channel != channel or record.platform != platform_name:
                raise ReleaseValidationError("Release platform or channel mismatch")
            if record.authorization_state not in {"authorized", "promoted"}:
                raise ReleaseUnauthorizedError(
                    "Release is not authorized for staging download"
                )

            channel_key = f"{channel}/{platform_name}"
            pointer = state.get("channels", {}).get(channel_key)
            current_seq = (
                int(pointer["current"]["sequence"])
                if pointer and pointer.get("current")
                else 1
            )
            if record.sequence < current_seq:
                raise ChannelSequenceConflictError(
                    "Release has been superseded by a newer sequence"
                )

            self._verify_registered_release(
                record,
                minimum_sequence=current_seq,
                now=now,
            )
            return record

