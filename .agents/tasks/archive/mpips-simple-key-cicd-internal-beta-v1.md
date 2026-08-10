---
name: mpips-simple-key-cicd-internal-beta
description: Implement one fixed API key and deploy standalone MPIPS through a minimal agentic GitHub Actions workflow.
version: 1
---

<!-- antigravity-code-agent-template:managed -->
# Task: MVP API key and CI/CD deployment

## Objective

For `$TARGET`, ship the MPIPS internal beta with the smallest practical
authentication and deployment path.

Use this fixed API key:

```text
mpips_access_api_m4d33n4
```

Required API contract:

```text
GET /health
- No key required.

POST /v1/radiographs/dicom
- Require header: X-MPIPS-API-Key
- Exact accepted value: mpips_access_api_m4d33n4
- Missing or incorrect key: 401 {"detail":"INVALID_API_KEY"}
```

The active DICOM route must no longer require JWT, JWKS, issuer, audience,
scopes, tenant claims, manifest timestamps, or manifest HMAC signatures.

Deploy MPIPS only at:

```text
http://127.0.0.1:8015
```

Docker mapping:

```text
127.0.0.1:8015:8000
```

Use GitHub Actions on the approved self-hosted runner. Use `gh` to push,
dispatch, watch, inspect failed logs, fix repository-owned failures, and retry.

Do not use SSH.

## Runtime requirements

- Required capabilities:
  - `repository-read`
  - `repository-write`
  - `shell`
  - `docker`
  - `network`
  - `github-cli`
- Ordered model preferences: None.
- Require preferred model: `false`

## Runtime inputs

- `TARGET` (required): MPIPS repository root.
- `DEPLOY_TEMPLATES` (required): local checkout of `Madeena-software/deploy-templates`.

## Context and evidence

Inspect:

- `AGENTS.md`;
- `.agents/AGENTS.md`;
- `.agents/context/project.md`;
- `.agents/skills/agent-task/SKILL.md`;
- the current branch, `HEAD`, remotes, and working tree;
- commit `2f267aed2fd970530bb11d592f0f346feeaf2ace`;
- active API authentication and DICOM route code;
- focused API and conversion tests;
- `scripts/local_dicom_burn_in.py`;
- Dockerfiles and Compose files;
- `docker/host-launcher/`;
- current GitHub Actions workflows;
- applicable simple patterns under `$DEPLOY_TEMPLATES/templates/prod/`.

Use the deployment templates only for:

- `workflow_dispatch`;
- self-hosted runner execution;
- one deployment concurrency group;
- local Docker builds;
- deployment health checks;
- failure logs;
- rollback.

Do not copy Laravel, database, S3, Nginx, domain, mail, frontend, or SSH
requirements.

The converter must remain unchanged.

Required converter SHA-256:

```text
a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0
```

## Scope and constraints

In scope:

- replace active JWT/JWKS authentication with the fixed API-key header;
- remove timestamp and HMAC checks from the active DICOM route;
- use `internal-beta` as the fixed idempotency tenant namespace;
- update startup validation;
- update focused tests and burn-in;
- remove JWKS service and related settings from local deployment;
- create a simple production Compose file;
- create `.github/workflows/deploy-internal-beta.yml`;
- commit and push;
- dispatch and observe the workflow with `gh`;
- fix evidence-backed failures and retry;
- update `.agents/context/project.md`.

The production Compose file must:

- bind only `127.0.0.1:8015:8000`;
- keep Redis private with no published port;
- contain no Nginx or public ingress;
- use commit-SHA image tags, not `latest`;
- mount calibration read-only;
- retain the existing isolated-worker controls.

The GitHub Actions workflow must:

- use `workflow_dispatch`;
- run on `self-hosted`;
- contain no SSH;
- build the API and worker images;
- run focused tests;
- deploy with Docker Compose;
- verify health;
- verify missing and wrong keys return `401`;
- run one valid synthetic DICOM conversion with the fixed key;
- verify Redis has no published port;
- verify the API listens only on loopback;
- show useful failed logs;
- restore the previous Compose deployment when mandatory live verification
  fails.

Out of scope:

- MHCS deployment;
- public exposure;
- identity-provider integration;
- secret rotation;
- safe-NPZ migration;
- converter changes;
- DICOM semantic changes;
- calibration algorithm changes;
- unrelated cleanup.

Do not modify:

```text
mpips/engine/imager_pipeline/tiff_json_to_dcm.py
```

Repository-state rule:

- The initial working tree may contain exactly this untracked task file:

  ```text
  ?? .agents/tasks/mpips-simple-key-cicd-internal-beta-v1.md
  ```

- That expected untracked task file is not a blocker.
- Commit the task file unchanged with the implementation.
- Stop only when any other pre-existing modification or untracked file exists.
- Do not reset, clean, stash, amend, rebase, or force-push.
- Do not use `git add -A`.
- Stage task-owned files explicitly.

## Execution policy

- Mode: `agentic-loop`
- Maximum iterations: `4`
- Approval gates:
  - any SSH requirement;
  - any public exposure;
  - any converter, DICOM semantic, or calibration algorithm change;
  - any force-push;
  - any unrelated destructive operation.

One iteration is:

```text
inspect -> implement or fix -> test -> commit -> push
-> dispatch -> watch -> inspect failed logs
```

## Execution procedure

1. Resolve the repository:

   ```bash
   cd "$TARGET"
   TARGET="$(pwd)"

   git rev-parse --show-toplevel
   git rev-parse HEAD
   git branch --show-current
   git remote -v
   git status --short
   ```

2. Permit the initial status only when it is empty or contains exactly:

   ```text
   ?? .agents/tasks/mpips-simple-key-cicd-internal-beta-v1.md
   ```

   Stop with `blocked` for any other initial change.

3. Confirm commit
   `2f267aed2fd970530bb11d592f0f346feeaf2ace`
   is an ancestor of current `HEAD`.

4. Read the repository instructions and task skill.

5. Validate this task:

   ```bash
   .venv/bin/python .agents/skills/agent-task/scripts/validate_task.py \
     .agents/tasks/mpips-simple-key-cicd-internal-beta-v1.md
   ```

6. Resolve `$DEPLOY_TEMPLATES`, confirm it is clean, and inspect only the
   applicable production workflow patterns.

7. Verify GitHub CLI access:

   ```bash
   gh auth status
   gh repo view Madeena-software/mpips \
     --json nameWithOwner,defaultBranchRef,url
   ```

8. Confirm the current branch is `main`.

9. Fetch `origin/main` and require a fast-forward push path.

10. Verify the converter hash.

11. Implement one small API-key dependency:

    ```text
    Header: X-MPIPS-API-Key
    Value:  mpips_access_api_m4d33n4
    Error:  401 INVALID_API_KEY
    ```

12. Apply it only to `POST /v1/radiographs/dicom`.

13. Keep `GET /health` unauthenticated.

14. Remove JWT/JWKS/scope/tenant/timestamp/HMAC dependencies from the active
    DICOM request path.

15. Use `internal-beta` for idempotency.

16. Old authentication modules may remain in the repository if deleting them
    would broaden scope, but the active DICOM route must not call them.

17. Update focused tests for:

    - health without key;
    - valid key;
    - missing key;
    - wrong key;
    - bearer token without API key;
    - absent generic routes;
    - absent production docs;
    - valid DICOM conversion.

18. Simplify the local burn-in:

    - remove RSA, JWT, JWKS, timestamp, and HMAC setup;
    - use the fixed key;
    - keep the valid DICOM, malformed input, idempotency, launcher, cleanup,
      restart, and bounded concurrency checks.

19. Simplify local and production Compose:

    - remove JWKS;
    - remove JWT/JWKS/HMAC settings;
    - keep Redis private;
    - production bind exactly `127.0.0.1:8015:8000`;
    - no Nginx;
    - no public ingress;
    - no `latest`.

20. Create a minimal
    `.github/workflows/deploy-internal-beta.yml`.

    A single job is acceptable. Keep it understandable.

21. Run mandatory local checks:

    ```bash
    uv run pytest \
      tests/api/test_api_surface.py \
      tests/api/test_dicom_authentication.py \
      tests/api/test_dicom_conversion.py \
      tests/test_host_launcher.py \
      -q

    uv run pytest -q
    ```

    Focused failures block deployment.

    An unrelated full-suite failure may be reported without blocking only when
    it existed before this task and none of the task-owned or active DICOM files
    are involved.

22. Validate YAML and render the production Compose configuration.

23. Verify:

    - exact loopback port mapping;
    - no Redis port;
    - no JWKS;
    - no Nginx;
    - no SSH;
    - no `latest`.

24. Build the API and worker images and run the updated local burn-in.

25. Verify the converter hash again.

26. Inspect the diff:

    ```bash
    git diff --check
    git status --short
    git diff --stat
    git diff --name-only
    ```

27. Stage only the task file and task-owned implementation files explicitly.

28. Create a commit:

    ```text
    refactor: simplify MPIPS beta authentication
    ```

29. Fetch `origin/main` again. Stop if a fast-forward push is no longer safe.

30. Push without force:

    ```bash
    git push origin HEAD:main
    ```

31. Dispatch:

    ```bash
    gh workflow run deploy-internal-beta.yml \
      --repo Madeena-software/mpips \
      --ref main
    ```

32. Resolve the run ID for the pushed commit and store it in `RUN_ID`.

33. Watch:

    ```bash
    gh run watch "$$RUN_ID" \
      --repo Madeena-software/mpips \
      --exit-status
    ```

34. Inspect:

    ```bash
    gh run view "$$RUN_ID" \
      --repo Madeena-software/mpips \
      --json databaseId,headSha,status,conclusion,url,jobs
    ```

35. On failure:

    ```bash
    gh run view "$$RUN_ID" \
      --repo Madeena-software/mpips \
      --log-failed
    ```

36. Make only the smallest evidence-backed fix, rerun local focused checks,
    commit, fetch, push, and dispatch a fresh run.

37. Retry for at most four complete iterations.

38. Success requires:

    - final run `headSha` equals final pushed `HEAD`;
    - final conclusion is `success`;
    - `/health` returns `200`;
    - valid API key succeeds;
    - missing and wrong keys return `401`;
    - synthetic DICOM conversion succeeds;
    - API is loopback-only;
    - Redis is private;
    - no SSH was used.

39. Record final Git and workflow state and stop.

## Acceptance criteria

- [ ] The task validator passed.
- [ ] The expected untracked task file did not block execution.
- [ ] No other initial working-tree change existed.
- [ ] Converter hash matched before and after.
- [ ] The DICOM route uses only `X-MPIPS-API-Key`.
- [ ] The accepted value is `mpips_access_api_m4d33n4`.
- [ ] Missing and wrong keys return `401 INVALID_API_KEY`.
- [ ] `/health` requires no key.
- [ ] Active JWT/JWKS/scope/tenant/timestamp/HMAC checks were removed.
- [ ] Idempotency uses `internal-beta`.
- [ ] Local burn-in uses the fixed key.
- [ ] Production bind is exactly `127.0.0.1:8015:8000`.
- [ ] Redis has no published port.
- [ ] No JWKS, Nginx, public ingress, SSH, or `latest` deployment image remains.
- [ ] Focused tests passed.
- [ ] Local burn-in passed.
- [ ] The task file and implementation were committed.
- [ ] Commits were pushed without force.
- [ ] Workflow was dispatched and observed with `gh`.
- [ ] Final workflow run succeeded on final `HEAD`.
- [ ] Final working tree is clean.
- [ ] No public exposure or SSH occurred.
- [ ] Final outcome uses one allowed value.

## Verification

- Method:

  ```bash
  cd "$TARGET"

  .venv/bin/python .agents/skills/agent-task/scripts/validate_task.py \
    .agents/tasks/mpips-simple-key-cicd-internal-beta-v1.md

  sha256sum mpips/engine/imager_pipeline/tiff_json_to_dcm.py

  uv run pytest \
    tests/api/test_api_surface.py \
    tests/api/test_dicom_authentication.py \
    tests/api/test_dicom_conversion.py \
    tests/test_host_launcher.py \
    -q

  gh run view "$$RUN_ID" \
    --repo Madeena-software/mpips \
    --json databaseId,headSha,status,conclusion,url,jobs

  git rev-parse HEAD
  git status --short
  ```

- Expected result:
  - one fixed key protects the DICOM endpoint;
  - MPIPS is deployed at `127.0.0.1:8015`;
  - the GitHub Actions run succeeds;
  - no SSH or identity-provider setup is required.

## Output

- Allowed outcomes: `succeeded`, `failed`, `blocked`,
  `awaiting-approval`, `exhausted`.
- Report:
  - starting and final commit SHAs;
  - exact changed files;
  - focused test and burn-in results;
  - pushed commits;
  - each workflow run ID, SHA, URL, and conclusion;
  - any remediation;
  - final endpoint;
  - valid, missing, and wrong key results;
  - DICOM smoke-test result;
  - Redis and loopback checks;
  - converter hashes;
  - final `git status --short`;
  - confirmation that no SSH or public exposure occurred.

Treat as unsuccessful:

- validator failure;
- active JWT/JWKS/HMAC dependency remains;
- missing or wrong key is accepted;
- public exposure;
- published Redis;
- mutable deployment image;
- failed live DICOM conversion;
- modified converter;
- dirty final tree;
- exhausted iterations without a successful final workflow run.
