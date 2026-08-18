import subprocess
import sys
import textwrap

from mpips.calibration import warp_image
from mpips.dag import (
    DAGExecutor,
    NODE_CATALOG,
    NODE_CLASSES,
    get_node_class,
    topological_sort,
)
from mpips.engine import (
    DAGExecutor as EngineDAGExecutor,
    NODE_CATALOG as EngineNodeCatalog,
    NODE_CLASSES as EngineNodeClasses,
    get_node_class as engine_get_node_class,
    topological_sort as engine_topological_sort,
)
from mpips.engine.calibration import warp_image as engine_warp_image
from mpips.engine.iqa import (
    calculate_all_metrics as engine_calculate_all_metrics,
    calculate_brisque as engine_calculate_brisque,
    calculate_cii as engine_calculate_cii,
    calculate_eme as engine_calculate_eme,
    calculate_entropy as engine_calculate_entropy,
    calculate_local_contrast as engine_calculate_local_contrast,
)
from mpips.iqa import (
    calculate_all_metrics,
    calculate_brisque,
    calculate_cii,
    calculate_eme,
    calculate_entropy,
    calculate_local_contrast,
)


def test_public_domain_symbols_reuse_engine_implementations() -> None:
    assert warp_image is engine_warp_image

    assert calculate_entropy is engine_calculate_entropy
    assert calculate_eme is engine_calculate_eme
    assert calculate_local_contrast is engine_calculate_local_contrast
    assert calculate_cii is engine_calculate_cii
    assert calculate_brisque is engine_calculate_brisque
    assert calculate_all_metrics is engine_calculate_all_metrics

    assert DAGExecutor is EngineDAGExecutor
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
    assert engine_warp_image is warp_image
    assert engine_calculate_all_metrics is calculate_all_metrics


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
