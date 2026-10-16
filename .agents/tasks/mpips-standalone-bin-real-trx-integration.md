---
title: Standalone Binary Review and Real TRX Calibration Integration
version: 1.1
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** Standalone Binary Review and Real TRX Calibration Integration (Remediation Revision 1.1)

**Task path:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md`

**Task contract state:** Validated/Published. Bounded review remediation contract published for execution.

**Delivery objective:** Remediate review findings for PR #23:
1. Implement pre-build calibration preparation and validation script (`prepare_calibration_bundle.py`) to verify source archive SHA-256 (`2871e78f...`), validate contents/metadata, generate manifest, and fail closed if calibration assets are missing/invalid before PyInstaller runs.
2. Implement strict runtime calibration validation in `mpips/conversion/worker.py` (exact profile ID, serial `DA5234480`, detector mode `TRX`, image shape, remap array and hash integrity) while preserving interface 1 external calibration contract. Add negative tests.
3. Update standalone qualification test suite with a strict qualification mode (`MPIPS_STRICT_QUALIFICATION=1`) that fails if `mpips-runtime.bin` is absent; cleanly distinguish test tiers.
4. Harden `MPIPSSubprocessAdapter` to enforce invocation contract differences (interface 1 requires calibration), validate versions safely without string leakage, handle timeouts with child process cleanup, and ensure worker resource limits fail safely on Linux.
5. Remediate qualification evidence doc (`mpips-standalone-real-trx-qualification.md`) and `.gitignore` (narrow `*.tar.gz`), maintaining G10 NOT RELEASED.

**Owner / designated planning authority:** PR #23 Review Remediation Directive of 2026-10-16.

## Delivery context

1. Verify archive `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz` provenance and SHA-256 (`2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556`).
2. Do not commit large binary calibration assets to Git. Narrow broad `*.tar.gz` rule to specific patterns.
3. Pre-build validation gate extracts and verifies real TRX calibration profile (`metadata.json`, `remap.npz`) and writes manifest before PyInstaller packaging.
4. Enhance calibration selection and validation in `mpips/conversion/worker.py` to enforce deterministic matching and array integrity.
5. Ensure Grabber adapter (`scripts/grabber_subprocess_adapter.py`) rejects missing calibration on interface 1, sanitizes errors, and cleans up timeouts.
6. Provide strict qualification mode for test suite when testing binary.
7. Update evidence documentation with accurate test classifications (`env -i` vs clean-host, review pending).

## Baseline and task revision

**Implementation baseline:**
`c9d0f67c8bb981440a480f59050a894b7d3e10b3` (HEAD of PR #23).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-CALIB-BUILD-INTEGRITY | Pre-build validation gate verifying archive SHA-256 `2871e78f...`, safe extraction, metadata/remap integrity, manifest generation | MPIPS | Build script pre-check & unit tests |
| REQ-CALIB-RUNTIME-INTEGRITY | Scoped fail-closed validation for embedded real TRX profile (identity, serial `DA5234480`, mode, shape, remap arrays/hash), preserving interface 1 | MPIPS | Negative tests for missing/wrong serial, bad fingerprint, altered/missing remap |
| REQ-QUAL-STRICT-ACCOUNTING | Strict qualification mode failing when binary missing; clear test tier accounting | MPIPS | Pytest with `MPIPS_STRICT_QUALIFICATION=1` |
| REQ-ADAPTER-SAFETY | Enforce interface 1 vs 2-experimental invocation contract; sanitize error strings; verify timeout cleanup & Linux resource limits fallback | MPIPS | Adapter test suite covering negative cases & resource limit checks |
| REQ-EVIDENCE-HYGIENE | Accurate evidence doc, narrowed `.gitignore`, G10 NOT RELEASED | MPIPS | File inspection, git status |

## Scope and constraints

- **In Scope:** Pre-build calibration validation, runtime integrity checks & negative tests, adapter contract hardening, strict test mode, evidence correction, gitignore narrowing.
- **Out of Scope:** Clinical deployment, merging PR #23, committing large calibration assets, modifying `mpips/conversion/tiff_json_to_dcm.py`, releasing G10.
