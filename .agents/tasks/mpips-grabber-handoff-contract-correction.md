---
title: MPIPS Grabber Handoff Contract Final Correction
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS Grabber Handoff Contract Final Correction (Milestone 4A Bounded Final Correction)

**Task path:** `.agents/tasks/mpips-grabber-handoff-contract-correction.md`

**Task contract state:** Validated/Published. Semantic readiness satisfied; published for final contract correction execution.

**Delivery objective:** Complete final bounded contract corrections for the Grabber developer handoff kit and subprocess adapter:
1. Manifest doc: Allowed `patient.sex` values are exactly `male`, `female`, `other`, `unknown`. Remove claim of case-insensitive support.
2. Sanitized error messages: Ensure exceptions never interpolate untrusted runtime response fields or patient-identifying filenames. Keep errors deterministic and sanitized. Add malicious-response regression tests.
3. Strict exit code to JSON status/code mapping: Validate every supported nonzero exit code (2: INVALID_INPUT, 3: INPUT_NOT_FOUND, 4: OUTPUT_EXISTS, 5: CONVERSION_TIMEOUT, 6: IO_ERROR, 7: CONVERSION_FAILED) against its exact expected JSON `code` and `status == "error"`. Reject mismatches without leaking untrusted response. Add regression tests.
4. Exception chaining / path shielding: Preserve internal diagnostics while shielding command arguments and private paths in traceback / string representations.

**Owner / designated planning authority:** Designated user instruction of 2026-10-16 ("MPIPS — Final Bounded Handoff Contract Correction").

## Delivery context

PR #19 resolved earlier remediation points. This final task addresses three remaining contract consistency items identified in independent review to conclude Milestone 4A.

## Baseline and task revision

**Implementation baseline:**
`0b08945fca7a2281526c2297c8c814117c203520` (verified `main` HEAD).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Objective

Harden contract alignment and exception sanitization:
- Update `docs/integration/grabber-handoff-kit/README.md` to state exact allowed values for `patient.sex`.
- Update `scripts/grabber_subprocess_adapter.py` with sanitized error messages, exact exit-code-to-JSON-code validation mapping, and sanitized response storage.
- Add regression tests in `tests/test_grabber_subprocess_adapter.py` for malicious response content, exit code / JSON code mismatches, and exact sex values.
- Update evidence in `.agents/evidence/mpips-grabber-developer-handoff-kit.md`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-SEX-EXACT | Document exact `patient.sex` allowed values (`male`, `female`, `other`, `unknown`) without unverified case-insensitivity claims | MPIPS | Guide documentation & schema test |
| REQ-ERR-SANITIZE | Error messages and exceptions never interpolate untrusted response fields or private filenames | MPIPS | Subprocess adapter & malicious response test |
| REQ-EXIT-MAP | Validate every nonzero exit code (2..7) against exact expected JSON code and status `error` | MPIPS | Subprocess adapter & mismatch unit tests |
| REQ-SAFETY | Converter immutability (`a4a30866...`), G10 NOT RELEASED | MPIPS | Converter hash check & clean CI |

## Scope and constraints

- **In Scope:** `docs/integration/grabber-handoff-kit/README.md`, `scripts/grabber_subprocess_adapter.py`, `tests/test_grabber_subprocess_adapter.py`, `.agents/evidence/mpips-grabber-developer-handoff-kit.md`.
- **Out of Scope:** Core converter changes, new packaging formats, external binary distribution, G10 release.
