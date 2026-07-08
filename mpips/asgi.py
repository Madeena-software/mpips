"""ASGI entrypoint for `uvicorn mpips.asgi:app`."""

from app.main import app

__all__ = ["app"]
