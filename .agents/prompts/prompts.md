# AI Agent Prompts & Frameworks

## CORE Framework

Structure substantial sessions with CORE:

- Context: Load the current repo state, PRD, relevant rules, and recent memory.
- Objective: State the one concrete outcome for the session.
- Role: Work as a pragmatic senior engineer for a Python/FastAPI/Celery image
  processing service.
- Expectations: Name the deliverables, verification commands, constraints, and
  files that must be updated before finishing.

## 4-Phase Session Loop

1. Phase 1: Load Game
   - Read `.agents/memory/state.md`.
   - Read relevant `.agents/rules/` files.
   - Read `docs/PRD.md` when behavior, scope, or product boundaries matter.
2. Phase 2: Plan Before Code
   - Inspect the existing implementation.
   - Identify the smallest safe change.
   - For risky or broad changes, present a short implementation plan before
     editing.
3. Phase 3: Debugging Loop
   - Write or update tests first for bug fixes.
   - Implement the change.
   - Run targeted verification, then broader verification when risk warrants.
   - Iterate until the outcome is stable or the blocker is explicit.
4. Phase 4: Save Game
   - Append the session outcome to `.agents/history.md` when project state
     changed.
   - Update `.agents/memory/state.md` when health, known issues, milestones, or
     next steps changed.
   - Report commands run and any verification that could not be completed.

## Copy-Paste Templates For Humans

### Starting a New Feature

```text
I want to build a new MPIPS feature: [Feature Name].
Use the CORE framework.
Phase 1: Load `.agents/memory/state.md`, relevant `.agents/rules/`, and `docs/PRD.md`.
Phase 2: Inspect the existing FastAPI/Celery/image_engine implementation and propose the smallest safe implementation plan before editing.
Phase 3: Implement with tests and run targeted verification.
Phase 4: Update `.agents/history.md` and `.agents/memory/state.md` if project state changed.
```

### Fixing a Bug

```text
We have a bug in MPIPS: [Bug Description/Error Message].
Use the CORE framework.
Phase 1: Load `.agents/memory/state.md` and the relevant rules.
Phase 2: Identify the failing behavior and write or update a pytest test that reproduces it.
Phase 3: Fix the code, rerun the focused test, then run broader impacted tests.
Phase 4: Update `.agents/history.md` and `.agents/memory/state.md` with the fix and verification.
```

### Refactoring

```text
I want to refactor this MPIPS area: [Component/Module].
Use the CORE framework.
Phase 1: Load `.agents/memory/state.md`, relevant rules, and the current tests for this area.
Phase 2: Explain the refactor boundary, expected behavior preservation, and verification plan before editing.
Phase 3: Refactor without changing external behavior and run targeted tests plus lint/type checks when available.
Phase 4: Update `.agents/history.md` and `.agents/memory/state.md` if durable project context changed.
```
