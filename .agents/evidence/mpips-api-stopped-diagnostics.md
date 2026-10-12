---
title: MPIPS stopped API operational triage
status: Draft PR — review required; no recovery performed
date: 2026-10-12
---

# MPIPS stopped API operational triage

## Baseline and task

- Verified `main` baseline: `cb0e7468b1c186119a3dfcc97d55176b6f4a9f98`.
- Validated task: `.agents/tasks/mpips-api-stopped-diagnostics.md` @
  `5f4e3a3edac964420ac14bc1c6fc167988d764a7`.
- Production audit evidence: [run 38272117045](https://github.com/Madeena-software/mpips/actions/runs/38272117045).
- The implementation branch is `feat/mpips-api-stopped-diagnostics`; no
  production workflow was dispatched during this task.
- Draft PR: [#11](https://github.com/Madeena-software/mpips/pull/11).

## Repository intent

`docker-compose.prod.yml` defines `mpips-api` as an expected internal-beta
service, maps its host port to loopback, gives it a health check, and declares
Redis as a healthy dependency. The API's configured Docker restart policy is
`unless-stopped`; Redis uses the same policy. The deployment workflow starts
Compose services and verifies API health and expected networking before
recording the deployed version. The verification workflow exercises the API
and conversion path. This establishes intended operation in the internal-beta
deployment; it does not establish the owner's current operational intent.

Docker documents `unless-stopped` as restarting a container after exit, while
remaining stopped after a manual stop (including across daemon restarts).
That policy does not identify the event that caused this observed stopped
state. [Docker restart policy documentation](https://docs.docker.com/engine/containers/start-containers-automatically/).

## Historical GitHub evidence

- Latest successful deployment in Actions metadata:
  [run 34553033212](https://github.com/Madeena-software/mpips/actions/runs/34553033212),
  source revision `6e5ebb736a1191eb955f018461e33a6b424029d8`, completed
  2026-09-11. Both build and deploy jobs passed, including Compose start and
  deployment-readiness checks.
- A workflow-triggered verification shortly afterward failed its burn-in
  step: [run 34553422639](https://github.com/Madeena-software/mpips/actions/runs/34553422639).
  Its failure-log step also completed, so the workflow emitted its configured
  Docker Compose and launcher log tails to public Actions logs.
- A manual verification on the same deployment revision passed, including
  deployment identity, conversion readiness, and burn-in:
  [run 34553464308](https://github.com/Madeena-software/mpips/actions/runs/34553464308).
- No later deployment workflow appears in the available repository Actions
  history before the October 12 infrastructure audit. No repository workflow
  record establishes a later authorized shutdown. GitHub history cannot rule
  out an out-of-band operator action.
- The October 12 audit reported the API container `stopped`, API health
  `unavailable`, Redis `running` and `healthy`, and the expected Compose
  project `complete`. It did not inspect exit state, OOM state, restart count,
  termination age, image marker, or container network attachment.

The successful deploy and manual verification prove the configured deployment
and checks passed at that earlier time. They do not prove the API remained
available afterward or establish why it stopped. The failed workflow-triggered
burn-in followed by a successful manual verification is inconsistent evidence
about that verification window, not proof of the later stop's cause.

## Public Actions-log boundary

The audit collector emits fixed labels and categories, but GitHub Actions also
emits standard setup metadata. Inspection of the public audit run established
that its setup log includes a runner-name field. The value is intentionally not
copied into this evidence or response. The repository is public, so the owner
must assess the runner name's suitability for public logs before another
production dispatch; the collector cannot suppress this platform-generated
field.

The deployment and verification workflow definitions include failure steps
that print raw Docker Compose logs and launcher logs. Failure runs confirm
those steps executed. Their contents were not reproduced or inspected for
this report. These are a separate existing exposure path from the sanitized
collector and should not be used to diagnose the incident through public logs.

## Cause and intent assessment

**Classification: Insufficient evidence.** The API container was stopped at
the audit time, and repository configuration indicates it is expected to
operate. No approved shutdown record was found. A stopped state is not by
itself proof of a crash or intentional stop.

Possible explanations, not verified facts, include manual stop/Compose stop,
host or Docker daemon interruption, a process exit or OOM kill, image/config
replacement, or deployment rollback/partial failure. The historical deploy
records do not establish which explanation applies.

The API requires operational attention as a possible service incident because
the expected API container was stopped. Clinical impact, current request
volume, and whether the owner intended maintenance are unknown. No restart,
redeploy, or replacement was performed.

## Bounded next diagnostic

The Draft implementation adds only Docker metadata classifications for API
exit category, OOM status, restart-count band, stopped-age band, actual restart
policy, image-tag comparison against the deployment version marker, and
whether API/Redis both attach to the expected internal network. It does not
read logs, environments, process arguments, host journals, addresses, or
clinical files. Categories cannot prove operator intent, cryptographically
attest an image, or establish application-level Redis connectivity.

The implementation is for GitHub-hosted CI and independent review only. Any
production use remains blocked on exact-PR review, owner disposition of public
runner-name metadata, fresh explicit dispatch authorization, and a pre-dispatch
check that no deployment or verification job is active or pending.

## Delivery status

- GitHub-hosted CI: use the checks attached to the exact current head of
  [Draft PR #11](https://github.com/Madeena-software/mpips/pull/11); no local
  test, format, lint, or mypy commands were run.
- Independent review: required before merge.
- Production diagnostic and service recovery: not authorized by this task.
- Separate Compose Release Service: still an unapproved proposal.
