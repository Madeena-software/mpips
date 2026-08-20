import hashlib
import subprocess
import sys
import textwrap

import numpy as np
import pytest

import mpips.processing as processing
import mpips.processing.radiography as radiography
from mpips.processing.filtering import apply_median_filter


def _median_fixture() -> np.ndarray:
    return np.array(
        [
            [0, 65535, 1000, 2000, 3000, 4000, 5000],
            [6000, 7000, 8000, 9000, 10000, 11000, 12000],
            [13000, 14000, 15000, 16000, 17000, 18000, 19000],
            [20000, 21000, 22000, 0, 24000, 25000, 26000],
            [27000, 28000, 29000, 30000, 31000, 32000, 33000],
            [34000, 35000, 36000, 37000, 38000, 39000, 40000],
            [41000, 42000, 43000, 44000, 45000, 46000, 65535],
        ],
        dtype=np.uint16,
    )


EXPECTED_AVAILABLE = {
    "standard": "c7ed75771093ef51dc4d401aa7a4a0570f725ee469e96bf01470b34123a6e513",
    "bilateral": "2a30a566212096a89ae4a3305c97bdbb61248dd758d5531480cdd231a5b338eb",
    "adaptive": "6c2123d518f74f20781ff4bb77becc831714a5a9ff583f53d43177c0dd0a064b",
    "nlm": "c7ed75771093ef51dc4d401aa7a4a0570f725ee469e96bf01470b34123a6e513",
    "morphological": "e84974037c3f41ff03ffc60a849554f0860d47e81892fa214cfea787f34ebaed",
    "hybrid_imagej": "e4e1a53a3d8d57fbdd26210d3bbe6513d11a966a89b56b31989a8bab1eb6026c",
    "circular_imagej": (
        "bac29ff9269813e7aa99732d295db3b09f2944b85b9f170ab99d69941dee36ff"
    ),
}

EXPECTED_AVAILABLE_RADIUS = {
    "standard": 1,
    "bilateral": 1,
    "adaptive": 1,
    "nlm": 1,
    "morphological": 1,
    "hybrid_imagej": 2,
    "circular_imagej": 2,
}

EXPECTED_HYBRID_DEFAULT = np.array(
    [
        [0, 7000, 2000, 3000, 3000, 4000, 5000],
        [6000, 7000, 8000, 9000, 10000, 11000, 12000],
        [13000, 14000, 15000, 16000, 17000, 18000, 19000],
        [20000, 21000, 22000, 17000, 24000, 25000, 26000],
        [27000, 28000, 29000, 30000, 31000, 32000, 33000],
        [34000, 35000, 36000, 37000, 38000, 39000, 40000],
        [41000, 42000, 43000, 44000, 45000, 46000, 65535],
    ],
    dtype=np.uint16,
)

EXPECTED_HYBRID_RADIUS_HASHES = {
    1: "bae3f3ae5bd790f662c82921394859461d4099969010b9b4f4e6481d5fe33fc6",
    2: EXPECTED_AVAILABLE["hybrid_imagej"],
    4: "57924d65b5e845ee133b87e177d031ee089857f6148d9b8e4697e75c43399afb",
}


def test_filtering_import_is_processing_and_service_safe() -> None:
    script = textwrap.dedent("""
        import sys

        from mpips.processing.filtering import apply_median_filter

        forbidden = {
            "boto3",
            "celery",
            "fastapi",
            "mpips.api",
            "mpips.conversion",
            "mpips.engine",
            "mpips.engine",
            "mpips.pipelines",
            "mpips.worker",
            "mpips.workflows",
        }
        loaded = forbidden.intersection(sys.modules)
        assert not loaded, sorted(loaded)
        assert callable(apply_median_filter)
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_filtering_has_one_canonical_owner() -> None:
    assert apply_median_filter.__module__ == "mpips.processing.filtering"
    assert callable(radiography.apply_median_filter)
    assert callable(processing.apply_median_filter)
    assert callable(processing.hybrid_median_filter)


@pytest.mark.parametrize("filter_type", tuple(EXPECTED_AVAILABLE))
def test_supported_filters_match_historical_available_goldens(
    filter_type: str,
) -> None:
    output = apply_median_filter(
        _median_fixture(),
        filter_type=filter_type,
        radius=EXPECTED_AVAILABLE_RADIUS[filter_type],
        imagej_available=True,
    )

    assert output.shape == (7, 7)
    assert output.dtype == np.uint16
    assert (
        hashlib.sha256(output.tobytes()).hexdigest() == EXPECTED_AVAILABLE[filter_type]
    )


def test_default_hybrid_imagej_matches_historical_pixels() -> None:
    output = apply_median_filter(_median_fixture())

    assert output.shape == EXPECTED_HYBRID_DEFAULT.shape
    assert output.dtype == np.uint16
    assert output.min() == 0
    assert output.max() == 65535
    np.testing.assert_array_equal(output, EXPECTED_HYBRID_DEFAULT)


@pytest.mark.parametrize(
    "radius,expected_hash", tuple(EXPECTED_HYBRID_RADIUS_HASHES.items())
)
def test_hybrid_radius_behavior_matches_historical_hash(
    radius: int, expected_hash: str
) -> None:
    output = apply_median_filter(
        _median_fixture(), filter_type="hybrid_imagej", radius=radius
    )

    assert output.shape == (7, 7)
    assert output.dtype == np.uint16
    assert hashlib.sha256(output.tobytes()).hexdigest() == expected_hash


def test_imagej_disabled_fallbacks_match_historical_behavior() -> None:
    image = _median_fixture()
    adaptive = apply_median_filter(
        image, filter_type="adaptive", radius=2, imagej_available=False
    )
    standard = apply_median_filter(
        image, filter_type="standard", radius=2, imagej_available=False
    )

    hybrid = apply_median_filter(
        image, filter_type="hybrid_imagej", radius=2, imagej_available=False
    )
    circular = apply_median_filter(
        image, filter_type="circular_imagej", radius=2, imagej_available=False
    )

    np.testing.assert_array_equal(hybrid, adaptive)
    np.testing.assert_array_equal(circular, standard)
    assert hashlib.sha256(hybrid.tobytes()).hexdigest() == (
        "6c2123d518f74f20781ff4bb77becc831714a5a9ff583f53d43177c0dd0a064b"
    )
    assert hashlib.sha256(circular.tobytes()).hexdigest() == (
        "cf0576217ef3d2804082df8f9860f92cfdc5654dfa17e47e83f262a2aa78f313"
    )


def test_unknown_filter_falls_back_to_hybrid_imagej() -> None:
    image = _median_fixture()
    unknown = apply_median_filter(
        image, filter_type="unknown", radius=2, imagej_available=True
    )
    hybrid = apply_median_filter(
        image, filter_type="hybrid_imagej", radius=2, imagej_available=True
    )

    np.testing.assert_array_equal(unknown, hybrid)


@pytest.mark.parametrize("filter_type", ("standard", "hybrid_imagej"))
@pytest.mark.parametrize("imagej_available", (True, False))
def test_public_median_wrappers_remain_compatible(
    filter_type: str, imagej_available: bool
) -> None:
    image = _median_fixture()

    np.testing.assert_array_equal(
        processing.apply_median_filter(
            image,
            filter_type,
            2,
            imagej_available=imagej_available,
        ),
        apply_median_filter(
            image,
            filter_type,
            2,
            imagej_available=imagej_available,
        ),
    )
    if filter_type == "hybrid_imagej" and imagej_available:
        np.testing.assert_array_equal(
            processing.hybrid_median_filter(image, radius=2),
            apply_median_filter(
                image,
                "hybrid_imagej",
                2,
                imagej_available=True,
            ),
        )
