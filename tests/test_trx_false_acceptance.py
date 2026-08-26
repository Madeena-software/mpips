import numpy as np
import cv2

from mpips.engine.imager_pipeline import complete_pipeline as pipeline
from scripts.validate_real_trx_pipeline import _first_collapse_stage, _geometry_failure


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


def test_pipeline_reports_observed_stage_metrics(tmp_path):
    observed = {}
    raw = np.arange(64, dtype=np.uint16).reshape(8, 8) + 1000
    dark = np.zeros_like(raw)
    flat = np.full_like(raw, 50000) + np.arange(64, dtype=np.uint16).reshape(8, 8)
    cv2.imwrite(str(tmp_path / "raw.tiff"), raw)
    cv2.imwrite(str(tmp_path / "dark.tiff"), dark)
    cv2.imwrite(str(tmp_path / "flat.tiff"), flat)

    pipeline.process_single_image(
        str(tmp_path / "raw.tiff"),
        str(tmp_path / "dark.tiff"),
        str(tmp_path / "flat.tiff"),
        str(tmp_path / "output.tiff"),
        detector_type="BED",
        stage_observer=observed.__setitem__,
    )

    assert "PRE_THRESHOLD" in observed
    assert observed["PRE_THRESHOLD"]["shape"] == [8, 8]
    assert "exact_zero_ratio" in observed["PRE_THRESHOLD"]
    assert "FINAL_IMAGE" in observed
    assert "DICOM" not in observed


def test_first_collapse_stage_is_not_dicom_when_invert_collapses():
    healthy = {"exact_zero_ratio": 0.01, "nonzero_ratio": 0.99}
    collapsed = {"exact_zero_ratio": 0.72, "nonzero_ratio": 0.28}
    assert (
        _first_collapse_stage({"PRE_THRESHOLD": healthy, "INVERT": collapsed})
        == "INVERT"
    )


def test_trx_bypasses_destructive_threshold_separation():
    assert pipeline.threshold_method_for_detector("TRX", "auto") == "none"
    assert pipeline.threshold_method_for_detector("BED", "auto") == "auto"
    assert pipeline.threshold_method_for_detector("TRX", "auto", "auto") == "auto"
