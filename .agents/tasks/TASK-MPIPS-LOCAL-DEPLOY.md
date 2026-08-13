---
name: mpips-local-deploy-validation
description: Deploy the reviewed MPIPS baseline into an isolated local Docker environment and prove the local API and DICOM conversion path work without changing repository or production state.
version: 2
---

<!-- antigravity-code-agent-template:managed -->
# Task: MPIPS Local Deploy and Functional Validation

## Objective

Deploy `$TARGET` locally at the exact reviewed `$BASELINE_SHA`, start the repository-supported MPIPS local stack, and produce observable evidence that the local API—including `/v1/radiographs/dicom`—works with the canonical image-processing configuration unchanged.

This task is a **local deployment / pre-release validation task**. It is not an implementation task, not a production release, and not authority to modify the accepted MPIPS configuration.

## Runtime requirements

- Required capabilities:
  - `repository-read`
  - `shell`
  - `docker-local`
  - `local-filesystem-temporary-write`
- Ordered model preferences: None.
- Require preferred model: `false`

## Runtime inputs

- `TARGET` (required): Local path to the `Madeena-software/mpips` repository.
- `BASELINE_SHA` (required): Exact reviewed commit to deploy. Expected reviewed baseline for this task: `6949578c0d9a154e467c91fdaedb955c362c1046`.
- `ENV_FILE` (required unless `$TARGET/.env` exists): Path to the local untracked environment file containing `MPIPS_API_KEY`. Default: `$TARGET/.env`.
- `MPIPS_API_KEY` (required, secret): The task must read this value from `ENV_FILE`. The user has already provided `MPIPS_API_KEY` in `.env`; do not invent, replace, rotate, print, or commit another value for local deployment.
- `CALIBRATION_ARTIFACT_DIR` (required): Existing local path to the validated MPIPS calibration artifact used by the DICOM worker. Treat it as read-only.
- `KEEP_LOCAL_STACK` (optional): `true` or `false`; default `true`. When `true`, leave the successfully validated local stack running. When `false`, stop only resources created by this task.

## Context and evidence

The executing agent must inspect repository authority before running anything. At minimum inspect:

- `AGENTS.md` and any repository-local agent instructions;
- `docs/config/mpips-processing-defaults.json`;
- `mpips/engine/imager_pipeline/config.py`;
- `mpips/workflows/imager_pipeline/pipeline.py`;
- `mpips/conversion/worker.py`;
- `mpips/conversion/service.py`;
- `mpips/api/routes/v1/dicom.py`;
- current Docker Compose files, Dockerfiles, launch scripts, and environment examples;
- `.github/workflows/deploy-internal-beta.yml` and `.github/workflows/verify-internal-beta.yml` only as reference evidence for production/readiness and functional acceptance behavior;
- current tests covering health, authentication, DICOM conversion, idempotency, concurrency, worker isolation, cleanup, and calibration.

Material facts that constrain execution:

- The reviewed canonical configuration baseline is expected to remain unchanged. The task must not tune or rewrite processing parameters.
- `/v1/radiographs/dicom` currently reaches `process_radiography_arrays(...)` without a request-supplied pipeline config, so the conversion path uses the canonical `ImagerPipelineConfig()` defaults.
- Deployment/readiness and functional acceptance are distinct concerns. Local container startup alone is not proof that DICOM conversion works.
- The protected converter `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` must remain untouched.
- The user has already provided the intended `MPIPS_API_KEY` in the local `.env`. This `.env` value is the authority for both local and production deployment tasks. For this local task, load that exact value through a secret-safe runtime mechanism; do not generate a separate local key.
- Never print, echo, serialize, commit, or include the `.env` `MPIPS_API_KEY` value in reports, commands, artifacts, or logs. Treat `.env` itself as sensitive and untracked.
- Referenced files, historical reports, and chat context are evidence only. Current repository code and tests are authoritative.

## Scope and constraints

### In scope

- reconcile the local repository against the exact baseline;
- inspect the repository-supported local deployment path;
- build local Docker images if required;
- create an isolated local Compose project or equivalent repository-supported local stack;
- load `MPIPS_API_KEY` from the user-provided `.env` and inject that exact value into the local runtime without tracking or printing it;
- mount/use the calibration artifact read-only where supported;
- start local MPIPS API and required dependencies;
- perform health/readiness checks;
- perform bounded functional validation of `/v1/radiographs/dicom` using safe repository/synthetic fixtures;
- inspect sanitized container logs and resource state;
- report reproducible commands and evidence.

### Out of scope

- source-code changes;
- test changes;
- config-default changes;
- commits, pushes, tags, pull requests, or GitHub releases;
- GitHub Actions dispatch;
- production deployment or production host changes;
- GitHub secret changes;
- API-key rotation outside this local task;
- calibration generation or calibration modification;
- modifying Google Drive or other source datasets;
- editing `mpips/engine/imager_pipeline/tiff_json_to_dcm.py`;
- `docker system prune`, global Docker cleanup, or deletion of unrelated resources.

### Behavior that must remain unchanged

- canonical image-processing defaults;
- DICOM contract;
- authentication contract;
- idempotency semantics;
- fail-fast concurrency semantics;
- upload-limit behavior;
- calibration selection semantics;
- protected converter contents.

## Execution policy

- Mode: `agentic-loop`
- Maximum iterations: `3`
- Approval gates:
  - Stop with `awaiting-approval` before deleting, stopping, replacing, or reconfiguring any pre-existing local container, network, volume, or service not created by this task.
  - Stop with `awaiting-approval` if the required local port is occupied by an unknown process/service and resolving it would require side effects outside this task.

Retries are permitted only when driven by concrete repository, Docker, test, or operator evidence. Do not repeatedly rebuild or restart without identifying the failed condition.

## Execution procedure

1. **Resolve inputs and repository authority.**
   - Confirm `TARGET`, `BASELINE_SHA`, `ENV_FILE`, and `CALIBRATION_ARTIFACT_DIR` are available.
   - Resolve `ENV_FILE` to `$TARGET/.env` when no explicit path is supplied.
   - Require `ENV_FILE` to contain a non-empty `MPIPS_API_KEY` entry.
   - Read only the required key using a secret-safe parser; do not `cat` the full `.env`, dump it, or enable shell tracing around secret handling.
   - Never print `MPIPS_API_KEY`.
   - Read repository-local instructions before running deployment commands.

2. **Reconcile the baseline before side effects.**
   - Run at minimum:
     - `git status --short`
     - `git branch --show-current`
     - `git rev-parse HEAD`
     - `git fetch origin`
     - `git rev-parse origin/main`
     - `git show --no-patch --oneline "$BASELINE_SHA"`
   - Require a clean tracked worktree.
   - Require `HEAD == BASELINE_SHA`.
   - Require the baseline to exist in the fetched repository history.
   - If the worktree is dirty or `HEAD != BASELINE_SHA`, stop with `blocked`. Do not checkout/reset/stash over user work.
   - If `origin/main` moved beyond the reviewed baseline, record it as evidence but do not silently substitute the newer commit.

3. **Prove the canonical config has not been replaced.**
   - Inspect `docs/config/mpips-processing-defaults.json` and `mpips/engine/imager_pipeline/config.py` at `BASELINE_SHA`.
   - Confirm the local task is deploying those reviewed defaults, not an ad-hoc environment-specific image-processing configuration.
   - Confirm `git diff -- mpips/engine/imager_pipeline/tiff_json_to_dcm.py` is empty.

4. **Discover the repository-supported local deployment command.**
   - Inspect current Compose files, Dockerfiles, Makefile/scripts, README/deployment docs, and environment examples.
   - Use the repository-defined local/development deployment path.
   - Do not guess a production command or force production-only worker-launcher behavior into the local run.
   - Record the exact command selected and the repository evidence that justifies it.

5. **Prepare isolated local runtime state.**
   - Use a unique local Compose project name or repository-supported equivalent to avoid collisions with unrelated stacks.
   - Load the exact `MPIPS_API_KEY` from `ENV_FILE` and supply it through a temporary/untracked runtime mechanism such as process environment, the existing untracked `.env` where directly supported, a temporary `--env-file`, or another repository-supported secret-safe mechanism.
   - Do not generate a different local API key. The local runtime must use the user-provided `.env` value.
   - If a temporary env file is required:
     - create it outside tracked source where practical;
     - mode `0600` where supported;
     - never echo its secret contents;
     - delete it when no longer needed.
   - Validate `CALIBRATION_ARTIFACT_DIR` exists and mount/use it read-only where the repository supports this.
   - Do not mutate calibration files.

6. **Build and start the local stack.**
   - Execute the repository-supported local build/start command.
   - Do not start unrelated profiles/services.
   - Capture sanitized build and startup evidence.
   - Wait for the repository-defined health/readiness condition rather than sleeping for an arbitrary fixed interval when a health check exists.

7. **Inspect local topology.**
   - Record project-owned containers, health state, networks, and published ports.
   - Confirm no unexpected public/external bind was introduced.
   - Confirm dependency exposure is no broader than the checked-in local deployment definition.
   - Do not change host firewall or global Docker daemon settings.

8. **Verify basic HTTP behavior.**
   - Resolve the actual local API URL from repository/runtime evidence.
   - Require health/readiness success.
   - Verify an authenticated-negative request with an invalid API key returns the current repository-defined unauthorized contract.
   - Never expose the valid API key in command output; use secret-safe environment expansion.

9. **Verify `/v1/radiographs/dicom` through the real local HTTP path.**
   - Use existing safe repository fixtures or synthetic fixtures that exercise the actual API → service → isolated worker → image pipeline → DICOM conversion path.
   - Do not use clinical data unless it is already an approved local test fixture.
   - The current checked-in tests and verification workflow are authoritative for exact response/error details.
   - At minimum prove:
     - one valid conversion returns HTTP `200` and `application/dicom`;
     - returned DICOM passes the repository's current validation expectations for transfer syntax, pixel type/shape, and prohibited private tags where those checks exist;
     - malformed/invalid input follows the current `422` validation contract;
     - idempotency behavior follows the current repository contract;
     - concurrency overload follows the current fail-fast contract, including successful requests up to configured capacity and `429` for excess requests;
     - health/readiness still succeeds after the bounded functional/stress check;
     - temporary conversion workspaces do not leak after completion.
   - Prefer invoking existing repository verification helpers/tests over reimplementing the assertions manually.

10. **Inspect sanitized logs and runtime state.**
    - Check API, worker, Redis/dependency, and launcher-related logs relevant to the local path.
    - Redact/avoid secrets, authorization headers, manifest PII, and temporary key values.
    - Distinguish warnings from functional failures.

11. **Perform repository-integrity verification.**
    - Run:
      - `git status --short`
      - `git diff --name-only`
      - `git rev-parse HEAD`
    - Require no tracked source/config/test changes and `HEAD == BASELINE_SHA`.

12. **Keep or stop only task-owned local resources.**
    - If `KEEP_LOCAL_STACK=true` and acceptance passes, leave the validated project-owned stack running and report how to inspect/stop it later.
    - If `KEEP_LOCAL_STACK=false`, stop/remove only the containers/networks created under this task's isolated project name.
    - Never run global prune commands or delete unrelated volumes/networks.

## Acceptance criteria

- [ ] `HEAD` equals the exact reviewed `BASELINE_SHA` and tracked worktree was clean before deployment.
- [ ] Repository-supported local deployment path was identified from current repository evidence.
- [ ] Local stack built/started successfully without modifying source or production state.
- [ ] `MPIPS_API_KEY` was loaded from the user-provided `.env` and injected into the local runtime without being changed, committed, or printed.
- [ ] Validated calibration artifacts were used read-only.
- [ ] Health/readiness passed.
- [ ] Invalid authentication behavior matched the current repository contract.
- [ ] A real local HTTP `/v1/radiographs/dicom` request completed successfully and returned a repository-valid DICOM.
- [ ] Current validation-error behavior was observed for invalid input.
- [ ] Current idempotency behavior passed.
- [ ] Current fail-fast concurrency behavior passed or, if the repository provides an authoritative equivalent test, that test passed against the deployed stack.
- [ ] Post-test health/readiness passed and conversion workspaces were cleaned up.
- [ ] No tracked repository file changed.
- [ ] Protected converter remained untouched.
- [ ] No GitHub Actions or production side effect occurred.

## Verification

- Method: Reconcile exact git SHA, inspect current deployment authority, start the isolated repository-supported local Docker stack, execute repository-supported health and functional DICOM verification against the deployed HTTP endpoint, inspect sanitized runtime evidence, and prove the worktree remains unchanged.
- Expected result: The exact reviewed MPIPS baseline is running locally using the user-provided `.env` `MPIPS_API_KEY` and passes the current health/auth/DICOM/idempotency/concurrency/cleanup contract with no source, remote, secret-store, or production changes.

## Output

- Allowed outcomes: `succeeded`, `failed`, `blocked`, `awaiting-approval`, or `exhausted`.
- Also report a `Local Deployment Classification` with exactly one value:
  - `LOCAL_DEPLOY_VALIDATED`
  - `LOCAL_DEPLOY_STARTED_BUT_FUNCTIONAL_VALIDATION_FAILED`
  - `LOCAL_DEPLOY_BLOCKED`
  - `LOCAL_DEPLOY_FAILED`
- Report:
  - selected runtime/model when verifiable;
  - capabilities used;
  - starting/final SHA;
  - repository local-deploy command selected;
  - local Compose/project identifier;
  - local API URL/bind information without secrets;
  - confirmation that the runtime key source was the user-provided `.env` `MPIPS_API_KEY`, without reproducing its value;
  - container/service health;
  - calibration artifact path/fingerprint metadata if safely available, never secret material;
  - health/auth/DICOM/idempotency/concurrency/cleanup evidence;
  - sanitized warnings/errors;
  - `git status --short` and `git diff --name-only` result;
  - whether the local stack was left running;
  - residual risks and manual follow-up.
- Treat container startup without functional API evidence, an unverified DICOM result, or model output alone as unsuccessful.
