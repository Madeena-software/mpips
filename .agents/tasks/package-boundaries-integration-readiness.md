---
title: Package Boundaries Integration Readiness
document_id: TASK-PACKAGE-BOUNDARIES-INTEGRATION-READINESS-001
version: 1.1
status: Validated/Published
language: en-US
last_updated: 2026-09-01
authority_note: >-
  This task authorizes bounded verification and non-persistent integration
  analysis of the accepted package-boundaries branch. It does not authorize
  merge, rebase, cherry-pick, conflict resolution that changes either branch,
  push, deployment, release, or production mutation.
---

# Executable Task

## Task identity

**Task title:**
`Package Boundaries Integration Readiness`

**Task path:**
`.agents/tasks/package-boundaries-integration-readiness.md`

**Task contract state:**
`Validated/Published`

**Delivery objective / Work Package / MVP:**
`Establish integration readiness evidence for refactor/package-boundaries`

**Owner / designated planning authority:**
`Repository Planner/Reviewer under the .agents/ delivery contract`

## Delivery context

The accepted `refactor/package-boundaries` implementation is substantially
diverged from the current `main`. This task determines whether the branch is
internally healthy and identifies integration risks for a later decision
against `main`, without silently synchronizing histories or reopening accepted
semantic decisions.

## Baseline and comparison identity

**Validated implementation baseline:**
`5d884d63887fb2c6a88fb78e4b9a015ab040b553`

**Relevant `main` comparison baseline:**
`e94784db65bb134d43e87a2046037ab4d1cbfe02`

**Known merge base:**
`fec5695048acbc3ce95d0a658032ec3701b6e045`

The branch is currently observed as 142 commits ahead and 53 commits behind
`main`. Git merge cleanliness alone is insufficient evidence of semantic
integration safety.

**Task revision:**
The exact immutable Git revision containing this published task must be
returned by the publication Executor and accepted by Planner/Reviewer before
execution begins. The implementation baseline and task revision are separate
identities.

## Authoritative inputs

### Governing authority

- applicable higher-priority Human Request;
- `AGENTS.md`
- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- accepted repository delivery state and decisions legitimately governing this work;
- this task once accepted as the governing delivery contract.

### Supporting context and procedure

- `.agents/context/project.md`;
- `.agents/prompts/plan-create-task.md`;
- `.agents/tasks/_template.md`.

These materials support planning and execution but do not independently govern
the delivery objective.

### Accepted prior decisions and traceability

- accepted/closed `.agents/tasks/main-hotfix-reconciliation.md` v1.14;
- accepted/closed `.agents/tasks/radiography-pipeline-optimization.md` v1.1;
- accepted implementation baseline `5d884d63887fb2c6a88fb78e4b9a015ab040b553`.

These are historical delivery contracts and accepted decisions for
traceability; they do not independently govern this new objective.

### Observed implementation and verification evidence

- source code, tests, and configuration relevant to package boundaries;
- Git history, current branch/main refs, and the known merge base;
- `.github/workflows/ci.yml` as the current observed/configured repository CI verification surface and a relevant source for reproducing applicable quality checks;
- available local or CI verification results.

Observed evidence describes repository reality and does not become governing
authority merely because it is useful for verification.

### Relevant accepted decisions and observed facts

- Main Hotfix Reconciliation is accepted/closed.
- Radiography Pipeline Optimization is accepted/closed at the validated implementation baseline.
- The TRX characterization test remains stale pending independent confirmation:
  `tests/test_config_characterization.py::test_characterize_trx_golden_output_hash`.
- Its historical expected hash is `5604df97f587cb2f158d5076fb0464b364e2f2449db5027cdef36a4b7a293b6b`.
- Accepted canonical TRX behavior has produced `5b9af36adc670ed1d93d650179d60b9cb2688cc53fa21f64fb4049de33e88d56` on both pre-optimization and accepted optimization states.
- Protected converter SHA-256 is `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

## Objective

Determine and document whether the accepted package-boundaries branch is
internally healthy and what semantic, architectural, or operational risks
must be resolved before a later integration decision against current `main`.
Produce reviewable evidence and bounded recommendations, not an integration
mutation.

## Scope

### In scope

- branch-wide verification of the accepted implementation baseline;
- comparison of branch and current `main` at the stated revisions and merge base;
- local, non-persistent integration analysis or simulation sufficient to expose conflicts and semantic risk;
- package/import-boundary, API-surface, configuration, dependency, converter, and test-contract readiness checks;
- assessment of the stale TRX characterization contract, with independent confirmation required before changing its expectation;
- traceable evidence of findings, limitations, and conditions for a later integration decision.

### Out of scope

- actual merge, rebase, cherry-pick, or conflict resolution that changes either branch;
- push, pull request or issue writes, deployment, release, or production mutation;
- updating the stale TRX golden expectation without the bounded independent-confirmation conditions defined below;
- reopening BED threshold semantics, TRX threshold bypass or orientation, ImageJ/Fiji fidelity decisions, calibration policy, or radiography optimization scope;
- changing the protected DICOM converter;
- unrelated refactoring, new product behavior, or dependency adoption.

### Preserved invariants

- BED configured-threshold behavior;
- TRX threshold bypass and accepted clockwise orientation;
- ImageJ/Fiji fidelity decisions;
- calibration default `fixed` and expanded calibration remaining opt-in;
- unapproved numeric calibration thresholds remaining unadopted;
- protected converter integrity and canonical package/import boundaries.

## Bounded TRX characterization alignment

The task authorizes correction of the stale expected golden value in
`tests/test_config_characterization.py::test_characterize_trx_golden_output_hash`
under this same umbrella objective only when the Executor independently:

1. reproduces the canonical TRX characterization output from the accepted implementation baseline;
2. obtains exactly `5b9af36adc670ed1d93d650179d60b9cb2688cc53fa21f64fb4049de33e88d56`;
3. verifies the accepted TRX orientation and geometry semantics; and
4. confirms that changing only the stale expected value from
   `5604df97f587cb2f158d5076fb0464b364e2f2449db5027cdef36a4b7a293b6b` is sufficient.

If the independently reproduced hash differs, or runtime/source changes are
needed, stop and return to Planner. This is test-contract alignment to
accepted behavior, not a new TRX semantic decision.

## Dependencies and assumptions

### Dependencies

- The implementation baseline and comparison revisions remain resolvable.
- Existing repository tooling and CI configuration remain available for local verification.

### Approved assumptions

- Integration readiness is a separate objective from the accepted Radiography Pipeline Optimization.
- The current `main` comparison revision is `e94784db65bb134d43e87a2046037ab4d1cbfe02`; if it advances materially, planning premises must be revalidated.

### Remaining approval requirements

- Planner/Reviewer acceptance of the immutable task revision before execution.
- Planner decision for any semantic conflict, scope expansion, merge strategy, or consequential external side effect.

## Required capabilities

- repository read and bounded local write;
- Git history and diff inspection;
- local shell, test, static-check, and build execution;
- evidence capture without committing external or subject data.

## Execution constraints

- Preserve unrelated working-tree state; do not reset, clean, stash, rebase, or cherry-pick.
- Keep prospective integration analysis non-persistent unless separately authorized.
- Use established repository checks and patterns; do not add a framework or dependency merely for analysis.
- Treat observed implementation as evidence of current reality, not authority to change accepted behavior.
- Distinguish branch-quality failures, semantic conflicts, environment limitations, and pre-existing failures.
- Do not treat mergeability as proof of semantic safety.

## Acceptance criteria

- [ ] Branch and comparison identities are recorded and remain consistent with the task.
- [ ] Branch-wide configured verification is run where the environment permits, including dependency/lock, converter protection, Black, Flake8, mypy, pytest, and applicable build/smoke checks.
- [ ] Package boundaries, public API behavior, configuration defaults, and protected converter integrity are assessed.
- [ ] Branch-versus-`main` differences are reviewed for semantic and architectural integration risk beyond textual conflicts.
- [ ] The stale TRX characterization result is independently confirmed before any expectation change is proposed.
- [ ] If the bounded TRX conditions are satisfied, the stale golden expectation is corrected under this task and the focused test passes; otherwise execution stops without changing it.
- [ ] BED, TRX, ImageJ/Fiji, calibration, and radiography optimization decisions remain preserved.
- [ ] Findings identify evidence, risk, limitations, and any required Planner decision.
- [ ] No merge or other integration mutation is performed.

## Stop and escalation conditions

Stop and return to Planner/Reviewer if:

- the actual baseline or `main` comparison revision differs materially from this contract;
- required authority is missing, contradictory, or materially changed;
- prospective integration requires semantic decisions beyond this contract;
- conflict resolution, merge, rebase, cherry-pick, or branch mutation would be required;
- the TRX golden expectation cannot be independently classified;
- a security, privacy, data-integrity, clinical, or operational issue needs new authority;
- verification cannot distinguish a branch defect from an environment or pre-existing failure.

## Authorized side effects

After Planner accepts the immutable task revision, Executor may inspect the
repository, run non-destructive local checks, perform non-persistent
integration analysis/simulation, create bounded textual evidence where
authorized, correct the stale TRX characterization expectation when the
conditions above are independently satisfied, and create ordinary bounded
test/evidence commits required by this objective.

The Executor retains discretion over the exact verification sequence,
non-persistent Git analysis mechanism, technically equivalent inspections,
temporary analysis artifacts, and bounded test/evidence implementation details.

Runtime or product source changes are not authorized merely to make readiness
checks pass; such a need returns to Planner.

This task does not authorize push, PR/issue writes, merge, rebase,
cherry-pick, deployment, release, production mutation, external-system
mutation, force push, destructive Git cleanup, or secrets handling.

## Expected execution terminal

`PACKAGE BOUNDARIES INTEGRATION READINESS CANDIDATE — PLANNER REVIEW REQUIRED`

Executor does not self-declare final acceptance or integration authorization.
