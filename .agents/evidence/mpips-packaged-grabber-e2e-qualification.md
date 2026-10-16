# Packaged Synthetic Grabber End-to-End Qualification — Evidence Record

## 1. Milestone Status and Gate Summary

- **Delivery Package:** Packaged Synthetic Grabber End-to-End Qualification
- **Protocol State:** Implementation Verified & Remediated
- **Release Gate Status (G10):** **NOT RELEASED** (This work is bounded synthetic qualification of offline installation and adapter invocation. No production deployment, external distribution, clinical use, or hospital network access has occurred or is authorized).
- **Scope Distinction:**
  - **Simulated / Synthetic Integration:** Demonstrates that the existing, bitwise-unmodified Milestone 3 `.tar.gz` package installs into an isolated Python 3.12 virtual environment offline (`--no-index`, `--require-hashes`) and that `MPIPSSubprocessAdapter` (`scripts/grabber_subprocess_adapter.py`) from the accepted main baseline drives the installed binary (`bin/mpips-runtime`) to produce valid BED and TRX DICOMs from synthetic NPZ/SIMRS data, matching all pixel regression hashes, dimensions, permissions (`0600`), and metadata, while cleanly handling negative and security boundaries.
  - **Real Grabber Integration:** Remains separate and pending. The external Grabber application source is not in this repository and was not modified.

## 2. Immutable Package and Runtime Provenance

### Candidate Archive Verification
- **Candidate Directory:** Configurable via `MPIPS_CANDIDATE_DIR` (defaults to local handoff directory).
- **Candidate Archive Filename:** `mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`
- **Archive File Size:** `144,103,304` bytes
- **Archive SHA-256:** `97ee9519e26120e1ceb2c7e621bcb7452b3d960cc9f3926f63086c529c34ce00`
- **Source Git Commit:** `ebda70638a64294b6b794d6c3e862ce10b909d4d` (Milestone 3 candidate baseline)
- **Status:** Unsigned development-candidate, non-distributable, non-clinical.
- **Companion Release Manifest:** `mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.release.json` verified matching exact SHA-256 and size.
- **Archive Contents (Verified via `tar -tzvf`):**
  - Root directory: `mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312/`
  - Documentation & Metadata: `INSTALL.txt`, `LICENSES/GPL-2.0.txt`, `THIRD_PARTY_NOTICES.md`, `build.json`, `requirements.txt`, `source.tar.gz`
  - Offline Wheelhouse (`wheels/`):
    - `annotated_types-0.7.0-py3-none-any.whl`
    - `imageio-2.37.3-py3-none-any.whl`
    - `lazy_loader-0.5-py3-none-any.whl`
    - `mpips-0.1.0-py3-none-any.whl`
    - `networkx-3.6.1-py3-none-any.whl`
    - `numpy-2.4.6-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
    - `opencv_python_headless-4.13.0.92-cp37-abi3-manylinux_2_28_x86_64.whl`
    - `packaging-26.2-py3-none-any.whl`
    - `pillow-12.3.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
    - `pydantic-2.13.4-py3-none-any.whl`
    - `pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
    - `pydicom-3.0.2-py3-none-any.whl`
    - `python_multipart-0.0.32-py3-none-any.whl`
    - `pywavelets-1.9.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
    - `scikit_image-0.26.0-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl`
    - `scipy-1.17.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
    - `tifffile-2026.6.1-py3-none-any.whl`
    - `typing_extensions-4.15.0-py3-none-any.whl`
    - `typing_inspection-0.4.2-py3-none-any.whl`
- **Package Immutability:** Candidate package was NOT rebuilt or modified; verified bitwise identical to the original Milestone 3 candidate.

### Adapter and Converter Identities
- **Governing Task:** `.agents/tasks/mpips-packaged-grabber-e2e-qualification.md`
- **Adapter Location:** `scripts/grabber_subprocess_adapter.py` (`MPIPSSubprocessAdapter`)
- **Schema Location:** `mpips.api.schemas.dicom.MHCSManifest`
- **Protected Converter File:** `mpips/conversion/tiff_json_to_dcm.py`
- **Protected Converter SHA-256:** `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` (Bitwise unchanged).

## 3. Fresh Offline Installation & Runtime Isolation

- **Isolation Environment:** Clean temporary directory created by pytest session fixture `installed_runtime`.
- **Python Version:** Python 3.12.3.
- **Offline Install Command:**
  `pip install --no-index --only-binary=:all: --require-hashes --find-links <wheels_dir> -r <requirements.txt>`
- **Runtime Executable Path:** `<isolated_venv>/bin/mpips-runtime`
- **Runtime Execution Isolation Check:**
  Verified that the installed virtual environment imports `mpips` strictly from its local `site-packages` directory and not from the repository source tree, with `PYTHONPATH` cleared:
  `assert 'site-packages' in os.path.abspath(mpips.__file__)` (PASSED).
- **Observed CLI Version Check (`bin/mpips-runtime --version`):**
  - Exit Code: `0`
  - Output format: Single-line JSON string:
    `{"code": "OK", "interface_version": "1", "runtime_version": "0.1.0", "status": "ok"}`
- **Observed Adapter Version Check (`adapter.check_version()`):**
  - Returns `RuntimeInfo(interface_version='1', runtime_version='0.1.0', status='ok', code='OK')`.

## 4. Reconciled Synthetic Grabber Workflow Results

All tests executed via `tests/test_packaged_grabber_e2e.py` driving the installed runtime executable via `MPIPSSubprocessAdapter`.

### A. Positive Qualification Cases

1. **Synthetic Mock SIMRS & Operator Confirmation:**
   - Evaluates mock SIMRS payload (`docs/integration/examples/simrs-response.synthetic.json`).
   - Validates patient identity (`no_rkm_medis`, `nm_pasien`, `tgl_lahir`) and encounter matching (`no_rawat == "SYNTHETIC-VISIT-2026-0001"`).
   - Enforces operator confirmation before manifest construction.
   - Composes schema-valid `MHCSManifest`.

2. **BED Synthetic Workflow Execution:**
   - Synthetic radiograph: 48×64 uint16 gradient NPZ.
   - Matching synthetic gain NPZ and validated calibration directory.
   - Converted via `adapter.convert(...)` using installed `bin/mpips-runtime`.
   - Exit code: `0`
   - JSON response: `status: "ok"`, `code: "OK"`, `output_path` verified.
   - DICOM Attributes Verified:
     - Output file permissions: `0600`
     - PatientID: `SYNTHETIC-001`
     - PatientName: `SYNTHETIC PATIENT`
     - PatientBirthDate: `20000102`
     - PatientSex: `""` (empty string for `unknown`)
     - SOP Class UID: `1.2.840.10008.5.1.4.1.1.1.1.1` (Digital X-Ray Image Storage - For Presentation)
     - Rows × Columns: `48 × 64`
     - BitsAllocated/Stored/HighBit: `16 / 16 / 15`, `MONOCHROME2`
     - Zero private tags present.
     - Pixel Data Digest: SHA-256 matches exact regression pin (`13a9a56a28e1cb6d0a6daf887cc3bf98fc9b85f17995935e6b933ead836510ca`). Note: This hash is an exact regression pin for this pipeline version and input fixture, not an independent proof of clinical numerical correctness.

3. **TRX Synthetic Workflow Execution:**
   - Synthetic radiograph: 48×64 uint16 gradient NPZ.
   - Detector orientation handling: TRX specifies 90° clockwise rotation in manifest metadata.
   - Converted via `adapter.convert(...)` using installed `bin/mpips-runtime`.
   - Exit code: `0`
   - JSON response: `status: "ok"`, `code: "OK"`.
   - DICOM Attributes Verified:
     - Output file permissions: `0600`
     - Rows × Columns: `64 × 48` (correctly rotated clockwise)
     - Pixel Data Digest: SHA-256 matches exact regression pin (`24d4be23a354de71302a9d6bed77b29acef049f05863dcf86da1d7da835439c1`).

### B. Negative and Safety Integration Cases

1. **Unconfirmed Patient Selection (`test_negative_unconfirmed_patient_selection`):**
   - Aborts before manifest composition; verified no converter subprocess spawned.
2. **SIMRS Visit Identifier Mismatch (`test_negative_simrs_visit_mismatch`):**
   - SIMRS encounter mismatch (`no_rawat != requested_visit`) raises `ValueError("Encounter ID mismatch")` before manifest composition.
3. **Schema-Invalid Manifest (`test_negative_invalid_manifest_schema`):**
   - Malformed manifest passed to converter; rejected by the installed runtime subprocess CLI preflight with exit code 2 (`INVALID_INPUT`). Output DICOM is not created.
4. **Missing Gain NPZ Input (`test_negative_missing_gain_npz`):**
   - Gain input path missing; detected and rejected by adapter pre-flight path validation before subprocess execution with exit code 3 (`INPUT_NOT_FOUND`).
5. **Existing Output Conflict (`test_negative_output_already_exists`):**
   - Destination DICOM path already exists; adapter pre-flight rejects collision before subprocess execution with exit code 4 (`OUTPUT_EXISTS`). Pre-existing file content and modification timestamp remain untouched.
6. **Dangling Symlink Output (`test_negative_output_dangling_symlink`):**
   - Destination path is a broken symlink; adapter pre-flight detects symlink before resolution and raises `MPIPSOutputExistsError` (exit code 4). The dangling symlink target is never created.
7. **Radiograph-Gain Identifier Mismatch (`test_negative_radiograph_gain_identifier_mismatch`):**
   - Radiograph references mismatched gain ID (`SYNTHETIC-OTHER-GAIN`); rejected by the installed runtime worker process with exit code 2 (`INVALID_INPUT`). Output DICOM is not created.
8. **Malicious Response Shielding (`test_negative_malicious_response_shielding`):**
   - Mock runtime emitting injection strings (`<script>alert('xss')</script>`, sensitive fields `SECRET-12345`); adapter raises sanitized `MPIPSInvalidInputError` with deterministic message `Runtime failed with exit code 2 (INVALID_INPUT)` without leaking untrusted response payload tokens.

## 5. Verification Results and CI Accounting

### A. Local Strict Qualification Run (`MPIPS_STRICT_QUALIFICATION=1`)
- **Command:** `MPIPS_STRICT_QUALIFICATION=1 .venv/bin/pytest tests/test_packaged_grabber_e2e.py -v`
- **Candidate Package SHA-256:** `97ee9519e26120e1ceb2c7e621bcb7452b3d960cc9f3926f63086c529c34ce00`
- **Candidate Source Commit:** `ebda70638a64294b6b794d6c3e862ce10b909d4d`
- **Installed Runtime Path:** `<tmp_path>/packaged-install<N>/runtime-venv/bin/mpips-runtime`
- **Runtime Interface / Version:** `interface 1` / `0.1.0`
- **Execution Accounting:**
  - **Passed:** **11**
  - **Skipped:** **0** (Zero skips required and achieved in strict qualification mode)
  - **Failed:** **0**
  - **Duration:** 26.50s

### B. Standard GitHub CI Accounting
- **Normal CI Behavior:** GitHub Actions runners do not host the local Windows/WSL candidate handoff directory. Standard GitHub CI (`pytest -q`) reports an explicit, graceful skip:
  `Skipped: Candidate package or metadata not found at ... Requires offline candidate handoff directory.`
- **Separate Packaging Workflow:** The companion GitHub workflow (`qualify-ubuntu-local-runtime-candidate.yml`) independently builds a temporary runtime candidate wheel and tests offline installation in CI.
- **Reporting Rule:** Tests skipped on standard GitHub CI are explicitly classified as skipped, never as executed.

## 6. Stated Boundaries and Limitations

1. **Candidate Archive Immutability:**
   - The Milestone 3 package (`mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`) was tested strictly as-is and was not rebuilt. It remains an unsigned, non-distributable development candidate.
2. **Synthetic Data Only:**
   - All patient identifiers, visits, accessions, pixel arrays, and detector calibrations use fictional synthetic fixtures. No clinical data or hospital systems were accessed.
3. **Grabber Boundary:**
   - Demonstrates subprocess and schema interoperability between the offline installed runtime executable and the Grabber adapter module (`scripts/grabber_subprocess_adapter.py`). The external Grabber codebase was not altered.
4. **Release Gate (G10):**
   - **NOT RELEASED**. Production deployment, distribution, or release authorization is out of scope.
