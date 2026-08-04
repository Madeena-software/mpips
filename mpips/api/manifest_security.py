from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict

from fastapi import Depends, HTTPException, Header, status

from mpips.api.security import verify_token_payload


def verify_image_convert_scope(
    payload: Dict[str, Any] = Depends(verify_token_payload),
) -> Dict[str, Any]:
    """Ensures token is authenticated and contains 'image:convert' scope."""
    tenant_id = payload.get("tenant_id")
    if not tenant_id or not str(tenant_id).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token lacks usable tenant_id claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scopes_str = str(payload.get("scope", ""))
    scopes = [s.strip() for s in scopes_str.split(" ") if s.strip()]

    if "image:convert" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required scope: image:convert",
        )

    return payload


def verify_manifest_signature(
    raw_manifest_bytes: bytes,
    timestamp_hdr: str | None = Header(None, alias="X-Madeena-Manifest-Timestamp"),
    signature_hdr: str | None = Header(None, alias="X-Madeena-Manifest-Signature"),
) -> None:
    """Verifies detached HMAC-SHA256 signature over exact raw manifest bytes."""
    secret = os.getenv("MPIPS_MANIFEST_HMAC_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC secret not configured",
        )

    if not timestamp_hdr or not timestamp_hdr.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or malformed X-Madeena-Manifest-Timestamp header",
        )

    if not signature_hdr or not signature_hdr.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or malformed X-Madeena-Manifest-Signature header",
        )

    given_signature = signature_hdr[len("sha256=") :].strip().lower()
    if len(given_signature) != 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature digest length",
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
            detail="Manifest signature timestamp is expired or skewed",
        )

    sig_input = timestamp_hdr.encode("utf-8") + b"." + raw_manifest_bytes
    expected_digest = (
        hmac.new(secret.encode("utf-8"), sig_input, hashlib.sha256).hexdigest().lower()
    )

    if not hmac.compare_digest(expected_digest, given_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid manifest signature",
        )
