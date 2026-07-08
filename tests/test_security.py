import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi import status
from fastapi.testclient import TestClient
import jwt
from mpips.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_env() -> None:
    # Clear and reset bypass configurations
    if "DEV_AUTH_BYPASS" in os.environ:
        del os.environ["DEV_AUTH_BYPASS"]
    if "DEV_BEARER_TOKEN" in os.environ:
        del os.environ["DEV_BEARER_TOKEN"]


def test_secure_endpoint_no_token() -> None:
    # Verify that requesting without auth header fails with 401
    response = client.get("/v1/secure-test")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json().get("detail", "")


def test_secure_endpoint_bypass_success() -> None:
    # Set environment variables for developer bypass
    os.environ["DEV_AUTH_BYPASS"] = "true"
    os.environ["DEV_BEARER_TOKEN"] = "test_bypass_token"

    response = client.get(
        "/v1/secure-test",
        headers={"Authorization": "Bearer test_bypass_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["client_id"] == "mock-client-id"
    assert "image:process" in data["scopes"]
    assert "nodes:read" in data["scopes"]
    assert data["tenant_id"] == "default-tenant-id"


def test_secure_endpoint_bypass_failure() -> None:
    os.environ["DEV_AUTH_BYPASS"] = "true"
    os.environ["DEV_BEARER_TOKEN"] = "test_bypass_token"

    response = client.get(
        "/v1/secure-test",
        headers={"Authorization": "Bearer wrong_bypass_token"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid developer bypass token" in response.json().get("detail", "")


@patch("mpips.api.security.decode_and_verify_token")
def test_secure_endpoint_real_jwt_success(mock_verify: MagicMock) -> None:
    # Set environment to standard auth (no bypass)
    os.environ["DEV_AUTH_BYPASS"] = "false"

    # Mock the return value of verification to represent a valid token
    mock_verify.return_value = {
        "sub": "prod-client-id",
        "scope": "image:process nodes:read extra:scope",
        "tenant_id": "tenant-123",
    }

    response = client.get(
        "/v1/secure-test",
        headers={"Authorization": "Bearer valid_jwt_token_xyz"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["client_id"] == "prod-client-id"
    assert data["tenant_id"] == "tenant-123"
    assert data["scopes"] == "image:process nodes:read extra:scope"


@patch("mpips.api.security.decode_and_verify_token")
def test_secure_endpoint_real_jwt_missing_scopes(mock_verify: MagicMock) -> None:
    os.environ["DEV_AUTH_BYPASS"] = "false"

    # Mock return value lacking "nodes:read" scope
    mock_verify.return_value = {
        "sub": "prod-client-id",
        "scope": "image:process",
        "tenant_id": "tenant-123",
    }

    response = client.get(
        "/v1/secure-test",
        headers={"Authorization": "Bearer valid_jwt_token_xyz"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Missing required scope" in response.json().get("detail", "")


@patch("mpips.api.security.JWKSKeyResolver.get_signing_key")
@patch("jwt.decode")
def test_decode_and_verify_token_invalid_signature(
    mock_jwt_decode: MagicMock, mock_get_signing_key: MagicMock
) -> None:
    # Simulate a signature validation error in PyJWT
    mock_get_signing_key.return_value = MagicMock()
    mock_jwt_decode.side_effect = jwt.PyJWTError("Signature verification failed")

    os.environ["DEV_AUTH_BYPASS"] = "false"

    response = client.get(
        "/v1/secure-test",
        headers={"Authorization": "Bearer invalid_jwt_token"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token or signature" in response.json().get("detail", "")
