# MPIPS — Linux Standalone .bin Feasibility and Embedded Calibration Qualification Report

**Document ID:** EV-STANDALONE-BIN-001  
**Status:** Complete  
**Date:** 2026-10-16  
**Target Environment:** Ubuntu 24.04 x86_64  
**Starting Baseline:** `8dd42a7106d13ff602f41a57b726668066791bec`  
**Governing Task:** `.agents/tasks/mpips-standalone-bin-prototype.md`  
**Result:** **PASS — Self-contained `.bin` qualified for synthetic BED/TRX only.**

---

## 1. Executive Summary

This qualification report records the feasibility assessment, freezing architecture, and automated qualification results for the experimental self-contained Linux ELF executable:

- **Executable:** `dist-experimental/mpips-runtime.bin`
- **Format:** ELF 64-bit LSB executable, x86-64, dynamically linked (`glibc 2.39`), stripped.
- **Size:** 164,520,048 bytes (~157 MiB).
- **SHA-256:** `cfabe395a6117d7e61c3fec4fb6d2e87c700e762b5e559dfde3768d3edada17a`
- **Embedded Calibration Assets:** Explicitly labeled synthetic calibration profiles for `BED` and `TRX` modes embedded under `mpips/resources/calibration`.
- **Public CLI Interface:** `interface_version: "2-experimental"`, allowing offline `convert` without `--calibration`.
- **Subprocess Worker Isolation:** Maintained via internal dispatch (`sys.executable _internal_worker ...`) under process group supervision with `0o077` umask and destination hard-link commit.

All Stage A (standalone directory) and Stage B (single-file ELF `.bin`) objectives passed qualification in an isolated Ubuntu 24.04 x86_64 environment.

---

## 2. Calibration Contract Assessment

| Asset Category | Location / Handling | Contract Separation |
|---|---|---|
| **Algorithms** | `mpips/processing/`, `mpips/pipelines/`, `mpips/conversion/` | Implemented in Python/C extensions in the core repository. Unchanged. |
| **Detector Assets** | `mpips/resources/calibration/bed_mode/` and `trx_mode/` | Embedded into the frozen bundle. Explicitly labeled `SYNTHETIC_DEVELOPMENT_ONLY`. Identity remap only. |
| **Per-acquisition Gain** | `--gain /path/to/gain.npz` | External CLI argument required per exam. Validated against radiograph `gain_id` and `detectorMode`. |

> [!CAUTION]
> **No Clinical Validity:** The embedded calibration profiles are synthetic identity grids for development and integration test fixtures. They **must not** be used for clinical imaging or detector hardware without approved profiles and provenance.

---

## 3. CLI Interface and Grabber Invocation

### Version Check
```bash
./mpips-runtime.bin --version
```
**Observed Output:**
```json
{"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}
```

### Conversion Without `--calibration`
```bash
./mpips-runtime.bin convert \
  --radiograph /private/exam/radiograph.npz \
  --gain /private/exam/gain.npz \
  --manifest /private/exam/manifest.json \
  --output /private/exam/result.dcm
```
**Observed Output:**
```json
{"code": "OK", "interface_version": "2-experimental", "output_byte_size": 7396, "runtime_version": "0.1.0", "status": "ok"}
```

---

## 4. Binary Architecture and Technical Solutions

1. **Standalone Subprocess Worker Isolation:**
   When running inside a PyInstaller frozen environment, `python` is not available on PATH. `mpips/conversion/service.py` detects `getattr(sys, "frozen", False)` and invokes `sys.executable _internal_worker <args_path> <result_path>`. The entrypoint dispatches to `mpips.conversion.worker.execute_conversion_worker` with RLIMIT resource bounds.

2. **Calibration Discovery:**
   `resolve_calibration_artifact_dir()` checks `sys._MEIPASS` when frozen, locating bundled calibration artifacts under `mpips/resources/calibration`.

3. **Protection and Non-Regression:**
   - Canonical converter `mpips/conversion/tiff_json_to_dcm.py` unchanged (SHA-256: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`).
   - Packaged Grabber E2E test suite (`tests/test_packaged_grabber_e2e.py`) passes 11/11 tests.
   - Subprocess adapter test suite (`tests/test_grabber_subprocess_adapter.py`) passes 20/20 tests.

---

## 5. Automated Qualification Results

Execution command:
```bash
.venv/bin/pytest tests/test_standalone_bin_qualification.py -v
```

Observed test run:
```text
tests/test_standalone_bin_qualification.py::test_bin_version PASSED                      [ 12%]
tests/test_standalone_bin_qualification.py::test_bin_convert_bed_synthetic_no_calibration PASSED [ 25%]
tests/test_standalone_bin_qualification.py::test_bin_convert_trx_synthetic_no_calibration PASSED [ 37%]
tests/test_standalone_bin_qualification.py::test_bin_negative_input_not_found PASSED       [ 50%]
tests/test_standalone_bin_qualification.py::test_bin_negative_invalid_manifest PASSED      [ 62%]
tests/test_standalone_bin_qualification.py::test_bin_negative_output_exists PASSED        [ 75%]
tests/test_standalone_bin_qualification.py::test_bin_negative_dangling_symlink PASSED     [ 87%]
tests/test_standalone_bin_qualification.py::test_bin_negative_detector_mode_mismatch PASSED [100%]
============================== 8 passed in 33.64s ==============================
```

---

## 6. Build Instructions and Reproducibility

1. Install build requirements in `.venv`:
   ```bash
   pip install pyinstaller pyinstaller-hooks-contrib altgraph
   ```
2. Run build script:
   ```bash
   ./build-standalone/scripts/build_standalone_bin.sh
   ```
3. Artifact is output to `dist-experimental/mpips-runtime.bin`.

---

## 7. Limitations and Next Steps

- **Synthetic-Only:** Validated strictly for synthetic BED/TRX data. Not for clinical production.
- **Binary Size & Cold-Start:** Size is ~157 MiB; cold startup execution takes ~2.6s due to PyInstaller self-extraction into `/tmp/_MEIxxxxxx`.
- **G10 Gate:** G10 remains **NOT RELEASED**. No external distribution or release artifact uploaded.
