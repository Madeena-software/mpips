---
title: MPIPS release distribution Phase B1 reference contract
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS release distribution Phase B1 reference contract
**Task path:** `.agents/tasks/mpips-release-distribution-phase-b1.md`
**Task contract state:** Validated/Published
**Delivery objective / Work Package:** Phase B1 — local release distribution contract and isolated reference implementation

**Owner / designated planning authority:** Repository owner, based on the human-supplied *Codex Task — MPIPS Release Distribution Phase B1* and approved design direction in this session.

## Delivery context

Phase A provides a local `mpips-runtime` CLI, offline candidate wheelhouse builder,
and Ed25519 metadata/signature tooling. It has no release server, uploader, or
promotion mechanism. This task adds an end-to-end, repository-local reference
contract that can be tested with synthetic artifacts and temporary storage. It
does not make decisions for, connect to, or deploy on the Madeena Release Server.

## Baseline and task revision

**Implementation baseline:** `05ba0f44df9004d09d6cc3438519bbe674750725`
**Task revision:** resolved from the immutable commit that publishes this task;
recorded in the execution evidence.

The starting tree was clean `main` at the verified baseline. PR #6 is merged by
the repository owner and its main CI and Ubuntu qualification checks passed. Its
prior evidence still says Review Required and GitHub has no review entries; this
task uses the user-specified main baseline without asserting an independent
review verdict for Phase A.

## Objective

Add and test a versioned local reference protocol for staging, authenticating,
discovering, downloading, approving, publishing, promoting, and rolling back
signed MPIPS runtime releases, plus a repository-side publisher limited to
offline dry-run and explicit loopback testing. Document the tested reference
behavior separately from proposed production responsibilities.

## Authoritative inputs

### Governing authority

- Human-supplied *Codex Task — MPIPS Release Distribution Phase B1* (current session).
- Human-approved B1 design direction (current session): standard-library local
  reference server and publisher; loopback-only networking; no production-capable
  publishing path; isolated local lifecycle simulation.
- `AGENTS.md`, `.agents/AGENTS.md`, `.agents/software-workflow.md`.
- `.agents/tasks/ubuntu-grabber-runtime.md` @
  `d574d8561de7ae6abd428eddb4a0ce1b645c1ebe` and its execution evidence.
- `docs/integration/ubuntu-grabber.md`, `scripts/runtime_release.py`,
  `scripts/build_runtime.py`, `.github/workflows/ci.yml`,
  `.github/workflows/qualify-ubuntu-runtime.yml`.
- Phase A protected converter and API boundaries, including the converter hash
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

### Requirement traceability

- `B1-CONTRACT` → supplied task §§2.A, 2.E: versioned discovery, signed snapshot,
  immutable package identity, lifecycle states, release history and rollback.
- `B1-REFERENCE` → supplied task §2.B: isolated local server, atomic channel
  changes, bounded requests, authenticated role boundaries and fail-closed errors.
- `B1-PUBLISHER` → supplied task §2.C: artifact validation, no-overwrite staging,
  separate promotion, offline dry-run and no automatic/remote publication.
- `B1-CI` → supplied task §2.D: GitHub-hosted contract/regression/security tests,
  audits preserved, and no production triggers, credentials or binary uploads.
- `B1-HANDOFF` → supplied task §2.E: exact examples, operating responsibilities,
  and explicit unresolved Madeena infrastructure decisions.
- `B1-PRESERVE` → supplied task §3: unchanged clinical DICOM/API, image processing,
  calibration, Phase A runtime, dependency floors, audit gates and patient privacy.

## Scope

### In scope

- `scripts/release_reference_server.py`: a minimal Python-standard-library
  reference server bound only to IPv4 loopback, with temporary/local filesystem
  storage and a programmatic start/stop interface for tests.
- `scripts/publish_runtime.py`: dry-run validation and a separately invoked
  publisher for explicit loopback reference-server staging and promotion. Reuse
  `scripts/runtime_release.py` verification rather than duplicating signature,
  compatibility, expiry, sequence, package hash or size rules.
- `tests/test_release_distribution.py`: synthetic signed artifacts and isolated
  temporary server storage; no hospital, external network, real credentials,
  patient data, or production service.
- Extend `.github/workflows/qualify-ubuntu-runtime.yml` with independent
  distribution-contract tests while keeping its GitHub-hosted runner and current
  audit, source, mypy-regression, pytest, and offline BED/TRX qualification gates.
- Extend `docs/integration/ubuntu-grabber.md` with exact reference endpoints,
  payloads, errors, local test steps, publisher dry-run/staging steps, and clear
  reference-versus-production labels.
- Record exact governing task, changed files, checks, results, and limitations in
  `.agents/evidence/mpips-release-distribution-phase-b1.md`.

### Protocol contract for this reference implementation

Version 1 is local-reference-only and uses JSON for control messages and raw
request bodies for uploaded bytes. `release_id` is the signed Phase A metadata
identity; `sequence` is the signed monotonic release sequence. Together they key
one immutable distribution record, allowing a later signed sequence to refer to
previously published package bytes without overwriting an earlier record.

Routes:

| Method and path | Role | Behavior |
|---|---|---|
| `PUT /v1/staging/{release_id}/{sequence}/metadata` | publisher | Stage exact signed metadata bytes; create-only |
| `PUT /v1/staging/{release_id}/{sequence}/signature` | publisher | Stage the 64-byte detached Ed25519 signature; create-only |
| `PUT /v1/staging/{release_id}/{sequence}/package` | publisher | Stream package bytes to bounded temporary storage; create-only |
| `POST /v1/staging/{release_id}/{sequence}/qualify` | local test qualifier | Record a synthetic qualification result only after complete package verification |
| `POST /v1/staging/{release_id}/{sequence}/approve` | local test approver | Record a distinct simulated approval; never accept an approval-reference string as proof |
| `POST /v1/staging/{release_id}/{sequence}/publish` | publisher | Make the verified, approved distribution record available immutably |
| `GET /v1/releases/{release_id}/{sequence}` | reader | Return lifecycle state plus exact metadata and signature as base64 in one JSON snapshot |
| `GET /v1/releases/{release_id}/{sequence}/package` | reader | Stream only the package verified against that metadata snapshot |
| `GET /v1/channels/{channel}/{target}` | reader | Return the current channel pointer and matching metadata/signature snapshot |
| `GET /v1/channels/{channel}/{target}/history` | reader | Return append-only promotion history for that channel/target |
| `POST /v1/channels/{channel}/{target}/promote` | local test promoter | Atomically promote an approved published record using expected-current sequence compare-and-swap |

Every response includes a versioned JSON error envelope for control failures:
`{"schema_version":1,"error":{"code":"...","message":"..."}}`.
Error messages MUST be fixed/sanitized and MUST NOT echo tokens, request bodies,
metadata contents, paths, or patient information. Success responses include
`schema_version: 1` and a reference-only mode marker. A channel snapshot contains
the base64-encoded exact metadata bytes and detached signature together, avoiding
the metadata/signature race in the earlier two-request proposal.

Path identifiers are restricted to safe ASCII slugs; `release_id` must also
match the signed metadata exactly. Sequence is a positive decimal integer with
no sign or leading zero. `target` is exactly
`ubuntu-{os_version}-{architecture}-py{python}`, for example
`ubuntu-24.04-x86_64-py3.12`; the metadata compatibility object remains the
source of truth and must map to that identifier. `channel` is 1–32 lowercase
ASCII letters, digits, or hyphens, beginning with a letter.

Uploads use raw bytes with a required `Content-Length`, not multipart encoding.
Metadata is limited to 64 KiB, the detached signature is exactly 64 bytes, and a
package is limited to 2 GiB. Success for component upload is `201 Created`.
Qualification, approval, publish, and promote requests have an empty body and
return `200 OK` with the resulting state. Promotion's body is the sole exception:
`{"expected_current_sequence": 0}` for an empty channel, or the currently
observed positive sequence. `GET` control routes return `200 OK`; package download
returns raw package bytes with its exact content length. Error status mapping is
`400` malformed request/unsupported transfer encoding, `401` missing or invalid
token, `403` valid token with insufficient role, `404` unknown release/channel,
`409` immutable collision/invalid transition/stale or replayed sequence, `413`
body above limit, and `422` signed metadata/package/compatibility verification
failure. Errors use only fixed messages and codes.

Release and channel `GET` snapshots have this shape (metadata bytes are the
original authenticated bytes, base64-encoded without parsing/reserialization):

```json
{
  "schema_version": 1,
  "mode": "local-reference-only",
  "release_id": "<signed release id>",
  "sequence": 2,
  "state": "promoted",
  "metadata_b64": "<base64 exact metadata bytes>",
  "signature_b64": "<base64 64-byte detached signature>"
}
```

Channel-history returns the same version/mode marker plus an ordered `history`
array of `{release_id, sequence, previous_sequence, promoted_at}` entries. No
patient data or credentials appear in any response. These snapshots are
reference-protocol examples, not a production API contract.

Lifecycle is kept outside the signed Phase A metadata to preserve its schema:
`candidate → qualified → approved → published → promoted`. Qualification,
approval, and promotion credentials exist only as synthetic, in-process test
fixtures. A local `qualified` or `approved` result MUST be clearly marked as
simulated and MUST NOT be described as production approval. The candidate's
existing `synthetic-only` qualification field is never sufficient by itself to
advance a lifecycle state.

Channel promotion MUST be atomic, require a published approved record, require
the caller's expected current sequence to match, and reject a sequence not greater
than the current channel sequence. History records each successful pointer change.
A remote rollback is represented only in this simulation as a separately signed,
higher-sequence distribution record that reuses the known-good package bytes; the
accepted sequence never decreases. No delete, overwrite, or sequence-reset route
is provided.

The server binds to `127.0.0.1` and has no configurable non-loopback bind option.
Role tokens are injected into its test constructor and never persisted or printed.
The publisher reads its local test token from an environment variable rather than
an argument. Plain HTTP is accepted only for literal loopback addresses. The
publisher has no remote HTTPS adapter in this phase; any future remote adapter
requires a new approved task and MUST use HTTPS with certificate verification.

Control-body limit is 64 KiB, signature size is exactly 64 bytes, and package
size limit is 2 GiB. The server requires a declared content length, rejects
unsupported transfer encoding, applies a bounded socket read timeout, streams
packages instead of buffering them in memory, and rejects traversal or malformed
release/channel/target path components. These are reference-server limits, not
production service capacity claims.

### Out of scope

- A production Madeena Release Server, host/storage/network changes, or deployment.
- Any remote publishing/upload adapter, real hostname, token, identity provider,
  TLS certificate, release secret, signing key, or GitHub production environment.
- Production qualification/approval evidence, release sequence allocation,
  retention/audit policy, rollback authorization, or approval-reference semantics.
- Grabber application/client changes, updater, download scheduling, install,
  activation, examination lock, user interface, or hospital integration.
- Changes to the protected converter, DICOM/API/image/calibration behavior,
  patient metadata rules, runtime interfaces, or vulnerable dependency floors.
- External binary publication, release promotion outside the local fixture,
  production workflow triggers, and all real patient data.

### Preserved behavior

- Existing API routes, deployment workflows, converter bytes/hash, DICOM rules,
  image processing, calibration, and Phase A `mpips-runtime` behavior/tests.
- `uv.lock`, all patched minimum dependency versions, and all existing audit gates.
- Phase A metadata schema version 1, signature semantics, and candidate-only status.
- Patient data remains local to the clinical conversion workflow; distribution
  tools accept only signed software-release artifacts and never clinical inputs.

## Dependencies and assumptions

### Dependencies

- Verified clean baseline `05ba0f44df9004d09d6cc3438519bbe674750725`.
- Python 3.12 standard library, OpenSSL and existing Phase A release validator.
- GitHub-hosted Ubuntu runners and the existing lock/audit configuration.
- No production infrastructure or external service is required or contacted.

### Approved assumptions

- The supplied request and approved design authorize an isolated protocol fixture,
  not a production service or production release decision.
- The current signed metadata is trusted only through the existing configured
  Ed25519 public key; uploads cannot provide or replace that trust root.
- The reference server's loopback-only role simulation is test behavior, not a
  proposed production authentication implementation.
- A package may be referenced by more than one signed sequence only when each
  sequence has a distinct immutable metadata/signature snapshot.

### Remaining approval requirements

- Infrastructure owner: production API/path/schema, host, authn/authz, TLS,
  storage, network, audit, sequence, retention, and rollback decisions before any
  production adapter or deployment work.
- Licensing owner: combined distribution assessment before any external binary
  publication.
- Signing-key owner: production key custody, rotation, revocation and trust update
  design before any production signing or client trust changes.
- Clinical/hardware owners: existing Phase A clinical and detector qualification
  gates remain; synthetic tests do not satisfy them.

## Required capabilities

- Repository read/write, local shell, Python/pytest, OpenSSL, Git commit/push, and
  GitHub-hosted PR checks.
- No production, hospital-network, Madeena-server, Grabber-repository, or secret
  access.

## Execution constraints

- No new dependency. Use Python standard library and existing validators.
- Follow established `scripts/`, `tests/`, documentation, and CI patterns.
- Treat all request paths, headers and bodies as untrusted; bound reads before
  writing, use exclusive immutable file creation, and atomic pointer replacement.
- Do not leak credentials or untrusted content to logs/errors. Never use patient
  fixtures or transmit clinical data.
- Ensure no routine commit, PR, merge, or main-branch event can stage, publish,
  approve, promote, deploy, or upload a binary artifact.
- No production endpoint may be inferred from `example.invalid` or existing docs.

## Acceptance criteria

- [ ] The versioned endpoints and payloads match this contract and have discoverable tests/docs.
- [ ] Signed metadata, detached signature, and package must all be present and verify before qualification/publication; incomplete, oversized, expired, incompatible, tampered, conflicting, traversal, and unauthorized requests fail closed.
- [ ] Staged and published release files cannot be overwritten; partial staging is never discoverable as published and is never promoted.
- [ ] Candidate, qualified, approved, published and promoted states are distinct; simulated states are explicitly reference-only and synthetic qualification never constitutes production approval.
- [ ] Channel promotion is atomic, compare-and-swap protected, history-bearing, and rejects replay/downgrade; rollback uses a higher signed sequence over known-good bytes.
- [ ] Channel discovery returns an internally consistent exact-byte metadata/signature snapshot; package delivery is bounded and follows only the immutable release identity.
- [ ] Publisher dry-run performs no network operation; explicit local-test operations require loopback and test credentials; no remote publisher exists.
- [ ] Authentication separates reader, publisher, qualifier, approver and promoter operations; error/log output does not expose credentials, paths, metadata or patient fields.
- [ ] Tests cover allowed lifecycle plus tampering, partial sets, oversize, auth failures, immutable collisions, concurrent/stale promotion, replay/downgrade, offline behavior, and synthetic-only boundaries.
- [ ] Existing MPIPS CI and Ubuntu runtime qualification pass; all three audits remain enabled and clean; new tests run on GitHub-hosted CI.
- [ ] DICOM converter SHA-256 remains the protected value and no clinical/API/image/calibration behavior changes.
- [ ] Documentation clearly distinguishes tested local reference behavior, simulated approvals, and unresolved proposed production decisions.

## Verification requirements

### Required checks

- Focused release-distribution tests, existing `tests/test_runtime_release.py`,
  full pytest suite, Black, Flake8, mypy regression, `uv lock --check`, and all
  three unchanged hash-locked dependency audit closures.
- Existing Ubuntu local runtime qualification including fresh offline installation
  and installed synthetic BED/TRX DICOM smoke.
- Static workflow review for production triggers, self-hosted runners, secrets,
  deployment environments, and binary upload steps.
- Security-focused tests for request-size/path limits, immutable staging,
  credential-role boundaries, exact-byte verification, atomic channel changes,
  concurrency/replay behavior, and sanitized errors.
- `git diff --check`, protected converter hash check, and changed-file review for
  clinical data, secrets, production URLs, and accidental API/deployment changes.

### Required evidence

Report the exact task and implementation revisions, all changed files, executed
commands and results, local versus GitHub evidence, known failures/limitations,
current Draft PR and CI states, and confirmation that no production service or
external binary was changed or published.

## Stop conditions

- A requirement to modify the clinical DICOM API, converter, imaging, calibration,
  patient metadata, or Phase A runtime behavior.
- A need to add a remote publisher, real server endpoint, production auth model,
  signer credentials, CI secrets, binary upload, deployment or promotion.
- Any required decision on production identity, release authority, qualifying
  evidence, retention, or rollback that cannot remain explicitly deferred.
- Failure of an existing security audit or pressure to weaken its gate.
- Any path to real patient data, hospital networking, Grabber repository access,
  or external service mutation.
- A schema change to Phase A signed metadata that lacks an approved migration.

## Side-effect authorization

### Explicitly authorized side effects

- Create a new feature branch from the verified `main` baseline.
- Commit and push the task publication and bounded Phase B1 implementation to
  that branch; open a Draft PR targeting `main`.
- Run local tests and GitHub-hosted PR workflows using existing repository CI.

No direct push to `main`, force push, PR merge, production deployment, real-server
mutation, production credential/key creation, external release publication or
binary upload is authorized.

## Expected terminal outcome

### Review Required

The implementation must return a reviewable branch/PR and observed evidence.
The Executor does not self-declare implementation acceptance or release approval.
