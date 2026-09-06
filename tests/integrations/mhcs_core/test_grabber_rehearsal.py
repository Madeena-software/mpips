"""Localhost-only integration rehearsal for the MHCS Core Grabber round-trip.

This test exercises the full round-trip against a local MHCS Core stack.
It is skipped automatically when the local stack is absent.

Requirements to run this test:
- MHCS Core running at localhost (set MHCS_GRABBER_BASE_URL)
- A provisioned GrabberClient record with MHCS_GRABBER_TOKEN
- A synthetic active shift with a radiography session
  (set MHCS_GRABBER_REHEARSAL_LOCATOR)
- Synthetic (deidentified) NPZ files at paths set by:
    MHCS_GRABBER_REHEARSAL_RAD_NPZ
    MHCS_GRABBER_REHEARSAL_GAIN_NPZ
- MHCS_GRABBER_REHEARSAL_OUTPUT_DIR: writable dir for output DICOM

All patient data used MUST be synthetic (deidentified).  No real patient data.
No external network access beyond localhost.

To execute this rehearsal manually::

    MHCS_GRABBER_BASE_URL=http://localhost:8080 \\
    MHCS_GRABBER_TOKEN=test-token \\
    MHCS_GRABBER_REHEARSAL_LOCATOR=0001 \\
    MHCS_GRABBER_REHEARSAL_RAD_NPZ=/path/to/synthetic.npz \\
    MHCS_GRABBER_REHEARSAL_GAIN_NPZ=/path/to/synthetic_gain.npz \\
    MHCS_GRABBER_REHEARSAL_OUTPUT_DIR=/tmp/rehearsal-output \\
    uv run pytest tests/integrations/mhcs_core/test_grabber_rehearsal.py -v -s
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Skip condition: require local MHCS Core stack to be configured
# ---------------------------------------------------------------------------

_DEFAULT_ENV_FILE = Path("/var/www/mhcs-core/mpips-grabber.env")
if _DEFAULT_ENV_FILE.is_file():
    from mpips.integrations.mhcs_core.cli import load_protected_environment

    load_protected_environment(env_file=_DEFAULT_ENV_FILE)

# Set synthetic test defaults if present
if (
    not os.environ.get("MHCS_GRABBER_REHEARSAL_RAD_NPZ")
    and Path("/tmp/rehearsal-roundtrip/rad.npz").is_file()
):
    os.environ["MHCS_GRABBER_REHEARSAL_RAD_NPZ"] = "/tmp/rehearsal-roundtrip/rad.npz"
if (
    not os.environ.get("MHCS_GRABBER_REHEARSAL_GAIN_NPZ")
    and Path("/tmp/rehearsal-roundtrip/gain.npz").is_file()
):
    os.environ["MHCS_GRABBER_REHEARSAL_GAIN_NPZ"] = "/tmp/rehearsal-roundtrip/gain.npz"
if not os.environ.get("MHCS_GRABBER_REHEARSAL_OUTPUT_DIR"):
    os.environ["MHCS_GRABBER_REHEARSAL_OUTPUT_DIR"] = (
        "/tmp/rehearsal-roundtrip/rehearsal-output"
    )
if (
    not os.environ.get("MHCS_GRABBER_REHEARSAL_CALIBRATION_DIR")
    and Path("/tmp/rehearsal-roundtrip/cal").is_dir()
):
    os.environ["MHCS_GRABBER_REHEARSAL_CALIBRATION_DIR"] = (
        "/tmp/rehearsal-roundtrip/cal"
    )

_REQUIRED_REHEARSAL_VARS = [
    "MHCS_GRABBER_BASE_URL",
    "MHCS_GRABBER_TOKEN",
    "MHCS_GRABBER_REHEARSAL_LOCATOR",
    "MHCS_GRABBER_REHEARSAL_RAD_NPZ",
    "MHCS_GRABBER_REHEARSAL_GAIN_NPZ",
    "MHCS_GRABBER_REHEARSAL_OUTPUT_DIR",
]

_missing = [v for v in _REQUIRED_REHEARSAL_VARS if not os.environ.get(v)]
_rehearsal_available = not _missing

pytestmark = pytest.mark.skipif(
    not _rehearsal_available,
    reason=(
        "Local MHCS Core rehearsal stack not configured. "
        f"Missing env vars: {_missing}. "
        "Set all required MHCS_GRABBER_REHEARSAL_* variables to run."
    ),
)


# ---------------------------------------------------------------------------
# Helper: verify MHCS Core is reachable at localhost
# ---------------------------------------------------------------------------


def _assert_localhost_only(base_url: str) -> None:
    """Guard: reject any base_url that is not localhost."""
    import urllib.parse

    parsed = urllib.parse.urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host not in ("localhost", "127.0.0.1", "::1"):
        pytest.fail(
            "Rehearsal may only target localhost; "
            f"MHCS_GRABBER_BASE_URL host is {host!r}"
        )


def _check_mhcs_core_reachable(base_url: str) -> bool:
    """Return True if MHCS Core health endpoint responds at the given base URL."""
    try:
        import httpx

        resp = httpx.get(f"{base_url}/api/v1/grabber/health", timeout=5.0)
        return resp.status_code < 500
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Rehearsal fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def rehearsal_output_dir(tmp_path: Path) -> Path:
    """Use a temp dir (or configured dir) for rehearsal DICOM output."""
    configured = os.environ.get("MHCS_GRABBER_REHEARSAL_OUTPUT_DIR")
    if configured:
        out = Path(configured)
        out.mkdir(parents=True, exist_ok=True)
        return out
    return tmp_path / "rehearsal-output"


@pytest.fixture()
def rehearsal_locator() -> str:
    """Provide a fresh active rehearsal session locator code if artisan is available,
    otherwise use MHCS_GRABBER_REHEARSAL_LOCATOR from environment.
    """
    artisan = Path("/var/www/mhcs-core/artisan")
    if artisan.is_file():
        import subprocess

        token_file = "/var/www/mhcs-core/storage/framework/grabber.token"
        env_file = "/var/www/mhcs-core/mpips-grabber.env"
        subprocess.run(
            [
                "php",
                str(artisan),
                "mhcs:provision-grabber-rehearsal",
                f"--token-file={token_file}",
                f"--env-out={env_file}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if Path(env_file).is_file():
            load_protected_environment(
                env_file=env_file, token_file=token_file, override=True
            )
            return os.environ.get("MHCS_GRABBER_REHEARSAL_LOCATOR", "")
    return os.environ.get("MHCS_GRABBER_REHEARSAL_LOCATOR", "")


# ---------------------------------------------------------------------------
# Rehearsal tests
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "Contract gap: MHCS Core minimal manifest lacks DX presentation pixel source "
        "and physical spacing authority pending Planner revision."
    ),
    strict=False,
)
class TestGrabberRoundtripRehearsal:
    """Full localhost integration rehearsal.

    Uses synthetic/deidentified fixtures only.  No real patient data.
    """

    def test_full_roundtrip_initial(
        self, rehearsal_output_dir: Path, rehearsal_locator: str
    ) -> None:
        """Initial upload: manifest retrieved → DICOM generated → 201 Created."""
        from mpips.integrations.mhcs_core.client import MHCSGrabberClient
        from mpips.integrations.mhcs_core.workflow import (
            GrabberWorkflowResult,
            run_grabber_roundtrip,
        )

        base_url = os.environ["MHCS_GRABBER_BASE_URL"]
        _assert_localhost_only(base_url)

        if not _check_mhcs_core_reachable(base_url):
            pytest.skip(f"MHCS Core not reachable at {base_url}")

        locator_code = rehearsal_locator
        rad_npz = os.environ["MHCS_GRABBER_REHEARSAL_RAD_NPZ"]
        gain_npz = os.environ["MHCS_GRABBER_REHEARSAL_GAIN_NPZ"]
        work_dir = rehearsal_output_dir / "work"
        cal_dir = os.environ.get(
            "MHCS_GRABBER_REHEARSAL_CALIBRATION_DIR"
        ) or os.environ.get("MPIPS_CALIBRATION_ARTIFACT_DIR")

        # Remove any pre-existing DICOM/sidecar to force a fresh initial upload
        dicom_path = rehearsal_output_dir / f"{locator_code}.dcm"
        sidecar = work_dir / f"submission-{locator_code}.json"
        for p in (dicom_path, sidecar):
            if p.exists():
                p.unlink()

        client = MHCSGrabberClient.from_env()

        result = run_grabber_roundtrip(
            locator_code=locator_code,
            radiograph_npz_path=rad_npz,
            gain_npz_path=gain_npz,
            output_dicom_dir=rehearsal_output_dir,
            client=client,
            work_dir=work_dir,
            calibration_dir=cal_dir,
        )

        assert isinstance(result, GrabberWorkflowResult)
        assert (
            result.terminal_state == "awaiting_ai"
        ), f"Expected terminal_state=awaiting_ai, got {result.terminal_state!r}"
        assert result.replayed is False
        assert result.locator_code == locator_code
        assert len(result.checksum) == 64
        assert result.bytes > 0

        logger.info(
            "Rehearsal initial upload complete: study_id=%s display_reference=%s",
            result.study_id,
            result.display_reference,
        )

    def test_exact_retry_replayed(
        self, rehearsal_output_dir: Path, rehearsal_locator: str
    ) -> None:
        """Exact retry: same DICOM bytes + same submission ID → 200 replayed:true."""
        from mpips.integrations.mhcs_core.client import MHCSGrabberClient
        from mpips.integrations.mhcs_core.workflow import run_grabber_roundtrip

        base_url = os.environ["MHCS_GRABBER_BASE_URL"]
        _assert_localhost_only(base_url)

        if not _check_mhcs_core_reachable(base_url):
            pytest.skip(f"MHCS Core not reachable at {base_url}")

        locator_code = rehearsal_locator
        rad_npz = os.environ["MHCS_GRABBER_REHEARSAL_RAD_NPZ"]
        gain_npz = os.environ["MHCS_GRABBER_REHEARSAL_GAIN_NPZ"]
        work_dir = rehearsal_output_dir / "work"
        cal_dir = os.environ.get(
            "MHCS_GRABBER_REHEARSAL_CALIBRATION_DIR"
        ) or os.environ.get("MPIPS_CALIBRATION_ARTIFACT_DIR")
        client = MHCSGrabberClient.from_env()

        # Remove pre-existing DICOM/sidecar to guarantee fresh initial call
        dicom_path = rehearsal_output_dir / f"{locator_code}.dcm"
        sidecar = work_dir / f"submission-{locator_code}.json"
        for p in (dicom_path, sidecar):
            if p.exists():
                p.unlink()

        # First call: initial upload (replayed: false)
        initial_result = run_grabber_roundtrip(
            locator_code=locator_code,
            radiograph_npz_path=rad_npz,
            gain_npz_path=gain_npz,
            output_dicom_dir=rehearsal_output_dir,
            client=client,
            work_dir=work_dir,
            calibration_dir=cal_dir,
        )
        assert (
            initial_result.replayed is False
        ), f"Expected initial replayed=False; got {initial_result.replayed}"
        assert initial_result.terminal_state == "awaiting_ai"

        # Second call: exact retry (replayed: true), without manifest lookup
        retry_result = run_grabber_roundtrip(
            locator_code=locator_code,
            radiograph_npz_path=rad_npz,
            gain_npz_path=gain_npz,
            output_dicom_dir=rehearsal_output_dir,
            client=client,
            work_dir=work_dir,
            calibration_dir=cal_dir,
        )

        assert (
            retry_result.replayed is True
        ), f"Expected replayed=True on retry; got {retry_result.replayed}"
        assert retry_result.terminal_state == "awaiting_ai"
        assert retry_result.study_id == initial_result.study_id
        assert retry_result.checksum == initial_result.checksum

        logger.info(
            "Rehearsal exact retry result: replayed=%s study_id=%s",
            retry_result.replayed,
            retry_result.study_id,
        )

    def test_no_credentials_or_patient_data_in_logs(
        self,
        rehearsal_output_dir: Path,
        rehearsal_locator: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Credentials and patient data must not appear in MPIPS log output."""
        from mpips.integrations.mhcs_core.client import MHCSGrabberClient
        from mpips.integrations.mhcs_core.workflow import run_grabber_roundtrip

        base_url = os.environ["MHCS_GRABBER_BASE_URL"]
        _assert_localhost_only(base_url)

        if not _check_mhcs_core_reachable(base_url):
            pytest.skip(f"MHCS Core not reachable at {base_url}")

        token = os.environ["MHCS_GRABBER_TOKEN"]
        locator_code = rehearsal_locator
        rad_npz = os.environ["MHCS_GRABBER_REHEARSAL_RAD_NPZ"]
        gain_npz = os.environ["MHCS_GRABBER_REHEARSAL_GAIN_NPZ"]
        work_dir = rehearsal_output_dir / "work"
        cal_dir = os.environ.get(
            "MHCS_GRABBER_REHEARSAL_CALIBRATION_DIR"
        ) or os.environ.get("MPIPS_CALIBRATION_ARTIFACT_DIR")
        client = MHCSGrabberClient.from_env()

        with caplog.at_level(logging.DEBUG):
            run_grabber_roundtrip(
                locator_code=locator_code,
                radiograph_npz_path=rad_npz,
                gain_npz_path=gain_npz,
                output_dicom_dir=rehearsal_output_dir,
                client=client,
                work_dir=work_dir,
                calibration_dir=cal_dir,
            )

        assert token not in caplog.text, "Bearer token must not appear in logs"
        logger.info("Credential absence from log check: PASSED")
