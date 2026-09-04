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
    "hybrid_imagej": "d8d28c579be200ec0811b040189252aa13d1db45278d240742df8a3e5a4e3757",
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
        [0, 65535, 1000, 2000, 3000, 4000, 5000],
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
    1: EXPECTED_AVAILABLE["hybrid_imagej"],
    2: EXPECTED_AVAILABLE["hybrid_imagej"],
    4: "d2ba39b0bcebd333d4019791a836ac0616627357c6961596012e4bc895df9329",
}

EXPECTED_CIRCULAR_I4A_HASHES = {
    ("uint8", 0.5): "5157cd80de4ea935cee4a786a516ff7f2041260c36fdb0ccb67fa682e82c0992",
    ("uint8", 1.0): "0fcd11108eedbad87ff6f194652203a9478e0e997024716a46db80748ef5bb3b",
    ("uint8", 1.5): "e72a4b5f10de3bd85f019d2cea69faec40726c470bc7217984ec849e92a52de7",
    ("uint8", 1.74): "e72a4b5f10de3bd85f019d2cea69faec40726c470bc7217984ec849e92a52de7",
    ("uint8", 1.75): "e72a4b5f10de3bd85f019d2cea69faec40726c470bc7217984ec849e92a52de7",
    ("uint8", 2.0): "89b7c92981dbe70477e5e60a21ef40d927ffeb270212b097699d401a74bef8c7",
    ("uint8", 2.5): "90e689333cf6fe68d803bd0f087ff303e67e23f6c821d0969b5bdd13dfd597b0",
    ("uint8", 2.84): "90e689333cf6fe68d803bd0f087ff303e67e23f6c821d0969b5bdd13dfd597b0",
    ("uint8", 2.85): "90e689333cf6fe68d803bd0f087ff303e67e23f6c821d0969b5bdd13dfd597b0",
    ("uint8", 3.0): "8e4e5923599608e8bbe2f7834794f8881475a32e6db199cd70ac50668634a6d1",
    ("uint16", 0.5): "591fb6b495566b159d3608336c22e84074ba41eaa092677626206f63eff29ad9",
    ("uint16", 1.0): "12cba42e4296eac0dd557f6a9106f1acba6073014076bae71f2701bb0504a6c5",
    ("uint16", 1.5): "b9a0490d260ecc63e135441b67389da4b756de8e4b1c053c3a9d02ffa6d37b05",
    (
        "uint16",
        1.74,
    ): "b9a0490d260ecc63e135441b67389da4b756de8e4b1c053c3a9d02ffa6d37b05",
    (
        "uint16",
        1.75,
    ): "b9a0490d260ecc63e135441b67389da4b756de8e4b1c053c3a9d02ffa6d37b05",
    ("uint16", 2.0): "af5398c57504217097440e2a525bb1b2026315083306d7f36a9d27430504a7a8",
    ("uint16", 2.5): "b2047c7fe0fcdfb4c1cdeaf540414771ac56938da77d73d280f3a96ad54ceec6",
    (
        "uint16",
        2.84,
    ): "b2047c7fe0fcdfb4c1cdeaf540414771ac56938da77d73d280f3a96ad54ceec6",
    (
        "uint16",
        2.85,
    ): "b2047c7fe0fcdfb4c1cdeaf540414771ac56938da77d73d280f3a96ad54ceec6",
    ("uint16", 3.0): "b65b95665a2d108ad31a02b7b66554b22f77a2418f880db0d6c97c90be64605c",
}


@pytest.mark.parametrize(
    "dtype,radius,expected_hash",
    [
        (dtype, radius, expected)
        for (dtype, radius), expected in EXPECTED_CIRCULAR_I4A_HASHES.items()
    ],
)
def test_circular_median_matches_accepted_i4a_matrix(
    dtype: str, radius: float, expected_hash: str
) -> None:
    values = np.array(
        [
            [9, 2, 7, 4, 6],
            [3, 8, 1, 5, 0],
            [6, 4, 9, 2, 7],
            [5, 1, 8, 3, 6],
            [0, 7, 2, 9, 4],
        ],
        dtype=np.uint8,
    )
    image = values if dtype == "uint8" else (values.astype(np.uint16) * 257)

    output = apply_median_filter(image, filter_type="circular_imagej", radius=radius)

    assert output.shape == image.shape
    assert output.dtype == image.dtype
    assert hashlib.sha256(output.tobytes()).hexdigest() == expected_hash


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
