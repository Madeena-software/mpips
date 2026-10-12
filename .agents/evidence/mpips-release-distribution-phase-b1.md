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
