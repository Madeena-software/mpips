---
title: MPIPS Phase B2 owner evidence request for Release Service placement
status: Draft — owner evidence requested
date: 2026-10-13
baseline: 691cb3aeda6cbd1b7ecf8e4eb7dbfa1e1a789fbb
---

# MPIPS Phase B2 owner evidence request

## Purpose

Request existing records needed to decide whether a standalone Release Service Compose project can safely share the existing production host. Prefer monitoring exports, approved infrastructure diagrams, IPAM records, and service runbooks. This request does not authorize new production inspection, diagnostic dispatch, infrastructure changes, implementation, or deployment. Unknown or unavailable evidence remains unknown; it is not a pass.

The architecture and placement proposal remain Draft. The stopped MPIPS API incident is an independent workstream and is not a prerequisite for this evidence request.

## Requested existing evidence

Please provide the following through the approved restricted evidence channel. Summaries and references are sufficient when they establish the decision; do not include credentials, private keys, raw client identifiers, or unrelated host data.

| Topic | Minimum evidence requested | Authoritative source / owner |
|---|---|---|
| Representative capacity | Monitoring records covering an owner-selected representative period and known peak windows for CPU, memory, disk headroom/growth, and network utilization; identify existing service budgets and acceptable interference criteria. Include whether measurements overlap clinical workloads, backup, maintenance, or update windows. | Infrastructure monitoring and MPIPS/MHCS service owners |
| Fleet and distribution demand | Current supported installation count as aggregate bands, expected rollout cadence/window, largest and typical signed package sizes, and expected peak concurrent downloads/retries. | Grabber/release operations and product owner |
| Ingress and naming | Approved ingress design and operator, current listener/port ownership records for required entry points, DNS zone/name ownership, backend route boundary, and approval for this service’s use. | Network/ingress and DNS owners |
| TLS and identity | Certificate authority/lifecycle owner, renewal and expiry monitoring evidence, accepted TLS policy, client identity/authentication owner, credential rotation/revocation process, and relevant access-control approval. No certificate private material is requested. | PKI, identity, security, and release owners |
| Candidate subnet | Owner-proposed candidate CIDR plus authoritative IPAM allocation and conflict comparison against Docker networks, routed networks, and relevant reserved ranges. Record who approves allocation. Do not reserve a subnet for this request. | Network/IPAM owner |
| Storage and recovery | Artifact/staging/log/backup capacity, approved retention and growth limits, backup destination/isolation and operator, and approved numeric RPO/RTO with evidence that restore can meet them. | Storage/backup owner and service owner |
| Operations | Named service and escalation owners, monitoring/alert destinations and response expectations, maintenance/change windows, runbook ownership, patching responsibility, backup/restore responsibility, and shared-host failure-domain acceptance or rejection. | Infrastructure and MPIPS/MHCS service owners |

If existing records cannot answer a request, identify the missing evidence and its accountable owner. A separate diagnostic proposal can be reviewed later; this document is not authorization to collect it.

## Decision use and verification stages

### Before deployment: design and placement verification

Use owner-approved records to decide whether capacity budgets fit, whether network isolation and a candidate subnet are valid, whether ingress/DNS/TLS/client identity have accountable operators, whether storage/backup meet retention and recovery objectives, and whether operational ownership accepts shared-host risk. Record source, date/coverage, owner, and limitations. Do not infer approval from occupied ports, a single low-load snapshot, or historical audit categories.

Every same-host gate needs affirmative evidence and owner approval. If a gate fails or stays unknown, do not approve same-host placement; evaluate a separate VM or host and repeat applicable gates there. Placement acceptance still does not authorize implementation or deployment.

### After any separately authorized implementation: runtime verification

Runtime verification is a future, separately authorized activity under an approved implementation task and change plan. It would verify the deployed network attachments and denied paths, actual ingress and TLS behavior, authentication and revocation, resource limits under representative authorized load, artifact integrity and publication controls, backup restoration, alerts/runbooks, and rollback/recovery. It must not be represented as pre-deployment evidence, and this request does not authorize access or dispatch.

## Provenance and boundary

The placement plan references prior audit run `38265842527` and later read-only audit run [`38311939625`](https://github.com/Madeena-software/mpips/actions/runs/38311939625). The latter's Actions metadata records a successful run at source revision `0e33129ff48ba99efc238b7210d9018dbd4ad26b`; no additional host-result claims are made here. The API incident remains independent.

No production runner was accessed, no diagnostic dispatched, no infrastructure modified, and no Release Service implemented or deployed to prepare this request. No executable implementation task is created. Owner responses and architecture approval remain prerequisites to further implementation planning.
