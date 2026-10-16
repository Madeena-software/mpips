# Synthetic Grabber End-to-End Simulation — Accepted Baseline Evidence (A9)

## Milestone Status and Gate Summary

- **Delivery Milestone:** Synthetic Grabber End-to-End Simulation
- **Protocol State:** Implementation Accepted (A9)
- **Release Gate Status (G10):** **NOT RELEASED** (No production deployment, workflow dispatch, server publication, external binary upload, clinical use, or live hospital network access occurred or is authorized).
- **Review Basis:** Independent conversational review PASS on implementation revision `dbf00e594a6455d82fb20a505de5fa6d04df11a9` (no blocking findings; no formal GitHub review approval claimed).

## Immutable Identities and Traceability

- **Repository:** `https://github.com/Madeena-software/mpips`
- **Governing Task:** `.agents/tasks/mpips-synthetic-grabber-e2e-simulation.md`
- **Governing Task Revision:** `4b3930c86c412044b6f8fb405e35057a2e574ab9`
- **Initial Implementation Baseline:** `1a25609f51ee5ed6b16b175bb387e3e960a5a276`
- **Accepted Implementation Revision:** `dbf00e594a6455d82fb20a505de5fa6d04df11a9`
- **Pull Request:** [#16 (Merged)](https://github.com/Madeena-software/mpips/pull/16)
- **Merged Development Baseline (main):** `e7a9c4391c24f942196dca6df2b31a78406e9331`
- **Protected Converter SHA-256:** `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` (`mpips/conversion/tiff_json_to_dcm.py` verified bitwise unchanged)

## Scope Implemented and Accepted

1. **Synthetic Grabber E2E Test Suite (`tests/test_grabber_e2e_synthetic.py`):**
   - Mock SIMRS lookup and synthetic candidate selection / visit confirmation gating.
   - Manifest composition: SIMRS-derived mapper identity is retained, with test-owned Grabber capture and DICOM metadata added for BED/TRX without a generalized deep-merge mechanism.
   - Real subprocess execution of `python -m mpips.runtime convert` across both BED and TRX modes.
   - DICOM verification: standard SOP class (`1.2.840.10008.5.1.4.1.1.1.1.1`), 16-bit unsigned `MONOCHROME2`, dimensions (BED 48×64, TRX 64×48), zero private tags, mode `0600`.
   - Deterministic pixel oracle assertions using fixed pixel SHA-256 regression pins, shape, uint16 dtype, nonconstant values, mode-specific monotonicity, and repeat-run BED determinism; these pins serve as regression evidence, not an independent numerical correctness proof.
   - Pre-CLI rejection tests verifying that malformed SIMRS data, visit mismatches, unconfirmed selection, and schema-invalid manifests abort before invoking the converter runtime.
   - CLI boundary failure tests verifying observed exit codes 2 (`INVALID_INPUT`) and 3 (`INPUT_NOT_FOUND`) with sanitized error statuses across corrupt manifests, detector mode mismatches, gain shape/id mismatches, missing calibrations, and unvalidated calibrations.
   - Process safety & isolation: safe individual `pidfd` process verification (NUL-delimited exact environment matching, live `fdinfo` verification, `execve` transition retry), eliminating unsafe process-group signaling and handling detached worker cleanup on timeout.
   - Subprocess network prohibition guard using Python-level audit hooks (`sys.addaudithook`) with canary verification and role-scoped load sentinels.
2. **Documentation Update:**
   - Factual qualification update in `docs/integration/ubuntu-grabber.md`.

## Verification Evidence

### Local Execution (Adlan / WSL2)

- **Environment:** Ubuntu 24.04.2 LTS on WSL2 (`Linux Adlan 5.15.167.4-microsoft-standard-WSL2 #1 SMP x86_64`), Python 3.12.3 via `.venv` and `uv`.
- **Synthetic Grabber E2E Suite (`tests/test_grabber_e2e_synthetic.py`):**
  - Command: `uv run pytest tests/test_grabber_e2e_synthetic.py -v`
  - Exit code: `0`
  - Result: **27 passed in 38.69s**
  - All positive BED/TRX, guard canary, timeout/cleanup, negative pre-CLI, CLI exit codes, and determinism tests passed.
- **Baseline Integration Tests (`tests/test_local_runtime.py tests/test_simrs_reference.py`):**
  - Command: `uv run pytest tests/test_local_runtime.py tests/test_simrs_reference.py -q`
  - Exit code: `0`
  - Result: **26 passed in 14.01s** (3 deprecation warnings in pydicom).
- **Code Quality and Static Analysis:**
  - `uv run black --check tests/test_grabber_e2e_synthetic.py`: Passed (1 file left unchanged).
  - `uv run flake8 tests/test_grabber_e2e_synthetic.py`: Passed (clean).
  - `uv run mypy tests/test_grabber_e2e_synthetic.py`: Passed (Success: no issues found in 1 source file).

### Remote GitHub CI Verification (PR #16 at `dbf00e5`)

- **Workflow Run 38733740825 (MPIPS CI):**
  - Status: Completed **SUCCESS**
  - Job: `test-and-verify` (ID 116417663398) in 8m 24s.
  - Verified: Dependency audit, converter immutability SHA-256, Black, Flake8, Mypy regression gate, pytest suite, Docker API image build, Docker NPZ worker build, lifespan container smoke test.
  - URL: `https://github.com/Madeena-software/mpips/actions/runs/38733740825`
- **Workflow Run 38733740824 (Qualify Ubuntu Local Runtime Candidate):**
  - Status: Completed **SUCCESS**
  - Job: `qualify` (ID 116417662931) in 4m 42s.
  - Verified: Dependency audit, converter protection, wheel build, offline install, and synthetic BED/TRX DICOM execution.
  - URL: `https://github.com/Madeena-software/mpips/actions/runs/38733740824`

## Stated Technical Limitations

1. **Synthetic-Only Data:** All test fixtures, patient IDs, visit IDs, accessions, and calibrations use explicitly synthetic and fictional values (`SYNTHETIC-*`). Clinical datasets, hospital SIMRS databases, and Google Drive collections were strictly excluded.
2. **Plumbing Qualification Only:** Synthetic identity-remap calibrations (`SYNTHETIC-IDENTITY-REMAP`) validate pipeline plumbing, data exchange, and process boundaries; they do not certify clinical diagnostic quality or physical detector geometry.
3. **Network Guard Boundary:** Subprocess network prohibition is enforced at the Python runtime level using `sys.addaudithook`. It is not kernel-level network namespace isolation (`unshare`/`cgroups`) and does not guard raw non-Python or C-extension sockets that bypass Python audit events.
4. **Release Gate (G10):** This milestone represents test/qualification and development baseline acceptance only. Release Gate G10 remains **NOT RELEASED**.
