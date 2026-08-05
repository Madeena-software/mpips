from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

API_KEY = "mpips_access_api_m4d33n4"


def require_api_key(
    api_key: str | None = Header(default=None, alias="X-MPIPS-API-Key"),
) -> str:
    if not secrets.compare_digest(api_key or "", API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_API_KEY",
        )
    return API_KEY
