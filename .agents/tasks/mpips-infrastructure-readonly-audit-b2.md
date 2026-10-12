---
title: MPIPS production infrastructure read-only inventory (Phase B2)
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS production infrastructure read-only inventory (Phase B2)
**Task path:** `.agents/tasks/mpips-infrastructure-readonly-audit-b2.md`
**Task contract state:** Validated/Published
**Delivery objective / Work Package:** Phase B2 — manually dispatched, public-log-safe infrastructure inventory
**Owner / designated planning authority:** Repository owner; human-supplied Phase B2 request

## Delivery context

Add a manually dispatched GitHub Actions workflow that classifies a small set of
host, Docker, filesystem, service, network, and local-port indicators on the
existing production runner. This determines which infrastructure facts remain
unknown before a proposed future MPIPS Release Service is considered. The
workflow is not a capacity certification, a Release Service design, or release
approval.

## Baseline and task revision

**Implementation baseline:** `0805fd974d19b07553a784923c457ff4c6b4a703`
**Task revision:** this file @ exact publication commit recorded by the Planner

The baseline is current `origin/main` at task creation. Phase B1 acceptance
history was reconciled in `.agents/evidence/mpips-release-distribution-phase-b1.md`:
the repository owner reported independent ChatGPT acceptance at PR #8 head
`916f19d6415820110116eb5910cbe55a366d5753`; GitHub confirms merge commit
`0805fd9…` and successful checks, but has no formal review entries. The
immutable Phase B1 task was not changed.

## Objective

Implement the safe inventory workflow and concise operator guide described by
the human-supplied Phase B2 request. The workflow must run only by manual
dispatch on `main`, run on `[self-hosted, production]`, perform read-only local
inspection, and emit only fixed coarse classifications or `unknown`.

## Authoritative inputs

### Governing authority

- Human-supplied “Codex — MPIPS Phase B2: Safe Production Infrastructure Inventory Workflow” request in this session.
- `AGENTS.md`, `.agents/AGENTS.md`, and `.agents/software-workflow.md`.
- `.agents/tasks/ubuntu-grabber-runtime.md`, `.agents/evidence/ubuntu-grabber-runtime.md`, `docs/integration/ubuntu-grabber.md`.
- `.agents/tasks/mpips-release-distribution-phase-b1.md`, `.agents/evidence/mpips-release-distribution-phase-b1.md`.
- `.github/workflows/deploy-internal-beta.yml`, `.github/workflows/verify-internal-beta.yml`, `docker-compose.prod.yml`.
- GitHub Actions workflow concurrency documentation: <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency>.

### Requirement traceability

- `B2-MANUAL` → human request §§3, 7, 9: manual-only dispatch, `main` guard, production labels, no production-runner development checks, authorized feature-branch PR.
- `B2-READONLY` → human request §§4, 6: bounded local read-only measurements; no state-changing host, Docker, network, package, service, deployment, or clinical operation.
- `B2-LOG-SAFETY` → human request §5: allowlisted coarse output only, captured command output, generic unknown on errors, no raw artifacts or credentials.
- `B2-SERIALIZATION` → human request §3: assess existing concurrency; never cancel active production work; do not replace pending runs.
- `B2-DOCS` → human request §8: explain coverage, limits, security review, separate dispatch authorization, categories, unresolved facts, and proposed architecture status.
- `B2-VERIFY` → human request §7: static and synthetic checks, graceful missing-command behavior, public-log and side-effect checks, and no production dispatch.

## Scope

### In scope

- `.github/workflows/audit-infrastructure-readonly.yml`: a manual-only workflow guarded to `refs/heads/main`, running on `[self-hosted, production]`, with a five-minute maximum, minimal token access, no secrets, no downloaded scripts or third-party Actions, and no uploads.
- `scripts/audit_infrastructure_readonly.py`: bounded read-only collection and allowlisted category output for OS compatibility; CPU and RAM capacity; root/runtime disk capacity and near-capacity status; current load; Docker/Compose availability; coarse running-container count; expected MPIPS services/networks; local ports 8014/80/443; aggregate service health when available; and ingress/network conflict status.
- `tests/test_infrastructure_readonly_audit.py`: synthetic command-output and static workflow safety checks; no production host access.
- `docs/integration/infrastructure-readonly-audit.md`: concise dispatch and interpretation guide with limits and authorization boundary.

### Out of scope

- Dispatching this workflow, contacting or testing the production runner, production host changes, deployment, merge, or release.
- Changes to deployment/verification workflows, runner settings, GitHub settings, secrets, Docker services, network configuration, firewall, TLS, DNS, or ingress.
- Selecting or reserving a future Release Service subnet, or asserting that an ingress is approved. Report `unknown` until an owner-approved candidate and ingress identity exist.
- Installing packages, changing runner software, third-party Actions, external downloads, raw inventory artifacts, public/external probes, load tests, clinical requests, conversions, or patient-record access.
- Complete host-capacity certification, peak-load qualification, or a production Release Service.

### Preserved behavior

- Existing deployment and verification workflows, services, networks, host files, and runner configuration remain unchanged.
- Workflow output contains only sanitized classifications; command output and detailed errors stay in process memory.
- The new workflow never cancels or replaces another production workflow.
- The proposed Compose Release Service remains a proposal, not an approved architecture or deployment.

## Dependencies and assumptions

### Dependencies

- Existing runner has standard Linux inspection utilities and Docker CLI when available; missing or failing commands produce `unknown` classifications.
- GitHub-hosted static/synthetic verification is available, but production runner access is not needed.

### Approved assumptions

- The repository is public; all workflow logs and summaries are public.
- Existing production workflows share `mpips-internal-beta`. GitHub's default concurrency behavior replaces an existing pending run; because changing those existing workflows is outside scope, this audit uses a separate non-canceling audit queue and documents that it does not serialize against deployment/verification runs.
- Candidate Release Service network ranges and an approved HTTPS ingress are not established by current repository authority; the workflow reports these as unknown.

### Remaining approval requirements

- A separate explicit human authorization is required before the first manual dispatch.
- Independent review is required before merge. No merge, dispatch, or production approval is authorized by this task.

## Execution constraints

- Start from `0805fd974d19b07553a784923c457ff4c6b4a703` on a new feature branch.
- Do not run any workflow on `[self-hosted, production]` during development or review.
- Commands executed by the workflow must use fixed arguments, bounded timeouts, captured stdout/stderr, and sanitized parsing. Use a minimal process environment; do not inherit host secrets, Docker context overrides, or credential paths.
- Do not print IPs, hostnames, MACs, usernames, process command lines, Docker IDs/names/configuration, environment variables, paths, exact filesystem inventories, exception text, or raw command output.
- Do not access environment/credential files, Docker logs, patient data, or external hosts. Do not perform Docker mutations, package operations, or filesystem writes.
- Keep execution below five minutes; do not use `set -x`; do not upload logs or artifacts.
- A workflow checkout is permitted only if justified to run the reviewed repository sanitizer; use GitHub's pinned first-party checkout action, `contents: read` only, and `persist-credentials: false`.
- Use an audit-only concurrency group with queueing and no cancellation. Do not join `mpips-internal-beta`, since that existing group can replace pending production runs.

## Acceptance criteria

- [ ] Workflow trigger is only `workflow_dispatch`; job-level condition requires `github.ref == 'refs/heads/main'`.
- [ ] Job uses `[self-hosted, production]`, timeout is at most five minutes, and permissions are limited to `contents: read` solely for the pinned checkout (or narrower if implemented without checkout).
- [ ] No production secrets, external script downloads, third-party Actions, package installs, artifacts, or automatic triggers are present.
- [ ] Concurrency cannot cancel active or pending existing production jobs; audit runs serialize only with other audits.
- [ ] Measurements use local read-only commands, return only the documented coarse categories/aggregates or `unknown`, and never emit raw command output or exception details.
- [ ] Candidate network conflict and approved HTTPS ingress return `unknown` absent explicit owner-approved values/configuration.
- [ ] Documentation explains coverage, deliberate exclusions, public-log sanitization, review steps, separate dispatch approval, category thresholds, unknown facts, proposed architecture status, and no-certification/no-deployment limits.
- [ ] Existing production workflows and Compose configuration are unchanged.
- [ ] Feature branch is based on the implementation baseline; a Draft PR is opened for independent review. No merge or dispatch occurs.

## Verification requirements

- Run focused synthetic tests with mocked command outputs, including sensitive-looking values and missing/failed commands.
- Run workflow static checks for dispatch-only trigger, main guard, runner, permissions, timeout, action pinning, concurrency safety, no credentials, no forbidden mutations, no raw output/artifacts, and no changes to existing production workflow boundaries.
- Run relevant formatting/lint and `git diff --check` checks if required by repository conventions.
- Do not run or dispatch any production workflow. Report exact commands and observed results.

## Stop conditions

- Stop if implementation needs a production workflow change, secrets, host configuration, Docker/network mutation, external probe, patient data, deployment, or architecture decisions beyond the approved request.
- Stop if safe sanitization cannot be demonstrated, a command's output cannot be reduced to an allowlisted field, checkout cannot be constrained to reviewed `main`, or the five-minute bound cannot be maintained.
- Use `unknown` for unavailable or unapproved infrastructure facts; do not invent ranges or ingress approval.

## Explicitly authorized side effects

- Create a new feature branch from the implementation baseline.
- Publish this validated task, implement and verify the bounded workflow, commit and push the feature branch, and open a Draft PR.
- Do not push `main`, merge, dispatch any production workflow, modify the production server, or change GitHub settings/secrets.

## Expected terminal outcome

Reviewable implementation and evidence on a feature branch with a Draft PR,
ending at **Review Required — Production Audit Not Executed**. Report the exact
task revision, implementation SHA, changed files, checks, sanitization controls,
residual public-log risks, and explicit confirmation that the production runner
was not contacted.
