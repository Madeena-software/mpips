# MPIPS Grabber Developer Integration Handoff Kit

Welcome to the MPIPS Grabber Developer Integration Handoff Kit. This documentation is prepared for external engineers developing and maintaining the local Grabber application that integrates with MPIPS.

> **CRITICAL BOUNDARY NOTICE**
> - The MPIPS offline runtime package is a **DEVELOPMENT CANDIDATE — NOT APPROVED FOR DISTRIBUTION**.
> - Redistribution, clinical use, or deployment to hospital production requires separate regulatory and institutional authorization (**G10 Release Gate: NOT RELEASED**).
> - Candidate `.release.json` metadata contains local development test sequence identifiers and is **unsigned**. Production releases require monotonic sequences signed with an approved Ed25519 key by the designated release owner.
> - Note: The existing Milestone 3 candidate package (`mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`) predates the Python subprocess adapter introduced in PR #18; the adapter script (`scripts/grabber_subprocess_adapter.py`) is delivered in the repository source tree and is designed to be copied directly into or vendored by the Grabber application.

---

## 1. Supported Platform & Runtime Prerequisites

* **Operating System**: **Ubuntu 24.04 LTS (`noble`)** (specifically tested and qualified on Ubuntu 24.04.2 LTS). Other Linux distributions or Ubuntu versions are currently unverified.
* **Architecture**: `x86_64`.
* **System Python**: CPython **3.12** pre-installed from Ubuntu distribution packages (`python3.12`, `python3.12-venv`).
* **glibc**: Minimum version **2.39**.
* **Network Isolation**: The runtime execution is completely offline. It starts no background HTTP daemon, Docker container, Redis, or Celery service, and makes zero network requests.

---

## 2. Offline Installation & Version Lifecycle

The MPIPS runtime is delivered as an offline wheelhouse bundle (`.tar.gz`) accompanied by candidate metadata (`.release.json`).

### Recommended Directory Layout on Grabber Host

```text
/opt/madeena/
├── versions/
│   └── 0.1.0-<commit>-ubuntu24.04-x86_64-py3.12/
│       ├── bundle/            # Extracted candidate wheelhouse & requirements.txt
│       └── runtime/           # Dedicated Python virtual environment
├── current -> versions/0.1.0-<commit>.../runtime/bin/mpips-runtime
├── calibrations/              # Read-only detector calibrations (independently approved)
└── clinical/                  # Private examination workspace (per-acquisition NPZ, manifest, DICOM)
```

### Unpacking & Offline Installation Command

```bash
# 1. Create a fresh virtual environment
python3.12 -m venv /opt/madeena/versions/<release-id>/runtime

# 2. Install completely offline from the local wheelhouse without accessing PyPI
/opt/madeena/versions/<release-id>/runtime/bin/python -m pip install \
    --no-index \
    --only-binary=:all: \
    --require-hashes \
    --find-links /opt/madeena/versions/<release-id>/bundle/wheels \
    -r /opt/madeena/versions/<release-id>/bundle/requirements.txt

# 3. Verify the installed runtime interface
/opt/madeena/versions/<release-id>/runtime/bin/mpips-runtime --version
```

---

## 3. Command-Line Interface (CLI) Contract

The executable boundary is `mpips-runtime`. Always invoke using explicit argument vectors (never use shell string interpolation).

```bash
mpips-runtime convert \
    --radiograph /path/to/radiograph.npz \
    --gain /path/to/gain.npz \
    --manifest /path/to/manifest.json \
    --calibration /path/to/calibration_directory \
    --output /path/to/destination.dcm
```

### Standard Output & Status Semantics
`mpips-runtime` emits **exactly one JSON object** on stdout.

#### Successful Conversion
```json
{
  "code": "OK",
  "interface_version": "1",
  "output_byte_size": 245760,
  "runtime_version": "0.1.0",
  "status": "ok"
}
```

#### Deterministic Exit Codes
| Exit Code | Code String | Meaning & Grabber Action |
|---|---|---|
| `0` | `OK` | Conversion succeeded. Consume and transfer output DICOM. |
| `2` | `INVALID_INPUT` | Bad manifest schema, dimension mismatch, or missing required tags. Do not auto-retry. |
| `3` | `INPUT_NOT_FOUND` | Specified input file or calibration folder does not exist. Verify filesystem paths. |
| `4` | `OUTPUT_EXISTS` | Destination file or symlink already exists. MPIPS will not overwrite. Choose a new destination. |
| `5` | `CONVERSION_TIMEOUT` | Conversion exceeded timeout limit. Preserve inputs and notify operator. |
| `6` | `IO_ERROR` | Permission denied or disk full. Check filesystem permissions. |
| `7` | `CONVERSION_FAILED` | Internal conversion algorithm failure. Preserve inputs for engineering diagnosis. |

---

## 4. Manifest & Input Contracts

### Manifest Schema (`MHCSManifest` v1.0)
The manifest must be a UTF-8 JSON file conforming to the `MHCSManifest` schema (`mpips/api/schemas/dicom.py`):
* `patient`:
  * `medical_record_number`: string (1–64 characters).
  * `name`: string or `{"full_name": "..."}`.
  * `sex`: Allowed values are exactly `"male"`, `"female"`, `"other"`, or `"unknown"`.
    * Mapping to DICOM `PatientSex`:
      * `"male"` $\to$ `"M"`
      * `"female"` $\to$ `"F"`
      * `"other"` $\to$ `"O"`
      * `"unknown"` $\to$ `""` (empty string)
  * `birth_date`: Optional ISO date (`"YYYY-MM-DD"`).
* `examination`: `encounter_id` (string), `performed_at` (ISO 8601 string with timezone offset).
* `capture`: `detector_type` (`"BED"` or `"TRX"`), `body_part_examined` (`"CHEST"`), `projection` (`"PA"` or `"AP"`), `detector_spacing` (`{"row_mm": float, "column_mm": float}`), `captured_at` (ISO 8601 string with timezone offset).
* `dicom`: `pixel_source` (`"CANONICAL_PRE_PRESENTATION"`), `pixel_intensity_relationship` (`"LIN"`), `pixel_intensity_relationship_sign` (`1`).

See complete reference in [grabber-manifest.synthetic.json](../examples/grabber-manifest.synthetic.json).

### NPZ Array Contract
* **Radiograph NPZ (`radiograph.npz`)**: Must contain `rawimage` (2D `uint16`), `id` (string), `gainid` (string matching gain NPZ), `cameraparams`, and `xrayparams` (`{"detectorMode": "BED"|"TRX"}`).
* **Gain NPZ (`gain.npz`)**: Must contain `rawimage` (2D `uint16`), `darkimage` (2D `uint16`), `id` (string matching `gainid`), `cameraparams`, and `xrayparams`.
* **Calibration Directory**: Must contain `metadata.json` (`validated: true`) and `remap.npz` (`map_x`, `map_y`).

---

## 5. Ready-to-Use Python Subprocess Adapter

For Python-based Grabber applications, an adapter is provided in the repository:
[scripts/grabber_subprocess_adapter.py](../../../scripts/grabber_subprocess_adapter.py).

### Safety Features
1. **Existing Output & Symlink Rejection**: Rejects output paths if they exist or are symlinks (including dangling symlinks) *before* path resolution, preserving the runtime's strict no-overwrite guarantees.
2. **Strict Response Verification**: Enforces single-line JSON output, verifies required keys (`interface_version`, `runtime_version`, `status`, `code`), checks `interface_version == "1"`, and ensures status/exit code consistency.
3. **Information Shielding**: Exceptions sanitize error messages; they never leak raw stdout or patient metadata into exception strings or logs.
4. **Subprocess Timeout & Termination**: Enforces timeout limits and terminates timed-out child processes cleanly via `proc.kill()` and `proc.wait()`.

> **Process Lifecycle Limitation Note**:
> While `MPIPSSubprocessAdapter` terminates the direct `mpips-runtime` process on timeout, `mpips-runtime` itself launches an internal worker script (`python -m mpips.workflows.imager_pipeline.file_runner`). In rare instances where the parent process is abruptly terminated, the detached descendant worker could temporarily persist until its own internal CPU/timeout limits expire (`MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS`, default 300s). Callers running on Linux can use session groups (`os.setsid`) or `prctl(PR_SET_PDEATHSIG)` if aggressive descendant tree termination is required.

### Quick Usage Example
```python
from pathlib import Path
from scripts.grabber_subprocess_adapter import (
    MPIPSSubprocessAdapter,
    MPIPSRuntimeError,
    MPIPSInvalidInputError,
    MPIPSOutputExistsError,
)

# 1. Initialize adapter with runtime binary
adapter = MPIPSSubprocessAdapter("/opt/madeena/current")

# 2. Query runtime version
info = adapter.check_version()
print(f"Connected to MPIPS Runtime v{info.runtime_version} (Interface {info.interface_version})")

# 3. Perform conversion
try:
    result = adapter.convert(
        radiograph="/opt/madeena/clinical/exam-001/radiograph.npz",
        gain="/opt/madeena/clinical/exam-001/gain.npz",
        manifest="/opt/madeena/clinical/exam-001/manifest.json",
        calibration="/opt/madeena/calibrations/trx-detector-01",
        output="/opt/madeena/clinical/exam-001/exam-001.dcm",
        timeout=300.0,
    )
    print(f"DICOM generated successfully: {result.output_path} ({result.output_byte_size} bytes)")
except MPIPSOutputExistsError as exc:
    print(f"Output path conflict (existing file or symlink): {exc}")
except MPIPSInvalidInputError as exc:
    print(f"Input validation rejected by MPIPS: {exc.response.get('code')}")
except MPIPSRuntimeError as exc:
    print(f"Conversion failed (exit code {exc.exit_code}): {exc}")
```

---

## 6. Synthetic Integration Acceptance Checklist

Prior to requesting clinical integration testing or deployment review, external developers must complete this checklist using synthetic test fixtures:

- [ ] **1. Python & OS Validation**:
  - [ ] Confirmed Ubuntu 24.04 LTS `x86_64` host.
  - [ ] Verified Python 3.12 (`python3 --version`).
- [ ] **2. Offline Package Verification**:
  - [ ] Verified SHA-256 and byte size against companion `.release.json`.
  - [ ] Installed into clean venv without internet connection (`--no-index`).
  - [ ] Confirmed `mpips-runtime --version` returns `status: "ok"` and `interface_version: "1"`.
- [ ] **3. Synthetic BED Qualification**:
  - [ ] Generated synthetic BED inputs (`48x64` uint16).
  - [ ] Invoked conversion via argument vector.
  - [ ] Verified output DICOM exists with mode `0600`.
  - [ ] Verified DICOM attributes: `Modality == "DX"`, `PhotometricInterpretation == "MONOCHROME2"`, `BitsAllocated == 16`.
- [ ] **4. Synthetic TRX Qualification**:
  - [ ] Generated synthetic TRX inputs (`48x64` uint16, resulting in `64x48` rotated output).
  - [ ] Verified clockwise 90-degree canonical TRX transformation in DICOM output.
- [ ] **5. Error Handling & Edge Cases**:
  - [ ] Tested duplicate output path: Verified exit code `4` (`OUTPUT_EXISTS`) and preservation of existing file.
  - [ ] Tested dangling symlink output path: Verified rejection with exit code `4` (`OUTPUT_EXISTS`) without following the link.
  - [ ] Tested missing gain NPZ: Verified exit code `3` (`INPUT_NOT_FOUND`).
  - [ ] Tested malformed manifest JSON: Verified exit code `2` (`INVALID_INPUT`).
  - [ ] Tested process timeout: Verified process termination and cleanup of temporary staging files.
- [ ] **6. Privacy & Security Audit**:
  - [ ] Confirmed no patient names, medical record numbers, or birthdates appear in error logs or stdout.
  - [ ] Confirmed calibration directory is kept read-only and separate from clinical data storage.
