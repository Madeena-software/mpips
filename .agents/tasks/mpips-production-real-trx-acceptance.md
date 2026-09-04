---
title: MPIPS production real TRX acceptance
document_id: TASK-MPIPS-PRODUCTION-REAL-TRX-ACCEPTANCE
version: 1.0
status: Validated/Published
language: en-US
scope:
  - read-only Stage C production acceptance of canonical real THORAX TRX inputs
authority_note: This task authorizes only the bounded verifier and workflow below. It does not authorize production mutation, deployment, release, or external-system changes.
---

# Executable Task

## Task identity

**Task title:** MPIPS production real TRX acceptance

**Task path:** `.agents/tasks/mpips-production-real-trx-acceptance.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Stage C — real TRX functional production acceptance.

**Owner / designated planning authority:** Human operator / Planner-Reviewer handoff.

## Delivery context

Stage B structurally promoted the reviewed TRX calibration into production. Stage C must prove the pinned real-THORAX regression set through the already-running production MPIPS API without changing calibration or infrastructure.

## Baseline and task revision

**Implementation baseline:** `899383f42ed07a213df47cdb9a8668df1209f594`

**Task revision:** resolved as the immutable Git publication revision before implementation handoff.

## Objective

Create a read-only production verification path that downloads the canonical real TRX gain and three real THORAX radiographs, verifies exact input identity, sends all three cases through the running production MPIPS API, and accepts Stage C only when compatibility, conversion, DICOM structure, and catastrophic-collapse checks pass for every case.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- `artifacts/test-data/real-thorax-trx-da5277082.json`
- Stage B production result and runtime values supplied by the Planner

### Requirement traceability

- Read-only production verification → this validated task
- Canonical real-data identity and expected geometry → canonical manifest
- No calibration or infrastructure mutation → repository delivery contract and this task

## Scope

### In scope

- `.github/workflows/verify-production-real-trx.yml`
- `scripts/verify_production_real_trx.py`
- `tests/test_verify_production_real_trx.py`
- Reuse of `validate_real_thorax_inputs()`, `run_real_thorax_checks()`, `_real_dicom_structure()`, and `_real_dicom_image_acceptance()` from the reviewed promotion module where appropriate.

### Out of scope

- application runtime code or `scripts/promote_production_calibration.py` changes unless absolutely unavoidable
- calibration modification, promotion, rollback, deployment, restart/recreate, Docker/network mutation, secrets, permissions, GHCR, or BED real-data E2E
- clinical validation, diagnostic accuracy, or end-user MHCS workflow acceptance
- production workflow dispatch during implementation

### Preserved behavior

- Production runtime SHA: `dd7c21eead66a2c5396522a2310f5dd9cbd85b85`
- API image: `mpips-api:dd7c21eead66a2c5396522a2310f5dd9cbd85b85`
- Worker image: `mpips-npz-worker:dd7c21eead66a2c5396522a2310f5dd9cbd85b85`
- TRX fingerprint: `1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492`
- TRX source/remap geometry: `3000x4096` / `3045x4114`, expanded origin `[42,-73]`
- Stage B BED metadata/remap SHA256: `15741968305c7b74bc1c84f5487216f7e944cdeaace0150500ede4aa32326ecd` / `f5ae883bd17960a56c60add99d5e8d2f393ea9427ec5ce3fd1a5d0b920c671bb`
- Production API remains on `127.0.0.1:8014` and calibration remains unchanged.

## Dependencies and assumptions

### Dependencies

- `origin/main` remains at the implementation baseline after task publication.
- The running production API and multimode calibration are available.
- `gdown==6.1.0` or the established repository download mechanism is available in the workflow.

### Remaining approval requirements

- Human authorization is required before dispatching the production workflow.
- No release or deployment authorization is granted by this task.

## Required capabilities

- repository read/write
- shell and focused test execution
- Codebase Memory MCP for implementation discovery where useful
- Git publication for the task only, followed by workflow implementation

## Execution constraints

- Cheap read-only preflight MUST complete before any real-data download.
- Download exactly four canonical files to one temporary directory, through `.part` files; verify size, SHA256, and ZIP/NPZ integrity before final rename and before any pickle-bearing `np.load`.
- Do not print arrays or pixel contents, persist real inputs, or upload them as artifacts; always clean the temporary directory.
- Use only the canonical manifest as real-data authority.
- Use the existing production diagnostic `_direct()` path through `run_real_thorax_checks()`; do not duplicate acceptance semantics.
- Do not call `promote()`, `prepare_root_staging()`, `_switch_to_multimode()`, or `_rollback()`.
- Failure exits non-zero without retry, remediation, rollback, or production mutation.

## Acceptance criteria

- [ ] Workflow is `workflow_dispatch` only, runs on `[self-hosted, production]`, and uses the `mpips-internal-beta` concurrency group.
- [ ] Preflight requires exact runtime/image values, `GET /health` HTTP 200, TRX fingerprint/layout, multimode visibility, and Stage B BED hashes before download.
- [ ] Canonical manifest supplies exactly one gain and three cases; all four downloads use `.part`, exact size/SHA256, and ZIP/NPZ integrity validation before loading.
- [ ] All three cases pass compatibility, conversion, DICOM structure, and image acceptance; DICOM geometry is Rows `4114`, Columns `3045`, 2-D non-empty `uint16`, with zero ratio `< 0.5` and non-trivial spatial support.
- [ ] Post-check health, unchanged calibration/layout, `CALIBRATION_MUTATION=NO`, and temporary cleanup are required.
- [ ] Success emits exactly `PRODUCTION_REAL_TRX_ACCEPTANCE=PASS` and `FINAL_STAGE_C_CLASSIFICATION=PRODUCTION_REAL_TRX_ACCEPTANCE_PASS`.
- [ ] Tests prove the workflow and all safety, ordering, identity, three-case, acceptance, and cleanup requirements without contacting production.

## Verification requirements

### Required checks

- `pytest tests/test_verify_production_real_trx.py -q`
- focused existing promotion/manifest tests as affected
- Python compile check, Black, Flake8, and `git diff --check`
- mocked verifier tests must not hit production or persist real inputs

### Required evidence

Report the exact implementation revision/working-tree state, commands and observed results, changed files, workflow safety properties, and any verification gaps.

## Stop conditions

Stop and return to planning if the baseline changes, the canonical manifest is missing or contradictory, application/runtime code must change, any production mutation is required, any new secret/permission is needed, or the required existing acceptance helpers cannot be reused safely.

## Side-effect authorization

This task authorizes task publication and repository implementation only. It does not authorize production workflow dispatch, production API mutation beyond read-only conversion requests, calibration mutation, deployment, external-system mutation, or release.

## Expected terminal outcome

**Review Required**

Expected implementation classification: `PRODUCTION_REAL_TRX_ACCEPTANCE_VERIFIER_READY_FOR_REVIEW`.
