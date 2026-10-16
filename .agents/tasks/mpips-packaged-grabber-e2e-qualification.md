---
title: Packaged Synthetic Grabber End-to-End Qualification
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** Packaged Synthetic Grabber End-to-End Qualification (Milestone 4B)

**Task path:** `.agents/tasks/mpips-packaged-grabber-e2e-qualification.md`

**Task contract state:** Validated/Published. Semantic readiness satisfied; published for execution.

**Delivery objective:** Prove that the existing MPIPS development-candidate offline wheelhouse TAR package (`mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`) can be installed offline and used by the current `MPIPSSubprocessAdapter` from accepted main baseline to execute a complete synthetic examination workflow (mock SIMRS $\to$ operator confirmation $\to$ manifest composition $\to$ synthetic radiograph+gain NPZ $\to$ validated DICOM for BED & TRX) plus representative failure and security cases. Implementation-only; no release or production effect.

**Owner / designated planning authority:** Designated user instruction of 2026-10-16 ("MPIPS — Packaged Synthetic Grabber E2E Qualification").

## Delivery context

Milestone 3 generated and qualified a local candidate TAR package on the host Windows/WSL desktop. Milestone 4A delivered and hardened the Grabber Developer Integration Handoff Kit and `MPIPSSubprocessAdapter`. This task integrates both:
1. Verifies the candidate package source commit (`ebda70638a64294b6b794d6c3e862ce10b909d4d`), package size, SHA-256 against `.release.json`, and archive integrity.
2. Extracts and installs the package offline into an isolated temporary Python 3.12 virtual environment without network index access (`--no-index`, `--require-hashes`).
3. Uses the repository's `MPIPSSubprocessAdapter` to execute synthetic BED and TRX examinations using the installed runtime binary.
4. Validates full workflow: mock SIMRS response, patient identity verification, operator confirmation, manifest creation, calibration mapping, DICOM attributes, orientation (clockwise 90-degree for TRX), and file mode `0600`.
5. Validates integration failures (unconfirmed selection, invalid manifest, missing gain, conflicting output, dangling symlink, malicious response shielding).
6. Preserves candidate package and converter immutability.

## Baseline and task revision

**Implementation baseline:**
`58168270236c2fdd8d5c3dddf75ddd8575333dae` (verified `main` HEAD).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-PKG-VERIFY | Verify candidate package exists, matches metadata SHA-256 (`97ee9519...`) and size (`144103304`) | MPIPS | Automated verification fixture |
| REQ-PKG-INSTALL | Fresh offline installation into isolated venv with `--no-index`, `--require-hashes`, zero PyPI egress | MPIPS | Subprocess pip install check |
| REQ-PKG-E2E | Full synthetic workflow through `MPIPSSubprocessAdapter`: mock SIMRS, operator confirmation, manifest, NPZs, calibration $\to$ verified DICOM (BED & TRX) | MPIPS | Pytest suite against installed binary |
| REQ-PKG-NEGATIVE | Negative and security cases: unconfirmed patient, bad manifest, missing gain, existing output, dangling symlink, malicious response shielding | MPIPS | Pytest negative suite |
| REQ-PKG-SAFETY | Converter immutability (`a4a30866...`), candidate non-distribution status, G10 NOT RELEASED | MPIPS | Converter hash check & clean boundaries |

## Scope and constraints

- **In Scope:** Test script/suite `tests/test_packaged_grabber_e2e.py` or runner `scripts/verify_packaged_grabber_e2e.py`, evidence report `.agents/evidence/mpips-packaged-grabber-e2e-qualification.md`.
- **Out of Scope:** Modifications to core converter `mpips/conversion/converter.py` or runtime `mpips/runtime.py`; changes to calling Grabber application; external distribution; hospital network calls.
