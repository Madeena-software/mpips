---
title: MPIPS production host launcher supervision and conversion readiness recovery
document_id: TASK-MPIPS-LAUNCHER-SUPERVISION-RECOVERY-001
version: 1.0
status: Validated/Published
language: en-US
last_updated: 2026-09-08
scope:
  - durable host launcher supervision and lifecycle management
  - production conversion-readiness contract and deployment verification gate
  - version pinning, permission boundary, and socket path alignment
  - prevention of false-healthy MPIPS API when launcher is absent
authority_note: This task authorizes only the bounded host-launcher supervision and conversion-readiness recovery implementation and associated regression coverage. It does not authorize production deployment, workflow execution, runtime mutation, calibration changes, external system mutation, or capture retry.
---

# Executable Task

## Task identity

**Task title:** MPIPS production host launcher supervision and conversion readiness recovery

**Task path:** `.agents/tasks/mpips-production-launcher-supervision-recovery.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Durable MPIPS host-launcher supervision and production conversion readiness recovery.

**Owner / designated planning authority:** Human operator / Planner-Reviewer incident response handoff.

## Delivery context

During incident MHCS capture `5054464a-9fb2-427b-88fa-a0680cc00186`, three conversion attempts to `POST /v1/radiographs/dicom` returned HTTP 500 with `CONVERSION_WORKER_FAILURE`, producing no DICOM study. Production diagnostics confirmed:
- MPIPS API was reachable and reported `/health` as HTTP 200;
- Production runtime was verified to be running commit `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a`;
- TRX calibration was present and valid;
- The host launcher runtime, launcher socket (`/var/www/mpips-runtime/launcher/launcher.sock`), and launcher service were absent/inactive;
- The conversion path at `f2bf7b9` requires the launcher socket to dispatch NPZ worker jobs;
- The absent socket raised `CONVERSION_WORKER_FAILURE` (HTTP 500), classified under primary root cause `MPIPS_LAUNCHER_RUNTIME_FAILURE`.

Investigation of `.github/workflows/deploy-internal-beta.yml` at `f2bf7b9` revealed the systemic lifecycle defect:
1. The deploy workflow started the versioned host launcher using an unsupervised `nohup` background Python process;
2. The workflow only checked that the socket appeared once during deployment;
3. It then deployed Compose and treated basic API health (`curl /health` returning 200) as sufficient for deployment success;
4. The launcher process later terminated or disappeared during ordinary runtime, while `mpips-api` continued reporting healthy;
5. Consequently, a mandatory conversion dependency was not durably supervised and was not represented in readiness/health checks, allowing a false-healthy API state.

This task governs the technical implementation to durably supervise the launcher, enforce version alignment and safe permissions, and couple conversion-readiness to actual launcher readiness.

## Baseline and task revision

**Implementation baseline:** `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a`

**Task revision:** resolved as the immutable Git publication revision before implementation handoff (`.agents/tasks/mpips-production-launcher-supervision-recovery.md` @ governing commit SHA).

## Objective

Deliver durable host launcher supervision and strict conversion readiness verification such that:
1. The production host launcher required for DICOM conversion is durably supervised and automatically restarted after unexpected termination;
2. The launcher is version-pinned to the exact deployed worker image revision and uses correct runtime permissions and socket paths;
3. `mpips-api` cannot be reported as conversion-ready if the launcher dependency is absent or unready;
4. Deploy workflows fail closed if the launcher fails supervision setup or readiness verification;
5. Regression tests verify supervision configuration, socket path agreement, image version pinning, conversion readiness gates, and prevention of unsupervised `nohup` lifecycles.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Incident MHCS capture `5054464a-9fb2-427b-88fa-a0680cc00186` diagnostic and root cause `MPIPS_LAUNCHER_RUNTIME_FAILURE`
- User task specification: URGENT MPIPS INCIDENT — TASK AUTHORING / PUBLICATION ONLY

### Requirement traceability

- Durable launcher supervision and automatic restart → User incident directive & lifecycle defect analysis
- Strict conversion-readiness invariant (`mpips-api` conversion-ready IFF launcher dependency ready) → User incident directive & lifecycle defect analysis
- Worker image version pinning and socket alignment → `docker-compose.prod.yml`, `.github/workflows/deploy-internal-beta.yml`, `docker/host-launcher/mpips-launcher.py`
- Preservation of container isolation (no Docker socket in `mpips-api`) → Architecture constraints in `.agents/context/project.md`
- Deployment fail-closed behavior with rollback on launcher failure → Deployment lifecycle invariants

## Scope

### In scope

- Host launcher supervision mechanism (e.g., robust systemd service/socket configuration or equivalent host supervision pattern compatible with self-hosted runner and deployment automation).
- Deployment workflow orchestration in `.github/workflows/deploy-internal-beta.yml` to replace unsupervised `nohup` execution with durable supervision, enforce launcher worker-image alignment to `$MPIPS_VERSION`, and handle safe clean transitions across redeployments.
- Conversion-readiness contract and verification gate: ensuring deployment readiness and/or API conversion readiness checks require active launcher readiness rather than generic `/health` only.
- Socket path, user/group IDs, and permissions configuration between host launcher supervisor, mounted runtime directory, and `mpips-api` container.
- Regression tests verifying:
  - Host launcher security and arguments validation (`tests/test_host_launcher.py`);
  - Supervision configuration and absence of unsupervised `nohup` launcher invocation in workflows;
  - Exact version-pinned worker image configuration;
  - Socket path and permission agreement across deployment config, compose, and API;
  - Conversion-readiness verification failing when launcher is absent and succeeding when launcher is ready;
  - Preservation of Docker socket isolation (mpips-api container never mounts Docker socket);
  - Existing API and DICOM conversion regression suites (`tests/api/test_api_surface.py`, `tests/api/test_dicom_authentication.py`, `tests/api/test_dicom_conversion.py`, `tests/test_production_dicom_e2e_diagnostic.py`).

### Out of scope

- Merging, pulling, or rebasing against `main` or newer branches.
- Modifying image-processing algorithms, FFC, CLAHE, or thresholding.
- Modifying TRX or BED orientation, crop/rotate logic, or calibration data/geometry.
- Modifying DICOM tags, encoding, or manifest schemas.
- Modifying MHCS code or external services.
- Executing production deployment or triggering GitHub Actions workflow runs.
- Mutating production host files, services, or runtime state.
- Consuming the remaining 2 attempts on incident capture `5054464a-9fb2-427b-88fa-a0680cc00186` (real capture retry is strictly out of scope).

### Preserved behavior

- Container isolation: `mpips-api` must NEVER mount `/var/run/docker.sock` or have direct Docker access.
- API authentication: Bearer API key verification via `MPIPS_API_KEY` remains intact.
- Worker isolation: Workers run via host launcher with `--read-only`, `--cap-drop=ALL`, `--network=none`, `--security-opt=no-new-privileges:true`, and per-job private workspaces.
- Calibration validation and layout verification remain required before deployment.
- Idempotency, concurrency controls, and upload limits in `mpips-api` remain unchanged.
- External API contracts and HTTP response codes for DICOM conversion remain backward compatible.

## Dependencies and assumptions

### Dependencies

- Exact production implementation baseline commit `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a`.
- Self-hosted GitHub Actions runner in production environment with systemd / host supervisor capabilities.
- Python 3.12, `uv`, Docker, Docker Compose, pytest, and existing repository tools.

### Approved assumptions

- The production environment has systemd available for supervising host services, or an equivalent host-level process manager.
- The host launcher must run as a managed service whose lifecycle extends beyond the GitHub Actions runner execution job.
- Re-deploying an updated version must atomically or sequentially update the launcher's worker image environment and restart the managed unit.

### Remaining approval requirements

- Executor implementation must be reviewed and accepted by Reviewer/Planner against this validated task.
- Production hotfix deployment workflow dispatch requires explicit Human Operator authorization.
- Synthetic/deidentified DICOM conversion verification must pass in production after deployment before capture retry can be considered.
- Capture retry for incident MHCS capture `5054464a-9fb2-427b-88fa-a0680cc00186` requires separate explicit post-recovery Planner and Human Operator authorization.

## Required capabilities

- Repository read/write on isolated hotfix branch.
- Shell and test execution (`pytest`, `uv`).
- Git for task publication and implementation commits.

## Execution constraints

- Do not grant `mpips-api` direct Docker access.
- Avoid unchecked hardcoding: do not blindly enable `docker/host-launcher/mpips-launcher.service` without ensuring that worker image tags (`mpips-npz-worker:$MPIPS_VERSION`), socket paths, and UID/GID permissions align with `deploy-internal-beta.yml` and `docker-compose.prod.yml`.
- The launcher must survive runner step completion and runner process termination.
- Supervision must include automatic restart policies for crashes or abnormal exits.
- Deployment readiness verification must assert that the launcher socket is alive and responding before declaring deployment success.
- If launcher setup or readiness fails, deployment must fail closed and trigger Compose rollback to the previous version without reporting MPIPS healthy.
- No secrets or PHI may be logged to stdout, journald, or GitHub Actions logs.

## Acceptance criteria

- [ ] Host launcher is managed by a durable supervisor (e.g. systemd service/socket) configured with automatic restart on abnormal exit.
- [ ] Deploy workflow no longer launches the worker launcher via unsupervised `nohup`.
- [ ] Deploy workflow configures/reloads the supervised launcher with the exact version-pinned worker image `mpips-npz-worker:$MPIPS_VERSION` matching the deployed `mpips-api` image.
- [ ] Socket path and file permissions (`MPIPS_LAUNCHER_SOCKET_PATH`, GID/UID) agree between supervisor, host filesystem, and `docker-compose.prod.yml`.
- [ ] A dedicated conversion-readiness check or deployment readiness check explicitly verifies launcher availability before deployment completion.
- [ ] False-healthy state is prevented: absence of the launcher socket causes conversion-readiness verification to fail.
- [ ] If launcher initialization or readiness fails during deployment, the deploy workflow fails closed and executes rollback.
- [ ] Regression tests cover:
  - [ ] Launcher configuration and supervisor definitions;
  - [ ] Prevention of unsupervised `nohup` in deploy workflows;
  - [ ] Socket path and version alignment;
  - [ ] Readiness verification failure on absent launcher;
  - [ ] Readiness verification success on active launcher;
  - [ ] Preservation of Docker isolation (no Docker socket in `mpips-api`);
  - [ ] Existing launcher and DICOM conversion test suites.
- [ ] No algorithm, orientation, calibration, or unrelated code changes are introduced.

## Verification requirements

### Required checks

- `uv run pytest tests/test_host_launcher.py -q`
- `uv run pytest tests/api/test_api_surface.py tests/api/test_dicom_authentication.py tests/api/test_dicom_conversion.py -q`
- `uv run pytest tests/test_production_dicom_e2e_diagnostic.py -q`
- New regression tests specifically covering launcher supervision, version alignment, and conversion-readiness gating.
- Static verification of workflow files and service definitions (`git diff --check`, syntax validation).
- Python compile check: `python -m compileall mpips/ docker/host-launcher/ tests/`

### Required evidence

The Executor must report:
- Implementation revision (commit SHA) and clean working-tree state;
- Exact command outputs for all executed test suites and linters;
- Tests added or modified;
- Verification that no Docker socket was exposed to `mpips-api`;
- Verification that `nohup` invocation was completely removed from the deployment lifecycle;
- Explicit confirmation that production runtime was not mutated and incident capture `5054464a-9fb2-427b-88fa-a0680cc00186` was not retried.

## Stop conditions

The Executor must stop implementation and return to planning if:
- Implementing supervision requires granting Docker socket access to `mpips-api`;
- Host environment assumptions (such as systemd availability or permissions on the runner) conflict with self-hosted runner constraints;
- Changes require altering the public DICOM API schemas or external MHCS contracts;
- Changes require altering calibration data, geometry, or image-processing algorithms;
- Any step requests live deployment, production command execution, or capture requeuing.

## Side-effect authorization

This task authorizes authoring and publication of this task contract, followed by implementation and test execution on the isolated branch. It does NOT authorize production deployment, workflow dispatch, production host mutation, or capture retry.

### Explicitly authorized side effects

- Publish this task file as its own Git commit on `hotfix/mpips-launcher-supervision-f2bf7b9`.
- Ordinary non-force push of the task commit to remote `origin` if available.
- Implementation and testing on the isolated branch once execution begins.

## Expected terminal outcome

**Review Required** (Upon completion of implementation and verification by Executor).
