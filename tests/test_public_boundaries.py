import subprocess
import sys
import textwrap

from mpips.calibration import warp_image
from mpips.calibration.warp import warp_image as canonical_warp_image
from mpips.dag import (
    DAGExecutor,
    NODE_CATALOG,
    NODE_CLASSES,
    get_node_class,
    topological_sort,
)
from mpips.dag.executor import DAGExecutor as CanonicalDAGExecutor
from mpips.engine import (
    DAGExecutor as EngineDAGExecutor,
    NODE_CATALOG as EngineNodeCatalog,
    NODE_CLASSES as EngineNodeClasses,
    get_node_class as engine_get_node_class,
    topological_sort as engine_topological_sort,
)
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
    assert DAGExecutor is EngineDAGExecutor
    assert CanonicalDAGExecutor.__module__ == "mpips.dag.executor"
    assert NODE_CATALOG is EngineNodeCatalog
    assert NODE_CLASSES is EngineNodeClasses
    assert get_node_class is engine_get_node_class
    assert topological_sort is engine_topological_sort


def test_existing_engine_imports_remain_compatible() -> None:
    assert EngineDAGExecutor is DAGExecutor
    assert EngineNodeCatalog is NODE_CATALOG
    assert EngineNodeClasses is NODE_CLASSES
    assert engine_get_node_class is get_node_class
    assert engine_topological_sort is topological_sort


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
