---
title: Runtime-Neutral Software Delivery Protocol
document_id: SD-PROTOCOL-001
version: 2.2
status: approved-reference
language: en-US
last_updated: 2026-08-10
applies_to:
  - software repositories
  - services and APIs
  - data pipelines
  - libraries and packages
  - internal tooling
  - documentation repositories
authority_note: Approved repository authority governs intended behavior. Observed repository evidence governs claims about current implementation reality. Neither silently overrides the other. Repository-specific policy MAY strengthen this protocol but MUST NOT silently weaken applicable authority, safety, compliance, or release requirements.
---

# Runtime-Neutral Software Delivery Protocol

> **Canonical delivery lifecycle**
>
> Business Sources → PRD → Requirement Registry & Matrices → Architecture & Repository Context → Delivery Planning → Validated Task → Execution & Verification → Implementation Review → Remediation or Acceptance → New Accepted Baseline → Separate Release Gate

## 1. Purpose

This document defines a reusable, runtime-neutral software-delivery protocol for work performed by humans, AI coding agents, or mixed teams.

The protocol governs **what must be understood, decided, bounded, verified, reviewed, and accepted** before software delivery advances. It deliberately does **not** prescribe generic coding technique, model selection, tool usage, test-first methodology, subagent orchestration, or other runtime-specific execution mechanics.

The protocol is designed to work with:

- greenfield repositories;
- repositories already under active development;
- mature repositories with established documentation and accepted baselines;
- legacy repositories with incomplete or inconsistent documentation;
- monorepos and multi-service systems; and
- non-application repositories such as libraries, data pipelines, or documentation projects.

Its goals are to ensure that:

- business intent is not translated directly into coding without analysis;
- product behavior and requirements remain traceable to legitimate sources;
- architecture, ownership, and authority remain explicit;
- delivery work is bounded before implementation begins;
- implementation evidence is based on observation rather than assertion;
- remediation does not silently become scope expansion;
- accepted implementation becomes an exact new baseline; and
- implementation acceptance remains distinct from production release.

---

# 2. Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are normative.

- **MUST / MUST NOT** define protocol requirements.
- **SHOULD / SHOULD NOT** define strong defaults that may be overridden when there is an explicit, recorded reason.
- **MAY** defines an allowed option.

Repository-specific policy MAY strengthen this protocol. It MUST NOT silently weaken a repository's approved authority, security, compliance, or release requirements.

---

# 3. Scope and non-goals

## 3.1 What this protocol governs

This protocol governs:

- intended-authority and observed-evidence model;
- repository entry and maturity assessment;
- business framing;
- product requirements;
- atomic requirement registration;
- source coverage and traceability;
- architecture and repository context;
- delivery planning;
- Work Package and MVP-oriented planning;
- executable-task readiness;
- execution boundaries;
- verification evidence;
- implementation review;
- remediation;
- acceptance and baseline progression; and
- release separation.

## 3.2 What this protocol does not govern

This protocol does not define:

- which AI model must be used;
- which coding agent or IDE must be used;
- how an agent brainstorms;
- how an agent performs TDD;
- how an agent debugs;
- how an agent uses worktrees;
- how an agent delegates to subagents;
- how an agent invokes MCP tools;
- how source code should be formatted beyond repository policy; or
- vendor-specific instruction discovery.

Those concerns belong to the execution runtime, its installed methodology, repository tooling, or repository-specific instructions.

---

# 4. Authority model

## 4.1 Repository authority and implementation evidence

The repository contains two distinct classes of material that MUST NOT be collapsed into a single authority hierarchy.

### Intended authority

Approved repository authority governs what the system is intended or permitted to do.

Depending on the repository, intended authority MAY include:

1. approved business sources and decision records;
2. approved PRD or equivalent product specification;
3. approved requirement registry and matrices;
4. approved architecture and repository instructions;
5. approved delivery plan, roadmap, or gap register; and
6. the published executable task governing the current work.

### Observed implementation evidence

Observed repository evidence governs claims about what currently exists, what changed, and what was actually verified.

Depending on the repository, observed evidence MAY include:

1. source code;
2. migrations;
3. configuration;
4. tests;
5. runtime observations;
6. commit history;
7. available CI evidence; and
8. accepted-baseline records and their immutable repository revisions.

Observed evidence MUST NOT silently override intended authority.

Intended authority MUST NOT be treated as evidence that implementation already conforms.

Chat transcripts, summaries, generated plans, derived indexes, search results, and agent memory are supporting context unless the repository explicitly promotes them to an approved artifact.

## 4.2 Intended authority versus observed reality

Approved business, product, requirement, and architecture artifacts define the **intended system state**.

Source code, configuration, migrations, tests, runtime observations, and deployed behavior define the **observed implementation state**.

When intended authority and observed reality disagree:

- the discrepancy MUST be recorded explicitly;
- the agent MUST NOT silently modify documentation to justify the code;
- the agent MUST NOT assume the code is compliant merely because an approved requirement exists; and
- the discrepancy MUST be resolved through planning, remediation, or an explicit authority decision.

Existing implementation MUST NOT be treated as retroactive justification for a missing requirement.

Approved requirements MUST NOT be treated as evidence that implementation already satisfies them.

---

# 5. Core delivery invariants

## 5.1 Do not jump from intent to implementation

Delivery MUST remain traceable through the concerns that are materially applicable:

```text
business intent
→ product behavior
→ atomic requirements
→ architecture and ownership
→ bounded delivery objective
→ validated task
→ implementation
→ verification evidence
→ review verdict
→ accepted baseline
```

## 5.2 Strict semantics, proportional artifacts

The protocol is semantically strict but artifact-light.

Every required delivery concern MUST be addressed, but the depth, separation, and formality of documentation SHOULD be proportional to:

- repository complexity;
- change impact;
- security exposure;
- privacy exposure;
- regulatory or contractual obligations;
- operational criticality;
- reversibility; and
- delivery risk.

A small repository MAY satisfy several protocol responsibilities in one compact approved document.

A complex or regulated system MAY require separate registries, matrices, ADRs, evidence records, and release controls.

The absence of a separate file does not imply the absence of the responsibility.

## 5.3 Logical artifacts are not mandatory physical files

Protocol artifacts are logical responsibilities, not mandatory filenames or directory paths.

A repository MAY:

- combine several artifact responsibilities in one document;
- split one responsibility across multiple documents; or
- use existing repository-native conventions.

This is allowed only when authority, status, ownership, and traceability remain unambiguous.

## 5.4 Existing repository conventions come first

This protocol MUST NOT force an existing repository to reorganize valid documentation merely to match a template directory structure.

Existing locations and naming conventions MUST be reused when they adequately represent the required responsibilities.

New locations SHOULD be introduced only when no suitable repository convention exists.

## 5.5 Evidence must be observed

Success MUST NOT be claimed solely from:

- commit messages;
- agent summaries;
- the existence of source code;
- hidden or unobserved actions;
- tests that do not execute the claimed boundary;
- local results described as CI; or
- documentation that has not been verified against implementation reality.

## 5.6 Acceptance is not release

```text
accepted implementation
≠ Work Package complete
≠ production ready
≠ deployed
≠ released
```

Release authorization remains a separate gate.

---

# 6. Repository entry and maturity assessment

## 6.1 No mandatory restart from zero

Existing repositories MUST NOT be forced to recreate valid workflow artifacts.

Before planning new implementation work, the planner SHOULD inspect existing repository evidence and map it to the protocol.

The repository MUST continue from the earliest gate that is:

- unmet;
- materially unreliable;
- stale enough to affect downstream work; or
- reopened by a change in approved authority.

Valid upstream artifacts MUST be reused.

## 6.2 Entry patterns

### Greenfield repository

A greenfield repository will commonly begin near the start of the lifecycle:

```text
Business Sources
→ PRD
→ Requirements
→ Architecture
→ Delivery Planning
→ Task
```

### In-progress repository

An in-progress repository SHOULD first reconcile what already exists:

```text
inspect repository
→ map existing artifacts
→ identify valid, stale, partial, or missing concerns
→ repair only what is necessary
→ continue from earliest unreliable gate
```

### Mature repository

A mature repository MAY begin from a new source, change request, incident, or accepted baseline:

```text
new source or change
→ impact analysis
→ affected requirements and architecture
→ delivery planning
→ next task
```

### Legacy repository

A legacy repository MAY have extensive code with incomplete authority artifacts.

The planner SHOULD distinguish:

- known intended behavior;
- inferred behavior;
- observed behavior;
- undocumented behavior;
- conflicts; and
- decisions requiring approval.

Inference MUST NOT be silently promoted to approved authority.

---

# 7. Artifact model

## 7.1 Artifact responsibilities

| Artifact responsibility | Primary question | Typical content |
|---|---|---|
| Business source | Why is this change or system needed? | Contract, regulation, stakeholder decision, incident, operational problem, constraint, target outcome. |
| Business framing | What problem and decision boundary are approved? | Problem, owner, goals, success metrics, assumptions, open decisions, non-goals. |
| PRD / product specification | What behavior should users or systems experience? | Actors, journeys, functional behavior, NFRs, rules, edge cases, scope, acceptance. |
| Requirement registry | What are the atomic obligations? | Stable ID, statement, type, source, owner, priority, dependency, status, verification method. |
| Source coverage mapping | Are approved sources represented? | Source-to-requirement coverage, exclusions, uncovered source detection. |
| Traceability mapping | Can delivery be traced end to end? | Source ↔ PRD ↔ requirement ↔ architecture ↔ delivery objective ↔ task ↔ implementation ↔ evidence ↔ baseline. |
| Dependency mapping | What must exist or be decided first? | Internal/external dependency, data contract, migration, infrastructure, policy, approval. |
| Decision record / ADR | Why was a material design choice made? | Options, trade-offs, decision, owner, consequences, revisit trigger. |
| Architecture / repository context | Where and under what authority does behavior live? | Module boundaries, source of truth, trust boundaries, stack, conventions, repository policy. |
| Delivery plan | How will approved requirements be delivered? | Work Packages, MVPs, sequencing, ownership, dependencies, risk. |
| Gap register | What is deliberately incomplete? | Gap ID, impact, temporary control, target phase, closure criteria, status. |
| Executable task | What bounded assignment may now be implemented? | Baseline, objective, scope, authority inputs, constraints, acceptance, verification, stop conditions. |
| Implementation evidence | What actually happened? | Source changes, tests, checks, logs, observed outcomes, limitations. |
| Accepted baseline record | Which exact repository revision is accepted? | Immutable revision, bounded acceptance statement, evidence references, open gaps, release status. |

## 7.2 Authority-bearing artifact lifecycle

Authority-bearing specification artifacts SHOULD use an explicit lifecycle such as:

- `Draft`;
- `In Review`;
- `Approved`;
- `Superseded`; and
- `Retired`.

AI-generated or reconstructed business, product, requirement, and architecture artifacts MUST remain `Draft` until approved by the designated authority.

Draft or In Review artifacts MUST NOT silently become authoritative inputs for executable implementation work.

## 7.3 Artifact-type-specific lifecycle

Not every artifact SHOULD use the same lifecycle.

For example:

- specification artifacts use approval-oriented states;
- requirements may also track delivery states such as planned, implemented, verified, accepted, deferred, or rejected;
- tasks use execution-oriented states;
- evidence records represent observed results rather than approval states; and
- accepted baselines identify exact accepted revisions.

Repositories MAY define more specific states when needed.

---

# 8. Traceability model

## 8.1 Progressive traceability

Traceability is mandatory, but downstream links MAY legitimately be absent before delivery reaches those stages.

For example, an approved requirement that has not yet been implemented may have:

```text
Source       ✓
PRD          ✓
Owner        ✓
Task         —
Code         —
Test         —
Accepted     —
```

Once a requirement is claimed as implemented, verified, or accepted, the corresponding downstream evidence MUST exist.

## 8.2 Minimum end-to-end trace

Important requirements SHOULD be traceable through:

```text
Business Source
→ PRD section or product decision
→ Requirement ID
→ Owning architecture/module
→ Work Package and/or MVP objective
→ Executable task
→ Implementation revision
→ Verification evidence
→ Accepted baseline
```

## 8.3 Bidirectional traceability

Traceability MUST support both directions:

- **forward traceability**: approved intent can be followed toward implementation and evidence;
- **reverse traceability**: implementation, tests, and tasks can be followed back to legitimate authority.

A requirement with no implementation may be an open delivery gap.

Implementation with no legitimate requirement or approved source may be an undocumented, unauthorized, obsolete, or unresolved behavior and MUST be reviewed rather than retroactively justified.

---

# 9. Quality-gate model

Quality gates provide stable, evidence-based protocol states.

A gate is not considered passed merely because a corresponding document exists.

## 9.1 Stable gate identifiers

| Gate | Name | Primary condition |
|---|---|---|
| B0 | Business Framing | Problem, authority, outcome, constraints, exclusions, and material decisions are sufficiently established. |
| P1 | Product Definition | Product behavior, actors, scope, business rules, failure behavior, and observable acceptance are sufficiently defined. |
| R2 | Requirements Traceability | Atomic requirements have stable IDs, legitimate sources, owners, dependencies, and verification methods. |
| A3 | Architecture Clarity | Module/data authority, trust boundaries, relevant architecture, and repository constraints are sufficiently unambiguous. |
| D4 | Delivery Readiness | The current MVP- or Work-Package-oriented delivery objective is bounded, dependency-aware, and reviewable. |
| T5 | Task Readiness | A task satisfies the executable-task contract and is published for execution. |
| E6 | Execution Verification | A reviewable implementation state and truthful verification evidence are ready for Reviewer evaluation; a valid stop with no reviewable implementation returns to planning without passing E6. |
| V7 | Implementation Review | The implementation has been reviewed against the correct baseline, task revision, authority, evidence, and available CI. |
| R8 | Remediation Closure | Required bounded remediation or evidence closure has been completed and re-reviewed. |
| A9 | Baseline Acceptance | The reviewed implementation revision is accepted as the next immutable development baseline. |
| G10 | Release Approval | Applicable production or publication release checks and approvals have passed. |

## 9.2 Gate states

Repositories MAY represent gate states using values such as:

- `pending`;
- `in_review`;
- `blocked`;
- `passed`;
- `reopened`; and
- `not_applicable` with recorded rationale.

## 9.3 Earliest unreliable gate rule

When adopting the protocol into an existing repository, delivery SHOULD continue from the earliest gate that is unmet or materially unreliable.

Downstream work MAY remain useful evidence, but it MUST NOT be used to pretend an upstream authority gap does not exist.

## 9.4 Blocking versus non-blocking unresolved items

Open decisions, assumptions, and dependencies MUST be classified by delivery impact.

A gate MUST remain blocked when an unresolved item can materially alter:

- authority;
- behavior;
- architecture;
- scope;
- safety;
- acceptance criteria;
- feasibility; or
- downstream ownership.

Non-blocking items MAY remain open when they are explicitly recorded with:

- an owner;
- impact;
- current assumption if any;
- resolution trigger; and
- the latest stage by which they must be resolved.

---

# 10. Phase 01 — Business Sources and Framing

## Objective

Establish the legitimate reason for the system or change, the accountable authority, the expected outcome, and the relevant constraints.

## Typical inputs

- contracts or agreements;
- regulations or policy;
- stakeholder decisions;
- incidents or audit findings;
- operational pain points;
- customer requests;
- market constraints;
- existing processes;
- service commitments; and
- business metrics.

## Required concerns

The planning process MUST distinguish, where relevant:

- facts;
- assumptions;
- approved decisions;
- unresolved decisions;
- constraints;
- risks;
- goals;
- non-goals;
- accountable owners; and
- source authority.

Material conflicts between sources MUST be recorded rather than silently resolved by the agent.

## Gate B0

B0 passes when the next product-definition work can proceed without inventing material business decisions.

---

# 11. Phase 02 — Product Requirements Document

## Objective

Translate approved business intent into product or system behavior that can be accepted or rejected.

## Required concerns

A PRD or equivalent product specification SHOULD address, as applicable:

- problem statement;
- goals and non-goals;
- actors and roles;
- user or system journeys;
- functional behavior;
- non-functional requirements;
- business rules;
- data classification and sensitivity;
- authorization expectations;
- failure behavior;
- edge cases;
- external dependencies;
- observability expectations;
- scope and exclusions;
- acceptance criteria; and
- success metrics.

## Product boundary

The product specification SHOULD describe behavior and outcomes rather than unnecessary internal implementation detail.

Implementation detail MAY appear when it is itself a business, regulatory, interoperability, security, or contractual constraint.

## Approval rule

AI MAY draft or reconstruct a PRD, but the artifact MUST remain Draft until the designated product authority approves it.

## Gate P1

P1 passes when product behavior is sufficiently explicit to decompose into atomic requirements without inventing material product decisions.

---

# 12. Phase 03 — Requirement Registry and Matrices

## Objective

Translate approved product and business authority into atomic, sourced, owned, and verifiable requirements.

## 12.1 Requirement registry

Each material requirement SHOULD include:

| Field | Meaning |
|---|---|
| ID | Stable identifier that does not change merely because sequencing changes. |
| Statement | One atomic, unambiguous obligation or constraint. |
| Type | Functional, security, privacy, architecture, data, operational, compliance, quality, or another repository-defined type. |
| Source | Approved business source, product decision, or PRD reference. |
| Owner | Owning module, service, team, or accountable authority. |
| Priority | Approved priority, class, or phase. |
| Status | Artifact-appropriate lifecycle state. |
| Dependency | Required data, decision, module, migration, integration, policy, or external condition. |
| Verification | How satisfaction will be demonstrated. |
| Notes | Bounded rationale or clarification. |

Requirements MUST use stable IDs.

Requirements MUST NOT be renumbered merely because roadmap sequencing changes.

## 12.2 Source coverage

Source coverage SHOULD identify:

- approved source content mapped to requirements;
- source content intentionally excluded with rationale;
- uncovered source content; and
- requirements with no legitimate source.

## 12.3 Traceability mapping

The repository MUST provide sufficient traceability to follow important requirements through delivery as their lifecycle progresses.

A dedicated traceability matrix MAY be used but is not mandatory if equivalent traceability is unambiguous elsewhere.

## 12.4 Dependency mapping

Dependencies SHOULD cover applicable concerns such as:

- internal modules or services;
- external APIs;
- data contracts;
- migrations;
- infrastructure;
- policy;
- privacy or legal decisions;
- security approvals;
- operational processes;
- third-party availability; and
- release environments.

## 12.5 Decision records

Material design choices with meaningful alternatives or consequences SHOULD be recorded using an ADR, decision log, or equivalent artifact.

## Rules

- Requirements MUST be sufficiently atomic to support ownership and verification.
- Each requirement MUST have a legitimate source or explicit approved rationale.
- Requirement matrices MUST NOT be cosmetically rewritten merely to match existing implementation.
- Deferred requirements MUST remain visible.

## Gate R2

R2 passes when approved requirements can be traced to legitimate authority, assigned to accountable ownership, and evaluated by defined verification methods.

---

# 13. Phase 04 — Architecture and Repository Context

## Objective

Define where requirements are implemented, who owns relevant data and behavior, which trust boundaries apply, and which repository constraints govern delivery.

## 13.1 System and module architecture

Relevant architecture SHOULD identify, as applicable:

- monolith, modular monolith, service, worker, library, pipeline, or package boundaries;
- module ownership;
- integration direction;
- synchronous and asynchronous communication;
- deployment topology;
- availability expectations; and
- failure isolation.

## 13.2 Data authority

Important data SHOULD have explicit answers for:

- source of truth;
- mutation authority;
- owner;
- projections or consumers;
- synchronization mechanism;
- consistency expectations;
- retention; and
- audit responsibility.

A module MUST NOT assume ownership merely because it has UI access, database access, or a local projection.

## 13.3 Security and trust boundaries

Architecture SHOULD document applicable concerns such as:

- authentication;
- authorization;
- caller identity;
- trusted and untrusted inputs;
- protected data;
- secret handling;
- session and credential rules;
- audit;
- idempotency;
- failure response;
- network boundaries;
- external integrations; and
- privacy controls.

## 13.4 Technology and repository conventions

Relevant context SHOULD identify:

- language and supported version;
- framework;
- persistence technology;
- queue or asynchronous processing;
- storage;
- testing framework;
- formatter and linter;
- dependency policy;
- migration policy;
- API conventions;
- error conventions;
- build and test commands; and
- repository-specific protected paths or policies.

## 13.5 Repository context map

When this protocol is packaged under `.agents/`, `.agents/context/project.md` SHOULD act as a concise, verified map to the repository's actual authoritative sources and current delivery state.

It SHOULD NOT duplicate large authoritative documents unnecessarily.

## Approval rule

AI MAY draft or reconstruct architecture context, but authority-bearing architecture decisions MUST remain Draft until approved by the designated technical authority.

## Gate A3

A3 passes when delivery planning can proceed without inventing material architecture, ownership, trust-boundary, or repository-policy decisions.

---

# 14. Phase 05 — Delivery Planning

## Objective

Select a bounded, dependency-aware delivery objective that can be implemented and reviewed without losing traceability to approved requirements.

## 14.1 Work Package

A **Work Package** groups approved requirements toward a broader expected end-state.

A Work Package:

- SHOULD be more stable than individual execution tasks;
- MAY span multiple delivery cycles;
- MUST retain visibility of incomplete requirements; and
- MUST NOT be marked complete merely because one bounded slice is accepted.

## 14.2 MVP

An **MVP** is a bounded vertical delivery slice that produces a usable or demonstrable outcome.

An MVP MAY cross interface, application, domain, persistence, authorization, audit, and verification boundaries when necessary to produce one coherent outcome.

Layer-only delivery SHOULD be avoided unless the layer itself is the approved outcome.

## 14.3 Planning mode selection

The protocol does not globally require MVP-first or Work-Package-first planning.

For each planning cycle, the planner MUST identify the current delivery objective as one of:

- **MVP-oriented**: optimize for a bounded vertical usable outcome; or
- **Work-Package-oriented**: optimize for coherent progress or completion toward the broader requirement end-state.

The selected mode MUST be explicit enough that task scope and acceptance can be evaluated correctly.

## 14.4 Roadmap and sequencing

Delivery planning SHOULD make applicable sequencing visible, including:

- current accepted baseline;
- target outcome;
- included scope;
- excluded scope;
- dependency ordering;
- approval requirements;
- risk;
- target gaps; and
- expected evidence.

## 14.5 Gap register

Deliberately incomplete behavior SHOULD remain visible through a gap register or equivalent mechanism.

A material gap SHOULD identify:

- stable ID;
- affected component or flow;
- impact;
- temporary control if any;
- target phase;
- status;
- closure criteria;
- revisit trigger; and
- evidence reference.

Unavailable external dependencies MUST become explicit dependencies, gaps, or approval blockers rather than invented contracts.

## 14.6 Task granularity

A task MUST represent one coherent delivery objective.

A task MAY span multiple files, modules, and technical steps when they are necessary to deliver that single objective.

Unrelated or independently valuable outcomes SHOULD be separate tasks.

Task size MUST NOT be defined solely by file count, line count, or estimated minutes.

## 14.7 Parallel planning

A planner MAY publish multiple tasks when they are independently executable and independently reviewable.

Parallel tasks MUST make explicit:

- dependencies;
- sequencing constraints;
- overlapping mutation surfaces;
- shared data or schema assumptions; and
- integration expectations.

Tasks with unresolved execution dependencies or materially conflicting write scope MUST be sequenced rather than executed concurrently.

## Gate D4

D4 passes when the selected delivery objective is sufficiently bounded, dependency-aware, authority-aligned, and reviewable to be converted into an executable task.

---

# 15. Phase 06 — Validated Executable Task

## Objective

Create a bounded delivery contract that allows an executor to implement the selected objective without inventing missing product, requirement, architecture, or approval decisions.

## 15.1 Planner versus executor responsibility

The planner owns the delivery contract:

```text
WHAT outcome is required
WHY it is legitimate
WHAT authority governs it
WHAT is in scope
WHAT is out of scope
WHAT must remain unchanged
WHAT must be verified
WHEN execution must stop
```

The executor retains bounded technical discretion over **HOW** to implement the task within approved architecture, repository conventions, and task constraints.

Task validation MUST NOT unnecessarily micromanage implementation details that are legitimately owned by the executor.

## 15.2 Minimum task contract

A validated task MUST define, directly or by unambiguous reference:

- objective;
- implementation baseline;
- authoritative inputs;
- parent delivery objective or requirement scope;
- included scope;
- excluded scope;
- preserved behavior;
- dependencies;
- assumptions;
- implementation constraints that are materially authoritative;
- acceptance criteria;
- verification requirements;
- approval requirements that still apply;
- stop conditions; and
- expected terminal outcomes.

Repository-specific task templates MAY include additional fields.

## 15.3 Validation semantics

A task is validated when its delivery contract is sufficiently explicit that implementation can proceed without inventing material upstream decisions.

Validation is a protocol property, not a specific tool command.

Repositories MAY use automated validators, schema checks, linters, or other tooling to enforce some or all of the contract.

## 15.4 Stable task paths and Git-backed history

The protocol MUST NOT require filename-based task versioning such as `task-v1.md`, `task-v2.md`, and `task-v3.md` merely to preserve revisions.

Task files SHOULD use stable, human-readable paths.

A task MAY be overwritten or updated as planning evolves.

Git or the repository's version-control system SHOULD preserve prior revisions.

Execution and review MUST remain tied to the exact task revision that governed that execution.

For Git repositories, task identity SHOULD be representable as:

```text
<task path> @ <immutable Git revision containing the governing task content>
```

The exact immutable task revision MAY be resolved externally from version-control history or orchestration metadata. The task body is not required to embed the commit SHA that contains itself.

A Draft placeholder such as `resolved when published` MAY be used before publication, but T5 MUST NOT pass and execution MUST NOT begin until the exact immutable governing task revision is resolvable.

## 15.5 Task lifecycle

A repository MAY represent task state using states such as:

```text
Draft
→ Validated / Published
→ In Execution
→ Review Required
→ Accepted
```

or:

```text
Draft
→ Validated / Published
→ In Execution
→ Review Required
→ Remediation Required
→ In Execution
→ Review Required
→ Accepted
```

Task lifecycle state and governing task revision are related but distinct concerns.

Execution and review MUST remain tied to the exact immutable task revision that governed the execution attempt.

A lifecycle-status update MUST NOT silently replace that governing revision.

Repositories MAY track execution and review state outside the task body when doing so preserves clearer contract identity.

When remediation materially changes the executable contract, the task MUST be republished as a new immutable governing task revision before renewed execution.

## 15.6 Publication and automatic execution

Once a task is validated and published, it MAY proceed automatically to execution.

Human approval is not a mandatory protocol gate between task publication and execution unless repository-specific policy requires it.

## 15.7 Mandatory implementation gate

Implementation-changing work MUST NOT begin without a published validated task.

This applies to material changes to:

- production source code;
- tests that alter implementation contract;
- migrations;
- configuration;
- infrastructure-as-code; and
- implementation documentation when it changes the delivery contract.

Read-only discovery, planning, analysis, and review MAY occur without an executable task when their purpose is to establish repository state, evaluate evidence, or produce the next task.

## Gate T5

T5 passes when the task satisfies the repository's applicable task contract, has an exact governing revision, and is eligible for execution.

---

# 16. Phase 07 — Execution and Verification

## Objective

Implement only the published bounded task and produce verification evidence sufficient for review.

## 16.1 Standard preflight

Before material mutation, the executor SHOULD establish applicable facts such as:

- repository identity;
- implementation baseline;
- task revision;
- current branch or equivalent workspace;
- current HEAD or immutable revision;
- working-tree state;
- staged, modified, and untracked files;
- overlapping work;
- required authority inputs;
- required tools and capabilities; and
- blocking dependencies.

If a precondition materially invalidates the task, execution MUST stop or return to planning.

## 16.2 Execution scope

The executor MUST:

- implement only the task's bounded objective;
- preserve explicitly excluded behavior;
- respect approved architecture and ownership;
- avoid inventing external contracts;
- avoid opportunistic unrelated refactoring; and
- stop when a material upstream decision is required.

## 16.3 Task changes during execution

If a task materially changes while execution is in progress, the current execution MUST NOT silently continue against a different contract.

The executor MUST identify the new task revision and either:

- re-evaluate the work against the revised task; or
- stop and return control to planning/review.

## 16.4 Verification strategy

Verification SHOULD use the smallest set of checks that directly demonstrates the changed boundary, plus targeted regressions appropriate to risk.

Applicable evidence MAY include:

- unit or domain tests;
- application-service tests;
- feature or HTTP tests;
- component tests;
- browser tests;
- architecture or security tests;
- integration tests;
- static analysis;
- formatting or linting;
- build checks;
- data validation;
- benchmarks; and
- runtime inspection.

## 16.5 Evidence recording

Evidence SHOULD record, when available and material:

- exact command or procedure;
- exact result;
- test counts;
- assertion counts;
- formatter or linter result;
- static-analysis result;
- build result;
- migrations or schema checks;
- runtime observations;
- local versus CI provenance;
- checks not run;
- limitations; and
- repository state.

## 16.6 Risk-proportional assurance

Verification depth MUST be proportional to risk and impact.

Higher-risk work requires stronger evidence and MAY require additional independent review or designated approval according to repository-specific policy.

Risk factors MAY include:

- security or authorization;
- privacy or sensitive data;
- financial impact;
- destructive data changes;
- schema or migration changes;
- public API compatibility;
- critical infrastructure;
- regulatory or contractual impact;
- irreversible operations; and
- production deployment consequences.

A technically small change MUST NOT automatically be classified as low risk.

## Gate E6

E6 passes when the bounded execution attempt has produced a reviewable implementation state and the Executor has accurately recorded the required and available verification evidence needed for Reviewer evaluation.

Individual checks MAY fail and explicit limitations MAY remain; E6 passage means the execution-and-evidence stage is sufficiently complete for V7 to determine the correct verdict, not that the implementation is already acceptable.

If the Executor reaches a valid stop condition and no reviewable implementation revision exists:

- the stop result and supporting evidence MUST be evaluated for accuracy;
- the execution attempt has reached a valid terminal state, but E6 MUST NOT be recorded as passed for implementation review;
- V7, R8, and A9 are `not_applicable` to that execution attempt;
- no implementation acceptance may be inferred; and
- control MUST return to the earliest affected planning gate or authority boundary.

---

# 17. Phase 08 — Implementation Review

## Objective

Evaluate the implementation revision against the correct implementation baseline, exact task revision, approved authority, observed behavior, verification evidence, and available CI.

## 17.1 Review inputs

Review SHOULD establish:

- implementation baseline revision;
- implementation revision under review;
- governing task path and task revision;
- relevant approved requirements;
- relevant architecture and repository policy;
- changed files and unrelated changes;
- verification evidence;
- tests not run;
- available CI or status checks; and
- material limitations.

## 17.2 Review boundary

The reviewer SHOULD evaluate applicable concerns such as:

- scope compliance;
- correctness;
- requirement satisfaction;
- authorization and ownership;
- data integrity;
- transactions and state transitions;
- idempotency and concurrency;
- audit behavior;
- protected data;
- error behavior;
- migration safety;
- API compatibility;
- user-visible behavior;
- test execution paths;
- negative behavior;
- regression risk;
- evidence quality; and
- documentation consistency.

## 17.3 Logical roles, not fixed models

Planner, Executor, and Reviewer are logical responsibilities.

A runtime MAY assign multiple logical responsibilities to the same model, agent, or session.

For example, the same session MAY act as Planner and Reviewer while a separate executor performs implementation.

Execution SHOULD be separated from review when practical.

Independent or fresh-context review MAY be used when higher assurance is required.

Repository-specific policy MAY require independent review for high-risk changes.

## 17.4 Verdicts

A review verdict SHOULD be explicit, for example:

- `accepted`;
- `accepted_with_documented_low_risk_limitation`;
- `remediation_required`;
- `blocked`; or
- `awaiting_authority_decision`.

A commit message or executor report alone is insufficient evidence for acceptance.

## Gate V7

V7 passes when the implementation has been reviewed against the correct boundaries and a defensible verdict has been recorded.

---

# 18. Phase 09 — Remediation and Evidence Closure

## Objective

Correct bounded findings without silently expanding the original delivery objective.

R8 applies only when the V7 verdict requires bounded remediation or evidence closure.

If V7 records `accepted` or `accepted_with_documented_low_risk_limitation`, and repository policy permits acceptance on that basis, R8 is `not_applicable` and delivery proceeds directly to A9.

If V7 records `blocked` or `awaiting_authority_decision`, control returns to the applicable planning gate, authority boundary, or evidence requirement rather than entering remediation by default.

## 18.1 Same-task remediation

When review identifies defects that remain within the original delivery objective, the planner/reviewer SHOULD update the existing task and republish it.

Git history SHOULD preserve the earlier task revision.

The revised task becomes the governing revision for the next execution attempt.

Examples of same-task remediation include:

- failed acceptance criteria;
- missing negative-path coverage;
- incorrect metadata within the same feature;
- incomplete audit behavior within the original scope;
- insufficient verification evidence; and
- bounded regression fixes required for the original objective.

## 18.2 New-scope boundary

A finding MUST return to Delivery Planning and become a separate task when it introduces:

- a materially different delivery objective;
- a new requirement;
- unrelated product scope;
- a materially new architecture decision;
- independent functionality; or
- scope that is valuable and reviewable separately.

Remediation MUST NOT become an uncontrolled roadmap-expansion mechanism.

## 18.3 Evidence closure

When the implementation revision is likely correct but required proof is incomplete, remediation MAY focus primarily on evidence closure, such as:

- execution-path tests;
- integration proof;
- browser evidence;
- exact audit association;
- CI confirmation; or
- corrected documentation claims.

## Gate R8

R8 passes when the bounded findings that prevented acceptance are closed and implementation, tests, evidence, and documentation are mutually consistent.

---

# 19. Phase 10 — Acceptance and New Baseline

## Objective

Establish the reviewed implementation revision as the next accepted development baseline.

## 19.1 Acceptance

A successful review verdict MAY establish the reviewed implementation revision as the new accepted baseline without mandatory human intervention, unless repository-specific policy requires additional approval.

Acceptance SHOULD confirm, as applicable:

- bounded behavior satisfies task acceptance criteria;
- required positive and negative paths are demonstrated;
- architecture and ownership remain valid;
- required focused and regression checks passed;
- material security and data boundaries are acceptable;
- documentation matches observed reality;
- unresolved limitations are recorded; and
- no unresolved finding remains that blocks acceptance under repository policy.

## 19.2 Immutable accepted baseline

An accepted baseline MUST identify an immutable repository revision.

In Git repositories, the full commit SHA SHOULD be used.

Branch names, moving tags, labels, or phrases such as `latest main` MAY be recorded for convenience but MUST NOT replace the immutable revision used for execution and review.

An accepted-baseline record SHOULD identify:

- immutable revision;
- bounded scope accepted;
- evidence references;
- limitations;
- open gaps;
- governing task revision; and
- release status.

## 19.3 Parallel work and moving baselines

When multiple independent tasks originate from the same accepted baseline, each task remains tied to the baseline against which it was planned.

Later integration MUST account for repository changes since that baseline rather than assuming the repository has remained unchanged.

## 19.4 Development continuation

Once A9 passes, planning MAY continue immediately from the new accepted baseline even if production release has not yet occurred.

## Gate A9

A9 passes when the reviewed implementation revision is explicitly established as the next immutable accepted development baseline.

---

# 20. Phase 11 — Separate Release Gate

## Objective

Determine whether an accepted implementation is authorized and ready for production deployment, publication, package release, or another environment-specific promotion.

## 20.1 Independent release track

Implementation acceptance and release approval are separate tracks.

```text
implementation review
→ accepted baseline
→ development may continue

accepted baseline
→ release checks
→ release authority decision
→ deployment / publication / release
```

Acceptance MUST NOT be interpreted as authorization to deploy, publish, or release.

## 20.2 Applicable release concerns

The Release Gate SHOULD evaluate concerns relevant to the repository and environment, such as:

- integration readiness;
- current CI;
- security review;
- privacy review;
- migration rehearsal;
- backup and rollback;
- configuration and secrets;
- infrastructure readiness;
- production dependencies;
- storage and retention;
- observability;
- performance;
- operational readiness;
- regulatory requirements;
- deployment procedure; and
- recovery strategy.

A documentation repository, library, data pipeline, internal tool, and healthcare backend may legitimately have very different release requirements.

## 20.3 Release authority

Repository-specific policy defines required release approvals.

The protocol MUST NOT assume that implementation reviewers automatically possess release authority.

## Gate G10

G10 passes only when all applicable release requirements and approvals defined by repository policy have passed.

---

# 21. Logical roles and decision rights

## 21.1 Logical delivery roles

| Logical role | Responsibility |
|---|---|
| Business Authority | Own business outcome, priority, constraints, and decisions that MUST NOT be invented. |
| Product Authority | Approve product behavior, scope, and acceptance. |
| Requirements Authority | Approve or govern atomic requirements and traceability according to repository policy. |
| Technical Authority | Approve architecture, module/data authority, trust boundaries, and material technical constraints. |
| Planner | Inspect authority and repository state, select delivery objective, publish validated tasks, and maintain delivery traceability. |
| Executor | Implement only the governing validated task and produce verification evidence. |
| Reviewer | Review implementation against baseline, task revision, authority, evidence, and available CI. |
| Security / Privacy Authority | Approve exceptions or high-assurance concerns when repository policy requires it. |
| Release Authority | Approve deployment, publication, or production release. |

## 21.2 Role composition

One person, model, agent, or session MAY hold multiple logical roles when repository policy permits it.

Role composition MUST NOT erase decision boundaries.

For example, a single AI session MAY act as Planner and Reviewer while a different executor performs implementation.

High-risk repositories MAY require stronger separation of duties.

## 21.3 Runtime neutrality

The protocol refers to logical roles only.

Model names, reasoning settings, provider selection, session layout, and orchestration belong to runtime configuration rather than this protocol.

---

# 22. Change-impact rules

Changes to approved business, product, requirement, or architecture authority MUST trigger impact analysis against applicable downstream artifacts.

Impact analysis SHOULD consider:

- downstream requirements;
- source coverage and traceability;
- architecture and ownership;
- Work Packages and MVPs;
- delivery roadmap;
- unpublished or published tasks;
- active execution;
- previously accepted implementation;
- tests and evidence;
- gaps;
- release assumptions; and
- accepted baselines that may need to be reopened.

Historical evidence MUST NOT be rewritten to pretend the earlier state never existed.

Superseded authority SHOULD remain traceable to its replacement.

---

# 23. Feedback and re-entry rules

| Finding | Return to |
|---|---|
| Business ambiguity | Business framing and decision authority. |
| Product conflict | PRD / product decision and acceptance definition. |
| Missing or unsourced requirement | Requirement registry and source coverage. |
| Wrong module or data ownership | Architecture / ADR / technical authority. |
| Blocking dependency unavailable | Dependency mapping, gap register, or designated authority. |
| Task contract insufficient | Task planning and validation. |
| Task materially changed during execution | Task re-evaluation before continuing. |
| Implementation defect within original objective | Same-task remediation. |
| Materially new objective discovered | Delivery Planning and a separate task. |
| Test does not execute claimed boundary | Evidence closure or stronger focused verification. |
| Evidence overclaim | Correct evidence and any affected status. |
| CI unavailable | Record local evidence accurately and preserve the CI limitation. |
| Approved source changes before execution | Re-run impact analysis and republish affected task. |
| Approved source changes after acceptance | Reopen affected requirement or gap and plan bounded change. |
| Emergency work | Use an expedited but still validated bounded task; close deferred traceability as soon as repository policy requires. |

---

# 24. Definition of Ready for Implementation

An executable task is ready when the concerns applicable to its risk and scope are sufficiently satisfied.

Typical readiness checks include:

- [ ] legitimate authority exists for the bounded objective;
- [ ] relevant product behavior is approved;
- [ ] relevant requirements are identified and traceable;
- [ ] architecture and ownership are sufficiently clear;
- [ ] blocking dependencies and decisions are resolved;
- [ ] delivery mode and objective are explicit;
- [ ] implementation baseline is immutable and known;
- [ ] task revision is exact and known;
- [ ] included and excluded scope are explicit;
- [ ] preserved behavior is explicit where material;
- [ ] acceptance criteria are observable;
- [ ] verification requirements are executable or otherwise inspectable;
- [ ] remaining approval gates are explicit;
- [ ] stop conditions are explicit; and
- [ ] the task can be executed without inventing upstream decisions.

A repository MAY use a machine validator, but machine validation does not replace semantic readiness.

---

# 25. Definition of Accepted Implementation

An implementation may be accepted when the applicable bounded-delivery criteria are satisfied, including:

- [ ] implementation is reviewed against the correct baseline;
- [ ] implementation is reviewed against the exact governing task revision;
- [ ] observed behavior satisfies accepted task scope;
- [ ] relevant authority and ownership remain correct;
- [ ] positive and negative paths are sufficiently verified;
- [ ] focused checks pass;
- [ ] targeted regressions pass;
- [ ] risk-proportional assurance is complete;
- [ ] evidence reflects actual observed results;
- [ ] tests not run and limitations are recorded;
- [ ] documentation and gap status match observed reality;
- [ ] blocking review findings are closed;
- [ ] the accepted immutable revision is recorded; and
- [ ] release status remains explicitly separate.

---

# 26. Repository integration guidance

## 26.1 Artifact locations

The protocol intentionally does not mandate repository paths for business, product, requirement, architecture, planning, or evidence artifacts.

Existing repository conventions SHOULD be reused.

For a new repository, a team MAY choose a structure such as:

```text
docs/
├── business/
├── product/
├── requirements/
├── architecture/
└── delivery/
```

This is an example, not a protocol requirement.

## 26.2 `.agents/` packaging

When this protocol is distributed as a runtime-neutral `.agents/` package, a minimal structure MAY be:

```text
.agents/
├── AGENTS.md
├── software-workflow.md
├── context/
│   └── project.md
├── prompts/
├── tasks/
└── runtime-adapters/
```

Responsibilities are:

- `.agents/AGENTS.md`: short canonical entrypoint and protocol contract;
- `.agents/software-workflow.md`: this normative delivery protocol;
- `.agents/context/`: repository-specific authority map and delivery state;
- `.agents/prompts/`: reusable Planner/Reviewer delivery-orchestration procedures;
- `.agents/tasks/`: published bounded execution contracts; and
- `.agents/runtime-adapters/`: thin runtime-specific bootstrap material.

Runtime adapters MUST NOT redefine the canonical software-delivery protocol.

## 26.3 Runtime-specific execution methodology

Generic coding-agent methodology SHOULD remain outside the canonical protocol.

A runtime MAY use its own or third-party methodologies for:

- brainstorming;
- planning technique;
- debugging;
- testing discipline;
- code review mechanics;
- worktree management;
- subagent coordination; and
- tool orchestration.

Those methodologies remain subordinate to repository authority and the bounded task contract.

---

# 27. Anti-patterns

| Anti-pattern | Why it violates the protocol |
|---|---|
| Business intent → coding directly | Product behavior, requirements, authority, and acceptance become ambiguous. |
| Rebuilding all artifacts in an existing repository | Discards valid repository authority and creates unnecessary documentation churn. |
| Treating implementation as the requirement source | Existing code becomes retroactive authority without approval. |
| Treating approved requirements as proof of implementation | Intended state is confused with observed reality. |
| Requirement without legitimate source | Scope can grow without authority. |
| Requirement without accountable owner | Source of truth and mutation authority become ambiguous. |
| Cosmetic traceability written after implementation | Matrices become retrospective justification rather than delivery control. |
| Mandatory one-file-per-artifact bureaucracy | Small repositories are forced into unnecessary documentation overhead. |
| Forcing every repository into one directory layout | Existing repository conventions are overridden without value. |
| Starting implementation without a validated task | Executor must invent scope, authority, or acceptance decisions. |
| Over-prescribing implementation in the task | Planner improperly owns technical decisions that belong to the executor. |
| Filename version spam for every task revision | Version control already preserves history; task directories become noisy. |
| Silent task mutation during execution | Executor and reviewer may operate against different contracts. |
| Remediation that introduces unrelated scope | Review closure becomes uncontrolled roadmap expansion. |
| Parallel execution with hidden dependencies | Tasks interfere and cannot be reviewed independently. |
| Evidence based on agent narrative | Success is asserted rather than observed. |
| Local result described as CI | Evidence provenance is overstated. |
| Accepted baseline described by moving branch name only | Execution and review boundaries become ambiguous. |
| Accepted implementation treated as release approval | Production-specific risks and authority are bypassed. |

---

# 28. Reusable protocol checklist

## Authority and product

- [ ] Business source and authority are known.
- [ ] Problem and target outcome are clear.
- [ ] Accountable owner is known.
- [ ] Material assumptions and open decisions are recorded.
- [ ] Product behavior is approved where required.
- [ ] Goals, non-goals, and exclusions are explicit.

## Requirements and architecture

- [ ] Requirements use stable IDs where material.
- [ ] Requirements have legitimate sources.
- [ ] Ownership is clear.
- [ ] Verification method is known.
- [ ] Dependencies are classified as blocking or non-blocking.
- [ ] Module/data authority is sufficiently clear.
- [ ] Trust boundaries are sufficiently clear.
- [ ] Intended authority and observed implementation conflicts are explicit.

## Delivery planning

- [ ] Current accepted baseline is known.
- [ ] Delivery mode is explicit: MVP-oriented or Work-Package-oriented.
- [ ] Current objective is coherent and bounded.
- [ ] Independent outcomes are separated.
- [ ] Parallel tasks are independent where used.
- [ ] Gaps and exclusions remain visible.

## Task readiness

- [ ] Exact implementation baseline is recorded.
- [ ] Exact governing task revision is recorded.
- [ ] Objective is explicit.
- [ ] Authoritative inputs are explicit.
- [ ] Scope and exclusions are explicit.
- [ ] Acceptance criteria are observable.
- [ ] Verification requirements are defined.
- [ ] Stop conditions are defined.
- [ ] Executor can proceed without inventing upstream decisions.

## Execution and verification

- [ ] Repository identity and current state are checked.
- [ ] Task revision has not silently changed.
- [ ] Only bounded scope is implemented.
- [ ] Focused verification is performed.
- [ ] Targeted regressions are performed where appropriate.
- [ ] Risk-proportional assurance is complete.
- [ ] Evidence records actual observed results.
- [ ] Tests not run and limitations are explicit.

## Review and acceptance

- [ ] Review compares exact baseline to implementation revision.
- [ ] Review uses the exact governing task revision.
- [ ] Requirement and architecture boundaries are checked.
- [ ] Evidence quality is checked.
- [ ] Unrelated changes are identified.
- [ ] Same-task remediation is used only for the same objective.
- [ ] Material new scope returns to planning.
- [ ] Accepted revision is immutable and recorded.
- [ ] Open gaps remain visible.
- [ ] Release status is separate.

---

# 29. Operating formula

The protocol can be summarized as:

```text
Discover repository authority and current state
→ reuse valid existing artifacts
→ repair only missing or unreliable gates
→ establish approved product and requirement authority
→ establish architecture and ownership
→ choose current delivery objective
→ publish a validated bounded task
→ execute against exact baseline and task revision
→ verify using observed evidence
→ review implementation against authority and evidence
→ remediate within the same objective when necessary
→ accept an immutable new baseline
→ continue planning independently of release
→ release only through the separate applicable Release Gate
```

Or, in lifecycle form:

```text
Business Sources
→ PRD
→ Requirement Registry & Matrices
→ Architecture & Repository Context
→ Delivery Planning
→ Validated Task
→ Execution & Verification
→ Implementation Review
→ Remediation or Acceptance
→ New Accepted Baseline
→ Separate Release Gate
```

---

# Appendix A — Glossary

| Term | Definition |
|---|---|
| Accepted baseline | Immutable repository revision accepted after review and used as a trusted starting point for subsequent planning. |
| Architecture authority | Approved technical authority defining module boundaries, data ownership, trust boundaries, and material technical constraints. |
| Business source | Legitimate input containing a problem, decision, contract, regulation, constraint, incident, or target outcome. |
| Delivery objective | The bounded outcome selected for the current planning cycle. |
| Evidence | Observed tests, checks, commands, runtime behavior, CI status, or other verifiable results. |
| Executable task | Published validated delivery contract governing one coherent implementation objective. |
| Gap | Deliberately incomplete or unresolved behavior with visible impact and closure criteria. |
| Implementation baseline | Immutable repository revision against which a task is planned and execution begins. |
| Intended authority | Approved business, product, requirement, and architecture definition of expected system behavior. |
| MVP | Bounded vertical delivery slice producing a usable or demonstrable outcome. |
| Observed reality | Current behavior evidenced by code, configuration, migrations, tests, runtime observation, or deployment. |
| Planner | Logical role that interprets repository authority, plans bounded delivery, and publishes validated tasks. |
| PRD | Approved product behavior and acceptance definition, regardless of physical filename. |
| Requirement | Atomic, sourced, owned, and verifiable obligation or constraint. |
| Requirement registry | Authoritative collection of stable requirements and their metadata. |
| Reviewer | Logical role that compares implementation against baseline, task revision, authority, and evidence. |
| Release Gate | Separate environment-specific approval required before deployment, publication, or production release. |
| Remediation | Bounded corrective work that remains within the original delivery objective. |
| Runtime adapter | Thin integration layer that teaches a specific AI runtime how to discover the canonical protocol without redefining it. |
| Task revision | Exact immutable revision of the task content that governed an execution attempt. |
| Traceability | Bidirectional mapping between legitimate authority, requirements, delivery work, implementation, evidence, and accepted baseline. |
| Work Package | Grouping of approved requirements toward a broader expected end-state. |

---

# Appendix B — Protocol maintenance

| Field | Rule |
|---|---|
| Authority | Approved repository authority governs intended behavior; observed repository evidence governs claims about current implementation reality. Repository-specific policy MAY strengthen this reusable protocol but MUST NOT silently weaken applicable authority, safety, compliance, or release requirements. |
| Review trigger | Material changes to authority model, requirement model, gate semantics, task contract, acceptance, baseline, or release separation. |
| Versioning | Material protocol changes SHOULD increment the protocol version. |
| History | Superseded protocol revisions SHOULD remain available through version control. |
| Format | Markdown is the canonical source format unless the repository explicitly defines another authoritative representation. |
| Runtime neutrality | Runtime-specific model names, commands, plugins, and vendor behavior MUST remain outside the normative core unless they are examples clearly marked as non-normative. |
