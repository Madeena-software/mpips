---
name: mpips-controlled-internal-beta-deploy-v1
description: Deploy the accepted MPIPS DICOM-only service as a private same-server internal beta, verify the live path, and document the trusted-NPZ residual-risk boundary.
version: 1
---

<!-- antigravity-code-agent-template:managed -->
# Task: Deploy MPIPS as a controlled internal beta

## Objective

For `$TARGET`, deploy the accepted MPIPS DICOM-only service on the same server
as MHCS as a controlled internal beta.

Accepted application commit:

```text
2f267aed2fd970530bb11d592f0f346feeaf2ace
```

Required endpoints:

```text
POST /v1/radiographs/dicom
GET  /health
```

The deployment must remain private. The executing agent must inspect the actual
MHCS runtime topology and select exactly one connection model:

```text
A. MHCS is containerized:
   MHCS -> http://mpips_api:8000 over a private shared Docker network.
   MPIPS publishes no host port.

B. MHCS runs directly on the host:
   MHCS -> http://127.0.0.1:${MPIPS_INTERNAL_PORT}
   MPIPS binds only to loopback.
```

Do not assume that `localhost` inside an MHCS container reaches MPIPS.

The beta is permitted only under this release condition:

```text
MPIPS accepts NPZ files only from the trusted MHCS capture path and trusted
Madeena detector software. Legacy pickle-enabled NPZ metadata remains a known
residual risk contained inside the network-disabled, non-root,
resource-limited isolated worker. Arbitrary third-party NPZ uploads are
prohibited.
```

The task may prepare deployment artifacts, create one scoped local commit,
deploy the beta, run live verification, and stop.

## Runtime requirements

- Required capabilities:
  - repository-read
  - repository-write
  - shell
  - docker
- Ordered model preferences: None.
- Require preferred model: false

## Runtime inputs

- TARGET (required): MPIPS repository root.
- DEPLOY_TEMPLATES (required): local checkout of Madeena-software/deploy-templates.
- MPIPS_INTERNAL_PORT (optional): loopback port for host-native MHCS; default 8000.
- REMOTE_PATH (optional): dedicated runtime directory; default /var/www/mpips-runtime.

## Context and evidence

Inspect:

- `AGENTS.md`;
- `.agents/AGENTS.md`;
- `.agents/context/project.md`;
- `.agents/skills/agent-task/SKILL.md`;
- current `HEAD`, branch, remotes, and working-tree status;
- commit `2f267aed2fd970530bb11d592f0f346feeaf2ace`;
- `Dockerfile`;
- `docker/Dockerfile.worker`;
- `docker-compose.local.yml`;
- `docker-compose.prod.yml`;
- `.env.local.example`;
- `.env.production.example`;
- `docker/entrypoint.sh`;
- `docker/host-launcher/`;
- `.github/workflows/`;
- `scripts/local_dicom_burn_in.py`;
- `mpips/api/`;
- `mpips/conversion/`;
- `mpips/workflows/imager_pipeline/npz_io.py`;
- focused and full tests;
- actual Docker, Swarm, systemd, network, and listener state;
- actual MHCS containers, services, stacks, networks, and host processes;
- applicable production templates under `$DEPLOY_TEMPLATES/templates/prod/`;
- SHA-256 of `mpips/engine/imager_pipeline/tiff_json_to_dcm.py`.

Madeena's deployment-template repository is the authority for self-hosted
runner, Swarm, dedicated deployment root, preflight, health waiting, rolling
updates, rollback, and secret-validation patterns. Adapt those patterns to
MPIPS. Do not copy irrelevant Laravel, PHP, MySQL, MinIO, public-domain,
frontend, queue, or Nginx requirements.

Required converter SHA-256:

```text
a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0
```

## Scope and constraints

In scope:

- determine actual MHCS topology from server evidence;
- prepare private production deployment configuration;
- adapt Madeena deployment-template patterns;
- build immutable MPIPS API and NPZ-worker images;
- configure private Redis;
- configure the isolated worker launcher;
- mount validated calibration artifacts read-only;
- configure the private MHCS-to-MPIPS connection;
- deploy locally on the same approved server;
- update the locally available MHCS runtime configuration only when the change
  is limited to the MPIPS internal base URL;
- run live health, route, authentication, HMAC, DICOM conversion, Redis,
  launcher, isolation, cleanup, restart, concurrency, and rollback checks;
- document the trusted-NPZ release condition;
- create one local implementation commit before deployment.

Deployment requirements:

- stack or project name: `mpips`;
- API service name: `api`;
- Swarm service name when applicable: `mpips_api`;
- no Nginx;
- no public hostname;
- no public ingress;
- no host port when MHCS is containerized;
- loopback-only host port when MHCS is host-native;
- Redis has no published port;
- Redis is accessible only to MPIPS;
- API and worker images use the deployed Git SHA, not `latest`;
- API, launcher, calibration, and workspace placement remain on the server that
  owns the required local paths and images;
- production documentation routes remain disabled;
- use one API replica for the initial beta unless shared state and local-path
  semantics are explicitly verified for more.

Trusted-NPZ beta conditions:

- only MHCS may call the endpoint;
- only trusted Madeena-generated NPZ files may be submitted;
- no direct end-user or third-party upload route may be introduced;
- safe non-pickle NPZ migration remains a mandatory post-beta task;
- the limitation must be recorded in project context and deployment notes.

Secrets and configuration:

- do not print or commit secret values;
- do not use fallback secrets;
- write runtime environment files with mode `0600`;
- require non-placeholder values for:
  - `MPIPS_MANIFEST_HMAC_SECRET`;
  - `MADEENA_IDP_JWKS_URL`;
  - `MADEENA_IDP_ISSUER`;
  - `MADEENA_IDP_AUDIENCE`;
  - `MPIPS_REDIS_PASSWORD`;
  - `MPIPS_CALIBRATION_HOST_PATH`;
- use `DEV_AUTH_BYPASS=false`;
- do not deploy local JWKS doubles or synthetic secrets.

Out of scope:

- public exposure or public hostname;
- TLS or public reverse proxy configuration;
- arbitrary third-party NPZ support;
- safe-NPZ migration;
- converter changes;
- DICOM semantic changes;
- calibration algorithm changes;
- generic DAG, Celery, S3, callback, webhook, or node-catalog deployment;
- deleting legacy generic code;
- unrelated cleanup.

Do not modify:

```text
mpips/engine/imager_pipeline/tiff_json_to_dcm.py
```

Do not modify DICOM semantics, calibration algorithms, or the NPZ producer
contract in this task.

Repository and server safety:

- stop if either repository is dirty;
- stop if accepted commit `2f267aed...` is not an ancestor of `HEAD`;
- do not reset, clean, stash, amend, rebase, or discard work;
- do not use `git add -A`;
- do not alter unrelated containers, stacks, services, networks, volumes,
  images, systemd units, or host files;
- snapshot task-relevant pre-deploy state;
- capture rollback evidence before changing the running service.

## Execution policy

- Mode: agentic-loop
- Maximum iterations: 6
- Approval gates:
  - ambiguous MHCS topology;
  - any public exposure;
  - converter, DICOM semantic, calibration algorithm, or NPZ contract change;
  - dependency installation or upgrade;
  - unavailable production secret;
  - missing or invalid calibration artifact;
  - destructive change to unrelated runtime resources;
  - any change outside stated scope;
  - live failure requiring product-contract changes.

Each iteration must follow:

```text
inspect -> preflight -> deploy or adjust -> observe -> diagnose
-> smallest scoped correction -> rerun affected verification
```

Do not weaken authentication, manifest signing, worker isolation, Redis
privacy, or verification checks.

## Execution procedure

1. Resolve inputs:

   ```bash
   cd "$TARGET"
   TARGET="$(pwd)"
   MPIPS_INTERNAL_PORT="${MPIPS_INTERNAL_PORT:-8000}"
   REMOTE_PATH="${REMOTE_PATH:-/var/www/mpips-runtime}"

   printf 'target=%s\n' "$TARGET"
   printf 'internal_port=%s\n' "$MPIPS_INTERNAL_PORT"
   printf 'remote_path=%s\n' "$REMOTE_PATH"

   git rev-parse --show-toplevel
   git rev-parse HEAD
   git status --short
   ```

2. Stop with `blocked` if the MPIPS tree is dirty.

3. Verify accepted baseline ancestry:

   ```bash
   git merge-base --is-ancestor \
     2f267aed2fd970530bb11d592f0f346feeaf2ace \
     HEAD
   ```

4. Resolve and inspect `$DEPLOY_TEMPLATES`:

   ```bash
   cd "$DEPLOY_TEMPLATES"
   DEPLOY_TEMPLATES="$(pwd)"
   git rev-parse --show-toplevel
   git rev-parse HEAD
   git status --short
   ```

5. Stop if the deployment-template repository is dirty or incorrect.

6. Read all applicable instructions and the task-execution skill.

7. Record converter hash before any change:

   ```bash
   cd "$TARGET"
   sha256sum mpips/engine/imager_pipeline/tiff_json_to_dcm.py
   ```

8. Record server state without exposing secrets:

   ```bash
   docker version
   docker compose version
   docker info
   docker ps --format '{{.ID}} {{.Names}} {{.Image}} {{.Ports}}'
   docker network ls
   docker volume ls
   docker stack ls
   docker service ls
   systemctl status mpips-launcher.socket --no-pager || true
   systemctl status mpips-launcher.service --no-pager || true
   ss -lnt
   ```

9. Determine MHCS topology:

   - `containerized-swarm`: MHCS runs as a Swarm service;
   - `containerized-compose`: MHCS runs as a container or Compose project;
   - `host-native`: MHCS runs directly on the host;
   - `ambiguous`: evidence is insufficient.

   Stop with `awaiting-approval` if ambiguous.

10. Select the connection model:

    - Swarm: use an approved private attachable overlay network and
      `http://mpips_api:8000`; publish no MPIPS host port.
    - Compose: use a private shared bridge network and stable service DNS;
      publish no MPIPS host port.
    - Host-native: bind only to
      `127.0.0.1:${MPIPS_INTERNAL_PORT}`.

11. Inspect Madeena deployment templates and record the source commit.

12. Inspect the local burn-in implementation and promote only production-safe
    parts. Do not carry local JWKS doubles, date-based tags, or synthetic
    secrets into the beta deployment.

13. Verify required production inputs without printing values:

    - JWKS URL, issuer, and audience are non-placeholder;
    - HMAC secret is non-placeholder and at least 32 characters;
    - Redis password is non-empty;
    - calibration path exists;
    - `metadata.json` and `remap.npz` exist;
    - calibration metadata has `validated: true`;
    - workspace and launcher socket paths are usable;
    - selected loopback port is available when host-native.

14. Prepare deployment artifacts with:

    - `mpips-api:<deployed-short-sha>`;
    - `mpips-npz-worker:<deployed-short-sha>`;
    - private Redis;
    - production environment;
    - `DEV_AUTH_BYPASS=false`;
    - read-only calibration mount;
    - shared workspace and launcher socket;
    - non-root API and worker;
    - network-disabled, read-only, capability-dropped worker;
    - no-new-privileges;
    - CPU, memory, PID, concurrency, and timeout limits;
    - no `latest`;
    - no Nginx;
    - no public port.

15. Configure the host launcher:

    - dedicated socket-access group;
    - socket mode `0660`;
    - immutable worker image;
    - fixed workspace root;
    - fixed worker invocation;
    - no arbitrary client-supplied Docker arguments;
    - idempotent systemd installation or update;
    - audit logging without PHI or secrets.

16. Add or update deployment validation tests as needed.

17. Update `.agents/context/project.md` with:

    - controlled internal beta status;
    - detected MHCS topology;
    - exact private MPIPS URL;
    - no public exposure;
    - trusted-NPZ condition;
    - pickle-enabled NPZ residual risk;
    - isolated-worker containment controls;
    - mandatory safe-NPZ follow-up;
    - deployment-template source commit;
    - exact deployment verification evidence.

18. Run pre-deploy checks:

    ```bash
    uv run pytest tests/api/test_api_surface.py -v
    uv run pytest tests/api/test_dicom_authentication.py -v
    uv run pytest tests/api/test_dicom_conversion.py -v
    uv run pytest tests/test_host_launcher.py -v
    uv run pytest -v
    uv run black --check mpips tests scripts
    uv run flake8 mpips tests scripts
    uv run mypy mpips tests
    ```

    Use the established `.venv/bin/python -m uv run` equivalent when needed.

19. Render deployment configuration with temporary environment values without
    printing secret values.

20. Verify rendered policy:

    - no public port for containerized MHCS;
    - loopback-only port for host-native MHCS;
    - no Redis host port;
    - no Nginx or public hostname;
    - no `latest`;
    - correct private network and immutable tags;
    - required mounts present;
    - no secret fallback rendered.

21. Build and inspect API and worker images.

22. Run a pre-deploy candidate stack using the exact candidate images and
    synthetic test data.

23. Run `scripts/local_dicom_burn_in.py` or its verified successor against the
    candidate stack. Require all active-path checks to pass.

24. Verify converter hash again.

25. Inspect and commit deployment artifacts:

    ```bash
    git diff --check
    git status --short
    git diff --stat
    git diff --name-only
    ```

26. Stage only task-owned files and create exactly one local commit:

    ```text
    deploy: release MPIPS controlled internal beta
    ```

27. Use the resulting commit SHA for final immutable image tags. Rebuild when
    necessary.

28. Capture rollback state:

    - current MPIPS stack or Compose configuration;
    - current images and service/container IDs;
    - current MHCS MPIPS URL;
    - current launcher configuration;
    - current health state.

29. Deploy exactly one mechanism:

    - Docker Swarm for `containerized-swarm`;
    - Docker Compose for `containerized-compose`;
    - loopback-bound Docker Compose for `host-native`.

30. Wait for Redis, launcher, and API health using finite timeouts.

31. Verify live exposure:

    - no public listener;
    - correct private URL from the MHCS execution context;
    - Redis private;
    - worker network-disabled;
    - no Nginx or ingress route.

32. Verify live routes:

    ```text
    GET /health                      -> 200
    GET /                            -> 404
    GET /v1/nodes                    -> 404
    GET /v1/jobs                     -> 404
    GET /v1/secure-test              -> 404
    GET /docs                        -> 404
    GET /redoc                       -> 404
    GET /openapi.json                -> 404
    ```

33. Run a live authenticated synthetic conversion from the same context used by
    MHCS.

34. Validate returned DICOM:

    - `application/dicom`;
    - readable by pydicom;
    - expected synthetic patient/study/UID mapping;
    - expected transfer syntax and dimensions;
    - uint16 pixel data;
    - no private tags;
    - validation result successful.

35. Run live beta checks:

    - unauthenticated request rejected;
    - missing scope rejected;
    - wrong HMAC rejected;
    - stale timestamp rejected;
    - malformed manifest rejected;
    - malformed NPZ rejected safely;
    - object-array synthetic case remains contained in the isolated worker;
    - Redis interruption gives controlled failure and recovery succeeds;
    - launcher unavailability gives controlled failure;
    - API restart recovers;
    - bounded concurrency obeys configured limit;
    - workspace and staging cleanup complete;
    - no orphan worker container remains.

36. Inspect sanitized logs for secrets, bearer tokens, HMAC values, complete
    manifests, non-synthetic patient identifiers, and client-visible internal
    traces.

37. For a scoped failure, diagnose and make the smallest correction, then rerun
    focused checks and redeploy within the iteration limit.

38. Roll back immediately when:

    - public exposure is observed;
    - valid conversion fails and cannot be corrected;
    - authentication or HMAC enforcement fails;
    - Redis is published;
    - worker isolation is absent;
    - cleanup leaves unsafe residual state;
    - a critical or high active-path issue is found.

39. Confirm from the MHCS execution context that the selected private URL
    reaches `/health`.

40. Do not use real patient files.

41. Record final state:

    ```bash
    git rev-parse HEAD
    git status --short
    docker ps --format '{{.ID}} {{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
    docker stack ls
    docker service ls
    ss -lnt
    ```

42. Stop. Do not expose MPIPS publicly and do not begin safe-NPZ migration in
    this task.

## Acceptance criteria

- [ ] Runtime inputs resolved correctly.
- [ ] Initial repositories were clean.
- [ ] Accepted commit `2f267aed...` was an ancestor of starting `HEAD`.
- [ ] Converter hash matched before and after.
- [ ] Actual MHCS topology was determined from evidence.
- [ ] Correct private connection model was selected.
- [ ] MPIPS was not exposed publicly.
- [ ] Containerized MHCS did not use `localhost` for MPIPS.
- [ ] Host-native MHCS used loopback only.
- [ ] Redis had no published host port.
- [ ] No Nginx or public ingress was deployed.
- [ ] API and worker images used immutable commit-derived tags.
- [ ] No deployed service used `latest`.
- [ ] Production authentication and manifest signing were enabled.
- [ ] No local JWKS double or synthetic secret was used in the beta deployment.
- [ ] Calibration artifacts were validated and mounted read-only.
- [ ] Host launcher used fixed, audited worker invocation.
- [ ] Worker remained non-root, read-only, network-disabled,
      capability-dropped, no-new-privileges, and resource-limited.
- [ ] Trusted-NPZ release condition was documented.
- [ ] Pickle-enabled NPZ residual risk was documented.
- [ ] Arbitrary third-party NPZ support was not claimed.
- [ ] Safe-NPZ migration was recorded as mandatory follow-up.
- [ ] Pre-deploy tests passed.
- [ ] Candidate burn-in passed.
- [ ] One scoped deployment commit was created.
- [ ] Rollback state was captured.
- [ ] Live health and route checks passed.
- [ ] Live authenticated synthetic DICOM conversion passed.
- [ ] DICOM parsing and validation passed.
- [ ] Authentication, HMAC, malformed-input, Redis, launcher, restart,
      concurrency, and cleanup checks passed.
- [ ] No secrets or non-synthetic patient data appeared in tracked files,
      client errors, or logs.
- [ ] No orphan worker or unsafe task-created resource remained.
- [ ] MHCS execution context reached the selected private MPIPS URL.
- [ ] Final Git working tree was clean.
- [ ] Final outcome used one allowed value.

## Verification

- Method:

  ```bash
  cd "$TARGET"

  sha256sum mpips/engine/imager_pipeline/tiff_json_to_dcm.py

  uv run pytest tests/api/test_api_surface.py -v
  uv run pytest tests/api/test_dicom_authentication.py -v
  uv run pytest tests/api/test_dicom_conversion.py -v
  uv run pytest tests/test_host_launcher.py -v
  uv run pytest -v

  git diff --check
  git status --short
  git show --stat --oneline --decorate --no-renames HEAD
  ```

  Also report exact observed results for topology detection, deployment-template
  source, rendered deployment configuration, image build and inspection,
  candidate burn-in, rollback snapshot, live deployment, private exposure,
  live DICOM conversion, Redis interruption and recovery, launcher failure,
  restart recovery, bounded concurrency, cleanup, and MHCS-context connectivity.

- Expected result:
  - MPIPS runs as a private same-server controlled internal beta;
  - MHCS reaches it only through the selected private URL;
  - no public MPIPS or Redis exposure exists;
  - the active DICOM path passes live verification;
  - trusted legacy NPZ input remains contained in the isolated worker;
  - residual pickle risk is explicitly documented;
  - rollback evidence exists;
  - final repository state is clean.

## Output

- Allowed outcomes: succeeded, failed, blocked, awaiting-approval, exhausted.
- Report:
  - selected runtime/model when verifiable;
  - capabilities and outcome;
  - resolved inputs;
  - starting and resulting commit SHAs;
  - exact changed files;
  - deployment-template source commit;
  - detected MHCS topology;
  - selected internal MPIPS URL;
  - deployed stack or Compose project;
  - immutable API and worker image tags;
  - required secret names without values;
  - calibration verification;
  - converter hashes before and after;
  - pre-deploy tests and candidate burn-in;
  - rollback snapshot;
  - live service health and route results;
  - live DICOM validation summary;
  - authentication, HMAC, Redis, launcher, restart, concurrency, and cleanup
    results;
  - public-exposure inspection;
  - trusted-NPZ release condition;
  - residual pickle risk;
  - mandatory safe-NPZ follow-up;
  - final `git status --short`;
  - residual risks;
  - exact rollback procedure;
  - confirmation that no public exposure or real-patient test occurred.

Treat as unsuccessful:

- ambiguous topology;
- missing secret or calibration artifact;
- public exposure or published Redis;
- mutable image tag;
- failed live DICOM conversion;
- failed authentication or HMAC enforcement;
- absent worker isolation;
- leaked secret or non-synthetic patient data;
- modified converter;
- dirty final tree;
- unresolved critical or high active-path defect;
- model output without observed deployment evidence.
