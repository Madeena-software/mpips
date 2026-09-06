"""Grabber round-trip orchestration workflow.

Accepts a four-digit radiography-session locator code and orchestrates:
  manifest lookup → NPZ-to-DICOM conversion → SHA-256 compute →
  submission ID generate/load → DICOM upload.

Idempotent retry reuses exactly the same DICOM bytes, checksum, and
submission ID.  The generated DICOM is retained on disk when an upload fails
so a subsequent call can resume from the same artifact.

No credentials, patient identity fields, or raw response bodies are logged.

Configuration
-------------
All MHCS Core credentials must be supplied via environment variables:
    MHCS_GRABBER_BASE_URL
    MHCS_GRABBER_TOKEN
    MHCS_GRABBER_ID  (optional)

The work directory (for DICOM and sidecar storage) defaults to a
``mpips-grabber-work/`` sub-directory relative to the output DICOM directory
and is configurable via the ``work_dir`` parameter.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion import ConversionError, convert_npz_to_dicom
from mpips.integrations.mhcs_core.client import (
    GrabberClientError,
    GrabberConnectionError,
    GrabberIdempotencyConflictError,
    GrabberRateLimitError,
    GrabberResponseValidationError,
    GrabberServerError,
    GrabberSessionIneligibleError,
    GrabberSessionStateError,
    GrabberTimeoutError,
    GrabberTransientNetworkError,
    MHCSGrabberClient,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrabberWorkflowResult:
    """Non-sensitive result returned by :func:`run_grabber_roundtrip`.

    Contains only operational fields — no patient identity, no credentials.
    """

    study_id: str
    display_reference: str
    terminal_state: str
    replayed: bool
    locator_code: str
    checksum: str
    bytes: int


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BACKOFF_BASE = 1.0
_DEFAULT_BACKOFF_MAX = 30.0
_DEFAULT_JITTER_FRACTION = 0.25


def _backoff_seconds(
    attempt: int,
    base: float = _DEFAULT_BACKOFF_BASE,
    cap: float = _DEFAULT_BACKOFF_MAX,
    jitter: float = _DEFAULT_JITTER_FRACTION,
) -> float:
    delay = min(base * (2**attempt), cap)
    return float(delay * (1.0 + random.uniform(-jitter, jitter)))  # noqa: S311


def _is_retryable(exc: GrabberClientError) -> bool:
    """Return True for transient errors that should be retried."""
    return isinstance(
        exc,
        (
            GrabberRateLimitError,
            GrabberServerError,
            GrabberTransientNetworkError,
        ),
    )


# ---------------------------------------------------------------------------
# Submission ID / sidecar persistence
# ---------------------------------------------------------------------------

_SIDECAR_VERSION = "1"


def _sidecar_path(work_dir: Path, locator_code: str) -> Path:
    return work_dir / f"submission-{locator_code}.json"


def _compute_input_fingerprint(
    radiograph_path: str | Path,
    gain_path: str | Path,
) -> str:
    """Compute non-sensitive fingerprint of input files to bind sidecar to a
    specific attempt.
    """
    rad_p = Path(radiograph_path)
    gain_p = Path(gain_path)
    hasher = hashlib.sha256()
    hasher.update(str(rad_p.resolve() if rad_p.exists() else rad_p).encode("utf-8"))
    if rad_p.is_file():
        hasher.update(hashlib.sha256(rad_p.read_bytes()).digest())
    hasher.update(str(gain_p.resolve() if gain_p.exists() else gain_p).encode("utf-8"))
    if gain_p.is_file():
        hasher.update(hashlib.sha256(gain_p.read_bytes()).digest())
    return hasher.hexdigest()


def _is_verified_dicom(dicom_bytes: bytes) -> bool:
    """Verify that bytes represent a minimally valid DICOM artifact
    (128 preamble + DICM magic).
    """
    return len(dicom_bytes) >= 132 and dicom_bytes[128:132] == b"DICM"


def _try_resume_artifact(
    work_dir: Path,
    locator_code: str,
    dicom_path: Path,
    input_fingerprint: str,
) -> tuple[str, bytes, str] | None:
    """Check if verified DICOM and matching sidecar exist for exact retry.

    Returns (submission_id, dicom_bytes, checksum) if verified, else None.
    """
    if not dicom_path.is_file():
        return None
    sidecar = _sidecar_path(work_dir, locator_code)
    if not sidecar.is_file():
        return None

    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    if data.get("version") != _SIDECAR_VERSION:
        return None
    if data.get("locator_code") != locator_code:
        return None
    if input_fingerprint and data.get("input_fingerprint") != input_fingerprint:
        logger.info(
            "Sidecar attempt identity mismatch for locator %s; "
            "will not resume stale artifact",
            locator_code,
        )
        return None

    sub_id = data.get("submission_id")
    expected_checksum = data.get("checksum")
    if not sub_id or not isinstance(sub_id, str):
        return None
    if not expected_checksum or not isinstance(expected_checksum, str):
        return None

    try:
        dicom_bytes = dicom_path.read_bytes()
    except Exception:
        return None

    if not _is_verified_dicom(dicom_bytes):
        logger.warning(
            "Existing DICOM artifact for locator %s is not valid DICOM; "
            "skipping resume",
            locator_code,
        )
        return None

    actual_checksum = _sha256_hex(dicom_bytes)
    if actual_checksum != expected_checksum:
        logger.warning(
            "Existing DICOM checksum mismatch for locator %s; skipping resume",
            locator_code,
        )
        return None

    return sub_id, dicom_bytes, actual_checksum


def _load_or_create_submission_id(
    work_dir: Path,
    locator_code: str,
    dicom_checksum: str,
    input_fingerprint: str = "",
) -> str:
    """Return an existing submission ID if the stored checksum matches,
    otherwise generate a fresh one and persist it.

    A new study attempt (different DICOM bytes / different checksum) always
    gets a new submission ID.  The ID is never reused with different bytes.

    Parameters
    ----------
    work_dir:
        Local private work directory for sidecars.
    locator_code:
        Four-digit session locator (used as part of the sidecar filename).
    dicom_checksum:
        Hex SHA-256 of the DICOM bytes for this attempt.
    input_fingerprint:
        Optional non-sensitive fingerprint of input files.

    Returns
    -------
    str
        Stable submission identifier (UUID hex string, ≤191 chars).
    """
    sidecar = _sidecar_path(work_dir, locator_code)
    if sidecar.is_file():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            if (
                data.get("version") == _SIDECAR_VERSION
                and data.get("checksum") == dicom_checksum
                and (
                    not input_fingerprint
                    or not data.get("input_fingerprint")
                    or data.get("input_fingerprint") == input_fingerprint
                )
            ):
                existing_id: str = data["submission_id"]
                logger.info(
                    "Reusing existing submission ID for locator %s (checksum match)",
                    locator_code,
                )
                return existing_id
        except Exception:
            logger.warning(
                "Sidecar for locator %s is corrupt; generating new submission ID",
                locator_code,
            )

    new_id = str(uuid.uuid4())
    sidecar_data = {
        "version": _SIDECAR_VERSION,
        "locator_code": locator_code,
        "submission_id": new_id,
        "checksum": dicom_checksum,
        "input_fingerprint": input_fingerprint,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(sidecar_data, indent=2), encoding="utf-8")
    logger.info("Generated new submission ID for locator %s", locator_code)
    return new_id


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Public workflow
# ---------------------------------------------------------------------------


def run_grabber_roundtrip(
    locator_code: str,
    radiograph_npz_path: str | Path,
    gain_npz_path: str | Path,
    output_dicom_dir: str | Path,
    *,
    client: MHCSGrabberClient | None = None,
    work_dir: str | Path | None = None,
    calibration_dir: str | Path | None = None,
    max_upload_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    upload_timeout: float = 30.0,
    upload_connect_timeout: float = 10.0,
    resume: bool | None = None,
) -> GrabberWorkflowResult:
    """Execute the full MHCS Core Grabber round-trip workflow.

    Steps
    -----
    1. Check for existing verified DICOM and matching sidecar (exact retry).
       If found, skip manifest lookup and conversion (handles server-side
       locator invalidation after successful initial ingestion).
    2. Retrieve the minimal DICOM manifest from MHCS Core (if not resuming).
    3. Convert the local NPZ radiograph + gain into a validated Part 10 DICOM
       via :func:`mpips.conversion.convert_npz_to_dicom`.
    4. Compute the SHA-256 checksum of the generated DICOM.
    5. Load or generate a stable client submission ID.
    6. Upload the DICOM to MHCS Core with idempotency headers.
    7. On upload failure, retain the DICOM on disk for exact retry.
    8. Return a non-sensitive :class:`GrabberWorkflowResult`.

    Parameters
    ----------
    locator_code:
        Four-digit radiography-session locator code.
    radiograph_npz_path:
        Path to the radiograph NPZ file.
    gain_npz_path:
        Path to the gain calibration NPZ file.
    output_dicom_dir:
        Directory in which the generated DICOM is written.
    client:
        Optional pre-constructed :class:`MHCSGrabberClient`. When ``None``,
        a client is created from environment variables.
    work_dir:
        Private work directory for DICOM sidecar/submission ID storage.
        Defaults to ``<output_dicom_dir>/mpips-grabber-work/``.
    calibration_dir:
        Optional calibration artifact directory for the converter.
    max_upload_attempts:
        Maximum number of upload attempts (initial + retries).
    upload_timeout:
        Per-upload request timeout in seconds.
    upload_connect_timeout:
        Connection timeout for upload requests.
    resume:
        Optional explicit resume control:
        - None (default): safely resume if verified artifact + sidecar match.
        - True: require existing verified artifact + sidecar (fail otherwise).
        - False: force fresh manifest lookup and conversion.
    """
    if client is None:
        client = MHCSGrabberClient.from_env(
            timeout=upload_timeout,
            connect_timeout=upload_connect_timeout,
        )

    out_dir = Path(output_dicom_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    work = Path(work_dir).resolve() if work_dir else out_dir / "mpips-grabber-work"
    work.mkdir(parents=True, exist_ok=True)

    dicom_path = out_dir / f"{locator_code}.dcm"
    input_fingerprint = _compute_input_fingerprint(radiograph_npz_path, gain_npz_path)

    resumed_data = None
    if resume is not False:
        resumed_data = _try_resume_artifact(
            work_dir=work,
            locator_code=locator_code,
            dicom_path=dicom_path,
            input_fingerprint=input_fingerprint,
        )

    if resume is True and resumed_data is None:
        raise GrabberClientError(
            f"Explicit resume requested but no verified DICOM artifact and matching "
            f"sidecar found for locator {locator_code}"
        )

    if resumed_data is not None:
        submission_id, dicom_bytes, checksum = resumed_data
        logger.info(
            "Resuming exact retry for locator %s: existing verified DICOM artifact and "
            "matching attempt identity found; skipping manifest lookup and conversion",
            locator_code,
        )
    else:
        # ------------------------------------------------------------------
        # Step 1: Manifest lookup
        # ------------------------------------------------------------------
        logger.info("Step 1: manifest lookup for locator %s", locator_code)
        raw_manifest = client.get_manifest(locator_code)

        try:
            manifest = MHCSManifest.model_validate(raw_manifest)
        except Exception as exc:
            raise ValueError(
                f"MHCS Core manifest for locator {locator_code} "
                f"is schema-incompatible: {type(exc).__name__}"
            ) from exc

        # ------------------------------------------------------------------
        # Step 2: NPZ-to-DICOM conversion
        # ------------------------------------------------------------------
        logger.info("Step 2: converting NPZ to DICOM for locator %s", locator_code)
        try:
            convert_npz_to_dicom(
                radiograph_npz_path=radiograph_npz_path,
                gain_npz_path=gain_npz_path,
                manifest=manifest,
                output_dicom_path=dicom_path,
                calibration_dir=calibration_dir,
            )
        except (FileNotFoundError, ValueError, TimeoutError, ConversionError):
            raise
        except Exception as exc:
            raise ConversionError(
                f"Unexpected error during NPZ-to-DICOM conversion: {exc}"
            ) from exc

        # ------------------------------------------------------------------
        # Step 3: Read DICOM and compute SHA-256
        # ------------------------------------------------------------------
        dicom_bytes = dicom_path.read_bytes()
        checksum = _sha256_hex(dicom_bytes)
        logger.info(
            "Step 3: DICOM SHA-256 computed for locator %s (%d bytes)",
            locator_code,
            len(dicom_bytes),
        )

        # ------------------------------------------------------------------
        # Step 4: Load or generate stable submission ID
        # ------------------------------------------------------------------
        submission_id = _load_or_create_submission_id(
            work_dir=work,
            locator_code=locator_code,
            dicom_checksum=checksum,
            input_fingerprint=input_fingerprint,
        )

    # ------------------------------------------------------------------
    # Step 5: Upload with bounded retry
    # ------------------------------------------------------------------
    logger.info(
        "Step 5: uploading DICOM for locator %s (submission %s)",
        locator_code,
        submission_id,
    )
    last_exc: GrabberClientError | None = None
    for attempt in range(max_upload_attempts):
        if attempt > 0:
            delay = _backoff_seconds(attempt - 1)
            logger.info(
                "Retry attempt %d for locator %s after %.1fs back-off",
                attempt + 1,
                locator_code,
                delay,
            )
            time.sleep(delay)
        try:
            response_payload = client.upload_dicom(
                locator_code=locator_code,
                dicom_bytes=dicom_bytes,
                checksum_sha256=checksum,
                submission_id=submission_id,
            )
            # Upload succeeded; extract and return validated non-sensitive result.
            return _build_result(
                response_payload=response_payload,
                locator_code=locator_code,
                checksum=checksum,
                dicom_bytes_len=len(dicom_bytes),
            )
        except GrabberIdempotencyConflictError:
            # Non-retryable; propagate immediately.
            raise
        except GrabberClientError as exc:
            last_exc = exc
            if not _is_retryable(exc):
                break
            logger.warning(
                "Transient error on upload attempt %d for locator %s: %s; "
                "DICOM retained at %s",
                attempt + 1,
                locator_code,
                type(exc).__name__,
                dicom_path,
            )

    # All attempts exhausted; DICOM already retained on disk.
    assert last_exc is not None  # always set when loop ends without return
    raise last_exc


def _build_result(
    response_payload: dict[str, Any],
    locator_code: str,
    checksum: str,
    dicom_bytes_len: int,
) -> GrabberWorkflowResult:
    """Extract non-sensitive fields from the server response and validate them."""
    if not isinstance(response_payload, dict):
        raise GrabberResponseValidationError(
            f"Malformed upload response payload for locator {locator_code}: "
            "expected dict"
        )

    study_id = response_payload.get("study_id")
    if not study_id or not isinstance(study_id, str):
        raise GrabberResponseValidationError(
            f"Upload response missing required study_id for locator {locator_code}"
        )

    display_ref = response_payload.get("display_reference")
    if not display_ref or not isinstance(display_ref, str):
        raise GrabberResponseValidationError(
            f"Upload response missing required display_reference "
            f"for locator {locator_code}"
        )

    terminal_state = response_payload.get("terminal_state")
    if terminal_state != "awaiting_ai":
        raise GrabberResponseValidationError(
            f"Invalid response terminal_state: expected 'awaiting_ai', "
            f"got {terminal_state!r} for locator {locator_code}"
        )

    replayed = response_payload.get("replayed", False)
    http_status = response_payload.get("_http_status")
    if http_status == 200 and replayed is not True:
        raise GrabberResponseValidationError(
            f"Invalid replay semantics: HTTP 200 received without replayed=True "
            f"for locator {locator_code}"
        )
    if http_status == 201 and replayed is True:
        raise GrabberResponseValidationError(
            f"Invalid replay semantics: HTTP 201 received with replayed=True "
            f"for locator {locator_code}"
        )

    return GrabberWorkflowResult(
        study_id=study_id,
        display_reference=display_ref,
        terminal_state=terminal_state,
        replayed=bool(replayed),
        locator_code=locator_code,
        checksum=checksum,
        bytes=dicom_bytes_len,
    )


# ---------------------------------------------------------------------------
# Convenience env-var re-exports (for documentation / tooling)
# ---------------------------------------------------------------------------

#: Names of environment variables consumed by this module.
REQUIRED_ENV_VARS: tuple[str, ...] = (
    "MHCS_GRABBER_BASE_URL",
    "MHCS_GRABBER_TOKEN",
)
OPTIONAL_ENV_VARS: tuple[str, ...] = ("MHCS_GRABBER_ID",)

__all__: list[str] = [
    "GrabberWorkflowResult",
    "run_grabber_roundtrip",
    "REQUIRED_ENV_VARS",
    "OPTIONAL_ENV_VARS",
    "GrabberTransientNetworkError",
    "GrabberTimeoutError",
    "GrabberConnectionError",
    "GrabberSessionStateError",
    "GrabberSessionIneligibleError",
    "GrabberResponseValidationError",
]
