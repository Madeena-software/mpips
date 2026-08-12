from __future__ import annotations

import os
from typing import Awaitable, Callable, Dict, Any
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


def get_max_request_body_bytes() -> int:
    try:
        limit = int(
            os.getenv("MPIPS_MAX_HTTP_REQUEST_BODY_BYTES", str(310 * 1024 * 1024))
        )
        if limit <= 0:
            return 310 * 1024 * 1024
        return limit
    except ValueError:
        return 310 * 1024 * 1024


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces cumulative HTTP request body size limits before FastAPI body parsing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length_str = request.headers.get("content-length")
        max_bytes = get_max_request_body_bytes()

        if content_length_str and content_length_str.isdigit():
            if int(content_length_str) > max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "UPLOAD_SIZE_EXCEEDED"},
                )

        accumulated = 0
        original_receive = request._receive

        async def custom_receive() -> Dict[str, Any]:
            nonlocal accumulated
            message = await original_receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                accumulated += len(body)
                if accumulated > max_bytes:
                    raise BodySizeLimitExceededError()
            return dict(message)

        request._receive = custom_receive

        try:
            res: Response = await call_next(request)
            return res
        except BodySizeLimitExceededError:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "UPLOAD_SIZE_EXCEEDED"},
            )


class BodySizeLimitExceededError(Exception):
    """Raised when streaming request body exceeds configured maximum bytes."""
