# Evidence Report: Milestone 4A Final Grabber Handoff Contract Corrections

## Baseline & Task Identity
* **Task**: [`.agents/tasks/mpips-grabber-handoff-contract-correction.md`](../tasks/mpips-grabber-handoff-contract-correction.md)
* **Starting Baseline**: `0b08945fca7a2281526c2297c8c814117c203520`
* **Branch**: `fix/grabber-handoff-contract-correction`
* **Status**: Execution complete; all 48 unit, regression, and adapter tests pass.

---

## Final Contract Corrections

1. **Exact `patient.sex` Schema Alignment**:
   * Updated [`docs/integration/grabber-handoff-kit/README.md`](file:///var/www/mpips/docs/integration/grabber-handoff-kit/README.md) to document that `patient.sex` accepts exactly `"male"`, `"female"`, `"other"`, and `"unknown"`.
   * Removed claim of case-insensitivity without implemented and tested normalization.

2. **Sanitized Exception Messages & Malicious Response Shielding**:
   * Hardened `scripts/grabber_subprocess_adapter.py`: Exception messages never reflect untrusted response fields or raw stdout.
   * Path conflict exceptions use sanitized static messages (`"Destination DICOM output already exists or is a symlink"`) without echoing caller-supplied filenames in exception message strings.
   * Suppressed exception chaining (`from None`) on subprocess timeouts and JSON decode errors to avoid exposing internal command arguments or private paths in tracebacks.
   * Added unit test `test_adapter_rejects_malicious_or_leaking_response` verifying that script tags, arbitrary injection strings, and private paths are never reflected in error messages.

3. **Strict Nonzero Exit Code to JSON Code/Status Mapping**:
   * Enforced validation of every supported nonzero exit code against its exact JSON code and `status == "error"`:
     * Exit `2` $\to$ `INVALID_INPUT`
     * Exit `3` $\to$ `INPUT_NOT_FOUND`
     * Exit `4` $\to$ `OUTPUT_EXISTS`
     * Exit `5` $\to$ `CONVERSION_TIMEOUT`
     * Exit `6` $\to$ `IO_ERROR`
     * Exit `7` $\to$ `CONVERSION_FAILED`
   * Added parameterized regression test `test_adapter_validates_all_supported_exit_code_mappings` verifying that any code/status mismatch fails closed with a sanitized `MPIPSRuntimeError`.

---

## Verification Evidence
* **Subprocess Adapter Suite**: 20 of 20 tests passed (`tests/test_grabber_subprocess_adapter.py`).
* **Converter Protection**: 1 passed (`tests/test_converter_protection.py`).
* **Synthetic Grabber E2E**: 27 passed (`tests/test_grabber_e2e_synthetic.py`).
* **Static Analysis**: `flake8` and `black --check` passed cleanly with 0 errors.
* **Typing Checks**: MyPy regression check passed with 0 new errors.
* **Converter Immutability**: SHA-256 confirmed unchanged: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

---

## Boundaries & Release Gate
* **G10 Release Gate**: **NOT RELEASED**.
* Output package remains a development candidate.
* Zero clinical data or external network endpoints accessed.
