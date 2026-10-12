# MPIPS Release Distribution Phase B1 — Execution Evidence

## Review state

**Review Required.** The Executor does not self-approve this implementation or
authorize production release activity.

## Governing task and baseline

- Task: `.agents/tasks/mpips-release-distribution-phase-b1.md`
- Immutable validated task revision: `945680560694413d70b8897b0315dee6678e29f6`
- Implementation baseline: `05ba0f44df9004d09d6cc3438519bbe674750725`
- Feature branch: `feat/mpips-release-distribution-b1`
- Implementation under verification: `f8d892b1c70f74f31fc41b52e7ccb7090cffd6c1`
- Baseline is the clean `main` commit after PR #6 was merged. The Phase A review
  remains Review Required as recorded in its own evidence.

## Reconciliation changes

- Added a standard-library HTTP reference server bound only to `127.0.0.1`;
  it stores create-only package/metadata/signature files, verifies signed
  releases through the existing `runtime_release.verify`, simulates distinct
  in-memory roles, and atomically updates a channel pointer with its history.
- Added a publisher with offline `dry-run`, explicit loopback-only staging and
  separate compare-and-swap promotion. Credentials come from environment
  variables; there is no remote publishing implementation.
- Added synthetic integration coverage for signed lifecycle, exact metadata and
  signature snapshots, role boundaries, partial/tampered/oversized input,
  collisions, sanitized errors, offline dry-run, loopback restriction, replay
  and concurrent promotion.
- Extended Ubuntu qualification lint inputs and documented the exact local
  reference routes, limits, errors, steps, and production boundaries.
- No dependency, `pyproject.toml`, `uv.lock`, clinical API, converter, image,
  calibration, deployment workflow, or runtime behavior change.

## Changed files

- `.agents/tasks/mpips-release-distribution-phase-b1.md` — immutable task
  publication only; its approved contents were not subsequently rewritten.
- `.agents/evidence/mpips-release-distribution-phase-b1.md` — this evidence.
- `scripts/release_reference_server.py`
- `scripts/publish_runtime.py`
- `tests/test_release_distribution.py`
- `.github/workflows/qualify-ubuntu-runtime.yml`
- `docs/integration/ubuntu-grabber.md`

## Local verification

Environment: Ubuntu 26.04 LTS, CPython 3.12.14, x86_64, glibc 2.43.

| Check | Result |
|---|---|
| `uv lock --check` | Passed; 116 packages resolved; lock unchanged |
| Main CI API runtime locked audit closure | Passed: no known vulnerabilities |
| Main CI NPZ worker locked audit closure | Passed: no known vulnerabilities |
| Main CI CI/test locked audit closure | Passed: no known vulnerabilities |
| Ubuntu runtime locked audit closure | Passed: no known vulnerabilities |
| Focused distribution and release verifier tests | Passed: 29 passed |
| Full `uv run pytest -q` | Local workspace: 924 passed, 2 skipped, 2 retired-package boundary tests failed because ignored stale `.pyc` files remain beneath `mpips/engine`; no tracked source exists there, and those unrelated ignored files were preserved. The clean GitHub checkout passed the full suite. |
| Ubuntu runtime Black check | Passed; 162 files unchanged |
| Ubuntu runtime Flake8 check | Passed |
| Mypy regression gate vs baseline | Passed: 0 new diagnostics, 2 reduced (`200` baseline, `198` candidate) |
| Protected converter | Passed; SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0` |
| `git diff --check` | Passed |

The focused tests also confirmed that dry-run opens no HTTP connection and that
the loopback publisher can stage all three verified artifacts without leaking
the test token. No real keys, patient data or external services were used.

## Ubuntu installed runtime qualification

Command:

```bash
uv run --with pip==26.2.1 python scripts/build_runtime.py \
  --commit f8d892b1c70f74f31fc41b52e7ccb7090cffd6c1 \
  --sequence 1 --output /tmp/mpips-phase-b1-runtime
```

Result: passed on the local Ubuntu 26.04 host. The candidate built from the
committed revision, installed into a fresh venv from the local wheelhouse with no
package index, and the installed CLI passed the synthetic BED and TRX DICOM
smoke. The output remained under `/tmp`; no binary artifact was published.

## GitHub and side-effect status

- Draft PR: [#8](https://github.com/Madeena-software/mpips/pull/8), based on
  feature revision `371e7529352344f70f72899d8ffc24ac14c31153`.
- GitHub CI: both required workflows passed on the clean PR checkout. Main CI
  run [38245110865](https://github.com/Madeena-software/mpips/actions/runs/38245110865)
  passed all three dependency audits, converter hash, Black, Flake8, mypy,
  full pytest, both Docker builds, and its container smoke. Ubuntu qualification
  run [38245110837](https://github.com/Madeena-software/mpips/actions/runs/38245110837)
  passed dependency audit, source checks, mypy, full pytest, offline package
  install and installed synthetic BED/TRX DICOM smoke.
- Production deployment, production service mutation, external binary upload,
  merge to `main`, and self-approval: none performed.

## Remaining review items

- Independent review of the code and exact task compliance.
- Confirm clean GitHub checks; distinguish those from the two local failures
  caused by ignored workspace bytecode cache residue.
- Production infrastructure, licensing, signing-key, clinical and detector
  approvals remain out of scope and unresolved as explicitly deferred by the
  governing task.

## PR #8 P1 cross-target verification remediation

**Review status: Review Required.** This bounded remediation does not modify the
immutable validated task at revision `945680560694413d70b8897b0315dee6678e29f6`.

- Remediation commit: `96c84320df37c2d5442b8534d5bca47fa2ab8459` on
  `feat/mpips-release-distribution-b1`.
- The shared verifier now separates structural compatibility-field validation
  from host matching. Its default still enforces the local Ubuntu, Python, CPU
  and glibc contract for consuming Grabbers. The reference server opts out of
  host matching only; signature, schema/interface, expiry, sequence, immutable
  identity, and package filename/size/hash checks remain in the shared verifier.
- Qualification rejects signed malformed compatibility and expired metadata;
  tampered metadata/signatures and package bytes are rejected. Promotion checks
  the authenticated declared target against the requested channel target.
- Cross-target regression: on Ubuntu 26.04, the local reference server
  qualified, approved, published and promoted a signed Ubuntu 24.04 release;
  promotion under the server's Ubuntu 26.04 target returned `404`, and the
  default consumer verifier rejected installation with
  `Incompatible runtime target`.
- Focused release verifier/distribution tests: `33 passed`.
- Full local `uv run pytest -q`: `927 passed, 2 skipped, 2 failed`. Both failures
  are the existing `test_engine_calibration_surfaces_are_retired` and
  `test_engine_package_is_physically_retired` checks, which detect ignored stale
  `.pyc` files under `mpips/engine`; no such tracked source was added or changed.
  The new test was separately included in the 33 passing focused tests.
- `uv lock --check`: passed (116 packages). API runtime, NPZ worker runtime,
  CI/test, and Ubuntu runtime `pip-audit --require-hashes` closures: all passed
  with no known vulnerabilities. No lock or dependency floor changed.
- Black, Flake8, `git diff --check`, and the mypy regression check passed;
  mypy reported 0 new diagnostics and 2 reduced. Protected converter SHA-256
  remains `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Installed runtime qualification built from the committed remediation SHA on
  Ubuntu 26.04 / CPython 3.12.14 / x86_64 / glibc 2.43, installed from the
  offline wheelhouse, and passed installed synthetic BED and TRX DICOM smoke
  tests. Output stayed in `/tmp`; no binary was published.
- GitHub checks passed on PR #8 head `13405bff0111aad16255f386618b7c46a7281cde`:
  [MPIPS CI run 38248835521](https://github.com/Madeena-software/mpips/actions/runs/38248835521)
  passed all locked audits, source/converter checks, mypy, full pytest
  (`930 passed, 2 skipped`), both Docker builds and container smoke;
  [Ubuntu qualification run 38248835520](https://github.com/Madeena-software/mpips/actions/runs/38248835520)
  passed audit, source checks, full pytest, offline install and installed
  synthetic BED/TRX DICOM smoke. No production deployment, external binary
  publication, PR merge, or self-approval occurred.

Files changed for this remediation: `scripts/runtime_release.py`,
`scripts/release_reference_server.py`, `tests/test_release_distribution.py`,
`docs/integration/ubuntu-grabber.md`, and this evidence file.

## Post-merge acceptance-record reconciliation

The repository owner supplied the following acceptance history in the Phase B2
planning request: an independent ChatGPT review accepted PR #8 at head
`916f19d6415820110116eb5910cbe55a366d5753`. This statement is the acceptance
source for Phase B1; it is not represented as a formal GitHub review.

Observed GitHub state on 2026-10-12: PR #8 is merged at
`0805fd974d19b07553a784923c457ff4c6b4a703`, its head is the reported review
revision, both required checks succeeded, and the GitHub review list is empty.
The historical `Review Required` labels above describe the pre-merge Executor
evidence and are stale as a current lifecycle status. The immutable B1 task was
not changed. This reconciliation records the owner-reported independent review
separately from the observable PR merge and check history; it does not invent a
GitHub approval event.
