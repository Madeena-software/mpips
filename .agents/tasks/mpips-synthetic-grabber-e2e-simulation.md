---
title: MPIPS synthetic Grabber end-to-end simulation
version: 0.3
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
- Process boundary (observed in `mpips/conversion/service.py`): the CLI process launches a second Python process (`python -m mpips.conversion.worker`) with `env=dict(os.environ)` plus overrides, so environment variables set for the CLI are inherited by that worker. A pytest-process socket monkeypatch does **not** reach either child.

### Remaining approval requirements

- Independent review/approval of the Draft PR and publication commit before execution.
- Data-use authorization before any real/Drive data is touched (outside this task).
- Merge, release, deployment: not authorized by this task.

## Required capabilities

- Repository read/write; local shell and pytest execution. No network, Graphify or browser required.

## Execution constraints

- Test files must be deterministic: fixed seeds/values, no wall-clock or random UIDs in assertions (compare pixel arrays and stable fields; do not hash whole DICOM files because UIDs/dates may vary, unless observed stable).
- **Network prohibition across the subprocess boundary** (stdlib only, test-only, no dependency): the Executor MUST NOT rely on a pytest-process socket patch for child processes. The test supplies the child environment with a temporary directory prepended to `PYTHONPATH` containing a test-generated `sitecustomize.py` that (a) installs `sys.addaudithook` rejecting `socket.connect`, `socket.bind`, `socket.sendto`, `socket.getaddrinfo` and `socket.gethostbyname` events for non-`AF_UNIX` targets (raising an exception), and (b) writes, to guard-record files in a per-run temp directory, a **process-attributable load sentinel** (role-tagged and PID-tagged) and one line per rejected attempt. Process role is determined by the guard from the process's own command line (`mpips.runtime` = `cli`; `mpips.conversion.worker` = `worker`), so the CLI and the worker write separate sentinels.
- **Guard-record scoping by case class** (the worker is spawned only after the CLI's preflight succeeds, per `mpips/runtime.py` and `mpips/conversion/service.py`; the Executor MUST NOT require a worker sentinel where no worker is spawned):
  1. *Pre-CLI failures* (rejected before any CLI launch): no CLI or worker is launched; no sentinels of either role are expected; the guard-record directory must be empty, and the in-process guard (labelled in-process only) must show zero attempts.
  2. *CLI preflight failures* (CLI starts and fails before conversion: for example missing input, missing calibration directory, invalid manifest JSON or schema, as the observed code path dictates): the **CLI sentinel must be present**; **no worker sentinel is expected or required**; zero rejection records.
  3. *Worker-reaching cases* (the CLI reaches `convert_npz_to_dicom` and spawns the worker, including any failure raised inside the worker, such as gain/calibration mismatch if so observed): **both the CLI sentinel and the worker sentinel must be present**, separately attributable by role/PID; zero rejection records. The Executor MUST determine from observation which negative cases fall in class 2 or 3 and record that classification; it must not assume it.
  4. *Required worker-reaching positives:* at least one successful **BED** conversion and one successful **TRX** conversion MUST each assert both sentinels present with distinct PIDs, `status: ok`, and zero rejection records.
- **Canary isolation:** the canary (a separate child with the same guard environment, `python -c` attempting a loopback TCP connect) uses its **own** guard-record directory, distinct from every system-under-test run, and expects the rejected attempt to be **observed** (exception raised and one rejection record). Every system-under-test run uses a fresh, empty record directory and expects **zero** rejection records; canary records must never be reused or counted toward them. If the guard cannot be shown to load in the worker for a worker-reaching case, that is a stop condition, not a silent pass.
- **Record hygiene:** sentinel and rejection records stay in test temp directories and are asserted programmatically; they MUST NOT be printed to stdout/stderr or included in public CI logs. On failure, assertion messages and any evidence may contain only sanitized classifications (for example `guard_loaded:cli`, `guard_loaded:worker`, `rejections:0`, `case_class:cli_preflight`), never PIDs, paths, hostnames, socket targets, or identifiers.
- **Stated limitation (must be recorded verbatim in evidence and docs):** this is Python-level, test-enforced verification, not kernel network isolation. It does not stop non-Python code, `ctypes`/C-extension raw sockets that bypass audit events, or interpreters started without the inherited environment. If the Executor finds a stronger dependency-free option that works unprivileged on the CI runner (for example `unshare -rn`), it MAY add it as an optional extra only when guarded by a capability probe that skips with a recorded reason; it MUST NOT make the task depend on it, and MUST NOT claim a guarantee the probe has not demonstrated.
- **SYNTHETIC identifier scope:** every test-controlled patient identifier (MRN, name), visit/encounter identifier, accession-like value and acquisition/gain/camera identifier written or asserted MUST start with `SYNTHETIC`. A helper fails if any other test-controlled identifier of those kinds appears in inputs or evidence. This does NOT apply to standards-defined or generated DICOM UIDs (SOP Class, Study/Series/SOP Instance UIDs, transfer syntax), which must be validated by DICOM UID syntax (and, for SOP Class, the expected value) instead.
- Subprocess runs use the real `python -m mpips.runtime convert`; mocks of the converter are not acceptable in the E2E positive/negative paths.
- Evidence output contains only synthetic values, statuses, shapes and pixel digests; no paths outside temp, no hostnames.
- Black/flake8 (line length 88) and mypy per repository policy.

## Acceptance criteria

- [ ] Positive BED and TRX: mock SIMRS response → confirmed selection → mapper → merged manifest validates with `MHCSManifest` → real CLI exit 0, `status: ok`, empty stderr.
- [ ] DICOM: PatientID, PatientName, BirthDate match the SIMRS-derived values; StudyInstanceUID etc. present; Modality DX; SOP class `1.2.840.10008.5.1.4.1.1.1.1.1`; 16-bit unsigned MONOCHROME2; shape (BED 48×64, TRX 64×48); no private tags; mode `0600`.
- [ ] Pixels and integrity: re-readable by pydicom; `DICM` preamble; pixel array dtype uint16 and non-constant. Pixel correctness MUST be checked against an oracle that is **not produced by the output under test**, in one of these ranked forms: (a) expected pixel data independently derived in the test from the fixed synthetic inputs by a separately written NumPy reference of the documented processing (gain/dark correction, identity remap, TRX orientation relation to BED), with the derivation justified in a comment; or (b) if (a) is infeasible, a hard-coded SHA-256 of the pixel bytes, recorded once with provenance (baseline/revision, exact command, Python/NumPy/OpenCV versions, platform) and a written justification that it is a regression pin rather than a correctness proof, plus the independent structural invariants of (a) as far as they can be derived (shape, dtype, BED/TRX geometric relation, monotonic relation to the synthetic input gradient). The digest MUST be shown stable locally and on CI before acceptance; if it is not, use invariants only. The digest MUST NOT be computed at test time from the produced DICOM, and a repeat-run equality check is a separate determinism check, not the oracle.
- [ ] Identity chain: examination encounter ID in manifest equals the requested synthetic visit; any other visit yields no DICOM.
- [ ] **Pre-CLI rejection tests** (SIMRS/selection/manifest-composition stage; the runtime is never invoked): malformed SIMRS (non-dict, `success` not true, missing identity), visit mismatch, unconfirmed selection, and manifest that fails `MHCSManifest` validation before any CLI call. Each asserts: the error is raised by the mapper/helper/schema (expected exception type), the CLI/`convert_npz_to_dicom` was **not** invoked (verified by a sentinel such as the command runner not being called and no subprocess/guard-log activity), no DICOM or output path exists, and the exception text and any evidence do not contain sensitive SIMRS values. No runtime exit code or JSON runtime status is asserted for these cases.
- [ ] **CLI failure tests** (runtime actually invoked as a subprocess): invalid manifest JSON file, schema-invalid manifest file, gain id/shape/detector-mode mismatch with the radiograph, missing calibration directory, calibration not validated or wrong shape. Each asserts: the exit code **observed** from `mpips/runtime.py` (one of 2–7, asserted exactly), the JSON stdout `status: error` with the matching `code`, no output DICOM at the destination, no `.mpips-*` residue, and sanitized stdout/stderr (no test-controlled identifiers, paths or exception text). Cases already identical to existing CLI tests are not duplicated.
- [ ] Offline verification as defined in Execution constraints: the canary observes its rejected TCP attempt in its own record directory; every system-under-test run shows zero rejected attempts in a fresh record directory; sentinel expectations follow the case class (pre-CLI: none; CLI preflight: CLI only; worker-reaching: CLI and worker separately attributable), with successful BED and TRX conversions each showing both sentinels; no sentinel or rejection record text appears in stdout/stderr or CI logs beyond sanitized classifications; the limitation statement that Python audit hooks are not kernel-level network isolation is present in evidence and documentation. No claim of kernel-level isolation.
- [ ] Provenance: the test-controlled-identifier helper rejects non-`SYNTHETIC` patient/visit/acquisition identifiers; DICOM UIDs are validated by UID syntax, not by prefix.
- [ ] Deterministic evidence: a JSON summary generated twice in one session is byte-identical and contains only the allowed fields.
- [ ] Documentation addition is factual and states limitations (identity calibration, no real data, not clinical qualification, Python-level network verification only).
- [ ] Preservation: all pre-existing tests pass unchanged; only the files in scope changed.

## Verification requirements

### Required checks

- `.venv/bin/python -m pytest -q tests/test_grabber_e2e_synthetic.py tests/test_local_runtime.py tests/test_simrs_reference.py`
- `.venv/bin/python -m pytest -q` (full suite). **Current CI baseline:** PR #15 CI run 38693246116 on `d89f97b` (task-file-only change over implementation baseline `1a25609`) passed `uv run pytest -v` with **987 passed, 2 skipped**; the expected post-change CI result is therefore 987 + the new tests passed, 2 skipped, and any deviation must be explained. The two local failures recorded in `ubuntu-grabber-runtime` evidence (legacy empty-directory tests, observed at an older baseline `d645662`) are **historical local-environment results**, not the current baseline; do not assume they are expected. Any failure in a local run must be diagnosed and reported as environmental/pre-existing only with evidence (for example reproducing it on the untouched baseline).
- `black --check`, `flake8`, `mypy` on the new test, per `pyproject.toml`
- `git diff --name-only <baseline>...HEAD` limited to scope; converter SHA-256 unchanged.
- Observe PR CI (`uv run pytest -v`) if available; report local and CI separately, and report the pixel-oracle stability evidence (local and CI) when form (b) is used.

### Required evidence

The Executor MUST report implementation revision, commands run and exact results, tests added, checks not run, deviations, blockers, and CI status separately from local results.

## Stop conditions

Stop and return to planning if: any change under `mpips/` seems necessary; the mapper and CLI cannot produce a valid DICOM without changing production behaviour; a fixture would need non-synthetic data; a negative case reveals a converter defect (record, do not fix); the baseline is no longer safely applicable; an unapproved side effect is required; or the child-process network guard cannot be shown to load in the CLI process for every case that launches the CLI, or in the worker process for any case that spawns the worker (a worker-process gap must be recorded and returned to planning rather than claimed as covered).

## Side-effect authorization

### Explicitly authorized side effects

- None by this Draft. After publication, execution authority is limited to creating a feature branch and local changes; commit/push/PR for the execution require the human's or repository policy's explicit authorization at handoff.
- Not authorized: merge, deploy, release, dependency changes, production or external access, real-data handling.

## Expected terminal outcome

Review Required with a reviewable revision and truthful evidence, or Planning Required on a stop condition. The Executor does not self-accept; implementation acceptance is not release.

## Remediation

**Review basis:** PR #15 at `d89f97b56eb95651bc0380b6a721805a6c980a03`, independent verdict CHANGES REQUESTED. The original objective, scope and baseline are unchanged; the task remains Draft and T5 is pending.

### Required corrections

- Pre-CLI rejection tests and CLI failure tests are separated; runtime exit codes are required only where the runtime is invoked.
- Network prohibition across the subprocess boundary is defined (child-environment audit-hook guard with canary, sentinels and an explicit Python-level limitation) instead of a pytest-process socket patch.
- The `SYNTHETIC` prefix applies to test-controlled patient, visit and acquisition identifiers only, not to DICOM UIDs.
- Verification distinguishes historical local failures from the current CI baseline (987 passed, 2 skipped).
- The pixel regression oracle must be independently derived, or a justified provenance-recorded pin, never generated from the output being checked.

### Additional verification

- Renewed independent review of this revision before publication.

### Final bounded remediation

**Review basis:** PR #15 at `a69e4a45a62666be2b7e377839b35506a8f93eb5`, verdict CHANGES REQUESTED for one network-guard contradiction. Corrected: guard expectations are now scoped by case class (pre-CLI, CLI preflight, worker-reaching); worker sentinels are required only where a worker is spawned; successful BED and TRX conversions must each show both process-attributable sentinels; canary and system-under-test use separate record directories; records are not emitted to CI logs beyond sanitized classifications; the Python-level (not kernel-level) limitation is preserved. Task remains Draft; T5 pending renewed review and publication.
