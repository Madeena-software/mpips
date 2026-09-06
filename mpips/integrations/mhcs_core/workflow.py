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
    GrabberIdempotencyConflictError,
    GrabberRateLimitError,
    GrabberServerError,
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
    return isinstance(exc, (GrabberRateLimitError, GrabberServerError))


# ---------------------------------------------------------------------------
# Submission ID / sidecar persistence
# ---------------------------------------------------------------------------

_SIDECAR_VERSION = "1"


def _sidecar_path(work_dir: Path, locator_code: str) -> Path:
    return work_dir / f"submission-{locator_code}.json"


def _load_or_create_submission_id(
    work_dir: Path,
    locator_code: str,
    dicom_checksum: str,
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
            ):
                existing_id: str = data["submission_id"]
                logger.info(
                    "Reusing existing submission ID for locator %s " "(checksum match)",
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
) -> GrabberWorkflowResult:
    """Execute the full MHCS Core Grabber round-trip workflow.

    Steps
    -----
    1. Retrieve the minimal DICOM manifest from MHCS Core.
    2. Convert the local NPZ radiograph + gain into a validated Part 10 DICOM
       via :func:`mpips.conversion.convert_npz_to_dicom`.
    3. Compute the SHA-256 checksum of the generated DICOM.
    4. Load or generate a stable client submission ID.
    5. Upload the DICOM to MHCS Core with idempotency headers.
    6. On upload failure, retain the DICOM on disk for exact retry.
    7. Return a non-sensitive :class:`GrabberWorkflowResult`.

    Idempotency
    -----------
    If a prior DICOM for this locator code already exists at
    ``<output_dicom_dir>/<locator_code>.dcm`` and a matching sidecar exists,
    the workflow skips conversion and re-uploads the same artifact.

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

    Returns
    -------
    GrabberWorkflowResult

    Raises
    ------
    GrabberClientError
        On authentication failure, locator not found, rate limit, or
        non-retryable server error after all attempts are exhausted.
    GrabberIdempotencyConflictError
        When the submission ID conflicts with a different DICOM on the server.
    ConversionError
        When NPZ-to-DICOM conversion fails.
    ValueError
        When the manifest response is schema-incompatible.
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

    # ------------------------------------------------------------------
    # Step 1: Manifest lookup
    # ------------------------------------------------------------------
    logger.info("Step 1: manifest lookup for locator %s", locator_code)
    raw_manifest = client.get_manifest(locator_code)

    try:
        manifest = MHCSManifest.model_validate(raw_manifest)
    except Exception as exc:
        raise ValueError(
            f"MHCS Core manifest for locator {locator_code} is schema-incompatible: "
            f"{type(exc).__name__}"
        ) from exc

    # ------------------------------------------------------------------
    # Step 2: NPZ-to-DICOM conversion (skip if exact artifact already exists)
    # ------------------------------------------------------------------
    if dicom_path.is_file():
        logger.info(
            "Step 2: DICOM already exists at %s; skipping conversion", dicom_path
        )
    else:
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
    submission_id = _load_or_create_submission_id(work, locator_code, checksum)

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
            # Upload succeeded; extract and return non-sensitive result.
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
    """Extract non-sensitive fields from the server response."""
    return GrabberWorkflowResult(
        study_id=str(response_payload.get("study_id", "")),
        display_reference=str(response_payload.get("display_reference", "")),
        terminal_state=str(response_payload.get("terminal_state", "")),
        replayed=bool(response_payload.get("replayed", False)),
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
]
