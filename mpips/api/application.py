import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from mpips.api.middleware import RequestBodySizeLimitMiddleware
from mpips.api.routes.v1.dicom import router as dicom_router
from mpips.api.routes.v1.health import get_health_report

_DESCRIPTION = """\
MPIPS synchronously converts an MHCS radiograph NPZ, matching gain NPZ, and
JSON manifest into a validated DICOM response.
"""

_TAGS_METADATA = [
    {
        "name": "Radiographs",
        "description": "Convert MHCS radiograph uploads to validated DICOM.",
    },
    {
        "name": "Health",
        "description": "MPIPS service health.",
    },
]


def _validate_production_configuration() -> None:
    env_mode = os.getenv("MPIPS_ENVIRONMENT", "development").lower()
    if env_mode != "production":
        return

    # Redis URL check
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url or "replace-with" in redis_url:
        raise RuntimeError(
            "Production configuration invalid: REDIS_URL must be configured"
        )

    # Upload limits & numeric checks
    try:
        max_manifest = int(
            os.getenv("MPIPS_DICOM_MAX_MANIFEST_BYTES", str(100 * 1024 * 1024))
        )
        max_rad = int(
            os.getenv("MPIPS_DICOM_MAX_RADIOGRAPH_BYTES", str(100 * 1024 * 1024))
        )
        max_gain = int(os.getenv("MPIPS_DICOM_MAX_GAIN_BYTES", str(100 * 1024 * 1024)))
        max_total = int(
            os.getenv("MPIPS_DICOM_MAX_TOTAL_BYTES", str(300 * 1024 * 1024))
        )
        body_limit = int(
            os.getenv("MPIPS_MAX_HTTP_REQUEST_BODY_BYTES", str(310 * 1024 * 1024))
        )
        process_timeout = int(os.getenv("MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS", "300"))
        idempotency_ttl = int(os.getenv("MPIPS_DICOM_IDEMPOTENCY_TTL_SECONDS", "86400"))
        worker_cpu = int(os.getenv("MPIPS_DICOM_WORKER_CPU_SECONDS", "120"))
        worker_mem = int(
            os.getenv("MPIPS_DICOM_WORKER_MEMORY_BYTES", str(2 * 1024 * 1024 * 1024))
        )
        max_concurrency = int(os.getenv("MPIPS_DICOM_MAX_CONCURRENT_CONVERSIONS", "2"))
    except ValueError as exc:
        raise RuntimeError(
            f"Production configuration invalid: numeric parameter error: {exc}"
        ) from exc

    if (
        max_manifest <= 0
        or max_rad <= 0
        or max_gain <= 0
        or max_total <= 0
        or body_limit <= 0
        or process_timeout <= 0
        or idempotency_ttl <= 0
        or worker_cpu <= 0
        or worker_mem <= 0
        or max_concurrency <= 0
    ):
        raise RuntimeError(
            "Production configuration invalid: limit settings must be positive integers"
        )

    max_individual = max(max_manifest, max_rad, max_gain)
    if max_total < max_individual:
        raise RuntimeError(
            f"Production configuration invalid: max_total ({max_total}) < "
            f"largest individual limit ({max_individual})"
        )


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None, None]:
    _validate_production_configuration()
    yield


def health_check() -> dict[str, str]:
    return get_health_report()


def build_app() -> FastAPI:
    production = os.getenv("MPIPS_ENVIRONMENT", "development").lower() == "production"
    application = FastAPI(
        title="Madeena Python Image Processing Services",
        description=_DESCRIPTION,
        version=os.getenv("MPIPS_VERSION", "0.1.0"),
        contact={
            "name": "Madeena Engineering",
            "url": "https://madeena.com",
        },
        license_info={"name": "Proprietary"},
        openapi_tags=_TAGS_METADATA,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(RequestBodySizeLimitMiddleware)
    application.include_router(dicom_router, prefix="/v1")
    application.add_api_route(
        "/health",
        health_check,
        methods=["GET"],
        summary="Health check",
        tags=["Health"],
        operation_id="healthCheck",
    )
    return application


app = build_app()
