import importlib
import inspect
import subprocess
import sys
import textwrap

import numpy as np
import pytest

from mpips.iqa.metrics import (
    BrisqueCalculator,
    ContrastImprovementIndexCalculator,
    EnhancementMeasureCalculator,
    EntropyCalculator,
    calculate_all_metrics,
    calculate_brisque,
    calculate_cii,
    calculate_eme,
    calculate_entropy,
    calculate_local_contrast,
)


def _constant_uint8() -> np.ndarray:
    return np.full((8, 8), 7, dtype=np.uint8)


def _binary_uint8() -> np.ndarray:
    image = np.zeros((8, 8), dtype=np.uint8)
    image[:, 4:] = 255
    return image


def _uint16_image() -> np.ndarray:
    return np.array([0, 1000, 2000, 65535] * 16, dtype=np.uint16).reshape(8, 8)


def _gray_gradient() -> np.ndarray:
    return np.arange(256, dtype=np.uint8).reshape(16, 16)


def _bgr_image() -> np.ndarray:
    gray = _gray_gradient()
    return np.stack((gray, np.flipud(gray), np.fliplr(gray)), axis=2)


def test_historical_entropy_values() -> None:
    assert calculate_entropy(_constant_uint8()) == 0.0
    assert calculate_entropy(_binary_uint8()) == 1.0
    assert calculate_entropy(_uint16_image()) == 2.0
    assert calculate_entropy(_bgr_image()) == pytest.approx(
        5.519881227620555, abs=1e-12
    )


def test_historical_eme_values() -> None:
    single_block = np.arange(1, 65, dtype=np.uint8).reshape(8, 8)
    multi_block = np.arange(1, 257, dtype=np.uint16).reshape(16, 16)
    zero_minimum = np.zeros((8, 8), dtype=np.uint8)
    zero_minimum[0, 0] = 255
    small = np.arange(1, 16, dtype=np.uint8).reshape(3, 5)
    partial_grid = np.arange(1, 17 * 19 + 1, dtype=np.uint16).reshape(17, 19)

    assert calculate_eme(single_block) == pytest.approx(8.317766166719343, abs=1e-12)
    assert calculate_eme(multi_block) == pytest.approx(4.360555144910095, abs=1e-12)
    assert calculate_eme(zero_minimum) == pytest.approx(29.50320783426922, abs=1e-12)
    assert calculate_eme(small) == 0.0
    assert calculate_eme(partial_grid) == pytest.approx(4.515461103188226, abs=1e-12)
    assert calculate_eme(single_block, block_size=4) == pytest.approx(
        3.167152336005949, abs=1e-12
    )


def test_historical_local_contrast_values() -> None:
    small = np.arange(15, dtype=np.uint8).reshape(3, 5)
    exact_block = np.arange(64, dtype=np.uint8).reshape(8, 8)
    multi_block = np.arange(256, dtype=np.uint16).reshape(16, 16)
    uint16_image = (np.arange(256, dtype=np.uint16).reshape(16, 16) * 257).astype(
        np.uint16
    )

    assert calculate_local_contrast(small) == pytest.approx(
        4.320493798938574, abs=1e-12
    )
    assert calculate_local_contrast(exact_block) == pytest.approx(
        18.472953201911167, abs=1e-12
    )
    assert calculate_local_contrast(multi_block) == pytest.approx(
        36.732138516563396, abs=1e-12
    )
    assert calculate_local_contrast(uint16_image) == pytest.approx(
        9440.159598756793, abs=1e-12
    )


def test_historical_cii_values() -> None:
    original = np.arange(256, dtype=np.float32).reshape(16, 16)
    processed = original * 2.0 + 5.0

    assert calculate_cii(processed, original) == 2.0
    assert calculate_cii(original, original) == 1.0
    assert (
        calculate_cii(np.arange(64, dtype=np.uint8).reshape(8, 8), _constant_uint8())
        == 1.0
    )


def test_historical_brisque_proxy_values() -> None:
    assert calculate_brisque(_constant_uint8()) == 70.0
    assert calculate_brisque(_gray_gradient()) == pytest.approx(
        87.5396384066457, abs=1e-12
    )
    uint16_image = (np.arange(256, dtype=np.uint16).reshape(16, 16) * 257).astype(
        np.uint16
    )
    assert calculate_brisque(uint16_image) == pytest.approx(87.5396384066457, abs=1e-12)
    assert calculate_brisque(_bgr_image()) == pytest.approx(
        80.70089247123602, abs=1e-12
    )


def test_historical_calculator_classes_remain_intact() -> None:
    single_block = np.arange(1, 65, dtype=np.uint8).reshape(8, 8)
    original = np.arange(256, dtype=np.float32).reshape(16, 16)
    processed = original * 2.0 + 5.0

    assert EntropyCalculator().calculate(_constant_uint8()) == 0.0
    assert EnhancementMeasureCalculator().calculate(single_block) == pytest.approx(
        8.317766166719343, abs=1e-12
    )
    assert ContrastImprovementIndexCalculator().calculate_local_contrast(
        np.arange(64, dtype=np.uint8).reshape(8, 8)
    ) == pytest.approx(18.472953201911167, abs=1e-12)
    assert ContrastImprovementIndexCalculator().calculate(processed, original) == 2.0
    assert BrisqueCalculator().calculate(_gray_gradient()) == pytest.approx(
        87.5396384066457, abs=1e-12
    )


def test_historical_all_metrics_order_and_rounding() -> None:
    result = calculate_all_metrics(_gray_gradient(), np.flipud(_gray_gradient()))

    assert list(result) == ["cii", "entropy", "eme", "brisque"]
    assert result == {
        "cii": 1.0,
        "entropy": 8.0,
        "eme": 9.0201,
        "brisque": 87.5396,
    }


def test_public_facade_resolves_only_canonical_metrics() -> None:
    facade = importlib.import_module("mpips.iqa")
    metrics = importlib.import_module("mpips.iqa.metrics")

    assert facade.__all__[:6] == [
        "calculate_entropy",
        "calculate_eme",
        "calculate_local_contrast",
        "calculate_cii",
        "calculate_brisque",
        "calculate_all_metrics",
    ]
    assert facade.__all__[6:] == [
        "StructuralSafetyMetrics",
        "analyze_structural_preservation",
    ]
    for name in facade.__all__[:6]:
        assert getattr(facade, name) is getattr(metrics, name)
        assert getattr(facade, name).__module__ == "mpips.iqa.metrics"

    safety = importlib.import_module("mpips.iqa.safety")
    for name in facade.__all__[6:]:
        assert getattr(facade, name) is getattr(safety, name)
        assert getattr(facade, name).__module__ == "mpips.iqa.safety"


def test_iqa_nodes_resolve_canonical_metrics() -> None:
    metrics = importlib.import_module("mpips.iqa.metrics")
    nodes = importlib.import_module("mpips.dag.nodes.iqa")

    for name in (
        "calculate_entropy",
        "calculate_eme",
        "calculate_cii",
        "calculate_brisque",
    ):
        assert getattr(nodes, name) is getattr(metrics, name)


def test_iqa_node_outputs_preserve_rounding_and_reference_fallback() -> None:
    from mpips.dag.nodes.iqa import (
        BrisqueNode,
        ContrastImprovementIndexNode,
        EnhancementMeasureNode,
        EntropyNode,
    )

    image = _gray_gradient()
    reference = np.flipud(image)

    assert EntropyNode().execute({"input_image": image}, {}) == {"entropy_score": 8.0}
    assert EnhancementMeasureNode().execute({"input_image": image}, {}) == {
        "eme_score": 9.0201
    }
    assert BrisqueNode().execute({"input_image": image}, {}) == {
        "brisque_score": 87.5396
    }
    assert ContrastImprovementIndexNode().execute(
        {"input_image": image, "reference_image": reference}, {}
    ) == {"cii_score": 1.0}
    assert ContrastImprovementIndexNode().execute({"input_image": image}, {}) == {
        "cii_score": 1.0
    }


def test_iqa_node_error_messages_remain_unchanged() -> None:
    from mpips.dag.nodes.iqa import (
        BrisqueNode,
        ContrastImprovementIndexNode,
        EnhancementMeasureNode,
        EntropyNode,
    )

    cases = [
        (EntropyNode(), "EntropyNode requires 'input_image' input."),
        (
            EnhancementMeasureNode(),
            "EnhancementMeasureNode requires 'input_image' input.",
        ),
        (BrisqueNode(), "BrisqueNode requires 'input_image' input."),
        (
            ContrastImprovementIndexNode(),
            "ContrastImprovementIndexNode requires 'input_image' input.",
        ),
    ]
    for node, message in cases:
        with pytest.raises(ValueError, match=f"^{message}$"):
            node.execute({}, {})


def test_dag_quality_assessment_resolves_canonical_metrics() -> None:
    from mpips.dag.executor import DAGExecutor

    source = inspect.getsource(DAGExecutor.execute)
    assert "from mpips.iqa import calculate_all_metrics" in source
    assert "mpips.engine.iqa" not in source


def test_engine_iqa_is_retired() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("mpips.engine.iqa")


def test_import_mpips_iqa_is_lightweight_and_engine_free() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.iqa

        forbidden = {
            "mpips.engine",
            "mpips.workflows",
            "mpips.api",
            "mpips.worker",
            "fastapi",
            "celery",
            "boto3",
            "torch",
            "matplotlib",
            "PIL",
            "cv2",
            "numpy",
        }
        loaded = sorted(
            name
            for name in sys.modules
            if name in forbidden
            or any(name.startswith(item + ".") for item in forbidden)
        )
        assert not loaded, loaded
        assert "mpips.iqa.metrics" not in sys.modules
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_explicit_metric_access_loads_canonical_without_engine_iqa() -> None:
    script = textwrap.dedent("""
        import sys

        import mpips.iqa

        assert "mpips.iqa.metrics" not in sys.modules
        from mpips.iqa import calculate_entropy

        assert calculate_entropy.__module__ == "mpips.iqa.metrics"
        assert "mpips.iqa.metrics" in sys.modules
        assert "mpips.engine.iqa" not in sys.modules
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
