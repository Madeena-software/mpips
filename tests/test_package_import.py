from fastapi import FastAPI

import mpips
from app.main import app as legacy_app
from mpips.api import app, create_app
from mpips.asgi import app as asgi_app
from mpips.engine import DAGExecutor, NODE_CATALOG, get_node_class, topological_sort


def test_public_package_exports_backend_app() -> None:
    assert isinstance(app, FastAPI)
    assert app is legacy_app
    assert asgi_app is legacy_app
    assert create_app() is legacy_app
    assert mpips.app is legacy_app


def test_public_package_exports_engine_primitives() -> None:
    assert mpips.DAGExecutor is DAGExecutor
    assert mpips.topological_sort is topological_sort
    assert len(NODE_CATALOG) == 24
    assert get_node_class("input").__name__ == "InputNode"
