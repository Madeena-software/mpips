from __future__ import annotations

import hashlib
import hmac
import os
import re
import time
import uuid
from typing import Any, Dict

from fastapi import Depends, HTTPException, Header, status

from mpips.api.security import verify_token_payload


def canonicalize_tenant_id(tenant_id: str) -> str:
    """Canonicalizes and validates tenant_id claim.

    Rules:
    - If valid UUID format, returns str(UUID).
    - Otherwise, preserves exact string after whitespace check, requiring
      pattern ^[a-zA-Z0-9_-]{1,64}$ (no dots allowed).
    """
    if not tenant_id or not isinstance(tenant_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token lacks usable tenant_id claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stripped = tenant_id.strip()
    if tenant_id != stripped:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tenant_id contains invalid leading/trailing whitespace",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        val = uuid.UUID(stripped)
        return str(val)
    except ValueError:
        pass

    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", stripped):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tenant_id format invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return stripped


def verify_image_convert_scope(
    payload: Dict[str, Any] = Depends(verify_token_payload),
) -> Dict[str, Any]:
    """Ensures token is authenticated, has valid tenant_id, and has scope."""
    tenant_id_raw = payload.get("tenant_id")
    canonical_tenant = canonicalize_tenant_id(str(tenant_id_raw or ""))

    scope_claim = payload.get("scope")
    if isinstance(scope_claim, str):
        scopes = [s.strip() for s in scope_claim.split(" ") if s.strip()]
    elif isinstance(scope_claim, list):
        scopes = [str(s).strip() for s in scope_claim if str(s).strip()]
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required scope: image:convert",
        )

    if "image:convert" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required scope: image:convert",
        )

    updated_payload = dict(payload)
    updated_payload["tenant_id"] = canonical_tenant
    return updated_payload


def compute_manifest_signature_digest(
    secret: str,
    tenant_id: str,
    timestamp_hdr: str,
    raw_manifest_bytes: bytes,
) -> str:
    """Helper to compute exact NUL-delimited HMAC digest."""
    sig_input = (
        b"mpips-manifest-v1\x00"
        + tenant_id.encode("utf-8")
        + b"\x00"
        + timestamp_hdr.encode("utf-8")
        + b"\x00"
        + raw_manifest_bytes
    )
    return (
        hmac.new(secret.encode("utf-8"), sig_input, hashlib.sha256).hexdigest().lower()
    )


def verify_manifest_signature(
    tenant_id: str,
    raw_manifest_bytes: bytes,
    timestamp_hdr: str | None = Header(None, alias="X-Madeena-Manifest-Timestamp"),
    signature_hdr: str | None = Header(None, alias="X-Madeena-Manifest-Signature"),
) -> None:
    """Verifies detached HMAC-SHA256 signature with canonical tenant_id."""
    secret = os.getenv("MPIPS_MANIFEST_HMAC_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC secret not configured",
        )

    if not timestamp_hdr or not timestamp_hdr.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MANIFEST_TIMESTAMP_INVALID",
        )

    if not signature_hdr or not signature_hdr.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MANIFEST_SIGNATURE_INVALID",
        )

    given_signature = signature_hdr[len("sha256=") :].strip().lower()
    if len(given_signature) != 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MANIFEST_SIGNATURE_INVALID",
        )

    try:
        max_skew = int(os.getenv("MPIPS_MANIFEST_MAX_CLOCK_SKEW_SECONDS", "300"))
    except ValueError:
        max_skew = 300

    ts_sec = int(timestamp_hdr)
    now_sec = int(time.time())

    if abs(now_sec - ts_sec) > max_skew:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MANIFEST_TIMESTAMP_INVALID",
        )

    canonical_tenant = canonicalize_tenant_id(tenant_id)
    expected_digest = compute_manifest_signature_digest(
        secret, canonical_tenant, timestamp_hdr, raw_manifest_bytes
    )

    if not hmac.compare_digest(expected_digest, given_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MANIFEST_SIGNATURE_INVALID",
        )
