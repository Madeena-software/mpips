---
title: Ubuntu Grabber local runtime and release preparation
version: 1.0
status: Validated/Published
language: en-US
---

# Executable task

## Task identity and delivery context

Task path: `.agents/tasks/ubuntu-grabber-runtime.md`.
Planning authority: the human's supplied **Codex Task — MPIPS Ubuntu Grabber
Integration and Distribution**, sections 1–10 (2026-10-12).
Delivery mode: Work-Package-oriented; one coherent developer handoff for an offline
local runtime and repository-side distribution preparation. This task does not
complete production distribution or confer implementation acceptance.

## Baseline and governing revision

Implementation baseline: `d645662cd9368c7ba59d9e89a7b033fc3da535b9`.
The exact governing revision is the immutable Git commit first publishing this
file, resolved through `git log --diff-filter=A --format=%H -- this-path` and
reported in the execution evidence; the body does not embed its own commit SHA.
Execution begins only after that commit is observed and pushed to the feature
branch. Preserve this contract unchanged during execution.

## Objective and authority

Provide a tested offline CLI over `convert_npz_to_dicom`, an offline-installable
versioned wheelhouse candidate, safe release metadata/signature tooling and CI
qualification, and one complete Grabber/SIMRS handoff. Governing inputs:

- The human request authorizes autonomous implementation, bounded task creation,
  feature-branch commits/pushes and a draft PR, with independent human-arranged review.
- `AGENTS.md`, `.agents/AGENTS.md`, `.agents/software-workflow.md`.
- `THIRD_PARTY_NOTICES.md`, `LICENSES/GPL-2.0.txt`: redistribution remains blocked.
- Existing integration boundaries in `docs/integration/python-import-module.md`,
  `docs/integration/mhcs-dicom-api.md`, package-boundary and import tasks.

Supporting evidence: `mpips/conversion/service.py`, `mpips/api/schemas/dicom.py`,
`pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, protected converter tests.
These establish current implementation, not new product authority.

## Readiness and pending-state assessment

- B0/P1: human sections 1, 3–7 explicitly define actors, local processing, update
  direction, metadata behavior, exclusions, and handoff outcome.
- R2: the source-to-requirement table below records those obligations without
  inventing clinical identifiers or infrastructure decisions.
- A3: additive executable over the established local import boundary; no new
  network service, converter, hospital client, or API deployment changes.
  Packaging technique is bounded executor discretion expressly requested in §3.
- D4: repository-only preparation can proceed independently of release approval.
- T5: semantic readiness checked against the template; immutable publication is
  required before implementation.
- Main/origin main agree at baseline, working tree was clean; PR #5 is observed
  merged at `084639395e7ecada982be72f46a2b8aff8ef79ac`. Its task still says candidate;
  this historical status discrepancy is recorded, not rewritten or self-accepted.
  This additive task uses the human-selected verified main base and preserves
  existing behavior. No pending local execution or review changes were observed.
- Project context's older prohibition on recreating docs is stale relative to
  existing integration documents and the current human's explicit instruction to
  follow existing integration-documentation conventions. Reuse `docs/integration/`.

## Requirements, ownership, and verification

| ID | Human source | Owner / obligation | Verification |
|---|---|---|---|
| GRAB-LOCAL | §3 | MPIPS: CLI accepts NPZ pair, manifest, external calibration; JSON version/status and deterministic exit codes; offline DICOM | Subprocess CLI tests, synthetic BED/TRX DICOM |
| GRAB-PRESERVE | §3,8 | MPIPS: converter bytes, imaging, calibration, API unchanged | Protection, imaging, API regression suites |
| GRAB-BUNDLE | §3,4 | MPIPS: version/commit identified offline wheelhouse with locked wheels, license notices, compatibility metadata | Build, fresh venv offline install and installed CLI conversion |
| GRAB-RELEASE | §4 | MPIPS: immutable package metadata, hash/size, signed metadata verification; configurable publication preparation | Tampered metadata/package, wrong key, compatibility failure tests |
| GRAB-CI | §4,9 | MPIPS: GitHub-hosted qualification without production triggers or external binary upload | Workflow inspection and local equivalent checks; observe CI if available |
| GRAB-SIMRS | §5,6 | Grabber developer: documented LAN response validation and schema mapping; synthetic reference adapter only | Synthetic fixtures, MHCS schema and malformed response tests |
| GRAB-HANDOFF | §7 | MPIPS: discoverable coherent guide, implemented/proposed distinction, offline/update/rollback/privacy/calibration | Reconcile guide with implementation and examples |

## Scope and constraints

In scope: `mpips/runtime.py` and console entry, packaging/release tooling under
`scripts/`, focused tests and synthetic fixtures/examples, additive GitHub-hosted
CI, integration guide/discovery links, execution evidence under `.agents/evidence/`.
Use existing validators and dependencies; packaging tools may download locked
wheels inside this isolated development environment. Prefer an offline wheelhouse
with an explicit system Python prerequisite over speculative bundler/deb support.
Evaluate alternatives in the guide and qualify only observed targets.

Out of scope: real SIMRS HTTP client, Grabber UI/drivers, hardware qualification,
clinical identifier policy decisions, imaging/schema changes, new services,
production workflows/servers, external binary uploads, tags/releases, live
publication, signing-key provisioning or production credentials.

Preserve: all API routes/deployment; converter SHA-256
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`;
16-bit MONOCHROME2, canonical TRX rotation, validation and resource limits.
Use synthetic patient identities only. Do not expose manifest values in errors.
Keep runtime/calibration/config/patient data separate. CLI must prevent overwriting
existing outputs and stage conversion privately before activation of output.

## Dependencies, assumptions, approvals and stop conditions

Python 3.12, existing lock, uv/pip, OpenSSL, local filesystem and GitHub access.
Local verified host is Ubuntu 26.04 x86_64 / glibc 2.43 / Python 3.12.14; it is
not evidence for Ubuntu 24.04. CI may target Ubuntu 24.04 x86_64 as a qualification
candidate, with status clearly recorded. No other Ubuntu/CPU compatibility claim.

Blocking for external release (independent of local preparation): owner licensing
review of combined distribution, infrastructure owner's hostname/authentication/
publication location/network approval, trusted signing-key provisioning, clinical
and hardware qualification. Hospital LAN/address/auth/error/sex-code and accession
policy remain unverified and must be resolved by hospital/clinical owners before
real use. Visit ID is encounter ID, not accession or queue; registration date is
not examination time. Signed update activation remains Grabber responsibility.

Stop affected work for converter changes, required API/imaging/schema mutation,
missing material authority, new architecture outside this boundary, secret
exposure, real-patient fixtures, or unapproved external effects. Continue
independent bounded work where safe. A target failing qualification must not be
labeled supported. No production endpoint may be guessed or contacted.

## Acceptance criteria and verification

- [ ] CLI version and all statuses are JSON; input/runtime/timeout/I/O failures
      have documented exits and sanitized diagnostics; existing output preserved.
- [ ] Real synthetic BED and rectangular TRX CLI conversions validate metadata,
      bit depth and dimensions; no external daemon/network required.
- [ ] Candidate bundle contains locked binary dependencies, MPIPS wheel,
      installation requirements with hashes, source identity and licensing notices;
      fresh venv installs using no index and executes synthetic conversion.
- [ ] Metadata binds version, full commit SHA, size/hash, interface, target and
      qualification state. Signing/verification fail closed on tampering; package
      hash alone is explicitly not authentication. Publication is preparation only.
- [ ] Additive CI has no self-hosted runner, deploy/promotion trigger, secrets or
      package-upload step before licensing approval; existing workflows preserved.
- [ ] Synthetic SIMRS reference example validates envelope, exact requested visit,
      required identity/date fields and approved explicit sex mapping; no HTTP client.
- [ ] Guide covers all §7 topics and unresolved approvals; no production/publication
      or target qualification is claimed without observation.

Required checks: new pytest tests; full existing pytest suite; Black/Flake8 on
mpips/tests/new scripts; existing mypy regression gate against baseline; uv lock
check; bundle build/offline install/installed synthetic smoke; OpenSSL signature
negative tests; diff review (secrets, patient data, production triggers), protected
converter hash. Record failures caused by environment or baseline separately.
CI evidence is additional and must not be conflated with local tests.

## Explicit side-effect authorization and terminal outcome

Human §2,9 authorizes create `feat/ubuntu-grabber-runtime` from baseline, commit
and non-force push task and implementation to that branch, install development
build/test dependencies locally, and open a Draft PR targeting main. No direct main
push, merge, production workflow dispatch, server access, live publication or
external binary upload. Synthetic ephemeral test signing keys may be created only
in temporary test directories and must never be tracked or transmitted.

Return **Review Required** with exact task/baseline/implementation identities,
changed files, commands/results/limitations and draft PR URL. The human's separate
ChatGPT review owns acceptance; no A9 or G10 declaration by this executor.
