from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from mpips.api.application import app

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _route_table(application: Any) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in application.routes
        for method in getattr(route, "methods", set())
    }


def test_dicom_and_dag_routes_are_registered() -> None:
    routes = _route_table(app)

    assert {
        ("POST", "/v1/radiographs/dicom"),
        ("GET", "/health"),
        ("GET", "/v1/nodes"),
        ("POST", "/v1/jobs"),
        ("GET", "/v1/jobs"),
        ("GET", "/v1/jobs/{id}"),
        ("DELETE", "/v1/jobs/{id}"),
    } <= routes
    assert {("GET", "/"), ("GET", "/v1/secure-test")}.isdisjoint(routes)


def test_health_describes_only_mpips() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "mpips",
        "status": "healthy",
        "version": os.getenv("MPIPS_VERSION", "0.1.0"),
        "environment": os.getenv("MPIPS_ENVIRONMENT", "development"),
    }


def test_production_route_table_has_no_documentation_routes() -> None:
    route_script = """
import json
from mpips.api.application import app

routes = sorted(
    (method, route.path)
    for route in app.routes
    for method in getattr(route, "methods", set())
)
print(json.dumps(routes))
"""
    environment = os.environ.copy()
    environment["MPIPS_ENVIRONMENT"] = "production"
    result = subprocess.run(
        [sys.executable, "-c", route_script],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    routes = {tuple(route) for route in json.loads(result.stdout)}

    assert {("POST", "/v1/radiographs/dicom"), ("GET", "/health")} <= routes
    assert not {path for _, path in routes} & {
        "/docs",
        "/redoc",
        "/openapi.json",
    }
