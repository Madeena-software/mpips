"""FastAPI application for the MPIPS staging update server."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from mpips.update_server.auth import (
    AuthenticationError,
    AuthorizationError,
    ClientAuthenticator,
)
from mpips.update_server.minio_adapter import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    MinIOArtifactStore,
    StorageUnavailableError,
    UpdateStorageError,
)
from mpips.update_server.registry import (
    ChannelSequenceConflictError,
    ReleaseNotFoundError,
    ReleaseRegistry,
    ReleaseUnauthorizedError,
    ReleaseValidationError,
)
from mpips.update_server.release_metadata import (
    RELEASE_ID_RE,
    SUPPORTED_CHANNEL,
    SUPPORTED_PLATFORM,
    validate_platform_compatibility,
)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "schema_version": 1,
            "error": {
                "code": code,
                "message": message,
            },
        },
        headers={"Cache-Control": "no-store"},
    )


def _load_configured_public_key() -> bytes:
    pem_env = os.getenv("MPIPS_UPDATE_PUBLIC_KEY_PEM", "").strip()
    if pem_env:
        return pem_env.encode("utf-8")
    key_path = os.getenv("MPIPS_UPDATE_PUBLIC_KEY_PATH", "").strip()
    if key_path:
        return Path(key_path).read_bytes()
    return b""


def create_update_server_app(
    *,
    registry: ReleaseRegistry | None = None,
    authenticator: ClientAuthenticator | None = None,
) -> FastAPI:
    """Build an isolated FastAPI app for MPIPS staging update discovery & download."""
    active_auth = authenticator if authenticator is not None else ClientAuthenticator()
    active_registry = registry

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        nonlocal active_registry
        if active_registry is None:
            pub_key = _load_configured_public_key()
            if pub_key:
                state_dir_raw = os.getenv("MPIPS_UPDATE_STATE_DIR", "").strip()
                state_dir = (
                    Path(state_dir_raw)
                    if state_dir_raw
                    else Path(tempfile.mkdtemp(prefix="mpips-update-state-"))
                )
                store = MinIOArtifactStore()
                active_registry = ReleaseRegistry(
                    state_dir=state_dir,
                    public_key_pem=pub_key,
                    artifact_store=store,
                )
        yield

    application = FastAPI(
        title="MPIPS Update Server",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def _no_store_headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def _require_auth(
        authorization: str | None,
        api_key: str | None,
    ) -> JSONResponse | None:
        try:
            active_auth.authenticate_staging_reader(
                authorization_header=authorization,
                api_key_header=api_key,
            )
            return None
        except AuthenticationError as exc:
            return _error_response(401, "unauthorized", str(exc))
        except AuthorizationError as exc:
            return _error_response(403, "forbidden", str(exc))

    def _resolve_platform(
        query_platform: str | None,
        header_platform: str | None,
    ) -> str:
        target = (query_platform or header_platform or SUPPORTED_PLATFORM).strip()
        validate_platform_compatibility(target)
        return target

    @application.get("/mpips/staging/health")
    def staging_health() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "service": "mpips-update-server",
                "environment": "staging",
            },
            headers={"Cache-Control": "no-store"},
        )

    @application.get("/mpips/staging/latest.json")
    def staging_latest_release(
        platform: str | None = Query(default=None),
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_mpips_api_key: str | None = Header(default=None, alias="X-MPIPS-API-Key"),
        x_client_platform: str | None = Header(
            default=None, alias="X-MPIPS-Client-Platform"
        ),
    ) -> JSONResponse:
        auth_err = _require_auth(authorization, x_mpips_api_key)
        if auth_err is not None:
            return auth_err

        try:
            resolved_platform = _resolve_platform(platform, x_client_platform)
        except ValueError:
            return _error_response(
                422,
                "incompatible_platform",
                "Requested platform is not supported by this release channel",
            )

        if active_registry is None:
            return _error_response(
                503,
                "service_not_configured",
                "Release registry is not initialized",
            )

        try:
            manifest = active_registry.get_latest_release(
                channel=SUPPORTED_CHANNEL,
                platform_name=resolved_platform,
            )
            return JSONResponse(
                status_code=200,
                content=manifest,
                headers={"Cache-Control": "no-store"},
            )
        except ReleaseNotFoundError:
            return _error_response(
                404,
                "artifact_not_found",
                "Promoted release artifact is not available",
            )
        except ReleaseUnauthorizedError:
            return _error_response(
                403,
                "release_unauthorized",
                "Release is not authorized for staging distribution",
            )
        except (ReleaseValidationError, ArtifactIntegrityError):
            return _error_response(
                422,
                "invalid_release",
                "Release metadata or artifact verification failed",
            )
        except ArtifactNotFoundError:
            return _error_response(
                404,
                "artifact_not_found",
                "Release artifact object is missing in storage",
            )
        except (StorageUnavailableError, UpdateStorageError):
            return _error_response(
                503,
                "storage_unavailable",
                "Artifact storage is temporarily unavailable",
            )

    @application.get("/mpips/staging/releases/{release_id}/download")
    def staging_release_download(
        release_id: str,
        platform: str | None = Query(default=None),
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_mpips_api_key: str | None = Header(default=None, alias="X-MPIPS-API-Key"),
        x_client_platform: str | None = Header(
            default=None, alias="X-MPIPS-Client-Platform"
        ),
    ) -> JSONResponse:
        auth_err = _require_auth(authorization, x_mpips_api_key)
        if auth_err is not None:
            return auth_err

        if not RELEASE_ID_RE.fullmatch(release_id):
            return _error_response(
                400,
                "invalid_release_id",
                "Malformed release identifier",
            )

        try:
            resolved_platform = _resolve_platform(platform, x_client_platform)
        except ValueError:
            return _error_response(
                422,
                "incompatible_platform",
                "Requested platform is not compatible with this release",
            )

        if active_registry is None:
            return _error_response(
                503,
                "service_not_configured",
                "Release registry is not initialized",
            )

        try:
            record = active_registry.get_authorized_release_for_download(
                release_id,
                channel=SUPPORTED_CHANNEL,
                platform_name=resolved_platform,
            )
            presigned = active_registry.artifact_store.generate_presigned_download(
                release_id=record.release_id,
                expected_size_bytes=record.size_bytes,
                channel=record.channel,
                platform_name=record.platform,
            )
            return JSONResponse(
                status_code=200,
                content={
                    "release_id": presigned.release_id,
                    "download_url": presigned.download_url,
                    "expires_at": presigned.expires_at,
                },
                headers={"Cache-Control": "no-store"},
            )
        except ReleaseNotFoundError:
            return _error_response(
                404,
                "release_not_found",
                "Requested release is not registered",
            )
        except ReleaseUnauthorizedError:
            return _error_response(
                403,
                "release_unauthorized",
                "Requested release is not authorized for download",
            )
        except ChannelSequenceConflictError:
            return _error_response(
                409,
                "release_superseded",
                "Requested release has been superseded by a newer sequence",
            )
        except (ReleaseValidationError, ArtifactIntegrityError):
            return _error_response(
                422,
                "invalid_release",
                "Release integrity or signature verification failed",
            )
        except ArtifactNotFoundError:
            return _error_response(
                404,
                "artifact_not_found",
                "Release binary is missing in artifact storage",
            )
        except (StorageUnavailableError, UpdateStorageError):
            return _error_response(
                503,
                "storage_unavailable",
                "Artifact storage is temporarily unavailable",
            )

    return application


app = create_update_server_app()
