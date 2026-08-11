---
name: mpips-prod-deploy-realdata-npz-dicom
description: Trigger the production internal-beta deployment via GitHub Actions and verify live operation with real data.
version: 1
---

<!-- antigravity-code-agent-template:managed -->
# Task: Production internal-beta deployment with real data

## Objective

For `$TARGET`, trigger the production internal-beta deployment (using the GitHub Actions workflow) and verify that the deployed MPIPS DICOM-only service functions correctly on the internal-beta host environment.

## Context

- The local deployment validation (burn-in and real data test) has passed and is accepted.
- The canonical loopback host-side port is `127.0.0.1:8014`.
- The repository relies on `.github/workflows/deploy-internal-beta.yml` for production deployments.

## Governing Authority

- Architecture: `project.md` (internal-beta topology).
- Pre-requisites: Local validation task completed successfully.

## Scope

### In scope
- Verifying the GitHub Actions deployment workflow configuration.
- Triggering the GitHub Actions workflow `deploy-internal-beta.yml` (either via `gh` CLI if authenticated, or by instructing the user to trigger it in the UI).
- Polling or waiting for the workflow to complete successfully.
- Observing the final live deployment state if accessible, or relying on the workflow's built-in live validation checks.

### Out of scope
- Changing the codebase or tests (all code must be exactly as in the accepted baseline).
- Modifying the GitHub workflow (other than required path fixes).
- Exposing the API publicly (must remain loopback-only on the host).

### Preserved behavior
- Converter SHA-256 remains unchanged.
- Idempotency and API key behavior remain intact.

## Implementation Baseline

- Target Revision: `2b13a96` or later (must include the port 8014 migration and memory limit increase).

## Verification Plan

### Acceptance criteria

- [ ] GitHub Actions workflow `deploy-internal-beta.yml` is triggered.
- [ ] Workflow completes with a `success` status.
- [ ] The workflow logs show that the live checks (health endpoint, DICOM conversion endpoint, correct loopback port `8014`) passed.

### Execution Instructions

If the `gh` CLI is available and authenticated, run:
```bash
gh workflow run deploy-internal-beta.yml --ref main
```
Then monitor the run:
```bash
gh run list --workflow deploy-internal-beta.yml --limit 1
gh run watch <run_id>
```

If `gh` is not authenticated, ask the user to manually trigger the workflow via the GitHub UI and report the result.

The Executor must report the final run status, any errors, and the completion of the deployment.
