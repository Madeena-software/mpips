from fastapi import FastAPI

import mpips
from mpips.api import app, create_app
from mpips.asgi import app as asgi_app
from mpips.engine import DAGExecutor, NODE_CATALOG, get_node_class, topological_sort


def test_public_package_exports_backend_app() -> None:
    assert isinstance(app, FastAPI)
    assert asgi_app is app
    assert create_app() is app
    assert mpips.app is app


def test_public_package_exports_engine_primitives() -> None:
    assert mpips.DAGExecutor is DAGExecutor
    assert mpips.topological_sort is topological_sort
    assert len(NODE_CATALOG) == 25
    assert get_node_class("input").__name__ == "InputNode"
    assert get_node_class("camera_calibration_warp").__name__ == (
        "CameraCalibrationWarpNode"
    )


def test_only_pure_opencv_nodes_are_browser_executable() -> None:
    browser_ids = {node.id for node in NODE_CATALOG if node.executable_in_browser}
    assert browser_ids == {
        "resize",
        "crop",
        "rotate",
        "flip",
        "grayscale",
        "brightness_contrast",
        "thresholding",
        "gamma_correction",
        "gaussian_blur",
        "median_blur",
        "canny",
        "sobel",
    }
