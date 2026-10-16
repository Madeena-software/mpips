---
title: MPIPS Grabber Developer Handoff Kit Remediation
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS Grabber Developer Handoff Kit Remediation (Milestone 4A Bounded Remediation)

**Task path:** `.agents/tasks/mpips-grabber-handoff-kit-remediation.md`

**Task contract state:** Validated/Published. Semantic readiness satisfied; published for feature remediation execution.

**Delivery objective:** Remediate integration-contract, documentation, and subprocess-safety defects in the developer handoff kit and subprocess adapter without expanding scope, changing converter logic, or authorizing release.

**Owner / designated planning authority:** Designated user instruction of 2026-10-16 ("MPIPS Milestone 4A — Bounded Handoff Kit Remediation").

## Delivery context

PR #18 established the initial Grabber Developer Integration Handoff Kit. Review confirmed 7 specific remediation obligations:
1. Manifest documentation: `patient.sex` accepts `male`, `female`, `other`, `unknown` (mapping to DICOM `M`, `F`, `O`, `""`), verified against `PatientSchema`.
2. Output path handling: Check `output.exists() or output.is_symlink()` on raw path directly to prevent `resolve()` from following dangling symlinks to newly writable targets, preserving runtime's no-overwrite guarantee.
3. Harden runtime response validation: Require single dict with expected keys, validate `interface_version == "1"` and `status == "ok"` matching exit 0, ensure error exit codes match JSON code/status, sanitize exceptions (no raw stdout/patient data leaks).
4. Validate and test timeout handling: Implement clean subprocess kill (`proc.kill()` and `proc.wait()`), test timeouts with mocked slow process, document worker lifecycle limitations.
5. Correct distribution documentation: State only verified Ubuntu targets (Ubuntu 24.04 LTS x86_64), explain unsigned candidate vs signed production metadata, explain that Milestone 3 `.tar.gz` predates adapter, reinforce G10 NOT RELEASED.
6. Replace machine-specific `file://` links with portable repository-relative markdown links.
7. Reconcile evidence and tests: Add targeted tests for symlinks, malformed JSON, suspicious response keys, version mismatches, and timeouts.

## Baseline and task revision

**Implementation baseline:**
`34b658de7fc9078b74b92b7f3f42872aa462da05` (verified `main` HEAD).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Objective

Harden the developer handoff kit:
- Update `scripts/grabber_subprocess_adapter.py` with safe output path checks, response parsing guards, and clean process termination.
- Update `docs/integration/grabber-handoff-kit/README.md` with accurate manifest schema, distribution boundaries, and process lifecycle documentation.
- Add comprehensive unit tests in `tests/test_grabber_subprocess_adapter.py` covering symlinks, invalid JSON, response validation, and timeouts.
- Update evidence in `.agents/evidence/mpips-grabber-developer-handoff-kit.md`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REM-MANIFEST | Document exact `patient.sex` enum (`male`, `female`, `other`, `unknown`) and DICOM mapping | MPIPS | Guide documentation & schema test |
| REM-SYMLINK | Reject existing outputs and dangling symlinks before resolve | MPIPS | Subprocess adapter & symlink unit tests |
| REM-VALIDATE | Strict response validation (dict type, expected interface version, status/exit consistency, no leaks) | MPIPS | Subprocess adapter & response parsing unit tests |
| REM-TIMEOUT | Subprocess timeout enforcement with cleanup & documentation of worker limits | MPIPS | Subprocess adapter, timeout unit test, & guide |
| REM-DISTRIB | Verified Ubuntu 24.04 compatibility, candidate vs signed metadata, M3 tarball note | MPIPS | Guide documentation |
| REM-LINKS | Portable repository-relative links across handoff kit docs | MPIPS | Guide documentation |
| REM-SAFETY | Converter immutability (`a4a30866...`), G10 NOT RELEASED | MPIPS | Converter hash check & clean CI |

## Scope and constraints

- **In Scope:** `scripts/grabber_subprocess_adapter.py`, `docs/integration/grabber-handoff-kit/README.md`, `tests/test_grabber_subprocess_adapter.py`, `.agents/evidence/mpips-grabber-developer-handoff-kit.md`.
- **Out of Scope:** Core converter changes, new packaging formats, SIMRS HTTP client, hospital network connections, production releases.
