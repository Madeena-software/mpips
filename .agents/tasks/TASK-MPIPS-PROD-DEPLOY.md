---
name: mpips-production-deploy-and-verify
description: Deploy one explicitly authorized reviewed MPIPS commit to the internal-beta production environment and independently verify functional acceptance at the same SHA.
version: 2
---

<!-- antigravity-code-agent-template:managed -->
# Task: MPIPS Production Deploy and Independent Verification

## Objective

Release the exact reviewed `$RELEASE_SHA` of `$TARGET` to the MPIPS internal-beta production environment through the repository-authorized deployment workflow, then run the repository-authorized functional verification workflow against the **same SHA** and report whether the deployment is accepted.

This task implements the **separate release gate** from `MS-WORKFLOW-001 v1.2`. An accepted implementation is not automatically authorized for production. This task requires explicit release authority before any production side effect.

## Runtime requirements

- Required capabilities:
  - `repository-read`
  - `shell`
  - `github-actions-read`
  - `github-actions-dispatch`
  - `production-runtime-read`
- Ordered model preferences: None.
- Require preferred model: `false`

## Runtime inputs

- `TARGET` (required): Local path or repository identifier for `Madeena-software/mpips`.
- `RELEASE_SHA` (required): Exact reviewed commit approved for release. Expected reviewed baseline for this task: `6949578c0d9a154e467c91fdaedb955c362c1046`.
- `PRODUCTION_RELEASE_AUTHORIZATION` (required): Human-provided approval string that must equal `AUTHORIZE_PRODUCTION_DEPLOY_AND_VERIFY=<RELEASE_SHA>` exactly.
- `ENV_FILE` (required unless a local `$TARGET/.env` exists): Path to the local untracked environment file containing `MPIPS_API_KEY`. Default: `$TARGET/.env`.
- `MPIPS_API_KEY` (required, secret): The user has already provided the intended key in `.env`. The production task must securely apply that exact value to the GitHub Actions repository secret named `MPIPS_API_KEY` before deployment, because the checked-in production workflows consume `${{ secrets.MPIPS_API_KEY }}` rather than reading the local `.env` directly.

The task must not infer, manufacture, or self-grant `PRODUCTION_RELEASE_AUTHORIZATION`.

## Context and evidence

Before deployment, inspect current repository authority. At minimum inspect:

- `AGENTS.md` and repository-local instructions;
- the exact commit identified by `RELEASE_SHA`;
- `docs/config/mpips-processing-defaults.json`;
- `.github/workflows/deploy-internal-beta.yml`;
- `.github/workflows/verify-internal-beta.yml`;
- production Compose/deployment files referenced by those workflows;
- API/worker health and DICOM verification scripts/tests invoked by the workflows;
- current concurrency, idempotency, calibration, and cleanup verification logic.

Material facts that constrain execution:

- Deployment/readiness and functional acceptance are separate gates. A successful deploy workflow alone is not production acceptance.
- The production deployment is expected to use the self-hosted production runner `simama-production-server` in runner group `madeena-devops`; current checked-in workflow authority must confirm the applicable runner targeting before dispatch.
- The production Docker topology uses the shared external network `madeena-software-network`; current checked-in deployment files are authoritative if that topology has changed.
- The host-local MPIPS API has historically been bound to `127.0.0.1:8014`; verify the checked-in production definition before treating that value as current authority.
- Redis must not gain an unintended host-public port.
- `/v1/radiographs/dicom` uses the canonical MPIPS image-processing configuration. The final parameter study concluded that the current reviewed baseline should be kept unchanged; this release task must not tune it.
- The checked-in deployment and verification workflows consume the GitHub Actions repository secret `MPIPS_API_KEY`; they do not read the operator's local `.env` directly.
- The user has already provided the intended `MPIPS_API_KEY` in the local `.env`, and has explicitly required that this same `.env` value be applied to both local and production deployment. Therefore, after the production release gate is authorized and before workflow dispatch, securely synchronize the `.env` value into the GitHub Actions repository secret named `MPIPS_API_KEY`.
- This synchronization is authorized only as part of this task's production release attempt. Never print, log, hash, compare, or expose the secret value, and never commit `.env`.
- The protected converter `mpips/engine/imager_pipeline/tiff_json_to_dcm.py` must remain untouched.
- Current repository workflows and tests override historical chat/report details where they differ.

## Scope and constraints

### In scope

- reconcile `RELEASE_SHA` against current repository state;
- validate explicit production release authorization;
- inspect production deployment and verification workflow definitions;
- securely load `MPIPS_API_KEY` from the user-provided `.env` without printing it;
- synchronize that exact value to the GitHub Actions repository secret `MPIPS_API_KEY` after release authorization and before deployment dispatch;
- verify the workflow still references the GitHub Actions secret name `MPIPS_API_KEY`;
- confirm production runner/workflow prerequisites where observable;
- dispatch the repository-authorized production deployment workflow for the exact authorized release baseline;
- observe deployment workflow status and evidence;
- independently dispatch the repository-authorized functional verification workflow against the same baseline only after deployment succeeds;
- inspect resulting production runtime health/topology using read-only observations;
- report exact workflow run IDs/URLs, SHAs, results, and release classification.

### Out of scope

- source/config/test/documentation changes;
- commits, pushes, tags, branches, PRs, or releases unrelated to the checked-in deployment workflow;
- changing image-processing parameters;
- editing the canonical config;
- changing GitHub secret values other than the explicitly authorized synchronization of `MPIPS_API_KEY` from the user-provided `.env` for this release attempt;
- printing or retrieving secret values;
- changing calibration artifacts;
- changing runner configuration;
- changing firewall/host networking outside the checked-in deployment path;
- automatic rollback;
- automatic source remediation;
- rewriting git history;
- editing `mpips/engine/imager_pipeline/tiff_json_to_dcm.py`;
- deleting Docker resources not owned by the checked-in deployment process.

### Behavior that must remain unchanged

- canonical image-processing defaults at the authorized SHA;
- DICOM contract;
- authentication contract;
- idempotency semantics;
- fail-fast concurrency semantics;
- upload-limit semantics;
- calibration validation/selection behavior;
- production network exposure model unless the authorized commit itself intentionally changes it.

## Execution policy

- Mode: `agentic-loop`
- Maximum iterations: `3`
- Approval gates:
  - **Production release gate:** Before any workflow dispatch or production mutation, require `PRODUCTION_RELEASE_AUTHORIZATION == AUTHORIZE_PRODUCTION_DEPLOY_AND_VERIFY=<RELEASE_SHA>` exactly. If absent or mismatched, stop with `awaiting-approval`.
  - **Rollback gate:** Any rollback, redeploy to another SHA, secret change other than the explicitly authorized pre-deploy `MPIPS_API_KEY` synchronization from `.env`, runner change, or manual production repair requires a separate explicit human authorization not granted by this task.
  - **Retry gate:** Do not automatically re-dispatch a failed production deploy/verify workflow. A retry after a failed production workflow requires explicit operator approval after the failure evidence is reported.

The maximum iteration count bounds investigation/observation. It does not grant permission for three production deployments.

## Execution procedure

1. **Resolve required inputs and capabilities.**
   - Resolve `TARGET`, `RELEASE_SHA`, `PRODUCTION_RELEASE_AUTHORIZATION`, and `ENV_FILE`.
   - Resolve `ENV_FILE` to `$TARGET/.env` when no explicit path is supplied.
   - Require `ENV_FILE` to contain a non-empty `MPIPS_API_KEY` entry.
   - Read only the required key with a secret-safe parser; do not `cat` the full `.env`, dump it, commit it, or enable shell tracing around secret handling.
   - If production Actions dispatch or GitHub Actions secret-update capability is unavailable, stop with `blocked` before any production side effect.

2. **Validate the explicit release gate before production side effects.**
   - Compute the required exact approval string:
     - `AUTHORIZE_PRODUCTION_DEPLOY_AND_VERIFY=<RELEASE_SHA>`
   - Compare it with the human-supplied `PRODUCTION_RELEASE_AUTHORIZATION`.
   - If it does not match exactly, stop with `awaiting-approval`.
   - Do not interpret conversational intent, task existence, or prior approval of implementation as release authorization.

3. **Reconcile the exact release baseline.**
   - Fetch repository state and inspect at minimum:
     - `git status --short`
     - `git branch --show-current`
     - `git rev-parse HEAD`
     - `git fetch origin`
     - `git rev-parse origin/main`
     - `git show --no-patch --oneline "$RELEASE_SHA"`
   - Require `RELEASE_SHA` to exist in fetched repository history.
   - For the normal `main` release path, require `origin/main == RELEASE_SHA` immediately before dispatch unless the checked-in workflow explicitly supports a safe immutable SHA/ref input.
   - If `origin/main` moved, stop with `blocked`; do not deploy a different commit and do not force-reset main.
   - A dirty local worktree must not be used as release evidence; production deploy must come from GitHub/repository state, not uncommitted local files.

4. **Inspect the exact deployment and verification workflow authority.**
   - Read `.github/workflows/deploy-internal-beta.yml` and `.github/workflows/verify-internal-beta.yml` at `RELEASE_SHA`.
   - Confirm their triggers, ref/input semantics, runner targeting, concurrency policy, secrets, environment, compose files, readiness checks, and functional verification commands.
   - Preserve any checked-in `cancel-in-progress: false` behavior. Do not change workflow concurrency policy.
   - If either workflow is missing, disabled, materially changed from the expected release architecture, or cannot be safely targeted to `RELEASE_SHA`, stop with `blocked` and report the discrepancy.

5. **Synchronize the user-provided `.env` API key and verify prerequisites.**
   - This step occurs only after the explicit production release gate in step 2 has passed.
   - Load the exact `MPIPS_API_KEY` value from `ENV_FILE` into process memory/environment without printing it.
   - Confirm the checked-in workflows reference the GitHub Actions repository secret name `MPIPS_API_KEY`.
   - Securely set/update the repository secret `MPIPS_API_KEY` from the loaded `.env` value using a secret-safe mechanism (for example, stdin to the repository's supported GitHub CLI/API secret-set operation), with shell tracing disabled.
   - Do not retrieve the existing GitHub secret value and do not compare old and new secret contents. Success is established only from the secret-update operation result plus the workflow's continued reference to the expected secret name.
   - Do not print, echo, hash, serialize, or place the key in command arguments that may be logged. Do not commit `.env`.
   - Confirm the expected self-hosted runner targeting from the workflow and, where observable, that the applicable runner is available.
   - Confirm any required external Docker network/calibration prerequisites are represented by current deployment evidence.
   - If the `.env` key cannot be securely applied, the workflow no longer references `MPIPS_API_KEY`, or another prerequisite is absent, stop with `blocked` before deployment dispatch.

6. **Dispatch production deployment exactly once.**
   - Dispatch `.github/workflows/deploy-internal-beta.yml` using the repository-supported trigger/ref/input at the authorized `RELEASE_SHA`.
   - Record workflow run ID and URL immediately.
   - Confirm the resulting run `head_sha`/resolved commit equals `RELEASE_SHA` before treating it as the authorized run.
   - If the run resolved to another SHA, classify as failed/blocked and do not continue to verification.

7. **Observe deployment workflow to terminal state.**
   - Read job/step status and logs necessary to determine success or failure.
   - Sanitize all reported evidence. Never reproduce secrets, authorization headers, production PII, or secret-containing environment dumps.
   - A successful deploy workflow proves deployment/readiness only.
   - If deployment fails or is cancelled, stop. Do not dispatch functional verification as if production were deployed successfully, do not retry automatically, and do not repair production outside this task.

8. **Perform read-only production topology/readiness inspection after successful deploy.**
   - Using workflow/runtime evidence, confirm the deployed commit is `RELEASE_SHA`.
   - Confirm expected MPIPS containers/services are healthy.
   - Confirm the checked-in shared network contract, expected API bind, and Redis exposure model.
   - Flag unexpected public port exposure, missing network membership, unhealthy containers, or mismatched image/commit as release blockers.
   - Do not change host networking or container state manually unless the checked-in workflow itself does so.

9. **Dispatch independent functional verification exactly once.**
   - Only after the deploy workflow succeeded and topology/readiness evidence is acceptable, dispatch `.github/workflows/verify-internal-beta.yml` using the repository-supported trigger/ref/input for the same `RELEASE_SHA`.
   - Record verification run ID and URL.
   - Confirm the verification run resolves to `RELEASE_SHA`.
   - If it resolves to another SHA, stop and classify the release as deployed but not accepted.

10. **Evaluate the verification workflow as the functional acceptance authority.**
    - Use the current checked-in verification workflow/tests as authority for exact assertions.
    - At minimum ensure the workflow exercises the current equivalents of:
      - health/readiness `200`;
      - expected absent/docs route behavior where intentionally private;
      - invalid authentication `401` with the repository-defined error contract;
      - a valid `/v1/radiographs/dicom` conversion returning a validated DICOM;
      - DICOM pixel/transfer-syntax/private-tag constraints encoded by current tests;
      - malformed manifest/radiograph validation behavior;
      - idempotency repeat/conflict behavior;
      - configured fail-fast concurrency behavior and `429` overload handling;
      - post-load health;
      - worker/launcher failure-control checks where applicable;
      - workspace cleanup/leak checks;
      - current synthetic burn-in/functional fixture checks.
    - Do not hardcode historical expected dimensions/status text if the current checked-in workflow intentionally changed them; report the current contract that actually ran.

11. **Handle verification failure safely.**
    - If deployment succeeded but verification failed, classify production as **deployed but not accepted**.
    - Stop after collecting bounded failure evidence.
    - Do not auto-rollback, auto-redeploy, modify source, perform any additional secret change, or dispatch additional runs.
    - State the exact failing job/step and the next approval/action required.

12. **Final release integrity check.**
    - Reconfirm:
      - deploy run SHA == `RELEASE_SHA`;
      - verify run SHA == `RELEASE_SHA` when verification ran;
      - repository baseline was not modified by this task;
      - protected converter was not edited;
      - the production workflow used the GitHub Actions secret `MPIPS_API_KEY` that was synchronized from the user-provided `.env` for this authorized attempt, without exposing the value;
      - no secret value was exposed;
      - no unapproved rollback/retry occurred.

## Acceptance criteria

- [ ] Explicit `AUTHORIZE_PRODUCTION_DEPLOY_AND_VERIFY=<RELEASE_SHA>` authorization was present before production side effects.
- [ ] `RELEASE_SHA` was reconciled against current repository state and was the exact commit targeted by deployment.
- [ ] Current checked-in deployment and verification workflows were inspected before dispatch.
- [ ] `MPIPS_API_KEY` was securely loaded from the user-provided `.env` after release authorization and synchronized to the GitHub Actions repository secret `MPIPS_API_KEY` without being printed, logged, committed, hashed, or retrieved back.
- [ ] The checked-in deployment and verification workflows consumed the repository secret name `MPIPS_API_KEY`.
- [ ] Deployment workflow ran exactly once for the authorized attempt and completed successfully at `RELEASE_SHA`.
- [ ] Production readiness/topology matched the current checked-in release contract with no unexpected public exposure.
- [ ] Verification workflow ran exactly once after successful deployment and completed successfully at the same `RELEASE_SHA`.
- [ ] Functional verification covered the current health/auth/DICOM/validation/idempotency/concurrency/cleanup acceptance contract.
- [ ] No source/config/default/calibration/runner change occurred outside the authorized deployment workflow, and the only permitted pre-dispatch secret change was synchronization of `MPIPS_API_KEY` from the user-provided `.env`.
- [ ] No automatic retry, rollback, or alternate-SHA deployment occurred.
- [ ] Protected converter remained untouched.

## Verification

- Method: Reconcile the immutable release SHA, validate explicit human release authority, inspect current workflow definitions, securely synchronize the user-provided `.env` `MPIPS_API_KEY` into the GitHub Actions repository secret of the same name, dispatch the checked-in deployment workflow once, verify terminal deployment/readiness evidence, dispatch the separate functional verification workflow once at the same SHA, inspect current acceptance evidence, and confirm runtime topology plus release integrity.
- Expected result: The exact authorized MPIPS release SHA is deployed through the repository-defined production path using the `MPIPS_API_KEY` supplied by the user in `.env`, and independently passes the repository-defined functional verification workflow at that same SHA, without secret disclosure or unapproved remediation/rollback.

## Output

- Allowed outcomes: `succeeded`, `failed`, `blocked`, `awaiting-approval`, or `exhausted`.
- Also report a `Production Release Classification` with exactly one value:
  - `PROD_DEPLOY_SUCCEEDED_AND_VERIFIED`
  - `PROD_DEPLOY_SUCCEEDED_VERIFY_FAILED`
  - `PROD_DEPLOY_FAILED`
  - `PROD_DEPLOY_BLOCKED_NO_AUTHORITY`
  - `PROD_DEPLOY_BLOCKED_PREREQUISITE`
- Report:
  - selected runtime/model when verifiable;
  - capabilities used;
  - release authorization gate result without reproducing secret material;
  - confirmation that production `MPIPS_API_KEY` was synchronized from the user-provided `.env` into the GitHub Actions secret of the same name, without reproducing its value;
  - `RELEASE_SHA` and reconciled `origin/main` SHA;
  - deployment workflow path/name;
  - deployment run ID, URL, resolved SHA, job/step result;
  - post-deploy runtime/topology/readiness evidence;
  - verification workflow path/name;
  - verification run ID, URL, resolved SHA, job/step result;
  - functional acceptance summary;
  - sanitized warnings/failures;
  - whether production is deployed and whether it is accepted;
  - residual risks and the exact next approval/manual action, if any.
- A successful deployment workflow without successful independent verification must not be reported as accepted production.
- Treat workflow output at the wrong SHA, missing release authority, missing prerequisite, unverified runtime state, or model output alone as unsuccessful.
