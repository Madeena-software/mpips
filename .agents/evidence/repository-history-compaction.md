# Repository History Compaction — Phase 2 Evidence

Status: Executor evidence; Review Required. This document does not constitute
Planner/Reviewer acceptance.

## Authority and baseline

- Governing task: `.agents/tasks/repository-history-compaction.md`
- Governing task revision before rewrite: `3f5697232ea4bb1cf8c48bf5fdbc96d551537f28`
- Governing task content SHA-256 before and after rewrite:
  `5c8f5513cbd8f474a4890051e9016c1944b34d6889afab31585264540df93ad8`
- Accepted Phase-1 baseline: `5aef640eb6c124d8fbd95009021f4648d3eb6c69`
- Phase-2 tool-authority remediation revision before rewrite:
  `3f5697232ea4bb1cf8c48bf5fdbc96d551537f28`

The governing task and its referenced authority were included in the rewrite.
The rewritten equivalent of the Phase-2 tool-authority governing-task revision
`3f5697232ea4bb1cf8c48bf5fdbc96d551537f28` is
`bd8a36e4c8bfba5121132f1d262b354cbb0cf6bb`.
The separate Phase-1 repository-size-reduction task validation commit
`a7704a1a3a0fddc929c984b11d232bddd82c9e70` rewrites to
`c2c613e112bfda9a46271964989421236a5f0add`.

## Rewritten branch refs

| Previous ref | Rewritten ref |
| --- | --- |
| `refs/heads/main` `c4d2756fccf7b89d5b5c1177692208d546376cd8` | `fec5695048acbc3ce95d0a658032ec3701b6e045` |
| `refs/heads/refactor-adlan-1` `0d06c4762e14b6bde595f0da631d1158a1af8344` | `c487d3d9c2e34d6a3371699cc0d4696739ddab45` |
| `refs/heads/copymain-10-august` `db13d7a2d2b0c68061e2d878bd1c78d8687e0a85` | `e5db5690c84d16cc50f7d5d76f4ba02a00e0133f` |
| `refs/heads/refactor/package-boundaries` `3f5697232ea4bb1cf8c48bf5fdbc96d551537f28` | `bd8a36e4c8bfba5121132f1d262b354cbb0cf6bb` |

The package-boundaries ref above is the raw rewritten tip. A subsequent normal
evidence-only normal commit moved `refactor/package-boundaries` to
`ce0b846ee3ccddab7f96defeb30c75dcfeb6c9b5`. The remediation commit created by
this instruction becomes the new final package-branch tip and is reported
separately in the Executor handoff.

The repository default branch is `main`.

## Historical commit map

The following mappings are copied from the authoritative
`rewrite-authoritative/filter-repo/commit-map`:

| Original SHA | Rewritten SHA | Meaning |
| --- | --- | --- |
| `c09012a1d20a72d3ce3cccaa7bb1ea4d38a82f20` | `fd7ebd61a3b705ea40a3962a7fcbbe992906797f` | historical mapped commit |
| `deaf1430f62c90ce02cd4cefc8b58ab380d2aad8` | `d80b10c412fb86237ef3d3f74bdffa3a3d814b80` | historical mapped commit |
| `b14625ab01fe031cb3a9258b9fc5ff2227b032b3` | `4255fe9871751b1adcf5ff10d78b19094f00023c` | historical mapped commit |
| `a7704a1a3a0fddc929c984b11d232bddd82c9e70` | `c2c613e112bfda9a46271964989421236a5f0add` | Phase-1 repository-size-reduction task validation |
| `ce0fe2df6f06e8fa370f4999734903cadea39638` | `943fc59bf2386509cd609b85b24e2a3a3218788b` | Phase-1 implementation |
| `5aef640eb6c124d8fbd95009021f4648d3eb6c69` | `225cb8dd32b256a9de50e7b3dafe5dc75fc6d5c6` | accepted Phase-1 baseline |
| `d944f72b1a8256e81911514a29ae389fbdfeaf11` | `0d58219af40d46a65f45f473e78885af80c5f838` | Phase-2 task publication |
| `3f5697232ea4bb1cf8c48bf5fdbc96d551537f28` | `bd8a36e4c8bfba5121132f1d262b354cbb0cf6bb` | Phase-2 tool-authority governing task |

The four original branch-tip mappings are recorded in the branch-ref table
above and the CSV companion. No mapping was inferred for these entries.

No tags existed before the rewrite and no tags exist after it. The advertised
server-managed `refs/pull/1/head` was not pushed or changed. Its pre-rewrite
value was `b02850d793c5b8c324f654cf225b8ecf2d6955fc`.

## Filter scope

The filter removed only the approved Phase-1 generated/reproducible artifacts,
their evidence-backed historical moved forms, and the three approved notebook
identities:

- current and historical `camera-calibration-dotgrid/output/**` forms;
- current and historical paths for the two approved TIFF inputs;
- current and historical paths for the six approved reference PDFs;
- current and historical paths for `try.ipynb`;
- the two current `research/kambing-260714` notebooks.

The historical candidate set was 55 unique blobs, totaling 254,730,118
uncompressed bytes (242.929571 MiB). This is larger than the Phase-1 active
tree deletion count of 53 files because historical moved and renamed identities
are included in the history candidate set.

The Phase-1 active-tree deletion arithmetic remains 42 output files + 2 TIFF
inputs + 6 PDFs + 3 notebooks = 53 files. No artifacts were restored.

## Rewrite tooling and rollback

- Tool: official `git-filter-repo` 2.47.0
- Tool version identifier: `a40bce548d2c`
- Isolated executable: `/root/.local/share/uv/tools/git-filter-repo/bin/git-filter-repo`
- Installation: `.venv/bin/python -m uv tool install git-filter-repo`
- No project dependency files were changed.
- Pre-rewrite rollback bundle: `/tmp/mpips-phase2.7xZfKi/pre-rewrite.bundle`
- Bundle verification reported: `The bundle contains a complete history`.

The rollback bundle remains outside the repository and must be retained until
Reviewer acceptance. It was not committed, uploaded, or pushed.

## Verification

The authoritative disposable rewritten mirror passed:

- `git fsck --full --no-progress`;
- no unreachable candidate blobs from any writable rewritten branch head;
- candidate reachability: 55 blobs / 254,730,118 bytes removed;
- retained remap blob size: 74,446,788 bytes;
- noncandidate tree comparison: zero differences on all four rewritten branch
  pairs;
- protected converter SHA-256:
  `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`;
- task SHA-256 unchanged as recorded above.

A new ordinary clone of the rewritten package branch reported:

- 2,225 packed objects, one pack, `72.31 MiB` pack size, zero garbage;
- 225 tracked files totaling 76,645,256 bytes (73.0946 MiB);
- one tracked file over 1 MiB, 5 MiB, 10 MiB, and 20 MiB;
- `git fsck --full --no-progress` passed;
- Black: 134 files unchanged;
- Flake8: passed with no output;
- focused converter-protection test: `1 passed in 0.03s`.

Broader pytest and mypy were not claimed: the bounded local mypy attempt did
not complete with an observable result. No CI result is claimed. No Python
production source changed in Phase 1 or in this history-only Phase 2 work.

## Preserved invariants

- `.gitignore` SHA-256: `4fe056ecafc3cf7c0c34b34a805033db47a31ea858ed09382afd81a4f9564868`.
- `artifacts/README.md` SHA-256:
  `8ae85892564d1669922cbf9bb926b1f53191e5e6b9389a9427159f6d71ce5f26`.
- Phase-2 candidate total remains 55 unique blobs / 254,730,118 bytes.
- No history rewrite was performed on tags, the server-managed PR ref, or any
  branch outside the four explicitly authorized branch refs.
- The canonical checkout `/var/www/mpips` was not used as the filter input and
  was not mutated by the rewrite.

## Clone and audit warning

Pre-rewrite SHAs remain historical audit identifiers only; rewritten SHAs are
the active repository identities. Old pre-rewrite clones must not push or merge
their old history back into rewritten branches. Fresh clones are preferred.
`/var/www/mpips` is still a pre-rewrite checkout and must not be used for future
commits or pushes until it is deliberately realigned or replaced with a fresh
rewritten clone. It was not realigned during this evidence-remediation turn.
