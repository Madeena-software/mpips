---
title: Align production deployment to Madeena standard template
document_id: TASK-MPIPS-PROD-DEPLOY-TEMPLATE-001
version: 1.0
status: Validated/Published
language: en-US
last_updated: 2026-08-12
---

<!-- antigravity-code-agent-template:managed -->
# Task: Align production deployment to Madeena standard deploy-template pattern

## Task identity

**Task title:**
Align production deployment to Madeena `templates/prod` standard pattern

**Task path:**
`.agents/tasks/mpips-prod-deploy-template-alignment.md`

**Task contract state:**
`Validated/Published`

**Delivery objective:**
Production internal-beta deployment — align with proven Madeena CI/CD template

**Owner / designated planning authority:**
User directive (2026-08-12) — explicit instruction to follow `Madeena-software/deploy-templates/tree/main/templates/prod`

## Delivery context

The existing `.github/workflows/deploy-internal-beta.yml` is a working hand-rolled workflow.
The user has directed that the production deployment follow the proven
[`Madeena-software/deploy-templates/templates/prod`](https://github.com/Madeena-software/deploy-templates/tree/main/templates/prod)
reference, specifically `standard-deploy-swarm.yml`, which has been successfully applied in other repositories.

The existing workflow already embeds the essential concepts (immutable versioned images, calibration
pre-check, launcher management, live health verification, rollback). The task is to **structurally
align** it with the template pattern: separate build and deploy jobs, top-level env guards, job
`timeout-minutes`, and `require_env`-style secret validation guards, while preserving every MPIPS-specific
constraint (loopback `127.0.0.1:8014`, Python/uv stack, host-launcher, converter SHA gate, burn-in).

A second stale workflow `.github/workflows/deploy-swarm.yml` exists that uses Docker Swarm
(`docker stack deploy`) and is incompatible with the current compose-based production topology.
It must be removed.

## Baseline and task revision

**Implementation baseline:**
`bc2e6ea` — "feat: add workflow for production runtime directory setup"

**Task revision:**
`resolved when published` — to be resolved by the immutable Git SHA of the commit containing this task.

## Objective

Refactor `.github/workflows/deploy-internal-beta.yml` to structurally match the
`standard-deploy-swarm.yml` template pattern, and remove the stale `deploy-swarm.yml` workflow,
so that the production deployment follows the proven Madeena template while preserving all MPIPS
operational invariants.

## Authoritative inputs

### Governing authority

- User directive (2026-08-12): "use `https://github.com/Madeena-software/deploy-templates/tree/main/templates/prod` as reference; it is proven successful in another repo."
- `.agents/context/project.md` — Deployment section; loopback `127.0.0.1:8014`; self-hosted runner; no SSH; `/var/www/mpips-runtime` runtime root; `deploy-internal-beta.yml` as canonical workflow.
- `project.md` — "The Madeena deployment-template repository is the external authority for environment-template implementation. Copy and specialize the applicable templates in `mpips`."
- `standard-deploy-swarm.yml` @ `Madeena-software/deploy-templates main` — reference pattern (blob SHA `f28856e59042e1c7d9debc1c1b466fb0c0983661`).

### Requirement traceability

- PROD-DEPLOY-01 → User directive: production deployment must follow the Madeena template pattern.
- PROD-DEPLOY-02 → `project.md`: loopback-only on `127.0.0.1:8014`; no public exposure.
- PROD-DEPLOY-03 → `project.md`: converter SHA `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` must remain unchanged.
- PROD-DEPLOY-04 → `project.md`: all server-side operations through GitHub Actions self-hosted runner; no SSH.
- PROD-DEPLOY-05 → existing `deploy-internal-beta.yml`: burn-in verification must pass before acceptance.

## Scope

### In scope

1. **Refactor `.github/workflows/deploy-internal-beta.yml`** to adopt the template structural pattern:
   - Split into a `build` job (runs Python focused checks, converter SHA gate, builds both Docker images, pins the version) and a `deploy` job (depends on `build`, handles runtime prep, launcher, compose up, live checks, rollback).
   - Add `timeout-minutes` to both jobs (build: ≤ 60, deploy: ≤ 30).
   - Add top-level `env:` block with `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` and `NODE_OPTIONS: "--dns-result-order=ipv4first"`.
   - Add a `require_env`-style guard at the start of the deploy step to fail fast when required variables are absent (minimum: `REMOTE_PATH`, `MPIPS_VERSION`).
   - All MPIPS-specific logic must be preserved exactly (see Preserved behavior).

2. **Remove `.github/workflows/deploy-swarm.yml`** — this stale workflow uses Docker Swarm which is incompatible with the current topology.

3. **Commit both changes** in a single commit referencing this task, then push to origin main.

### Out of scope

- Any changes to `docker-compose.prod.yml`, `Dockerfile`, `docker/Dockerfile.worker`, source code, or tests.
- Changing any production runtime secret names or values.
- Enabling Swarm mode (`docker stack deploy`) — MPIPS uses plain `docker compose`.
- Adding database, MinIO, S3, or Laravel-specific template sections (not applicable to MPIPS).

### Preserved behavior

- Loopback binding `127.0.0.1:8014` — port-binding check in live verification.
- Converter SHA gate `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Focused pytest gate (`test_api_surface`, `test_dicom_authentication`, `test_dicom_conversion`, `test_host_launcher`).
- Calibration pre-check (`test -s metadata.json` and `test -s remap.npz`).
- Launcher lifecycle (kill old PID, remove old socket, start new launcher, wait for socket).
- Rollback logic (restore previous compose, relaunch previous launcher version).
- `COMPOSE_PROJECT_NAME=mpips-internal-beta` and `REMOTE_PATH=/var/www/mpips-runtime`.
- `concurrency: group: mpips-internal-beta, cancel-in-progress: false`.
- Redis isolation check (no published ports on redis container).
- Burn-in verification (both `prepare` and `run` phases).
- Version pinning files (`.mpips-version`, `.mpips-worker-image`).
- `workflow_dispatch`-only trigger (no push/PR triggers).
- Task validation step: `.agents/skills/agent-task/scripts/validate_task.py` against archive task.
- `show-failed-deployment-logs` step (`if: failure()`).

## Dependencies and assumptions

### Dependencies

- `setup-runtime-dirs.yml` must have been run at least once to populate calibration files. Pre-existing operational dependency; not changed by this task.
- Self-hosted runner registered and online with Docker available.
- Baseline `bc2e6ea` is clean.

### Approved assumptions

- The `standard-deploy-swarm.yml` template applies structurally; its Laravel/PHP/DB/MinIO sections are not applicable and must not be introduced.
- `deploy-swarm.yml` has never been used in production and its removal is safe.
- No GitHub Secrets need to be added; the current deployment uses internal-beta fixed API key only.

### Remaining approval requirements

- **Production deployment trigger:** After committing, the user must manually trigger `deploy-internal-beta.yml` via GitHub Actions UI or `gh workflow run`. The Executor MUST NOT trigger the production deployment autonomously.

## Required capabilities

- Repository read and write (file editing and Git commit/push).
- Shell command execution (YAML syntax validation).

## Execution constraints

- The Executor must NOT trigger the GitHub Actions workflow — only commit and push the file changes.
- Workflow must remain `workflow_dispatch`-only.
- Do not introduce `docker stack deploy` or `docker swarm` commands.
- Do not add database, email, S3, MinIO secrets or steps.
- Maintain `set -Eeuo pipefail` in all inline shell scripts.
- `require_env` guard must check at minimum: `REMOTE_PATH`, `MPIPS_VERSION`.
- Both jobs must run on `self-hosted`.
- `build` job must pass `app_version` (the commit SHA) to `deploy` job via `outputs`.

## Acceptance criteria

- [ ] `.github/workflows/deploy-internal-beta.yml` has two jobs: `build` and `deploy`.
- [ ] `build` job: Python setup, uv sync, focused pytest, converter SHA gate, both Docker image builds, `app_version` output.
- [ ] `deploy` job: depends on `build`, `require_env` guard, all deployment steps (runtime prep, launcher lifecycle, compose up, live checks, rollback, burn-in, version files).
- [ ] Both jobs have `timeout-minutes` set.
- [ ] Top-level `env:` block includes `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` and `NODE_OPTIONS`.
- [ ] All MPIPS-specific invariants are preserved (see Preserved behavior section).
- [ ] `.github/workflows/deploy-swarm.yml` no longer exists in the repository.
- [ ] Changes committed in a single Git commit and pushed.
- [ ] YAML is syntactically valid.

## Verification requirements

### Required checks

- `python -c "import yaml, sys; yaml.safe_load(open('.github/workflows/deploy-internal-beta.yml'))" && echo YAML_OK`
- `test ! -f .github/workflows/deploy-swarm.yml && echo removed`
- `git diff --stat HEAD~1` — confirm only the two workflow files appear.

### Required evidence

The Executor MUST report:

- Exact implementation revision (Git commit SHA after push).
- YAML syntax validation output.
- `git diff --stat HEAD~1` output.
- Confirmation that converter SHA value is unchanged in the refactored file.
- Confirmation of each preserved-behavior element's location in the committed file.
- Any deviations and their rationale.

## Stop conditions

- If refactoring requires changing MPIPS operational logic beyond structural reorganization — stop and return to planning.
- If `docker-compose.prod.yml` requires changes — stop and return to planning.
- If splitting into two jobs requires image registry or artifact storage that is not available on the runner — stop and return to planning with specific blocker.
- If any required side effect beyond the two authorized workflow file changes is needed — stop.

## Side-effect authorization

### Explicitly authorized side effects

- Edit `.github/workflows/deploy-internal-beta.yml`.
- Delete `.github/workflows/deploy-swarm.yml`.
- `git add`, `git commit`, and `git push origin main` for these two files.

All other side effects are NOT authorized.

## Expected terminal outcome

### Review Required

Expected evidence:
- Committed Git SHA (pushed to origin main).
- YAML validation output (pass).
- `git diff --stat HEAD~1` confirming only workflow files changed.
- Annotated summary of where each preserved MPIPS behavior appears in the refactored file.
