"""FastAPI application helpers for installed MPIPS deployments."""

from fastapi import FastAPI

from app.main import app


def create_app() -> FastAPI:
    """Return the MPIPS FastAPI application singleton."""
    return app


__all__ = ["app", "create_app"]
