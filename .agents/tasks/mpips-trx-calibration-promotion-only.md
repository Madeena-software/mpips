---
title: TRX calibration promotion-only Stage B
document_id: TASK-MPIPS-TRX-CALIBRATION-PROMOTION-ONLY
version: 1.0
status: Validated/Published
language: en-US
scope:
  - structural production promotion of the reviewed TRX calibration
  - explicit separation of Stage B from Stage C real-THORAX acceptance
authority_note: This task authorizes only the bounded implementation scope below. Production mutation, deployment, release, and external-system changes remain unauthorized.
---

# Executable Task

## Task identity

**Task title:** TRX calibration promotion-only Stage B

**Task path:** `.agents/tasks/mpips-trx-calibration-promotion-only.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** TRX Stage B.3R — separate structural production calibration promotion from real-THORAX production acceptance.

**Owner / designated planning authority:** Human operator / Planner-Reviewer handoff.

## Delivery context

Production must gain the reviewed TRX calibration using the already TRX-capable deployed runtime. The deployed production runtime remains `dd7c21eead66a2c5396522a2310f5dd9cbd85b85` and has passed `CAMERA_INDEPENDENT_RUNTIME=PASS` and `TRX_PIPELINE_RUNTIME=PASS`. Production calibration remains legacy BED. The reviewed TRX carrier is established and validated. Production run `33020815690` was intentionally cancelled while downloading real-THORAX data after `PRE_DOWNLOAD_PREFLIGHT=PASS`, `CARRIER_VERIFICATION=PASS`, and `TRX_ARTIFACT_VALIDATION=PASS`, before promotion invocation; no calibration mutation was reached.

Real-THORAX functional acceptance is deferred to Stage C. The approximately 243 MB real-THORAX payload is not part of this task.

## Baseline and task revision

**Implementation baseline:** `392ceaecddbf9a26e277ebe526cbaf3b204c0b4d`

**Task revision:** resolved as the immutable Git publication revision before implementation handoff.

The implementation baseline must not silently advance during execution. If main moves after task publication, the Executor must stop and return to planning unless explicitly reconciled.

## Objective

Refactor the production calibration-promotion path so an explicit promotion-only Stage B path safely promotes the reviewed TRX calibration using production runtime provenance, legacy BED validation, reviewed TRX carrier validation, structural multimode staging, BED byte preservation, atomic mode switching, post-swap layout validation, and running-container calibration visibility, without downloading or processing real-THORAX data.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Established multi-mode calibration capability and current promotion implementation as observed implementation evidence
- Human/Planner decisions: production TRX availability is the immediate priority; real-THORAX acceptance is deferred to Stage C; no GHCR migration; BED real E2E deferred; application redeployment is not required

### Requirement traceability

- TRX Stage B.3R structural promotion → this Planner-defined delivery objective
- Production safety gates and rollback preservation → repository delivery contract and current promotion implementation
- Stage C deferral → explicit Human/Planner decision

## Scope

### In scope

Implementation may modify only:

- `.github/workflows/promote-production-calibration.yml`
- `scripts/promote_production_calibration.py`
- `tests/test_promotion_workflow.py`

An already-existing directly related promotion test file may be changed only when technically necessary for focused coverage.

Required behavior:

- Introduce an explicit `--promotion-only` execution path.
- Production Stage B downloads exactly the reviewed TRX calibration carrier and none of the real-THORAX gain or radiographs.
- Promotion-only requires `--promotion-only`, `--carrier`, `--active`, and `--summary`, but not `--real-data-dir`.
- Promotion-only does not invoke `validate_real_thorax_inputs`, `_run_local_trx_validation`, or `run_real_thorax_checks`.
- Existing real-THORAX helper functionality remains available for future Stage C.
- Runtime provenance, carrier validation, legacy BED byte identity, atomic switch, rollback, post-swap layout, and running-container visibility gates remain mandatory.

### Out of scope

- production workflow dispatch or calibration mutation
- application deployment, container restart/recreate, Docker build, networking, secrets, permissions, GHCR, or runtime image changes
- real-THORAX downloads, production E2E, or clinical image-quality validation
- BED real E2E or debugging
- calibration algorithm, threshold, or camera-validation changes

### Preserved behavior

Reviewed TRX identity must remain exact:

- fingerprint: `1979a66b7d83bc0f14c4ebdf7c8ad2e37b6f16d7ead3e1c089381af3e7dd1492`
- carrier file ID: `1TpiHJfM0EHEKvZ1rZ2VqSV0-k0ycrzCG`
- carrier size: `73915583`
- carrier SHA256: `b0d645233eb598c549a1b04fc24a1364f68b79cc0d0e0db51ac1936d7e11f90f`
- source shape: `3000x4096`
- remap shape: `3045x4114`
- expanded origin: `[42,-73]`
- expected later TRX DICOM shape: `4114x3045`

Preserve legacy BED bytes exactly, single runtime deployment, multimode lookup, camera-independent runtime behavior, TRX compatibility gates, rollback architecture, production calibration root/inode behavior, the read-only calibration mount, and existing real-THORAX tooling for Stage C.

## Dependencies and assumptions

### Dependencies

- The implementation baseline remains `392ceaecddbf9a26e277ebe526cbaf3b204c0b4d`.
- The reviewed TRX carrier and established TRX-capable runtime remain available.

### Approved assumptions

- Structural promotion does not require real-THORAX data.
- Existing real-THORAX helpers remain available for Stage C.

### Remaining approval requirements

- Human authorization is required before task publication commit/push.
- Production workflow dispatch, production mutation, deployment, and release require separate authorization and are not authorized by this task.

## Required capabilities

- repository read/write
- shell and focused test execution
- Codebase Memory MCP for implementation discovery where useful

## Execution constraints

- No production calibration path may be used by verification.
- No implementation may change runtime application code, calibration semantics, secrets, permissions, GHCR, or deployment.
- No real-THORAX dataset may be downloaded or required for structural promotion.
- Use established promotion, atomic switch, rollback, and multimode mechanisms.
- No production mutation is authorized.

Before any future Stage B production execution, require all of:

- `PRE_DOWNLOAD_PREFLIGHT=PASS`
- `PROMOTION_MANIFEST=PASS`
- `CARRIER_ID_CONFIGURATION=PASS`
- `API_KEY_CONFIGURATION=PASS`
- `CAMERA_INDEPENDENT_RUNTIME=PASS`
- `TRX_PIPELINE_RUNTIME=PASS`
- `LEGACY_BED_LAYOUT=PASS`
- `CARRIER_VERIFICATION=PASS`
- `TRX_ARTIFACT_VALIDATION=PASS`

Record BED pre-promotion SHA256 values. No production mutation may occur before these gates pass.

The future release operation, which this task does not authorize, changes `/var/www/mpips-runtime/calibration` from root-level `metadata.json` and `remap.npz` to `BED/metadata.json`, `BED/remap.npz`, `TRX/metadata.json`, and `TRX/remap.npz`. BED bytes must remain identical and TRX must be exactly the reviewed calibration.

## Acceptance criteria

- [ ] Production workflow has exactly one calibration payload download: the reviewed carrier.
- [ ] Workflow contains none of these real-THORAX file IDs: `1kI99se2CjzCgo4qInMEGUuJ-ZJZE3iQY`, `1ocIGsYS6RHIurhRuOwJCzSHTv-6STc_m`, `1G9HTPyJzYFHwbAfZ3SU0sL84k9A6i5BD`, `1Ft3OALtx_d3ua-z0DSS34jJmywaXjLu2`.
- [ ] Workflow does not invoke `--verify-real-input-only` or pass `--real-data-dir`.
- [ ] Promotion-only CLI does not require `real-data-dir`.
- [ ] Promotion-only does not invoke `validate_real_thorax_inputs`, `_run_local_trx_validation`, or `run_real_thorax_checks`.
- [ ] Runtime camera and TRX gates remain required.
- [ ] Invalid carrier stops before mutation.
- [ ] Exact BED byte preservation and atomic mode switching remain required.
- [ ] Container calibration visibility remains required; visibility failure continues through reviewed rollback.
- [ ] Successful structural result emits `PRODUCTION_TRX_CALIBRATION_AVAILABLE=PASS`.
- [ ] Real-TRX functional acceptance emits `DEFERRED_TO_STAGE_C` semantics, including `REAL_TRX_LOCAL_PIPELINE`, `REAL_THORAX_ACCEPTANCE`, and `REAL_THORAX_ALL_PASS`.
- [ ] Existing real-THORAX helper functions remain available.

Structural promotion success requires `ATOMIC_MODE_SWITCH=PASS`, `POST_SWAP_BED_BYTE_PRESERVATION=PASS`, `POST_SWAP_LAYOUT=PASS`, and `CONTAINER_CALIBRATION_VIEW=PASS` before recording `PRODUCTION_TRX_CALIBRATION_AVAILABLE=PASS`. That result means the reviewed TRX calibration is structurally available to the already TRX-capable production runtime; it does not mean real-THORAX, clinical, or BED functional acceptance.

After any post-mutation failure, rollback must restore the exact legacy BED state and preserve `ROLLBACK_BED_LAYOUT`, `ROLLBACK_BED_METADATA_SHA256`, `ROLLBACK_BED_REMAP_SHA256`, `ROLLBACK_BED_BYTE_IDENTITY`, and `ROLLBACK_RESULT` evidence. Rollback must not become manual repair.

## Verification requirements

### Required checks

- `pytest tests/test_promotion_workflow.py -q`
- Other directly affected focused tests
- Black
- Flake8
- Python compile check
- `git diff --check`
- A fixture/mocked CLI smoke test proving `python -m scripts.promote_production_calibration --promotion-only --carrier <fixture> --active <fixture> --summary <temporary summary>` does not require `--real-data-dir`

No verification command may point to production calibration paths.

### Required evidence

The Executor must report the implementation revision or exact working-tree state, commands actually executed, observed results, tests added or changed, verification gaps, deviations, and blockers.

## Stop conditions

Stop and return to planning if implementation requires runtime application changes, calibration algorithm changes, real-THORAX data, production mutation, a new secret or permission, GHCR migration, broader file scope, changed runtime provenance, loss of rollback semantics, or a baseline mismatch.

The Executor must not reinterpret this task into a materially different objective.

## Side-effect authorization

This task does not authorize production workflow dispatch, production mutation, application deployment, external-system mutation, secret or Google Drive mutation, Docker runtime mutation, GHCR publication, real-THORAX downloads, commit, or push.

## Expected terminal outcome

**Review Required**

Expected implementation classification: `TRX_STAGE_B3_PROMOTION_ONLY_READY_FOR_REVIEW`.

Production remains untouched until a later separate release authorization.
