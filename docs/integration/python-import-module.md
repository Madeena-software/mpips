# MPIPS NPZ-to-DICOM Python Library Integration Guide

**Repository:** [MPIPS](https://github.com/Madeena-software/mpips)  
**Target Consumer:** Python library consumers, data processing scripts, automated pipelines  
**Public Surface:** `convert_npz_to_dicom`  
**Contract Status:** Authoritative Library Integration Guide  

---

## 1. Overview

MPIPS provides a supported, local Python library interface for converting raw NPZ radiographs and gain calibrations into standard, validated DICOM files (`DX` modality) without requiring a running HTTP server (FastAPI), message queue (Celery), cache (Redis), or external background daemon.

---

## 2. Installation via Direct Git Distribution

Users can install MPIPS directly from public GitHub using `pip` or `uv` targeting an immutable commit SHA, without manually cloning the repository.

### Bare Installation Sufficiency

Clean-environment testing confirms that a **bare installation** (without optional extras) satisfies all runtime dependencies for NPZ-to-DICOM conversion. The base dependencies (`numpy`, `opencv-python-headless`, `pydantic`, `scipy`, `scikit-image`, `PyWavelets`, `pydicom`, `python-multipart`) provide all required scientific processing and DICOM formatting capabilities.

### Installation Commands

#### Primary: Using `pip`

```bash
pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
```

#### Secondary: Using `uv`

```bash
uv pip install "git+https://github.com/Madeena-software/mpips.git@<commit-sha>"
```

*(Replace `<commit-sha>` with the exact immutable commit SHA).*

---

## 3. Python Import Surface

### Mandatory Acceptance Interface

The primary supported import entrypoint is at the root package level:

```python
from mpips import convert_npz_to_dicom
```

### Optional Convenience Interface

For consumers importing directly from the conversion subpackage, the function is also exposed from:

```python
from mpips.conversion import convert_npz_to_dicom
```

Both imports reference the exact same underlying function.

---

## 4. API Reference

### Function Signature

```python
from pathlib import Path
from typing import Any, Dict, Union
from mpips.api.schemas.dicom import MHCSManifest, ResolvedMHCSManifest

def convert_npz_to_dicom(
    radiograph_npz_path: Union[str, Path],
    gain_npz_path: Union[str, Path],
    manifest: Union[str, Path, Dict[str, Any], MHCSManifest, ResolvedMHCSManifest],
    output_dicom_path: Union[str, Path],
    *,
    calibration_dir: Union[str, Path, None] = None,
) -> Path: ...
```

### Parameters

- **`radiograph_npz_path`** (`str | Path`): Path to the radiograph NPZ file.
- **`gain_npz_path`** (`str | Path`): Path to the gain calibration NPZ file.
- **`manifest`** (`str | Path | dict | MHCSManifest | ResolvedMHCSManifest`): Manifest metadata. Can be provided as:
  - A filesystem path to a JSON manifest file (`str` or `Path`)
  - A raw JSON string (`str` starting with `{`)
  - A parsed Python dictionary (`dict`)
  - A validated `MHCSManifest` or `ResolvedMHCSManifest` instance
- **`output_dicom_path`** (`str | Path`): Target destination path where the validated DICOM file will be written. Parent directories will be created if they do not exist.
- **`calibration_dir`** (`str | Path | None`, optional): Path to calibration directory containing `remap.npz` and `metadata.json`. If omitted, resolves via environment variables `MPIPS_CALIBRATION_ARTIFACT_DIR` or `MPIPS_ARTIFACT_ROOT`.

### Return Value

- **`Path`**: The resolved filesystem `Path` to the created DICOM file.

### Exceptions

The library interface completely decouples from web-framework exceptions (`fastapi.HTTPException`). Callers receive standard Python exceptions:

- **`FileNotFoundError`**: Raised if radiograph NPZ, gain NPZ, manifest file, or calibration directory does not exist.
- **`ValueError`**: Raised if manifest schema is invalid, JSON is malformed, or NPZ data fails descriptor/validation checks.
- **`TimeoutError`**: Raised if isolated subprocess execution exceeds configured timeout.
- **`ConversionError`** (subclass of `RuntimeError`): Raised if conversion or validation fails during execution.

---

## 5. Usage Example

```python
from pathlib import Path
from mpips import convert_npz_to_dicom, ConversionError

radiograph_file = Path("data/capture.npz")
gain_file = Path("data/gain.npz")
output_dicom = Path("output/study_result.dcm")

manifest_data = {
    "manifest_version": "1.0",
    "examination": {
        "study_description": "Chest Radiography",
        "accession_number": "ACC12345",
    },
    "patient": {
        "medical_record_number": "MRN-0012345",
        "name": {"full_name": "Jane Doe", "family_name": "Doe"},
        "sex": "female",
        "birth_date": "1990-05-12",
    },
    "capture": {
        "detector_type": "THORAX",
        "body_part_examined": "CHEST",
        "laterality": "U",
        "projection": "PA",
        "detector_spacing": {"row_mm": 0.150, "column_mm": 0.160},
        "view_code_sequence": [
            {
                "code_value": "272479007",
                "coding_scheme_designator": "SCT",
                "code_meaning": "postero-anterior",
            }
        ],
    },
    "dicom": {
        "pixel_source": "CANONICAL_PRE_PRESENTATION",
        "pixel_intensity_relationship": "LIN",
        "pixel_intensity_relationship_sign": 1,
    },
}

try:
    dcm_path = convert_npz_to_dicom(
        radiograph_npz_path=radiograph_file,
        gain_npz_path=gain_file,
        manifest=manifest_data,
        output_dicom_path=output_dicom,
    )
    print(f"DICOM generated successfully: {dcm_path}")
except ConversionError as err:
    print(f"Conversion failed: {err}")
```

---

## 6. Clinical & DICOM Invariants

All DICOM files produced by `convert_npz_to_dicom` enforce clinical standards and repository invariants:
- **Modality**: `DX` (Digital Radiography).
- **SOP Class UID**: `1.2.840.10008.5.1.4.1.1.1.1.1` (Digital X-Ray Image Storage - For Presentation).
- **Bit Depth**: 16-bit unsigned integers (`BitsAllocated == 16`, `BitsStored == 16`, `HighBit == 15`, `PixelRepresentation == 0`).
- **Photometric Interpretation**: `MONOCHROME2`.
- **TRX Orientation**: In TRX mode, canonical clockwise rotation and threshold bypass invariants are strictly applied.
- **Readability**: Fully readable by standard DICOM parsers (`pydicom.dcmread`).
