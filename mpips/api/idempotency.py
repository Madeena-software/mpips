from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from redis.exceptions import RedisError

from mpips.worker.tasks import get_redis_client


@dataclass
class ClaimResult:
    status: str  # "CLAIMED", "IN_PROGRESS", "SUCCEEDED_SAME", "SUCCEEDED_DIFF"
    lease_token: Optional[str] = None
    cached_uids: Optional[Dict[str, Any]] = None


def compute_manifest_fingerprint(
    tenant_id: str,
    manifest_version: str,
    conversion_job_id: str,
    canonical_manifest_json: str,
    radiograph_sha256: str,
    gain_sha256: str,
) -> str:
    import hashlib

    hasher = hashlib.sha256()
    hasher.update(tenant_id.encode("utf-8"))
    hasher.update(manifest_version.encode("utf-8"))
    hasher.update(conversion_job_id.encode("utf-8"))
    hasher.update(canonical_manifest_json.encode("utf-8"))
    hasher.update(radiograph_sha256.lower().encode("utf-8"))
    hasher.update(gain_sha256.lower().encode("utf-8"))
    return hasher.hexdigest()


class IdempotencyService:
    @staticmethod
    def _get_lease_ttl() -> int:
        try:
            timeout = int(os.getenv("MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS", "300"))
        except ValueError:
            timeout = 300
        return timeout + 30

    @staticmethod
    def _get_success_ttl() -> int:
        try:
            ttl = int(os.getenv("MPIPS_DICOM_IDEMPOTENCY_TTL_SECONDS", "86400"))
        except ValueError:
            ttl = 86400
        return ttl

    @classmethod
    def claim_job(
        cls,
        tenant_id: str,
        conversion_job_id: str,
        fingerprint: str,
    ) -> ClaimResult:
        key = f"mpips:dicom_idempotency:{tenant_id}:{conversion_job_id}"
        lease_token = uuid.uuid4().hex
        lease_ttl = cls._get_lease_ttl()

        try:
            r = get_redis_client()
            existing_data_str = r.get(key)
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency storage service unavailable",
            ) from exc

        if not existing_data_str:
            data = {
                "status": "processing",
                "fingerprint": fingerprint,
                "lease_token": lease_token,
                "tenant_id": tenant_id,
            }
            try:
                acquired = r.set(key, json.dumps(data), ex=lease_ttl, nx=True)
                if acquired:
                    return ClaimResult(status="CLAIMED", lease_token=lease_token)
                existing_data_str = r.get(key)
            except RedisError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Idempotency storage service unavailable",
                ) from exc

        if not existing_data_str:
            return ClaimResult(status="CLAIMED", lease_token=lease_token)

        try:
            existing = json.loads(existing_data_str)
        except Exception:
            existing = {}

        current_status = existing.get("status")
        existing_fp = existing.get("fingerprint")

        if current_status == "processing":
            return ClaimResult(status="IN_PROGRESS")

        if current_status == "succeeded":
            if existing_fp == fingerprint:
                data = {
                    "status": "processing",
                    "fingerprint": fingerprint,
                    "lease_token": lease_token,
                    "tenant_id": tenant_id,
                    "cached_uids": existing.get("cached_uids"),
                }
                r.set(key, json.dumps(data), ex=lease_ttl)
                return ClaimResult(
                    status="SUCCEEDED_SAME",
                    lease_token=lease_token,
                    cached_uids=existing.get("cached_uids"),
                )
            return ClaimResult(status="SUCCEEDED_DIFF")

        # status == "failed" or other
        if existing_fp == fingerprint:
            data = {
                "status": "processing",
                "fingerprint": fingerprint,
                "lease_token": lease_token,
                "tenant_id": tenant_id,
            }
            r.set(key, json.dumps(data), ex=lease_ttl)
            return ClaimResult(status="CLAIMED", lease_token=lease_token)

        return ClaimResult(status="SUCCEEDED_DIFF")

    @classmethod
    def mark_success(
        cls,
        tenant_id: str,
        conversion_job_id: str,
        lease_token: str,
        cached_uids: Dict[str, Any],
    ) -> None:
        key = f"mpips:dicom_idempotency:{tenant_id}:{conversion_job_id}"
        ttl = cls._get_success_ttl()
        try:
            r = get_redis_client()
            existing_data_str = r.get(key)
            if existing_data_str:
                existing = json.loads(existing_data_str)
                if existing.get("lease_token") == lease_token:
                    existing["status"] = "succeeded"
                    existing["cached_uids"] = cached_uids
                    r.set(key, json.dumps(existing), ex=ttl)
        except RedisError:
            pass

    @classmethod
    def mark_failure(
        cls,
        tenant_id: str,
        conversion_job_id: str,
        lease_token: str,
        error_msg: str,
    ) -> None:
        key = f"mpips:dicom_idempotency:{tenant_id}:{conversion_job_id}"
        try:
            r = get_redis_client()
            existing_data_str = r.get(key)
            if existing_data_str:
                existing = json.loads(existing_data_str)
                if existing.get("lease_token") == lease_token:
                    existing["status"] = "failed"
                    existing["error"] = error_msg[:256]
                    r.set(key, json.dumps(existing), ex=300)
        except RedisError:
            pass
