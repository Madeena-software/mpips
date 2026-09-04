---
name: mpips-deployment-build-cache-optimization
description: Persist and bound local BuildKit caches for internal-beta API and worker image builds.
version: 2
status: Validated/Published
---

# Task: MPIPS Production Deployment Build Cache Optimization

## Objective

Reduce repeated network downloads and Docker rebuild time in
`.github/workflows/deploy-internal-beta.yml` by using a persistent Docker
Buildx builder, bounded local BuildKit cache rotation, and uv cache mounts,
while preserving deployment and runtime semantics.

## Baseline and authority

- Implementation baseline: `f2bf7b9980f9af7649e1a6c45c46aaee7a55a36a`
- Governing request: `MPIPS — PRODUCTION DEPLOYMENT BUILD CACHE OPTIMIZATION`
- Preconditions observed before publication: deployment run `33127264314`
  succeeded at the baseline SHA; `origin/main` equals the baseline SHA.

## Remediation required

Review basis: production run `33130072220` and implementation
`bda82397079238d417e4b9caf9fba86170a5f460`.

Finding: `TRANSIENT_BUILDKIT_BOOTSTRAP_NETWORK_FAILURE`. The docker-container
builder bootstrap performs one network-dependent attempt to obtain/start
BuildKit. A transient connection reset during that first bootstrap aborts the
deployment before image construction.

Bounded remediation: add a finite retry around BuildKit bootstrap only, with
exactly three maximum attempts and finite bounded backoff (10 seconds after
attempt 1 and 30 seconds after attempt 2). Reuse the same named builder without
deleting or recreating it between attempts. Bootstrap failure after the final
attempt remains fatal, and image builds must not begin unless bootstrap
succeeds.

Do not add retries around tests, image builds, deployment, Compose, health
verification, rollback, or calibration validation. Do not change either
Dockerfile or any existing cache, image, deployment, or safety semantics.

## Scope

### In scope

- Update `.github/workflows/deploy-internal-beta.yml` to use the persistent
  `mpips-production-cache` docker-container Buildx builder, local API/worker
  cache scopes under `${HOME}/.cache/mpips-buildkit`, safe `.next` rotation,
  `--load`, cache import/export, and image inspection.
- Pin the uv image to digest
  `sha256:95f2aa1fe59274951cfe9b0cbc7972e879ff1004bc8945d130a32eb0dbd85945`
  in `Dockerfile` and `docker/Dockerfile.worker` using a named uv stage.
- Keep the apt/system-library layer independent of the uv stage and add
  distinct locked BuildKit uv cache mounts for API and worker dependencies.
- Add `tests/test_deployment_build_cache.py` using repository test conventions.

### Out of scope

- Application behavior, `pyproject.toml`, `uv.lock`, dependency extras, or
  system package sets.
- Removing or changing the Deploy job's Python/uv environment.
- GHCR or `type=gha` Docker caches, image pushes, mutable image tags, or any
  production deployment, rollback, or external mutation.

## Preserved behavior

- `workflow_dispatch`, concurrency group `mpips-internal-beta`, immutable
  `$GITHUB_SHA` image tags, `--load`, Compose deployment, rollback, health and
  authentication checks, network validation, runtime markers, launcher,
  calibration handling, ports, Redis isolation, MHCS integration network,
  secrets, and all existing deployment safety semantics.
- `UV_LINK_MODE=copy`, frozen dependency sync semantics, and existing API and
  worker extras.
- Existing Dockerfile application-source ordering: dependency sync occurs
  before application source is copied.

## Execution constraints

- Do not use `uv sync --upgrade`.
- Use separate API and worker cache directories and uv cache IDs.
- A missing active cache must not fail the build.
- Remove stale `.next` before each build; export to `.next`; replace the active
  cache only after a successful image build and verified `.next/index.json`.
  Preserve the prior active cache on build or cache-export failure.
- Do not delete or recreate the named builder on each run.
- Do not add `--no-cache` or modify application/runtime files.

## Acceptance criteria

- [ ] Both Dockerfiles use the same immutable uv digest and not `uv:latest`.
- [ ] Both Dockerfiles use `RUN --mount=type=cache` with distinct uv cache IDs.
- [ ] Apt/system libraries precede uv binary copy; dependency sync precedes
      application-source copies with existing extras unchanged.
- [ ] Workflow safely reuses or creates the named docker-container builder and
      bootstraps it.
- [ ] Both builds use `docker buildx build`, `--load`, local `--cache-from`,
      local `--cache-to`, and `mode=max` with distinct persistent scopes.
- [ ] Cache rotation preserves the old cache until successful build/export and
      verified `.next/index.json`; missing cache directories are supported.
- [ ] SHA-based image tags remain unchanged and each loaded image is inspected.
- [ ] No GHCR push, `type=gha` cache, mutable application tag, or `--no-cache`
      is introduced.
- [ ] Deploy-job uv setup remains present and all listed production safeguards
      remain unchanged.
- [ ] Focused deterministic regression tests cover the Dockerfile and workflow
      invariants above.
- [ ] The bootstrap retry has exactly three attempts, finite backoff, fatal
      final failure, and no builder removal or recreation inside the retry loop.

## Verification requirements

- Run `pytest tests/test_deployment_build_cache.py -q`.
- Run `pytest tests/api/test_api_surface.py tests/api/test_dicom_authentication.py
  tests/api/test_dicom_conversion.py tests/test_host_launcher.py -q`.
- Run `pytest tests/test_verify_production_real_trx.py -q`.
- Run YAML validation, `python -m compileall tests`, and `git diff --check`.
- Run Black and Flake8 on the new or materially modified Python test file only.
- Extend `tests/test_deployment_build_cache.py` with deterministic source-level
  assertions for the bounded bootstrap retry and unchanged workflow behavior.
- Run a focused YAML/source inspection sufficient to verify preserved workflow
  safeguards and exact cache rotation behavior.
- Report the exact working-tree state and observed command results.

## Stop conditions

Stop and return to planning if implementation requires changing application
behavior, dependency manifests/lockfile, production runtime semantics, an
unapproved cache backend, or any external/production mutation.

## Side-effect boundary

Authorized: implementation repository edits, local verification, one
implementation commit, and pushing that implementation commit to `origin/main`.
The implementation commit message MUST be:
`ci: add persistent Docker build cache`.

Prohibited: deploy workflow dispatch, Stage C dispatch, production mutation,
calibration mutation, Docker or network mutation outside the workflow source,
and secrets or other external-system mutation. Do not deploy after pushing.
