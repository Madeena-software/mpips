<!-- runtime-adapter: antigravity | version: 1.1 | status: approved-template -->

# Repository AI Delivery Bootstrap for Antigravity

This workspace rule connects Antigravity to the repository-local, runtime-neutral software-delivery contract under `.agents/`.

Configure this rule as **Always On** when materialized at:

```text
.agents/rules/code-agent-workflow.md
```

The canonical repository AI delivery contract is:

@../AGENTS.md

Read and obey that contract before material repository work.

This rule is a runtime bootstrap only. It MUST NOT redefine or weaken the canonical `.agents/` protocol, repository authority, governing task, evidence requirements, approval boundaries, or release boundaries.

## Canonical routing

Use `.agents/AGENTS.md` for role routing and progressive loading.

`.agents/software-workflow.md` remains the normative delivery protocol.

When acting as Planner or Reviewer, follow the canonical loading rules and use:

```text
.agents/prompts/plan-create-task.md
```

as the delivery-orchestration procedure.

When acting as Executor, implement only an exact published validated task and load only the authority, context, implementation surface, and evidence relevant to that task.

Do not redo delivery planning merely to replace the governing task with a preferred implementation objective.

If execution reaches a task stop condition, return the issue to Planner/Reviewer orchestration.

## Antigravity rules and scoped instructions

Antigravity may apply both Global Rules and Workspace Rules.

Global Rules are runtime-level user instructions applied across workspaces. Workspace Rules MAY define repository-wide or scoped technical conventions, commands, tests, ownership rules, or implementation constraints.

Neither rule type silently becomes approved repository authority merely because Antigravity loads it.

Active rules MUST be interpreted together with applicable direct user instructions and the canonical `.agents/` contract.

A rule MUST NOT silently:

- redefine approved business or product intent;
- change approved requirements;
- weaken approved architecture or repository policy;
- bypass a required delivery gate;
- authorize implementation without a validated task;
- broaden a governing task;
- replace the exact governing task revision;
- self-approve implementation acceptance;
- convert acceptance into release authorization;
- weaken security, privacy, safety, compliance, permission, or side-effect boundaries.

A direct user or designated-authority instruction MAY legitimately change repository authority when it is explicit and applicable. Do not infer such authority merely from a generic or ambiguous Global Rule.

If an active Global Rule, Workspace Rule, direct instruction, and canonical repository authority materially conflict or leave authority ambiguous, stop and surface the conflicting sources and affected delivery decision rather than silently continuing.

## Skills, plugins, and engineering methodology

Antigravity skills, plugins, MCP servers, browser capabilities, agents, workflows, and other runtime-native capabilities are engineering, analysis, and evidence aids.

Use relevant installed capabilities when they materially improve the current responsibility and repository policy permits their use.

Runtime methodology remains subordinate to:

1. applicable human and approved repository authority;
2. `.agents/software-workflow.md`;
3. `.agents/AGENTS.md`;
4. the exact governing validated task when executing;
5. applicable approval, permission, security, privacy, and side-effect boundaries.

Installed capability does not become repository authority.

A skill, plugin, workflow, or agent MUST NOT be used to justify changing a delivery objective, requirement, architecture decision, acceptance criterion, approval state, or release state without legitimate authority.

## Superpowers

When Superpowers is installed and applicable, use it according to its current Antigravity skill-routing and session bootstrap behavior.

Superpowers MAY guide technical practices such as:

- design exploration;
- implementation planning;
- test-driven development;
- systematic debugging;
- work isolation;
- subagent coordination;
- technical review;
- verification before completion.

Superpowers governs **how technical work is performed**.

The canonical `.agents/` framework governs **what delivery work is legitimate, bounded, reviewable, and acceptable**.

Superpowers-generated design documents, plans, specifications, or similar methodology artifacts do not automatically become approved repository authority.

During Executor work, keep methodology planning ephemeral unless the governing task or applicable repository authority explicitly permits the artifact to be persisted.

Do not commit methodology artifacts unless both artifact creation and commit are authorized.

If a Superpowers workflow requests an action that conflicts with applicable direct user instructions, approved repository authority, the governing task, approval boundaries, or required stop conditions, treat it as a methodology conflict.

Adapt the methodology when its own rules allow that adaptation. If it cannot be followed without violating those boundaries, stop and surface the conflict.

## Workflows

Antigravity Workflows MAY be used as runtime convenience wrappers for repeatable procedures.

A Workflow MUST NOT become a second canonical delivery protocol.

If a runtime-specific Workflow invokes or summarizes repository planning, it MUST route back to the canonical procedure:

```text
.agents/prompts/plan-create-task.md
```

Do not maintain a divergent copy of that Planner/Reviewer procedure under Antigravity workflow files.

## Repository intelligence

When Graphify, Codebase Memory MCP, or equivalent repository-intelligence capabilities are available, follow the intelligence boundaries defined by `.agents/AGENTS.md` and the active Planner/Reviewer procedure or governing task.

Derived graphs, indexes, summaries, search results, and symbol maps are supporting intelligence.

Material conclusions MUST be verified against approved repository authority or current observed implementation evidence as applicable.

## Agents and delegation

Antigravity MAY use supported multi-agent or delegated-work capabilities when appropriate.

Delegation does not create new delivery authority.

### Planner / Reviewer delegation

Planner or Reviewer delegation MAY occur before a governing task exists.

Delegated work MUST remain bounded by:

- current verified repository state and accepted baseline when known;
- applicable intended authority;
- the specific planning, discovery, evidence, or review question;
- applicable approval and side-effect boundaries.

Planning or review delegation MUST NOT silently become implementation mutation.

### Executor delegation

Executor delegation MUST remain bounded by the same:

- implementation baseline;
- exact governing task revision;
- authority inputs;
- in-scope and preserved behavior;
- execution constraints;
- stop conditions;
- remaining approval requirements;
- side-effect authorization.

Parallel implementation MUST respect explicit dependencies and overlapping write surfaces.

Independent implementation objectives that require separate validated tasks MUST NOT be hidden inside delegated work.

Agent summaries and artifacts are supporting evidence until verified against the repository.

## Antigravity artifacts

Antigravity may create plans, task lists, screenshots, recordings, diagrams, diffs, or other runtime artifacts for communication and verification.

Runtime artifacts are not automatically repository authority.

Do not treat an Antigravity-generated plan as a replacement for:

- approved business or product authority;
- requirements;
- architecture;
- the canonical Planner/Reviewer procedure;
- a validated task;
- verification evidence required by the task;
- Reviewer acceptance;
- Release Gate approval.

When an artifact records useful evidence, preserve or reference it only according to repository policy and the governing delivery scope.

## Terminal, browser, file, and external-system permissions

Antigravity settings determine what the runtime is technically able to access or execute.

Runtime capability does not itself authorize repository delivery side effects.

Apply both boundaries:

```text
runtime permission
AND
repository delivery authorization
```

This applies to actions such as:

- shell commands with material side effects;
- Git commits;
- pushes or pull requests;
- dependency installation or replacement;
- browser actions that mutate external systems;
- production or infrastructure changes;
- destructive data operations;
- deployment;
- publication;
- release;
- access outside the intended workspace or project boundary.

If either boundary is not satisfied, do not perform the action.

Strict Mode, command review settings, sandboxing, browser restrictions, and file-access controls MAY strengthen runtime safety but do not replace repository authorization.

## Evidence and completion

Use Antigravity editor, terminal, browser, artifacts, agents, and other tools to gather actual evidence where appropriate.

Do not represent:

- inferred command results;
- unobserved tests;
- local checks as CI;
- agent summaries;
- generated artifacts;
- plugin output;
- cached repository intelligence;

as stronger evidence than was actually observed.

Before reporting **Review Required**, satisfy the governing task's applicable verification requirements and accurately report any remaining verification limitation.

If execution reaches a valid stop condition before a reviewable implementation state exists, report the task's **Planning Required** terminal outcome with supporting evidence instead of claiming successful completion.

Final implementation acceptance remains a Planner/Reviewer responsibility under the canonical `.agents/` framework.

## Operating rule

For every material repository action:

```text
Antigravity Always-On workspace rule
→ .agents/AGENTS.md
→ role-specific canonical loading
→ applicable Antigravity skills/plugins/agents/workflows
→ bounded work
→ observed evidence
→ canonical Planner/Reviewer loop
```

When Antigravity runtime methodology and repository delivery governance differ, preserve repository authority and surface the conflict.
