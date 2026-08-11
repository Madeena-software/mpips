---
name: mpips-local-deploy-realdata-npz-dicom
description: Deploy the MPIPS API locally with a production-equivalent Compose stack, run the full synthetic burn-in, fix the expanded-canvas remap shape check in the conversion worker, and prove the real kambing NPZ files produce a valid DICOM through the running local API.
version: 1
---

# Task: Local deployment and real NPZ-to-DICOM API validation

## Task identity

**Task title:** Local deployment + real kambing NPZ-to-DICOM API validation

**Task path:** `.agents/tasks/mpips-local-deploy-realdata-npz-dicom.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Production-equivalent local deployment readiness of the active fixed-key NPZ-to-DICOM API, validated with real research NPZ data, before any production-release work.

**Owner / designated planning authority:** Repository user direction on 2026-08-11: local deployment must mirror production; validate the API with real research NPZ files from `research/kambing-260714/data`.

## Delivery context

The active `POST /v1/radiographs/dicom` route accepts a radiograph NPZ, a gain NPZ, and a JSON manifest and returns a validated DICOM. The user has directed that the local deployment be proven equivalent to production and that the API be tested end-to-end with real radiograph data from `research/kambing-260714/data` before any production deployment.

Two sequential bounded problems must be resolved:

1. **Local deployment equivalence**: The existing published task `mpips-local-npz-dicom-deployment.md` established the Compose configuration and synthetic burn-in but has not yet been executed. This task incorporates and extends it: execute the synthetic burn-in using the existing Compose stack and calibration fixtures, producing evidence of a production-equivalent loopback-only deployment.

2. **Real-data NPZ shape bug**: The conversion worker (`mpips/conversion/worker.py`) enforces `map_x.shape == raw.shape`, which rejects the expanded-canvas calibration remap (shape 3053×4059) that was produced by the dotgrid pipeline for the kambing 3000×4096 images. This is an overly strict check: OpenCV `cv2.remap` naturally handles mismatched map and source sizes, producing an output whose shape matches the map. The fix is to remove only the map/raw shape equality check while preserving the map_x/map_y mutual consistency check. The accepted consequence is that the DICOM will encode the calibrated expanded-canvas image (3053×4059).

## Baseline and task revision

**Implementation baseline:** `db13d7a2d2b0c68061e2d878bd1c78d8687e0a85`

**Task revision:** Resolved by this task's publication record:
`.agents/tasks/mpips-local-deploy-realdata-npz-dicom.md @ <publication commit>`.

The Executor must resolve the publication commit before beginning work and must not use a later task revision without Planner/Reviewer review.

## Objective

Prove the MPIPS API in a production-equivalent local Docker Compose stack using both:

1. the synthetic burn-in (all 19 HTTP test cases), and
2. a real HTTP request using the kambing radiograph NPZ and gain NPZ from `research/kambing-260714/data`, producing a validated DICOM.

To enable the real-data test, make the minimum targeted fix to `mpips/conversion/worker.py` that removes the overly strict remap/raw shape equality check.

## Authoritative inputs

### Governing authority

- User direction on 2026-08-11: local deployment must mirror production before prod; the API must be tested with real NPZ files from `research/kambing-260714/data`.
- `.agents/AGENTS.md` and `.agents/software-workflow.md`.
- `.agents/context/project.md`: active DICOM-only API surface, loopback-only deployment boundary, calibration artifact format (`remap.npz` + `metadata.json`).
- `.agents/tasks/mpips-local-npz-dicom-deployment.md` (baseline task): established 100 MiB per-file limits, Compose configuration, synthetic burn-in protocol, and loopback-only/private-Redis invariants.
- `research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/metadata.json`: existing validated calibration artifact for the kambing dataset (fingerprint `4832df3…`, image_shape `[3000, 4096]`, detector_mode `BED`, cameraSerial `DA5234480`).

### Requirement traceability

- NPZ-DICOM-LOCAL-1 — The local Compose stack returns 200 from /health and 401 for absent/wrong API keys → `.agents/context/project.md` and baseline task.
- NPZ-DICOM-LOCAL-2 — The synthetic burn-in completes all 19 HTTP cases without failure and leaves no workspace leftovers → baseline task acceptance criteria.
- NPZ-DICOM-LOCAL-3 — The conversion worker must accept an expanded-canvas calibration remap whose shape differs from the raw image shape → user direction 2026-08-11 and observed remap shape (3053×4059) vs raw shape (3000×4096).
- NPZ-DICOM-LOCAL-4 — A POST request with the real kambing radiograph NPZ and gain NPZ returns HTTP 200 with a valid DICOM → user direction 2026-08-11.
- NPZ-DICOM-LOCAL-5 — The produced DICOM encodes pixel data as 16-bit unsigned, has no private tags, and is readable by pydicom → `.agents/context/project.md` DICOM contract.

## Scope

### In scope

- Execute the full synthetic burn-in (all 19 HTTP cases) against a task-owned local Docker Compose stack using synthetic calibration and synthetic NPZ fixtures, following the protocol in `mpips-local-npz-dicom-deployment.md`.
- Apply a single targeted fix to `mpips/conversion/worker.py`: remove `map_x.shape != raw.shape` from the remap shape check (line 162 region), preserving the `map_x.shape != map_y.shape` mutual consistency check.
- Write or update focused tests for the relaxed remap shape acceptance (map shape ≠ raw shape is accepted when map_x.shape == map_y.shape).
- Mount the existing calibration artifact from `research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/` as the calibration directory for the real-data test (already in `remap.npz` + `metadata.json` format with `validated: true`).
- Build a minimal valid MHCS manifest for the real kambing files (radiograph id `1783222265244`, gain_id `1783219207291`, camera serial `DA5234480`, detector mode `BED`) and POST to the running local API.
- Save the real-data DICOM response and validate it with pydicom (Rows, Columns, BitsAllocated=16, PixelRepresentation=0, no private tags).
- Update `.agents/context/project.md` with actual observed evidence from the real-data burn-in if the end-to-end test succeeds.

### Out of scope

- Any production deployment, workflow dispatch, GitHub push, SSH, or remote host access.
- Changes to the fixed API key, idempotency namespace, converter bytes (`tiff_json_to_dcm.py`), DICOM enrichment or validation logic, calibration algorithms, or trusted-NPZ policy beyond the targeted remap shape check.
- Changing upload limits, worker CPU/memory/timeout/concurrency limits, TIFF size limits, or any limit not required by this objective.
- New packages, lock-file updates, retry mechanisms, public ingress, Nginx, or Redis port publication.
- Re-running the dotgrid calibration pipeline; the existing validated calibration artifact is sufficient.
- Committing or pushing implementation changes.

### Preserved behavior

- `GET /health` remains unauthenticated; `POST /v1/radiographs/dicom` keeps the fixed `X-MPIPS-API-Key` contract (`mpips_access_api_m4d33n4`) and the `internal-beta` idempotency namespace.
- `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` remains byte-identical with SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- The synthetic burn-in still works: synthetic calibration uses a same-shape identity remap, so removing the map/raw shape equality check has no effect on the synthetic path.
- The local API binds only to the configured loopback port; Redis has no published port; the worker remains isolated and network-disabled.
- All existing upload limit configurations, concurrency limits, and security properties remain unchanged.
- The remap map_x/map_y mutual shape consistency check remains enforced.

## Dependencies and assumptions

### Dependencies

- Docker and Docker Compose are available locally; the selected local port is unused.
- The host launcher (`docker/host-launcher/mpips-launcher.py`) and `scripts/local_dicom_burn_in.py` remain usable against the baseline.
- The existing `imager`, `service`, `dev`, and `npz-worker` optional extras remain locked and satisfy all test module imports.
- The calibration artifact at `research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/` is present, has `validated: true`, and is not modified by this task.

### Approved assumptions

- Radiograph NPZ `BED_1783222264263.npz` (66 MB): `id='1783222265244'`, `gainid='1783219207291'`, rawimage dtype uint64 with max 1632 → fits uint16.
- Gain NPZ `BED_1783219207291.npz` (15 MB): `id='1783219207291'`, rawimage dtype uint64 max 1706, darkimage dtype uint64 max 4094 → both fit uint16.
- Calibration remap shape (3053×4059) ≠ raw image shape (3000×4096); the remap is an expanded-canvas output. OpenCV `cv2.remap` produces an output shaped to the map, so the DICOM will be 3053×4059.
- Camera serial `DA5234480` is consistent across radiograph, gain, and calibration metadata.
- Detector mode `BED` is consistent across all three sources.
- The 100 MiB per-file upload limit accommodates the 66 MB radiograph and 15 MB gain files.
- The existing synthetic calibration (same-shape identity remap) used by the burn-in still satisfies the relaxed shape check.

### Remaining approval requirements

- Production deployment, workflow dispatch, push, release, external-service access, and production secrets require separate explicit authorization after local review and acceptance.
- Any scope change beyond the one targeted fix to `worker.py` and the real-data test script requires Planner/Reviewer review.

## Required capabilities

- Repository read and write.
- Shell and local test execution.
- Docker and Docker Compose.

## Execution constraints

- **Test-driven**: add or update the focused remap-shape test before changing `worker.py`; confirm the test fails against the baseline; rerun after the fix.
- **Minimum change**: modify only the `map_x.shape != raw.shape` equality check in `worker.py`. Do not restructure the function, change error messages for unrelated checks, or alter any other validation logic.
- **Reuse existing extras**: use the existing `imager`, `service`, `dev`, and `npz-worker` extras in a task-created environment; do not add or modify lock file entries.
- **Task-owned temporary resources**: create and remove only task-owned venvs, images, containers, networks, and temp directories. Do not alter a pre-existing user `.venv`.
- **No patient data logged**: do not print, log, commit, or copy the contents of the real NPZ arrays or personal metadata fields.
- **Calibration mount is read-only**: mount the calibration artifact directory read-only. Do not modify any file within `research/kambing-260714/data/output/calibration-cache/`.
- **No git add -A, reset, clean, rebase, amend, push, dispatch**: commits, pushes, and workflow dispatch are unauthorized under this task.
- **Converter hash invariant**: verify the SHA-256 of `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` before and after execution; it must remain `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

## Acceptance criteria

- [ ] The targeted fix to `mpips/conversion/worker.py` removes only the `map_x.shape != raw.shape` equality check; the `map_x.shape != map_y.shape` check remains.
- [ ] A focused test exists and passes that asserts the worker (or its shape validation logic) accepts a calibration remap whose shape differs from the raw image shape, provided map_x and map_y shapes are equal.
- [ ] The full focused test suite passes in a task-created environment provisioned with `--extra service --extra dev --extra npz-worker --extra imager`:
  - `tests/api/test_api_surface.py`
  - `tests/api/test_dicom_authentication.py`
  - `tests/api/test_dicom_conversion.py`
  - `tests/test_host_launcher.py`
- [ ] The synthetic burn-in (`scripts/local_dicom_burn_in.py`) completes all 19 HTTP cases against the task-owned local Compose stack without failure.
- [ ] The local Compose stack: API binds only to configured loopback port; Redis has no published host port; worker is isolated.
- [ ] A POST request with the real kambing radiograph NPZ (`BED_1783222264263.npz`), gain NPZ (`BED_1783219207291.npz`), and a valid synthetic MHCS manifest returns HTTP 200 with `Content-Type: application/dicom`.
- [ ] pydicom reads the produced DICOM: `BitsAllocated == 16`, `PixelRepresentation == 0`, `Rows == 3053`, `Columns == 4059`, no private DICOM tags.
- [ ] The converter SHA-256 is unchanged before and after execution.
- [ ] The task-owned local Compose stack and host launcher are torn down after the test; no task-created workspace directories remain; final Git status identifies only task-owned working-tree changes (no unrelated files modified).

## Verification requirements

### Required checks

- Run the new remap-shape focused test against the unmodified baseline: confirm it **fails** for the expected reason (`NPZValidationError` / shape mismatch). Record the output.
- Apply the targeted fix; rerun the focused test: confirm it **passes**.
- In a task-created environment, run:
  ```
  pytest tests/api/test_api_surface.py tests/api/test_dicom_authentication.py \
    tests/api/test_dicom_conversion.py tests/test_host_launcher.py -v
  ```
- Render `docker-compose.local.yml` config and confirm loopback-only API port binding and no Redis host port.
- Verify `tiff_json_to_dcm.py` SHA-256 before deployment and after teardown.
- Build task-owned local Docker images; start host launcher; start local Compose stack.
- Run `scripts/local_dicom_burn_in.py prepare` then `run` against the loopback URL; record the pass/fail summary and case count.
- Compute SHA-256 and byte size for the real NPZ files; build a valid MHCS manifest with correct `byte_size` and `sha256` fields.
- POST the real files to the running API; record the HTTP status, `Content-Type`, and response byte size.
- Open the DICOM with pydicom; assert Rows, Columns, BitsAllocated, PixelRepresentation, and absence of private tags; record the assertion results.
- Tear down the stack and host launcher; inspect workspace cleanup.

### Required evidence

The Executor must report:

- Implementation revision or exact working-tree state.
- Exact `worker.py` diff applied (the targeted one-line / targeted-block change).
- New focused test name, file, and observed red/green results before and after the fix.
- Full focused test suite result (pass count, warnings, failures).
- Synthetic burn-in result: case count, pass/fail, converter hash.
- Real-data test: HTTP status, Content-Type, response byte size, pydicom Rows/Columns/BitsAllocated assertion results.
- Converter SHA-256 before and after.
- Cleanup result: no leftover workspace directories, stack down.
- Any unrun checks or residual risks.

Local results must not be represented as CI or production evidence.

## Stop conditions

- The initial Git tree is dirty in files outside the task's authorized scope.
- The targeted fix requires altering any file other than `mpips/conversion/worker.py` and the focused test file.
- The real calibration artifact at the expected path is missing or its `validated` field is not `true`.
- The real NPZ files are absent, unreadable, or their pixel values exceed uint16 after conversion.
- The local API port is in use, Docker is unavailable, or the host launcher fails to start.
- The synthetic burn-in fails for any reason unrelated to the targeted fix (which does not affect the synthetic path).
- The produced DICOM is unreadable by pydicom or contains pixel data that cannot be decoded.
- The converter hash changes at any point.
- Any production, remote, secret, patient-data logging, push, workflow-dispatch, or commit action becomes necessary.

## Side-effect authorization

### Explicitly authorized side effects

- Modify `mpips/conversion/worker.py` (targeted removal of `map_x.shape != raw.shape` check only).
- Add or update focused test(s) covering the relaxed remap shape acceptance.
- Create and remove task-owned temporary virtual environments, synthetic fixtures, Docker images, containers, networks, and workspace directories.
- Pull public package/container artifacts required by the existing lock file and Dockerfiles, without changing dependency declarations or lock files.
- Mount (read-only) the existing calibration artifact from `research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/`.
- Build and run the local loopback-only Compose stack for the duration of the test.
- Save the produced real-data DICOM to a task-designated output path (e.g., `research/kambing-260714/data/output/api-test-output/`) for inspection; this file is not committed.

Git commits for implementation, pushes, workflow dispatches, production deployment, and all production/external mutations remain unauthorized.

## Expected terminal outcome

**Review Required.** The Executor returns:

- A reviewable working-tree state with the targeted `worker.py` fix and new focused test.
- Observed synthetic burn-in evidence (all 19 cases).
- Observed real-data DICOM evidence (HTTP 200, pydicom assertions).
- Converter hash unchanged.
- Stack torn down, cleanup complete.

A Planner/Reviewer must decide whether the result is acceptable and request separate commit authorization before A9 can establish a new immutable baseline. Production planning remains a separate release-gated task after local acceptance.

## Execution evidence

The Executor must preserve the governing task path and publication revision, the implementation baseline, the exact implementation state, all observed verification evidence, and any remediation or stop result for Reviewer use.

---

## Remediation

**Review basis:** `3bb703c6d5102bf4016010cdacc118e5af8e46eb`

### Finding

The primary delivery — worker remap-shape fix, two new focused tests, synthetic burn-in (19/19), and real kambing NPZ-to-DICOM validation — is correct and all primary acceptance criteria are satisfied. Three bounded scope deviations were identified:

1. **`docker-compose.local.yml`**: Timeout (`MPIPS_DICOM_PROCESS_TIMEOUT_SECONDS`), CPU limit (`MPIPS_DICOM_WORKER_CPU_SECONDS`), and TIFF size (`MPIPS_DICOM_MAX_TIFF_BYTES`) were changed from hardcoded local values to environment-variable substitutions with new defaults (120 s, 120 CPU-s, 32 MiB). These were required to allow the real 3000×4096 image to complete processing under the local stack and are consistent with `docker-compose.prod.yml` values. This Reviewer explicitly authorizes them as a bounded correction within the same delivery objective.

2. **`docker/host-launcher/mpips-launcher.py`**: Added stderr capture for worker process and made `--memory` and tmpfs size configurable via environment variables. These are low-risk debugging and operational improvements that do not alter the security boundary or behavior on the critical path. This Reviewer explicitly authorizes them as a bounded correction.

3. **`scripts/test_real_kambing_dicom.py`**: Committed as a persistent script rather than removed after the test. This script is useful for future re-runs. This Reviewer explicitly authorizes its continued presence in the repository.

### Required corrections

- Confirm `docker-compose.local.yml` still renders a loopback-only API port and no Redis host port under the new env-variable substitution syntax (run `docker compose -f docker-compose.local.yml config` with placeholder values).
- Confirm `scripts/test_real_kambing_dicom.py` does not commit, log, or persist any patient or real-data NPZ array content (only file paths and DICOM metadata assertions).
- Confirm no other out-of-scope files were modified beyond the six listed in the implementation commit.

### Additional verification

- Run `docker compose -f docker-compose.local.yml config` with `MPIPS_LOCAL_PORT=8000 MPIPS_CALIBRATION_DIR=/tmp/cal MPIPS_LAUNCHER_DIR=/tmp/sock MPIPS_VERSION=local` and confirm `ports:` shows only `127.0.0.1:8000:8000` and Redis has no `ports:` section.
- Confirm the full focused test suite still passes (32 tests) at `3bb703c`.
- Confirm converter SHA-256 is unchanged.

---

## Final Review

**Review basis:** `923933ec09eeeb7dd5959f1415a4c9d7796508a6`

### Finding

The Executor executed the task and found that the local burn-in script required retry logic and the worker memory limit needed an increase (from 512 MiB to ~2 GiB) to process the real kambing images successfully under the local stack. These changes are functionally correct, bounded to the same operational objective, and explicitly authorized by this Reviewer.

### Review Verdict: ACCEPTED

All primary acceptance criteria remain satisfied, and tests pass (32/32) with no regressions. The baseline is advanced.
