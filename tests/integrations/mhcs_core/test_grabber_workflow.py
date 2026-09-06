"""Unit tests for run_grabber_roundtrip orchestration workflow.

All tests use mocked MHCSGrabberClient and mocked convert_npz_to_dicom.
No live server or real NPZ files are required.

Tests cover:
- Full round-trip: manifest → convert → checksum → upload → 201 result
- Retry path: existing DICOM + submission ID reused → 200 replayed
- Failed upload: DICOM retained on disk, exception propagated
- Idempotency conflict: non-retryable exception propagated immediately
- Patient data absence from logs during manifest lookup
- Credential absence from logs during upload
- Submission ID persistence and reuse on exact retry
- New submission ID on different DICOM bytes
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mpips.integrations.mhcs_core.client import (
    GrabberClientError,
    GrabberConnectionError,
    GrabberIdempotencyConflictError,
    GrabberLocatorNotFoundError,
    GrabberResponseValidationError,
    GrabberServerError,
    GrabberSessionStateError,
    GrabberTimeoutError,
    MHCSGrabberClient,
)
from mpips.integrations.mhcs_core.workflow import (
    GrabberWorkflowResult,
    _compute_input_fingerprint,
    _load_or_create_submission_id,
    _sha256_hex,
    run_grabber_roundtrip,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures (no real patient data)
# ---------------------------------------------------------------------------

_LOCATOR = "9999"

MINIMAL_MANIFEST_DICT = {
    "manifest_version": "1.0",
    "patient": {
        "medical_record_number": "MRN-SYNTH-WORKFLOW-001",
        "name": {"full_name": "SYNTHETIC WORKFLOW PATIENT"},
        "sex": "unknown",
    },
}

# Minimal valid DICOM bytes (DICM magic at byte 128)
_DICOM_BYTES = b"\x00" * 128 + b"DICM" + b"\x00" * 4

_CHECKSUM = hashlib.sha256(_DICOM_BYTES).hexdigest()

_UPLOAD_RESPONSE_201 = {
    "status": "ingested",
    "study_id": "STU-SYNTH-001",
    "display_reference": "REF-SYNTH-001",
    "admission_id": "ADM-SYNTH-001",
    "locator_code": _LOCATOR,
    "terminal_state": "awaiting_ai",
    "replayed": False,
    "checksum": _CHECKSUM,
    "bytes": len(_DICOM_BYTES),
}

_UPLOAD_RESPONSE_200_REPLAYED = {
    **_UPLOAD_RESPONSE_201,
    "replayed": True,
}


def _make_mock_client(
    manifest: dict[str, Any] = MINIMAL_MANIFEST_DICT,
    upload_return: dict[str, Any] = _UPLOAD_RESPONSE_201,
    upload_side_effect: Exception | list[Any] | None = None,
) -> MagicMock:
    client = MagicMock(spec=MHCSGrabberClient)
    client.get_manifest.return_value = manifest
    if upload_side_effect is not None:
        client.upload_dicom.side_effect = upload_side_effect
    else:
        client.upload_dicom.return_value = upload_return
    return client


def _fake_convert_side_effect(
    radiograph_npz_path: Any,
    gain_npz_path: Any,
    manifest: Any,
    output_dicom_path: Any,
    calibration_dir: Any = None,
) -> Path:
    p = Path(output_dicom_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(_DICOM_BYTES)
    return p


def _write_fake_dicom(path: Path) -> None:
    """Write synthetic DICOM bytes to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_DICOM_BYTES)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunGrabberRoundtrip:
    def test_full_roundtrip_201_result(self, tmp_path: Path) -> None:
        """Full round-trip: manifest → convert → checksum → upload → 201 result."""
        client = _make_mock_client()
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:

            mock_convert.side_effect = _fake_convert_side_effect

            result = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "rad.npz",
                gain_npz_path=tmp_path / "gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=tmp_path / "work",
            )

        assert isinstance(result, GrabberWorkflowResult)
        assert result.study_id == "STU-SYNTH-001"
        assert result.terminal_state == "awaiting_ai"
        assert result.replayed is False
        assert result.locator_code == _LOCATOR
        assert result.checksum == _CHECKSUM
        assert result.bytes == len(_DICOM_BYTES)

        # convert_npz_to_dicom was called once
        mock_convert.assert_called_once()
        # manifest object passed to convert was validated MHCSManifest
        call_kwargs = mock_convert.call_args
        assert call_kwargs is not None
        from mpips.api.schemas.dicom import MHCSManifest

        manifest_arg = call_kwargs.kwargs.get("manifest") or call_kwargs.args[2]
        assert isinstance(manifest_arg, MHCSManifest)

    def test_retry_path_reuses_existing_dicom(self, tmp_path: Path) -> None:
        """Existing DICOM + matching sidecar → skip conversion, reuse bytes."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Pre-write the DICOM
        dicom_path = out_dir / f"{_LOCATOR}.dcm"
        dicom_path.write_bytes(_DICOM_BYTES)

        rad_path = tmp_path / "rad.npz"
        gain_path = tmp_path / "gain.npz"
        fp = _compute_input_fingerprint(rad_path, gain_path)

        # Pre-write the sidecar with matching checksum and input fingerprint
        sub_id = "pre-existing-submission-id"
        sidecar = work_dir / f"submission-{_LOCATOR}.json"
        sidecar.write_text(
            json.dumps(
                {
                    "version": "1",
                    "locator_code": _LOCATOR,
                    "submission_id": sub_id,
                    "checksum": _CHECKSUM,
                    "input_fingerprint": fp,
                }
            ),
            encoding="utf-8",
        )

        client = _make_mock_client(upload_return=_UPLOAD_RESPONSE_200_REPLAYED)
        # Even if get_manifest raises locator invalidated, exact retry must succeed
        client.get_manifest.side_effect = GrabberLocatorNotFoundError(
            "Locator invalidated"
        )

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            result = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=rad_path,
                gain_npz_path=gain_path,
                output_dicom_dir=out_dir,
                client=client,
                work_dir=work_dir,
            )

        # Manifest lookup and conversion must NOT be called when resuming
        client.get_manifest.assert_not_called()
        mock_convert.assert_not_called()
        assert result.replayed is True
        assert result.terminal_state == "awaiting_ai"
        # Same submission ID reused
        client.upload_dicom.assert_called_once_with(
            locator_code=_LOCATOR,
            dicom_bytes=_DICOM_BYTES,
            checksum_sha256=_CHECKSUM,
            submission_id=sub_id,
        )

    def test_failed_upload_retains_dicom(self, tmp_path: Path) -> None:
        """When upload fails, the generated DICOM is retained on disk."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        client = _make_mock_client(
            upload_side_effect=GrabberClientError("connection lost")
        )

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:

            mock_convert.side_effect = _fake_convert_side_effect

            with pytest.raises(GrabberClientError, match="connection lost"):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                    max_upload_attempts=1,
                )

        # DICOM must still be on disk after failed upload
        dicom_path = out_dir / f"{_LOCATOR}.dcm"
        assert dicom_path.is_file(), "DICOM must be retained after upload failure"
        assert dicom_path.read_bytes() == _DICOM_BYTES

    def test_idempotency_conflict_raises_immediately(self, tmp_path: Path) -> None:
        """409 conflict → GrabberIdempotencyConflictError, no retry."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        client = _make_mock_client(
            upload_side_effect=GrabberIdempotencyConflictError("conflict")
        )

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:

            mock_convert.side_effect = _fake_convert_side_effect

            with pytest.raises(GrabberIdempotencyConflictError):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                    max_upload_attempts=3,
                )

        # upload_dicom called exactly once (no retry on conflict)
        client.upload_dicom.assert_called_once()

    def test_patient_data_absent_from_logs(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Patient identity fields must not appear in log output."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        sensitive_manifest = {
            "manifest_version": "1.0",
            "patient": {
                "medical_record_number": "SENSITIVEPATIENT-MRN-999",
                "name": {"full_name": "JOHN DOE SENSITIVE"},
                "sex": "male",
                "birth_date": "1980-01-01",
            },
        }

        client = _make_mock_client(manifest=sensitive_manifest)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:

            mock_convert.side_effect = _fake_convert_side_effect

            with caplog.at_level(logging.DEBUG):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

        all_log_text = caplog.text
        assert (
            "SENSITIVEPATIENT-MRN-999" not in all_log_text
        ), "MRN must not appear in logs"
        assert (
            "JOHN DOE SENSITIVE" not in all_log_text
        ), "Patient name must not appear in logs"
        assert "1980-01-01" not in all_log_text, "Birth date must not appear in logs"

    def test_credential_absent_from_logs(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Bearer token must not appear in log output."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        secret_token = "SUPER_SECRET_GRABBER_TOKEN_VALUE_12345"
        real_client = MHCSGrabberClient(
            base_url="http://localhost:9999", token=secret_token
        )
        # Patch the actual HTTP calls so we don't need a live server
        real_client.get_manifest = MagicMock(  # type: ignore[method-assign]
            return_value=MINIMAL_MANIFEST_DICT
        )
        real_client.upload_dicom = MagicMock(  # type: ignore[method-assign]
            return_value=_UPLOAD_RESPONSE_201
        )

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:

            mock_convert.side_effect = _fake_convert_side_effect

            with caplog.at_level(logging.DEBUG):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=real_client,
                    work_dir=tmp_path / "work",
                )

        assert (
            secret_token not in caplog.text
        ), "Credential must not appear in log output"

    def test_5xx_server_error_retried_then_raises(self, tmp_path: Path) -> None:
        """5xx errors are retried; after exhaustion the error is raised."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        client = _make_mock_client(
            upload_side_effect=GrabberServerError("server error")
        )

        with (
            patch(
                "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
            ) as mock_convert,
            patch("mpips.integrations.mhcs_core.workflow.time.sleep"),
        ):

            mock_convert.side_effect = _fake_convert_side_effect

            with pytest.raises(GrabberServerError):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                    max_upload_attempts=2,
                )

        # Should have been called twice (initial + 1 retry)
        assert client.upload_dicom.call_count == 2

    def test_exact_retry_after_initial_upload_with_locator_invalidation(
        self, tmp_path: Path
    ) -> None:
        """Initial 201 Created followed by exact retry 200 replayed: true
        succeeds even when server invalidates the locator after ingestion."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        client = MagicMock(spec=MHCSGrabberClient)
        client.get_manifest.side_effect = [
            MINIMAL_MANIFEST_DICT,
            GrabberLocatorNotFoundError("Locator invalidated after ingestion"),
        ]
        client.upload_dicom.side_effect = [
            _UPLOAD_RESPONSE_201,
            _UPLOAD_RESPONSE_200_REPLAYED,
        ]

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect

            # Initial upload
            res1 = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "rad.npz",
                gain_npz_path=tmp_path / "gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=work_dir,
            )
            assert res1.replayed is False
            assert res1.terminal_state == "awaiting_ai"

            # Exact retry with same locator and inputs
            res2 = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "rad.npz",
                gain_npz_path=tmp_path / "gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=work_dir,
            )
            assert res2.replayed is True
            assert res2.terminal_state == "awaiting_ai"
            assert res2.study_id == res1.study_id
            assert res2.checksum == res1.checksum

        # get_manifest was called ONLY once (during initial); skipped on exact retry
        client.get_manifest.assert_called_once()
        # convert was called ONLY once
        mock_convert.assert_called_once()
        # upload was called twice, both with the same submission ID
        assert client.upload_dicom.call_count == 2
        call1_args = client.upload_dicom.call_args_list[0].kwargs
        call2_args = client.upload_dicom.call_args_list[1].kwargs
        assert call1_args["submission_id"] == call2_args["submission_id"]
        assert call1_args["checksum_sha256"] == call2_args["checksum_sha256"]

    def test_different_inputs_do_not_reuse_stale_dicom(self, tmp_path: Path) -> None:
        """When locator is reused with different inputs, stale DICOM is not reused."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Write existing DICOM and sidecar for an earlier session
        old_dicom = out_dir / f"{_LOCATOR}.dcm"
        old_dicom.write_bytes(_DICOM_BYTES)
        sidecar = work_dir / f"submission-{_LOCATOR}.json"
        sidecar.write_text(
            json.dumps(
                {
                    "version": "1",
                    "locator_code": _LOCATOR,
                    "submission_id": "old-sub-id",
                    "checksum": _CHECKSUM,
                    "input_fingerprint": "completely-different-fingerprint",
                }
            ),
            encoding="utf-8",
        )

        client = _make_mock_client(upload_return=_UPLOAD_RESPONSE_201)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect

            result = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "new_rad.npz",
                gain_npz_path=tmp_path / "new_gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=work_dir,
            )

        # Must have fetched fresh manifest and reconverted
        client.get_manifest.assert_called_once_with(_LOCATOR)
        mock_convert.assert_called_once()
        assert result.replayed is False
        # Old submission ID must NOT be reused
        upload_sub_id = client.upload_dicom.call_args.kwargs["submission_id"]
        assert upload_sub_id != "old-sub-id"

    def test_upload_timeout_retried_and_succeeds(self, tmp_path: Path) -> None:
        """Timeout on upload is retried and succeeds on subsequent attempt."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        client = _make_mock_client(
            upload_side_effect=[
                GrabberTimeoutError("Upload timed out"),
                _UPLOAD_RESPONSE_201,
            ]
        )

        with (
            patch(
                "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
            ) as mock_convert,
            patch("mpips.integrations.mhcs_core.workflow.time.sleep"),
        ):
            mock_convert.side_effect = _fake_convert_side_effect
            result = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "rad.npz",
                gain_npz_path=tmp_path / "gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=tmp_path / "work",
                max_upload_attempts=2,
            )

        assert result.terminal_state == "awaiting_ai"
        assert client.upload_dicom.call_count == 2

    def test_upload_timeout_exhaustion_retains_dicom_and_raises(
        self, tmp_path: Path
    ) -> None:
        """When timeouts exhaust all attempts, GrabberTimeoutError is raised
        and DICOM retained.
        """
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        client = _make_mock_client(upload_side_effect=GrabberTimeoutError("Timeout"))

        with (
            patch(
                "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
            ) as mock_convert,
            patch("mpips.integrations.mhcs_core.workflow.time.sleep"),
        ):
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberTimeoutError):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                    max_upload_attempts=2,
                )

        assert (out_dir / f"{_LOCATOR}.dcm").is_file(), "DICOM must be retained on disk"
        assert client.upload_dicom.call_count == 2

    def test_upload_connection_error_retried_and_succeeds(self, tmp_path: Path) -> None:
        """Connection loss on upload is retried and succeeds on subsequent attempt."""
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        client = _make_mock_client(
            upload_side_effect=[
                GrabberConnectionError("Connection lost"),
                _UPLOAD_RESPONSE_201,
            ]
        )

        with (
            patch(
                "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
            ) as mock_convert,
            patch("mpips.integrations.mhcs_core.workflow.time.sleep"),
        ):
            mock_convert.side_effect = _fake_convert_side_effect
            result = run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "rad.npz",
                gain_npz_path=tmp_path / "gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=tmp_path / "work",
                max_upload_attempts=2,
            )

        assert result.terminal_state == "awaiting_ai"
        assert client.upload_dicom.call_count == 2

    def test_upload_connection_error_exhaustion_retains_dicom_and_raises(
        self, tmp_path: Path
    ) -> None:
        """When connection errors exhaust all attempts, GrabberConnectionError
        is raised and DICOM retained.
        """
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        client = _make_mock_client(
            upload_side_effect=GrabberConnectionError("Conn error")
        )

        with (
            patch(
                "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
            ) as mock_convert,
            patch("mpips.integrations.mhcs_core.workflow.time.sleep"),
        ):
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberConnectionError):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                    max_upload_attempts=2,
                )

        assert (out_dir / f"{_LOCATOR}.dcm").is_file(), "DICOM must be retained on disk"
        assert client.upload_dicom.call_count == 2

    def test_upload_session_ineligible_raises_immediately(self, tmp_path: Path) -> None:
        """409 session ineligible raises GrabberSessionStateError immediately
        without retry.
        """
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        client = _make_mock_client(
            upload_side_effect=GrabberSessionStateError("Session is not active")
        )

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberSessionStateError):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                    max_upload_attempts=3,
                )

        assert (out_dir / f"{_LOCATOR}.dcm").is_file()
        assert client.upload_dicom.call_count == 1

    def test_workflow_rejects_missing_study_id(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        bad_response = {**_UPLOAD_RESPONSE_201, "study_id": ""}
        client = _make_mock_client(upload_return=bad_response)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberResponseValidationError, match="study_id"):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

    def test_workflow_rejects_missing_display_reference(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        bad_response = {**_UPLOAD_RESPONSE_201, "display_reference": None}
        client = _make_mock_client(upload_return=bad_response)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(
                GrabberResponseValidationError, match="display_reference"
            ):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

    def test_workflow_rejects_completed_terminal_state(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        bad_response = {**_UPLOAD_RESPONSE_201, "terminal_state": "completed"}
        client = _make_mock_client(upload_return=bad_response)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberResponseValidationError, match="terminal_state"):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

    def test_workflow_rejects_arbitrary_terminal_state(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        bad_response = {**_UPLOAD_RESPONSE_201, "terminal_state": "unknown_state"}
        client = _make_mock_client(upload_return=bad_response)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberResponseValidationError, match="terminal_state"):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

    def test_workflow_rejects_200_without_replayed_true(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        bad_response = {**_UPLOAD_RESPONSE_201, "replayed": False, "_http_status": 200}
        client = _make_mock_client(upload_return=bad_response)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberResponseValidationError, match="replayed=True"):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

    def test_workflow_rejects_201_with_replayed_true(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        bad_response = {**_UPLOAD_RESPONSE_201, "replayed": True, "_http_status": 201}
        client = _make_mock_client(upload_return=bad_response)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            with pytest.raises(GrabberResponseValidationError, match="replayed=True"):
                run_grabber_roundtrip(
                    locator_code=_LOCATOR,
                    radiograph_npz_path=tmp_path / "rad.npz",
                    gain_npz_path=tmp_path / "gain.npz",
                    output_dicom_dir=out_dir,
                    client=client,
                    work_dir=tmp_path / "work",
                )

    def test_explicit_resume_true_fails_if_no_verified_artifact(
        self, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        client = _make_mock_client()
        with pytest.raises(GrabberClientError, match="Explicit resume requested"):
            run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=tmp_path / "rad.npz",
                gain_npz_path=tmp_path / "gain.npz",
                output_dicom_dir=out_dir,
                client=client,
                work_dir=tmp_path / "work",
                resume=True,
            )

    def test_explicit_resume_false_forces_fresh_conversion(
        self, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Existing DICOM and sidecar
        dicom_path = out_dir / f"{_LOCATOR}.dcm"
        dicom_path.write_bytes(_DICOM_BYTES)
        rad_path = tmp_path / "rad.npz"
        gain_path = tmp_path / "gain.npz"
        fp = _compute_input_fingerprint(rad_path, gain_path)
        sidecar = work_dir / f"submission-{_LOCATOR}.json"
        sidecar.write_text(
            json.dumps(
                {
                    "version": "1",
                    "locator_code": _LOCATOR,
                    "submission_id": "existing-sub-id",
                    "checksum": _CHECKSUM,
                    "input_fingerprint": fp,
                }
            ),
            encoding="utf-8",
        )

        client = _make_mock_client(upload_return=_UPLOAD_RESPONSE_201)

        with patch(
            "mpips.integrations.mhcs_core.workflow.convert_npz_to_dicom"
        ) as mock_convert:
            mock_convert.side_effect = _fake_convert_side_effect
            run_grabber_roundtrip(
                locator_code=_LOCATOR,
                radiograph_npz_path=rad_path,
                gain_npz_path=gain_path,
                output_dicom_dir=out_dir,
                client=client,
                work_dir=work_dir,
                resume=False,
            )

        # Forced fresh: get_manifest and convert MUST be called
        client.get_manifest.assert_called_once()
        mock_convert.assert_called_once()


# ---------------------------------------------------------------------------
# Submission ID persistence tests
# ---------------------------------------------------------------------------


class TestSubmissionIdPersistence:
    def test_new_submission_id_created_and_persisted(self, tmp_path: Path) -> None:
        sub_id = _load_or_create_submission_id(tmp_path, "1234", _CHECKSUM)
        assert isinstance(sub_id, str) and len(sub_id) > 0

        sidecar = tmp_path / "submission-1234.json"
        assert sidecar.is_file()
        data = json.loads(sidecar.read_text())
        assert data["submission_id"] == sub_id
        assert data["checksum"] == _CHECKSUM

    def test_existing_id_reused_on_matching_checksum(self, tmp_path: Path) -> None:
        first_id = _load_or_create_submission_id(tmp_path, "1234", _CHECKSUM)
        second_id = _load_or_create_submission_id(tmp_path, "1234", _CHECKSUM)
        assert first_id == second_id

    def test_new_id_on_different_checksum(self, tmp_path: Path) -> None:
        first_id = _load_or_create_submission_id(tmp_path, "1234", _CHECKSUM)
        other_checksum = "b" * 64
        second_id = _load_or_create_submission_id(tmp_path, "1234", other_checksum)
        assert first_id != second_id

    def test_corrupt_sidecar_replaced(self, tmp_path: Path) -> None:
        sidecar = tmp_path / "submission-1234.json"
        sidecar.write_text("not json", encoding="utf-8")
        sub_id = _load_or_create_submission_id(tmp_path, "1234", _CHECKSUM)
        assert isinstance(sub_id, str) and len(sub_id) > 0


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------


class TestSha256Hex:
    def test_known_value(self) -> None:
        data = b"hello"
        expected = hashlib.sha256(data).hexdigest()
        assert _sha256_hex(data) == expected

    def test_returns_64_chars(self) -> None:
        assert len(_sha256_hex(b"test")) == 64
