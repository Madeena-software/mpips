---
title: MPIPS Repository Size Reduction — Active Tree Hygiene and History Audit
status: Validated/Published
---

# Executable Task

## Task identity

**Task title:** MPIPS Repository Size Reduction — Active Tree Hygiene and History Audit

**Task path:** `.agents/tasks/repository-size-reduction.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Repository maintenance — Phase 1
active-tree hygiene and Git-history audit.

**Owner / designated planning authority:** Repository Planner / designated
delivery authority.

## Delivery context

Measure and reduce unnecessary repository weight from tracked datasets,
generated outputs, notebooks, papers, and other large artifacts while
preserving MPIPS runtime behavior. Produce evidence and a bounded candidate set
for a later history-compaction task. This phase must not rewrite Git history.

## Baseline and task revision

**Implementation baseline:**
`b14625ab01fe031cb3a9258b9fc5ff2227b032b3`

**Task revision:** The immutable governing revision is the publication commit
containing this file.

## Objective

Measure current repository, active-tree, and reachable-history size; identify
the largest current and historical blobs; safely remove unnecessary large
artifacts from the active tree; establish artifact-retention and prevention
policy; quantify active-tree savings; and produce an evidence-backed Phase 2
history-compaction candidate set and projected savings.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Current accepted baseline `b14625ab01fe031cb3a9258b9fc5ff2227b032b3`
- Repository policy and existing artifact conventions

### Requirement traceability

- Repository size reduction Phase 1 → this approved delivery directive,
  repository delivery contract, and accepted baseline.

## Scope

### In scope

- Measure `git count-objects -vH`, active-tree size and tracked-file count.
- Build a deterministic reachable-object inventory using
  `git rev-list --objects --all` and `git cat-file --batch-check` or an
  equivalent standard-library/scripted method.
- Report repository object-store size, packed size, largest current files,
  largest reachable historical blobs, paths where known, blob SHAs, byte sizes,
  current-HEAD presence, and historical-only status.
- Classify candidate artifacts by runtime/test need, authoritative source
  status, external replaceability, reproducibility, and obsolescence.
- Remove verified unnecessary large tracked artifacts from the active tree on
  `refactor/package-boundaries` only.
- Preserve lightweight metadata, citations, checksums, manifests, or
  reproduction instructions where useful and safe.
- Update `.gitignore` and/or an existing validation mechanism with a narrow,
  sustainable large-artifact prevention policy; add lightweight policy
  documentation only if needed.
- Produce lightweight audit evidence covering before/after metrics, decisions,
  exact removals, prevention changes, and Phase 2 history candidates.

### Out of scope

- Git history rewriting, including `git filter-repo`, `git filter-branch`, BFG,
  history replacement, or equivalent operations.
- Force-push, branch/tag deletion or recreation, merge, or changes to `main`.
- Uploading removed files, mutating Google Drive, or inventing external homes
  for files without authoritative locations.
- Git LFS or new third-party tooling unless returned to planning and approved.
- Production code, processing algorithms, defaults, APIs, DAG, workers,
  dependencies, lockfiles, deployment, or release configuration.
- Mechanical deletion based only on file extension.

### Preserved behavior and invariants

- MPIPS processing behavior, IQA, ImageJReplicator, threshold, CLAHE,
  contrast, denoising, median filtering, calibration, conversion, API, DAG,
  workers, production defaults, and dependencies remain unchanged.
- `mpips/conversion/tiff_json_to_dcm.py` remains byte-identical with SHA-256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Preserve runtime-required and test-required assets unless a safe approved
  replacement is within scope.
- Do not delete accepted lightweight characterization evidence:
  `artifacts/real-data-regression/kambing-baseline.json`,
  `artifacts/real-data-regression/radiograph-structural-characterization.md`,
  `artifacts/real-data-regression/radiograph-structural-characterization.json`,
  `artifacts/real-data-regression/radiograph-structural-characterization.csv`.

## Dependencies and assumptions

### Dependencies

- Read access to the complete local Git repository and reachable refs.
- Existing repository conventions for tests, artifacts, and validation.

### Approved assumptions

- GitHub's reported approximately 281350 KB repository size is context only;
  local measurements are authoritative for this task.
- TIFF files under `artifacts/camera-calibration-dotgrid/data/` are audit
  candidates, not automatically removable assets.
- Large TIFF/TIF, DICOM, NPZ/NPY, raw/processed image, generated image,
  embedded-notebook-output, PDF, temporary-output, and diagnostic artifacts
  require individual classification rather than extension-only deletion.

### Remaining approval requirements

- Any material ownership, licensing, retention, runtime/test dependency,
  external-data, architecture, dependency, or scope ambiguity requires return
  to planning.
- No external-system mutation is authorized.

## Required capabilities

- Repository read/write and local command execution.
- Git object and tree inspection.
- Existing repository test and static-check tooling.

## Execution constraints

- Work only on `refactor/package-boundaries`; do not touch `main`.
- Reuse existing repository conventions and standard-library tooling.
- Do not add large binary audit evidence.
- Record the exact path, blob SHA, size, classification, and decision for each
  removed or retained candidate group.
- For history candidates, report reachable byte contribution, projected saving,
  refs where practical, rewrite risks, changed commit-SHA implications,
  force-push/ref-migration requirements, and fresh-clone verification.
- A normal fast-forward commit may be created and pushed only after the task is
  published and the authorized bounded execution is complete.

## Acceptance criteria

- [ ] Repository object-store, packed, active-tree, and tracked-file metrics
      are measured locally rather than guessed.
- [ ] Largest current files and reachable historical blobs are inventoried with
      paths where known, blob SHAs, sizes, and current/history-only status.
- [ ] Each candidate artifact group has an evidence-backed classification and
      safe retain/remove decision.
- [ ] Verified unnecessary large active-tree artifacts are removed without
      breaking runtime or automated-test requirements.
- [ ] Lightweight policy/prevention changes prevent casual recurrence without
      blocking legitimate small fixtures.
- [ ] Before/after active-tree size, byte savings, percentage savings, and
      tracked large-file counts are demonstrated.
- [ ] A specific Phase 2 history-compaction candidate set and projected saving
      are available for Reviewer decision.
- [ ] Tests/checks support cleanup safety; the protected converter hash is
      unchanged; no production behavior or dependency changes occurred.
- [ ] No history rewrite, force-push, `main` modification, Google Drive
      mutation, or external upload occurred.

## Verification requirements

### Required checks

- Run `git count-objects -vH` before and after the normal commit, explaining
  why reachable historical blobs remain.
- Run deterministic current-tree and reachable-history inventories before and
  after cleanup.
- Verify removed files are not runtime imports and are not required by tests.
- Run relevant focused tests and the full repository suite when practical.
- Run repository-required lint, type, and static checks.
- Verify the protected converter SHA-256.
- Verify no unexpected large binary was added and inspect `git status`/diff.

### Required evidence

The Executor must report the governing task revision, accepted baseline, final
Phase 1 commit SHA, exact changed/deleted files, all before/after metrics,
largest current and historical blobs, classification decisions, active-tree
savings, checks and results, protected converter SHA, Phase 2 candidates and
projected savings, and confirmation that history, `main`, and external systems
were not mutated.

## Stop conditions

Return to planning if a large artifact is required for runtime/tests and no
safe lightweight alternative is in scope; cleanup requires dependency or
architecture changes; ownership/licensing/retention is materially ambiguous;
meaningful reduction requires immediate history rewrite; branch/ref topology
makes later compaction materially risky; or unrelated work appears on the
branch.

## Side-effect authorization

Future execution may delete verified unnecessary tracked artifacts from
`refactor/package-boundaries`, add/update lightweight manifests, policy,
documentation, `.gitignore`, bounded size guards, and audit evidence, and
commit/push normal fast-forward changes to that branch.

It may not touch `main`, merge, rewrite history, force-push, delete/recreate
refs, mutate external storage, upload files, install unapproved tooling, or
change production behavior.

## Expected terminal outcome

### Review Required

Use when the bounded Phase 1 cleanup, evidence, and verification are complete
and available for Reviewer inspection.

### Planning Required

Use when a stop condition prevents safe completion within this contract.
