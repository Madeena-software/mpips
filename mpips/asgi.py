"""ASGI entrypoint for `uvicorn mpips.asgi:app`."""

from mpips.api import app

__all__ = ["app"]
