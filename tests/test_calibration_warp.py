import hashlib
import inspect

import cv2
import numpy as np
import pytest

from mpips.calibration.warp import warp_image


def _historical_cases() -> (
    list[tuple[str, np.ndarray, np.ndarray, np.ndarray, dict[str, int], np.ndarray]]
):
    image8 = np.arange(12, dtype=np.uint8).reshape(3, 4)
    y_values, x_values = np.indices(image8.shape, dtype=np.float64)
    image16 = np.arange(12, dtype=np.uint16).reshape(3, 4) * 1000 + 500
    image32 = np.arange(12, dtype=np.float32).reshape(3, 4) / 10.0 + 0.25

    return [
        (
            "u8_identity_default_float64_maps",
            image8,
            x_values,
            y_values,
            {},
            image8.copy(),
        ),
        (
            "u8_identity_nearest",
            image8,
            x_values,
            y_values,
            {"interpolation": cv2.INTER_NEAREST},
            image8.copy(),
        ),
        (
            "u8_translated_default",
            image8,
            x_values - 1.0,
            y_values - 1.0,
            {},
            np.array([[0, 0, 0, 0], [0, 0, 1, 2], [0, 4, 5, 6]], dtype=np.uint8),
        ),
        (
            "u8_translated_nearest_border123",
            image8,
            x_values - 1.0,
            y_values - 1.0,
            {"interpolation": cv2.INTER_NEAREST, "border_value": 123},
            np.array(
                [[123, 123, 123, 123], [123, 0, 1, 2], [123, 4, 5, 6]],
                dtype=np.uint8,
            ),
        ),
        (
            "u8_translated_replicate",
            image8,
            x_values - 1.0,
            y_values - 1.0,
            {"border_mode": cv2.BORDER_REPLICATE},
            np.array([[0, 0, 1, 2], [0, 0, 1, 2], [4, 4, 5, 6]], dtype=np.uint8),
        ),
        (
            "u16_identity",
            image16,
            x_values,
            y_values,
            {},
            image16.copy(),
        ),
        (
            "f32_identity",
            image32,
            x_values,
            y_values,
            {},
            image32.copy(),
        ),
        (
            "u8_fractional_linear_float64_maps",
            np.array([[10, 20], [30, 40]], dtype=np.uint8),
            np.array([[0.25, 1.25], [0.25, 1.25]], dtype=np.float64),
            np.array([[0.25, 0.25], [1.25, 1.25]], dtype=np.float64),
            {},
            np.array([[18, 19], [24, 23]], dtype=np.uint8),
        ),
        (
            "u8_fractional_nearest_float64_maps",
            np.array([[10, 20], [30, 40]], dtype=np.uint8),
            np.array([[0.25, 1.25], [0.25, 1.25]], dtype=np.float64),
            np.array([[0.25, 0.25], [1.25, 1.25]], dtype=np.float64),
            {"interpolation": cv2.INTER_NEAREST},
            np.array([[10, 20], [30, 40]], dtype=np.uint8),
        ),
    ]


EXPECTED_SHA256 = {
    "u8_identity_default_float64_maps": (
        "fff3a9bcdd37363d703c1c4f9512533686157868f0d4f16a0f02d0f1da24f9a2"
    ),
    "u8_identity_nearest": (
        "fff3a9bcdd37363d703c1c4f9512533686157868f0d4f16a0f02d0f1da24f9a2"
    ),
    "u8_translated_default": (
        "a97f6d3f06be25e963f2e7355b4d71c47707d6f14db4cb06f8f5730642bb0a1e"
    ),
    "u8_translated_nearest_border123": (
        "94200c09f55661e83aa15aa3dd1261b41cbf9939f8386d759f372ba103cd35b6"
    ),
    "u8_translated_replicate": (
        "dc178dc00e0c44c85402dda9662b4f9d8072c12f81d563bf63ac673058b0a968"
    ),
    "u16_identity": (
        "bf43ae55b108175d512cebed73036dd69e061f24ff46db183ea80e218c5e8562"
    ),
    "f32_identity": (
        "dfbe5c16b20cce4a3f0887219aa045288fa5cb591c9504790f82ff78b3d9aa39"
    ),
    "u8_fractional_linear_float64_maps": (
        "8bc765fe3701cea6ae19741cc77e4d483fa8ba7043f4041cbd0e3989dfefaca1"
    ),
    "u8_fractional_nearest_float64_maps": (
        "5f53c0ff07ba5d9a330e68c95dabb1a9bc49e29f9ed53f6fa7c6d99abb000050"
    ),
}


@pytest.mark.parametrize(
    "name,image,map_x,map_y,kwargs,expected",
    _historical_cases(),
    ids=[case[0] for case in _historical_cases()],
)
def test_warp_image_matches_historical_cases(
    name: str,
    image: np.ndarray,
    map_x: np.ndarray,
    map_y: np.ndarray,
    kwargs: dict[str, int],
    expected: np.ndarray,
) -> None:
    output = warp_image(image, map_x, map_y, **kwargs)

    assert output.shape == expected.shape
    assert output.dtype == expected.dtype
    np.testing.assert_array_equal(output, expected)
    assert hashlib.sha256(output.tobytes()).hexdigest() == EXPECTED_SHA256[name]


def test_warp_image_float64_maps_are_coerced_to_float32() -> None:
    image = np.array([[10, 20], [30, 40]], dtype=np.uint8)
    map_x = np.array([[0.25, 1.25], [0.25, 1.25]], dtype=np.float64)
    map_y = np.array([[0.25, 0.25], [1.25, 1.25]], dtype=np.float64)

    expected = cv2.remap(
        image,
        map_x.astype(np.float32, copy=False),
        map_y.astype(np.float32, copy=False),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    np.testing.assert_array_equal(warp_image(image, map_x, map_y), expected)


def test_warp_image_signature_and_defaults_are_preserved() -> None:
    parameters = inspect.signature(warp_image).parameters

    assert list(parameters) == [
        "image",
        "map_x",
        "map_y",
        "interpolation",
        "border_mode",
        "border_value",
    ]
    assert parameters["interpolation"].default == cv2.INTER_LINEAR
    assert parameters["border_mode"].default == cv2.BORDER_CONSTANT
    assert parameters["border_value"].default == 0
