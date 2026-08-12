from __future__ import annotations

import os
import secrets
from typing import Any, Optional

from fastapi import Header, HTTPException, status

DEFAULT_DEV_API_KEY = "mpips_dev_key_synthetic_only"


def get_api_key() -> Optional[str]:
    """Retrieve configured API key from runtime environment."""
    key = os.getenv("MPIPS_API_KEY") or os.getenv("API_KEY")
    if key and key.strip():
        return key.strip()

    env = os.getenv("MPIPS_ENVIRONMENT", "development").lower()
    if env == "production":
        return None

    return DEFAULT_DEV_API_KEY


def require_api_key(
    api_key: str | None = Header(default=None, alias="X-MPIPS-API-Key"),
) -> str:
    configured = get_api_key()
    if (
        not configured
        or not api_key
        or not api_key.strip()
        or not secrets.compare_digest(api_key.strip(), configured)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_API_KEY",
        )
    return configured


def __getattr__(name: str) -> Any:
    if name == "API_KEY":
        return get_api_key() or ""
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
