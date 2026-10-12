---
title: MPIPS B2 operational evidence closure
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS B2 operational evidence closure  
**Task path:** `.agents/tasks/mpips-b2-operational-evidence-closure.md`  
**Task contract state:** Validated/Published  
**Delivery objective / Work Package:** Phase B2 — safely improve read-only diagnostics after the initial audit  
**Owner / designated planning authority:** Repository owner; human-supplied request in this session

## Delivery context

The initial audit reported missing expected services alongside healthy aggregate
container health, and could not classify ports 8014, 80, or 443. Improve the
collector so those labels distinguish the expected API and Redis containers,
their individual health, expected project completeness, and target-port
listeners. This is diagnostic code and does not change deployed services.

## Baseline and task revision

**Implementation baseline:** `bfe5237f86a4a535c76c9368099a65e0b1fad653`  
**Task revision:** this file @ exact publication commit recorded in the Planner handoff.

## Objective

Correctly classify expected Compose service presence and health, and classify
target TCP listeners with narrowly scoped, fail-closed inspection. Record
unresolved service-state and ingress questions in a Draft ADR. Do not execute a
production audit.

## Authoritative inputs

### Governing authority

- Human-supplied “MPIPS B2 Operational Evidence Closure” request in this session.
- `.agents/AGENTS.md`, `.agents/software-workflow.md`, and root `AGENTS.md`.
- `docker-compose.prod.yml` for current expected project service names and health-check configuration.
- First audit, run `38265842527`, as observed evidence only; it does not establish current live state.

### Requirement traceability

- `B2-STATE` → human request §§1–3: distinguish API and Redis state and health; missing services and inspection errors differ; Redis health cannot stand in for API health.
- `B2-PORTS` → human request §2: exclusively loopback port 8014 and listener presence on 80/443; narrowly scoped parsing with unknown for ambiguity.
- `B2-PUBLIC-LOGS` → human request §3: fixed categories only; no raw inspection output or sensitive values.
- `B2-VERIFY` → human request §4: comprehensive synthetic coverage and GitHub-hosted CI only.
- `B2-ARCH` → human request §6: record open service-state and ingress questions in a Draft ADR; Compose Release Service remains a proposal.
- `B2-BOUNDARY` → human request §§4–5: no deployment/workflow changes, production workflow dispatch/contact, merge, or release.

## Scope

### In scope

- `scripts/audit_infrastructure_readonly.py`: fixed classifications for API and Redis container state (`running`, `stopped`, `not_found`, `unknown`); individual health (`healthy`, `unhealthy`, `unavailable`, `unknown`); expected Compose project completeness; exclusive loopback binding on 8014; and listener presence on 80/443.
- `tests/test_infrastructure_readonly_audit.py`: synthetic partial/missing/stopped/duplicate service results, health combinations, failed/malformed Docker inspection, IPv4/IPv6 and wildcard listener forms, absent listeners, missing output, malformed target output, and malformed unrelated-port output.
- `docs/integration/infrastructure-readonly-audit.md`: updated output labels and interpretation.
- `.agents/architecture/adr-mpips-b2-operational-questions.md`: Draft ADR recording unresolved service-state, ingress, and listener questions and preserving the separate Compose Release Service as a proposal.
- `.agents/evidence/mpips-b2-operational-evidence-closure.md`: execution, CI, and side-effect evidence for this task.

### Out of scope

- Changes to deployment or verification workflows, Compose configuration, production services, Docker/network configuration, runner settings, secrets, or GitHub settings.
- Production workflow dispatch, runner contact, production inspection, redeploy, restart, merge, self-approval, or release.
- Resolving operational or ingress questions by assumption, selecting infrastructure, or approving/implementing a Release Service.
- Uploading reports, artifacts, raw command output, or debug logs.

### Preserved behavior

- The existing audit workflow remains manual-only, main-guarded, read-only, resource-limited, and protected by its existing security boundaries.
- The collector keeps all raw inspection output inside its process and prints only fixed allowlisted categories. It never prints addresses, hostnames, identities, command lines, credentials, or Docker output.
- Inspection failures and genuinely ambiguous output remain `unknown`; a healthy Redis container does not imply API health.
- Existing deployment and verification workflows and production services remain unchanged.

## Dependencies and assumptions

### Dependencies

- `docker-compose.prod.yml` identifies expected service labels `mpips-api` and `redis` and their configured health checks.
- Existing GitHub-hosted `MPIPS CI` and Ubuntu qualification PR checks are the only permitted verification execution for this task.

### Approved assumptions

- Docker Compose service labels are the expected project-service identity. A valid inventory that omits one or both expected services establishes `not_found`; command failure or malformed output establishes `unknown`.
- For a present service, a valid non-running Docker state maps to `stopped`. A running service without a configured health check is `unavailable`; health inspection failure or unrecognized status is `unknown`.
- Project completeness is `yes` only when exactly one API and one Redis service container are identified; a valid inventory showing a missing service is `no`; duplicate or uninterpretable service records are `unknown`.
- Listener commands may be scoped to one requested TCP port at a time. Only interpretable matching listeners contribute to the result; malformed target-port evidence remains `unknown`.

### Remaining approval requirements

- Independent review of the exact Draft PR is required before merge.
- A new, explicit owner authorization is required before any later production diagnostic run. Before that dispatch, verify that no production deployment or verification job is active or pending.
- Architecture and owner decisions remain required for actual service-state resolution, approved HTTPS ingress identity, candidate network ranges, and any Release Service proposal.

## Required capabilities

- Repository read/write, Git publication, GitHub PR and Actions status access.
- GitHub-hosted CI execution through normal pull-request checks only.

## Execution constraints

- Start from `bfe5237f86a4a535c76c9368099a65e0b1fad653` on a new feature branch.
- Do not run local tests, formatting, lint, or mypy as verification; use GitHub-hosted CI only.
- Keep command outputs private; use fixed commands and arguments; do not print raw Docker or `ss` output or sensitive values.
- Do not alter `.github/workflows/deploy-internal-beta.yml`, `.github/workflows/verify-internal-beta.yml`, `.github/workflows/audit-infrastructure-readonly.yml`, or `docker-compose.prod.yml`.
- Preserve the current audit trigger, `main` guard, production runner, concurrency, permissions, timeout, and no-upload/no-secret boundaries.
- The Draft ADR records questions and options only; it MUST NOT state an unapproved architecture decision. The separate single-server Compose Release Service stays a preferred proposal, not approved deployment.

## Acceptance criteria

- [ ] API and Redis states independently classify as `running`, `stopped`, `not_found`, or `unknown`.
- [ ] API and Redis health independently classify as `healthy`, `unhealthy`, `unavailable`, or `unknown`; Redis health never determines API health.
- [ ] Expected project completeness distinguishes valid missing-service inventory from inspection errors and ambiguity.
- [ ] Port 8014 is `yes` only when all observed target listeners use recognized loopback addresses; any wildcard/non-loopback match is `no`; no listener is `no`; missing or malformed target inspection is `unknown`.
- [ ] Ports 80 and 443 report listener presence; malformed output for unrelated ports does not make target results unknown.
- [ ] Synthetic tests cover partial stacks, stopped/not-found services, healthy/unhealthy combinations, Docker failures and malformed records, IPv4/IPv6 loopback and wildcard formats, non-loopback, absent listeners, and malformed unrelated-port data.
- [ ] Public output contains only fixed labels/categories and no raw inspection output or actual address data.
- [ ] Documentation and a Draft ADR accurately explain results and open questions without deciding service recovery or ingress architecture.
- [ ] GitHub-hosted PR CI passes focused tests, formatting, lint, mypy regression checks, and relevant CI. No local verification commands are run.
- [ ] Existing deployment, verification, and audit workflow files and Compose configuration are unchanged; no production workflow is run or production runner contacted.
- [ ] A new feature branch and Draft PR are published for independent review. No merge occurs.

## Verification requirements

- Required evidence is limited to GitHub-hosted checks triggered by the Draft PR. Report exact run URLs, SHA, and observed conclusions.
- Include focused audit tests, full applicable CI, Black, Flake8, and mypy regression results as reported by the hosted workflows.
- Inspect the exact diff and GitHub workflow run metadata read-only; do not trigger workflow dispatches.
- Record explicit evidence that no production workflow was dispatched/run for this task. The prior one-time authorization for run `38265842527` is not reusable.

## Stop conditions

- Stop if implementation requires a production workflow/configuration change, production access, a deployment action, secrets, or a new architecture decision.
- Stop if fixed-category output cannot be guaranteed or inspection failure cannot be separated from a valid missing-service result.
- Stop if existing audit security boundaries would need to be weakened.
- Stop if the only available verification path would execute on the production runner or requires manual workflow dispatch.

## Side-effect authorization

### Explicitly authorized side effects

- Create a new branch from the stated baseline; commit and push the validated task and bounded implementation; create/update a Draft PR; allow its normal GitHub-hosted PR checks to run; record reviewable execution evidence.
- Do not merge, dispatch a workflow, contact the production runner, change production, or approve a release.

## Expected terminal outcome

Review Required — Production Diagnostic Not Executed. Return the exact task
publication revision, implementation SHA, Draft PR URL, changed files, observed
hosted CI results, evidence of no production workflow run, and remaining live
service/ingress unknowns for independent review.
