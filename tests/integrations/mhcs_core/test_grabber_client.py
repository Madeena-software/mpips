"""Unit tests for MHCSGrabberClient (all mocked; no live server required).

Tests cover:
- Manifest success (valid 4-digit code, returns MHCSManifest-compatible dict)
- Authentication failure (401 → GrabberAuthError)
- Locator not found (404 → GrabberLocatorNotFoundError)
- Rate limit (429 + Retry-After → GrabberRateLimitError)
- Upload timeout / connection loss → local DICOM retained; exception raised
- Malformed manifest response (non-JSON → GrabberManifestError)
- Idempotency conflict (409 → GrabberIdempotencyConflictError)
- Idempotency replay (200 + replayed:true → returns replayed result)
- Upload 201 Created (initial)
- Upload 5xx → GrabberServerError
- from_env() missing credentials → GrabberClientError
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from mpips.integrations.mhcs_core.client import (
    GrabberAuthError,
    GrabberClientError,
    GrabberIdempotencyConflictError,
    GrabberLocatorNotFoundError,
    GrabberManifestError,
    GrabberRateLimitError,
    GrabberServerError,
    GrabberUploadError,
    MHCSGrabberClient,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_LOCATOR = "1234"
_TOKEN = "test-grabber-token"
_BASE_URL = "http://localhost:9000"

MINIMAL_MANIFEST_DICT = {
    "manifest_version": "1.0",
    "patient": {
        "medical_record_number": "MRN-SYNTH-001",
        "name": {"full_name": "SYNTHETIC PATIENT"},
        "sex": "unknown",
    },
}

UPLOAD_RESPONSE_201 = {
    "status": "ingested",
    "study_id": "STU-0001",
    "display_reference": "REF-0001",
    "admission_id": "ADM-0001",
    "locator_code": _LOCATOR,
    "terminal_state": "awaiting_ai",
    "replayed": False,
    "checksum": "a" * 64,
    "bytes": 132,
}

UPLOAD_RESPONSE_200_REPLAYED = {
    **UPLOAD_RESPONSE_201,
    "replayed": True,
}


def _client() -> MHCSGrabberClient:
    return MHCSGrabberClient(base_url=_BASE_URL, token=_TOKEN)


def _mock_response(
    status_code: int, json_body: object = None, text: str = ""
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = httpx.Headers({"Content-Type": "application/json"})
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("not valid JSON")
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# from_env() tests
# ---------------------------------------------------------------------------


class TestFromEnv:
    def test_missing_base_url_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MHCS_GRABBER_BASE_URL", raising=False)
        monkeypatch.delenv("MHCS_GRABBER_TOKEN", raising=False)
        with pytest.raises(GrabberClientError, match="MHCS_GRABBER_BASE_URL"):
            MHCSGrabberClient.from_env()

    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MHCS_GRABBER_BASE_URL", "http://localhost:9000")
        monkeypatch.delenv("MHCS_GRABBER_TOKEN", raising=False)
        with pytest.raises(GrabberClientError, match="MHCS_GRABBER_TOKEN"):
            MHCSGrabberClient.from_env()

    def test_valid_env_builds_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MHCS_GRABBER_BASE_URL", "http://localhost:9000")
        monkeypatch.setenv("MHCS_GRABBER_TOKEN", "tok")
        monkeypatch.delenv("MHCS_GRABBER_ID", raising=False)
        c = MHCSGrabberClient.from_env()
        assert c._base_url == "http://localhost:9000"

    def test_optional_grabber_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MHCS_GRABBER_BASE_URL", "http://localhost:9000")
        monkeypatch.setenv("MHCS_GRABBER_TOKEN", "tok")
        monkeypatch.setenv("MHCS_GRABBER_ID", "grabber-01")
        c = MHCSGrabberClient.from_env()
        assert c._grabber_id == "grabber-01"


# ---------------------------------------------------------------------------
# Manifest lookup tests
# ---------------------------------------------------------------------------


class TestGetManifest:
    def test_manifest_success(self) -> None:
        """200 response returns the parsed JSON dict."""
        resp = _mock_response(200, json_body=MINIMAL_MANIFEST_DICT)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            result = _client().get_manifest(_LOCATOR)
        assert result["patient"]["medical_record_number"] == "MRN-SYNTH-001"

    def test_manifest_401_raises_auth_error(self) -> None:
        resp = _mock_response(401)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberAuthError):
                _client().get_manifest(_LOCATOR)

    def test_manifest_404_raises_not_found(self) -> None:
        resp = _mock_response(404)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberLocatorNotFoundError, match=_LOCATOR):
                _client().get_manifest(_LOCATOR)

    def test_manifest_429_raises_rate_limit_with_retry_after(self) -> None:
        resp = _mock_response(429)
        resp.headers = httpx.Headers({"Retry-After": "42"})
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberRateLimitError) as exc_info:
                _client().get_manifest(_LOCATOR)
        assert exc_info.value.retry_after == 42

    def test_manifest_429_no_retry_after(self) -> None:
        resp = _mock_response(429)
        resp.headers = httpx.Headers({})
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberRateLimitError) as exc_info:
                _client().get_manifest(_LOCATOR)
        assert exc_info.value.retry_after is None

    def test_manifest_5xx_raises_server_error(self) -> None:
        resp = _mock_response(503)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberServerError):
                _client().get_manifest(_LOCATOR)

    def test_manifest_non_json_response_raises_manifest_error(self) -> None:
        """Non-JSON body on a 200 response raises GrabberManifestError."""
        resp = _mock_response(200, json_body=None)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberManifestError, match="not valid JSON"):
                _client().get_manifest(_LOCATOR)

    def test_manifest_timeout_raises_grabber_client_error(self) -> None:
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("timed out")
            )
            with pytest.raises(GrabberClientError, match="Connection error"):
                _client().get_manifest(_LOCATOR)

    def test_manifest_connect_error_raises_grabber_client_error(self) -> None:
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.side_effect = (
                httpx.ConnectError("refused")
            )
            with pytest.raises(GrabberClientError, match="Connection error"):
                _client().get_manifest(_LOCATOR)

    def test_manifest_unexpected_status_raises_client_error(self) -> None:
        resp = _mock_response(418)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberClientError, match="418"):
                _client().get_manifest(_LOCATOR)


# ---------------------------------------------------------------------------
# DICOM upload tests
# ---------------------------------------------------------------------------

_DICOM_BYTES = b"DICM" + b"\x00" * 128
_CHECKSUM = "a" * 64
_SUBMISSION_ID = "sub-test-001"


class TestUploadDicom:
    def test_upload_201_initial(self) -> None:
        """201 Created response returns the result dict with replayed=False."""
        resp = _mock_response(201, json_body=UPLOAD_RESPONSE_201)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            result = _client().upload_dicom(
                _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
            )
        assert result["replayed"] is False
        assert result["terminal_state"] == "awaiting_ai"

    def test_upload_200_replayed(self) -> None:
        """200 OK with replayed:true returns replayed result."""
        resp = _mock_response(200, json_body=UPLOAD_RESPONSE_200_REPLAYED)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            result = _client().upload_dicom(
                _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
            )
        assert result["replayed"] is True

    def test_upload_401_raises_auth_error(self) -> None:
        resp = _mock_response(401)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            with pytest.raises(GrabberAuthError):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )

    def test_upload_409_raises_idempotency_conflict(self) -> None:
        resp = _mock_response(409)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            with pytest.raises(GrabberIdempotencyConflictError):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )

    def test_upload_429_raises_rate_limit(self) -> None:
        resp = _mock_response(429)
        resp.headers = httpx.Headers({"Retry-After": "10"})
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            with pytest.raises(GrabberRateLimitError) as exc_info:
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )
        assert exc_info.value.retry_after == 10

    def test_upload_5xx_raises_server_error(self) -> None:
        resp = _mock_response(500)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            with pytest.raises(GrabberServerError):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )

    def test_upload_timeout_raises_client_error(self) -> None:
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("timed out")
            )
            with pytest.raises(GrabberClientError, match="Connection error"):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )

    def test_upload_connect_error_raises_client_error(self) -> None:
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.side_effect = (
                httpx.ConnectError("refused")
            )
            with pytest.raises(GrabberClientError, match="Connection error"):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )

    def test_upload_4xx_other_raises_upload_error(self) -> None:
        resp = _mock_response(422)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            with pytest.raises(GrabberUploadError, match="422"):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )

    def test_upload_response_non_json_raises_client_error(self) -> None:
        resp = _mock_response(201, json_body=None)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.return_value = resp
            with pytest.raises(GrabberClientError, match="not valid JSON"):
                _client().upload_dicom(
                    _LOCATOR, _DICOM_BYTES, _CHECKSUM, _SUBMISSION_ID
                )


# ---------------------------------------------------------------------------
# Auth header tests
# ---------------------------------------------------------------------------


class TestAuthHeaders:
    def test_bearer_token_header_present(self) -> None:
        c = MHCSGrabberClient(base_url=_BASE_URL, token="my-token")
        headers = c._auth_headers()
        assert headers["Authorization"] == "Bearer my-token"

    def test_grabber_id_header_present_when_set(self) -> None:
        c = MHCSGrabberClient(base_url=_BASE_URL, token="my-token", grabber_id="gid-01")
        headers = c._auth_headers()
        assert headers["X-Grabber-ID"] == "gid-01"

    def test_grabber_id_absent_when_not_set(self) -> None:
        c = MHCSGrabberClient(base_url=_BASE_URL, token="my-token")
        headers = c._auth_headers()
        assert "X-Grabber-ID" not in headers

    def test_token_not_in_exception_message(self) -> None:
        """Token value must not appear in any raised exception message."""
        resp = _mock_response(401)
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = resp
            with pytest.raises(GrabberAuthError) as exc_info:
                MHCSGrabberClient(
                    base_url=_BASE_URL, token="SUPERSECRETTOKEN"
                ).get_manifest(_LOCATOR)
        assert "SUPERSECRETTOKEN" not in str(exc_info.value)
