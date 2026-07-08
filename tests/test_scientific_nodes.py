import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from typing import Any

from mpips.engine.nodes.scientific import (
    NonLocalMeansNode,
    HomomorphicFilterNode,
    WaveletDenoisingNode,
    FlatFieldCorrectionNode,
    CameraCalibrationNode,
    FABEMDNode,
)
from mpips.engine.nodes.iqa import (
    BrisqueNode,
    ContrastImprovementIndexNode,
    EnhancementMeasureNode,
    EntropyNode,
)
from mpips.engine.iqa import (
    calculate_entropy,
    calculate_eme,
    calculate_cii,
    calculate_brisque,
    calculate_all_metrics,
)


@pytest.fixture
def dummy_gray_image() -> np.ndarray:
    # A 128x128 grayscale image (uint8)
    return np.random.randint(0, 256, (128, 128), dtype=np.uint8)


@pytest.fixture
def dummy_color_image() -> np.ndarray:
    # A 128x128 BGR color image (uint8)
    return np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)


def test_nlm_denoising(
    dummy_gray_image: np.ndarray, dummy_color_image: np.ndarray
) -> None:
    node = NonLocalMeansNode()

    # Grayscale
    res = node.execute(
        {"input_image": dummy_gray_image}, {"h": 3.0, "template_window_size": 7}
    )
    assert "output_image" in res
    assert res["output_image"].shape == dummy_gray_image.shape

    # Color
    res_color = node.execute({"input_image": dummy_color_image}, {"h": 3.0})
    assert "output_image" in res_color
    assert res_color["output_image"].shape == dummy_color_image.shape


def test_homomorphic_filter(
    dummy_gray_image: np.ndarray, dummy_color_image: np.ndarray
) -> None:
    node = HomomorphicFilterNode()

    # Grayscale
    res = node.execute({"input_image": dummy_gray_image}, {"cutoff_frequency": 20.0})
    assert "output_image" in res
    assert res["output_image"].shape == dummy_gray_image.shape

    # Color
    res_color = node.execute({"input_image": dummy_color_image}, {})
    assert "output_image" in res_color
    assert res_color["output_image"].shape == dummy_color_image.shape


def test_wavelet_denoising(
    dummy_gray_image: np.ndarray, dummy_color_image: np.ndarray
) -> None:
    node = WaveletDenoisingNode()

    # Grayscale
    res = node.execute(
        {"input_image": dummy_gray_image}, {"wavelet": "haar", "mode": "soft"}
    )
    assert "output_image" in res
    assert res["output_image"].shape == dummy_gray_image.shape

    # Color
    res_color = node.execute(
        {"input_image": dummy_color_image}, {"wavelet": "db1", "mode": "hard"}
    )
    assert "output_image" in res_color
    assert res_color["output_image"].shape == dummy_color_image.shape


@patch("mpips.engine.nodes.scientific.download_image")
@patch("cv2.imread")
def test_flat_field_correction(
    mock_imread: Any, mock_download: Any, dummy_gray_image: np.ndarray
) -> None:
    node = FlatFieldCorrectionNode()

    # Configure mock imread to return calibration frames
    dark_frame = np.ones((128, 128), dtype=np.uint8) * 10
    flat_frame = np.ones((128, 128), dtype=np.uint8) * 240
    mock_imread.side_effect = [dark_frame, flat_frame]

    res = node.execute(
        {"input_image": dummy_gray_image},
        {"dark_field_key": "dark.png", "flat_field_key": "flat.png"},
    )
    assert "output_image" in res
    assert res["output_image"].shape == dummy_gray_image.shape
    assert mock_download.call_count == 2


@patch("mpips.engine.nodes.scientific.download_image")
def test_camera_calibration(mock_download: Any, dummy_gray_image: np.ndarray) -> None:
    node = CameraCalibrationNode()

    # 1. Test calibration key empty -> returns original image
    res_bypass = node.execute(
        {"input_image": dummy_gray_image}, {"calibration_file_key": ""}
    )
    assert np.array_equal(res_bypass["output_image"], dummy_gray_image)

    # 2. Test calibration with npz file load
    camera_matrix = np.array([[100, 0, 64], [0, 100, 64], [0, 0, 1]], dtype=float)
    dist_coefs = np.array([0.1, -0.05, 0, 0, 0], dtype=float)

    with patch("numpy.load") as mock_np_load:
        mock_file = MagicMock()
        mock_file.__enter__.return_value = {
            "mtx": camera_matrix,
            "dist": dist_coefs,
        }
        mock_np_load.return_value = mock_file

        res = node.execute(
            {"input_image": dummy_gray_image}, {"calibration_file_key": "cal.npz"}
        )
        assert "output_image" in res
        assert res["output_image"].shape == dummy_gray_image.shape


def test_fabemd(dummy_gray_image: np.ndarray, dummy_color_image: np.ndarray) -> None:
    node = FABEMDNode()

    # Grayscale
    res = node.execute({"input_image": dummy_gray_image}, {"num_imfs": 2})
    assert "output_image" in res
    assert res["output_image"].shape == dummy_gray_image.shape

    # Color
    res_color = node.execute({"input_image": dummy_color_image}, {"num_imfs": 1})
    assert "output_image" in res_color
    assert res_color["output_image"].shape == dummy_color_image.shape


def test_iqa_calculators(
    dummy_gray_image: np.ndarray, dummy_color_image: np.ndarray
) -> None:
    # 1. Entropy
    ent_gray = calculate_entropy(dummy_gray_image)
    ent_color = calculate_entropy(dummy_color_image)
    assert isinstance(ent_gray, float)
    assert isinstance(ent_color, float)

    # 2. EME
    eme_gray = calculate_eme(dummy_gray_image, block_size=8)
    eme_color = calculate_eme(dummy_color_image, block_size=4)
    assert isinstance(eme_gray, float)
    assert isinstance(eme_color, float)

    # 3. CII
    processed = dummy_gray_image + 10
    cii = calculate_cii(processed, dummy_gray_image)
    assert isinstance(cii, float)

    # 4. BRISQUE
    brisque_gray = calculate_brisque(dummy_gray_image)
    assert 0.0 <= brisque_gray <= 100.0

    # 5. All Metrics
    all_metrics = calculate_all_metrics(processed, dummy_gray_image)
    assert "cii" in all_metrics
    assert "entropy" in all_metrics
    assert "eme" in all_metrics
    assert "brisque" in all_metrics


def test_iqa_nodes_execute_catalog_outputs(dummy_gray_image: np.ndarray) -> None:
    cii = ContrastImprovementIndexNode().execute(
        {"input_image": dummy_gray_image, "reference_image": dummy_gray_image}, {}
    )
    entropy = EntropyNode().execute({"input_image": dummy_gray_image}, {})
    eme = EnhancementMeasureNode().execute(
        {"input_image": dummy_gray_image}, {"block_size": 8}
    )
    brisque = BrisqueNode().execute({"input_image": dummy_gray_image}, {})

    assert "cii_score" in cii
    assert "entropy_score" in entropy
    assert "eme_score" in eme
    assert "brisque_score" in brisque
