# AI Agent Prompts & Frameworks

## The CORE Framework
Every interaction should be structured using the CORE framework:
- **Context**: Establish the current state and background.
- **Objective**: Define the clear, singular goal for the session.
- **Role**: Assume the persona of an Expert Software Architect.
- **Expectations**: Define the specific deliverables and constraints.

## 4-Phase Session Loop
AI Agents must strictly follow this 4-phase loop for all tasks:
1. **Phase 1: Load Game**: Read `memory/state.md` to establish context.
2. **Phase 2: Plan Before Code**: Draft an implementation plan and request human approval before executing any file changes.
3. **Phase 3: Debugging Loop**: Write code, run tests, and iterate until the feature/fix is stable.
4. **Phase 4: Save Game**: Update `memory/state.md` and append the session details to `history.md`.

---

## Copy-Paste Templates for Humans

### Starting a New Feature
```text
I want to build a new feature: [Feature Name].
Please use the CORE Framework to structure this request.
Phase 1: Load the game state.
Phase 2: Review the PRD and create an implementation plan for this feature, focusing on the Laravel architecture. Request my approval before writing code.
```

### Fixing a Bug
```text
We have a bug: [Bug Description/Error Message].
Phase 1: Load the game state.
Phase 2: Plan the fix. Remember that TDD is mandatory. Plan the failing test first.
Phase 3: Execute the TDD loop.
```

### Refactoring
```text
I want to refactor: [Component/Module].
Phase 1: Load the game state.
Phase 2: Provide a refactoring plan that adheres to our Laravel/Filament architectural rules.
Phase 3: Execute the refactoring and ensure all existing Pest/Dusk tests pass.
```
