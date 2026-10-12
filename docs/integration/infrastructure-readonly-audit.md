# Production infrastructure read-only audit

This manually dispatched workflow prints coarse classifications from the
existing production runner. It is an initial inventory for planning a possible
MPIPS Release Service; it is not an approval to build or deploy one.

## Coverage and limits

It classifies Linux compatibility, CPU capacity and current load, total and
available RAM, free space on the root and MPIPS runtime filesystems, Docker and
Compose availability, a coarse running-container count, expected MPIPS
services and networks, local listener status for ports 8014, 80 and 443, and
aggregate container health when available.

It does not inspect complete host, process, network, container, or filesystem
inventories. It does not inspect environment or credential files, Docker logs,
patient data, or clinical workspaces. It makes no external network requests,
clinical requests, conversions, or load tests. It does not change host files,
services, containers, networks, packages, firewall, TLS, DNS, or runner
configuration, and uploads no report or artifact.

The repository does not identify an owner-approved Release Service network
range or an approved HTTPS ingress identity/configuration source. The workflow
therefore reports candidate network conflict and approved HTTPS ingress as
`unknown`. A listener on port 443 is not proof of a reverse proxy, approved
certificate, or valid TLS service. The audit cannot certify total host
capacity, peak-load capacity, or production deployment readiness.

## Public-log handling

This is a public repository, so Actions logs and summaries are public. The
collector captures command output internally and prints only fixed categories
or `unknown`; it suppresses command errors and does not print hostnames,
addresses, IDs, usernames, command lines, raw output, detailed exceptions,
credentials, or exact filesystem inventories. Docker commands run with a
minimal environment that excludes host Docker context and credential-path
overrides. Do not add raw debug output or artifacts.

## Review and dispatch

Before any use, review the workflow and
[`audit_infrastructure_readonly.py`](../../scripts/audit_infrastructure_readonly.py)
at the `main` revision. Confirm the manual-only trigger, main-branch guard,
production runner labels, minimal permissions, pinned checkout, timeout,
read-only command list, output allowlist, and absence of secrets or uploads.
Run only the synthetic/static tests on a GitHub-hosted runner during review.

The workflow does not share the deployment concurrency group: GitHub may
replace an existing pending run in that group when another run is queued. Its
separate queue prevents audit runs from canceling one another, but does not
serialize an audit against deployment or verification. Before dispatch, the
repository owner must separately authorize the run and ensure no production
deployment or verification is active or pending. Select `main` in the manual
dispatch UI. A dispatch against another ref is skipped by the job condition.

## Interpreting categories

| Measurement | Categories |
|---|---|
| CPU capacity | `small` (up to 2 logical CPUs), `medium` (3–8), `large` (more than 8), `unknown` |
| CPU architecture | `x86_64`, `arm64`, `other`, `unknown` |
| RAM total / available | below 8 GiB, 8–16 GiB, 16–32 GiB, above 32 GiB, `unknown` |
| Filesystem available | `low` (under 10 GiB), `moderate` (10–50 GiB), `sufficient` (over 50 GiB), `unknown` |
| Approaching capacity | `yes` when free space is under 10 GiB or under 10% of the filesystem; otherwise `no`, or `unknown` if either required measurement is unavailable |
| Current CPU/load | `low` (load/core below 0.7), `moderate` (0.7 to under 1.5), `high` (1.5 or more), `unknown` |
| Running containers | `none`, `1–5`, `6–15`, `above 15`, `unknown` |
| Docker, Compose, ports, services and networks | `yes`/`no`, `present`/`missing`, or `unknown` as labeled |
| Network conflict / approved HTTPS ingress | `unknown` until owner-approved candidate ranges and ingress authority are established |

Free-space labels describe current availability only, not total volume size or
future demand. Load is a short snapshot. Missing commands, permission errors,
timeouts, and unavailable paths produce `unknown` or a non-success
classification; they do not fail open as a positive capacity claim.

The separate Compose Release Service remains a proposed architecture. This
inventory does not select its topology, network range, storage, ingress,
identity, retention, or operating policy.
