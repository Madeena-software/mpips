# MPIPS Grabber Developer Integration Handoff Kit

Welcome to the MPIPS Grabber Developer Integration Handoff Kit. This documentation is prepared for external engineers developing and maintaining the local Grabber application that integrates with MPIPS.

> **CRITICAL BOUNDARY NOTICE**
> - The MPIPS offline runtime package is a **DEVELOPMENT CANDIDATE — NOT APPROVED FOR DISTRIBUTION**.
> - Redistribution, clinical use, or deployment to hospital production requires separate regulatory and institutional authorization (**G10 Release Gate: NOT RELEASED**).
> - Candidate `.release.json` metadata contains local development test sequence identifiers and is **unsigned**. Production releases require monotonic sequences signed with an approved Ed25519 key by the designated release owner.
> - Note: The existing Milestone 3 candidate package (`mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`) predates the Python subprocess adapter introduced in PR #18; the adapter script (`scripts/grabber_subprocess_adapter.py`) is delivered in the repository source tree and is designed to be copied directly into or vendored by the Grabber application.

---

## 1. Interface Separation Overview: Interface `1` vs. Interface `2-experimental`

MPIPS maintains two distinct runtime integration interfaces. **Do not mix their CLI flags or installation procedures.**

| Dimension | Legacy Interface `1` (Wheelhouse Bundle) | Standalone Interface `2-experimental` (`mpips-runtime.bin`) |
|---|---|---|
| **Artifact Format** | Offline Python wheelhouse archive (`.tar.gz`) | Single-file self-contained Linux ELF executable (`mpips-runtime.bin`) |
| **System Python Required?** | **Yes** (`python3.12` and `python3.12-venv` required on host) | **No** (Python-free standalone binary; embeds CPython 3.12 and native libraries) |
| **Calibration Argument** | **Required** (`--calibration /path/to/calibration_dir`) | **Forbidden** (omitted; passing `--calibration` fails closed with exit code `2` `INVALID_INPUT`) |
| **Detector Calibration Source** | External read-only calibration directory on host | Embedded inside the verified ELF (`GOTRI-TRX-001` real TRX + synthetic dev BED) |
| **Per-Acquisition Gain NPZ** | Required (`--gain /path/to/gain.npz`) | Required (`--gain /path/to/gain.npz`) |
| **`--version` JSON Output** | `{"code": "OK", "interface_version": "1", "runtime_version": "0.1.0", "status": "ok"}` | `{"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}` |
| **Grabber Invocation** | Direct CLI argv or optional Python `MPIPSSubprocessAdapter` | Direct CLI argv from any language (C++/Go/Rust/C#/Python) or optional Python `MPIPSSubprocessAdapter` |

---

## 2. Standalone Interface `2-experimental` (`mpips-runtime.bin`)

### 2.1 Supported Platform & Ubuntu 24.04 Compatibility Evidence

* **Operating System**: **Ubuntu 24.04 LTS (`noble`)** `x86_64` (`Ubuntu GLIBC 2.39-0ubuntu8.4` / `glibc 2.39`).
* **Maximum Required GLIBC Symbol Version**: `GLIBC_2.14` (observed ELF symbol version set via `objdump -T` / `readelf -V`: `GLIBC_2.2.5`, `GLIBC_2.3`, `GLIBC_2.3.4`, `GLIBC_2.4`, `GLIBC_2.7`, `GLIBC_2.14`).
* **Host Shared Library Dependencies (`ldd`)**: Only standard base OS libraries (`libc.so.6`, `libdl.so.2`, `libpthread.so.0`, `libz.so.1`, `ld-linux-x86-64.so.2`).
* **Zero External Python Dependency**: Confirmed via clean Ubuntu 24.04 container qualification and scrubbed-environment execution (`/usr/bin/env -i PATH=/usr/bin:/bin ./mpips-runtime.bin --version` and `convert` with no `PYTHON*` variables or system Python required).
* **Verified Candidate Artifact Identity**:
  * **Filename**: `mpips-runtime.bin`
  * **Exact Size**: `241,288,024` bytes (~230.1 MiB)
  * **Exact SHA-256**: `189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`
* **Qualification Boundary**: Qualified in isolated container and local test environments (`EV-STANDALONE-REAL-TRX-001`). Physical bare-metal hospital Grabber hardware qualification remains pending. Gate **G10 remains NOT RELEASED**.

### 2.2 Embedded Detector Calibration & Supported Profiles

Interface `2-experimental` embeds detector geometric calibration directly inside the ELF payload and verifies SHA-256 integrity inside the worker subprocess before processing:

1. **Designated Real TRX Profile (`GOTRI-TRX-001`)**:
   * **Classification**: `REAL_GEOMETRIC_CALIBRATION` (`LOCAL_REAL_TRX_ACCEPTANCE`)
   * **Detector Mode**: `TRX`
   * **Camera Serial**: `DA5234480` (checked fail-closed against radiograph `cameraparams.serialNumber` / `cameraSerial`)
   * **Camera Model**: `MV-CH120-10UM`
   * **Required Input Array Shape**: `3000 x 4096` (`uint16`)
   * **Output DICOM Pixel Array Shape**: `4096 x 3000` (`uint16`, 90-degree clockwise canonical TRX orientation)
   * **Calibration Fingerprint**: `606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d`
   * **Embedded Remap SHA-256**: `32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893`
   * **Source Archive SHA-256**: `2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556`
2. **Embedded Synthetic BED Profile (`SYNTHETIC-EMBEDDED-BED-CALIBRATION-V1`)**:
   * **Classification**: `SYNTHETIC_DEVELOPMENT_ONLY` (non-clinical synthetic regression fixture only; `48 x 64` `uint16`, remap SHA-256 `57749f83ba9bd0704347a0c41cd4e454ed87829c00314f4948b3e9f03d2a7ddc`).
   * **Real BED Hardware**: A production real BED geometric calibration profile is not yet embedded in this candidate.
3. **Fail-Closed Rules**:
   * Per-acquisition `--gain /path/to/gain.npz` remains mandatory for every conversion.
   * Passing `--calibration` to `mpips-runtime.bin` (`2-experimental`) is strictly rejected with exit code `2` (`INVALID_INPUT`).
   * Any mismatch in `detectorMode`, `cameraSerial` (`DA5234480`), or input dimensions (`3000 x 4096` for TRX) fails closed before image processing.

### 2.3 Direct Python-Free Executable Invocation vs. Optional Python Adapter

* **Python-Free Standalone Binary (`mpips-runtime.bin`)**:
  The Grabber application does **not** need to be written in Python and does **not** need Python installed on the host to run `mpips-runtime.bin`. Any Grabber runtime (C++, C#, Rust, Go, Java, Node.js, or Python) can invoke `mpips-runtime.bin` directly via `execve` / `posix_spawn` argument vectors:
  ```bash
  # Version & interface self-check (no Python required on host)
  /opt/madeena/current/mpips-runtime.bin --version

  # Standalone conversion (NOTE: NO --calibration flag)
  /opt/madeena/current/mpips-runtime.bin convert \
      --radiograph /opt/madeena/clinical/exam-001/radiograph.npz \
      --gain /opt/madeena/clinical/exam-001/gain.npz \
      --manifest /opt/madeena/clinical/exam-001/manifest.json \
      --output /opt/madeena/clinical/exam-001/exam-001.dcm
  ```
* **Optional Python Subprocess Adapter (`scripts/grabber_subprocess_adapter.py`)**:
  Provided only as a convenience helper if the Grabber application (or its local integration harness) uses Python. `MPIPSSubprocessAdapter` supports both `"1"` and `"2-experimental"` via `negotiate_interface()` / `check_version()`, automatically omitting `--calibration` when talking to `"2-experimental"` and rejecting any caller attempt to pass `calibration=...` under `"2-experimental"`.

### 2.4 JSON Standard Output, Exit Codes & DICOM Output Contract (`2-experimental`)

* **`--version` Output (Exit Code `0`)**:
  ```json
  {"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}
  ```
* **Successful `convert` Output (Exit Code `0`)**:
  ```json
  {"code": "OK", "interface_version": "2-experimental", "output_byte_size": 24577268, "runtime_version": "0.1.0", "status": "ok"}
  ```
* **Error Output (Non-Zero Exit Code)**:
  ```json
  {"code": "INVALID_INPUT", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "error"}
  ```
* **DICOM Output Guarantees**:
  * Atomically hard-linked to `--output` only after full validation; never overwrites an existing file or symlink (`exit 4` `OUTPUT_EXISTS`).
  * Created with strict owner-only permissions `0600` (`-rw-------`).
  * Conforms to Digital X-Ray (`Modality = "DX"`, `SOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1.1"`, `PhotometricInterpretation = "MONOCHROME2"`, `BitsAllocated = 16`, `PixelRepresentation = 0`, zero private tags).

---

## 3. Legacy Interface `1` (Offline Python Wheelhouse Bundle)

* **Operating System & Python**: Ubuntu 24.04 LTS `x86_64` with system CPython **3.12** (`python3.12`, `python3.12-venv`) and `glibc >= 2.39`.
* **Network Isolation**: Completely offline execution; starts no daemon and makes zero network requests.

### Recommended Directory Layout on Grabber Host (Legacy Interface `1`)

```text
/opt/madeena/
├── versions/
│   └── 0.1.0-<commit>-ubuntu24.04-x86_64-py3.12/
│       ├── bundle/            # Extracted candidate wheelhouse & requirements.txt
│       └── runtime/           # Dedicated Python virtual environment
├── current -> versions/0.1.0-<commit>.../runtime/bin/mpips-runtime
├── calibrations/              # Read-only detector calibrations (required by Interface 1)
└── clinical/                  # Private examination workspace (per-acquisition NPZ, manifest, DICOM)
```

### Unpacking & Offline Installation Command (Legacy Interface `1`)

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

# 3. Verify the installed runtime interface (returns interface_version: "1")
/opt/madeena/versions/<release-id>/runtime/bin/mpips-runtime --version
```

### Legacy Interface `1` CLI Invocation (Requires `--calibration`)

```bash
mpips-runtime convert \
    --radiograph /path/to/radiograph.npz \
    --gain /path/to/gain.npz \
    --manifest /path/to/manifest.json \
    --calibration /path/to/calibration_directory \
    --output /path/to/destination.dcm
```

### Deterministic Exit Codes (Shared Across Interfaces `1` and `2-experimental`)
| Exit Code | Code String | Meaning & Grabber Action |
|---|---|---|
| `0` | `OK` | Conversion succeeded. Consume and transfer output DICOM. |
| `2` | `INVALID_INPUT` | Bad manifest schema, dimension/serial mismatch, missing required tags, or forbidden `--calibration` in `2-experimental`. Do not auto-retry. |
| `3` | `INPUT_NOT_FOUND` | Specified input file (or calibration folder in Interface `1`) does not exist. Verify filesystem paths. |
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

## 5. Optional Python Subprocess Adapter (`scripts/grabber_subprocess_adapter.py`)

For Python-based Grabber applications, an optional adapter is provided in the repository:
[scripts/grabber_subprocess_adapter.py](../../../scripts/grabber_subprocess_adapter.py).
Non-Python Grabber applications should invoke `mpips-runtime.bin` directly via `execve` / `posix_spawn` argument vectors as shown in Section 2.3.

### Safety Features
1. **Existing Output & Symlink Rejection**: Rejects output paths if they exist or are symlinks (including dangling symlinks) *before* path resolution, preserving the runtime's strict no-overwrite guarantees.
2. **Version-Aware Interface Negotiation**: Enforces single-line JSON output, verifies required keys (`interface_version`, `runtime_version`, `status`, `code`), supports both `interface_version == "1"` (requires `calibration=...`) and `interface_version == "2-experimental"` (forbids `calibration=...`), and ensures status/exit code consistency.
3. **Information Shielding**: Exceptions sanitize error messages; they never leak raw stdout or patient metadata into exception strings or logs.
4. **Subprocess Timeout & Termination**: Enforces timeout limits and terminates timed-out child processes cleanly via `proc.kill()` and `proc.wait()`.

> **Process Lifecycle Limitation Note**:
> While `MPIPSSubprocessAdapter` terminates the direct `mpips-runtime` process on timeout, `mpips-runtime` launches an internal worker child process (`_internal_worker` in frozen ELF mode or `python -m mpips.workflows.imager_pipeline.file_runner` in legacy wheelhouse mode) under process-group supervision and `RLIMIT_CPU` / `MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS` (default 300s). Callers running on Linux can also use session groups (`os.setsid`) or `prctl(PR_SET_PDEATHSIG)` if aggressive descendant tree termination is required.

### Quick Usage Example (`2-experimental` vs. Legacy `1`)
```python
from scripts.grabber_subprocess_adapter import (
    MPIPSSubprocessAdapter,
    MPIPSRuntimeError,
    MPIPSInvalidInputError,
    MPIPSOutputExistsError,
)

# 1. Initialize adapter with standalone ELF (2-experimental) or legacy venv binary (1)
adapter = MPIPSSubprocessAdapter("/opt/madeena/current/mpips-runtime.bin")

# 2. Query runtime version & interface
info = adapter.check_version()
print(f"Connected to MPIPS Runtime v{info.runtime_version} (Interface {info.interface_version})")

# 3a. Standalone Interface 2-experimental conversion (NO calibration argument)
if info.interface_version == "2-experimental":
    result = adapter.convert(
        radiograph="/opt/madeena/clinical/exam-001/radiograph.npz",
        gain="/opt/madeena/clinical/exam-001/gain.npz",
        manifest="/opt/madeena/clinical/exam-001/manifest.json",
        output="/opt/madeena/clinical/exam-001/exam-001.dcm",
        timeout=300.0,
    )
# 3b. Legacy Interface 1 conversion (requires external calibration directory)
else:
    result = adapter.convert(
        radiograph="/opt/madeena/clinical/exam-001/radiograph.npz",
        gain="/opt/madeena/clinical/exam-001/gain.npz",
        manifest="/opt/madeena/clinical/exam-001/manifest.json",
        calibration="/opt/madeena/calibrations/trx-detector-01",
        output="/opt/madeena/clinical/exam-001/exam-001.dcm",
        timeout=300.0,
    )
```

---

## 6. Synthetic Integration Acceptance Checklist

Prior to requesting clinical integration testing or deployment review, external developers must complete this checklist using synthetic test fixtures:

- [ ] **1. OS & Runtime Validation**:
  - [ ] Confirmed Ubuntu 24.04 LTS (`noble`) `x86_64` host (`glibc >= 2.39`).
  - [ ] For Interface `2-experimental`: Verified `mpips-runtime.bin` runs without system Python (`env -i PATH=/usr/bin:/bin ./mpips-runtime.bin --version`).
  - [ ] For Legacy Interface `1`: Verified Python 3.12 (`python3.12 --version`) and offline wheelhouse installation (`--no-index --require-hashes`).
- [ ] **2. Artifact & Signature Verification**:
  - [ ] Verified Ed25519 signature (`64` bytes) over canonical `signed_metadata_b64` and cross-checked all outer manifest fields *before* sequence comparison or download.
  - [ ] Verified exact SHA-256 (`189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) and byte size (`241,288,024` bytes) of `mpips-runtime.bin`.
- [ ] **3. Synthetic BED Qualification**:
  - [ ] Generated synthetic BED inputs (`48x64` uint16).
  - [ ] Invoked conversion via argument vector (without `--calibration` for `2-experimental`).
  - [ ] Verified output DICOM exists with mode `0600`, `Modality == "DX"`, `PhotometricInterpretation == "MONOCHROME2"`, `BitsAllocated == 16`, shape `(48, 64)`.
- [ ] **4. Full-Resolution Real TRX Qualification (`2-experimental`)**:
  - [ ] Generated synthetic TRX inputs (`3000x4096` uint16, camera serial `DA5234480`, model `MV-CH120-10UM`).
  - [ ] Verified 90-degree clockwise rotated `(4096, 3000)` uint16 DICOM output using embedded `GOTRI-TRX-001` calibration.
- [ ] **5. Error Handling & Edge Cases**:
  - [ ] Tested forbidden `--calibration` flag in `2-experimental`: Verified exit code `2` (`INVALID_INPUT`).
  - [ ] Tested duplicate/symlink output path: Verified exit code `4` (`OUTPUT_EXISTS`) and preservation of existing file.
  - [ ] Tested missing gain/radiograph NPZ: Verified exit code `3` (`INPUT_NOT_FOUND`).
  - [ ] Tested malformed manifest JSON or wrong camera serial: Verified exit code `2` (`INVALID_INPUT`).
- [ ] **6. Privacy & Security Audit**:
  - [ ] Confirmed explicit operator confirmation (`confirmed=True`) is enforced after SIMRS patient lookup before generating manifest.
  - [ ] Confirmed no patient names, medical record numbers, or birthdates appear in error logs or stdout.

---

## 7. Staging Update Server Integration & Grabber-Owned Updater Responsibilities

The MPIPS staging update server (`https://ip.mhcsgo.cloud`, port `8015`) provides automated discovery and authenticated download for the standalone Linux ELF binary (`mpips-runtime.bin`).

### Summary API Contract for Grabber Clients

| Endpoint | Method | Auth | Purpose & Format |
|---|---|---|---|
| `/mpips/staging/health` | GET | None | Health check. Returns `{"status": "ok", "service": "mpips-update-server", "environment": "staging"}`. |
| `/mpips/staging/latest.json?platform=ubuntu-24.04-x86_64` | GET | Bearer (`Authorization: Bearer <token>`) | Channel discovery. Returns `schema_version: 1` and either `status: "no_release"` or `status: "available"` with `artifact` descriptor and signed metadata. |
| `/mpips/staging/releases/{release_id}/download` | GET | Bearer (`Authorization: Bearer <token>`) | Presigned download URL issuer. Returns `{"release_id": "...", "download_url": "https://...", "expires_at": "..."}`. |

### Key Integration Rules for Grabber Developers
1. **Platform Target**: Supported canonical platform is strictly `ubuntu-24.04-x86_64`.
2. **Mandatory Pre-Download Signature Verification**: Verify the 64-byte Ed25519 signature in `signature` over the canonical bytes of `signed_metadata_b64` using the pinned staging Ed25519 public key **before** trusting `sequence` or calling `download_endpoint`. Cross-check all 12 signed metadata fields (`schema_version`, `channel`, `platform`, `release_id`, `version`, `sequence`, `source_commit`, `interface_version`, `artifact`, `release_status`, `expires_at`, `compatibility`) between the outer manifest and inner signed metadata.
3. **Client-Side Monotonic Sequence Check**: Compare the authenticated `sequence` against the locally persisted installed sequence and enforce `sequence > current_sequence`.
4. **Presigned Download URL & Storage Host Validation**: Fetch the binary from `download_url` via HTTP GET **without** forwarding MPIPS `Authorization` headers, rejecting all HTTP `3xx` redirects, and verifying that the URL uses `https://` with an approved storage host (`s3.mhcsgo.cloud`).
5. **Streaming & Bounded Download**: Stream in chunks (e.g., 64 KiB) with incremental SHA-256 calculation. Abort immediately if downloaded bytes exceed `artifact.size_bytes` or the 512 MiB maximum limit. Verify exact byte count and SHA-256 before setting executable permissions or running `--version`.
6. **PR #23 Candidate Provenance**: Under open PR #23 (`EV-STANDALONE-REAL-TRX-001`), the verified local candidate ELF binary size is `241,288,024` bytes (~230.1 MiB, SHA-256 `189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) embedding real TRX (`GOTRI-TRX-001`) and synthetic development BED calibration profiles. Gate G10 remains **NOT RELEASED**; live staging returns `status: "no_release"`.
7. **Detailed Reference**: See [Ubuntu Grabber Integration Guide](../ubuntu-grabber.md#staging-release-distribution-and-update-server-api-contract) for full JSON request/response envelopes and client state machine specifications.

### Production Grabber Updater vs. Test Simulation (`tests/test_grabber_update_flow_simulation.py`)

> **IMPORTANT**: `tests/test_grabber_update_flow_simulation.py` in the MPIPS repository is **test-only verification code**, not a production updater library. The external Grabber application owner must implement the following production behaviors:
> - **Persistent Release Sequence State**: Atomically persist and fsync the currently active `sequence` and `release_id` on disk across reboots (`<update-state-root>/state.json`).
> - **Trusted Public-Key Provisioning**: Provision and pin the approved Ed25519 public key in root/owner-protected site configuration (`<config-root>/`), with support for owner-authorized key rotation.
> - **Approved Storage-Host Validation**: Enforce strict HTTPS TLS certificate verification, an explicit storage hostname allowlist (`s3.mhcsgo.cloud`), zero HTTP redirects, and no credential forwarding.
> - **Safe Versioned Installation & Atomic Symlink Activation**: Install each verified release into an immutable version directory (`<install-root>/versions/<release_id>/mpips-runtime.bin`), fsync the file and parent directory, and switch `<install-root>/current` via atomic symlink replacement (`ln -sfn` + `rename`).
> - **Rollback & Retention**: Retain at least the previous known-good version directory and automatically revert `<install-root>/current` if post-promotion health or conversion checks fail.
> - **Exam-Idle Update Policy**: Never download, promote, or switch the active runtime while a patient examination, detector acquisition, or DICOM conversion is in progress.
> - **Crash Recovery & Staging Cleanup**: Clean up incomplete `.tmp` downloads and unpromoted staging directories on startup after an unexpected power loss or crash.
> - **Offline Continuation**: Treat update server unreachable/timeout/5xx or `status: "no_release"` as non-fatal when a valid runtime is already installed, continuing normal offline clinical examination processing without blocking the operator.

