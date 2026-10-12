# MPIPS B2 Operational Evidence Closure — Execution Evidence

## Review state

**Review Required — Production Diagnostic Not Executed.** This record is
execution evidence only; it is not independent acceptance or release approval.

## Governing task and baseline

- Task: `.agents/tasks/mpips-b2-operational-evidence-closure.md`
- Immutable validated task revision: `2ce1b91cdee682dc36dbdfd9763378bad3eb5cb6`
- Implementation baseline: `bfe5237f86a4a535c76c9368099a65e0b1fad653`
- Feature branch: `feat/mpips-b2-operational-evidence-closure`
- Draft PR: [#10](https://github.com/Madeena-software/mpips/pull/10)
- Implementation revision verified by CI: `c06ac51b509f0cfd3fda2cabbd178adca9784906`

## Initial audit analysis

The prior run was `38265842527`, a successful manual `workflow_dispatch` on
`main` at `bfe5237f86a4a535c76c9368099a65e0b1fad653`. Its sanitized output
reported expected services `missing`, aggregate health `healthy`, and ports
8014/80/443 `unknown`; host resource categories were promising, not a capacity
certification. No inference about actual service availability follows from
those categories.

At the audited source revision, service presence came from running containers
with the expected Compose project label and service labels, while aggregate
health came from every running container with the project label. Since the
queries did not restrict health to the expected API and Redis services, a
healthy unrelated project container could satisfy aggregate health while an
expected service label was missing. This explains how those two output labels
could coexist; it does not prove whether a service was down or the collector
misidentified live state.

The old listener parser processed all rows from one host-wide `ss -H -ltn`
result and validated each row before testing its port. An unrelated malformed
row could therefore make all three target results unknown. The implementation
now scopes each query to one TCP port and ignores a parseable non-target row;
malformed target evidence remains unknown.

## Implementation and verification

Implementation is in Draft PR #10 at code revision
`c06ac51b509f0cfd3fda2cabbd178adca9784906`. No local tests, lint, or mypy
checks were run. The installed Black formatter was used to format the changed
Python files; formatter validity was established only by GitHub-hosted CI.

Changed files:

- `.agents/tasks/mpips-b2-operational-evidence-closure.md`
- `.agents/architecture/adr-mpips-b2-operational-questions.md`
- `.agents/evidence/mpips-b2-operational-evidence-closure.md`
- `.github/workflows/qualify-ubuntu-runtime.yml`
- `docs/integration/infrastructure-readonly-audit.md`
- `scripts/audit_infrastructure_readonly.py`
- `tests/test_infrastructure_readonly_audit.py`

Final checks on implementation revision `c06ac51b509f0cfd3fda2cabbd178adca9784906`:

- [MPIPS CI run 38268382206](https://github.com/Madeena-software/mpips/actions/runs/38268382206): passed dependency audits, protected converter hash, Black, Flake8, mypy regression, full pytest (`973 passed, 2 skipped, 302 warnings`), both Docker builds, and the CI container smoke test.
- [Ubuntu qualification run 38268382232](https://github.com/Madeena-software/mpips/actions/runs/38268382232): passed dependency audit, Black, Flake8, mypy regression, offline package installation, and installed synthetic BED/TRX DICOM smoke.
- Earlier hosted attempts caught Black formatting and one Flake8 line-length issue; these were corrected before the passing runs above.

The PR evidence-only update may produce a newer head SHA; its CI status is
reported from the current Draft PR checks separately. No local test suite or
local lint/type-check command was run.

## Production and side-effect status

- No production workflow was dispatched or run during this task.
- The production runner was not contacted.
- No container, service, network, deployment, or production configuration was
  changed.
- The one-time authorization for prior run `38265842527` was not reused.
- No merge or self-approval occurred.
- Read-only Actions metadata after this task began showed no new audit,
  deployment, or verification workflow run. The only listed audit dispatch is
  the earlier run `38265842527`; the latest listed deployment/verification
  runs predate this task.

## Remaining live questions

Whether the expected API and Redis services are present, stopped, absent, or
misidentified remains unknown until a separately authorized diagnostic or
authoritative owner-provided evidence. Ownership and approval of HTTPS ingress,
listener ownership, and candidate network ranges also remain unresolved. The
Draft ADR records these questions; the separate single-server Compose Release
Service remains a proposal, not an approved deployment.

## Required next steps

- Independent review of the exact PR revision and CI evidence.
- After review and merge, obtain new explicit owner authorization for any
  diagnostic dispatch and verify no production deployment or verification
  workflow is active or pending immediately before dispatch.
