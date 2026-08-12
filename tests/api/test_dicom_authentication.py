from __future__ import annotations

import secrets
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mpips.api.api_key import require_api_key
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


def test_production_configured_key_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("MPIPS_API_KEY", "prod-secret-key-999")
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": "prod-secret-key-999"},
    )
    assert response.status_code == 422


def test_production_configured_key_wrong_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("MPIPS_API_KEY", "prod-secret-key-999")
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}


def test_production_configured_key_missing_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("MPIPS_API_KEY", "prod-secret-key-999")
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}


def test_production_without_api_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.delenv("MPIPS_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    response = TestClient(app).post(
        "/v1/radiographs/dicom",
        files=_dicom_files(),
        headers={"X-MPIPS-API-Key": "any-key"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "INVALID_API_KEY"}


def test_dev_config_does_not_depend_on_historical_production_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "development")
    monkeypatch.setenv("MPIPS_API_KEY", "test-synthetic-dev-key")
    assert require_api_key("test-synthetic-dev-key") == "test-synthetic-dev-key"


def test_whitespace_and_empty_values_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MPIPS_ENVIRONMENT", "production")
    monkeypatch.setenv("MPIPS_API_KEY", "valid-key-123")

    for empty_val in ["", "   ", "\t\n"]:
        response = TestClient(app).post(
            "/v1/radiographs/dicom",
            files=_dicom_files(),
            headers={"X-MPIPS-API-Key": empty_val},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "INVALID_API_KEY"}


def test_constant_time_comparison_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPIPS_API_KEY", "my-secret-key")
    with patch("secrets.compare_digest", wraps=secrets.compare_digest) as mock_cmp:
        require_api_key("my-secret-key")
        mock_cmp.assert_called_once_with("my-secret-key", "my-secret-key")
