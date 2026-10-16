# MPIPS — Standalone Binary Review and Real TRX Calibration Integration Qualification Report

**Document ID:** EV-STANDALONE-REAL-TRX-001  
**Status:** Approved Qualification Evidence  
**Date:** 2026-10-16  
**Target Environment:** Ubuntu 24.04 x86_64 (`glibc 2.39`, Linux 5.15/6.x)  
**Accepted Main Baseline:** `8dd42a7106d13ff602f41a57b726668066791bec`  
**Governing Task:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md`  
**Result:** **PASS — Standalone `.bin` qualified with embedded Real TRX geometric calibration.**

---

## 1. Executive Summary

This qualification report records the review and full qualification of the self-contained Linux ELF executable **`mpips-runtime.bin`** embedded with the designated **real TRX detector geometric calibration profile**.

- **Executable:** `dist-experimental/mpips-runtime.bin`
- **Format:** ELF 64-bit LSB executable, x86-64, dynamically linked (`glibc 2.39`), stripped.
- **File Size:** `237,341,200` bytes (~226 MiB).
- **SHA-256 Digest:**
  ```text
  b9b9db3ee056b31f8a1e378a7c38e53bed0bbef9cb72ab5e38df0d6903e4e07f
  ```
- **Designated Real TRX Asset Provenance:**
  - Archive: `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz`
  - Archive SHA-256: `2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556` (exact match verified)
  - Extracted Remap Size: 72,080,774 bytes (~72 MiB)
  - Fingerprint: `606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d`
  - Detector Mode: `TRX`, Camera Serial: `DA5234480`, Camera Model: `MV-CH120-10UM`, Image Shape: `3000 x 4096`
  - Scope: `LOCAL_REAL_TRX_ACCEPTANCE`
- **Protected Converter:** `mpips/conversion/tiff_json_to_dcm.py` verified unmodified (SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`).
- **Release Status:** Gate **G10 remains NOT RELEASED**. No external distribution or PR merge is authorized.

---

## 2. Separate Acceptance Verdicts

| Dimension | Verdict | Evidence / Observed Result |
|---|---|---|
| **One-file Standalone ELF Build** | **PASS** | Dynamic PyInstaller specs (`SPECPATH`-relative) successfully built 226 MiB stripped ELF binary into `dist-experimental/mpips-runtime.bin`. |
| **Embedded Real TRX Calibration Provenance** | **PASS** | Archive hash verified against `2871e78f...`. Embedded metadata and remap array loaded and validated directly by worker child process. Large assets excluded from Git. |
| **Full-Resolution Synthetic TRX Conversion** | **PASS** | 3000 x 4096 synthetic inputs processed through real TRX geometry into valid DICOM with 4096 x 3000 rotated uint16 pixel array in ~53s (~24.5 MiB DICOM). |
| **Synthetic BED Regression** | **PASS** | Small synthetic BED test fixtures continue to convert without `--calibration` and pass regression invariants. |
| **Grabber Adapter Compatibility** | **PASS** | `MPIPSSubprocessAdapter` updated with version-aware strategy supporting both interface 1 and experimental interface without `--calibration`. 20/20 unit/adapter tests passed. |
| **Clean-Host Operation Without Python** | **PASS** | Executed in pure `env -i PATH=/usr/bin:/bin` from `/tmp` with zero Python/repo environment variables. Full-res DICOM conversion passed. |
| **Negative & Security Cases** | **PASS** | Rejection of camera serial mismatch, detector mode mismatch, missing inputs, malformed manifest, existing output, and dangling symlinks. File mode `0600` enforced. |
| **Repository Regression & CI** | **PASS** | Protected converter check passed; Packaged Grabber E2E passed (11/11 tests). |

---

## 3. Calibration Contract & Selection Safety

1. **Deterministic Matching & Fail-Closed Behavior:**
   - Radiograph metadata must match detector mode (`TRX`) and camera serial (`DA5234480`).
   - If radiograph specifies an incompatible serial (e.g., `WRONG-SERIAL-9999`), conversion fails with `NPZ_VALIDATION_ERROR` (exit code 2).
   - If radiograph input array dimensions do not match the calibration image shape (`3000 x 4096`), conversion fails immediately before processing.
   - Ambiguous profiles (multiple candidates with conflicting serials) fail closed.
2. **Gain Separation:**
   - Per-acquisition `gain.npz` remains an external requirement; its dark/flat shapes and detector mode are verified against the radiograph.
3. **No External Fallback:**
   - The frozen executable bundle checks `sys._MEIPASS` and does not fall back to local disk paths or identity remapping.

---

## 4. Grabber Adapter Version-Aware Integration

`scripts/grabber_subprocess_adapter.py` now defines:
```python
SUPPORTED_INTERFACE_VERSION = "1"
EXPERIMENTAL_INTERFACE_VERSION = "2-experimental"
SUPPORTED_INTERFACE_VERSIONS = {SUPPORTED_INTERFACE_VERSION, EXPERIMENTAL_INTERFACE_VERSION}
```
When invoking `convert`, `calibration` is optional. When omitted, the adapter omits `--calibration` from the argument vector. Existing interface 1 invocations with `--calibration` remain 100% backward compatible and tested.

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
Command: `.venv/bin/pytest tests/test_standalone_bin_qualification.py -v`
```text
tests/test_standalone_bin_qualification.py::test_bin_version PASSED                      [ 10%]
tests/test_standalone_bin_qualification.py::test_bin_convert_bed_synthetic_no_calibration PASSED [ 20%]
tests/test_standalone_bin_qualification.py::test_bin_convert_trx_full_resolution_no_calibration PASSED [ 30%]
tests/test_standalone_bin_qualification.py::test_bin_via_adapter_no_calibration PASSED [ 40%]
tests/test_standalone_bin_qualification.py::test_bin_negative_camera_serial_mismatch PASSED [ 50%]
tests/test_standalone_bin_qualification.py::test_bin_negative_input_not_found PASSED       [ 60%]
tests/test_standalone_bin_qualification.py::test_bin_negative_invalid_manifest PASSED      [ 70%]
tests/test_standalone_bin_qualification.py::test_bin_negative_output_exists PASSED        [ 80%]
tests/test_standalone_bin_qualification.py::test_bin_negative_dangling_symlink PASSED     [ 90%]
tests/test_standalone_bin_qualification.py::test_bin_negative_detector_mode_mismatch PASSED [100%]
======================== 10 passed in 113.89s (0:01:53) ========================
```

### Subprocess Adapter Suite
Command: `.venv/bin/pytest tests/test_grabber_subprocess_adapter.py -v`
```text
============================= 20 passed in 12.06s ==============================
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
