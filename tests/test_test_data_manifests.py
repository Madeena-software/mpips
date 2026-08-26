import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
TEST_DATA_DIR = ROOT / "artifacts" / "test-data"


def test_real_thorax_trx_manifest_valid():
    manifest_path = TEST_DATA_DIR / "real-thorax-trx-da5277082.json"
    assert manifest_path.is_file(), f"Manifest missing: {manifest_path}"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"radiograph", "gain", "expected"}

    rad = data["radiograph"]
    assert rad["file_id"] == "1ocIGsYS6RHIurhRuOwJCzSHTv-6STc_m"
    assert rad["filename"] == "TRX_1787727857802.npz"
    assert rad["size"] == 71253472
    assert re.fullmatch(r"[0-9a-f]{64}", rad["sha256"])
    assert (
        rad["sha256"]
        == "954fee2669755fce140b600d4b7d6a67f5a8a141f5a639a0a82317d973963cf2"
    )

    gain = data["gain"]
    assert gain["file_id"] == "1kI99se2CjzCgo4qInMEGUuJ-ZJZE3iQY"
    assert gain["filename"] == "TRX_1787726609597.npz"
    assert gain["size"] == 17190412
    assert re.fullmatch(r"[0-9a-f]{64}", gain["sha256"])
    assert (
        gain["sha256"]
        == "38918e436e5329e28b08c844e8df3766a1ab83a1fc3135c83df56370c480b2a9"
    )

    exp = data["expected"]
    assert exp["detector_mode"] == "TRX"
    assert exp["external_detector_type"] == "THORAX"
    assert exp["image_shape"] == [3000, 4096]
    assert exp["camera_serial"] == "DA5277082"
    assert exp["gain_id"] == "1787726609597"
