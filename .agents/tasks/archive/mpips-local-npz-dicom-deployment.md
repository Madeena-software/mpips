---
name: mpips-local-npz-dicom-deployment
description: Make the active NPZ-to-DICOM API accept two 100 MiB NPZ files and prove the fixed-key service locally through the existing private Docker burn-in.
version: 1
---

# Task: Local 100 MiB-per-file NPZ-to-DICOM deployment

## Task identity

**Task title:** Local 100 MiB-per-file NPZ-to-DICOM deployment
**Task path:** .agents/tasks/mpips-local-npz-dicom-deployment.md
**Task contract state:** Validated/Published
**Delivery objective / Work Package / MVP:** Private local readiness of the active fixed-key NPZ-to-DICOM API before any production-release work.
**Owner / designated planning authority:** Repository user direction on 2026-08-10: each radiograph and gain NPZ may be up to 100 MiB; local delivery precedes production.

## Delivery context

The active POST /v1/radiographs/dicom route takes a radiograph NPZ, a gain NPZ, and a manifest. Current per-file and aggregate limits contradict the approved 100 MiB-per-file decision, and the deployment workflow's focused-test environment omits the already-declared imager extra required by the DICOM test module. Correct those bounded readiness defects and prove the complete current API path only in a private local Docker deployment.

## Baseline and task revision

**Implementation baseline:** 491dd34721d2322e289574731795ab5f388f2fd3

**Task revision:** Resolved by this task's publication record:
.agents/tasks/mpips-local-npz-dicom-deployment.md @ <publication commit>.

The Executor must resolve the publication commit before beginning work and must not use a later task revision without Planner/Reviewer review.

## Objective

Make the active API and its local deployment configuration support one radiograph NPZ of up to 100 MiB and one gain NPZ of up to 100 MiB in the same request, then demonstrate a successful synthetic NPZ-to-DICOM conversion on a loopback-only local Compose stack.

## Authoritative inputs

### Governing authority

- User direction in this conversation: local NPZ-to-DICOM delivery before production, with a 100 MiB limit for each NPZ file.
- .agents/AGENTS.md and .agents/software-workflow.md.
- .agents/context/project.md, which defines the active DICOM-only API surface and loopback-only deployment boundary.
- Historical API contract in .agents/tasks/archive/mpips-simple-key-cicd-internal-beta-v1.md: fixed X-MPIPS-API-Key, internal-beta idempotency namespace, no public ingress, and no Redis host port.

### Requirement traceability

- NPZ-DICOM-L1 — Each radiograph and gain NPZ is individually limited to 100 MiB → user direction, 2026-08-10.
- NPZ-DICOM-L2 — A request may carry both maximum-size NPZ files and one maximum-size manifest without an aggregate/body-limit rejection → NPZ-DICOM-L1 and the route's three-part request contract.
- NPZ-DICOM-L3 — The local active API completes a fixed-key synthetic NPZ-to-DICOM conversion while remaining loopback-only and keeping Redis private → repository context and historical fixed-key task.
- NPZ-DICOM-L4 — The deployment workflow's declared focused-test environment can collect the DICOM conversion suite → observed review evidence and the existing imager optional dependency.

## Scope

### In scope

- Update active upload-limit defaults and production validation in mpips/api/application.py and mpips/api/routes/v1/dicom.py.
- Set the gain limit to 100 MiB and set aggregate/body limits that allow two 100 MiB NPZ files plus one manifest with multipart headroom.
- Update matching values in docker-compose.local.yml, docker-compose.prod.yml, and .env.production.example.
- Add focused tests before implementation changes for the coherent limit envelope and for production configuration rejecting an insufficient aggregate or body limit.
- Make .github/workflows/deploy-internal-beta.yml install the existing imager extra along with its present focused-test extras; do not add a new dependency or modify the lock file.
- Build task-owned local API and worker images, prepare only synthetic local fixtures, run scripts/local_dicom_burn_in.py, and verify the existing loopback-only Compose stack.
- Update .agents/context/project.md only with actual current-HEAD local evidence if the burn-in completes.

### Out of scope

- Any production deployment, workflow dispatch, GitHub push, SSH, or remote host access.
- Changes to the fixed API key, public route surface, converter bytes, DICOM semantics, calibration algorithms, or trusted-NPZ policy.
- Changing worker CPU, memory, concurrency, TIFF-size, or timeout limits.
- New packages, lock-file updates, retry mechanisms, public ingress, Nginx, or Redis port publication.

### Preserved behavior

- GET /health remains unauthenticated; the DICOM route keeps the fixed X-MPIPS-API-Key contract and internal-beta idempotency namespace.
- mpips/engine/imager_pipeline/tiff_json_to_dcm.py remains byte-identical with SHA-256 a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0.
- The local API binds only to the configured loopback port; Redis has no published port, and the worker remains isolated and network-disabled.
- The aggregate upload limit still rejects requests larger than its approved envelope; this task does not make uploads unbounded.

## Dependencies and assumptions

### Dependencies

- Docker and Docker Compose are available locally; the selected local port is unused.
- The existing local host-launcher and synthetic burn-in script remain usable against the baseline or are corrected only when a reproducible scoped fault requires it.
- The existing imager optional extra remains locked and includes the dependencies required by tests/api/test_dicom_conversion.py.

### Approved assumptions

- 100 MiB means 104857600 bytes for each NPZ file.
- The 1 MiB manifest allowance remains unchanged. The aggregate file-content limit is therefore 210763776 bytes (201 MiB), and the HTTP request-body limit is 211812352 bytes (202 MiB) to retain 1 MiB multipart headroom.
- The task-local burn-in's small synthetic fixtures are sufficient to verify the conversion path; limit behavior is verified by focused configuration tests rather than generating 200 MiB of fixture data.

### Remaining approval requirements

- Production deployment, workflow dispatch, push, release, external-service access, and production secrets require separate explicit authorization after local review and acceptance.
- A production capacity or resource-limit change beyond the values specified here requires Planner/Reviewer review.

## Required capabilities

- Repository read and write.
- Shell and local test execution.
- Docker and Docker Compose.
- Codebase Memory MCP for implementation impact discovery.

## Execution constraints

- Follow test-driven development: add the focused failing tests, observe the expected failure, then make the smallest configuration/code changes needed for them to pass.
- Reuse the existing imager extra in the workflow; do not create, install, or lock a new dependency.
- Production startup validation must reject configurations where the aggregate limit is less than manifest + radiograph + gain, or where the body limit is less than aggregate + 1 MiB headroom.
- Use a task-created temporary virtual environment for dependency sync; do not modify a pre-existing user .venv. Remove only task-created temporary environments and Docker resources during cleanup.
- Run Compose only with generated local values and synthetic fixtures. Never read, print, copy, or commit production secrets or patient data.
- Do not use git add -A, reset, clean, rebase, amend, push, dispatch a workflow, or commit implementation changes under this task.

## Acceptance criteria

- [ ] _get_upload_limits() defaults and production configuration yield 104857600 bytes for both radiograph and gain, 210763776 bytes aggregate, and a 211812352 byte request-body limit.
- [ ] Production startup validation rejects an aggregate limit below the sum of maximum manifest, radiograph, and gain limits, and rejects a body limit below the aggregate limit plus 1 MiB headroom.
- [ ] The focused DICOM conversion test module collects and runs in a fresh environment provisioned by the same extras declared in the workflow.
- [ ] docker compose -f docker-compose.local.yml config renders the approved limits, API loopback-only port binding, and no Redis host port.
- [ ] The task-owned local stack returns 200 from /health; missing and wrong API keys return 401; the existing synthetic burn-in returns a validated DICOM response and leaves no task-created worker workspace.
- [ ] The converter hash is unchanged, the local stack is removed, final Git status identifies only task-owned changes, and no public or production mutation occurs.

## Verification requirements

### Required checks

- Run the new focused limit/configuration tests first and confirm they fail against the baseline for the intended reason; rerun them after the minimal change.
- In a task-created environment provisioned with --extra service --extra dev --extra npz-worker --extra imager, run:

  pytest tests/api/test_api_surface.py tests/api/test_dicom_authentication.py \
    tests/api/test_dicom_conversion.py tests/test_host_launcher.py -v
- Render both Compose files using non-secret placeholder environment values.
- Verify the converter SHA-256 before and after local execution.
- Build task-owned local images; run scripts/local_dicom_burn_in.py prepare and run against the selected loopback URL; inspect container port mappings, Redis port exposure, worker isolation, and cleanup.

### Required evidence

The Executor must report the exact working-tree revision/state, tests added, observed red/green test results, rendered limit values, local URL, image tags, port/Redis inspection output, burn-in result, converter hashes, cleanup result, and all unrun checks or residual risks. Local results must not be represented as CI or production evidence.

## Stop conditions

- The initial Git tree is dirty, the selected local port is in use, Docker is unavailable, or a non-task local resource would need alteration.
- The required dependency extras cannot be provisioned without a lock-file or dependency change.
- The local stack exposes a non-loopback API port, publishes Redis, lacks the worker isolation boundary, fails a valid conversion, or changes the protected converter hash.
- A solution requires an upload limit, body limit, resource limit, or scope beyond the exact values stated in this task.
- A production, remote, secret, patient-data, push, workflow-dispatch, or commit action becomes necessary.

## Side-effect authorization

### Explicitly authorized side effects

- Modify only the in-scope repository files and tests.
- Create and remove task-owned temporary virtual environments, synthetic fixtures, local images, containers, networks, volumes, and workspaces.
- Pull public package/container artifacts required by the existing lock file and Dockerfiles, without changing dependency declarations or lock files.
- Build and run the local loopback-only Compose stack.

Git commits for implementation, pushes, workflow dispatches, production deployment, and all production/external mutations remain unauthorized.

## Expected terminal outcome

**Review Required.** The Executor returns a reviewable task-owned working-tree state and observed local verification evidence. A Planner/Reviewer must decide whether it is acceptable and request separate commit authorization before A9 can establish a new immutable baseline. Production planning remains a separate release-gated task after local acceptance.

## Execution evidence

The Executor must preserve the governing task path and publication revision, the implementation baseline, the exact implementation state, all observed verification evidence, and any remediation or stop result for Reviewer use.
