import hashlib
from pathlib import Path

LEGACY_PATH = Path("mpips/engine/imager_pipeline/tiff_json_to_dcm.py")
CANONICAL_PATH = Path("mpips/conversion/tiff_json_to_dcm.py")
EXPECTED_SHA = "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0"


def test_converter_exists_at_one_authorized_path_with_exact_hash() -> None:
    existing_paths = [path for path in (LEGACY_PATH, CANONICAL_PATH) if path.exists()]

    assert len(existing_paths) == 1
    converter_path = existing_paths[0]
    assert converter_path.is_file()

    with converter_path.open("rb") as converter_file:
        actual_sha = hashlib.file_digest(converter_file, "sha256").hexdigest()

    assert actual_sha == EXPECTED_SHA
