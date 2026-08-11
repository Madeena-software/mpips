---
name: mpips-prod-runtime-setup
description: Create a one-time GitHub Actions workflow that provisions the production runtime directory structure on the self-hosted runner server, including copying the validated BED calibration artifact.
version: 1
---

<!-- antigravity-code-agent-template:managed -->
# Task: Production runtime directory setup via GitHub Actions

## Objective

For `$TARGET`, create a one-time GitHub Actions `workflow_dispatch` workflow that provisions the required production runtime directory structure on the self-hosted runner. This replaces the need for SSH access to the server.

## Context

The production deployment workflow (`deploy-internal-beta.yml`) requires the following to exist on the server before it can run:

```
/var/www/mpips-runtime/
  calibration/
    metadata.json   ← from the validated BED calibration artifact
    remap.npz       ← from the validated BED calibration artifact
  launcher/         ← empty directory, created by the launcher process
```

The validated BED calibration artifact already exists on the self-hosted runner at:

```
/var/www/mpips/research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/
```

Key files in that directory:
- `metadata.json` — `validated: true`, `detector_mode: "BED"`, fingerprint `4832df384f053...`
- `remap.npz` — 74 MB remap artifact

SSH access to the server is not available. All server-side operations must be performed through GitHub Actions using the self-hosted runner.

## Governing Authority

- Architecture: `project.md` — loopback-only deployment, self-hosted runner, `/var/www/mpips-runtime` is the canonical runtime root.
- `deploy-internal-beta.yml` lines 58-60 require `$REMOTE_PATH/calibration/metadata.json` and `$REMOTE_PATH/calibration/remap.npz` to exist and be non-empty.

## Scope

### In scope

1. **Create `.github/workflows/setup-runtime-dirs.yml`** — a `workflow_dispatch`-only workflow that:
   - Runs on `self-hosted`
   - Creates `/var/www/mpips-runtime/calibration/`
   - Creates `/var/www/mpips-runtime/launcher/`
   - Creates `/tmp/mpips-workspaces`
   - Copies `metadata.json` and `remap.npz` from the calibration cache source path into `/var/www/mpips-runtime/calibration/`
   - Verifies that both files exist and are non-empty (`test -s`) after copying
   - Prints a confirmation of the file sizes and the `validated` field from `metadata.json`

2. **Hardcode the source calibration path** as:
   ```
   /var/www/mpips/research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b
   ```

3. **Idempotent**: if the files already exist, the workflow must overwrite them safely (use `cp -f`) without failing.

### Out of scope

- Modifying `deploy-internal-beta.yml`
- Creating any GitHub Secrets
- Any SSH-based operations

### Preserved behavior

- The calibration files must remain read-only at the destination (`chmod 444`)
- The launcher directory must be writable (`chmod 755`)
- No code changes to the API, worker, or tests

## Implementation Baseline

- Target Revision: `b2b378d6cff441c008c078c438e3a29b5527c00a`

## Verification Plan

### Acceptance criteria

- [ ] Workflow file `.github/workflows/setup-runtime-dirs.yml` is committed.
- [ ] Workflow runs successfully via `gh workflow run setup-runtime-dirs.yml --ref main` (or user triggers it via GitHub UI).
- [ ] Workflow output confirms:
  - `/var/www/mpips-runtime/calibration/metadata.json` exists and is non-empty
  - `/var/www/mpips-runtime/calibration/remap.npz` exists and is non-empty
  - `validated: true` is present in `metadata.json`
- [ ] Running the main `deploy-internal-beta.yml` workflow immediately after no longer fails at the "Prepare runtime and rollback state" step.

The Executor must commit the workflow file and report the successful run output.
