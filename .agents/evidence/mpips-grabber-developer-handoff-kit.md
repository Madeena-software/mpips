# Evidence Report: Milestone 4A Grabber Developer Integration Handoff Kit

## Baseline & Task Identity
* **Task**: `.agents/tasks/mpips-grabber-developer-handoff-kit.md`
* **Baseline**: `ebda70638a64294b6b794d6c3e862ce10b909d4d`
* **Branch**: `feat/grabber-integration-handoff-kit`
* **Status**: Execution complete; tests passing.

---

## Deliverables Summary

1. **Discoverable Developer Integration Guide**:
   * File: [`docs/integration/grabber-handoff-kit/README.md`](file:///var/www/mpips/docs/integration/grabber-handoff-kit/README.md)
   * Linked from canonical [`docs/integration/ubuntu-grabber.md`](file:///var/www/mpips/docs/integration/ubuntu-grabber.md).
   * Details: Supported platform, offline wheelhouse installation, directory layout recommendations, single-line JSON stdout contract, exit code table, and manifest/calibration separation rules.

2. **Verified Subprocess Adapter**:
   * File: [`scripts/grabber_subprocess_adapter.py`](file:///var/www/mpips/scripts/grabber_subprocess_adapter.py)
   * Details: Python subprocess adapter using argument arrays (no shell string interpolation), deterministic exit-code validation, pre-flight input/output checks, timeout enforcement, and sanitized exception hierarchy.

3. **Synthetic Acceptance Checklist**:
   * Embedded in `docs/integration/grabber-handoff-kit/README.md` Section 6.
   * Six actionable qualification domains: Python/OS, offline package, synthetic BED, synthetic TRX (with canonical 90-degree clockwise rotation), error handling, and privacy/calibration boundaries.

4. **Automated Test Suite**:
   * File: [`tests/test_grabber_subprocess_adapter.py`](file:///var/www/mpips/tests/test_grabber_subprocess_adapter.py)
   * Tests:
     - `test_adapter_check_version`: verifies `--version` query and `RuntimeInfo` parsing.
     - `test_adapter_convert_bed_synthetic`: verifies end-to-end BED execution to valid DICOM.
     - `test_adapter_convert_trx_synthetic`: verifies end-to-end TRX execution to valid DICOM.
     - `test_adapter_output_exists_error`: verifies prevention of overwriting existing outputs.
     - `test_adapter_missing_input_error`: verifies fast detection of missing inputs.
     - `test_adapter_invalid_input_error`: verifies structured error handling on malformed JSON.
   * Results: 6 of 6 tests passed in 16.07s.

---

## Full Regression Testing Results
* `tests/test_grabber_subprocess_adapter.py`: 6 passed.
* `tests/test_grabber_e2e_synthetic.py` & `tests/test_local_runtime.py`: 37 passed in 49.96s.
* Converter SHA-256 hash verified unchanged: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

---

## Boundaries & Release Gate
* **G10 Release Gate**: **NOT RELEASED**.
* Output package remains a development candidate.
* Zero clinical data or external network endpoints accessed.
