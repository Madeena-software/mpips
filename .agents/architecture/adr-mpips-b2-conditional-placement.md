---
title: MPIPS Release Service conditional placement preference
status: Owner decision recorded — placement gates pending
date: 2026-10-13
decision: Prefer existing production host as initial candidate, conditional on evidence and approvals
baseline: 599682455086e47dcd80176e910a3c1144652644
---

# MPIPS Release Service conditional placement preference

## Decision source and scope

This record captures the human-supplied owner preference in the Phase B2 placement request. It is a conditional preference for planning and evidence gathering, not final placement approval, an amendment that approves the overall Draft architecture, an implementation task, or production authorization.

The broader design remains in [ADR — MPIPS Production Release Service](adr-mpips-release-service-production.md). The bounded evidence-gathering plan is in [MPIPS Release Service placement evidence plan](mpips-release-service-placement-evidence-plan.md).

## Recorded owner preference

**Decision:** Prefer the existing production server as the initial candidate for the Phase B2 Release Service, using a standalone Docker Compose project.

This preference is conditional on all of the following being demonstrated and approved:

- Representative capacity evidence supports host sharing.
- A dedicated non-overlapping network and isolation from MPIPS/MHCS workloads can be demonstrated.
- An approved private ingress path is available without broadening access to clinical workloads.
- DNS, TLS/certificate, ingress, firewall, and network ownership are established.
- Durable storage, backup, restoration, monitoring, maintenance, and operational ownership requirements are satisfied.
- Deployment and operation do not disrupt existing MPIPS/MHCS services.

**Fallback:** Select a separate VM or physical host if any condition is not met, remains unknown at the placement gate, or the infrastructure/security owner judges shared-host risk unacceptable.

## Authority boundary and status

This owner preference authorizes documentation and planning only. It does not authorize production inspection or dispatch, provisioning, subnet reservation, infrastructure/service modification, Release Service implementation, or deployment. Each production evidence action requires separate explicit authorization and the applicable review and pre-dispatch checks.

The overall Release Service architecture ADR remains **Draft — Architecture Review Required**. Host capacity, subnet allocation, ingress ownership, and final placement remain unapproved until the evidence and decisions in the placement plan are closed. The MPIPS API incident remains an independent workstream.

**Decision owner:** Infrastructure/service owner and designated security/release authorities

**Recorded by:** Human-supplied Phase B2 request

**Decision state:** Conditional preference recorded; acceptance gates open
