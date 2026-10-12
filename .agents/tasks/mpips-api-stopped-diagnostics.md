---
title: MPIPS stopped API read-only diagnostics
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS stopped API read-only diagnostics  
**Task path:** `.agents/tasks/mpips-api-stopped-diagnostics.md`  
**Task contract state:** Validated/Published  
**Delivery objective / Work Package:** Phase B2 operational triage — explain stopped API state without recovery or service mutation  
**Owner / designated planning authority:** Repository owner; human-supplied “MPIPS Production API Stopped: Operational Triage” request

## Delivery context

The infrastructure audit at run `38272117045` observed the expected MPIPS API
container as stopped and Redis as running and healthy. Repository configuration
and historical Actions runs do not establish why the API stopped. Add narrowly
scoped read-only diagnostics so a future separately authorized audit can report
fixed categories that help distinguish runtime failure, OOM termination,
restart behavior, deployment identity mismatch, and missing API/Redis network
attachment without exposing raw inspection output.

## Baseline and task revision

**Implementation baseline:** `cb0e7468b1c186119a3dfcc97d55176b6f4a9f98`  
**Task revision:** resolved to the immutable publication commit before execution.

## Objective

Extend the existing read-only infrastructure collector with allowlisted API
container diagnostics, synthetic coverage, and documentation for interpreting
those categories. Do not access production during implementation and do not
restart, redeploy, replace, or otherwise mutate any service.

## Authoritative inputs

### Governing authority

- Human-supplied “MPIPS Production API Stopped: Operational Triage” request.
- `.agents/AGENTS.md`, `.agents/software-workflow.md`, root `AGENTS.md`, and
  `.agents/prompts/plan-create-task.md`.
- Current accepted baseline `cb0e7468b1c186119a3dfcc97d55176b6f4a9f98`.
- `docker-compose.prod.yml` and the internal beta deployment/verification
  workflows as implementation evidence, not authority to recover production.
- Existing infrastructure audit run `38272117045` as a point-in-time,
  sanitized observation only.

### Requirement traceability

- `API-TRIAGE-STATE` → human request §§1–2: classify the API's stopped-state
  evidence without inferring intent from exit code alone.
- `API-TRIAGE-IDENTITY` → human request §2: compare expected deployment marker,
  container image identity, and API/Redis shared network attachment using
  fixed output categories.
- `API-TRIAGE-PRIVACY` → human request §2 and public-log boundary: keep raw
  Docker output private and emit only fixed allowlisted categories.
- `API-TRIAGE-VERIFY` → human request §3: add synthetic tests and use
  GitHub-hosted CI only.
- `API-TRIAGE-OPS` → human request §§3–4: no production dispatch or service
  recovery; retain the requirement for new explicit owner authorization after
  independent review.

## Scope

### In scope

- `scripts/audit_infrastructure_readonly.py`: inspect only the expected API
  and Redis containers; classify API exit as `zero`, `nonzero`, `not_applicable`,
  or `unknown`; OOM state as `yes`, `no`, or `unknown`; restart count as
  `none`, `few` (1–5), `many` (6+), or `unknown`; stopped age as `recent`
  (less than 24 hours), `historical`, `not_applicable`, or `unknown`; actual
  restart policy as `unless-stopped`, `other`, or `unknown`; API image versus
  `/var/www/mpips-runtime/.mpips-version` as `yes`, `no`, or `unknown`; and
  whether API and Redis both attach to `mpips-internal-beta-v1` as `yes`, `no`,
  or `unknown`.
- `tests/test_infrastructure_readonly_audit.py`: synthetic stopped/running
  containers; zero/nonzero exit categories; OOM states; restart count bounds;
  recent/historical/malformed timestamps; restart policies; matching,
  mismatching, and missing deployment markers; shared/missing/uninterpretable
  network attachment; and Docker command failures. Verify that no IDs, image
  names or tags, addresses, marker contents, raw output, or arbitrary errors
  reach public output.
- `docs/integration/infrastructure-readonly-audit.md`: describe the new fixed
  categories, their limits, and why exit status does not prove intentional
  termination.
- `.agents/evidence/mpips-api-stopped-diagnostics.md`: record task and CI
  evidence, historical deployment conclusions, and public Actions log
  limitations without reproducing sensitive values.

### Out of scope

- Any production workflow dispatch, runner contact, host inspection, service
  restart, redeploy, replacement, configuration change, or recovery.
- Changes to deployment/verification workflows, Compose configuration,
  runner registration/name/group, networks, ingress, storage, certificates,
  credentials, or production services.
- Reading or emitting container logs, container environment, raw Docker output,
  process command lines, patient/clinical workspace data, actual addresses,
  hostnames, user identities, container IDs, image tags, or error strings.
- Resolving whether the stop was intentional, approving recovery, or approving
  the separate Compose Release Service.

### Preserved behavior

- The existing infrastructure audit remains manual-only, `main`-guarded,
  read-only, resource-limited, and without secrets, artifact uploads, or
  workflow-run triggers.
- Only fixed labels and enumerated categories are emitted by the collector.
- Missing or ambiguous inspection data remains `unknown`.
- Existing deployment, verification, Docker, and network configuration remain
  unchanged.
- No exit code or OOM result alone is treated as proof of user intent or root
  cause.

## Dependencies and assumptions

### Dependencies

- The deployment workflow writes `.mpips-version` after its readiness check;
  its format is a full Git commit SHA.
- Docker inspect can query a present stopped container without starting it.
- Pull-request CI is GitHub-hosted and does not target the production runner.

### Approved assumptions

- “Recent” means less than 24 hours from collector execution; `FinishedAt`
  must parse as an unambiguous UTC timestamp or age is `unknown`.
- Restart count categories are `none` for 0, `few` for 1–5, and `many` for 6
  or greater. These bands are descriptive only.
- A version-marker match means only that the container's configured image tag
  matches the deployment marker; it does not cryptographically attest an image
  or independently establish owner approval.
- Shared attachment to the expected internal network is a topology indicator,
  not proof of application-level Redis connectivity.

### Remaining approval requirements

- Independent review of the exact Draft PR is required before merge.
- Any later production diagnostic requires fresh explicit owner authorization.
  Before dispatch, verify no production deployment or verification job is
  active or pending.
- Before any public production run, the owner must decide whether the
  standard GitHub Actions runner-name metadata is acceptable for public logs or
  authorize an appropriate runner-identity remediation. The workflow source
  cannot suppress this platform-emitted setup metadata.
- Recovery requires a separate explicit owner authorization and assessment.

## Execution constraints

- Create a new feature branch from the implementation baseline above.
- Do not run local tests, formatting, lint, or mypy as verification; use
  GitHub-hosted CI only.
- Keep captured command output private to the collector. Use bounded,
  read-only commands with fixed arguments and timeouts.
- Do not add or change deployment, verification, or infrastructure audit
  workflow behavior, Compose files, runner settings, or production config.
- Do not inspect Docker logs, host journals, processes, environments, files in
  clinical workspaces, or any data beyond the explicitly scoped marker and
  Docker metadata.
- Treat GitHub Actions setup metadata as a separate public-log channel from
  collector output. Record the observed runner-name field without copying its
  value into repository artifacts or responses.
- Do not merge, dispatch a workflow, contact production, or perform recovery.

## Acceptance criteria

- [ ] API exit status, OOM state, restart count, and stopped age use only the
  specified fixed categories and fail closed to `unknown` on malformed or
  failed inspection.
- [ ] The actual restart policy, deployment-marker/image comparison, and
  expected API/Redis network attachment are classified independently and do
  not expose raw values.
- [ ] A zero or nonzero exit category is explicitly documented as insufficient
  to determine intent or cause.
- [ ] Synthetic tests cover boundaries, malformed values, absent containers,
  command failures, and public-output sanitization.
- [ ] Documentation and evidence distinguish verified history from hypotheses
  and preserve the no-recovery/no-production-access boundary.
- [ ] GitHub-hosted PR CI passes focused tests, formatting, lint, mypy
  regression checks, and relevant repository CI.
- [ ] The infrastructure audit workflow, deployment and verification workflows,
  Compose configuration, and production state are unchanged.
- [ ] A Draft PR is published for independent review; no merge or production
  diagnostic occurs in this task.

## Verification requirements

- Use GitHub-hosted pull-request CI only; record exact run URLs, commit SHA,
  conclusions, and checks observed.
- Read Actions run metadata without printing raw deployment, verification,
  runner, or collector logs.
- No production workflow may be dispatched, and no production runner may be
  contacted during implementation or review preparation.

## Stop conditions

- Stop if the diagnostics require logs, environments, process command lines,
  clinical data, raw addresses, secrets, or a production mutation.
- Stop if the version marker or Docker fields cannot be interpreted safely;
  report `unknown` instead of inferring.
- Stop if task implementation requires changing the audit workflow, runner
  settings, deployment/verification workflows, or production configuration.
- Stop before merge or production dispatch; return the PR for independent
  review and await new explicit authorization for any diagnostic run.

## Explicitly authorized side effects

- Create and publish a feature branch, commit the validated task and bounded
  implementation, open a Draft PR, and allow its ordinary GitHub-hosted PR CI
  checks to run.
- Do not merge, dispatch any production workflow, contact the production
  runner, change production, restart or redeploy services, or approve recovery.

## Expected terminal outcome

Draft PR ready for independent review, with GitHub-hosted CI evidence and no
production diagnostic or service mutation. The cause and intent of the API
container stop remain unknown pending separately authorized diagnostics.
