---
title: Executable Task Template
document_id: AGENT-TASK-001
version: 1.1
status: approved-template
language: en-US
last_updated: 2026-08-10
scope:
  - validated executable delivery tasks
  - bounded implementation contracts
  - execution and review traceability
authority_note: A published validated task authorizes only the bounded implementation scope explicitly defined by the task and applicable approved repository authority. Observed repository evidence governs claims about current implementation reality but does not silently redefine the task or its intended authority.
---

# Executable Task

This file defines a bounded software-delivery contract for implementation.

A validated task MUST provide enough authority, scope, acceptance, verification, and stop-condition information for an Executor to proceed without inventing material product, requirement, architecture, scope, or approval decisions.

A task is not a generic coding recipe. Implementation technique remains the Executor's responsibility within the constraints established here.

## Task identity

**Task title:**  
`<short human-readable title>`

**Task path:**  
`<relative path to this task file>`

**Task contract state:**  
`<Draft | Validated/Published>`

The task file is the executable delivery contract.

Execution and review lifecycle states such as `In Execution`, `Review Required`, `Remediation Required`, and `Accepted` SHOULD normally be tracked by orchestration, review records, repository metadata, or another mechanism that preserves the exact governing task revision.

A lifecycle-status update MUST NOT silently replace the immutable task revision that governed an execution attempt.

When remediation materially changes this executable contract, edit the same stable task path, return it to Draft as needed, and republish it as a new immutable governing task revision before renewed execution.

**Delivery objective / Work Package / MVP:**  
`<identifier or description>`

**Owner / designated planning authority:**  
`<owner or authority reference>`

## Delivery context

Describe the bounded delivery outcome and why this task exists.

Keep this concise and traceable to approved authority.

`<delivery context>`

## Baseline and task revision

**Implementation baseline:**  
`<immutable repository revision>`

**Task revision:**  
`<exact immutable task-content revision, or "resolved when published" while Draft only>`

`resolved when published` is a Draft placeholder. It is not sufficient for T5.

Before this task is treated as `Validated/Published` or handed to an Executor, the exact immutable governing task revision MUST be resolvable.

For Git repositories, the preferred published task identity is:

```text
<task path> @ <full Git commit SHA containing the governing task content>
```

The immutable revision MAY be supplied externally by version-control history, publication metadata, Planner handoff, runtime metadata, or another repository-approved immutable content-identity mechanism. The task body does not need to embed the commit SHA that contains itself.

If establishing the immutable published task revision requires an otherwise unauthorized commit, publication, or other side effect, stop for the applicable authorization. Do not claim the task is Validated/Published while its governing revision remains unresolved.

The implementation baseline and governing task revision are separate references.

Do not change the implementation baseline silently during execution.

If parallel or intervening repository changes require reconciliation, return the issue to planning or follow explicit repository policy.

## Objective

State one coherent delivery outcome.

The objective MAY span multiple files, modules, or technical steps when necessary to achieve one bounded result.

Unrelated or independently valuable outcomes SHOULD be separate tasks.

**Objective:**  
`<clear outcome>`

## Authoritative inputs

List the approved sources that constrain this task.

Examples MAY include:

- business decisions;
- PRD sections;
- requirement identifiers;
- requirement matrices;
- architecture specifications;
- ADRs;
- repository policy;
- accepted planning artifacts;
- approved external specifications.

### Governing authority

- `<authority reference>`
- `<authority reference>`

### Requirement traceability

- `<requirement-id>` → `<authority reference>`
- `<requirement-id>` → `<authority reference>`

Do not use existing implementation as retroactive justification for missing authority.

If required authority is Draft, unresolved, contradictory, or unapproved, this task MUST NOT be validated for implementation unless repository policy explicitly permits it.

## Scope

### In scope

- `<required behavior or bounded change>`
- `<required behavior or bounded change>`

### Out of scope

- `<explicitly excluded behavior, subsystem, refactor, migration, or operational action>`
- `<explicit exclusion>`

### Preserved behavior

List behavior, compatibility, contracts, data properties, or repository boundaries that MUST remain unchanged where material.

- `<preserved behavior or invariant>`
- `<preserved behavior or invariant>`

Preserve unrelated behavior.

Do not expand scope merely because adjacent improvements are technically convenient.

## Dependencies and assumptions

### Dependencies

- `<dependency, prerequisite, external contract, related task, or required state>`

For parallel tasks, document overlapping files, shared resources, sequencing requirements, or reconciliation expectations where relevant.

### Approved assumptions

- `<assumption explicitly supported by approved authority or verified repository evidence>`

Observed repository evidence MAY support assumptions about current implementation reality. Such evidence does not become intended authority merely because it supports the assumption.

Do not convert unresolved product, requirement, architecture, safety, acceptance, or scope decisions into implementation assumptions.

### Remaining approval requirements

Record approvals that still apply after task publication.

Examples MAY include:

- designated human approval before a particular side effect;
- security or privacy approval;
- migration or data-operation approval;
- external-system authorization;
- release or deployment approval;
- another repository-specific approval boundary.

- `<approval requirement, owner/authority, and trigger>`
- `<approval requirement, or "None beyond the task's existing authority">`

A remaining approval requirement MUST be explicit enough that the Executor knows when to stop rather than silently cross the boundary.

## Required capabilities

List only capabilities genuinely required to execute or verify this task.

Examples:

- repository read;
- repository write;
- shell or local command execution;
- test execution;
- Graphify;
- Codebase Memory MCP;
- browser or external-system access.

**Required capabilities:**

- `<capability>`

Runtime, model, vendor, reasoning level, or agent implementation SHOULD NOT be encoded here unless a repository-specific authority explicitly requires it.

## Execution constraints

Record material implementation constraints derived from approved authority, architecture, repository policy, existing conventions, or delivery risk.

Examples MAY include:

- compatibility requirements;
- repository pattern reuse;
- migration constraints;
- data-integrity rules;
- security or privacy requirements;
- prohibited dependencies;
- generated-code boundaries;
- API stability;
- transactional guarantees;
- concurrency constraints;
- operational restrictions.

### Constraints

- `<constraint>`
- `<constraint>`

Apply repository reuse discipline.

Prefer established repository mechanisms and patterns when they satisfy the approved need.

Do not introduce parallel abstractions, frameworks, persistence mechanisms, authorization models, service layers, state machines, queues, transaction mechanisms, or comparable infrastructure without a concrete approved need.

## Acceptance criteria

Acceptance criteria define observable conditions that MUST be satisfied for this delivery objective.

They SHOULD describe required behavior and externally meaningful constraints rather than prescribing unnecessary implementation detail.

- [ ] `<observable acceptance criterion>`
- [ ] `<observable acceptance criterion>`
- [ ] `<compatibility / preservation criterion when applicable>`
- [ ] `<error / failure behavior when applicable>`

Every criterion MUST be traceable to approved authority, a necessary implementation invariant, or an explicitly approved delivery decision.

## Verification requirements

Define the minimum evidence required before review.

Verification depth MUST be proportional to risk and impact.

### Required checks

- `<test, static check, build, migration check, runtime check, integration check, or other verification>`
- `<required check>`

### Required evidence

The Executor MUST report:

- implementation revision or exact working-tree state;
- commands and checks actually executed;
- observed results;
- tests added or changed;
- known verification gaps;
- material deviations;
- blockers encountered;
- any evidence that could affect review.

Do not represent unobserved, skipped, or local-only checks as broader evidence than they actually provide.

## Stop conditions

The Executor MUST stop implementation and return the issue to planning when any of the following materially affects the task:

- a required authority decision is missing or contradictory;
- a blocking dependency is unresolved;
- the governing architecture cannot support the task without a material decision;
- the implementation baseline is no longer safely applicable;
- the task requires materially expanded or changed scope;
- acceptance criteria cannot be satisfied within the approved objective;
- an unexpected security, privacy, data-integrity, or operational risk requires new authority;
- execution would require an unapproved side effect or permission expansion;
- the task itself is materially ambiguous.

Additional task-specific stop conditions:

- `<stop condition>`
- `<stop condition>`

The Executor MUST NOT silently reinterpret the task into a materially different objective.

## Side-effect authorization

Implementation authorization is bounded to the task's defined execution scope.

Unless explicitly authorized by this task, applicable repository policy, or designated authority, the task does NOT authorize:

- Git commit;
- push;
- pull-request creation;
- deployment;
- publication;
- release;
- destructive data operations;
- destructive infrastructure operations;
- production mutation;
- external-system mutation;
- dependency installation or replacement;
- permission expansion;
- secret access, copying, or disclosure;
- unrelated repository changes.

### Explicitly authorized side effects

- `<authorized action, or "None">`

## Expected terminal outcome

The Executor's implementation phase SHOULD end in one of these states:

### Review Required

Use when a reviewable implementation state and truthful verification evidence are available for Reviewer evaluation.

Expected evidence:

- exact implementation revision or precisely identified working-tree state;
- verification results;
- deviations and known gaps;
- unresolved non-blocking observations.

A mutable working-tree state MAY be sufficient for V7 evaluation when repository policy permits it, but A9 acceptance requires an immutable accepted implementation revision.

### Planning Required

Use when a stop condition prevents safe completion within the governing task.

Expected evidence:

- blocking issue;
- affected authority, scope, architecture, dependency, or acceptance condition;
- repository evidence supporting the escalation.

The Executor does not self-declare final acceptance.

## Review and remediation handling

The Reviewer evaluates implementation against the exact governing task revision, applicable authority, implementation baseline, implementation revision, and observed evidence.

If the implementation is accepted, the reviewed immutable repository revision MAY become the new accepted baseline when repository policy permits it.

Acceptance does not imply release authorization.

If review identifies bounded corrections within the same delivery objective, update and republish this same task rather than creating filename-version copies.

A remediation update MAY add a concise section such as:

```markdown
## Remediation

**Review basis:** `<implementation revision>`

### Required corrections

- `<bounded correction>`
- `<bounded correction>`

### Additional verification

- `<verification required for remediation>`
```

The updated executable contract MUST receive a new immutable governing task revision before renewed execution.

A status-only review record or lifecycle transition MUST NOT be treated as a new governing task revision.

Materially new objectives, unrelated findings, or scope expansion MUST return to Delivery Planning and become separate task work.

## Execution evidence

Execution evidence is normally reported outside the planning contract rather than written by the Executor into the task as self-certification.

The governing review record SHOULD preserve or reference:

- governing task path and immutable task revision;
- implementation baseline;
- implementation revision;
- verification evidence;
- Reviewer verdict;
- remediation requirements when applicable;
- accepted baseline when acceptance occurs.
