import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import Depends, FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_redoc_html,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.health import get_health_report
from app.api.v1.router import router as api_v1_router
from app.core.security import verify_token

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
| **Processing Nodes** | 24 built-in nodes across 6 \
categories |
| **DAG Execution** | Topological sort with cycle \
detection |
| **Storage** | S3-compatible object storage with \
tenant isolation |
| **Quality Assessment** | CII, Entropy, EME, BRISQUE \
metrics |
| **Security** | JWT/JWKS verification with scope \
enforcement |

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
        "description": (
            "Browse the catalog of available "
            "image-processing nodes, their "
            "parameters, and connection slots."
        ),
    },
    {
        "name": "Jobs",
        "description": (
            "Submit, monitor, and cancel "
            "asynchronous image-processing jobs. "
            "Jobs execute DAG pipelines on Celery "
            "workers and report progress via Redis."
        ),
    },
    {
        "name": "Health",
        "description": (
            "Service health checks and system "
            "information for monitoring "
            "and observability."
        ),
    },
]


_dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None, None]:
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

app.include_router(api_v1_router)

# Mount dashboard static files
if os.path.isdir(_dashboard_dir):
    app.mount(
        "/dashboard",
        StaticFiles(directory=_dashboard_dir, html=True),
        name="dashboard",
    )


# ── Custom Swagger UI with branding ──────────────────


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    """Serve branded Swagger UI."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=(f"{app.title} — API Documentation"),
        swagger_css_url=(
            "https://cdn.jsdelivr.net/npm/" "swagger-ui-dist@5/swagger-ui.css"
        ),
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
    """Serve branded ReDoc page."""
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=(f"{app.title} — API Reference"),
        redoc_favicon_url="",
    )


# ── Root & Health ────────────────────────────────────


@app.get(
    "/",
    summary="Service root",
    tags=["Health"],
    operation_id="getRoot",
)
def read_root() -> Dict[str, Any]:
    """Returns service identity and navigation links."""
    return {
        "service": "mpips",
        "title": app.title,
        "version": app.version,
        "status": "running",
        "links": {
            "docs": "/docs",
            "redoc": "/redoc",
            "dashboard": "/dashboard/",
            "openapi": "/openapi.json",
            "health": "/health",
            "nodes": "/v1/nodes",
        },
    }


@app.get(
    "/health",
    summary="Health check",
    description=(
        "Returns service health including Redis "
        "connectivity, Celery worker availability, "
        "and uptime metrics. This endpoint does not "
        "require authentication."
    ),
    tags=["Health"],
    operation_id="healthCheck",
)
def health_check() -> Dict[str, Any]:
    """Public health check endpoint."""
    return get_health_report()


@app.get(
    "/v1/secure-test",
    summary="Auth verification test",
    description=(
        "Test endpoint to verify that Bearer token "
        "authentication is configured correctly. "
        "Returns the decoded token claims."
    ),
    tags=["Health"],
    operation_id="secureTest",
)
def secure_test(
    payload: Dict[str, Any] = Depends(verify_token),
) -> Dict[str, Any]:
    """Validates authentication and returns token claims."""
    return {
        "message": "Authentication successful",
        "client_id": payload.get("sub"),
        "scopes": payload.get("scope"),
        "tenant_id": payload.get("tenant_id"),
    }
