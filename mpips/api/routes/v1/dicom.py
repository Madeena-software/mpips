from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

import anyio
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from mpips.api.idempotency import (
    IdempotencyService,
    compute_manifest_fingerprint,
)
from mpips.api.api_key import require_api_key
from mpips.api.schemas.dicom import MHCSManifest
from mpips.conversion.service import run_isolated_dicom_conversion

router = APIRouter(prefix="", tags=["Radiographs"])

_concurrency_limiter: anyio.CapacityLimiter | None = None


def get_concurrency_limiter() -> anyio.CapacityLimiter:
    global _concurrency_limiter
    if _concurrency_limiter is None:
        try:
            max_conc = int(os.getenv("MPIPS_DICOM_MAX_CONCURRENT_CONVERSIONS", "4"))
            if max_conc <= 0:
                max_conc = 4
        except ValueError:
            max_conc = 4
        _concurrency_limiter = anyio.CapacityLimiter(max_conc)
    return _concurrency_limiter


def _get_upload_limits() -> tuple[int, int, int, int]:
    try:
        max_manifest = int(
            os.getenv("MPIPS_DICOM_MAX_MANIFEST_BYTES", str(1 * 1024 * 1024))
        )
        if max_manifest <= 0:
            max_manifest = 1 * 1024 * 1024
    except ValueError:
        max_manifest = 1 * 1024 * 1024

    try:
        max_rad = int(
            os.getenv("MPIPS_DICOM_MAX_RADIOGRAPH_BYTES", str(100 * 1024 * 1024))
        )
        if max_rad <= 0:
            max_rad = 50 * 1024 * 1024
    except ValueError:
        max_rad = 50 * 1024 * 1024

    try:
        max_gain = int(os.getenv("MPIPS_DICOM_MAX_GAIN_BYTES", str(50 * 1024 * 1024)))
        if max_gain <= 0:
            max_gain = 50 * 1024 * 1024
    except ValueError:
        max_gain = 50 * 1024 * 1024

    try:
        max_total = int(
            os.getenv("MPIPS_DICOM_MAX_TOTAL_BYTES", str(100 * 1024 * 1024))
        )
        if max_total <= 0:
            max_total = 100 * 1024 * 1024
    except ValueError:
        max_total = 100 * 1024 * 1024

    return max_manifest, max_rad, max_gain, max_total


@router.post(
    "/radiographs/dicom",
    summary="Convert MHCS radiograph & gain NPZs to DICOM",
    description=(
        "Synchronously converts one radiograph NPZ and matching gain NPZ "
        "with an MHCS metadata manifest into a validated DICOM response."
    ),
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/dicom": {}},
            "description": "Validated DICOM file",
        },
        400: {"description": "Malformed multipart or invalid header"},
        401: {"description": "Invalid API key"},
        409: {"description": "Idempotency conflict or job in progress"},
        413: {"description": "Upload size limit exceeded"},
        422: {"description": "Validation error"},
        429: {"description": "Concurrency limit exceeded"},
        503: {"description": "Redis dependency unavailable"},
        504: {"description": "Processing timeout"},
    },
)
async def convert_radiograph_to_dicom(
    radiograph_npz: UploadFile = File(...),
    gain_npz: UploadFile = File(...),
    manifest: UploadFile = File(...),
    _api_key: str = Depends(require_api_key),
) -> FileResponse:
    tenant_id = "internal-beta"

    max_manifest, max_rad, max_gain, max_total = _get_upload_limits()

    # Private staging directory
    stage_dir = Path(tempfile.mkdtemp(prefix="mpips-dicom-stage-"))
    os.chmod(stage_dir, 0o700)

    cleanup_transferred = False

    try:
        total_accumulated_bytes = 0

        # 1. Read raw manifest bytes strictly
        raw_manifest_bytes = bytearray()
        while True:
            chunk = await manifest.read(1024 * 64)
            if not chunk:
                break
            raw_manifest_bytes.extend(chunk)
            total_accumulated_bytes += len(chunk)
            if (
                len(raw_manifest_bytes) > max_manifest
                or total_accumulated_bytes > max_total
            ):
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="UPLOAD_SIZE_EXCEEDED",
                )

        manifest_bytes = bytes(raw_manifest_bytes)

        # 2. Decode UTF-8 & parse JSON with Pydantic
        try:
            manifest_text = manifest_bytes.decode("utf-8")
            mhcs_manifest = MHCSManifest.model_validate_json(manifest_text)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="MANIFEST_SCHEMA_INVALID",
            ) from exc

        # 3. Stream radiograph NPZ
        rad_path = stage_dir / "radiograph.npz"
        rad_hasher = hashlib.sha256()
        rad_size = 0
        with rad_path.open("wb") as f_out:
            os.chmod(rad_path, 0o600)
            while True:
                chunk = await radiograph_npz.read(1024 * 1024)
                if not chunk:
                    break
                rad_size += len(chunk)
                total_accumulated_bytes += len(chunk)
                if rad_size > max_rad or total_accumulated_bytes > max_total:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="UPLOAD_SIZE_EXCEEDED",
                    )
                rad_hasher.update(chunk)
                f_out.write(chunk)

        rad_sha256 = rad_hasher.hexdigest().lower()

        # 4. Stream gain NPZ
        gain_path = stage_dir / "gain.npz"
        gain_hasher = hashlib.sha256()
        gain_size = 0
        with gain_path.open("wb") as f_out:
            os.chmod(gain_path, 0o600)
            while True:
                chunk = await gain_npz.read(1024 * 1024)
                if not chunk:
                    break
                gain_size += len(chunk)
                total_accumulated_bytes += len(chunk)
                if gain_size > max_gain or total_accumulated_bytes > max_total:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="UPLOAD_SIZE_EXCEEDED",
                    )
                gain_hasher.update(chunk)
                f_out.write(chunk)

        gain_sha256 = gain_hasher.hexdigest().lower()

        # 5. Verify file hashes and byte sizes against manifest
        expected_rad = mhcs_manifest.capture.radiograph
        if rad_size != expected_rad.byte_size or rad_sha256 != expected_rad.sha256:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="NPZ_VALIDATION_ERROR",
            )

        expected_gain = mhcs_manifest.capture.gain
        if gain_size != expected_gain.byte_size or gain_sha256 != expected_gain.sha256:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="NPZ_VALIDATION_ERROR",
            )

        # 6. Atomic Redis Idempotency Claim
        fp = compute_manifest_fingerprint(
            tenant_id,
            mhcs_manifest.manifest_version,
            str(mhcs_manifest.conversion_job_id),
            mhcs_manifest.model_dump_json(),
            rad_sha256,
            gain_sha256,
        )

        claim = IdempotencyService.claim_job(
            tenant_id, str(mhcs_manifest.conversion_job_id), fp
        )

        if claim.status == "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="IDEMPOTENCY_IN_PROGRESS",
            )

        if claim.status == "SUCCEEDED_DIFF":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="IDEMPOTENCY_CONFLICT",
            )

        output_dicom_path = stage_dir / "output.dcm"

        # 7. Bound process concurrency via process-wide CapacityLimiter
        limiter = get_concurrency_limiter()
        try:
            limiter.acquire_nowait()
        except (anyio.WouldBlock, RuntimeError):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="CONCURRENCY_LIMIT_EXCEEDED",
                headers={"Retry-After": "5"},
            )

        try:
            # Execute conversion in thread pool off the main event loop
            await anyio.to_thread.run_sync(
                run_isolated_dicom_conversion,
                rad_path,
                gain_path,
                mhcs_manifest,
                output_dicom_path,
            )

            if claim.lease_token:
                IdempotencyService.mark_success(
                    tenant_id,
                    str(mhcs_manifest.conversion_job_id),
                    claim.lease_token,
                    {"sop_instance_uid": mhcs_manifest.dicom.sop_instance_uid},
                )
        except Exception as exc:
            if claim.lease_token:
                err_detail = getattr(exc, "detail", "CONVERSION_FAILED")
                IdempotencyService.mark_failure(
                    tenant_id,
                    str(mhcs_manifest.conversion_job_id),
                    claim.lease_token,
                    str(err_detail),
                )
            raise
        finally:
            limiter.release()

        # 8. Response preparation & Cleanup Ownership Transfer
        safe_cid = re.sub(r"[^a-zA-Z0-9_-]", "_", mhcs_manifest.capture.capture_id)
        filename = f"{safe_cid}.dcm"

        headers = {
            "X-Correlation-ID": str(mhcs_manifest.correlation_id),
            "X-Conversion-Job-ID": str(mhcs_manifest.conversion_job_id),
        }

        cleanup_transferred = True
        return FileResponse(
            path=str(output_dicom_path),
            media_type="application/dicom",
            filename=filename,
            headers=headers,
            background=BackgroundTask(
                shutil.rmtree, str(stage_dir), ignore_errors=True
            ),
        )

    finally:
        if not cleanup_transferred and stage_dir.exists():
            shutil.rmtree(str(stage_dir), ignore_errors=True)
