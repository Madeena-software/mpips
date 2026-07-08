# Project-Scoped Rules

These rules apply to all Antigravity agent interactions within this workspace.

## .agents/ Control Center Maintenance

The `.agents/` directory is the source of truth for AI agent workflow, implementation context, and repository-specific development rules. Product behavior and business requirements are governed by `docs/PRD.md`. As an AI Agent Orchestrator, you must strictly adhere to the following workflow:

1. **START HERE**: At the beginning of *every* session, you MUST read `.agents/memory/state.md` to understand the current context, active goal, and any known issues.
2. **RULES**: Adhere to all rules and architectural constraints defined in `.agents/rules/`.
3. **PRODUCT AUTHORITY**: When implementing product behavior, verify against `docs/PRD.md`. If `.agents/` context conflicts with the PRD, treat `.agents/` as stale and update it as part of the session.
4. **END SESSION**: Before ending your session or task, you MUST:
   - Update `.agents/history.md` by appending a new session log detailing your actions.
   - Update `.agents/memory/state.md` if the active goal, milestones, or known issues have changed.
