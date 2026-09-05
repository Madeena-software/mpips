import numpy as np
import pytest

from mpips.processing.filtering import apply_median_filter
from mpips.processing.imagej import ImageJReplicator

HYBRID_FIXTURE = np.array(
    [
        [93, 24, 143, 50, 142, 35, 170, 144, 9, 193, 209],
        [196, 199, 15, 110, 50, 179, 45, 71, 1, 218, 151],
        [6, 193, 178, 198, 9, 169, 3, 8, 250, 62, 222],
        [194, 170, 42, 19, 230, 212, 65, 204, 248, 218, 166],
        [210, 14, 245, 26, 97, 185, 146, 15, 66, 235, 155],
        [19, 138, 152, 83, 236, 255, 1, 166, 54, 151, 104],
        [53, 53, 174, 133, 63, 221, 66, 52, 209, 174, 133],
        [67, 92, 169, 162, 4, 19, 52, 142, 6, 71, 82],
        [238, 242, 184, 142, 146, 60, 46, 158, 205, 41, 143],
        [85, 221, 19, 78, 133, 63, 16, 78, 171, 229, 181],
        [37, 148, 116, 213, 189, 189, 201, 203, 129, 174, 234],
    ],
    dtype=np.uint8,
)

EXPECTED_UINT8 = {
    3: np.array(
        [
            [93, 24, 143, 50, 142, 35, 170, 144, 9, 193, 209],
            [196, 193, 50, 110, 50, 142, 45, 71, 62, 218, 193],
            [193, 193, 178, 110, 110, 169, 45, 45, 218, 151, 218],
            [194, 170, 42, 42, 185, 185, 65, 146, 218, 218, 166],
            [170, 42, 138, 83, 97, 185, 146, 54, 66, 166, 155],
            [53, 138, 152, 97, 185, 221, 52, 146, 54, 151, 104],
            [53, 67, 152, 133, 83, 66, 66, 52, 151, 151, 133],
            [82, 92, 169, 162, 63, 52, 52, 142, 52, 71, 82],
            [143, 221, 169, 142, 133, 60, 52, 142, 158, 82, 143],
            [143, 184, 116, 133, 133, 63, 63, 129, 171, 205, 181],
            [85, 148, 116, 213, 189, 189, 201, 203, 129, 174, 234],
        ],
        dtype=np.uint8,
    ),
    5: np.array(
        [
            [93, 24, 143, 50, 142, 35, 170, 144, 9, 193, 209],
            [193, 170, 50, 110, 50, 142, 65, 144, 71, 209, 193],
            [193, 170, 143, 110, 142, 169, 65, 65, 204, 144, 199],
            [170, 170, 50, 110, 152, 185, 65, 179, 166, 210, 166],
            [174, 133, 152, 97, 97, 169, 146, 65, 151, 151, 155],
            [62, 138, 152, 97, 133, 185, 52, 146, 65, 151, 104],
            [104, 82, 152, 133, 133, 66, 66, 52, 146, 133, 133],
            [82, 138, 152, 162, 60, 63, 52, 142, 52, 133, 82],
            [151, 148, 169, 142, 133, 60, 66, 158, 143, 82, 143],
            [85, 162, 116, 116, 133, 78, 78, 129, 171, 205, 174],
            [116, 148, 116, 213, 189, 189, 201, 203, 129, 174, 234],
        ],
        dtype=np.uint8,
    ),
    7: np.array(
        [
            [93, 24, 143, 50, 142, 35, 170, 144, 9, 193, 209],
            [193, 143, 143, 110, 50, 142, 142, 71, 71, 193, 152],
            [178, 193, 151, 50, 142, 169, 65, 104, 170, 62, 166],
            [152, 155, 104, 110, 97, 185, 65, 166, 204, 193, 166],
            [170, 133, 166, 133, 97, 169, 146, 65, 146, 146, 155],
            [62, 146, 152, 92, 158, 166, 62, 146, 82, 151, 104],
            [104, 82, 146, 133, 133, 133, 66, 60, 146, 133, 138],
            [104, 138, 166, 162, 60, 78, 52, 142, 82, 138, 85],
            [133, 174, 162, 142, 146, 133, 66, 158, 142, 82, 143],
            [85, 133, 116, 116, 133, 78, 78, 129, 171, 171, 174],
            [116, 148, 116, 213, 189, 189, 201, 203, 129, 174, 234],
        ],
        dtype=np.uint8,
    ),
}

EXPECTED_REPEATED_UINT8 = np.array(
    [
        [93, 24, 143, 50, 142, 35, 170, 144, 9, 193, 204],
        [170, 170, 50, 110, 50, 142, 71, 144, 144, 193, 193],
        [193, 170, 143, 110, 142, 142, 142, 71, 179, 144, 174],
        [170, 170, 110, 110, 110, 169, 65, 151, 166, 166, 166],
        [166, 133, 143, 110, 110, 146, 146, 66, 151, 151, 155],
        [133, 138, 138, 133, 133, 142, 65, 146, 65, 151, 104],
        [104, 97, 152, 133, 133, 66, 66, 60, 146, 133, 133],
        [104, 138, 152, 152, 78, 66, 63, 142, 82, 133, 82],
        [151, 148, 148, 142, 133, 78, 78, 133, 143, 82, 143],
        [116, 151, 116, 133, 133, 116, 129, 129, 171, 171, 174],
        [116, 148, 116, 213, 189, 189, 201, 203, 129, 174, 234],
    ],
    dtype=np.uint8,
)


def _fixture(dtype: type[np.generic]) -> np.ndarray:
    if dtype == np.uint8:
        return HYBRID_FIXTURE.copy()
    return HYBRID_FIXTURE.astype(np.uint16) * 257


def _expected(values: np.ndarray, dtype: type[np.generic]) -> np.ndarray:
    if dtype == np.uint8:
        return values
    return values.astype(np.uint16) * 257


@pytest.mark.parametrize("dtype", (np.uint8, np.uint16))
@pytest.mark.parametrize("kernel_size", (3, 5, 7))
def test_hybrid_median_matches_imagej_at_edges_corners_and_interior(
    dtype: type[np.generic], kernel_size: int
) -> None:
    output = ImageJReplicator.hybrid_median_filter_2d(
        _fixture(dtype), kernel_size=kernel_size
    )

    assert output.dtype == dtype
    np.testing.assert_array_equal(output, _expected(EXPECTED_UINT8[kernel_size], dtype))


@pytest.mark.parametrize("dtype", (np.uint8, np.uint16))
def test_hybrid_median_repeated_passes_match_imagej(
    dtype: type[np.generic],
) -> None:
    output = ImageJReplicator.hybrid_median_filter_2d(
        _fixture(dtype), kernel_size=5, repetitions=2
    )

    np.testing.assert_array_equal(output, _expected(EXPECTED_REPEATED_UINT8, dtype))


@pytest.mark.parametrize(
    ("image", "expected_center"),
    (
        (
            np.array([[200, 200, 200], [100, 0, 100], [200, 200, 200]], dtype=np.uint8),
            100,
        ),
        (
            np.array([[100, 100, 100], [200, 0, 200], [100, 100, 100]], dtype=np.uint8),
            100,
        ),
        (
            np.array(
                [[200, 200, 200], [100, 150, 100], [200, 200, 200]], dtype=np.uint8
            ),
            150,
        ),
    ),
)
def test_hybrid_median_uses_plus_x_and_center_medians(
    image: np.ndarray, expected_center: int
) -> None:
    output = ImageJReplicator.hybrid_median_filter_2d(image, kernel_size=3)

    assert output[1, 1] == expected_center


def test_hybrid_imagej_wrapper_radius_two_matches_imagej_5x5() -> None:
    output = apply_median_filter(
        _fixture(np.uint16),
        filter_type="hybrid_imagej",
        radius=2,
        imagej_available=True,
    )

    assert output.dtype == np.uint16
    np.testing.assert_array_equal(output, _expected(EXPECTED_UINT8[5], np.uint16))
