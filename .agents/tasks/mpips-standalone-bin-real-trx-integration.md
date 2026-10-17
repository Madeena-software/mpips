---
title: Standalone Binary Review and Real TRX Calibration Integration
version: 1.2
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** Standalone Binary Review and Real TRX Calibration Integration (Targeted Remediation Revision 1.2)

**Task path:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md`

**Task contract state:** Validated/Published. Targeted review remediation contract published for execution.

**Delivery objective:** Remediate targeted review findings for PR #23:
1. Close Real TRX Validation Bypass:
   - In `mpips/conversion/worker.py`, ensure all TRX mode conversions use the designated approved embedded calibration (or enforce exact profile ID, serial `DA5234480`, detector mode `TRX`, image shape `(3000, 4096)`, fingerprint, and remap SHA-256 integrity).
   - In `mpips/standalone_runtime.py`, reject external `--calibration` override for interface 2-experimental.
   - Preserve legacy external calibration interface 1 contract.
   - Add regression tests attempting substitute TRX profiles with altered metadata/remap failing before image processing.
2. Reproducible Clean-Checkout Build:
   - In `build-standalone/scripts/prepare_calibration_bundle.py`, generate and verify the synthetic BED fixture deterministically on demand if missing from a clean checkout.
   - Strictly require authorized, hash-verified TRX archive (`2871e78f...`).
   - Fail before PyInstaller if any asset is missing or invalid.
   - Do not commit real calibration remap assets.
3. Enforce Worker Resource Limits:
   - Remove exception suppression around Linux RLIMIT_CPU initialization in `mpips/standalone_runtime.py` (`_internal_worker`) and `mpips/conversion/worker.py`.
   - Worker must fail safely before processing data if required Linux CPU resource limit cannot be established.
   - Add focused failure-path tests.
4. Adapter Contract:
   - In `scripts/grabber_subprocess_adapter.py`, enforce interface negotiation/pre-verification before conversion: interface 1 requires external calibration; interface 2-experimental uses embedded calibration contract (omits `--calibration`).
   - Preserve sanitized JSON status/error reporting.
5. Requalification:
   - Run targeted negative tests, rebuild standalone binary, run strict binary qualification (`MPIPS_STRICT_QUALIFICATION=1`), test adapter, converter protection, and legacy TAR regression.
   - Pass lint/mypy/CI, update evidence report with new SHA-256, push remediation commit to PR #23 without merging. Gate G10 remains NOT RELEASED.

**Owner / designated planning authority:** PR #23 Targeted Review Remediation Directive of 2026-10-16.

## Delivery context

1. Verify archive `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz` provenance and SHA-256 (`2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556`).
2. Synthetic BED fixture generated deterministically during pre-build preparation if absent.
3. Fail-closed real TRX validation in worker regardless of metadata spoofing.
4. Interface 2-experimental rejects external `--calibration` overrides.
5. Worker CPU resource limits enforced strictly without exception suppression.
6. Adapter explicitly negotiates/verifies expected interface contract before conversion.

## Baseline and task revision

**Implementation baseline:**
`db8eb9dcb904570aca698505ad53edc363b8d91d` (HEAD of PR #23).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-CLOSE-TRX-BYPASS | Scoped fail-closed enforcement for all TRX conversions in embedded mode; reject altered/substituted TRX metadata/remap; reject external `--calibration` in interface 2-experimental | MPIPS | Negative tests attempting substitute TRX profiles and `--calibration` overrides |
| REQ-REPRODUCIBLE-BUILD | Deterministic generation and verification of synthetic BED fixture; require hash-verified TRX archive; fail before PyInstaller if any asset missing/invalid | MPIPS | Pre-build script run on clean checkout test |
| REQ-ENFORCE-RESOURCE-LIMITS | Remove exception suppression on Linux worker RLIMIT_CPU initialization; fail safely before processing | MPIPS | Unit tests exercising Linux resource limit failure paths |
| REQ-ADAPTER-NEGOTIATION | Explicit interface verification/negotiation in adapter before conversion; interface 1 requires calibration, interface 2 uses embedded | MPIPS | Adapter unit and integration test suite |
| REQ-REQUALIFICATION-G10 | Rebuild binary, strict qualification pass, converter protection verified, CI green, G10 NOT RELEASED | MPIPS | Test suites, CI status, evidence doc |

## Scope and constraints

- **In Scope:** TRX validation bypass closure, reproducible synthetic BED fixture generation, resource limit enforcement, adapter interface verification, binary rebuild, strict qualification, evidence doc update.
- **Out of Scope:** Clinical deployment, merging PR #23, committing large calibration assets, modifying `mpips/conversion/tiff_json_to_dcm.py`, releasing G10.
