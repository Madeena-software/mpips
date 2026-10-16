---
title: Standalone Binary Review and Real TRX Calibration Integration
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** Standalone Binary Review and Real TRX Calibration Integration (Milestone 5 Real TRX Extension)

**Task path:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md`

**Task contract state:** Validated/Published. Semantic readiness satisfied; published for execution.

**Delivery objective:** Integrate the designated real TRX calibration asset (`trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz`, SHA-256 `2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556`) into the standalone Linux ELF executable `mpips-runtime.bin`. Embed the real TRX profile into the binary bundle (while preserving synthetic BED for synthetic-only test fixtures). Implement deterministic fail-closed calibration selection based on detector mode, camera serial identity (`DA5234480`), image shape (3000 x 4096), and calibration integrity/fingerprint. Update Grabber subprocess adapter with an explicitly version-aware integration strategy for interface 1 and experimental interface. Build the candidate without hardcoded machine paths in PyInstaller specs. Qualify full-resolution (3000 x 4096) synthetic TRX conversion using real geometry and negative tests on an isolated Ubuntu 24.04 x86_64 host without Python environment dependencies. Preserves converter immutability and existing TAR baseline. Gate G10 remains NOT RELEASED.

**Owner / designated planning authority:** Designated user instruction of 2026-10-16 ("MPIPS — Standalone Binary Review and Real TRX Calibration Integration").

## Delivery context

1. Verify archive `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz` provenance and SHA-256 (`2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556`).
2. Do not commit large binary calibration assets to Git (maintain `.gitignore` entries for calibration archives and extracted real assets).
3. Embed validated real TRX calibration profile (`metadata.json`, `remap.npz`) into PyInstaller frozen bundle.
4. Enhance calibration selection and validation in `mpips/conversion/worker.py` and `mpips/standalone_runtime.py` to enforce deterministic matching (detector mode, camera serial, image shape, fingerprint).
5. Ensure Grabber adapter (`scripts/grabber_subprocess_adapter.py`) supports version-aware execution: supports both interface 1 (with `--calibration`) and experimental interface (without `--calibration`), parsing responses without globally relaxing checks.
6. Make PyInstaller spec paths dynamic relative to `REPO_ROOT` (no hardcoded `/var/www/mpips`).
7. Execute full-resolution (3000 x 4096) TRX synthetic tests through real geometry with performance and memory measurements.
8. Qualify on clean host environment without Python or source repo access.

## Baseline and task revision

**Implementation baseline:**
`e55cd7685b487e89af6bf94fdc906b6001149987` (HEAD of `feat/standalone-bin-prototype`).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-REAL-TRX-PROVENANCE | Verify archive hash `2871e78f...` and inspect metadata (`DA5234480`, `MV-CH120-10UM`, `3000x4096`, fingerprint `606db560...`) | MPIPS | Provenance check & test fixture |
| REQ-SPEC-PORTABILITY | Remove hardcoded paths from `mpips_dir.spec` and `mpips_onefile.spec` | MPIPS | Spec file inspection & reproducible build |
| REQ-CALIB-FAIL-CLOSED | Calibration selection matches detector mode, camera serial, image shape, fingerprint; fails closed on ambiguity or mismatch | MPIPS | Worker validation unit & integration tests |
| REQ-ADAPTER-COMPAT | Version-aware `MPIPSSubprocessAdapter` supporting interface 1 and experimental interface without `--calibration` | MPIPS | Adapter test suite covering both interfaces |
| REQ-FULL-RES-QUALIFY | Run full-resolution 3000 x 4096 TRX synthetic conversion through `mpips-runtime.bin`; verify DICOM, memory, dimensions, orientation | MPIPS | Full-resolution automated qualification test |
| REQ-CLEAN-HOST-QUALIFY | Qualify binary execution in environment isolated from system Python and repo source | MPIPS | Subprocess execution with purged environment |
| REQ-SAFETY-GOV | Converter immutability (`a4a30866...`), real assets kept out of Git, G10 NOT RELEASED | MPIPS | Git status, hash verification, clean boundaries |

## Scope and constraints

- **In Scope:** Embedding verified real TRX calibration, dynamic PyInstaller specs, calibration selection hardening, adapter interface adaptation, full-resolution tests, qualification evidence report.
- **Out of Scope:** Clinical deployment, committing real calibration assets to Git, modifying `mpips/conversion/tiff_json_to_dcm.py`, releasing G10.
