import hashlib
from pathlib import Path

LEGACY_PATH = Path("mpips/engine/imager_pipeline/tiff_json_to_dcm.py")
CANONICAL_PATH = Path("mpips/conversion/tiff_json_to_dcm.py")
EXPECTED_SHA = "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0"


def test_canonical_converter_owns_the_protected_path() -> None:
    assert CANONICAL_PATH.exists()
    assert CANONICAL_PATH.is_file()
    assert not LEGACY_PATH.exists()

    with CANONICAL_PATH.open("rb") as converter_file:
        actual_sha = hashlib.file_digest(converter_file, "sha256").hexdigest()

    assert actual_sha == EXPECTED_SHA
