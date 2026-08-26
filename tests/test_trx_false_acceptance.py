import numpy as np

from mpips.engine.imager_pipeline import complete_pipeline as pipeline
from scripts.validate_real_trx_pipeline import _geometry_failure


def _otsu(image: np.ndarray, monkeypatch) -> float:
    monkeypatch.setitem(pipeline.CONFIG, "THRESHOLD_METHOD", "otsu")
    return pipeline.auto_threshold_detection(image)


def test_uint16_otsu_is_scalar_and_independent_of_first_pixel(monkeypatch):
    image = np.full((32, 32), 5000, dtype=np.uint16)
    image[:, 16:] = 45000

    threshold_a = _otsu(image, monkeypatch)
    image[0, 0] = 45000
    threshold_b = _otsu(image, monkeypatch)

    assert threshold_a == threshold_b
    assert 0 < threshold_a < 65535


def test_float32_otsu_is_scalar_and_independent_of_first_pixel(monkeypatch):
    image = np.full((32, 32), 5000 / 65535, dtype=np.float32)
    image[:, 16:] = 45000 / 65535

    threshold_a = _otsu(image, monkeypatch)
    image[0, 0] = 45000 / 65535
    threshold_b = _otsu(image, monkeypatch)

    assert threshold_a == threshold_b
    assert 0 < threshold_a < 1


def test_real_trx_gate_rejects_catastrophic_zero_occupancy():
    assert _geometry_failure(
        {
            "zero_pixel_ratio": 0.72,
            "non_background_width_ratio": 0.98,
            "non_background_height_ratio": 0.99,
        }
    )
