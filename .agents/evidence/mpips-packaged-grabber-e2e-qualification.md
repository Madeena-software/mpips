# Packaged Synthetic Grabber End-to-End Qualification — Evidence Record

## 1. Milestone Status and Gate Summary

- **Delivery Package:** Packaged Synthetic Grabber End-to-End Qualification
- **Protocol State:** Implementation Verified & Ready for Review
- **Release Gate Status (G10):** **NOT RELEASED** (This work is bounded synthetic qualification of offline installation and adapter invocation. No production deployment, external distribution, clinical use, or hospital network access has occurred or is authorized).
- **Scope Distinction:**
  - **Simulated / Synthetic Integration:** Demonstrates that the existing, bitwise-unmodified Milestone 3 `.tar.gz` package installs into a clean Python 3.12 virtual environment offline (`--no-index`, `--require-hashes`) and that `MPIPSSubprocessAdapter` from the accepted main baseline drives the installed binary (`bin/mpips-runtime`) to produce valid BED and TRX DICOMs from synthetic NPZ/SIMRS data, matching all pixel digests, dimensions, and metadata requirements, while cleanly handling negative and security boundaries.
  - **Real Grabber Integration:** Remains separate. The external Grabber application source is not in this repository and was not modified.

## 2. Immutable Package and Runtime Identities

### Package Source Verification
- **Local Candidate Directory:** `/mnt/c/Users/faliq/Desktop/mpips-candidate-handoff/`
- **Candidate Archive Filename:** `mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`
- **Archive File Size:** `144,103,304` bytes
- **Archive SHA-256:** `97ee9519e26120e1ceb2c7e621bcb7452b3d960cc9f3926f63086c529c34ce00`
- **Source Git Commit:** `ebda70638a64294b6b794d6c3e862ce10b909d4d` (Milestone 3 candidate baseline)
- **Status:** Unsigned development-candidate, non-distributable, non-clinical.
- **Companion Release Manifest:** `.release.json` verified matching exact SHA-256 and size.
- **Wheelhouse Contents:** Verified containing all expected wheels: `mpips-0.1.0-py3-none-any.whl`, `numpy`, `scipy`, `pydicom`, `pydantic`, `pydantic_core`, `pillow`, `tifffile`, `annotated_types`, `typing_extensions`, and `install.sh`.
- **Package Immutability:** Package was NOT rebuilt or modified; verified bitwise identical to the original Milestone 3 candidate.

### Adapter and Converter Identities
- **Governing Task:** `.agents/tasks/mpips-packaged-grabber-e2e-qualification.md`
- **Accepted Starting Baseline:** `58168270236c2fdd8d5c3dddf75ddd8575333dae`
- **Current Branch:** `feat/packaged-grabber-e2e-qualification`
- **Protected Converter File:** `mpips/conversion/tiff_json_to_dcm.py`
- **Protected Converter SHA-256:** `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` (Bitwise unchanged).

## 3. Fresh Offline Installation Verification

- **Environment:** Clean temporary directory via `pytest` session fixture `installed_runtime`.
- **Python Version:** Python 3.12.3.
- **Installation Mechanism:** Extracted candidate archive and invoked `pip install --no-index --find-links=wheelhouse --require-hashes -r wheelhouse/requirements.txt`.
- **Isolation:** Executed with zero source-tree Python imports (`sys.path` does not include workspace repository for the runtime subprocess).
- **Installed Runtime Executable:** `<tmp_path>/venv/bin/mpips-runtime`
- **Observed CLI Version Check:**
  - Command: `bin/mpips-runtime --version`
  - Exit Code: `0`
  - Output: `mpips-runtime 0.1.0 (interface 1)`
- **Observed Adapter Version Check (`adapter.get_version()`):**
  - `RuntimeVersionInfo(raw_output='mpips-runtime 0.1.0 (interface 1)', runtime_version='0.1.0', interface_version=1)`

## 4. Synthetic Grabber Workflow Results

All synthetic end-to-end tests executed via `tests/test_packaged_grabber_e2e.py` using `MPIPSSubprocessAdapter(runtime_executable=...)`.

### Positive Qualification Cases

1. **Synthetic Mock SIMRS & Operator Confirmation:**
   - Validated candidate selection matching Patient ID, Visit ID, and Accession Number.
   - Tested operator confirmation gating: unconfirmed selection aborts without invoking the runtime.
   - Composed valid JSON manifest matching `mpips.schema.manifest`.

2. **BED Synthetic Workflow Execution:**
   - Synthetic radiograph: 48×64 uint16 gradient NPZ.
   - Matching synthetic gain NPZ and synthetic validated calibration.
   - Converted using installed `mpips-runtime`.
   - Exit Code: `0`
   - JSON Status: `code: "SUCCESS"`, `status: "ok"`, `output_path` verified.
   - DICOM Verification:
     - Output file permissions: `0600`
     - SOP Class UID: `1.2.840.10008.5.1.4.1.1.1.1.1` (Digital X-Ray Image Storage - For Presentation)
     - Rows × Columns: `48 × 64`
     - BitsAllocated/Stored/HighBit: `16 / 16 / 15`, `MONOCHROME2`
     - Zero private tags present.
     - Pixel Data Digest: SHA-256 matches exact known deterministic hash (`ecfa37b12d59fcb52df39c5cb4fb3cb5421da2195dfb0c7a5f2ec39e7829705a`).

3. **TRX Synthetic Workflow Execution:**
   - Synthetic radiograph: 48×64 uint16 gradient NPZ.
   - Detector orientation handling: TRX specifies 90° clockwise rotation in manifest metadata.
   - Converted using installed `mpips-runtime`.
   - Exit Code: `0`
   - JSON Status: `code: "SUCCESS"`, `status: "ok"`.
   - DICOM Verification:
     - Output file permissions: `0600`
     - Rows × Columns: `64 × 48` (correctly rotated)
     - Pixel Data Digest: SHA-256 matches exact known deterministic hash (`97f02b378037a346e49e8a7199bc45ee44a8549320e6a8e578c7921a99d45e69`).

### Negative and Safety Verification Cases

1. **Unconfirmed Patient Selection:**
   - Aborts before runtime invocation; verifies no subprocess spawned.
2. **Schema-Invalid Manifest JSON:**
   - Fails fast in adapter pre-flight schema validation without launching runtime subprocess.
3. **Missing Gain NPZ Input:**
   - Fails fast in adapter pre-flight path validation without launching runtime subprocess; existing inputs untouched.
4. **Existing Output Conflict:**
   - Destination DICOM path already exists: adapter raises `MPIPSExecutionError("Output file already exists: ...")` before execution; existing output file content and timestamp preserved intact.
5. **Dangling Symlink Output:**
   - Destination path is a broken symlink: adapter safely detects and rejects it without following or unlinking.
6. **Malicious Response Shielding & Untrusted Data Leakage:**
   - Synthetic malformed JSON responses containing injection attacks, e.g. `<script>alert(1)</script>`, malicious formatting tokens, or interface version mismatches (`interface_version: 999`).
   - Verified that adapter raises sanitized `MPIPSRuntimeError` or `MPIPSInterfaceIncompatibleError` without interpolating untrusted payload fields into the exception message string.

## 5. Automated Test Suite Execution Summary

- **Command:** `.venv/bin/pytest tests/test_packaged_grabber_e2e.py -v`
- **Results:**
  - `test_packaged_runtime_version_and_interface`: **PASSED**
  - `test_full_synthetic_workflow_e2e[BED]`: **PASSED**
  - `test_full_synthetic_workflow_e2e[TRX]`: **PASSED**
  - `test_negative_unconfirmed_patient_selection`: **PASSED**
  - `test_negative_invalid_manifest`: **PASSED**
  - `test_negative_missing_gain_input`: **PASSED**
  - `test_negative_existing_output_conflict`: **PASSED**
  - `test_negative_dangling_symlink_output`: **PASSED**
  - `test_negative_malicious_response_shielding`: **PASSED**
- **Summary:** **9 passed in 114.70s**
- **Code Standards:**
  - `flake8 tests/test_packaged_grabber_e2e.py`: Clean (0 errors).
  - `black --check tests/test_packaged_grabber_e2e.py`: Clean (0 reformats needed).

## 6. Stated Boundaries and Limitations

1. **Candidate Archive Immutability:**
   - The Milestone 3 package (`mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`) was tested strictly as-is and was not rebuilt. It remains unsigned and development-only.
2. **Synthetic Data Only:**
   - All patient identifiers, visits, accessions, pixel arrays, and detector calibrations use fictional synthetic fixtures. No clinical data or hospital systems were accessed.
3. **Grabber Boundary:**
   - The test demonstrates interoperability between the offline installed runtime executable and the Grabber integration adapter module (`mpips.integration.grabber.adapter`). The external Grabber codebase was not altered.
4. **Release Gate (G10):**
   - **NOT RELEASED**. Production deployment, distribution, or release authorization is out of scope.
