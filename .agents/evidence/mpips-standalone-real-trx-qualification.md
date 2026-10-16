# MPIPS — Standalone Binary Review and Real TRX Calibration Integration Qualification Report

**Document ID:** EV-STANDALONE-REAL-TRX-001  
**Status:** Independent Review Remediation (Review Pending)  
**Date:** 2026-10-16  
**Target Environment:** Ubuntu 24.04 x86_64 (`glibc 2.39`, Linux 5.15/6.x)  
**Accepted Main Baseline:** `8dd42a7106d13ff602f41a57b726668066791bec`  
**Governing Task:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md` (Revision 1.1)  
**Result:** **QUALIFIED LOCALLY (STRICT MODE PASS) — Independent Review in Progress**

---

## 1. Executive Summary

This qualification report records the review, remediation, and qualification of the self-contained Linux ELF executable **`mpips-runtime.bin`** embedded with the designated **real TRX detector geometric calibration profile**.

- **Executable:** `dist-experimental/mpips-runtime.bin` (local build candidate only; not distributed or released on GitHub)
- **Format:** ELF 64-bit LSB executable, x86-64, dynamically linked (`glibc 2.39`), stripped.
- **File Size:** `237,341,200` bytes (~226 MiB).
- **Local Candidate SHA-256 Digest:**
  ```text
  664906aa491b04735307f23c8a4cb821ef2f8c04c6cc33f8768c1e7ee7d6a115
  ```
  *(Note: Tied explicitly to validated local build; binary payload is not committed to git or uploaded to GitHub Actions).*
- **Designated Real TRX Asset Provenance:**
  - Archive: `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz`
  - Archive SHA-256: `2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556` (exact match verified by pre-build gate)
  - Remap SHA-256: `32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893`
  - Fingerprint: `606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d`
  - Detector Mode: `TRX`, Camera Serial: `DA5234480`, Camera Model: `MV-CH120-10UM`, Image Shape: `3000 x 4096`
  - Scope: `LOCAL_REAL_TRX_ACCEPTANCE`
- **Protected Converter:** `mpips/conversion/tiff_json_to_dcm.py` verified unmodified (SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`).
- **Release Status:** Gate **G10 remains NOT RELEASED**. No external distribution or PR merge is authorized.

---

## 2. Separate Acceptance Verdicts

| Dimension | Verdict | Evidence / Observed Result |
|---|---|---|
| **One-file Standalone ELF Build** | **PASS** | Dynamic PyInstaller specs (`SPECPATH`-relative) preceded by `prepare_calibration_bundle.py` validation gate successfully built 226 MiB stripped ELF binary into `dist-experimental/mpips-runtime.bin`. |
| **Embedded Real TRX Calibration Provenance** | **PASS** | Source archive hash verified against `2871e78f...`. Embedded metadata and remap array validated with SHA-256 integrity checks directly by worker child process. Large assets excluded from Git. |
| **Full-Resolution Synthetic TRX Conversion** | **PASS** | 3000 x 4096 synthetic inputs processed through real TRX geometry into valid DICOM with 4096 x 3000 rotated uint16 pixel array in ~53s (~24.5 MiB DICOM). |
| **Synthetic BED Regression** | **PASS** | Small synthetic BED test fixtures continue to convert without `--calibration` and pass regression invariants. Deterministic synthetic BED coordinate grid generated cleanly. |
| **Grabber Adapter Compatibility** | **PASS** | `MPIPSSubprocessAdapter` enforces contract differences: interface negotiation verifies version; interface 1 requires calibration; interface 2-experimental uses embedded calibration and strictly rejects external `--calibration`. 25/25 adapter unit tests passed. |
| **Clean-Host Environment Isolation** | **PASS (Env-Isolated) / PENDING (Physical Clean Host)** | Subprocess execution verified under environment isolation (`env -i PATH=/usr/bin:/bin` from `/tmp`) with all Python/repo environment variables scrubbed. Physical or containerized execution without Python installed remains pending. |
| **Negative & Security Cases** | **PASS** | Strict fail-closed verification of camera serial identity, detector mode, remap hash, and fingerprint. Negative tests for wrong/missing serial, bad fingerprint, altered remap, missing remap, substitute TRX profile bypass attempts, external calibration override rejection in interface 2, and unhandled Linux RLIMIT_CPU failure all pass. File mode `0600` enforced. |
| **Repository Regression & CI** | **PASS (CI Suite) / LOCAL ONLY (.bin Execution)** | Standard CI suite passes completely on GitHub Actions (Black, Flake8, Mypy regression gate, pytest, Docker builds, smoke tests). Standalone binary execution is qualified strictly locally with `MPIPS_STRICT_QUALIFICATION=1`. |

---

## 3. Calibration Contract & Selection Safety

1. **Deterministic Matching & Fail-Closed Behavior:**
   - Radiograph metadata must match detector mode (`TRX`) and camera serial (`DA5234480`).
   - If radiograph specifies an incompatible serial (e.g., `WRONG-SERIAL-9999`), conversion fails with `NPZ_VALIDATION_ERROR` (exit code 2).
   - If radiograph input array dimensions do not match the calibration image shape (`3000 x 4096`), conversion fails immediately before processing.
   - Ambiguous profiles (multiple candidates with conflicting serials) fail closed.
   - Any attempt to supply a substitute TRX profile with altered profile ID, wrong fingerprint, absent camera serial, or altered remap payload fails before image processing.
2. **Gain Separation:**
   - Per-acquisition `gain.npz` remains an external requirement; its dark/flat shapes and detector mode are verified against the radiograph.
3. **No External Fallback:**
   - The frozen executable bundle checks `sys._MEIPASS` and does not fall back to local disk paths or identity remapping. Interface 2-experimental strictly rejects explicit external `--calibration` arguments.

---

## 4. Grabber Adapter Version-Aware Integration

`scripts/grabber_subprocess_adapter.py` defines:
```python
SUPPORTED_INTERFACE_VERSION = "1"
EXPERIMENTAL_INTERFACE_VERSION = "2-experimental"
SUPPORTED_INTERFACE_VERSIONS = {SUPPORTED_INTERFACE_VERSION, EXPERIMENTAL_INTERFACE_VERSION}
```
When invoking `convert`, interface negotiation occurs via `negotiate_interface()` or explicit `expected_interface_version`. Interface 1 requires an explicit external calibration directory. Interface 2-experimental requires embedded calibration and rejects external `--calibration`. Sanitized JSON responses and error translations are fully preserved.

---

## 5. Performance and Resource Metrics

- **Binary Cold Startup:** ~2.68s (self-extraction of bundle to `/tmp/_MEIxxxxxx`).
- **Full-Resolution (3000 x 4096) Conversion Duration:** ~53.1s.
- **Output DICOM File Size:** 24,577,268 bytes.
- **Output File Permissions:** `0600` (read/write by owner only).
- **Runtime Host Libraries (`ldd`):** `libdl.so.2`, `libz.so.1`, `libpthread.so.0`, `libc.so.6`, `ld-linux-x86-64.so.2` (standard Ubuntu 24.04).

---

## 6. Test Suite Evidence

### Standalone Qualification Suite
Command: `MPIPS_STRICT_QUALIFICATION=1 .venv/bin/pytest tests/test_standalone_bin_qualification.py -v`
```text
tests/test_standalone_bin_qualification.py::test_bin_version PASSED                      [  8%]
tests/test_standalone_bin_qualification.py::test_bin_convert_bed_synthetic_no_calibration PASSED [ 16%]
tests/test_standalone_bin_qualification.py::test_bin_convert_trx_full_resolution_no_calibration PASSED [ 25%]
tests/test_standalone_bin_qualification.py::test_bin_via_adapter_no_calibration PASSED [ 33%]
tests/test_standalone_bin_qualification.py::test_bin_negative_camera_serial_mismatch PASSED [ 41%]
tests/test_standalone_bin_qualification.py::test_bin_negative_input_not_found PASSED       [ 50%]
tests/test_standalone_bin_qualification.py::test_bin_negative_invalid_manifest PASSED      [ 58%]
tests/test_standalone_bin_qualification.py::test_bin_negative_output_exists PASSED        [ 66%]
tests/test_standalone_bin_qualification.py::test_bin_negative_dangling_symlink PASSED     [ 75%]
tests/test_standalone_bin_qualification.py::test_bin_negative_detector_mode_mismatch PASSED [ 83%]
tests/test_standalone_bin_qualification.py::test_worker_negative_real_trx_validation_cases PASSED [ 91%]
tests/test_standalone_bin_qualification.py::test_bin_rejects_explicit_calibration_override_in_interface_2 PASSED [100%]
======================== 12 passed in 119.91s ========================
```

### Subprocess Adapter Suite
Command: `.venv/bin/pytest tests/test_grabber_subprocess_adapter.py -v`
```text
============================= 25 passed in 10.58s ==============================
```

### Packaged Grabber E2E Regression
Command: `.venv/bin/pytest tests/test_packaged_grabber_e2e.py -v`
```text
============================= 11 passed in 31.37s ==============================
```

### Canonical Converter Immutability
Command: `.venv/bin/pytest tests/test_converter_protection.py -v`
```text
============================== 1 passed in 0.03s ===============================
```
