from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

import mpips.dag.nodes.scientific as scientific


def _fixture_images() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y_values, x_values = np.indices((16, 16), dtype=np.uint16)
    gray = (
        (x_values * 17 + y_values * 29 + (x_values * y_values) % 7 * 11) % 256
    ).astype(np.uint8)
    bgr = np.stack([gray, np.roll(gray, 2, axis=0), np.roll(gray, 3, axis=1)], axis=2)
    bgra = np.concatenate([bgr, np.full((16, 16, 1), 77, dtype=np.uint8)], axis=2)
    uint16 = (gray.astype(np.uint16) * 257).astype(np.uint16)
    return gray, bgr, bgra, uint16


def _sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def test_non_local_means_historical_hashes_and_channel_contracts() -> None:
    gray, bgr, bgra, uint16 = _fixture_images()
    node = scientific.NonLocalMeansNode()

    cases = (
        (
            gray,
            "f6bdd287633ec39a7a7018573aeffce006ee32e020ea658fae379f72e3df7e30",
        ),
        (
            bgr,
            "7fcdc70c1813ee0e4e55a6c8b34bf5c61d8938f68fd35580523576e60c481ecc",
        ),
        (
            bgra,
            "3fcc0c63a599338b21dbd5785042fb591632b9a9d974b01e9e485e01ee2da69f",
        ),
        (
            uint16,
            "b061c550343798050b712f670d881139f5e4dca2edf7bdb7dfe822cf4aa5a33a",
        ),
    )

    for image, expected_hash in cases:
        output = node.execute({"input_image": image}, {})["output_image"]
        assert output.shape == image.shape
        assert output.dtype == image.dtype
        assert _sha256(output) == expected_hash

    output = node.execute({"input_image": bgra}, {})["output_image"]
    np.testing.assert_array_equal(output[:, :, 3], bgra[:, :, 3])


def test_non_local_means_preserves_even_window_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gray, _, _, _ = _fixture_images()
    captured: dict[str, Any] = {}

    def fake_denoise(
        image: np.ndarray,
        _destination: None,
        *,
        h: float,
        templateWindowSize: int,
        searchWindowSize: int,
    ) -> np.ndarray:
        captured.update(
            h=h,
            templateWindowSize=templateWindowSize,
            searchWindowSize=searchWindowSize,
        )
        return image

    monkeypatch.setattr(cv2, "fastNlMeansDenoising", fake_denoise)
    output = scientific.NonLocalMeansNode().execute(
        {"input_image": gray},
        {"h": 4.5, "template_window_size": 6, "search_window_size": 20},
    )["output_image"]

    assert captured == {"h": 4.5, "templateWindowSize": 7, "searchWindowSize": 21}
    np.testing.assert_array_equal(output, gray)


def test_non_local_means_preserves_exact_dimension_and_channel_errors() -> None:
    node = scientific.NonLocalMeansNode()

    with pytest.raises(ValueError, match="^Unsupported channel size in NLM: 2$"):
        node.execute({"input_image": np.zeros((4, 4, 2), dtype=np.uint8)}, {})
    with pytest.raises(ValueError, match=r"^Invalid image dimensions\.$"):
        node.execute({"input_image": np.zeros((4,), dtype=np.uint8)}, {})
    with pytest.raises(
        ValueError, match=r"^NonLocalMeansNode requires 'input_image' input\.$"
    ):
        node.execute({}, {})


def test_homomorphic_filter_historical_hashes_and_filter_channel_values() -> None:
    gray, bgr, _, uint16 = _fixture_images()
    node = scientific.HomomorphicFilterNode()

    cases = (
        (
            gray,
            "3985ece2cb9001a9fa1af5717da545bdd0a8e287836ce89063c89523d9e13fe7",
        ),
        (
            bgr,
            "6d48c32ac40e946b1ba35d4b89704dc34bbb18093e5293f41276250c80dc88e2",
        ),
        (
            uint16,
            "72ddae0931c1c2777a5c9bc961f28c0346a5a1c55ff11dbeac1b75decd706b44",
        ),
    )
    for image, expected_hash in cases:
        output = node.execute({"input_image": image}, {})["output_image"]
        assert output.shape == image.shape
        assert output.dtype == image.dtype
        assert _sha256(output) == expected_hash

    filtered = node._filter_channel(gray, 0.5, 1.5, 30.0)
    np.testing.assert_allclose(
        filtered[[0, 3], [0, 4]],
        np.array([-0.09353629275179538, 13.513338824147741]),
        rtol=0,
        atol=1e-12,
    )


def test_homomorphic_filter_preserves_dimension_error() -> None:
    with pytest.raises(ValueError, match=r"^Invalid image dimensions\.$"):
        scientific.HomomorphicFilterNode().execute(
            {"input_image": np.zeros((2, 2, 1, 1), dtype=np.uint8)}, {}
        )


def test_wavelet_historical_hashes_dtype_and_shape_contracts() -> None:
    gray, bgr, _, uint16 = _fixture_images()
    node = scientific.WaveletDenoisingNode()
    cases = (
        (
            gray,
            {"wavelet": "db1", "mode": "soft"},
            "9e63ac44752c7438f9047e92e6dfeda367dca071c140ade91018eda8b9bd4fb2",
        ),
        (
            bgr,
            {"wavelet": "db2", "mode": "hard"},
            "1a08948e286e542db53be03db7b6a821d2169905f11860e1a6c69343773b5974",
        ),
        (
            uint16,
            {"wavelet": "sym2", "mode": "soft"},
            "8913c6031e3ad8fa4c866af750ea270d868ca90aa45aa9302c7042497254d287",
        ),
    )
    for image, params, expected_hash in cases:
        output = node.execute({"input_image": image}, params)["output_image"]
        assert output.shape == image.shape
        assert output.dtype == image.dtype
        assert _sha256(output) == expected_hash


def test_flat_field_supplied_frames_zero_denominator_and_resize_contract() -> None:
    node = scientific.FlatFieldCorrectionNode()
    raw = np.array([[10, 20, 30], [40, 50, 60]], dtype=np.uint16)
    dark = np.full_like(raw, 5)
    flat = np.array([[5, 15, 25], [35, 45, 55]], dtype=np.uint16)

    output = node.execute(
        {
            "input_image": raw,
            "dark_field_image": dark,
            "flat_field_image": flat,
        },
        {},
    )["output_image"]
    np.testing.assert_array_equal(output, np.array([[65535, 37, 31], [29, 28, 27]]))
    assert _sha256(output) == (
        "08ada6ba15edd0f3e2bf5dbe9fd865fd5c0efe5ba19443a4dd4f0ced9cce09e9"
    )

    zero = node.execute(
        {
            "input_image": np.array([[4]], dtype=np.uint16),
            "dark_field_image": np.array([[4]], dtype=np.uint16),
            "flat_field_image": np.array([[4]], dtype=np.uint16),
        },
        {},
    )["output_image"]
    np.testing.assert_array_equal(zero, np.zeros((1, 1), dtype=np.uint16))

    resized = node.execute(
        {
            "input_image": np.arange(16, dtype=np.uint8).reshape(4, 4),
            "dark_field_image": np.ones((2, 2), dtype=np.uint8),
            "flat_field_image": np.full((2, 2), 9, dtype=np.uint8),
        },
        {},
    )["output_image"]
    np.testing.assert_array_equal(
        resized,
        np.array(
            [[0, 0, 1, 2], [3, 4, 5, 6], [7, 8, 9, 10], [11, 12, 13, 14]],
            dtype=np.uint8,
        ),
    )


def test_flat_field_blank_keys_and_storage_fallback_preserve_cleanup_and_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = scientific.FlatFieldCorrectionNode()
    raw = np.array([[10, 20], [30, 40]], dtype=np.uint8)
    output = node.execute({"input_image": raw}, {})["output_image"]
    np.testing.assert_array_equal(output, raw)

    downloaded: list[tuple[str, bool, str]] = []
    temp_paths: list[str] = []
    frames = [np.full((2, 2), 2, dtype=np.uint8), np.full((2, 2), 10, dtype=np.uint8)]

    def fake_download(
        source: str, destination: str, is_presigned_url: bool = False
    ) -> None:
        downloaded.append((source, is_presigned_url, destination))
        temp_paths.append(destination)

    monkeypatch.setattr(scientific, "download_image", fake_download)
    monkeypatch.setattr(cv2, "imread", lambda *_args: frames.pop(0))
    node.execute(
        {"input_image": raw},
        {"dark_field_key": "https://example/dark.png", "flat_field_key": "flat.png"},
    )

    assert [(source, is_url) for source, is_url, _ in downloaded] == [
        ("https://example/dark.png", True),
        ("flat.png", False),
    ]
    assert all(not Path(path).exists() for path in temp_paths)


@pytest.mark.parametrize(
    "failure, expected",
    [
        (
            "imread",
            "Flat-Field Correction failed to read frame 'bad.png': "
            "Could not load flat-field calibration image: bad.png",
        ),
        (
            "download",
            "Flat-Field Correction failed to read frame 'bad.png': network failure",
        ),
    ],
)
def test_flat_field_storage_errors_wrap_and_cleanup(
    monkeypatch: pytest.MonkeyPatch, failure: str, expected: str
) -> None:
    node = scientific.FlatFieldCorrectionNode()
    paths: list[str] = []

    def fake_download(_source: str, destination: str, **_kwargs: Any) -> None:
        paths.append(destination)
        if failure == "download":
            raise RuntimeError("network failure")

    monkeypatch.setattr(scientific, "download_image", fake_download)
    if failure == "imread":
        monkeypatch.setattr(cv2, "imread", lambda *_args: None)

    with pytest.raises(ValueError) as error:
        node.execute(
            {"input_image": np.ones((2, 2), dtype=np.uint8)},
            {"dark_field_key": "bad.png"},
        )
    assert str(error.value) == expected
    assert all(not Path(path).exists() for path in paths)


def test_leveling_historical_roi_dtype_and_edge_contracts() -> None:
    node = scientific.LevelingNode()
    image = np.array([[50, 50, 150, 150], [50, 50, 150, 150]], dtype=np.uint8)
    output = node.execute(
        {"input_image": image},
        {"target_mean": 100, "x_start": 0, "y_start": 0, "width": 2, "height": 2},
    )["output_image"]
    np.testing.assert_array_equal(
        output, np.array([[100, 100, 255, 255], [100, 100, 255, 255]], dtype=np.uint8)
    )

    uint16 = node.execute(
        {"input_image": np.full((2, 2), 1000, dtype=np.uint16)}, {"target_mean": 500}
    )["output_image"]
    assert uint16.dtype == np.uint16
    np.testing.assert_array_equal(uint16, np.full((2, 2), 500, dtype=np.uint16))

    edge = node.execute(
        {"input_image": np.full((2, 2), 50, dtype=np.uint8)},
        {"target_mean": 100, "width": 0, "height": 0},
    )["output_image"]
    np.testing.assert_array_equal(edge, np.full((2, 2), 100, dtype=np.uint8))

    zero_target = node.execute(
        {"input_image": np.full((2, 2), 50, dtype=np.uint8)}, {"target_mean": 0}
    )["output_image"]
    np.testing.assert_array_equal(zero_target, np.zeros((2, 2), dtype=np.uint8))

    zero_current = np.zeros((2, 2), dtype=np.uint8)
    unchanged = node.execute({"input_image": zero_current}, {"target_mean": 50})[
        "output_image"
    ]
    assert unchanged is not zero_current
    np.testing.assert_array_equal(unchanged, zero_current)

    with pytest.raises(ValueError) as error:
        node.execute({"input_image": image}, {"target_mean": -1})
    assert str(error.value) == (
        "target_mean must be a non-negative reference brightness "
        "(the mean of the batch's baseline image's ROI)."
    )


def test_camera_calibration_bypass_aliases_storage_urls_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node = scientific.CameraCalibrationNode()
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    assert node.execute({"input_image": image}, {})["output_image"] is image

    downloaded: list[tuple[str, bool, str]] = []
    matrix = np.array([[100.0, 0, 2], [0, 100.0, 2], [0, 0, 1]])
    distortion = np.array([0.1, -0.05, 0, 0, 0])
    temp_paths: list[str] = []
    current_payload: dict[str, Any] = {}

    def fake_download(
        source: str, destination: str, is_presigned_url: bool = False
    ) -> None:
        downloaded.append((source, is_presigned_url, destination))
        temp_paths.append(destination)
        np.savez(destination, **current_payload)

    calls: dict[str, Any] = {}

    def fake_new_camera(
        mtx: np.ndarray,
        dist: np.ndarray,
        size: tuple[int, int],
        alpha: int,
        new_size: tuple[int, int],
    ) -> tuple[np.ndarray, None]:
        calls["new"] = (mtx, dist, size, alpha, new_size)
        return mtx, None

    def fake_undistort(
        input_image: np.ndarray,
        mtx: np.ndarray,
        dist: np.ndarray,
        _none: None,
        new_mtx: np.ndarray,
    ) -> np.ndarray:
        calls["undistort"] = (input_image, mtx, dist, new_mtx)
        return input_image + 1

    monkeypatch.setattr(scientific, "download_image", fake_download)
    monkeypatch.setattr(cv2, "getOptimalNewCameraMatrix", fake_new_camera)
    monkeypatch.setattr(cv2, "undistort", fake_undistort)

    for source, payload, expected_url in (
        ("cal.npz", {"mtx": matrix, "dist": distortion}, False),
        (
            "https://example/cal.npz",
            {"camera_matrix": matrix, "dist_coefs": distortion},
            True,
        ),
    ):
        current_payload = payload
        output = node.execute({"input_image": image}, {"calibration_file_key": source})[
            "output_image"
        ]
        np.testing.assert_array_equal(output, image + 1)
        assert downloaded[-1][0:2] == (source, expected_url)
        assert calls["new"][2:] == ((4, 4), 1, (4, 4))
        assert all(not Path(path).exists() for path in temp_paths)


@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {"dist": np.zeros(5)},
            "Camera Calibration failed: 'Camera matrix (mtx/camera_matrix) "
            "not found in calibration file.'",
        ),
        (
            {"mtx": np.eye(3)},
            "Camera Calibration failed: 'Distortion coefficients (dist/dist_coefs) "
            "not found in calibration file.'",
        ),
    ],
)
def test_camera_calibration_missing_keys_are_wrapped(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any], expected: str
) -> None:
    node = scientific.CameraCalibrationNode()

    def fake_download(_source: str, destination: str, **_kwargs: Any) -> None:
        np.savez(destination, **payload)

    monkeypatch.setattr(scientific, "download_image", fake_download)
    with pytest.raises(ValueError) as error:
        node.execute(
            {"input_image": np.zeros((2, 2), dtype=np.uint8)},
            {"calibration_file_key": "cal.npz"},
        )
    assert str(error.value) == expected


def test_camera_calibration_download_failure_wraps_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths: list[str] = []

    def fake_download(_source: str, destination: str, **_kwargs: Any) -> None:
        paths.append(destination)
        raise RuntimeError("download failure")

    monkeypatch.setattr(scientific, "download_image", fake_download)
    with pytest.raises(ValueError) as error:
        scientific.CameraCalibrationNode().execute(
            {"input_image": np.zeros((2, 2), dtype=np.uint8)},
            {"calibration_file_key": "cal.npz"},
        )
    assert str(error.value) == "Camera Calibration failed: download failure"
    assert all(not Path(path).exists() for path in paths)


def test_fabemd_historical_hashes_and_normalization() -> None:
    gray, bgr, _, _ = _fixture_images()
    node = scientific.FABEMDNode()

    gray_output = node.execute({"input_image": gray}, {"num_imfs": 2})
    assert list(gray_output) == ["bimf_1", "bimf_2", "residual"]
    assert {key: _sha256(value) for key, value in gray_output.items()} == {
        "bimf_1": "38a6e98d671647d1a60055da8834dbedd7d83b9644c42e860abccc9e00deb4f3",
        "bimf_2": "ed55e5a4c2c078f9e043dadeba4d3e4f30040ca15792fbea54fae045d1ca86a0",
        "residual": "ac2c9535549c2c76b927f43b7379e866a1e4e800be888dc8e9803eee5d6cf2f7",
    }

    color_output = node.execute({"input_image": bgr}, {"num_imfs": 1})
    assert list(color_output) == ["bimf_1", "residual"]
    assert {key: _sha256(value) for key, value in color_output.items()} == {
        "bimf_1": "33af609f9b1c5e6497fc49a75b037dfe2dec440d98a25cd873722916f47608d1",
        "residual": "2f05953ef68fac48308b6ebae30ab9815dc39aaec4472115a1931b5cd9ddcbdc",
    }
    for value in (*gray_output.values(), *color_output.values()):
        assert value.dtype == np.uint8
        assert value.shape in (gray.shape, bgr.shape)

    lower = node.execute({"input_image": gray}, {"num_imfs": 0})
    upper = node.execute({"input_image": gray}, {"num_imfs": 999})
    assert list(lower) == ["bimf_1", "residual"]
    assert list(upper) == [f"bimf_{index}" for index in range(1, 11)] + ["residual"]

    constant = node.execute(
        {"input_image": np.full((4, 4), 9, dtype=np.uint8)}, {"num_imfs": 2}
    )
    for value in constant.values():
        np.testing.assert_array_equal(value, np.zeros((4, 4), dtype=np.uint8))


def test_fabemd_preserves_invalid_dimension_error() -> None:
    with pytest.raises(ValueError, match=r"^Invalid image dimensions\.$"):
        scientific.FABEMDNode().execute(
            {"input_image": np.zeros((2, 2, 1, 1), dtype=np.uint8)}, {}
        )


def test_scientific_package_imports_preserve_lazy_and_engine_free_boundaries() -> None:
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent("""
        import sys

        import mpips.dag
        import mpips.dag.nodes

        forbidden = {
            "mpips.engine",
            "mpips.api",
            "mpips.worker",
            "cv2",
            "numpy",
            "scipy",
            "skimage",
            "mpips.storage",
            "boto3",
            "fastapi",
            "celery",
            "torch",
            "matplotlib",
            "PIL",
        }

        def loaded():
            return sorted(
                name
                for name in sys.modules
                if name in forbidden
                or any(name.startswith(item + ".") for item in forbidden)
            )

        assert loaded() == []
        import mpips.dag.nodes.scientific

        assert "mpips.engine" not in sys.modules
        assert "mpips.api" not in sys.modules
        assert "mpips.worker" not in sys.modules
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
