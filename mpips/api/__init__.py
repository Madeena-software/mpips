"""FastAPI application surface for MPIPS."""

from typing import Any


def create_app() -> Any:
    """Return the MPIPS FastAPI application singleton."""
    from mpips.api.application import app

    return app


def __getattr__(name: str) -> Any:
    if name == "app":
        from mpips.api.application import app

        return app
    raise AttributeError(f"module 'mpips.api' has no attribute {name!r}")


__all__ = ["app", "create_app"]
