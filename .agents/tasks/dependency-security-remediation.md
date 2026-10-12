---
title: MPIPS locked dependency security remediation
version: 1.0
status: Validated/Published
language: en-US
---

# Executable task

## Task identity and delivery context

Task path: `.agents/tasks/dependency-security-remediation.md`.
Objective: remove current known vulnerabilities from all three hash-locked
closures audited by MPIPS main CI, without changing application behavior or
weakening its audit gate.

## Baseline and governing revision

Implementation baseline: `d645662cd9368c7ba59d9e89a7b033fc3da535b9` (verified
`origin/main` on 2026-10-12).
Task revision: this file at its immutable publishing commit, reported with the
implementation evidence.

## Authority and observed evidence

- Human request: **Codex — MPIPS Dependency Security Remediation**, 2026-10-12;
  it authorizes a dedicated feature branch from verified `main`, task and
  implementation commits/pushes, necessary development dependency installation,
  and a Draft PR. It prohibits direct main pushes, merge, deployment, production
  workflow dispatch, Madeena Server changes, binaries, and RSKIA access.
- Repository policy: `AGENTS.md`, `.agents/AGENTS.md`, and
  `.agents/software-workflow.md`.
- Current CI evidence: run `38225861045`, job `114733081347`, at PR #6 commit
  `258a3246fb2c0eeb7827f6bd5b9830d7ab234cb6`. Its existing audit failed on 19
  findings in `anyio 4.13.0`, `urllib3 2.7.0`, and `pyjwt 2.13.0` in the API
  closure.
- Independent current locked-closure audit at the implementation baseline,
  using the same exported, hashed lock requirements and pip-audit 2.10.1:
  API: 19 findings in those three packages; worker: no findings; CI/test: 20
  findings, the same 19 plus `werkzeug 3.1.8` (`CVE-2026-102598`).
- Current PyPA/OSV advisory records confirm fixes: AnyIO 4.14.2,
  urllib3 2.8.0, PyJWT 2.15.0 (including later advisories beyond the 2.14.0
  fixes), and Werkzeug 3.1.9. Sources: OSV records `PYSEC-2026-4025`,
  `PYSEC-2026-4177`, `PYSEC-2026-4141`, and `CVE-2026-102598`.
- PR #6 is open as a Draft and its implementation is awaiting independent
  review. This work is parallel and based on `main`; avoid its branch and do
  not alter its files. Its `pyproject.toml` adds a build requirement, so
  reconcile that file-level overlap during PR review/integration.

## Objective and scope

### In scope

- Raise every existing PyJWT declaration in `pyproject.toml` to `>=2.15.0`.
- Add uv `constraint-dependencies` for transitive AnyIO `>=4.14.2`, urllib3
  `>=2.8.0`, and Werkzeug `>=3.1.9`; constraints must not introduce a package
  into closures that do not otherwise require it.
- Regenerate `uv.lock` using selective package upgrades only as needed to
  resolve those constraints, preserving all unrelated locked versions where
  possible.
- Audit all three exact closures used in `.github/workflows/ci.yml`:
  API (`service`), worker (`imager` + `npz-worker`), and CI/test (`service` +
  `dev` + `npz-worker` + `calibration`).

### Out of scope

- Any CI gate, audit command, severity policy, advisory, or dependency closure
  suppression, skip, disable, or weakening.
- Runtime/application source, API contracts, DICOM conversion, image processing,
  calibration, metadata, isolated execution, or tests unless observed behavior
  demonstrates a compatibility risk from these package updates.
- `mpips/conversion/tiff_json_to_dcm.py` (protected; do not modify).
- Other dependency refreshes, unrelated advisory remediation, PR #6 changes,
  merge, deployment, release, production systems, or external infrastructure.

## Preserved behavior and constraints

- Preserve all API, DICOM, clinical metadata, image-processing, calibration,
  and isolated-execution behavior.
- Do not suppress or bypass any dependency audit. Keep hash-locked requirements.
- Use the smallest compatible patched versions and do not upgrade unrelated
  lock entries without resolver necessity.
- Do not modify the protected converter.
- Stop and return to planning if a fix requires an API, architectural, runtime,
  or scope change, or if relevant compatibility cannot be established.

## Acceptance criteria

- [ ] PyJWT direct declarations and uv transitive constraints require the
  patched minimum versions listed above.
- [ ] `uv.lock` is valid, consistent with declarations, hash-locked, and has no
  unnecessary unrelated package upgrades.
- [ ] Current pip-audit against each of the three hash-locked exported closures
  reports no known vulnerabilities; no audits are skipped or weakened.
- [ ] Relevant existing tests and checks pass, or any baseline/unrelated
  failures are reported separately with observed output.
- [ ] No application source or protected converter changed; no image-processing,
  API, DICOM, metadata, calibration, or isolation behavior changed.
- [ ] A dedicated branch is based on the stated `main` baseline. A Draft PR
  targets `main`; no merge or production action occurs.

## Verification requirements

- `uv lock --check` and inspect the lockfile diff.
- Run the unchanged three-closure hash-locked `pip-audit` gate from
  `.github/workflows/ci.yml` and confirm all closures are audited.
- Run the existing full pytest suite, mypy, Black check, and Flake8 per project
  conventions; distinguish known baseline failures.
- Verify protected converter SHA-256 remains
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Run the repository CI on the Draft PR and report observed status separately
  from local checks.

## Stop conditions

- Any required API, architecture, image-processing, DICOM, metadata, calibration,
  isolation, or clinical-invariant change.
- Any new material compatibility risk that cannot be covered within this
  dependency-only task.
- Any request to suppress audit findings or weaken the CI gate.
- Any unexpected production or external-system mutation requirement.

## Explicitly authorized side effects

- Create `fix/mpips-dependency-audit` from the verified main baseline.
- Commit and push the task publication and bounded implementation to that branch.
- Install necessary development dependencies in the isolated development
  environment.
- Open a Draft PR targeting `main`.

No commit or push to `main`, PR merge, deployment, production workflow dispatch,
Madeena Server modification, binary publication, or RSKIA access is authorized.

## Expected outcome

Return **Review Required** with the exact task revision, baseline SHA,
implementation SHA, branch, Draft PR URL, package versions before/after,
advisories resolved or remaining, exact commands and observed results, GitHub CI
status, risks, and confirmation that no production deployment or merge occurred.
Independent ChatGPT review owns acceptance.
