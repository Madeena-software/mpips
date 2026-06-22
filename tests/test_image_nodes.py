import numpy as np
from image_engine.factory import get_node_class


def test_resize_node() -> None:
    node_cls = get_node_class("resize")
    node = node_cls()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    res = node.execute(
        {"input_image": img}, {"width": 50, "height": 50, "interpolation": "NEAREST"}
    )
    out_img = res["output_image"]
    assert out_img.shape == (50, 50, 3)


def test_crop_node() -> None:
    node_cls = get_node_class("crop")
    node = node_cls()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Fill crop area with a distinct value to verify
    img[10:30, 20:50] = 255
    res = node.execute(
        {"input_image": img}, {"x_start": 20, "y_start": 10, "width": 30, "height": 20}
    )
    out_img = res["output_image"]
    assert out_img.shape == (20, 30, 3)
    assert np.all(out_img == 255)


def test_rotate_node() -> None:
    node_cls = get_node_class("rotate")
    node = node_cls()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    res = node.execute({"input_image": img}, {"angle": 90.0, "expand": True})
    out_img = res["output_image"]
    assert out_img.shape == (100, 100, 3)


def test_flip_node() -> None:
    node_cls = get_node_class("flip")
    node = node_cls()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[0:50, 0:50] = 255
    res = node.execute({"input_image": img}, {"direction": "horizontal"})
    out_img = res["output_image"]
    assert out_img.shape == (100, 100, 3)
    # After horizontal flip, top-left quadrant goes to top-right
    assert np.all(out_img[0:50, 50:100] == 255)


def test_grayscale_node() -> None:
    node_cls = get_node_class("grayscale")
    node = node_cls()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    res = node.execute({"input_image": img}, {})
    out_img = res["output_image"]
    assert len(out_img.shape) == 2  # 1 channel (grayscale)
    assert out_img.shape == (100, 100)


def test_brightness_contrast_node() -> None:
    node_cls = get_node_class("brightness_contrast")
    node = node_cls()
    img = np.ones((5, 5), dtype=np.uint8) * 10
    res = node.execute({"input_image": img}, {"alpha": 1.5, "beta": 5.0})
    out_img = res["output_image"]
    # 10 * 1.5 + 5 = 20
    assert np.all(out_img == 20)


def test_brightness_contrast_preserves_uint16() -> None:
    node_cls = get_node_class("brightness_contrast")
    node = node_cls()
    img = np.ones((5, 5), dtype=np.uint16) * 1000
    res = node.execute({"input_image": img}, {"alpha": 2.0, "beta": 500.0})
    out_img = res["output_image"]
    assert out_img.dtype == np.uint16
    assert np.all(out_img == 2500)


def test_thresholding_node_binary() -> None:
    node_cls = get_node_class("thresholding")
    node = node_cls()
    img = np.ones((5, 5), dtype=np.uint8) * 100
    res = node.execute({"input_image": img}, {"threshold_value": 50, "type": "binary"})
    out_img = res["output_image"]
    assert np.all(out_img == 255)  # 100 > 50 -> 255


def test_thresholding_preserves_uint16_max_value() -> None:
    node_cls = get_node_class("thresholding")
    node = node_cls()
    img = np.ones((5, 5), dtype=np.uint16) * 1000
    res = node.execute({"input_image": img}, {"threshold_value": 500, "type": "binary"})
    out_img = res["output_image"]
    assert out_img.dtype == np.uint16
    assert np.all(out_img == np.iinfo(np.uint16).max)


def test_gamma_correction_node() -> None:
    node_cls = get_node_class("gamma_correction")
    node = node_cls()
    img = np.ones((5, 5), dtype=np.uint8) * 128
    res = node.execute({"input_image": img}, {"gamma": 2.0})
    out_img = res["output_image"]
    assert out_img.shape == (5, 5)


def test_gamma_correction_preserves_float32() -> None:
    node_cls = get_node_class("gamma_correction")
    node = node_cls()
    img = np.linspace(0.0, 1.0, 25, dtype=np.float32).reshape(5, 5)
    res = node.execute({"input_image": img}, {"gamma": 2.0})
    out_img = res["output_image"]
    assert out_img.dtype == np.float32
    assert out_img.shape == (5, 5)


def test_gaussian_blur_node() -> None:
    node_cls = get_node_class("gaussian_blur")
    node = node_cls()
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    res = node.execute({"input_image": img}, {"kernel_size": 3, "sigma": 0.5})
    out_img = res["output_image"]
    assert out_img.shape == (10, 10, 3)


def test_median_blur_node() -> None:
    node_cls = get_node_class("median_blur")
    node = node_cls()
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    res = node.execute({"input_image": img}, {"kernel_size": 3})
    out_img = res["output_image"]
    assert out_img.shape == (10, 10, 3)


def test_canny_node() -> None:
    node_cls = get_node_class("canny")
    node = node_cls()
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    res = node.execute(
        {"input_image": img}, {"low_threshold": 50, "high_threshold": 150}
    )
    out_img = res["output_image"]
    assert out_img.shape == (10, 10)


def test_canny_accepts_uint16_and_outputs_uint8_edges() -> None:
    node_cls = get_node_class("canny")
    node = node_cls()
    img = np.zeros((10, 10), dtype=np.uint16)
    img[:, 5:] = 4095
    res = node.execute(
        {"input_image": img}, {"low_threshold": 50, "high_threshold": 150}
    )
    out_img = res["output_image"]
    assert out_img.dtype == np.uint8
    assert out_img.shape == (10, 10)


def test_sobel_node() -> None:
    node_cls = get_node_class("sobel")
    node = node_cls()
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    res = node.execute({"input_image": img}, {"dx": 1, "dy": 0, "ksize": 3})
    out_img = res["output_image"]
    assert out_img.shape == (10, 10)


def test_sobel_preserves_uint16() -> None:
    node_cls = get_node_class("sobel")
    node = node_cls()
    img = np.zeros((10, 10), dtype=np.uint16)
    img[:, 5:] = 4095
    res = node.execute({"input_image": img}, {"dx": 1, "dy": 0, "ksize": 3})
    out_img = res["output_image"]
    assert out_img.dtype == np.uint16
    assert out_img.shape == (10, 10)
