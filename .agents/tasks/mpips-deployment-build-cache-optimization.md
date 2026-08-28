---
name: mpips-deployment-build-cache-optimization
description: Persist and bound local BuildKit caches for internal-beta API and worker image builds.
version: 1
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

## Verification requirements

- Run `python -m uv run pytest tests/test_deployment_build_cache.py -q`.
- Run a focused YAML/source inspection sufficient to verify preserved workflow
  safeguards and exact cache rotation behavior.
- Report the exact working-tree state and observed command results.

## Stop conditions

Stop and return to planning if implementation requires changing application
behavior, dependency manifests/lockfile, production runtime semantics, an
unapproved cache backend, or any external/production mutation.

## Side-effect boundary

Repository edits and local verification are authorized. Do not dispatch
workflows, deploy, push, publish, mutate production, or modify external
systems.
