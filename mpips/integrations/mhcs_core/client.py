"""Typed MHCS Core Grabber HTTP client.

Reads credentials exclusively from environment variables.  Never logs or
exposes credential values, patient identity fields, or raw response bodies
that may contain patient data.

Required environment variables
-------------------------------
MHCS_GRABBER_BASE_URL : str
    Base URL of the MHCS Core server (e.g. ``http://localhost:8080``).
MHCS_GRABBER_TOKEN : str
    Grabber bearer-token credential.

Optional environment variables
-------------------------------
MHCS_GRABBER_ID : str, optional
    Grabber client identifier (sent as ``X-Grabber-ID`` when provided).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

_SENSITIVE_HEADERS = frozenset({"authorization", "x-grabber-token", "x-grabber-id"})


class GrabberClientError(Exception):
    """Base class for all Grabber client errors."""


class GrabberAuthError(GrabberClientError):
    """Raised when the server rejects the Grabber credential (401)."""


class GrabberLocatorNotFoundError(GrabberClientError):
    """Raised when the session locator is not found or not accessible (404)."""


class GrabberRateLimitError(GrabberClientError):
    """Raised when the server returns 429 Too Many Requests."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class GrabberIdempotencyConflictError(GrabberClientError):
    """Raised when a submission-ID conflict is detected (409)."""


class GrabberManifestError(GrabberClientError):
    """Raised when the manifest response cannot be parsed or is invalid."""


class GrabberUploadError(GrabberClientError):
    """Raised for non-retryable upload failures (4xx other than above)."""


class GrabberServerError(GrabberClientError):
    """Raised for 5xx server errors."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0


def _load_credentials() -> tuple[str, str, str | None]:
    """Return (base_url, token, grabber_id) from environment.

    Raises
    ------
    GrabberClientError
        If required environment variables are not set.
    """
    base_url = os.environ.get("MHCS_GRABBER_BASE_URL", "").rstrip("/")
    if not base_url:
        raise GrabberClientError(
            "MHCS_GRABBER_BASE_URL environment variable is not set"
        )
    token = os.environ.get("MHCS_GRABBER_TOKEN", "")
    if not token:
        raise GrabberClientError("MHCS_GRABBER_TOKEN environment variable is not set")
    grabber_id = os.environ.get("MHCS_GRABBER_ID") or None
    return base_url, token, grabber_id


def _build_auth_headers(token: str, grabber_id: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    if grabber_id:
        headers["X-Grabber-ID"] = grabber_id
    return headers


# ---------------------------------------------------------------------------
# Sanitized diagnostics helpers
# ---------------------------------------------------------------------------

_PATIENT_LOG_FIELDS = frozenset(
    {
        "medical_record_number",
        "name",
        "full_name",
        "family_name",
        "birth_date",
        "sex",
        "member_id",
    }
)


def _safe_status(response: httpx.Response) -> str:
    return f"HTTP {response.status_code}"


def _sanitized_headers(headers: httpx.Headers) -> dict[str, str]:
    """Return a copy of response headers safe for logging (drops credentials)."""
    return {k: v for k, v in headers.items() if k.lower() not in _SENSITIVE_HEADERS}


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------


class MHCSGrabberClient:
    """Synchronous MHCS Core Grabber HTTP client.

    Instantiate with ``base_url`` and ``token`` for direct use in tests.
    In production, prefer ``MHCSGrabberClient.from_env()`` to load credentials
    from environment variables automatically.

    Parameters
    ----------
    base_url:
        MHCS Core server base URL (no trailing slash).
    token:
        Grabber bearer-token credential.
    grabber_id:
        Optional grabber client identifier.
    timeout:
        Per-request timeout in seconds.
    connect_timeout:
        Connection timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        grabber_id: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._grabber_id = grabber_id
        self._timeout = httpx.Timeout(timeout, connect=connect_timeout)

    @classmethod
    def from_env(
        cls,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT_SECONDS,
    ) -> "MHCSGrabberClient":
        """Construct a client from environment variables.

        Raises ``GrabberClientError`` if required variables are absent.
        """
        base_url, token, grabber_id = _load_credentials()
        return cls(
            base_url=base_url,
            token=token,
            grabber_id=grabber_id,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )

    def _auth_headers(self) -> dict[str, str]:
        return _build_auth_headers(self._token, self._grabber_id)

    # ------------------------------------------------------------------
    # Manifest lookup
    # ------------------------------------------------------------------

    def get_manifest(self, locator_code: str) -> dict[str, Any]:
        """Retrieve the minimal DICOM manifest for a radiography session.

        Calls ``GET /api/v1/grabber/manifest/{code}``.

        Parameters
        ----------
        locator_code:
            Four-digit active radiography-session locator code.

        Returns
        -------
        dict
            Raw manifest payload as a Python dict, structurally compatible
            with ``MHCSManifest``.

        Raises
        ------
        GrabberAuthError
            Server returned 401.
        GrabberLocatorNotFoundError
            Server returned 404.
        GrabberRateLimitError
            Server returned 429.
        GrabberManifestError
            Response body is not valid JSON or cannot be decoded.
        GrabberServerError
            Server returned 5xx.
        GrabberClientError
            Any other HTTP error or connection failure.
        """
        url = f"{self._base_url}/api/v1/grabber/manifest/{locator_code}"
        logger.info("Requesting manifest for locator code %s", locator_code)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=self._auth_headers())
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise GrabberClientError(
                f"Connection error fetching manifest for locator {locator_code}: "
                f"{type(exc).__name__}"
            ) from exc

        self._raise_for_manifest_status(response, locator_code)

        try:
            payload: dict[str, Any] = response.json()
        except Exception as exc:
            raise GrabberManifestError(
                f"Manifest response for locator {locator_code} is not valid JSON"
            ) from exc

        logger.info(
            "Manifest retrieved for locator code %s (%s)",
            locator_code,
            _safe_status(response),
        )
        return payload

    def _raise_for_manifest_status(
        self, response: httpx.Response, locator_code: str
    ) -> None:
        code = response.status_code
        if code == 200:
            return
        if code == 401:
            raise GrabberAuthError(
                "MHCS Core rejected Grabber credentials (401 Unauthorized)"
            )
        if code == 404:
            raise GrabberLocatorNotFoundError(
                f"Radiography session not found or not accessible "
                f"for locator {locator_code} (404)"
            )
        if code == 429:
            retry_after_str = response.headers.get("Retry-After", "")
            retry_after: int | None = None
            try:
                retry_after = int(retry_after_str)
            except (ValueError, TypeError):
                pass
            raise GrabberRateLimitError(
                f"Rate limited on manifest request for locator {locator_code} "
                f"(429); Retry-After: {retry_after_str or 'unspecified'}",
                retry_after=retry_after,
            )
        if code >= 500:
            raise GrabberServerError(
                f"MHCS Core returned server error {code} on manifest request "
                f"for locator {locator_code}"
            )
        raise GrabberClientError(
            f"Unexpected HTTP {code} on manifest request " f"for locator {locator_code}"
        )

    # ------------------------------------------------------------------
    # DICOM upload
    # ------------------------------------------------------------------

    def upload_dicom(
        self,
        locator_code: str,
        dicom_bytes: bytes,
        checksum_sha256: str,
        submission_id: str,
    ) -> dict[str, Any]:
        """Upload a DICOM file to MHCS Core.

        Calls ``POST /api/v1/grabber/radiography-sessions/{code}/dicom``
        with multipart ``file`` field.

        Parameters
        ----------
        locator_code:
            Four-digit radiography-session locator code.
        dicom_bytes:
            Raw bytes of the generated DICOM file.
        checksum_sha256:
            Hex-encoded SHA-256 of ``dicom_bytes`` (64 chars, lowercase).
        submission_id:
            Client-generated stable submission/idempotency identifier
            (max 191 chars, non-empty).

        Returns
        -------
        dict
            Server response payload containing at minimum ``status``,
            ``study_id``, ``display_reference``, ``terminal_state``,
            ``replayed``, ``locator_code``, ``checksum``, ``bytes``.

        Raises
        ------
        GrabberAuthError
            Server returned 401.
        GrabberIdempotencyConflictError
            Server returned 409 (submission-ID conflict).
        GrabberRateLimitError
            Server returned 429.
        GrabberUploadError
            Server returned non-retryable 4xx.
        GrabberServerError
            Server returned 5xx.
        GrabberClientError
            Connection/timeout error.
        """
        url = (
            f"{self._base_url}/api/v1/grabber/radiography-sessions"
            f"/{locator_code}/dicom"
        )
        extra_headers = {
            "X-Submission-ID": submission_id,
            "X-Checksum-SHA256": checksum_sha256,
        }
        upload_headers = {**self._auth_headers(), **extra_headers}

        logger.info(
            "Uploading DICOM for locator code %s (submission %s, %d bytes)",
            locator_code,
            submission_id,
            len(dicom_bytes),
        )
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers=upload_headers,
                    files={"file": ("image.dcm", dicom_bytes, "application/dicom")},
                )
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise GrabberClientError(
                f"Connection error uploading DICOM for locator {locator_code}: "
                f"{type(exc).__name__}"
            ) from exc

        result = self._raise_for_upload_status(response, locator_code)
        logger.info(
            "DICOM upload complete for locator %s: %s (replayed=%s)",
            locator_code,
            _safe_status(response),
            result.get("replayed"),
        )
        return result

    def _raise_for_upload_status(
        self, response: httpx.Response, locator_code: str
    ) -> dict[str, Any]:
        code = response.status_code
        if code in (200, 201):
            try:
                result: dict[str, Any] = response.json()
            except Exception as exc:
                raise GrabberClientError(
                    f"Upload response for locator {locator_code} is not valid JSON"
                ) from exc
            return result
        if code == 401:
            raise GrabberAuthError(
                "MHCS Core rejected Grabber credentials on upload (401)"
            )
        if code == 409:
            raise GrabberIdempotencyConflictError(
                f"Submission-ID conflict on upload for locator {locator_code} (409); "
                "this submission ID was used with different DICOM bytes"
            )
        if code == 429:
            retry_after_str = response.headers.get("Retry-After", "")
            retry_after: int | None = None
            try:
                retry_after = int(retry_after_str)
            except (ValueError, TypeError):
                pass
            raise GrabberRateLimitError(
                f"Rate limited on DICOM upload for locator {locator_code} "
                f"(429); Retry-After: {retry_after_str or 'unspecified'}",
                retry_after=retry_after,
            )
        if code >= 500:
            raise GrabberServerError(
                f"MHCS Core returned server error {code} on DICOM upload "
                f"for locator {locator_code}"
            )
        raise GrabberUploadError(
            f"Unexpected HTTP {code} on DICOM upload for locator {locator_code}"
        )
