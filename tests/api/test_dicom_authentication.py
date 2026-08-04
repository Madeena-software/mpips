from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from mpips.api.application import app
from mpips.api.manifest_security import verify_image_convert_scope
from mpips.api.security import verify_token_payload


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _dicom_files() -> dict[str, tuple[str, bytes, str]]:
    return {
        "radiograph_npz": ("radiograph.npz", b"", "application/octet-stream"),
        "gain_npz": ("gain.npz", b"", "application/octet-stream"),
        "manifest": ("manifest.json", b"{}", "application/json"),
    }


def test_dicom_request_without_authorization_returns_401_before_conversion() -> None:
    with patch("mpips.api.routes.v1.dicom.run_isolated_dicom_conversion") as convert:
        response = TestClient(app).post("/v1/radiographs/dicom", files=_dicom_files())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    convert.assert_not_called()


def test_invalid_development_bypass_token_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("DEV_BEARER_TOKEN", "expected-token")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            verify_token_payload(
                credentials=_credentials("wrong-token"),
                resolver=MagicMock(),
            )
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_jwt_signature_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")

    with patch(
        "mpips.api.security.jwt.decode",
        side_effect=jwt.InvalidSignatureError("invalid signature"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                verify_token_payload(
                    credentials=_credentials("invalid-jwt"),
                    resolver=MagicMock(),
                )
            )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_token_without_image_convert_scope_returns_403() -> None:
    with pytest.raises(HTTPException) as exc_info:
        verify_image_convert_scope(
            payload={"tenant_id": "tenant-123", "scope": "image:process"}
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_token_without_usable_tenant_id_returns_401() -> None:
    with pytest.raises(HTTPException) as exc_info:
        verify_image_convert_scope(
            payload={"tenant_id": None, "scope": "image:convert"}
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_valid_image_convert_payload_passes_scope_verification() -> None:
    payload = {"tenant_id": "tenant-123", "scope": "image:convert"}

    verified = verify_image_convert_scope(payload=payload)

    assert verified["tenant_id"] == "tenant-123"
    assert verified["scope"] == "image:convert"
