from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mpips.api.api_key import API_KEY
from mpips.api.application import app


def _dicom_files() -> dict[str, tuple[str, bytes, str]]:
    return {
        "radiograph_npz": ("radiograph.npz", b"", "application/octet-stream"),
        "gain_npz": ("gain.npz", b"", "application/octet-stream"),
        "manifest": ("manifest.json", b"{}", "application/json"),
    }


def test_health_is_unauthenticated() -> None:
    assert TestClient(app).get("/health").status_code == 200


def test_dicom_request_without_api_key_returns_401_before_conversion() -> None:
    with patch("mpips.api.routes.v1.dicom.run_isolated_dicom_conversion") as convert:
        response = TestClient(app).post("/v1/radiographs/dicom", files=_dicom_files())

    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}
    convert.assert_not_called()


def test_dicom_request_with_wrong_api_key_returns_401() -> None:
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}


def test_bearer_token_without_api_key_returns_401() -> None:
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"Authorization": "Bearer legacy-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}


def test_valid_api_key_reaches_request_validation() -> None:
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": API_KEY},
    )

    assert response.status_code == 422


def test_custom_env_api_key_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPIPS_API_KEY", "custom-secret-key-123")
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": "custom-secret-key-123"},
    )
    assert response.status_code == 422


def test_production_without_api_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.delenv("MPIPS_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": "mpips_access_api_m4d33n4"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}
