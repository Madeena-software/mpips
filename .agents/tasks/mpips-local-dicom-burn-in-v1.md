---
name: mpips-local-dicom-burn-in-v1
description: Deploy the accepted MPIPS DICOM-only API locally in a production-like Docker environment and iteratively test, diagnose, and remediate the active API path until all scoped local safety gates pass.
version: 1
---

<!-- antigravity-code-agent-template:managed -->
# Task: Local production-like deployment and exhaustive DICOM API burn-in

## Objective

For `$TARGET`, create and run a local, production-like MPIPS deployment that is
reachable only from the local machine, then exercise the complete active
MHCS-to-MPIPS DICOM path through an agentic test-and-remediation loop.

The active product surface is:

```text
POST /v1/radiographs/dicom
GET  /health
```

The local deployment must bind only to:

```text
127.0.0.1:${MPIPS_LOCAL_PORT}
```

The task must repeatedly inspect, test, diagnose, and correct defects within the
approved scope until every scoped acceptance criterion passes or the iteration
limit is exhausted.

This task does not claim absolute security. Its observable outcome is:

```text
A locally running, production-like MPIPS DICOM service with no known critical
or high-severity defect in the tested API, authentication, manifest integrity,
idempotency, NPZ handling, calibration, isolated-worker, DICOM validation,
cleanup, resource-limit, and local-network exposure boundaries.
```

The task may create one local implementation commit after all scoped gates pass.

It must not push, deploy to a remote server, dispatch GitHub Actions, expose a
public interface, or begin the production deployment task.

## Runtime requirements

- Required capabilities:
  - `repository-read`
  - `repository-write`
  - `shell`
  - `docker`
- Ordered model preferences: None.
- Require preferred model: `false`

When preferences are present, use a numbered list of unique opaque
provider/model identifiers. With `false`, preferences are advisory and the
executing runtime may continue with another capable model while reporting the
selection. With `true`, execution must stop before meaningful output or side
effects unless a listed model is selected and verified.

## Runtime inputs

- `TARGET` (required): MPIPS repository root.
- `MPIPS_LOCAL_PORT` (optional): loopback port for the local API; default `8000`.

## Context and evidence

The executing agent must inspect:

- the repository-root `AGENTS.md`;
- `.agents/AGENTS.md`;
- `.agents/context/project.md`;
- `.agents/skills/agent-task/SKILL.md`;
- current `HEAD`, branch, remotes, and working-tree status;
- accepted Task 00 commits:
  - `3a17baca8bcd63a90ebe3297de5c72bda2ef7f17`;
  - `279b84d77ef179865e42739d358a10b4d7bc8b81`;
- `Dockerfile`;
- `.dockerignore`;
- `docker-compose.prod.yml`;
- `docker/entrypoint.sh`;
- `docker/host-launcher/`;
- `mpips/api/`;
- `mpips/conversion/`;
- `mpips/workflows/imager_pipeline/`;
- current API, authentication, conversion, calibration, idempotency, and
  launcher tests;
- the current registered FastAPI route table;
- the current SHA-256 of
  `mpips/engine/imager_pipeline/tiff_json_to_dcm.py`;
- current local Docker state relevant to MPIPS;
- current local port use for `$MPIPS_LOCAL_PORT`.

The accepted converter must remain byte-for-byte unchanged.

Required converter SHA-256:

```text
a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0
```

Repository context and tests are evidence, not proof that local deployment is
safe. Verify behavior from actual source, rendered configuration, running
containers, HTTP responses, generated DICOM files, logs, process state,
filesystem state, and Docker inspection output.

## Scope and constraints

### In scope

- create or update `docker-compose.local.yml`;
- create a local-only environment example such as `.env.local.example`;
- create local test fixtures or scripts under an appropriate `scripts/` or
  `tests/` path;
- create a deterministic local calibration fixture for testing only;
- create a local-only Redis service;
- create a local production-like API service;
- create or adapt a local host-launcher service or container only when required
  to exercise the production isolated-worker path;
- correct `tests/test_host_launcher.py` when required to match the actual
  newline-delimited socket protocol and formatting rules;
- add focused tests for local deployment behavior;
- make narrowly scoped fixes to the active API, authentication, manifest
  security, idempotency, conversion orchestration, worker isolation, cleanup,
  or local deployment configuration when a reproducible defect is found;
- update `.agents/context/project.md` with exact local verification evidence;
- create one local implementation commit after all scoped gates pass.

### Local topology

The local deployment must use:

```text
Host/MHCS test client
    |
    | http://127.0.0.1:${MPIPS_LOCAL_PORT}
    v
MPIPS API container
    |
    +-- private Redis container
    +-- private workspace
    +-- validated test calibration artifact
    +-- isolated NPZ worker path
```

The local deployment must:

- publish only the API;
- bind the API only to `127.0.0.1`;
- publish no Redis port;
- have no Nginx service;
- have no public hostname;
- use a dedicated Docker network;
- use deterministic local image tags;
- use non-root containers where supported;
- mount only task-required paths;
- use temporary or dedicated local test data;
- remove only task-created runtime resources during cleanup.

### Required local test identities and secrets

Use generated, non-production values only.

The task may generate temporary local values for:

```text
DEV_BEARER_TOKEN
MPIPS_MANIFEST_HMAC_SECRET
MPIPS_REDIS_PASSWORD
```

The task must never read, copy, print, or reuse real production secrets.

Generated values must:

- remain outside tracked files;
- not be printed in the final report;
- not be committed;
- be removed during cleanup unless retained in a user-owned ignored local file
  that the task explicitly reports.

### Prohibited behavior

Do not:

- expose MPIPS on `0.0.0.0`;
- publish Redis;
- add Nginx, Traefik, or public ingress;
- create a public hostname;
- use real patient data;
- use real production credentials;
- contact live MHCS, Redis, JWKS, S3, or other production services;
- push commits;
- dispatch workflows;
- deploy to a remote server;
- modify production Docker Swarm or systemd state;
- install dependencies;
- delete generic DAG code;
- weaken authentication, HMAC, tenant, idempotency, calibration, worker
  isolation, or DICOM validation controls;
- change the approved converter;
- modify unrelated legacy code merely to make an unrelated full-suite check
  green.

### Protected files

Do not modify:

```text
mpips/engine/imager_pipeline/tiff_json_to_dcm.py
```

Do not modify DICOM tag mappings, pixel encoding, UID behavior, calibration
algorithms, or image-processing semantics unless a directly reproducible defect
in the active local DICOM flow requires it.

If such a change becomes necessary, stop with outcome `awaiting-approval` and
report the evidence. Do not proceed without explicit approval.

### Repository-state boundary

- Stop if the initial working tree is dirty.
- Confirm the accepted Task 00 commit is an ancestor of current `HEAD`.
- Preserve all pre-existing user files and Docker resources.
- Do not reset, clean, stash, amend, rebase, or discard changes.
- Do not use `git add -A`.
- Stage only task-owned files.
- Remove only containers, networks, images, volumes, and temporary files created
  by this task.

## Execution policy

- Mode: `agentic-loop`
- Maximum iterations: `8`
- Approval gates:
  - any change to the approved converter;
  - any DICOM semantic or clinical metadata change;
  - any calibration algorithm change;
  - any public exposure;
  - any real production secret or infrastructure access;
  - any dependency installation or upgrade;
  - any destructive Docker operation affecting non-task resources;
  - any change outside the stated scope;
  - any remote deployment, push, or workflow dispatch.

Each iteration must follow:

```text
inspect -> hypothesize -> reproduce -> make the smallest scoped change
-> run focused checks -> observe -> classify residual risk
```

Do not make speculative changes without a reproducible failure or a directly
observable configuration defect.

Retry only from repository, runtime, test, or human feedback.

Stop when:

- all acceptance criteria pass;
- approval is required;
- progress is blocked;
- execution fails irrecoverably; or
- eight iterations are exhausted.

## Execution procedure

### Phase 1: Preconditions and baseline

1. Resolve `$TARGET` and `$MPIPS_LOCAL_PORT`:

   ```bash
   cd "$TARGET"
   TARGET="$(pwd)"
   MPIPS_LOCAL_PORT="${MPIPS_LOCAL_PORT:-8000}"

   printf 'target=%s\n' "$TARGET"
   printf 'local_port=%s\n' "$MPIPS_LOCAL_PORT"

   git rev-parse --show-toplevel
   git rev-parse HEAD
   git status --short
   ```

2. Stop with outcome `blocked` if the working tree is not clean.

3. Confirm accepted Task 00 ancestry:

   ```bash
   git merge-base --is-ancestor \
     279b84d77ef179865e42739d358a10b4d7bc8b81 \
     HEAD
   ```

4. Read all applicable instructions and the task-execution skill.

5. Verify required tools without installing anything:

   ```bash
   docker version
   docker compose version
   ```

6. Confirm the local port is available. Do not stop or kill an unrelated
   process. Stop with outcome `blocked` if the selected port is owned by a
   non-task process.

7. Record current task-relevant Docker resources so cleanup can distinguish
   pre-existing resources from task-created resources.

8. Record the converter hash:

   ```bash
   sha256sum mpips/engine/imager_pipeline/tiff_json_to_dcm.py
   ```

   Stop with outcome `blocked` if it differs from the required hash.

9. Inspect the current route table and record development and production routes.

10. Establish a verification baseline before modifications:

    ```bash
    uv run pytest tests/api/test_api_surface.py -v
    uv run pytest tests/api/test_dicom_authentication.py -v
    uv run pytest tests/api/test_dicom_conversion.py -v
    uv run pytest tests/test_host_launcher.py -v
    ```

    When `uv` is unavailable on `PATH` but the existing virtual environment
    exposes the uv module, use the established equivalent and report it exactly.

11. Run the full suite once as informational baseline:

    ```bash
    uv run pytest -v
    ```

    Record unrelated pre-existing failures separately.

    An unrelated baseline failure does not authorize unrelated remediation and
    does not by itself block this task. Every test covering the active DICOM
    path, authentication, manifest security, idempotency, calibration,
    conversion, launcher, and local deployment must pass.

### Phase 2: Build the local production-like environment

12. Inspect current deployment and launcher implementation.

13. Create or update `docker-compose.local.yml` with:

    - API bound to `127.0.0.1:${MPIPS_LOCAL_PORT}:8000`;
    - private Redis with authentication;
    - no Redis host port;
    - no Nginx;
    - no public hostname;
    - a dedicated local Docker network;
    - health checks;
    - explicit CPU and memory limits where supported;
    - production-like environment settings;
    - generated local-only secrets supplied from an untracked temporary env
      file;
    - read-only calibration mount;
    - private workspace mount;
    - launcher socket or equivalent local isolated-worker boundary;
    - deterministic local image tags;
    - no `latest` tag in the rendered configuration.

14. Create deterministic synthetic local test fixtures:

    - radiograph NPZ;
    - matching gain NPZ;
    - signed JSON manifest;
    - validated calibration artifact;
    - expected DICOM assertions.

    Synthetic data must contain no real patient information.

15. Create a reusable local smoke and abuse-test client that:

    - generates a valid bearer identity or uses the approved local bypass;
    - creates a correct manifest signature;
    - submits multipart requests;
    - saves returned DICOM to a temporary task directory;
    - validates response headers;
    - parses the DICOM;
    - verifies expected patient, study, UID, image, and pixel properties;
    - never prints secret values or full sensitive payloads.

16. Render and inspect the local compose configuration:

    ```bash
    docker compose -f docker-compose.local.yml config
    ```

17. Verify from rendered output:

    - API bind address is loopback only;
    - Redis has no published port;
    - no Nginx service exists;
    - no service uses `latest`;
    - no secret value is embedded in tracked configuration;
    - only expected mounts and networks are present.

18. Build local images without pushing.

19. Inspect image metadata and verify:

    - non-root runtime user where expected;
    - API command and entrypoint;
    - worker command and entrypoint;
    - no secret values in image configuration;
    - no production credential or fixture embedded in an image layer.

### Phase 3: Start and verify the local deployment

20. Start only the task-created local stack.

21. Wait for health with a finite timeout.

22. Verify local exposure:

    ```text
    http://127.0.0.1:${MPIPS_LOCAL_PORT}/health -> 200
    ```

23. Verify the API is not bound to a non-loopback host interface using Docker
    inspection and host socket evidence.

24. Verify production route privacy:

    ```text
    GET /                              -> 404
    GET /v1/nodes                      -> 404
    GET /v1/jobs                       -> 404
    GET /v1/secure-test                -> 404
    GET /docs                          -> 404
    GET /redoc                         -> 404
    GET /openapi.json                  -> 404
    ```

25. Verify Redis is reachable only from the private Docker network and is not
    published on the host.

### Phase 4: Exhaustive active-path test matrix

26. Run the valid end-to-end conversion case:

    ```text
    valid bearer identity
    + valid image:convert authorization
    + valid tenant_id
    + valid timestamp
    + valid HMAC
    + valid manifest
    + matching radiograph/gain NPZs
    + valid calibration
    -> HTTP 200 application/dicom
    ```

27. Parse and validate the returned DICOM:

    - readable by pydicom;
    - expected transfer syntax;
    - expected SOP, Study, and Series UIDs;
    - expected patient and study mapping from synthetic manifest;
    - expected Rows and Columns;
    - uint16 pixel representation;
    - non-empty pixel data;
    - expected `BurnedInAnnotation`;
    - expected lossy-compression declaration;
    - no unexpected private or secret values;
    - validation code reports success.

28. Run authentication and authorization failures:

    - no Authorization header;
    - malformed bearer header;
    - wrong development token when bypass is enabled;
    - invalid JWT signature path using local mocks or focused tests;
    - missing `image:convert` scope;
    - missing tenant identifier;
    - malformed tenant identifier;
    - tenant mismatch between token and signed request assumptions.

29. Run manifest-signature failures:

    - missing timestamp;
    - non-numeric timestamp;
    - stale timestamp;
    - future timestamp outside allowed skew;
    - missing signature;
    - malformed signature prefix;
    - wrong signature length;
    - wrong HMAC;
    - valid signature over modified manifest;
    - whitespace or canonicalization edge cases.

30. Run multipart and upload failures:

    - missing radiograph file;
    - missing gain file;
    - missing manifest;
    - wrong content type;
    - empty files;
    - truncated NPZ;
    - malformed JSON;
    - manifest above limit;
    - radiograph above limit;
    - gain above limit;
    - combined body above limit;
    - suspicious filename;
    - duplicate form parts where parser behavior matters.

31. Run NPZ and calibration failures:

    - radiograph missing required keys;
    - gain missing required keys;
    - gain ID mismatch;
    - image-shape mismatch;
    - unsupported dtype;
    - object-array or unsafe-pickle input;
    - detector-mode mismatch;
    - camera-serial mismatch;
    - missing calibration artifact;
    - invalid calibration metadata;
    - remap-shape mismatch;
    - unvalidated calibration artifact;
    - unexpected worker output file;
    - malformed worker result.

32. Run idempotency and replay cases against local Redis:

    - first valid claim;
    - identical completed replay;
    - in-progress duplicate;
    - same job identifier with different manifest fingerprint;
    - expired lease or TTL behavior where supported;
    - Redis unavailable;
    - malformed cached state;
    - no cross-tenant reuse.

33. Run isolated-worker and cleanup cases:

    - successful launcher request;
    - malformed launcher JSON;
    - invalid job ID;
    - path traversal attempt;
    - workspace outside approved root;
    - missing `args.json`;
    - worker non-zero exit;
    - worker timeout;
    - launcher unavailable;
    - malformed launcher response;
    - unexpected worker output;
    - output symlink attempt where supported;
    - task workspace removed after success;
    - task workspace removed after API failure;
    - task workspace removed after timeout;
    - upload staging directory removed after response completion.

34. Run concurrency and resilience cases with bounded local load:

    - sequential successful requests;
    - concurrent requests up to configured limit;
    - one request above configured concurrency limit;
    - repeated invalid requests;
    - health response during conversion;
    - service restart followed by health recovery;
    - Redis restart followed by controlled failure and recovery;
    - no unbounded process, container, file, or memory growth across the bounded
      run.

35. Use finite, conservative test values. Do not run an uncontrolled load test,
    denial-of-service simulation, or infinite loop.

36. Collect sanitized evidence only:

    - status codes;
    - error identifiers;
    - response content type;
    - DICOM validation summary;
    - container health;
    - bounded resource observations;
    - cleanup results;
    - relevant log excerpts without secrets or complete manifests.

### Phase 5: Agentic remediation loop

37. For each failure in the scoped matrix:

    1. reproduce it deterministically;
    2. classify severity and affected boundary;
    3. identify whether it is:
       - task-caused;
       - active-path pre-existing;
       - unrelated legacy;
       - environmental;
    4. make the smallest coherent fix only for active-path or task-caused defects;
    5. add or strengthen a regression test;
    6. rerun the smallest focused test;
    7. rerun the affected matrix group;
    8. rerun the valid end-to-end conversion;
    9. inspect logs, cleanup, and Docker state;
    10. continue until pass, approval gate, blocker, or iteration exhaustion.

38. Do not weaken assertions, bypass security, disable isolation, suppress errors,
    or mark failing tests as skipped merely to obtain a green result.

39. Any discovered critical or high-severity active-path defect must be fixed and
    regression-tested before success can be reported.

40. Any discovered critical or high-severity issue that requires a protected or
    approval-gated change must stop the task with `awaiting-approval`.

### Phase 6: Final verification

41. Rerun all focused suites:

    ```bash
    uv run pytest tests/api/test_api_surface.py -v
    uv run pytest tests/api/test_dicom_authentication.py -v
    uv run pytest tests/api/test_dicom_conversion.py -v
    uv run pytest tests/test_host_launcher.py -v
    ```

42. Run every new local-deployment, smoke, security, idempotency, worker, and
    cleanup test explicitly.

43. Run the complete scoped test matrix once from a clean local stack.

44. Run the full repository test suite again as informational evidence:

    ```bash
    uv run pytest -v
    ```

    Compare failures to the initial baseline. No new unrelated failure may be
    introduced.

45. Run quality checks on task-owned and active-path files:

    ```bash
    uv run black --check <task-owned-and-active-path-python-files>
    uv run flake8 <task-owned-and-active-path-python-files>
    uv run mypy <task-owned-and-active-path-python-files>
    ```

    Also run existing repository-wide quality commands when feasible and report
    any unchanged unrelated baseline failure separately.

46. Validate compose and tracked-file safety again.

47. Verify the converter hash again.

48. Inspect the final diff and scope:

    ```bash
    git diff --check
    git status --short
    git diff --stat
    git diff --name-only
    ```

49. Search tracked changes for accidental credentials, local absolute paths,
    synthetic patient values that should remain fixtures only, and generated
    binary artifacts.

50. Stop the local stack and remove only task-created:

    - containers;
    - networks;
    - anonymous volumes;
    - temporary environment files;
    - generated smoke-test outputs;
    - temporary images when not needed for the final local rerun.

51. Confirm no task-created listener remains on `$MPIPS_LOCAL_PORT`.

52. Confirm no non-task Docker resource was removed or modified.

53. If all acceptance criteria pass, stage only task-owned files explicitly and
    create exactly one local commit with message:

    ```text
    test: validate local MPIPS DICOM deployment
    ```

54. Record:

    ```bash
    git rev-parse HEAD
    git status --short
    git show --stat --oneline --decorate --no-renames HEAD
    ```

55. Stop. Do not push, deploy remotely, dispatch a workflow, or begin production
    deployment.

## Acceptance criteria

### Repository and scope

- [ ] `$TARGET` resolved to the intended MPIPS repository.
- [ ] Required capabilities were available.
- [ ] Applicable repository instructions and task skill were read.
- [ ] Initial working tree was clean.
- [ ] Accepted Task 00 commit was an ancestor of current `HEAD`.
- [ ] No unrelated user or Docker resource was modified.
- [ ] No prohibited converter change occurred.
- [ ] Converter hash matched before and after.

### Local deployment

- [ ] `docker-compose.local.yml` rendered successfully.
- [ ] API bound only to `127.0.0.1:${MPIPS_LOCAL_PORT}`.
- [ ] Redis had no host-published port.
- [ ] No Nginx or public ingress existed.
- [ ] No service used a production `latest` tag.
- [ ] Only generated local secrets were used.
- [ ] No local secret was committed or printed.
- [ ] API and worker images built successfully.
- [ ] Expected non-root and entrypoint properties were verified.
- [ ] Local stack reached healthy state.
- [ ] Task-created local stack was removed cleanly at completion.

### API surface

- [ ] `GET /health` returned 200.
- [ ] `POST /v1/radiographs/dicom` remained the only business endpoint.
- [ ] Root, nodes, jobs, secure-test, docs, ReDoc, and OpenAPI routes were absent
      in production mode.
- [ ] No public or non-loopback listener exposed MPIPS.
- [ ] Redis was private.

### Authentication and manifest integrity

- [ ] Missing or malformed bearer credentials were rejected.
- [ ] Invalid token validation path was covered.
- [ ] Missing `image:convert` was rejected.
- [ ] Missing or malformed tenant identity was rejected.
- [ ] Timestamp and HMAC negative cases were rejected.
- [ ] Modified signed content was rejected.
- [ ] No authentication or manifest-security control was weakened.

### Upload, NPZ, calibration, and conversion

- [ ] Required multipart parts were enforced.
- [ ] File and total upload limits were enforced.
- [ ] Malformed JSON and NPZ files were rejected safely.
- [ ] Unsafe object-array or pickle behavior was rejected.
- [ ] Gain, shape, dtype, detector, and camera mismatches were rejected.
- [ ] Missing or invalid calibration failed closed.
- [ ] Valid synthetic input produced a valid DICOM.
- [ ] Expected DICOM tags, UIDs, dimensions, and uint16 pixel data were verified.
- [ ] Converter remained unchanged.

### Idempotency and dependencies

- [ ] First claim, replay, in-progress, and conflict cases were covered.
- [ ] Cross-tenant reuse was rejected.
- [ ] Redis failure produced a controlled response.
- [ ] Recovery after Redis restart was verified.
- [ ] No secret or internal connection detail leaked in errors.

### Worker isolation and cleanup

- [ ] Valid launcher flow passed.
- [ ] Invalid job, path, workspace, and request cases were rejected.
- [ ] Worker failure, timeout, and unavailable launcher cases were controlled.
- [ ] Worker remained network-disabled and resource-limited in the tested local
      production-like path.
- [ ] Unexpected output and symlink behavior were rejected where supported.
- [ ] Workspaces and staging directories were cleaned after success and failure.
- [ ] No orphan process or task-created container remained.

### Resilience

- [ ] Bounded sequential and concurrent valid requests passed.
- [ ] Concurrency limit behavior was verified.
- [ ] Health remained responsive during bounded conversion activity.
- [ ] API restart recovery was verified.
- [ ] No unbounded resource or filesystem growth was observed in the bounded run.

### Verification and output

- [ ] All focused active-path suites passed.
- [ ] Every new local-deployment and burn-in test passed.
- [ ] Valid end-to-end conversion passed after final remediation.
- [ ] No new unrelated full-suite failure was introduced.
- [ ] Task-owned formatting, lint, and type checks passed.
- [ ] Tracked files contained no generated secrets or binary smoke outputs.
- [ ] Exactly one local implementation commit was created.
- [ ] Final Git working tree was clean.
- [ ] No push, remote deployment, workflow dispatch, or production mutation
      occurred.
- [ ] Final outcome used one allowed value.

## Verification

- Method:

  ```bash
  cd "$TARGET"

  sha256sum mpips/engine/imager_pipeline/tiff_json_to_dcm.py

  docker compose -f docker-compose.local.yml config

  uv run pytest tests/api/test_api_surface.py -v
  uv run pytest tests/api/test_dicom_authentication.py -v
  uv run pytest tests/api/test_dicom_conversion.py -v
  uv run pytest tests/test_host_launcher.py -v

  uv run pytest -v

  git diff --check
  git status --short
  git diff --stat
  git diff --name-only
  git show --stat --oneline --decorate --no-renames HEAD
  ```

  Also execute and report:

  - every task-created local deployment test;
  - every smoke and abuse-test matrix group;
  - compose exposure inspection;
  - image metadata inspection;
  - local listener inspection;
  - Redis privacy verification;
  - DICOM parse and validation evidence;
  - idempotency and worker-isolation evidence;
  - workspace and staging cleanup evidence;
  - bounded concurrency and recovery evidence.

- Expected result:
  - every scoped local safety gate passes;
  - valid synthetic input returns a validated DICOM;
  - invalid input fails closed with controlled errors;
  - MPIPS is reachable only through the loopback address;
  - Redis and isolated-worker boundaries remain private;
  - no known critical or high-severity defect remains in the tested active path;
  - the converter is unchanged;
  - one scoped local commit exists;
  - final repository and local runtime state are clean;
  - no remote deployment side effect occurred.

## Output

- Allowed outcomes: `succeeded`, `failed`, `blocked`, `awaiting-approval`, or
  `exhausted`.
- Report the selected runtime/model when verifiable, capabilities, outcome,
  changed files, affected interfaces, verification evidence, residual risks,
  and manual follow-up.
- Also report:
  - resolved `$TARGET`;
  - resolved local port;
  - starting and resulting commit SHAs;
  - initial and final `git status --short`;
  - exact changed-file list;
  - iteration count and per-iteration defect summary;
  - baseline focused and full-suite results;
  - final focused and full-suite results;
  - rendered local service topology;
  - local bind-address evidence;
  - Redis privacy evidence;
  - image tags and inspected runtime users;
  - every active-path matrix result;
  - valid DICOM validation summary;
  - authentication and HMAC negative-case summary;
  - upload, NPZ, calibration, and idempotency summary;
  - launcher, timeout, failure, and cleanup summary;
  - bounded concurrency and recovery summary;
  - converter SHA-256 before and after;
  - task-created Docker resources and cleanup result;
  - confirmation that no secret was committed or printed;
  - confirmation that no non-task resource was modified;
  - confirmation that no push, workflow dispatch, remote deployment, or
    production mutation occurred;
  - exact residual risks and untested external integrations;
  - exact next step for independent audit before preparing production
    deployment.

Treat any of the following as unsuccessful:

- iteration exhaustion with unresolved scoped failure;
- skipped mandatory focused verification;
- invalid or unparsed DICOM output;
- public or non-loopback exposure;
- published Redis;
- leaked or committed secrets;
- unresolved critical or high-severity active-path defect;
- modified converter;
- dirty final repository state;
- orphaned task-created runtime resources;
- model output alone without observed execution evidence.
