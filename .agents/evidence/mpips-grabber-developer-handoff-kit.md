# Evidence Report: Milestone 4A Grabber Developer Integration Handoff Kit Remediation

## Baseline & Task Identity
* **Remediation Task**: [`.agents/tasks/mpips-grabber-handoff-kit-remediation.md`](../tasks/mpips-grabber-handoff-kit-remediation.md)
* **Initial PR #18 Baseline**: `34b658de7fc9078b74b92b7f3f42872aa462da05`
* **Branch**: `fix/grabber-handoff-kit-remediation`
* **Status**: Execution complete; all 13 unit tests and 37 full regression tests passing.

---

## Remediation Details

1. **Manifest Documentation Corrections**:
   * Verified against `mpips/api/schemas/dicom.py` (`PatientSchema`).
   * Explicitly documented `patient.sex` enum: `"male"`, `"female"`, `"other"`, and `"unknown"`.
   * Explicitly documented mapping to DICOM `PatientSex` (`M`, `F`, `O`, and `""` empty string).

2. **Output Path Handling & Dangling Symlink Hardening**:
   * Updated `scripts/grabber_subprocess_adapter.py` to inspect `raw_out.exists() or raw_out.is_symlink()` *before* invoking `resolve()`.
   * Rejects existing files and dangling symlinks directly, preventing `resolve()` from bypassing checks to newly writable targets.
   * Added unit test `test_adapter_output_dangling_symlink_error` verifying rejection without creating or modifying the target.

3. **Harden Runtime Response Validation**:
   * Enforced single-line JSON output verification.
   * Enforced validation of required keys (`interface_version`, `runtime_version`, `status`, `code`).
   * Enforced `interface_version == "1"` check, failing closed with typed error on version mismatch.
   * Enforced status/code consistency (`status == "ok"` and `code == "OK"` on exit 0; `status == "error"` on non-zero exit).
   * Sanitized exception messages to shield raw stdout and patient data.
   * Added unit tests for malformed JSON, multi-line responses, missing keys, incompatible versions, and inconsistent status codes.

4. **Timeout Enforcement & Subprocess Lifecycle**:
   * Implemented clean process termination using `proc.kill()` and `proc.wait()` in `scripts/grabber_subprocess_adapter.py`.
   * Added unit test `test_adapter_timeout_enforcement_and_cleanup`.
   * Documented residual worker lifecycle limitations: while `mpips-runtime` process is terminated, detached worker descendants may persist until internal timeout (`MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS`, default 300s) expires. Recommended session grouping (`os.setsid`) if immediate descendant tree termination is required.

5. **Distribution Boundaries & Packaging Clarifications**:
   * Explicitly restricted qualified OS scope to **Ubuntu 24.04 LTS (`noble`)**.
   * Documented distinction between unsigned local candidate metadata (`.release.json`) and authenticated Ed25519-signed production metadata.
   * Clarified that Milestone 3 `.tar.gz` package predates the PR #18 adapter.
   * Reinforced **G10 Release Gate: NOT RELEASED**.

6. **Relative Markdown Links**:
   * Replaced machine-specific `file://` links in handoff documentation with repository-relative paths.

---

## Test & Verification Evidence

* **Adapter Tests**: 13 passed in `tests/test_grabber_subprocess_adapter.py` (including symlink, version check, timeout, and response error cases).
* **Synthetic E2E & Local Runtime Regression**: 37 passed in `tests/test_grabber_e2e_synthetic.py` and `tests/test_local_runtime.py`.
* **Converter Immutability**: `mpips/conversion/tiff_json_to_dcm.py` SHA-256 confirmed unchanged: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
* **Code Quality**: `flake8` and `black --check` passed cleanly with 0 errors.
