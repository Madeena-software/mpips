from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
import os

from fastapi import Depends, FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_redoc_html,
)
from fastapi.responses import HTMLResponse

from mpips.api.middleware import RequestBodySizeLimitMiddleware
from mpips.api.routes.v1.health import get_health_report
from mpips.api.routes.v1.router import router as api_v1_router
from mpips.api.security import verify_token

_DESCRIPTION = """\
**MPIPS** is the scientific image-processing execution
microservice of the Madeena Image Platform.

It accepts Directed Acyclic Graph (DAG) pipelines of
image-processing operations, executes them
asynchronously on Celery workers, and streams results
back to the control plane via signed webhooks.

## Key Capabilities

| Area | Details |
|------|---------|
| **Processing Nodes** | 25 built-in nodes across 6 categories |
| **DAG Execution** | Topological sort with cycle detection |
| **Storage** | S3-compatible object storage with tenant isolation |
| **Quality Assessment** | CII, Entropy, EME, BRISQUE metrics |
| **Security** | JWT/JWKS verification with scope enforcement |

## Authentication

All API endpoints require a **Bearer JWT** token in
the `Authorization` header. In development mode,
set `DEV_AUTH_BYPASS=true` and use the configured
static token.

---

*Built with FastAPI · Celery · OpenCV · Redis*
"""

_TAGS_METADATA = [
    {
        "name": "Nodes",
        "description": "Browse the catalog of available image-processing nodes.",
    },
    {
        "name": "Jobs",
        "description": "Submit, monitor, and cancel DAG jobs.",
    },
    {
        "name": "Health",
        "description": "Service health checks and observability.",
    },
]


def _validate_production_configuration() -> None:
    env_mode = os.getenv("MPIPS_ENVIRONMENT", "development").lower()
    if env_mode != "production":
        return

    # 1. DEV_AUTH_BYPASS must be false in production
    if os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true":
        raise RuntimeError(
            "Production configuration invalid: DEV_AUTH_BYPASS cannot be true"
        )

    # 2. HMAC Secret check
    hmac_secret = os.getenv("MPIPS_MANIFEST_HMAC_SECRET", "").strip()
    if not hmac_secret or "replace-with" in hmac_secret or len(hmac_secret) < 32:
        raise RuntimeError(
            "Production configuration invalid: "
            "MPIPS_MANIFEST_HMAC_SECRET must be set and >= 32 chars"
        )

    # 3. IDP Configuration checks
    jwks_url = os.getenv("MADEENA_IDP_JWKS_URL", "").strip()
    issuer = os.getenv("MADEENA_IDP_ISSUER", "").strip()
    audience = os.getenv("MADEENA_IDP_AUDIENCE", "").strip()
    if not jwks_url or "replace-with" in jwks_url or not jwks_url.startswith("http"):
        raise RuntimeError(
            "Production configuration invalid: MADEENA_IDP_JWKS_URL must be a valid URL"
        )
    if not issuer or "replace-with" in issuer:
        raise RuntimeError(
            "Production configuration invalid: MADEENA_IDP_ISSUER must be set"
        )
    if not audience or "replace-with" in audience:
        raise RuntimeError(
            "Production configuration invalid: MADEENA_IDP_AUDIENCE must be set"
        )

    # 4. Redis URL check
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url or "replace-with" in redis_url:
        raise RuntimeError(
            "Production configuration invalid: REDIS_URL must be configured"
        )

    # 5. Upload limits & numeric checks
    try:
        max_manifest = int(
            os.getenv("MPIPS_DICOM_MAX_MANIFEST_BYTES", str(1 * 1024 * 1024))
        )
        max_rad = int(
            os.getenv("MPIPS_DICOM_MAX_RADIOGRAPH_BYTES", str(50 * 1024 * 1024))
        )
        max_gain = int(os.getenv("MPIPS_DICOM_MAX_GAIN_BYTES", str(50 * 1024 * 1024)))
        max_total = int(
            os.getenv("MPIPS_DICOM_MAX_TOTAL_BYTES", str(100 * 1024 * 1024))
        )
        body_limit = int(
            os.getenv("MPIPS_MAX_HTTP_REQUEST_BODY_BYTES", str(105 * 1024 * 1024))
        )
        process_timeout = int(os.getenv("MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS", "300"))
        idempotency_ttl = int(os.getenv("MPIPS_DICOM_IDEMPOTENCY_TTL_SECONDS", "86400"))
        worker_cpu = int(os.getenv("MPIPS_DICOM_WORKER_CPU_SECONDS", "120"))
        worker_mem = int(
            os.getenv("MPIPS_DICOM_WORKER_MEMORY_BYTES", str(2 * 1024 * 1024 * 1024))
        )
        max_concurrency = int(os.getenv("MPIPS_DICOM_MAX_CONCURRENT_CONVERSIONS", "4"))
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


app = FastAPI(
    title="Madeena Python Image Processing Services",
    description=_DESCRIPTION,
    version=os.getenv("MPIPS_VERSION", "0.1.0"),
    contact={
        "name": "Madeena Engineering",
        "url": "https://madeena.com",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_tags=_TAGS_METADATA,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(RequestBodySizeLimitMiddleware)
app.include_router(api_v1_router)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=(f"{app.title} — API Documentation"),
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="",
        swagger_ui_parameters={
            "docExpansion": "list",
            "defaultModelsExpandDepth": 2,
            "persistAuthorization": True,
            "tryItOutEnabled": True,
            "filter": True,
            "syntaxHighlight.theme": "monokai",
        },
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=(f"{app.title} — API Reference"),
        redoc_favicon_url="",
    )


@app.get(
    "/",
    summary="Service root",
    tags=["Health"],
    operation_id="getRoot",
)
def read_root() -> Dict[str, Any]:
    return {
        "service": "mpips",
        "title": app.title,
        "version": app.version,
        "status": "running",
        "links": {
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "nodes": "/v1/nodes",
        },
    }


@app.get(
    "/health",
    summary="Health check",
    tags=["Health"],
    operation_id="healthCheck",
)
def health_check() -> Dict[str, Any]:
    return get_health_report()


@app.get(
    "/v1/secure-test",
    summary="Auth verification test",
    tags=["Health"],
    operation_id="secureTest",
)
def secure_test(
    payload: Dict[str, Any] = Depends(verify_token),
) -> Dict[str, Any]:
    return {
        "message": "Authentication successful",
        "client_id": payload.get("sub"),
        "scopes": payload.get("scope"),
        "tenant_id": payload.get("tenant_id"),
    }
