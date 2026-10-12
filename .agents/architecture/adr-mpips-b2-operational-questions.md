---
title: MPIPS B2 service state and ingress questions
status: Draft
date: 2026-10-12
decision: Pending owner review
---

# MPIPS B2 service state and ingress questions

## Status

**Draft — no architecture decision is approved by this record.**

## Context

The first read-only infrastructure audit (GitHub Actions run
`38265842527`, source revision `bfe5237f86a4a535c76c9368099a65e0b1fad653`)
reported expected services as missing while reporting aggregate container
health as healthy. It returned `unknown` for listeners on ports 8014, 80 and
443. This output does not establish that MPIPS is down, that the collector is
wrong, or which process owns any listener.

The collector source at that revision queried running project containers for
service labels, then inspected health for all running containers with the
project label. Therefore those categories did not describe the same set of
containers. Its listener parser examined every row from one host-wide `ss`
listing before filtering by target port, so malformed unrelated rows could
make all target-port classifications unknown. These are source-level
limitations; they do not resolve live production state.

## Questions for the owner and architecture review

1. Are the API and Redis containers present, stopped, absent, or represented
   under unexpected Compose project/service labels? Which approved evidence
   should identify the intended deployment instance?
2. What system or operator owns listeners on ports 80 and 443, and what
   evidence identifies the approved HTTPS ingress, TLS termination, and
   certificate lifecycle?
3. Is the host-side API listener on port 8014 exclusively loopback-bound in
   the deployed state, and what source of truth should corroborate the
   namespace/listener observation?
4. Which candidate network ranges, if any, are approved for a future separate
   Release Service, and who owns conflict approval?

## Options to evaluate

- Obtain a separately authorized, sanitized read-only diagnostic after the
  collector correction is independently reviewed and merged.
- Use owner-provided deployment/runtime evidence that can be reviewed without
  contacting the production runner.
- Keep service identity, ingress identity, or network conflict `unknown`
  until authoritative evidence and owner decisions are available.

No option is selected here. A diagnostic classification can inform an
architecture decision but does not itself approve service recovery, ingress,
network allocation, or deployment.

## Release Service proposal status

A separate single-server Compose Release Service remains the preferred
proposal for future analysis. It is not an approved deployment or architecture
decision. This record does not authorize an executable Release Service task.

## Consequences and next step

Service presence, service health, ingress ownership, and candidate network
conflict remain unresolved until the owner reviews the questions and provides
appropriate evidence or decisions. Any later production diagnostic requires a
new explicit owner authorization. Before a dispatch, verify no production
deployment or verification workflow is active or pending.

**Decision owner:** Repository owner / designated architecture authority  
**Approval:** Pending
