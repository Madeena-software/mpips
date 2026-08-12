---
title: Separate deployment from beta verification in GitHub Actions
document_id: TASK-MPIPS-CI-WORKFLOW-SEP-001
version: 1.1
status: Validated/Published
language: en-US
last_updated: 2026-08-12
review_verdict: REMEDIATION REQUIRED — bounded
execution_attempt: 31557705541 (deploy SUCCESS), 31557823992 (verify FAILURE)
remediation_baseline: e4166a0e3e2cf0c65a5d96e39af00fa9bb0c3af8
---

<!-- antigravity-code-agent-template:managed -->
# Task: Separate deployment from beta verification in GitHub Actions

## Task identity

**Task title:**
Separate deployment from beta verification in GitHub Actions

**Task path:**
`.agents/tasks/mpips-ci-workflow-separation.md`

**Task contract state:**
`Validated/Published`

**Delivery objective:**
CI workflow architecture refactor — decouple deployment readiness from functional acceptance testing

**Owner / designated planning authority:**
User directive 2026-08-12; Planner review conclusion: PLANNING REQUIRED on task `mpips-prod-deploy-realdata-npz-dicom.md`

## Delivery context

The current `deploy-internal-beta.yml` workflow couples two responsibilities in a single step (`Verify live beta and rollback on failure`):

1. Lightweight deployment readiness checks (health, port binding, Redis isolation)
2. Full functional burn-in (`local_dicom_burn_in.py run`) including DICOM dimension assertions

This coupling means that a burn-in assertion failure — even when the API is healthy and conversions return HTTP 200 — triggers a destructive rollback on a working deployment. The rollback is currently doubly unsafe because `MPIPS_PREVIOUS_VERSION` has never been written (no deployment has ever completed the burn-in pass), so rollback always tears the stack down without restoring anything.

This task refactors the CI architecture so that:
- A **successful deployment** means: the service started and is reachable.
- **Functional verification** is a separate, independently-triggerable workflow.

## Baseline and task revision

**Implementation baseline:**
`eb445a40e66fc383ec5d29d18f4180345a0b1d2f` — "fix(burn-in): use dynamic target_shape in validate_dicom assertions"

**Task revision:**
`resolved when published` — resolved by the immutable Git SHA of the commit containing this task.

## Objective

1. Refactor `.github/workflows/deploy-internal-beta.yml` to perform deployment + lightweight readiness checks only.
2. Create `.github/workflows/verify-internal-beta.yml` for full post-deployment functional verification.
3. Make a single focused commit and push to `main`.
4. Dispatch `deploy-internal-beta.yml` once and confirm it reaches `success` without burn-in.
5. Dispatch `verify-internal-beta.yml` once; report the result including any assertion failure evidence.

## Authoritative inputs

- `project.md` — loopback `127.0.0.1:8014`; self-hosted runner; no SSH; `/var/www/mpips-runtime` runtime root; converter SHA `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`
- `.github/workflows/deploy-internal-beta.yml @ eb445a40` — current workflow to refactor
- `scripts/local_dicom_burn_in.py @ eb445a40` — burn-in script to reuse (do not modify)
- User directive 2026-08-12: architecture boundaries, rollback semantics, agent iteration limits

## Requirement traceability

- CI-SEP-01 → User directive: deployment workflow must succeed independently of functional acceptance.
- CI-SEP-02 → User directive: verification workflow must be independently triggerable (`workflow_dispatch`).
- CI-SEP-03 → User directive: verification must auto-run after successful deployment (`workflow_run` on `Deploy MPIPS Internal Beta`).
- CI-SEP-04 → User directive: verification failure must NOT trigger automatic rollback.
- CI-SEP-05 → User directive: deploy workflow must record `.mpips-version` on successful deployment.
- CI-SEP-06 → User directive: rollback must NOT fire from the verification workflow.
- CI-SEP-07 → `project.md`: converter SHA gate must remain in build job.
- CI-SEP-08 → `project.md`: loopback-only binding at `127.0.0.1:8014` must remain a deployment readiness check.
- CI-SEP-09 → User directive: do not modify `local_dicom_burn_in.py` or application code in this task.
- CI-SEP-10 → User directive: do not modify `tiff_json_to_dcm.py` in this task.

## Scope

### In scope

**`deploy-internal-beta.yml` — keep:**
- `build` job: checkout, Python, uv, focused checks (converter SHA gate, pytest), set version, build images — **unchanged**
- `deploy` job steps: checkout, Python, uv, set deployment variables, validate env, prepare runtime + rollback state, start versioned worker launcher, deploy Compose services — **unchanged**
- Deployment readiness checks (refactored out of the `Verify live beta and rollback on failure` step):
  - `wait_for_health` — curl loop until `GET /health` returns 200
  - `test "$(docker port "$API_CONTAINER" 8000/tcp)" = "127.0.0.1:8014"` — loopback binding
  - `test -z "$(docker port "$REDIS_CONTAINER" || true)"` — Redis has no external port
  - `! docker compose ... config | grep -Eiq 'latest|nginx|jwks'` — config safety check
- Write `.mpips-version` and `.mpips-worker-image` on deployment readiness success
- `Show failed deployment logs` step — unchanged
- Rollback logic, scoped to deployment readiness failure only

**`deploy-internal-beta.yml` — remove:**
- `verify_key_status` auth checks from the deployment readiness step (move to verify workflow)
- `uv run python scripts/local_dicom_burn_in.py ... run` (both occurrences — one inside `live_checks()` and one after the API restart) — move to verify workflow
- `docker compose ... restart mpips-api` — remove (unnecessary once burn-in is removed from deploy)

**`verify-internal-beta.yml` — create new:**

Triggers:
```yaml
on:
  workflow_dispatch:
  workflow_run:
    workflows: ["Deploy MPIPS Internal Beta"]
    types: [completed]
```

Jobs: single `verify` job, `runs-on: [self-hosted, production]`, conditional:
```yaml
if: >-
  github.event_name == 'workflow_dispatch' ||
  github.event.workflow_run.conclusion == 'success'
```

Steps:
1. Checkout
2. Set up Python 3.12
3. Install uv and dependencies (`--extra service --extra dev --extra npz-worker --extra imager`)
4. Set deployment variables (same as deploy workflow: `REMOTE_PATH`, `MPIPS_LAUNCHER_SOCKET_PATH`, `COMPOSE_PROJECT_NAME`)
5. Run burn-in verification:
   - `uv run python scripts/local_dicom_burn_in.py --base-dir "$REMOTE_PATH/burn-in" prepare`
   - Auth checks (missing key, wrong key, bearer-without-key) using curl
   - `uv run python scripts/local_dicom_burn_in.py --base-dir "$REMOTE_PATH/burn-in" --url http://127.0.0.1:8014 run`
6. Show verification logs on failure (no rollback, no `exit` from rollback path)

Concurrency: same `group: mpips-internal-beta`, `cancel-in-progress: false` — prevents verification from running while a deployment is in progress.

### Out of scope

- Modifying `scripts/local_dicom_burn_in.py`
- Modifying `mpips/engine/imager_pipeline/tiff_json_to_dcm.py`
- Modifying any application source code or tests
- Redesigning the rollback system
- Fixing the DICOM dimension assertion (Phase F, separate task after this one succeeds)
- Modifying `ci.yml` or `setup-runtime-dirs.yml`

### Preserved behavior / invariants

- Converter SHA gate (`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`) remains in the `build` job of `deploy-internal-beta.yml`
- API loopback binding at `127.0.0.1:8014` remains a deployment readiness check
- Redis isolation check remains a deployment readiness check
- Concurrency group `mpips-internal-beta` applies to both workflows
- `workflow_run` trigger does NOT create a recursive trigger (verify does not trigger deploy)
- A failed deployment does NOT automatically launch verification
- `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` and `NODE_OPTIONS` env vars are preserved
- All existing `deploy` job runtime directory and launcher steps are unchanged

## Material dependencies

- Self-hosted runner `[self-hosted, production]` must be registered and online
- `setup-runtime-dirs.yml` must have been run previously (calibration files must exist at `/var/www/mpips-runtime/calibration/`)
- No other `mpips-internal-beta` workflow run in progress
- `gh` CLI authenticated on the runner for dispatch

## Approved assumptions

- The `workflow_run` trigger for `verify-internal-beta.yml` is the safest GitHub Actions mechanism for auto-verification after deployment
- A single `verify` job (no matrix) is sufficient
- The auth checks in the verify workflow can reuse inline curl (no separate script needed), keeping them close to the burn-in script call for readability

## Required capabilities

- Read/write to `.github/workflows/`
- `git commit` and `git push` to `main`
- `gh workflow run` to dispatch both workflows
- `gh run view` and `gh run list` to observe results

## Execution constraints

- **One focused commit only** — both workflow file changes in a single commit
- **Commit message scope:** `refactor(ci): separate deployment from beta verification`
- **Do not** make multiple speculative commits
- **Do not** modify any files outside `.github/workflows/`
- **Do not** enter an indefinite polling loop — check workflow status at most 3 times per workflow
- If a workflow is still running after 3 checks, report run ID, URL, current job/step, and stop with `still-in-progress`
- Maximum per agent iteration: one commit, one deployment dispatch, one verification dispatch, no second remediation cycle
- After verification, if the DICOM assertion reproduces, **stop and report** — do not enter another fix/deploy loop

## Acceptance criteria

### Deploy workflow (`deploy-internal-beta.yml`)

- [ ] `build` job: unchanged behavior — focused checks, SHA gate, pytest, image builds all pass
- [ ] `deploy` job: Compose stack starts, launcher socket appears, health check passes, loopback binding correct, Redis has no external port, config check clean
- [ ] `.mpips-version` is written to `$REMOTE_PATH/.mpips-version`
- [ ] `.mpips-worker-image` is written to `$REMOTE_PATH/.mpips-worker-image`
- [ ] Workflow concludes `success` without running `local_dicom_burn_in.py run`
- [ ] No rollback was triggered

### Verify workflow (`verify-internal-beta.yml`)

- [ ] Workflow is present and valid YAML
- [ ] Triggers on `workflow_dispatch`
- [ ] Triggers automatically after a successful `Deploy MPIPS Internal Beta` via `workflow_run`
- [ ] Does NOT trigger after a failed deployment
- [ ] Runs burn-in: reports pass or fail with exact failure output
- [ ] Does NOT perform automatic rollback on failure

### Commit

- [ ] Single commit on `main` with message matching `refactor(ci): separate deployment from beta verification`
- [ ] Only `.github/workflows/deploy-internal-beta.yml` and `.github/workflows/verify-internal-beta.yml` changed

## Verification requirements

### Required checks before commit

```bash
# YAML syntax validation
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-internal-beta.yml'))" && echo "deploy: YAML OK"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/verify-internal-beta.yml'))" && echo "verify: YAML OK"

# Confirm tiff_json_to_dcm.py SHA is unchanged
test "$(sha256sum mpips/engine/imager_pipeline/tiff_json_to_dcm.py | awk '{print $1}')" = \
  "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0" && echo "SHA OK"

# Confirm no application files modified
git diff --name-only HEAD

# Focused application tests
MPIPS_ENVIRONMENT=development uv run pytest \
  tests/api/test_api_surface.py \
  tests/api/test_dicom_authentication.py \
  tests/api/test_dicom_conversion.py \
  tests/test_host_launcher.py \
  -q
```

### Required evidence

The Executor MUST report:

1. Git diff summary (files changed, lines added/removed)
2. YAML validation results for both files
3. Focused test results
4. Deployment run ID, URL, final status, and key step outputs (version recorded, health=200)
5. Verification run ID, URL, final status
6. If verification fails: exact traceback and assertion values (what `dataset.Rows`/`dataset.Columns` were vs. `target_shape`)

## Stop conditions

- If YAML validation fails: fix before committing
- If focused tests fail: stop, do not commit, return to planning
- If the deploy workflow fails at a step OTHER than burn-in: stop, report, return to planning
- If the deploy workflow still runs burn-in (burn-in is not removed): stop, do not record success
- After verification dispatch: if still running after 3 status checks, report `still-in-progress` and stop
- If verification fails on the DICOM assertion: stop and report awaiting-approval (do NOT start another fix/deploy cycle)

## Side-effect authorization

### Explicitly authorized

- Edit `.github/workflows/deploy-internal-beta.yml`
- Create `.github/workflows/verify-internal-beta.yml`
- `git add`, `git commit`, `git push origin main` — single commit only
- `gh workflow run deploy-internal-beta.yml --ref main` — once
- `gh workflow run verify-internal-beta.yml --ref main` — once, after deployment succeeds
- Reading workflow logs via `gh run view`

### Not authorized

- Modifying any file outside `.github/workflows/`
- Multiple commits
- Push to any branch other than `main`
- Modifying application code, tests, scripts, Docker files, or compose files
- Automatic rollback from verify workflow

## Expected terminal outcome

After successful deployment (Phase E), the Executor should report:
- Deploy: ✅ success — `.mpips-version` written, no burn-in run
- Verify: pass or fail with exact evidence

If verification fails on the dimension assertion, the Executor stops and reports:
- Exact DICOM `Rows`, `Columns` values from the failure
- The `target_shape` value used by the assertion
- The production calibration `image_shape`
- Classification of the defect (application / processing-shape / DICOM / calibration / test-harness)

Final outcome: `succeeded`, `failed`, `blocked`, `awaiting-approval`, or `still-in-progress`
