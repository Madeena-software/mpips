---
title: MPIPS Repository History Compaction — Phase 2
status: Validated/Published
---

# Executable Task

## Task identity

**Task title:** MPIPS Repository History Compaction — Phase 2

**Task path:** `.agents/tasks/repository-history-compaction.md`

**Task contract state:** Validated/Published

**Delivery objective / Work Package / MVP:** Repository maintenance — remove
the approved Phase-1 artifact blobs from reachable branch history while
preserving branch-tip contents and repository behavior.

**Owner / designated planning authority:** Repository Planner / designated
delivery authority.

## Delivery context

Phase 1 active-tree cleanup was accepted at
`5aef640eb6c124d8fbd95009021f4648d3eb6c69`. The active tree is now
`76,629,279` bytes / `73.079` MiB, but the Git pack remains approximately
`274.69 MiB` because removed artifacts remain reachable in history.

This task authorizes a controlled history migration for the already-approved
artifact classes. The primary success criterion is a substantially smaller
fresh clone from the rewritten supported branch refs, while preserving the
intended branch-tip contents and repository functionality.

## Baseline and task revision

**Implementation / accepted baseline:**
`5aef640eb6c124d8fbd95009021f4648d3eb6c69`

**Phase-1 governing task:**
`.agents/tasks/repository-size-reduction.md` @
`a7704a1a3a0fddc929c984b11d232bddd82c9e70`

**Phase-1 evidence:**
`.agents/evidence/repository-size-reduction-phase-1.md`

**Measured candidate history removal:** `254,730,118` uncompressed bytes
across 55 unique reachable blobs, excluding the retained runtime calibration
cache. This is a projection, not a promise of final packed-clone savings.

**Task revision:** The immutable publication commit containing this file.

## Objective

Rewrite reachable history for all affected authorized branch refs so that only
the verified Phase-1-approved artifact classes are removed, then prove locally
and from a fresh clone that:

- the candidate blobs are no longer reachable from rewritten writable branch
  histories;
- retained runtime calibration data remains present;
- branch-tip content is preserved apart from the approved artifact removal;
- repository instructions, task content, source, tests, and protected converter
  remain correct; and
- fresh-clone history size falls substantially from the Phase-1 pack baseline.

## Authoritative inputs

### Governing authority

- `.agents/AGENTS.md`
- `.agents/software-workflow.md`
- `.agents/context/project.md`
- Accepted Phase-1 baseline `5aef640eb6c124d8fbd95009021f4648d3eb6c69`
- `.agents/evidence/repository-size-reduction-phase-1.md`
- User authorization in the publication directive for affected branch-history
  rewrite, including `main`, and force-push after all safety gates pass.

### Requirement traceability

- Repository size reduction Phase 2 → accepted Phase-1 evidence and this
  validated task.

## Scope

### In scope

- Independently inventory current remote and local ref topology immediately
  before migration, including heads, tags, remotes, and discoverable PR refs.
- Capture original branch tips, default branch, tag targets, task SHA256, and
  candidate blob reachability.
- Create and verify a complete local rollback bundle or equivalent mirror
  outside the repository and do not publish it as a backup ref.
- Use an independently fetched disposable migration clone or mirror, not
  `/var/www/mpips`, for destructive filtering.
- Rewrite only the approved Phase-1 artifact classes and verified historical
  renamed/moved forms of those same identities:
  - `artifacts/camera-calibration-dotgrid/output/` generated/reproducible files;
  - the Phase-1-approved TIFF inputs under
    `artifacts/camera-calibration-dotgrid/data/`;
  - bundled PDFs under `artifacts/camera-calibration-dotgrid/references/`;
  - `artifacts/imager-pipeline/archive/try.ipynb`;
  - `research/kambing-260714/imager_pipeline_tweak.ipynb`; and
  - `research/kambing-260714/imager_pipeline_tweak_local.ipynb`.
- Rewrite affected authorized branch refs, including `main` where affected,
  only after all local and remote gates pass.
- Preserve old-to-new commit mapping and lightweight migration evidence.
- Verify fresh-clone reachability, size, branch-tip content, tests, and static
  checks after remote mutation.

### Out of scope

- Rewriting, moving, or deleting tags without separate explicit authorization.
- Rewriting or force-updating `refs/pull/*` or other server-managed refs.
- Deleting branches, modifying branch protection, or changing GitHub settings.
- Application behavior, processing defaults, IQA, ImageJReplicator, calibration
  algorithms, APIs, DAGs, workers, dependencies, lockfiles, or deployment.
- Externalizing the retained runtime calibration cache, Git LFS, Google Drive
  mutation, dataset upload, or unrelated history deletion.
- Any cleanup rerun or restoration of Phase-1-deleted artifacts.

### Preserved behavior and invariants

- Branch-tip source, tests, configuration, documentation, and functionality
  remain content-equivalent except for approved artifact removal.
- `mpips/conversion/tiff_json_to_dcm.py` remains SHA256
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
- Retain both `metadata.json` and `remap.npz` under:
  `research/kambing-260714/data/output/calibration-cache/`
  `4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/`.
- `.gitignore`, `artifacts/README.md`, Phase-1 evidence, and repository task
  content survive byte-identically except for the new Phase-2 evidence itself.

## Dependencies and assumptions

### Dependencies

- Read/write access to the repository and authorized remote branch refs.
- A disposable temporary migration workspace with sufficient disk space.
- The official `git-filter-repo` tool. If a compatible installation is already
  available, use it. If it is unavailable, future execution is explicitly
  authorized to install it temporarily as an isolated user/tool installation,
  preferably with `uv tool install git-filter-repo`, or with `pipx install
  git-filter-repo` when `pipx` is already available and appropriate.
- The temporary tool installation must remain outside MPIPS project
  dependency management and must not modify `pyproject.toml`, `uv.lock`, any
  requirements file, application/runtime dependencies, or Docker/deployment
  dependencies.
- Ability to create and verify a local rollback bundle outside the repository.
- Fresh-clone access after remote update.

### Approved assumptions

- Phase-1 classification and candidate totals are authoritative for the
  approved removal set.
- GitHub's displayed repository size may lag; fresh-clone measurements are the
  acceptance measurement.
- Branch topology must be rediscovered; the publication-time list is not a
  permanent allowlist.

### Remaining approval requirements

- If any tag retains a candidate blob, stop before remote rewrite and report
  the tag, blobs, and projected impact.
- If a currently tracked candidate is required by `main` or another branch,
  stop and return to planning.
- If any affected remote branch advances after the pre-rewrite snapshot, stop
  without overwriting it.
- Branch-protection or force-push rejection requires separate human handling;
  do not disable controls automatically.

## Required capabilities

- Repository and remote Git inspection.
- Disposable-clone filesystem and shell execution.
- Official `git-filter-repo`, either already available or installed through an
  authorized isolated `uv tool`/already-available `pipx` mechanism.
- Git bundle creation and verification.
- Test and static-check execution.
- Fresh ordinary clone and size measurement.

## Execution constraints

### Pre-rewrite snapshot

Before filtering, persist lightweight evidence containing:

- every discovered branch and original tip SHA;
- default branch;
- every tag and target;
- relevant remote and discoverable PR refs;
- governing task SHA256 and publication SHA;
- accepted Phase-1 SHA;
- candidate blob/path reachability;
- exact filter rules; and
- protected historical identifiers:
  `c09012a1d20a72d3ce3cccaa7bb1ea4d38a82f20`,
  `deaf1430f62c90ce02cd4cefc8b58ab380d2aad8`,
  `b14625ab01fe031cb3a9258b9fc5ff2227b032b3`,
  `a7704a1a3a0fddc929c984b11d232bddd82c9e70`,
  `ce0fe2df6f06e8fa370f4999734903cadea39638`, and
  `5aef640eb6c124d8fbd95009021f4648d3eb6c69`.

After publication, include this task's publication SHA as well.

### Filtering

- Use the official `git-filter-repo` tool only. If it is already available and
  compatible, use it; otherwise install it temporarily with `uv tool install
  git-filter-repo` when `uv tool` is available and appropriate, or use
  `pipx install git-filter-repo` when `pipx` is already available and
  appropriate.
- Before filtering, capture `git-filter-repo --version` or equivalent
  authoritative version evidence, the resolved executable path, and the
  installation command actually used.
- The installation must be isolated outside MPIPS project dependency
  management. Do not use `pip install` into the MPIPS project environment,
  and do not use sudo or system-wide installation.
- If installation fails, the package/source cannot be verified as the official
  `git-filter-repo` distribution, compatibility cannot be established, or
  elevated privileges/system mutation are required, stop and return to
  planning.
- Do not use `git filter-branch`, BFG, or an improvised substitute.
- Do not filter directly in `/var/www/mpips`.
- Do not broaden the candidate set because another historical file is large.
- Do not filter tags or server-managed PR refs.

### Local dry run and rollback

Complete and inspect the disposable-clone rewrite before any remote mutation.
Verify changed refs, candidate reachability, retained cache, `git fsck
--full`, branch-tip trees, tag identity, task byte identity, converter hash,
and rewritten object/pack size. Discard the migration clone and stop if the
result differs materially from the approved candidate scope.

The verified local bundle/mirror is the rollback artifact. It must remain
outside the repository and available until Reviewer acceptance. Rollback may
restore only the exact captured pre-rewrite branch tips; do not improvise a
different rollback state.

### Remote update

Immediately before force-push, fetch again and compare every affected remote
branch with the snapshot. Force-update only explicitly affected branch refs,
including `main` where affected. Do not use indiscriminate `--mirror`; do not
touch tags, `refs/pull/*`, unrelated refs, or branch protection.

Existing clones must not casually push old history after migration. Fresh
clones are preferred; collaborators with old clones must reset or rebase
carefully against rewritten refs and must not merge old pre-rewrite history
back into them.

## Acceptance criteria

- [ ] Complete original ref snapshot and verified local rollback bundle exist.
- [ ] Only the approved Phase-1 candidate set was filtered.
- [ ] All affected authorized branch refs, including `main` where needed, are
      rewritten consistently.
- [ ] Tags, unrelated branches, and PR refs are not rewritten or deleted.
- [ ] Candidate blobs are absent from rewritten writable branch reachability.
- [ ] Retained calibration `metadata.json` and `remap.npz` remain present.
- [ ] Branch-tip tree comparison shows no unrelated content loss.
- [ ] Protected converter content and hash are unchanged.
- [ ] Old-to-new mappings exist for branch tips, this task, Phase-1 baseline,
      and listed historical audit SHAs where mappings exist.
- [ ] Task content SHA256 is identical before and after rewrite, with old and
      rewritten publication identities recorded.
- [ ] Local and fresh-clone `git fsck --full` pass.
- [ ] Remote updates do not overwrite intervening branch work.
- [ ] Fresh clone succeeds and demonstrates substantial history-size reduction
      from approximately 274.69 MiB pack size.
- [ ] Tests and static checks are reported truthfully, with no CI claim for
      local evidence.
- [ ] Rollback artifact remains available until Reviewer acceptance.

## Verification requirements

### Required checks

- Inventory refs, tags, branch tips, candidate blobs, and task hashes before
  rewrite.
- Verify rollback bundle or mirror before filtering.
- Verify local rewritten refs, trees, tags, candidate reachability, retained
  cache, task identity, converter hash, and `git fsck --full`.
- Run converter protection, relevant focused tests, full pytest when practical,
  Black, Flake8, and mypy when practical.
- Create a new ordinary fresh clone after push and measure `.git`, tracked
  tree, reachable blobs, large-file thresholds, and pack/fetch size where
  observable.

### Required evidence

Persist `.agents/evidence/repository-history-compaction.md` and, if reasonably
sized, `.agents/evidence/repository-history-compaction-commit-map.csv` with:

- original and rewritten branch tips;
- original and rewritten task publication identities;
- Phase-1 baseline mapping;
- important historical SHA mappings where available;
- ref/tag/PR inventory and unchanged-tag result;
- candidate reachability before and after;
- rollback artifact verification and location outside the repository;
- local and fresh-clone size measurements;
- tests/checks actually executed and observed;
- explicit statement that old SHAs are audit identifiers and are not active
  post-rewrite identities; and
- rollback and collaborator guidance.

Do not represent skipped, terminated, local-only, or unobserved checks as CI or
as successful verification.

## Stop conditions

Stop before destructive push and return to planning if:

- branch topology changes materially;
- any affected branch advances after the snapshot;
- any tag retains a candidate blob;
- `git-filter-repo` cannot be obtained as an authorized isolated official tool
  installation, installation fails, compatibility cannot be established, or
  installation requires permissions/system mutation beyond this authority;
- candidate classification is insufficient;
- a candidate is runtime/test-required on another branch;
- unrelated content disappears;
- `git fsck` fails;
- branch-tip content comparison fails;
- task content does not map byte-identically;
- protected converter changes;
- rewritten local or fresh-clone state is not demonstrably smaller; or
- any new security, privacy, data, ownership, or operational issue appears.

## Side-effect authorization

Future execution of this task is explicitly authorized by the user to rewrite
Git history and force-update all affected **branch refs**, including `main`,
after every required safety and verification gate passes.

Future execution is also explicitly authorized to install the official
`git-filter-repo` temporarily outside MPIPS project dependency management when
it is not already available. The preferred mechanism is `uv tool install
git-filter-repo`; the acceptable fallback is `pipx install git-filter-repo`
when `pipx` is already available and appropriate. This installation authority
does not authorize `pip install` into the MPIPS project environment, sudo,
system-wide installation, or changes to project dependency/deployment files.

This authority does not extend to:

- rewriting, moving, or deleting tags;
- deleting branches;
- modifying branch protection or GitHub settings;
- rewriting `refs/pull/*`;
- external storage mutation or uploads; or
- unrelated repository changes.

The publication turn itself authorizes only creation, commit, and normal push
of this task file on `refactor/package-boundaries`; it does not authorize any
history rewrite or force-push.

## Expected terminal outcome

### Review Required

Use when the local migration, authorized remote update, fresh-clone evidence,
and rollback artifact are complete and available for Reviewer inspection.

### Planning Required

Use when a stop condition prevents safe completion within this contract.
