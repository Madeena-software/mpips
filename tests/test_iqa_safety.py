import numpy as np
import pytest

from mpips.iqa import StructuralSafetyMetrics, analyze_structural_preservation


def _reference() -> np.ndarray:
    image = np.zeros((96, 96), dtype=np.uint16)
    image[20:76, 24:72] = 42000
    image[32:64, 32:64] = 56000
    image[44:52, 72:88] = 18000
    return image


def _candidate_cases() -> dict[str, np.ndarray]:
    reference = _reference()
    return {
        "identity": reference.copy(),
        "brightness_contrast": np.clip(
            reference.astype(np.float32) * 0.8 + 5000, 0, 65535
        ).astype(np.uint16),
        "inversion": np.iinfo(np.uint16).max - reference,
        "smoothing": np.asarray(
            __import__("cv2").GaussianBlur(reference, (5, 5), 0), dtype=np.uint16
        ),
        "local_deletion": reference.copy(),
        "large_deletion": np.zeros_like(reference),
    }


def test_structural_metrics_are_typed_and_finite_for_uint16_and_float() -> None:
    reference = _reference()

    result = analyze_structural_preservation(reference, reference)
    float_result = analyze_structural_preservation(
        reference.astype(np.float32) / 65535.0,
        reference.astype(np.float32) / 65535.0,
    )

    assert isinstance(result, StructuralSafetyMetrics)
    assert result.informative_tile_count > 0
    assert result.edge_recall == pytest.approx(1.0)
    assert result.gradient_energy_retention == pytest.approx(1.0)
    assert result.lost_informative_tile_fraction == pytest.approx(0.0)
    assert result.low_percentile_tile_retention == pytest.approx(1.0)
    assert result.informative_extreme_fraction == pytest.approx(0.0)
    assert all(np.isfinite(value) for value in result.as_tuple())
    assert float_result.edge_recall == pytest.approx(result.edge_recall)
    assert float_result.gradient_energy_retention == pytest.approx(
        result.gradient_energy_retention
    )


def test_structure_survives_brightness_contrast_inversion_and_smoothing() -> None:
    reference = _reference()
    cases = _candidate_cases()
    identity = analyze_structural_preservation(reference, cases["identity"])

    for name in ("brightness_contrast", "inversion"):
        result = analyze_structural_preservation(reference, cases[name])
        assert result.edge_recall >= identity.edge_recall * 0.9, name
        assert (
            result.gradient_energy_retention >= identity.gradient_energy_retention * 0.8
        ), name
        assert result.lost_informative_tile_fraction <= 0.25, name

    smoothing = analyze_structural_preservation(reference, cases["smoothing"])
    assert smoothing.edge_recall >= identity.edge_recall * 0.9
    assert smoothing.lost_informative_tile_fraction == 0.0
    assert smoothing.low_percentile_tile_retention > 0.5


def test_localized_deletion_is_visible_to_tile_measurement() -> None:
    reference = _reference()
    local_candidate = _candidate_cases()["local_deletion"]
    local_candidate[44:52, 72:88] = 0
    local = analyze_structural_preservation(reference, local_candidate)
    large = analyze_structural_preservation(
        reference, _candidate_cases()["large_deletion"]
    )

    assert local.lost_informative_tile_fraction > 0.0
    identity = analyze_structural_preservation(reference, reference)
    assert (
        local.low_percentile_tile_retention
        < identity.low_percentile_tile_retention * 0.8
    )
    assert large.edge_recall < local.edge_recall
    assert large.gradient_energy_retention < local.gradient_energy_retention
    assert large.lost_informative_tile_fraction >= local.lost_informative_tile_fraction


def test_valid_mask_excludes_padding_from_structural_scores() -> None:
    reference = _reference()
    candidate = reference.copy()
    valid_mask = np.ones(reference.shape, dtype=bool)
    valid_mask[:16, :] = False
    valid_mask[:, :16] = False
    reference[:16, :] = 65535
    reference[:, :16] = 65535
    candidate[:16, :] = 0
    candidate[:, :16] = 0

    result = analyze_structural_preservation(
        reference, candidate, valid_mask=valid_mask
    )
    assert result.edge_recall == pytest.approx(1.0)
    assert result.gradient_energy_retention == pytest.approx(1.0)
    assert result.lost_informative_tile_fraction == pytest.approx(0.0)

    with pytest.raises(ValueError, match="valid_mask shape"):
        analyze_structural_preservation(
            reference, candidate, valid_mask=np.ones((2, 2))
        )

    empty = analyze_structural_preservation(
        reference, candidate, valid_mask=np.zeros(reference.shape, dtype=bool)
    )
    assert empty.edge_recall == 0.0
    assert empty.gradient_energy_retention == 0.0
    assert empty.lost_informative_tile_fraction == 1.0


@pytest.mark.parametrize("value", [0, 1e-12])
def test_blank_and_near_blank_inputs_are_explicitly_not_perfect(value: float) -> None:
    reference = np.full((32, 32), value, dtype=np.float32)
    result = analyze_structural_preservation(reference, reference)

    assert result.informative_tile_count == 0
    assert result.edge_recall == 0.0
    assert result.gradient_energy_retention == 0.0
    assert result.lost_informative_tile_fraction == 1.0
    assert all(np.isfinite(number) for number in result.as_tuple())


def test_structural_safety_public_export_is_lazy() -> None:
    import importlib

    facade = importlib.import_module("mpips.iqa")
    assert "analyze_structural_preservation" in facade.__all__
    assert "StructuralSafetyMetrics" in facade.__all__
    assert facade.analyze_structural_preservation.__module__ == "mpips.iqa.safety"
