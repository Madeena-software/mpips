import subprocess
import sys
import textwrap

from mpips.calibration import warp_image
from mpips.calibration.warp import warp_image as canonical_warp_image
from mpips.dag import (
    DAGExecutor,
)
from mpips.dag.executor import DAGExecutor as CanonicalDAGExecutor
from mpips.iqa.metrics import (
    calculate_all_metrics as canonical_calculate_all_metrics,
    calculate_brisque as canonical_calculate_brisque,
    calculate_cii as canonical_calculate_cii,
    calculate_eme as canonical_calculate_eme,
    calculate_entropy as canonical_calculate_entropy,
    calculate_local_contrast as canonical_calculate_local_contrast,
)
from mpips.iqa import (
    calculate_all_metrics,
    calculate_brisque,
    calculate_cii,
    calculate_eme,
    calculate_entropy,
    calculate_local_contrast,
)


def test_public_domain_symbols_reuse_canonical_implementations() -> None:
    assert warp_image is canonical_warp_image
    assert canonical_warp_image.__module__ == "mpips.calibration.warp"

    assert calculate_entropy is canonical_calculate_entropy
    assert calculate_eme is canonical_calculate_eme
    assert calculate_local_contrast is canonical_calculate_local_contrast
    assert calculate_cii is canonical_calculate_cii
    assert calculate_brisque is canonical_calculate_brisque
    assert calculate_all_metrics is canonical_calculate_all_metrics

    assert DAGExecutor is CanonicalDAGExecutor
    assert CanonicalDAGExecutor.__module__ == "mpips.dag.executor"


def test_engine_dag_compatibility_surface_is_retired() -> None:
    script = textwrap.dedent("""
        import importlib
        import sys

        import mpips.dag
        assert "mpips.engine" not in sys.modules
        import mpips.engine

        assert mpips.dag.__all__ == [
            "DAGExecutor",
            "NODE_CATALOG",
            "NODE_CLASSES",
            "get_node_class",
            "topological_sort",
        ]
        assert "mpips.engine" in sys.modules

        for name in (
            "DAGExecutor",
            "NODE_CATALOG",
            "NODE_CLASSES",
            "get_node_class",
            "topological_sort",
        ):
            assert not hasattr(mpips.engine, name)

        for module_name in (
            "mpips.engine.dag",
            "mpips.engine.catalog",
            "mpips.engine.registry",
            "mpips.engine.schemas",
            "mpips.engine.nodes",
            "mpips.engine.nodes.scientific",
        ):
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue
            raise AssertionError(f"retired module imported: {module_name}")
        """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_dag_executor_access_stays_engine_free() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.dag

        forbidden = {
            "mpips.engine",
            "mpips.api",
            "mpips.worker",
            "celery",
            "fastapi",
            "boto3",
        }
        assert not any(
            name in sys.modules
            or any(name.startswith(item + ".") for item in forbidden)
            for name in forbidden
        )

        from mpips.dag import DAGExecutor

        assert DAGExecutor.__module__ == "mpips.dag.executor"
        assert "mpips.dag.executor" in sys.modules
        assert "mpips.engine" not in sys.modules
        assert "mpips.engine.dag" not in sys.modules
        """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_scientific_boundaries_do_not_import_service_runtime() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips
        import mpips.calibration
        import mpips.dag
        import mpips.iqa

        forbidden = {"boto3", "celery", "fastapi", "httpx", "mpips.api", "mpips.worker"}
        loaded = forbidden.intersection(sys.modules)
        assert not loaded, sorted(loaded)
        assert "app" not in mpips.__dict__
        """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_calibration_import_is_optional_dependency_safe() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.calibration
        from mpips.calibration import warp_image

        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "matplotlib",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.pipelines",
            "mpips.worker",
            "mpips.workflows",
            "PIL",
            "torch",
        }
        loaded = sorted(
            name
            for name in sys.modules
            if name in forbidden
            or any(name.startswith(item + ".") for item in forbidden)
        )
        assert not loaded, loaded
        assert warp_image.__module__ == "mpips.calibration.warp"
        """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
