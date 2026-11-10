# MPIPS — Standalone Binary Review and Real TRX Calibration Integration Qualification Report

**Document ID:** EV-STANDALONE-REAL-TRX-001  
**Status:** Independent Review Remediation & Offline Integrated Acceptance (Review Pending)  
**Date:** 2026-11-10  
**Target Environment:** Ubuntu 24.04 LTS (`noble`) x86_64 (`glibc 2.39`, Linux 5.15/6.x)  
**Accepted Main Baseline:** `8dd42a7106d13ff602f41a57b726668066791bec`  
**Standalone Qualification Baseline:** `cbf2b24ba4fb8f2b5fc25b6a86f381ba7cf5f4b1`  
**Staging Hardening Baseline:** `b7d0a10a600ccc1215e529c5a6bbc05036ab2998`  
**Integration Merge Commit (`feat/offline-integrated-elf-acceptance`):** `90fa785b1607d6d63fe39e3e2557468e64da4717`  
**Governing Task:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md` (Revision 1.2)  
**Result:** **OFFLINE_INTEGRATED_ELF_PASS (Container & Local Env-Isolated Qualification) — Independent Review in Progress**

---

## 1. Executive Summary

This qualification report records the review, remediation, Ubuntu 24.04 container qualification, and offline integrated update-server acceptance of the self-contained Linux ELF executable **`mpips-runtime.bin`** embedded with the designated **real TRX detector geometric calibration profile**.

- **Executable:** `dist-experimental/mpips-runtime.bin` (local build candidate only; not distributed or released on GitHub)
- **Format:** ELF 64-bit LSB executable, x86-64, dynamically linked, stripped.
- **File Size:** `241,288,024` bytes (~230.1 MiB).
- **Verified Candidate SHA-256 Digest:**
  ```text
  189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937
  ```
  *(Recorded in `dist-experimental/mpips-runtime.bin.sha256`; supersedes the earlier `236,532,616`-byte candidate `8ef48229d72adaa4eb9df832a5315e2ecf42abb448f78c2674c330d964004669`).*
- **GLIBC Symbol Version Requirements (`objdump -T` / `readelf -V`):**
  1. **ELF Bootloader (`dist-experimental/mpips-runtime.bin`):** Requires `GLIBC_2.2.5`, `GLIBC_2.3`, `GLIBC_2.3.4`, `GLIBC_2.4`, `GLIBC_2.7`, `GLIBC_2.14` (maximum bootloader symbol version: `GLIBC_2.14`).
  2. **Bundled Shared Libraries (`152` `.so` libraries in PyInstaller archive):** Require symbol versions `GLIBC_2.2.5` through `GLIBC_2.38` (maximum bundled shared-library symbol version: **`GLIBC_2.38`**, observed in `libstdc++.so.6`).
  3. **Execution on Ubuntu 24.04 LTS (`noble`, `glibc 2.39`):** Confirmed compatible on Ubuntu 24.04.2 LTS (`Ubuntu GLIBC 2.39-0ubuntu8.4`), which satisfies both the outer bootloader (`<= GLIBC_2.14`) and all bundled native libraries (`<= GLIBC_2.38`).
- **Ubuntu 24.04 Container & Clean-Environment Qualification:**
  - **Container Image Identity:** Qualified against `ubuntu:24.04` (Ubuntu 24.04 LTS `noble` x86_64, `glibc 2.39`). An immutable Docker image digest (`sha256:...`) was not recorded in the original qualification log and is not claimed here because the local Docker daemon was offline during evidence reconciliation.
  - **No External Python Runtime Required:** Confirmed inside a clean container and via scrubbed environment invocation (`/usr/bin/env -i PATH=/usr/bin:/bin ./mpips-runtime.bin --version` returning `{"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}` and `convert` from `/tmp` with zero `PYTHON*` or `.venv` variables and no system `python3` invoked by the binary).
  - **Physical Hardware Qualification:** **NOT CLAIMED / PENDING.** Qualification was performed in container and WSL 2 environments only, not on physical bare-metal hospital Grabber hardware.
- **Designated Real TRX Asset Provenance:**
  - Archive: `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz`
  - Archive SHA-256: `2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556` (exact match verified by pre-build gate)
  - Remap SHA-256: `32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893`
  - Fingerprint: `606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d`
  - Profile ID: `GOTRI-TRX-001`, Detector Mode: `TRX`, Camera Serial: `DA5234480`, Camera Model: `MV-CH120-10UM`, Image Shape: `3000 x 4096`
  - Embedded BED Profile: `SYNTHETIC-EMBEDDED-BED-CALIBRATION-V1` (`48 x 64`, `SYNTHETIC_DEVELOPMENT_ONLY`, remap SHA-256 `57749f83ba9bd0704347a0c41cd4e454ed87829c00314f4948b3e9f03d2a7ddc`)
  - Scope: `LOCAL_REAL_TRX_ACCEPTANCE`
- **Protected Converter:** `mpips/conversion/tiff_json_to_dcm.py` verified unmodified (SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`).
- **Release Status:** Gate **G10 remains NOT RELEASED**. No external distribution or PR merge is authorized.

---

## 2. Separate Acceptance Verdicts

| Dimension | Verdict | Evidence / Observed Result |
|---|---|---|
| **One-file Standalone ELF Build** | **PASS** | Dynamic PyInstaller specs (`SPECPATH`-relative) preceded by `prepare_calibration_bundle.py` validation gate successfully built `241,288,024`-byte (~230.1 MiB) stripped ELF binary into `dist-experimental/mpips-runtime.bin`. |
| **Embedded Real TRX Calibration Provenance** | **PASS** | Source archive hash verified against `2871e78f...`. Embedded metadata and remap array validated with SHA-256 integrity checks directly by worker child process. Large assets excluded from Git. |
| **Full-Resolution Synthetic TRX Conversion** | **PASS** | 3000 x 4096 synthetic inputs processed through real TRX geometry into valid DICOM with 4096 x 3000 rotated uint16 pixel array in ~53s (~24.5 MiB DICOM). |
| **Synthetic BED Regression** | **PASS** | Small synthetic BED test fixtures continue to convert without `--calibration` and pass regression invariants. Deterministic synthetic BED coordinate grid generated cleanly. |
| **Grabber Adapter Compatibility** | **PASS** | `MPIPSSubprocessAdapter` enforces contract differences: interface negotiation verifies version; interface 1 requires calibration; interface 2-experimental uses embedded calibration and strictly rejects external `--calibration`. 27/27 adapter unit tests passed. |
| **Clean-Host Environment Isolation** | **PASS (Env-Isolated) / PENDING (Physical Clean Host)** | Subprocess execution verified under environment isolation (`env -i PATH=/usr/bin:/bin` from `/tmp`) with all Python/repo environment variables scrubbed. Physical or containerized execution without Python installed remains pending. |
| **Negative & Security Cases** | **PASS** | Strict fail-closed verification of camera serial identity, detector mode, remap hash, and fingerprint. Negative tests for wrong/missing serial, bad fingerprint, altered remap, missing remap, substitute TRX profile bypass attempts, external calibration override rejection in interface 2, and unhandled Linux RLIMIT_CPU failure all pass. File mode `0600` enforced. |
| **Repository Regression & CI** | **PASS (CI Suite) / LOCAL ONLY (.bin Execution)** | Standard CI suite passes completely on GitHub Actions (Black, Flake8, Mypy regression gate, pytest, Docker builds, smoke tests). Standalone binary execution is qualified strictly locally with `MPIPS_STRICT_QUALIFICATION=1`. |

---

## 3. Calibration Contract & Selection Safety

1. **Deterministic Matching & Fail-Closed Behavior:**
   - Radiograph metadata must match detector mode (`TRX`) and camera serial (`DA5234480`).
   - If radiograph specifies an incompatible serial (e.g., `WRONG-SERIAL-9999`), the internal worker raises `NPZ_VALIDATION_ERROR` and the top-level `mpips-runtime.bin` CLI exits with code `2` (`INVALID_INPUT`).
   - Top-level `mpips-runtime.bin` CLI exit and JSON `code` contract:
     - `0` -> `OK`
     - `2` -> `INVALID_INPUT`
     - `3` -> `INPUT_NOT_FOUND`
     - `4` -> `OUTPUT_EXISTS`
     - `5` -> `CONVERSION_TIMEOUT`
     - `6` -> `IO_ERROR`
     - `7` -> `CONVERSION_FAILED`
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
======================== 12 passed in 114.54s ========================
```

### Subprocess Adapter Suite
Command: `.venv/bin/pytest tests/test_grabber_subprocess_adapter.py -v`
```text
============================= 27 passed in 10.82s ==============================
```

### Packaged Grabber E2E Regression
Command: `.venv/bin/pytest tests/test_packaged_grabber_e2e.py -v`
```text
============================= 11 passed in 31.42s ==============================
```

### Full Local Test Suite
Command: `.venv/bin/pytest -q`
```text
1076 passed, 315 warnings in 442.57s
```

### Canonical Converter Immutability
Command: `.venv/bin/pytest tests/test_converter_protection.py -v`
```text
============================== 1 passed in 0.03s ===============================
```

### Offline Integrated Update-Server & Real ELF Acceptance
Command: `MPIPS_STRICT_QUALIFICATION=1 .venv/bin/pytest tests/test_grabber_update_flow_simulation.py -v`
```text
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_successful_update_and_conversion PASSED [  9%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_unauthenticated_request PASSED [ 18%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_invalid_token PASSED [ 27%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_older_or_equal_sequence PASSED [ 36%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_invalid_signature_before_download PASSED [ 45%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_corrupted_sha256_preserves_runtime PASSED [ 54%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_incompatible_platform PASSED [ 63%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_failed_self_check_preserves_runtime PASSED [ 72%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_failed_synthetic_conversion_preserves_runtime PASSED [ 81%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_network_isolation_no_live_egress PASSED [ 90%]
tests/test_grabber_update_flow_simulation.py::test_real_update_server_and_real_elf_offline_integrated_acceptance PASSED [100%]
======================== 11 passed in 95.52s (0:01:35) =========================
```
- **Distinction Between Mock Protocol Simulation Tests (1–10) and Genuine ELF + Real Server Acceptance Test (11):**
  - **Mock Protocol Tests (`test_protocol_simulation_*`, 10 tests):** Use `MockUpdateServerFixture` and lightweight mock executable scripts (`_create_mock_runtime_script`) to test protocol edge cases: successful mock promotion, unauthenticated request rejection (`401`), invalid token rejection (`401`), older/equal sequence rejection, invalid Ed25519 signature rejection prior to download, corrupted SHA-256 download rejection, incompatible platform rejection (`422`), failed `--version` self-check rejection, failed synthetic conversion rejection, and Python-level `socket.create_connection` loopback egress blocking.
  - **Genuine ELF + Real Update-Server Test (`test_real_update_server_and_real_elf_offline_integrated_acceptance`, 1 test):**
    1. Hosted the real `mpips.update_server.app:create_update_server_app` (`ReleaseRegistry`, `ClientAuthenticator`, `MinIOArtifactStore`) backed by `LocalIsolatedS3Client` (simulated local loopback S3 storage, not a live MinIO instance) with a disposable Ed25519 keypair and synthetic `staging-reader` bearer token.
    2. Verified initial `status: "no_release"` (`run_checks(..., mode="infra") is True`, `mode="distribution"` is `False`, and first-bootstrap rejection when no valid runtime is installed).
    3. Registered, authorized, and promoted the genuine `241,288,024`-byte `dist-experimental/mpips-runtime.bin` (`189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) as `release_id: "0.1.0-real-elf-staging-r11"` (`sequence: 11`), and verified `run_checks(..., mode="distribution") is True`.
    4. Executed `simulate_grabber_update_flow` to discover `/mpips/staging/latest.json`, verify the 64-byte Ed25519 signature over `signed_metadata_b64` and all 12 `SIGNED_METADATA_KEYS`, call `/mpips/staging/releases/0.1.0-real-elf-staging-r11/download`, validate the loopback storage host and `StrictNoRedirectHandler`, stream all `241,288,024` bytes, verify exact byte length and SHA-256, run `--version` and synthetic BED smoke conversion, and atomically replace `installed_bin` (`os.replace`).
    5. Executed the downloaded ELF `--version` in a scrubbed environment (`/usr/bin/env -i PATH=/usr/bin:/bin`), confirming exact JSON output `{"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}`.
    6. Parsed a synthetic SIMRS response (`visit_id = "SYNTHETIC-VISIT-2026-0777"`, `no_rkm_medis = "SYNTHETIC-MRN-0777"`), verified `SIMRSConfirmationRequiredError` when `confirmed=False`, and generated confirmed BED (`48 x 64`) and full-resolution TRX (`3000 x 4096`, `DA5234480`, `MV-CH120-10UM`) manifests and NPZ inputs.
    7. Invoked the downloaded real ELF without `--calibration` to produce both BED DICOM (`(48, 64)` `uint16`, mode `0600`) and full-resolution TRX DICOM (`(4096, 3000)` `uint16`, mode `0600`, `Modality = "DX"`, `PatientID = "SYNTHETIC-MRN-0777"`).
    8. Verified deterministic CLI failure codes on the downloaded real ELF: external `--calibration` override rejected with exit code `2` (`INVALID_INPUT`), existing output path rejected with exit code `4` (`OUTPUT_EXISTS`), and missing input file rejected with exit code `3` (`INPUT_NOT_FOUND`).
    9. Registered a subsequent `release_id: "0.1.0-real-elf-staging-r12"` (`sequence: 12`), injected stream corruption (`srv.corrupt_storage_stream = True`), confirmed `GrabberUpdateError` (`SHA-256 mismatch`), verified cleanup of `candidate_runtime.tmp`, and confirmed the installed `sequence: 11` real ELF remained intact (`241,288,024` bytes, SHA-256 `189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) and passed `adapter.check_version()`.
  - **Explicit Simulation Boundaries:** The test harness does not implement durable `state.json` persistence with `fsync`, does not perform post-activation rollback (because activation only occurs after pre-promotion `--version` and synthetic smoke conversion succeed), uses a Python-level socket guard rather than kernel-level network namespaces, and uses `LocalIsolatedS3Client` rather than a live MinIO server.
