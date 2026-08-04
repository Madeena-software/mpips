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


CLAIM_LUA = """
local key = KEYS[1]
local fp = ARGV[1]
local lease_token = ARGV[2]
local tenant_id = ARGV[3]
local lease_ttl = tonumber(ARGV[4])

local existing = redis.call('GET', key)
if not existing then
    local data = cjson.encode({
        status = "processing",
        fingerprint = fp,
        lease_token = lease_token,
        tenant_id = tenant_id
    })
    redis.call('SET', key, data, 'EX', lease_ttl)
    return "CLAIMED"
end

local ok, data = pcall(cjson.decode, existing)
if not ok or type(data) ~= "table" then
    data = {}
end

local status = data["status"]
local existing_fp = data["fingerprint"]

if status == "processing" then
    return "IN_PROGRESS"
elseif status == "succeeded" then
    if existing_fp == fp then
        data["status"] = "processing"
        data["lease_token"] = lease_token
        local updated = cjson.encode(data)
        redis.call('SET', key, updated, 'EX', lease_ttl)
        local uids_json = cjson.encode(data["cached_uids"] or {})
        return "SUCCEEDED_SAME:" .. uids_json
    else
        return "SUCCEEDED_DIFF"
    end
else
    if existing_fp == fp then
        data["status"] = "processing"
        data["lease_token"] = lease_token
        local updated = cjson.encode(data)
        redis.call('SET', key, updated, 'EX', lease_ttl)
        return "CLAIMED"
    else
        return "SUCCEEDED_DIFF"
    end
end
"""

SUCCESS_LUA = """
local key = KEYS[1]
local lease_token = ARGV[1]
local cached_uids_json = ARGV[2]
local success_ttl = tonumber(ARGV[3])

local existing = redis.call('GET', key)
if not existing then
    return 0
end

local ok, data = pcall(cjson.decode, existing)
if not ok or type(data) ~= "table" then
    return 0
end

if data["status"] == "processing" and data["lease_token"] == lease_token then
    data["status"] = "succeeded"
    local uids_ok, uids = pcall(cjson.decode, cached_uids_json)
    if uids_ok then
        data["cached_uids"] = uids
    end
    local updated = cjson.encode(data)
    redis.call('SET', key, updated, 'EX', success_ttl)
    return 1
else
    return 0
end
"""

FAILURE_LUA = """
local key = KEYS[1]
local lease_token = ARGV[1]
local error_code = ARGV[2]

local existing = redis.call('GET', key)
if not existing then
    return 0
end

local ok, data = pcall(cjson.decode, existing)
if not ok or type(data) ~= "table" then
    return 0
end

if data["status"] == "processing" and data["lease_token"] == lease_token then
    data["status"] = "failed"
    data["error_code"] = error_code
    local updated = cjson.encode(data)
    redis.call('SET', key, updated, 'EX', 300)
    return 1
else
    return 0
end
"""


class IdempotencyService:
    @staticmethod
    def _get_lease_ttl() -> int:
        try:
            timeout = int(os.getenv("MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS", "300"))
        except ValueError:
            timeout = 300
        return timeout + 60  # Complete operation margin

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
            res = r.eval(
                CLAIM_LUA, 1, key, fingerprint, lease_token, tenant_id, lease_ttl
            )
            res_str = res.decode("utf-8") if isinstance(res, bytes) else str(res)

            if res_str == "CLAIMED":
                return ClaimResult(status="CLAIMED", lease_token=lease_token)
            elif res_str == "IN_PROGRESS":
                return ClaimResult(status="IN_PROGRESS")
            elif res_str == "SUCCEEDED_DIFF":
                return ClaimResult(status="SUCCEEDED_DIFF")
            elif res_str.startswith("SUCCEEDED_SAME:"):
                uids_raw = res_str[len("SUCCEEDED_SAME:") :]
                try:
                    uids = json.loads(uids_raw)
                except Exception:
                    uids = {}
                return ClaimResult(
                    status="SUCCEEDED_SAME",
                    lease_token=lease_token,
                    cached_uids=uids,
                )
            return ClaimResult(status="CLAIMED", lease_token=lease_token)
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="IDEMPOTENCY_STORAGE_UNAVAILABLE",
            ) from exc

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
            uids_json = json.dumps(cached_uids)
            res = r.eval(SUCCESS_LUA, 1, key, lease_token, uids_json, ttl)
            if res != 1 and int(res or 0) != 1:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="IDEMPOTENCY_PERSISTENCE_FAILURE",
                )
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="IDEMPOTENCY_PERSISTENCE_FAILURE",
            ) from exc

    @classmethod
    def mark_failure(
        cls,
        tenant_id: str,
        conversion_job_id: str,
        lease_token: str,
        sanitized_error_code: str,
    ) -> None:
        key = f"mpips:dicom_idempotency:{tenant_id}:{conversion_job_id}"
        try:
            r = get_redis_client()
            r.eval(FAILURE_LUA, 1, key, lease_token, sanitized_error_code)
        except RedisError:
            pass
