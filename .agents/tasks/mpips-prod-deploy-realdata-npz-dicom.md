---
title: Trigger and verify production internal-beta deployment
document_id: TASK-MPIPS-PROD-DEPLOY-LIVE-001
version: 2.0
status: Validated/Published
language: en-US
last_updated: 2026-08-12
---

<!-- antigravity-code-agent-template:managed -->
# Task: Trigger and verify production internal-beta deployment

## Task identity

**Task title:**
Trigger and verify production internal-beta deployment

**Task path:**
`.agents/tasks/mpips-prod-deploy-realdata-npz-dicom.md`

**Task contract state:**
`Validated/Published`

**Delivery objective:**
Production internal-beta deployment — trigger and verify live operation

**Owner / designated planning authority:**
User directive; accepted baseline `1a15bae`

## Delivery context

The `deploy-internal-beta.yml` workflow has been refactored to the Madeena two-job standard template
pattern (commit `1a15bae`) and is ready for its first production run against the live server.

The workflow:
1. **`build` job** — runs focused checks (converter SHA gate, focused pytest), builds versioned API and worker images.
2. **`deploy` job** — provisions runtime, starts launcher, brings up Compose stack, runs live checks (health, auth, loopback port, burn-in), rolls back on failure.

The `setup-runtime-dirs.yml` workflow must have been run at least once first to populate
`/var/www/mpips-runtime/calibration/` on the self-hosted runner.

## Baseline and task revision

**Implementation baseline:**
`1a15bae` — "feat(ci): align production deployment to Madeena standard deploy-template pattern"

**Task revision:**
`resolved when published` — resolved by the immutable Git SHA of the commit containing this task.

## Objective

Trigger `.github/workflows/deploy-internal-beta.yml` on `main` and confirm that the two-job workflow
completes with `success` status and all built-in live checks pass on the production host.

## Authoritative inputs

### Governing authority

- `project.md` — loopback `127.0.0.1:8014`; self-hosted runner; no SSH; `/var/www/mpips-runtime` runtime root.
- `.github/workflows/deploy-internal-beta.yml @ 1a15bae` — the exact workflow that will execute.
- User directive (2026-08-12): production deployment follows the Madeena template pattern.

### Requirement traceability

- PROD-DEPLOY-01 → User directive: production deployment must be triggered and verified.
- PROD-DEPLOY-02 → `project.md`: loopback-only on `127.0.0.1:8014`.
- PROD-DEPLOY-03 → `project.md`: converter SHA must not have changed.
- PROD-DEPLOY-05 → workflow: burn-in verification must pass.

## Scope

### In scope

- Check `setup-runtime-dirs.yml` has been run (calibration files exist on runner).
- Trigger `deploy-internal-beta.yml` via `gh workflow run` or instruct user to trigger via GitHub UI.
- Monitor the workflow run until a terminal state (success or failure).
- Report the outcome, including workflow logs for the `build` and `deploy` jobs.

### Out of scope

- Changing any source code, tests, or workflow files.
- Exposing the API outside `127.0.0.1:8014`.
- Making any Git commits.

### Preserved behavior

- Converter SHA `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` unchanged.
- Loopback-only binding at `127.0.0.1:8014`.
- Idempotency and API key behavior intact.
- Redis has no published ports.

## Dependencies and assumptions

### Dependencies

- Self-hosted runner registered and online with Docker available.
- `/var/www/mpips-runtime/calibration/metadata.json` and `/var/www/mpips-runtime/calibration/remap.npz` must exist and be non-empty (populated by `setup-runtime-dirs.yml`). If absent, run `setup-runtime-dirs.yml` first and stop this task.
- No other `mpips-internal-beta` workflow run must be in progress (enforced by concurrency group).

### Approved assumptions

- The runner user owns `/var/www/mpips-runtime` and can run `mkdir`, `docker`, and `nohup` without `sudo`.
- The `gh` CLI may or may not be authenticated; if not, user triggers manually.

### Remaining approval requirements

- **Deployment trigger:** The Executor may trigger the workflow via `gh workflow run` if the CLI is authenticated. If the CLI is not authenticated, the Executor MUST stop and ask the user to trigger the workflow manually via the GitHub Actions UI.

## Required capabilities

- Shell command execution (`gh` CLI or browser access to GitHub Actions UI).
- Read access to workflow run logs via `gh run view` or the GitHub UI.

## Execution constraints

- Do not make any source code or workflow file changes — this task is trigger + observe only.
- Do not expose the API port publicly.
- If the `build` job fails, report the exact failing step and logs; do not attempt to modify code.
- If the `deploy` job fails, report the rollback outcome and launcher log tail.

## Acceptance criteria

- [ ] `setup-runtime-dirs.yml` has been run and calibration files are confirmed present on the runner (either from a previous run or verified in this task).
- [ ] `deploy-internal-beta.yml` workflow is triggered on `main`.
- [ ] **`build` job** completes with `success` — focused checks, converter SHA gate, pytest, and both Docker image builds pass.
- [ ] **`deploy` job** completes with `success` — runtime prep, launcher socket appears, Compose stack starts, all live checks pass (health `200`, auth `401`, loopback port `127.0.0.1:8014`, Redis no ports, no `latest`/`nginx`/`jwks` in config, burn-in passes).
- [ ] Workflow run overall status is `success`.
- [ ] No rollback was triggered.

## Verification requirements

### Required checks

```bash
# Check calibration files exist (run on runner or infer from setup-runtime-dirs output)
test -s /var/www/mpips-runtime/calibration/metadata.json && echo "metadata OK"
test -s /var/www/mpips-runtime/calibration/remap.npz && echo "remap OK"

# Trigger workflow
gh workflow run deploy-internal-beta.yml --ref main

# Monitor
gh run list --workflow deploy-internal-beta.yml --limit 1
gh run watch <run_id>

# View logs on completion
gh run view <run_id> --log
```

### Required evidence

The Executor MUST report:

- Whether calibration files were confirmed present before triggering.
- The GitHub Actions run ID and URL.
- Terminal status of both `build` and `deploy` jobs (success / failure).
- Any failing step name and relevant log output if a job failed.
- Whether rollback was triggered and its outcome.
- Final overall workflow run status.

## Stop conditions

- If calibration files are absent: stop, run `setup-runtime-dirs.yml` first, return result to planning.
- If `gh` CLI is not authenticated and user has not manually triggered the workflow: stop and request user action.
- If the `build` job fails due to a code defect (test failure, SHA mismatch): stop, do not attempt code fixes in this task, return to planning.
- If the `deploy` job fails and rollback is triggered: stop, report the failure fully, return to planning.

## Side-effect authorization

### Explicitly authorized side effects

- `gh workflow run deploy-internal-beta.yml --ref main` (trigger only).
- Reading workflow logs via `gh run view`.

No Git commits, source changes, or infrastructure mutations are authorized.

## Expected terminal outcome

### Review Required

Expected evidence:
- Workflow run ID and final status.
- Confirmation that both jobs completed successfully.
- Log excerpt confirming live checks passed (health 200, loopback port, burn-in).
- No rollback triggered.

