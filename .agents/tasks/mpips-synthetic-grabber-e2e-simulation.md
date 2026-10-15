---
title: MPIPS synthetic Grabber end-to-end simulation
version: 0.2
status: Draft
language: en-US
---

# Executable Task

## Task identity

**Task title:** MPIPS synthetic Grabber end-to-end simulation

**Task path:** `.agents/tasks/mpips-synthetic-grabber-e2e-simulation.md`

**Task contract state:** Draft. Semantic readiness is assessed below as satisfied,
but the task is **not** Validated/Published: T5 requires independent review/approval of
this Draft PR and a resolvable immutable governing revision (see Task revision).

**Delivery objective:** Work-Package-oriented maintenance slice: a standalone
functional-test workstream independent of Phase B2 production infrastructure and the
MPIPS API incident. Implementation-only; no release or production effect.

**Owner / designated planning authority:** the human Planner request of 2026-10-15
("MPIPS Synthetic Grabber End-to-End Simulation Planning") and its 2026-10-15
continuation, following the precedent of `.agents/tasks/ubuntu-grabber-runtime.md`
(designated human instruction as B0/P1 authority; source-to-requirement table in the task).

## Delivery context

The accepted Grabber runtime already provides `mpips-runtime convert`, a synthetic
SIMRS reference mapper and a synthetic installed-CLI smoke. No test currently chains
the mapper output through the real CLI to a verified DICOM, nor exercises most
failure paths at the CLI boundary. This task closes those integration gaps with a
fully synthetic, deterministic, offline test, and nothing else.

## Baseline and task revision

**Implementation baseline:**
`1a25609f51ee5ed6b16b175bb387e3e960a5a276` (verified `main`/`origin/main` HEAD on
2026-10-15; working tree clean apart from this Draft). Observed at baseline:
`tests/test_local_runtime.py` + `tests/test_simrs_reference.py` = 26 passed
(`.venv/bin/python -m pytest -q`, local, not CI).

**Task revision:**
resolved when published. Draft placeholder only; **not sufficient for T5**. The Draft
PR commit is a review artifact, not the governing revision. On approval the Reviewer
publishes by committing the status change to `Validated/Published`; the governing
identity is then `<task path> @ <that full commit SHA>`, resolved from Git history.
The Executor MUST NOT begin until that revision is communicated.

## Objective

**Objective:** Add one repository-local, fully synthetic, deterministic, offline test
suite proving the chain mock SIMRS response → patient/visit validation and
manifest build → Grabber-owned capture metadata merge → synthetic radiograph+gain NPZ
and synthetic calibration → real `mpips.runtime convert` subprocess → verified DICOM,
for BED and TRX, plus end-to-end negative cases, with sanitized deterministic evidence.

## Authoritative inputs

### Governing authority

- Human planning request and continuation (2026-10-15), including: fictional data only,
  no hospital/production/release/upload, Drive datasets excluded, no implementation in
  planning.
- `.agents/AGENTS.md`, `.agents/software-workflow.md`, `.agents/prompts/plan-create-task.md`, `.agents/tasks/_template.md`.
- `.agents/tasks/ubuntu-grabber-runtime.md` and its evidence (runtime interface 1, exit codes, GRAB-SIMRS ownership split).
- `docs/integration/ubuntu-grabber.md` (SIMRS mapping, Grabber owns capture/site fields, synthetic qualification), `docs/integration/examples/*.synthetic.json`.

### Supporting evidence (observed implementation; not authority)

`mpips/runtime.py`, `mpips/conversion/service.py`, `mpips/api/schemas/dicom.py`,
`scripts/grabber_smoke.py`, `scripts/simrs_manifest_example.py`,
`tests/test_local_runtime.py`, `tests/test_simrs_reference.py`,
`tests/api/test_dicom_conversion.py`, `.github/workflows/ci.yml` (`uv run pytest -v`).

### Requirement traceability

| ID | Obligation (source: human request §Planning requirements) | Verification |
|---|---|---|
| E2E-SYN-DATA | Only fictional identifiers/metadata; no network | Provenance assertions, socket guard |
| E2E-SIMRS | Simulated lookup, no hospital contact | Mapper-driven positive/negative tests |
| E2E-ID | Patient and visit/exam identity mapping validated | Positive field assertions; mismatch negatives |
| E2E-INPUT | Matching synthetic radiograph/gain NPZ | Generated inputs, gain-pair checks |
| E2E-CAL | Explicitly synthetic calibration | `SYNTHETIC-*` fingerprint asserted |
| E2E-CLI | Real MPIPS local conversion interface | Subprocess `python -m mpips.runtime convert` |
| E2E-DICOM | DICOM metadata, pixel properties, integrity | DICOM assertions below |
| E2E-MODES | BED and TRX | Parametrized |
| E2E-NEG | Malformed SIMRS, mismatch, invalid manifest, gain mismatch, unavailable calibration | Negative table below |
| E2E-EVID | Deterministic sanitized evidence | Evidence-structure test |

## Readiness assessment (B0–T5)

- **B0 passes (for this bounded objective):** reason, outcome, constraints and exclusions are explicit in designated human instructions; same authority model the repo accepted for `ubuntu-grabber-runtime`. No clinical, hospital or release decision is required.
- **P1 passes:** the behaviour is test/qualification behaviour only; no product behaviour changes. Expected observable outcomes are defined below.
- **R2 passes:** table above gives stable IDs, human source, owner (MPIPS tests), verification.
- **A3 passes:** ownership is already documented: Grabber owns SIMRS access/capture/site fields; MPIPS owns the local converter. Test-only change; no module boundary or trust boundary moves; the mapper intentionally emits identity-only fields (verified in `scripts/simrs_manifest_example.py`).
- **D4 passes:** single coherent objective, no unresolved dependency; independent of B2/API incident (no shared write surface: new test file and a doc section only).
- **T5 is NOT passed:** (a) no immutable governing task revision exists; (b) independent review of this Draft is pending. These are process gates, not content blockers.
- Pending-state: no pending execution/review on this line. Discrepancy recorded, not rewritten: `ubuntu-grabber-runtime` evidence records its PR as candidate/review-dependent with no formal A9 record observed; `.agents/context/project.md` (verified 2026-08-05) predates the Grabber runtime and says not to recreate a root `docs/` while `docs/integration/` exists. This task relies only on the code at the baseline (observed and test-passing), reuses existing `docs/integration/` convention, and does not depend on those records for authority.

### Planner resolutions of technical questions (verified, not owner decisions)

1. *Patient selection/confirmation step:* test-only helper in the test module (candidate list → select by visit → explicit confirmation boolean gating manifest build). Not a product module, no new package. Basis: Grabber owns confirmation (`ubuntu-grabber.md` ownership table).
2. *Manifest composition:* mapper output is identity-only, so the test composes the final manifest by deep-merging mapper output with the Grabber-owned `capture`/`dicom` blocks from `docs/integration/examples/grabber-manifest.synthetic.json` (detector type per mode). Mapper-owned identity fields must not be overridden by the merge.
3. *Calibration legitimacy:* reuse the identity-remap calibration in `scripts/grabber_smoke.py::make_inputs`; already observed to convert BED and TRX through the real CLI (26-passed run). It is labelled `SYNTHETIC-IDENTITY-REMAP`. It proves pipeline plumbing, not geometric-correction accuracy; the evidence must state that limitation.
4. *Sex mapping:* positive path uses `confirmed_sex_codes={}` (sex `unknown`, as the existing positive test); a confirmed-code path may be added only if fixture data stays fictional.
5. *Negative expected codes:* the Executor characterises each failure at the CLI boundary from the observed code in `mpips/runtime.py` (2–7), then asserts that exact code. Where an existing API test already proves the underlying rule, the new test proves only the CLI mapping.
6. *Reuse:* import `make_inputs`/`verify_output` and `build_manifest`; no new framework, fixtures package, or production change.

## Scope

### In scope

- New test module `tests/test_grabber_e2e_synthetic.py` (stable name; Executor may add a small private helper in the same module).
- Positive E2E for BED and TRX; negative E2E per table; determinism and evidence tests.
- A short factual addition to `docs/integration/ubuntu-grabber.md` under "Synthetic end-to-end qualification" describing what the new test covers and that Drive/real data are excluded.

### Out of scope

- Any change to `mpips/`, converter, calibration, API, packaging, workflows, CI config, dependencies, `uv.lock`.
- Real SIMRS, network, production, Release Service, uploads, clinical or real acquisition data of any kind, including the Google Drive collections.
- Real-data compatibility/dataset qualification (separate future Draft task requiring data-use authorization; filename/metadata match does not prove NPZ compatibility).
- Duplicating existing coverage: do not re-add tests already present (mapper negatives, schema field negatives, exit codes 5–7, no-leak for sex, output-exists).

### Preserved behavior

- Existing tests unchanged and passing; protected converter bytes/hash unchanged.
- Runtime interface 1 and exit codes unchanged.

## Dependencies and assumptions

### Dependencies

- Baseline code only; `.venv` with project dependencies. No new dependency.

### Approved assumptions (verified at baseline)

- `convert_npz_to_dicom` accepts a manifest file and an external calibration dir (`mpips/runtime.py`).
- The existing identity-remap calibration converts BED and TRX (observed).
- TRX output shape is transposed relative to BED for the same input (existing `verify_output`).

### Remaining approval requirements

- Independent review/approval of the Draft PR and publication commit before execution.
- Data-use authorization before any real/Drive data is touched (outside this task).
- Merge, release, deployment: not authorized by this task.

## Required capabilities

- Repository read/write; local shell and pytest execution. No network, Graphify or browser required.

## Execution constraints

- Test files must be deterministic: fixed seeds/values, no wall-clock or random UIDs in assertions (compare pixel arrays and stable fields; do not hash whole DICOM files because UIDs/dates may vary, unless observed stable).
- A socket-blocking guard in the test must make accidental network use fail.
- Every identifier written or asserted must start with `SYNTHETIC`; a helper must fail if any other patient identifier appears in inputs or evidence.
- Subprocess runs use the real `python -m mpips.runtime convert`; mocks of the converter are not acceptable in the E2E positive/negative paths.
- Evidence output contains only synthetic values, statuses, shapes and pixel digests; no paths outside temp, no hostnames.
- Black/flake8 (line length 88) and mypy per repository policy.

## Acceptance criteria

- [ ] Positive BED and TRX: mock SIMRS response → confirmed selection → mapper → merged manifest validates with `MHCSManifest` → real CLI exit 0, `status: ok`, empty stderr.
- [ ] DICOM: PatientID, PatientName, BirthDate match the SIMRS-derived values; StudyInstanceUID etc. present; Modality DX; SOP class `1.2.840.10008.5.1.4.1.1.1.1.1`; 16-bit unsigned MONOCHROME2; shape (BED 48×64, TRX 64×48); no private tags; mode `0600`.
- [ ] Pixels and integrity: re-readable by pydicom; `DICM` preamble; pixel array dtype uint16, non-constant, equal to a fixed expected digest, and identical across two runs.
- [ ] Identity chain: examination encounter ID in manifest equals the requested synthetic visit; any other visit yields no DICOM.
- [ ] Negative (each: expected exit code observed and asserted, `status: error`, no output file, no `.mpips-*` residue, no synthetic identifier text in stdout/stderr): malformed SIMRS (non-dict, `success` not true, missing identity) rejected before the CLI; visit mismatch; unconfirmed selection; invalid manifest JSON; schema-invalid manifest; gain id/shape/detector-mode mismatch with the radiograph; missing calibration directory; calibration not validated or wrong shape. Cases already identical to existing CLI tests are not duplicated.
- [ ] Offline/synthetic: the test fails if a socket connection is attempted; provenance helper rejects non-`SYNTHETIC` identifiers.
- [ ] Deterministic evidence: a JSON summary generated twice in one session is byte-identical and contains only the allowed fields.
- [ ] Documentation addition is factual and states limitations (identity calibration, no real data, not clinical qualification).
- [ ] Preservation: all pre-existing tests pass unchanged; only the files in scope changed.

## Verification requirements

### Required checks

- `.venv/bin/python -m pytest -q tests/test_grabber_e2e_synthetic.py tests/test_local_runtime.py tests/test_simrs_reference.py`
- `.venv/bin/python -m pytest -q` (full suite; compare failures with baseline; two pre-existing legacy-directory failures are documented in `ubuntu-grabber-runtime` evidence)
- `black --check`, `flake8`, `mypy` on the new test, per `pyproject.toml`
- `git diff --name-only <baseline>...HEAD` limited to scope; converter SHA-256 unchanged.
- Observe PR CI (`uv run pytest -v`) if available; report local and CI separately.

### Required evidence

The Executor MUST report implementation revision, commands run and exact results, tests added, checks not run, deviations, blockers, and CI status separately from local results.

## Stop conditions

Stop and return to planning if: any change under `mpips/` seems necessary; the mapper and CLI cannot produce a valid DICOM without changing production behaviour; a fixture would need non-synthetic data; a negative case reveals a converter defect (record, do not fix); the baseline is no longer safely applicable; or an unapproved side effect is required.

## Side-effect authorization

### Explicitly authorized side effects

- None by this Draft. After publication, execution authority is limited to creating a feature branch and local changes; commit/push/PR for the execution require the human's or repository policy's explicit authorization at handoff.
- Not authorized: merge, deploy, release, dependency changes, production or external access, real-data handling.

## Expected terminal outcome

Review Required with a reviewable revision and truthful evidence, or Planning Required on a stop condition. The Executor does not self-accept; implementation acceptance is not release.
