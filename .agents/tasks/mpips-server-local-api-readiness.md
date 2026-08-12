---
title: MPIPS server-local API readiness on shared Madeena network
document_id: TASK-MPIPS-SERVER-LOCAL-API-001
version: 1.0
status: Validated/Published
language: en-US
last_updated: 2026-08-12
---

# Task: Establish MPIPS as a persistent server-local API on `madeena-software-network`

## Task identity

**Task path:**  
`.agents/tasks/mpips-server-local-api-readiness.md`

**Implementation baseline:**  
`eb445a40e66fc383ec5d29d18f4180345a0b1d2f`

**Delivery objective:**  
Make MPIPS run persistently on the production server, reachable from the server host through `127.0.0.1:8014` and from future Madeena containers such as MHCS through the shared private Docker network `madeena-software-network`.

**Owner / planning authority:**  
User directive.

## Bootstrap requirement

This file is supplied externally to Antigravity. Before implementation:

1. Read `.agents/AGENTS.md`, `.agents/software-workflow.md`, `.agents/context/project.md`, and `.agents/tasks/_template.md`.
2. Materialize this task at `.agents/tasks/mpips-server-local-api-readiness.md`.
3. Reconcile it with current repository authority and implementation evidence.
4. Publish it according to the repository task protocol so its exact immutable governing revision is resolvable.
5. Execute only the published revision.

Do not begin implementation from an unpublished task revision.

## Objective

Deliver a stable MPIPS runtime with this final connectivity model:

```text
Production server host
    |
    +-- http://127.0.0.1:8014
    |
    +-- Docker network: madeena-software-network
            |
            +-- mpips-api:8000
            |
            +-- future MHCS image-worker
```

MPIPS must remain private. No public MPIPS ingress is permitted.

## Required final network contract

The canonical shared Docker network name is:

```text
madeena-software-network
```

This network is intended to be reusable by Madeena services deployed on the same server.

It MUST NOT be lifecycle-owned by a single application Compose stack.

Preferred implementation:

```yaml
networks:
  madeena-software-network:
    external: true
    name: madeena-software-network
```

Provision the network idempotently through the approved GitHub Actions/self-hosted-runner path:

```bash
docker network inspect madeena-software-network >/dev/null 2>&1 || \
  docker network create madeena-software-network
```

Do not use SSH.

Do not rename it back to `mpips-internal-beta-v1`.

Do not create an additional MPIPS-only production network unless technically necessary and explicitly justified.

## Preserved API contract

Preserve the active MPIPS production surface:

```text
GET  /health
POST /v1/radiographs/dicom
```

Preserve:

- `POST /v1/radiographs/dicom` multipart fields:
  - `radiograph_npz`
  - `gain_npz`
  - `manifest`
- existing `X-MPIPS-API-Key` authentication contract;
- existing idempotency behavior;
- existing worker isolation and resource limits;
- Redis with no published host port;
- calibration artifacts mounted read-only;
- production documentation routes disabled;
- protected TIFF-to-DICOM converter bytes and SHA-256 invariant.

Do not modify `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` unless direct evidence proves it is defective and the user separately approves changing the protected converter.

## Scope

### In scope

1. Replace the production Docker network name with `madeena-software-network`.
2. Make the shared network external and lifecycle-independent from MPIPS Compose.
3. Provision the shared network idempotently through the existing GitHub Actions/self-hosted-runner operational path.
4. Keep host-side API access at:
   `http://127.0.0.1:8014`.
5. Prove container-side access on the shared network using a stable service address, expected to be:
   `http://mpips-api:8000`.
6. Separate deployment from full functional verification:
   - `.github/workflows/deploy-internal-beta.yml`
   - `.github/workflows/verify-internal-beta.yml`
7. Make deployment success mean that MPIPS is started, healthy, correctly networked, and ready to receive requests.
8. Move full DICOM burn-in/acceptance testing to the verification workflow.
9. Fix the currently known burn-in DICOM shape expectation only after reproducing and proving the authoritative output-shape semantics.
10. Leave MPIPS running when the task succeeds.
11. Update `.agents/context/project.md` only with observed final runtime evidence.

### Out of scope

- modifying `mhcs-core`;
- public MPIPS ingress;
- binding MPIPS to `0.0.0.0`;
- Nginx or public reverse proxy;
- public DNS or TLS;
- publishing Redis;
- redesigning authentication;
- changing calibration algorithms;
- unrelated image-processing refactors;
- host sysctl changes;
- Redis `vm.overcommit_memory` remediation;
- unrelated pydicom warning cleanup.

## Execution phases

### Phase 1 — Baseline and repository inspection

Run:

```bash
git rev-parse HEAD
git status --short
```

Expected baseline:

```text
eb445a40e66fc383ec5d29d18f4180345a0b1d2f
```

If HEAD differs, do not reset, rebase, clean, or discard changes. Report the actual state and return to planning/approval.

Inspect at minimum:

```text
.agents/AGENTS.md
.agents/software-workflow.md
.agents/context/project.md
.github/workflows/ci.yml
.github/workflows/setup-runtime-dirs.yml
.github/workflows/deploy-internal-beta.yml
docker-compose.prod.yml
docker-compose.local.yml
Dockerfile
docker/entrypoint.sh
docker/host-launcher/mpips-launcher.py
scripts/local_dicom_burn_in.py
mpips/api/application.py
mpips/api/routes/v1/dicom.py
mpips/conversion/service.py
mpips/conversion/worker.py
mpips/conversion/validation.py
mpips/workflows/imager_pipeline/pipeline.py
```

Before editing, report:

```text
current host binding
current production network
current deployment checks
current functional verification checks
current rollback behavior
current version-marker behavior
current known DICOM burn-in failure
```

### Phase 2 — Establish `madeena-software-network`

Change production networking so MPIPS joins the externally managed network:

```text
madeena-software-network
```

Update the runtime setup path to ensure the network exists before deployment.

The network creation must be idempotent.

After provisioning, verify:

```bash
docker network inspect madeena-software-network
```

Do not remove this network during normal MPIPS deployment teardown.

The network must be safe for future MHCS attachment.

### Phase 3 — Refactor deployment workflow

Refactor `.github/workflows/deploy-internal-beta.yml`.

Deployment responsibilities:

- checkout;
- dependency/bootstrap steps required by the current workflow;
- focused pre-deploy checks;
- protected converter SHA check;
- build versioned API and worker images;
- verify calibration artifacts exist;
- ensure `madeena-software-network` exists;
- prepare runtime directories;
- start the host launcher;
- wait for launcher socket;
- deploy Compose services;
- wait for Redis health;
- wait for MPIPS API health;
- verify host port is exactly `127.0.0.1:8014`;
- verify Redis has no published port;
- verify `mpips-api` is attached to `madeena-software-network`;
- verify private Docker DNS connectivity;
- persist the deployed version marker.

The deployment workflow MUST NOT run the full:

```text
scripts/local_dicom_burn_in.py ... run
```

The deployment workflow MUST NOT use the full `/v1/radiographs/dicom` acceptance suite as a deployment-success condition.

A functional test-harness failure must not tear down an otherwise healthy deployment.

### Phase 4 — Private Docker-network readiness probe

Prove a container attached to:

```text
madeena-software-network
```

can reach MPIPS through a deterministic private service address.

Expected address:

```text
http://mpips-api:8000/health
```

Prefer an existing MPIPS image/tool for the probe instead of adding an unrelated diagnostic image.

Observed success must include HTTP 200.

If `mpips-api` does not resolve as the stable alias, inspect the actual Docker network aliases and make the smallest deterministic networking correction.

Do not expose another host port to solve container-to-container networking.

### Phase 5 — Correct deployment version semantics

After deployment readiness succeeds, persist:

```text
/var/www/mpips-runtime/.mpips-version
/var/www/mpips-runtime/.mpips-worker-image
```

These markers mean:

```text
successfully deployed and ready
```

They do not mean:

```text
all post-deployment acceptance tests passed
```

Do not overload one marker with both deployment and acceptance semantics.

### Phase 6 — Create separate verification workflow

Create:

```text
.github/workflows/verify-internal-beta.yml
```

Required trigger:

```text
workflow_dispatch
```

Also configure safe automatic execution after a successful `Deploy MPIPS Internal Beta` run if repository policy and GitHub Actions semantics allow it without ambiguity.

For automatic verification, use the deployed workflow run's exact commit SHA rather than silently checking an unrelated newer `main`.

Run verification on the production self-hosted runner.

Verification owns the existing functional checks, including where applicable:

```text
GET /health
missing API key
wrong API key
bearer-without-API-key
valid POST /v1/radiographs/dicom
malformed manifest
malformed radiograph
idempotency
bounded concurrency
launcher failure boundaries
workspace cleanup
DICOM validation
restart/persistence verification
```

Reuse `scripts/local_dicom_burn_in.py`.

Do not duplicate the full functional test logic in YAML.

Verification failure must mark the verification workflow failed but MUST NOT run `docker compose down` on the healthy deployed service.

### Phase 7 — Resolve the current DICOM shape verification defect

The known recent behavior is:

```text
API health succeeds
valid /v1/radiographs/dicom returns HTTP 200
NPZ worker succeeds
DICOM is created
burn-in dimension assertion fails afterward
```

Do not remove dimension validation.

Do not hardcode observed production dimensions.

Do not swap rows and columns without evidence.

Do not derive expected shape from the DICOM currently under test.

Prove the relationship between:

```text
radiograph raw image shape
gain image shape
calibration metadata image_shape
remap map_x.shape
remap map_y.shape
processed_uint16.shape
generated TIFF shape
DICOM Rows/Columns
DICOM pixel_array.shape
```

The existing repository has expanded-canvas calibration behavior. Verify whether the active remap geometry is the authoritative pre-output shape for final processed TIFF/DICOM dimensions.

If evidence confirms that `cv2.remap` produces output shaped by `map_x/map_y`, derive expected final DICOM shape from the active production remap geometry.

Add the smallest focused regression test for:

```text
input image shape != remap output shape
```

and verify DICOM validation uses the authoritative processed-output canvas.

If evidence contradicts this hypothesis, stop and report the actual semantics instead of forcing the expected implementation.

### Phase 8 — Local verification

Before push/deployment, run the smallest relevant tests plus:

```bash
MPIPS_ENVIRONMENT=development uv run pytest \
  tests/api/test_api_surface.py \
  tests/api/test_dicom_authentication.py \
  tests/api/test_dicom_conversion.py \
  tests/test_host_launcher.py \
  -q
```

Run the focused regression test added for output-shape semantics.

Verify the protected converter SHA before and after.

Validate Compose configuration with safe non-secret placeholder values.

Do not claim skipped checks as passed.

### Phase 9 — Commit and push

After local verification passes, create focused commits.

Preferred scopes:

```text
refactor(deploy): use shared Madeena network and separate verification
fix(burn-in): validate authoritative output canvas
```

Maximum implementation commits:

```text
2
```

Push verified changes to `main`.

Do not use:

```text
git reset --hard
git clean -fd
git rebase
git push --force
```

### Phase 10 — Deploy once

Dispatch:

```text
deploy-internal-beta.yml
```

exactly once.

Do not use indefinite `gh run watch`.

Check status at most 3 times using sensible intervals.

If still running after bounded checks, report run ID, URL, job, step, and commit, then return `still-in-progress`.

Deployment success requires observed evidence of:

```text
launcher socket exists
Redis healthy
MPIPS API healthy
127.0.0.1:8014/health == 200
host binding == 127.0.0.1:8014
Redis host ports == none
madeena-software-network exists
mpips-api attached to madeena-software-network
private-network health probe == 200
deployed version marker persisted
```

Leave MPIPS running after success.

### Phase 11 — Verify once

After deployment success, dispatch:

```text
verify-internal-beta.yml
```

exactly once.

Verification success requires a real functional path through:

```text
POST /v1/radiographs/dicom
    -> isolated NPZ processing
    -> TIFF
    -> DICOM
```

and meaningful DICOM validation.

If verification fails:

- collect exact logs/evidence;
- classify the failure;
- do not tear down the healthy deployment;
- do not begin another speculative commit/deploy loop;
- return `awaiting-approval` unless the remaining correction was already reproduced locally and is explicitly within the published task.

Maximum post-deployment remediation cycles:

```text
1
```

### Phase 12 — MHCS integration handoff

Do not modify `mhcs-core`.

Report the verified MPIPS connection contract for the later MHCS deployment task.

Host operational endpoint:

```text
http://127.0.0.1:8014
```

Shared Docker network:

```text
madeena-software-network
```

Expected container-private endpoint, only if runtime-proven:

```text
http://mpips-api:8000
```

Future MHCS must attach its Image Gateway/image-worker service to:

```text
madeena-software-network
```

rather than using `127.0.0.1` from inside the MHCS container.

### Phase 13 — Update repository context

After observed successful deployment/verification, update `.agents/context/project.md` with:

- shared network name;
- network ownership/lifecycle rule;
- host endpoint;
- verified Docker-private service address;
- deployed commit;
- deployment run ID;
- verification run ID;
- health evidence;
- DICOM verification evidence;
- residual known risks.

Do not create duplicate root documentation.

## Acceptance criteria

- [ ] The shared network is named exactly `madeena-software-network`.
- [ ] The shared network is external/lifecycle-independent from the MPIPS Compose project.
- [ ] Network provisioning is idempotent through the approved GitHub Actions/self-hosted-runner path.
- [ ] MPIPS remains host-accessible only at `127.0.0.1:8014`.
- [ ] MPIPS is not publicly exposed.
- [ ] Redis has no published host port.
- [ ] MPIPS API is attached to `madeena-software-network`.
- [ ] A container attached to `madeena-software-network` can reach MPIPS privately and receive HTTP 200 from `/health`.
- [ ] Deployment and full DICOM verification are separate workflows.
- [ ] `deploy-internal-beta.yml` does not execute the full DICOM burn-in.
- [ ] `verify-internal-beta.yml` performs the functional burn-in.
- [ ] Verification failure does not tear down an otherwise healthy deployment.
- [ ] `/v1/radiographs/dicom` succeeds in the verification workflow.
- [ ] DICOM shape validation uses authoritative output-shape semantics and is not weakened.
- [ ] Protected converter SHA remains unchanged.
- [ ] `.mpips-version` records the successfully deployed runtime version.
- [ ] MPIPS remains running after successful task completion.
- [ ] `.agents/context/project.md` reflects observed final runtime evidence.

## Side-effect authorization

This task authorizes, within this bounded objective:

- repository file edits required by the task;
- focused test execution;
- Docker/Compose validation;
- creation of the external Docker network `madeena-software-network` through the self-hosted GitHub Actions runner;
- focused Git commits;
- push to `main`;
- one deployment workflow dispatch;
- one verification workflow dispatch;
- reading workflow logs and runtime status required for verification.

This task does NOT authorize:

- SSH;
- public ingress;
- destructive host cleanup;
- force push;
- secret disclosure;
- unrelated infrastructure changes;
- modification of `mhcs-core`;
- release/publication beyond this internal server deployment.

## Agent limits

Maximum:

```text
local diagnosis/fix iterations: 3
implementation commits: 2
deployment dispatches: 1
verification dispatches: 1
post-deployment remediation cycles: 1
workflow status checks per dispatch: 3
```

Do not enter an autonomous deployment/fix/deployment loop.

## Stop conditions

Stop and return to planning/approval if:

- repository baseline differs materially from the task baseline;
- unrelated dirty working-tree changes are present;
- required production calibration artifacts are missing or invalid;
- the shared network change requires public exposure;
- the required fix expands into unrelated architecture;
- protected converter modification appears necessary;
- a production mutation outside the explicit side-effect authorization is required;
- the bounded iteration limits are exhausted.

## Final report

Return these sections:

```text
1. Governing Task Revision
2. Starting and Final SHA
3. Files Changed
4. Shared Network Provisioning
5. Deployment Workflow Result
6. Host-Loopback Verification
7. Docker-Private Verification
8. Verification Workflow Result
9. DICOM Shape Root Cause and Fix
10. MHCS Integration Handoff
11. Residual Risks
12. Final Outcome
```

Required observed evidence:

```text
task publication SHA
starting SHA
final SHA
commits created
tests run and results
converter SHA before/after
deployment run ID and URL
verification run ID and URL
127.0.0.1:8014 health result
Docker port evidence
madeena-software-network inspect evidence
MPIPS network attachment evidence
private Docker DNS/health probe
DICOM HTTP status
DICOM Rows/Columns
DICOM pixel_array.shape
.mpips-version value
launcher PID/socket evidence
```

Use exactly one terminal state:

```text
succeeded
failed
blocked
awaiting-approval
still-in-progress
```

Use `succeeded` only if MPIPS is left running, host-loopback access is proven, private `madeena-software-network` access is proven, and the functional DICOM verification passes.
