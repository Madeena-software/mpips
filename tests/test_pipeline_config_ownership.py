"""Ownership and compatibility contracts for pipeline configuration."""

# Legacy modules are intentionally outside the typed pipeline boundary.
# mypy: disable-error-code=attr-defined

import hashlib
import json
import subprocess
import sys
import textwrap


def _json_sha256(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def test_pipeline_config_has_canonical_location() -> None:
    from mpips.pipelines.config import ImagerPipelineConfig

    assert ImagerPipelineConfig.__module__ == "mpips.pipelines.config"


def test_config_class_and_default_factory_identity_is_preserved() -> None:
    from mpips.engine.imager_pipeline.config import (
        ImagerPipelineConfig as LegacyConfig,
        get_default_config as LegacyDefaultConfig,
    )
    from mpips.pipelines.config import (
        ImagerPipelineConfig as CanonicalConfig,
        get_default_config as CanonicalDefaultConfig,
    )
    from mpips.workflows.imager_pipeline import ImagerPipelineConfig as WorkflowConfig
    from mpips.workflows.imager_pipeline.models import (
        ImagerPipelineConfig as WorkflowModelConfig,
    )

    assert CanonicalConfig is LegacyConfig
    assert CanonicalConfig is WorkflowConfig
    assert CanonicalConfig is WorkflowModelConfig
    assert CanonicalDefaultConfig is LegacyDefaultConfig


def test_config_enum_identity_is_preserved() -> None:
    from mpips.engine.imager_pipeline.config import (
        ContrastMode as LegacyContrastMode,
        MedianFilterType as LegacyMedianFilterType,
        ThresholdMethod as LegacyThresholdMethod,
        WaveletMethod as LegacyWaveletMethod,
        WaveletMode as LegacyWaveletMode,
    )
    from mpips.pipelines.config import (
        ContrastMode,
        MedianFilterType,
        ThresholdMethod,
        WaveletMethod,
        WaveletMode,
    )

    assert ContrastMode is LegacyContrastMode
    assert ThresholdMethod is LegacyThresholdMethod
    assert WaveletMode is LegacyWaveletMode
    assert WaveletMethod is LegacyWaveletMethod
    assert MedianFilterType is LegacyMedianFilterType


def test_default_and_stretch_serialization_matches_accepted_baseline() -> None:
    from mpips.pipelines.config import ImagerPipelineConfig

    default = ImagerPipelineConfig()
    stretch = ImagerPipelineConfig(contrast_mode="stretch")

    assert _json_sha256(default.to_dict()) == (
        "a3aae23c0fe890fa8fcc634f91f4df61b2a40d277d2a2419e06198560078d2e4"
    )
    assert _json_sha256(default.to_legacy_engine_dict()) == (
        "0ecb09d739a2f9a896c084ab9346043b17d9b4538e9df6d12fcaa980826d2901"
    )
    assert _json_sha256(stretch.to_dict()) == (
        "53751ed3e1573db4df873dae1e3a5349a485b0b04edf3635b2448ccad9001da6"
    )
    assert _json_sha256(stretch.to_legacy_engine_dict()) == (
        "4eb736734e5239c71fb7a9c539f8b41298319a38480764072c113f22b301325a"
    )


def test_pipeline_config_import_is_runtime_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.pipelines import ImagerPipelineConfig
        from mpips.pipelines.config import ContrastMode

        assert ImagerPipelineConfig.__module__ == "mpips.pipelines.config"
        assert ContrastMode.__module__ == "mpips.pipelines.config"
        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine.imager_pipeline.complete_pipeline",
            "mpips.worker",
            "mpips.workflows",
        }
        assert forbidden.isdisjoint(sys.modules)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
