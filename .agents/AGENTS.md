---
title: Repository AI Delivery Contract
document_id: AGENTS-CONTRACT-001
version: 1.2
status: approved-reference
language: en-US
last_updated: 2026-08-10
scope:
  - repository-local AI delivery governance
  - runtime-neutral agent routing
  - planning, execution, and review boundaries
  - repository intelligence and evidence rules
authority_note: Approved repository authority governs intended behavior. Observed repository evidence governs claims about current implementation reality. Neither silently overrides the other.
---

# Repository AI Delivery Contract

This `.agents/` package defines the repository-local, runtime-neutral software-delivery contract for AI coding agents and mixed human/AI delivery.

It governs repository authority, delivery routing, context loading, task execution boundaries, evidence, and acceptance.

It does not define generic coding methodology or vendor-specific agent behavior.

## Canonical delivery protocol

`.agents/software-workflow.md` is the normative software-delivery protocol.

Planning, execution, and review MUST conform to that protocol, including its authority model, quality gates, traceability requirements, task contract, evidence rules, acceptance model, and separate Release Gate. Progressive loading does not require every role to read the entire protocol when this contract and the governing task provide the applicable execution boundaries.

Do not bypass a required protocol gate merely because implementation is technically possible.

Repository-specific approved policy MAY strengthen the protocol.

## Authority and evidence

Distinguish **intended authority** from **observed implementation reality**.

Intended authority MAY include:

- approved business sources and decisions;
- approved PRD or equivalent product specification;
- approved requirements and matrices;
- approved architecture and repository policy;
- approved delivery planning;
- the governing published validated task.

Observed implementation reality MAY include:

- source code;
- configuration;
- migrations;
- tests;
- runtime observations;
- version-control state;
- available CI evidence.

When intended authority and observed reality disagree, record and resolve the discrepancy explicitly.

Do not silently modify one side merely to make them appear consistent.

Existing implementation MUST NOT become retroactive justification for a missing requirement.

Approved requirements MUST NOT be treated as proof that implementation satisfies them.

Context files, prompts, derived indexes, external methodologies, agent summaries, search results, and generic model knowledge are supporting aids. They MUST NOT override authoritative repository sources or observed repository evidence.

## Role routing

Planner, Executor, and Reviewer are logical responsibilities rather than fixed models, agents, or sessions.

A runtime MAY assign more than one responsibility to the same model or session when repository policy permits it.

### Planner

The Planner establishes or re-establishes delivery readiness and publishes validated executable work.

Before material planning, load:

- this contract;
- `.agents/software-workflow.md`;
- `.agents/context/project.md`;
- only the scoped context relevant to the current work;
- relevant authoritative repository artifacts;
- `.agents/prompts/plan-create-task.md`.

The Planner MUST identify the earliest unmet or materially unreliable quality gate rather than forcing an existing repository to restart from the beginning of the protocol.

### Executor

The Executor implements only a published validated task.

Before implementation, load:

- this contract;
- the exact governing task revision;
- the implementation baseline identified by the task;
- authoritative inputs referenced by the task;
- relevant repository context and implementation evidence.

The Executor normally SHOULD NOT load the Planner/Reviewer delivery-orchestration prompt.

The Executor retains bounded technical discretion over implementation details that are not already constrained by approved authority, architecture, repository conventions, or the governing task.

If execution reveals a missing authority decision, blocking dependency, architecture conflict, materially changed task, or required scope expansion, stop implementation and return the issue to planning.

### Reviewer

The Reviewer determines whether implementation satisfies its governing delivery contract.

Before material review, load:

- this contract;
- `.agents/software-workflow.md`;
- `.agents/context/project.md`;
- only the scoped context relevant to the review;
- the exact governing task revision;
- the implementation baseline and implementation revision;
- applicable repository authority;
- verification evidence and available CI;
- `.agents/prompts/plan-create-task.md`.

A successful review MAY establish the reviewed immutable revision as the new accepted baseline when repository-specific policy does not require additional approval.

Implementation acceptance MUST NOT be interpreted as release authorization.

## Repository context

`.agents/context/project.md` is the repository-level orientation map and context entrypoint.

It MAY summarize:

- repository purpose;
- top-level architecture and boundaries;
- locations of authoritative artifacts;
- current delivery state;
- current accepted baseline;
- known gaps;
- relevant repository conventions;
- available scoped context.

Additional scoped context MAY exist under `.agents/context/` for modules, services, domains, packages, integrations, or other repository-defined boundaries.

Load repository-level context first, then load only the scoped context materially relevant to the current work.

Context is supporting, refreshable repository knowledge rather than primary authority.

When context is missing, stale, contradictory, or inconsistent with authoritative sources or current implementation evidence, reverify the affected claims before relying on them materially.

A deeper scoped context file does not implicitly override broader repository context or authoritative repository sources.

## Delivery orchestration procedure

Files under `.agents/prompts/` are reusable delivery procedures, not repository authority.

Use the canonical delivery-orchestration prompt deliberately rather than treating prompts as persistent instructions.

The canonical delivery-orchestration procedure is:

- `plan-create-task.md` for reviewing pending implementation and evidence, determining acceptance or bounded remediation, establishing the current accepted baseline, assessing delivery state, addressing planning-stage gaps, selecting the next coherent delivery objective, and publishing validated task work.

The same procedure MAY be invoked repeatedly throughout delivery. Task creation is one possible outcome, not a requirement of every invocation.

The procedure MAY create or repair logical Business, PRD, Requirement Registry & Matrices, Architecture, Repository Context, or Delivery Planning artifacts when required by the earliest unmet or unreliable gate.

AI-generated authority-bearing artifacts remain Draft until approved by the designated authority.

Prompts MUST NOT override the canonical delivery protocol, repository authority, observed implementation evidence, or a governing task revision.

## Executable tasks

Implementation-changing work MUST NOT begin without a published validated task.

A validated task is a delivery contract, not an implementation recipe.

It MUST define, directly or by unambiguous reference, enough information for execution to proceed without inventing material product, requirement, architecture, scope, or approval decisions.

Task files SHOULD use stable human-readable paths.

Filename-based version proliferation is not required.

Task updates MAY overwrite the existing task file when appropriate; version-control history preserves prior revisions.

Execution and review MUST remain tied to the exact task revision that governed the work.

For Git repositories, task identity SHOULD be representable as:

`<task path> @ <immutable Git revision containing the governing task content>`

The immutable task revision MAY be resolved externally from version-control history or orchestration metadata; the task body does not need to embed the commit SHA that contains itself.

A Draft task MAY temporarily use an unresolved publication placeholder, but a task MUST NOT be treated as Validated/Published or handed to the Executor until its exact immutable governing revision is resolvable.

Task lifecycle state and governing task revision are distinct. A status-only update MUST NOT silently replace the immutable task revision that governed an execution attempt. A remediation change that materially alters the executable contract MUST be republished as a new immutable task revision before renewed execution.

If establishing the immutable published task revision requires an otherwise unauthorized side effect, planning MUST stop for the applicable authorization rather than hand an unresolved task to the Executor.

A validated published task MAY proceed automatically to execution unless repository-specific policy requires another approval gate.

Bounded remediation within the original delivery objective SHOULD update and republish the same task.

Materially new scope, objectives, or unrelated findings MUST return to Delivery Planning rather than being hidden inside remediation.

## Repository intelligence

Repository-intelligence tools are discovery and analysis aids, not authority.

When available and relevant:

- use **Graphify** for documentation-oriented discovery, relationship analysis, and narrowing the authoritative document set;
- use **Codebase Memory MCP** for implementation-oriented code intelligence such as symbols, callers, call paths, dependencies, routes, services, tests, and implementation impact.

Derived intelligence MUST be verified against the exact authoritative repository artifacts or observed implementation evidence before supporting material planning, review, acceptance, requirement, or architecture claims.

Reuse sufficiently fresh graphs and indexes when available.

Prefer incremental refreshes over unnecessary full rebuilds.

If freshness or repository identity is uncertain, verify directly against the repository and report the limitation.

## Reuse discipline

Apply **Ponytail** reuse discipline throughout planning, execution, and review.

Prefer established repository patterns, boundaries, primitives, and mechanisms over parallel abstractions.

Before introducing a new framework, abstraction, service layer, authorization model, persistence mechanism, state machine, queue mechanism, transaction mechanism, testing architecture, or comparable infrastructure, inspect whether the repository already provides an adequate pattern.

New abstractions MUST arise from a concrete approved delivery need rather than speculative generalization.

Preserve unrelated behavior and avoid opportunistic refactoring outside the governing delivery objective.

## Evidence and verification

Claims of completion, correctness, acceptance, compatibility, security, or readiness MUST be based on observed evidence.

Do not claim success solely from:

- source-code existence;
- an agent summary;
- a commit message;
- hidden or unobserved execution;
- tests that do not exercise the claimed boundary;
- local results represented as CI;
- documentation that has not been reconciled with implementation reality.

Verification depth MUST be proportional to risk and impact.

Higher-risk work MAY require broader regression coverage, stronger evidence, independent review, or additional designated approval according to repository-specific policy.

## Side effects and approval boundaries

A validated task authorizes only the mutations within its defined execution scope.

It does not implicitly authorize:

- Git commits;
- pushes or pull requests;
- deployment, publication, or release;
- destructive data or infrastructure operations;
- production or external-system mutation;
- dependency installation or replacement;
- permission expansion;
- secret access or disclosure;
- changes outside the bounded delivery objective.

Those actions require explicit authorization from the governing task, repository policy, or designated human authority.

Never invent, expose, copy, or persist secret values.

## Engineering methodology

Runtime-native or externally installed software-engineering methodologies, skills, plugins, and tools MAY be used when appropriate.

Examples include methodologies for brainstorming, implementation planning, debugging, testing discipline, worktree management, code review, subagent coordination, and verification.

Such methodologies are execution aids.

They MUST remain subordinate to:

1. applicable human and repository authority;
2. the canonical software-delivery protocol;
3. the governing validated task;
4. applicable approval and safety boundaries.

No external methodology becomes repository authority merely because it is installed or popular.

## Runtime neutrality

The canonical `.agents/` contract MUST NOT depend on a specific coding-agent vendor, model, IDE, instruction-discovery mechanism, or orchestration implementation.

Model selection and runtime-specific behavior remain runtime concerns unless repository policy explicitly constrains them.

Planner, Executor, and Reviewer responsibilities MAY be mapped differently by different runtimes without changing the canonical delivery protocol.

## Runtime adapters

`.agents/runtime-adapters/` contains thin integration material for specific runtimes.

A runtime adapter MAY explain:

- how the runtime discovers this contract;
- which bootstrap file must be copied or activated;
- how runtime-native rules or instruction files connect to `.agents/AGENTS.md`;
- recommended optional execution tooling or methodology.

Runtime adapters MUST NOT redefine, duplicate, or weaken the canonical delivery protocol.

After installation into a target repository, runtime-specific adapter material MAY be materialized into the locations required by that runtime.

## Operating principle

Use the smallest sufficient context and follow this control loop:

```text
establish current delivery state
→ identify intended authority and observed evidence
→ load only relevant context
→ resolve pending implementation, review, remediation, or approval state first
→ establish or confirm the accepted baseline
→ plan from the earliest unmet or materially unreliable gate
→ publish a validated bounded task only when T5 is satisfied
→ execute against the exact baseline and governing task revision
→ reuse established repository patterns
→ verify with observed evidence
→ return to Planner/Reviewer orchestration
→ remediate, accept a new immutable baseline, repair authority, or publish the next valid task
→ continue development independently of release
```

When uncertain, verify the repository rather than inventing authority.
