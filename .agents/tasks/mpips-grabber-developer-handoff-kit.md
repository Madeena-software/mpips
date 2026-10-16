---
title: MPIPS Grabber Developer Integration Handoff Kit
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS Grabber Developer Integration Handoff Kit (Milestone 4A)

**Task path:** `.agents/tasks/mpips-grabber-developer-handoff-kit.md`

**Task contract state:** Validated/Published. Semantic readiness satisfied; executable delivery contract published for feature branch execution.

**Delivery objective:** Milestone 4A: Prepare a discoverable, implementation-ready developer integration handoff kit for a separately developed, locally maintained Grabber application, without modifying the Grabber application, altering converter logic, or deploying to production.

**Owner / designated planning authority:** Designated user instruction of 2026-10-16 ("MPIPS — Milestone 4A: Grabber Developer Integration Handoff Kit").

## Delivery context

Milestone 3 successfully built and qualified a local candidate package (`mpips-0.1.0-ebda70638a64294b6b794d6c3e862ce10b909d4d-ubuntu24.04-x86_64-py312.tar.gz`) and verified complete offline installation, interface inspection, BED/TRX execution, and failure handling. The separate Grabber application developer needs a self-contained, concrete integration kit in the repository:
1. Clear Ubuntu/Python 3.12 prerequisites and offline wheelhouse installation contract.
2. Verified Python subprocess invocation adapter (`scripts/grabber_subprocess_adapter.py`) using argument vectors (no shell interpolation), exit code verification, and JSON status decoding.
3. Discoverable developer guide and acceptance checklist (`docs/integration/grabber-handoff-kit/README.md` and links from `docs/integration/ubuntu-grabber.md`).
4. Automated verification suite (`tests/test_grabber_subprocess_adapter.py`) testing the adapter against the real installed runtime with synthetic inputs.

## Baseline and task revision

**Implementation baseline:**
`ebda70638a64294b6b794d6c3e862ce10b909d4d` (verified `main` HEAD).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Objective

Deliver an implementation-ready Grabber Developer Integration Handoff Kit:
- A discoverable developer integration guide (`docs/integration/grabber-handoff-kit/README.md`) linking to the canonical architecture, contracts, manifest schema, and candidate package specifications.
- A clean, reusable, minimal Python subprocess adapter (`scripts/grabber_subprocess_adapter.py`) encapsulating `mpips-runtime convert` and `mpips-runtime --version` calls with timeout enforcement, argument vectors, exit-code validation, and structured error propagation.
- A developer integration acceptance checklist covering prerequisites, offline installation, manifest creation, calibration mapping, subprocess execution, DICOM verification, and failure scenarios.
- Complete regression and unit test verification in `tests/test_grabber_subprocess_adapter.py`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-KIT-GUIDE | Developer integration guide & discovery link | MPIPS | Formatted markdown in `docs/integration/grabber-handoff-kit/README.md` and `docs/integration/ubuntu-grabber.md` |
| REQ-KIT-ADAPTER | Python subprocess adapter (no shell, exit 0 & ok status validation, typed exceptions) | MPIPS | `scripts/grabber_subprocess_adapter.py` unit & synthetic smoke verification |
| REQ-KIT-CHECKLIST | Step-by-step synthetic integration acceptance checklist | MPIPS | Embedded in handoff guide with verifiable test steps |
| REQ-KIT-TESTS | Automated tests for adapter success, error handling, timeout, and output validation | MPIPS | Pytest suite `tests/test_grabber_subprocess_adapter.py` passing |
| REQ-KIT-SAFETY | Converter immutability, zero clinical data, G10 NOT RELEASED | MPIPS | Converter hash check and clean repository boundaries |

## Scope and constraints

- **In Scope:** `docs/integration/grabber-handoff-kit/README.md`, `scripts/grabber_subprocess_adapter.py`, `tests/test_grabber_subprocess_adapter.py`, cross-reference in `docs/integration/ubuntu-grabber.md`, evidence report in `.agents/evidence/mpips-grabber-developer-handoff-kit.md`.
- **Out of Scope:** Modifications to core converter `mpips/conversion/converter.py` or `mpips/runtime.py`; real SIMRS HTTP client; real detector acquisition hardware; clinical upload; external binary publishing or production release (G10 NOT RELEASED).

## Boundaries and stop conditions

- Never introduce real patient information or clinical data.
- Never modify the protected converter SHA-256 (`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`).
- Stop if unapproved external network dependencies are required.
