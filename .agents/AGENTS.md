# Project-Scoped Agent Rules

These rules apply to all AI agent interactions within `/var/www/mpips`.

## Control Center

The `.agents/` directory is the source of truth for AI workflow, repository
context, and session state. Product behavior and business requirements are
governed by `docs/PRD.md`.

1. Start every session by reading `.agents/memory/state.md`.
2. Read and follow the rules in `.agents/rules/` before editing files.
3. Treat `docs/PRD.md` as the product authority. If `.agents/` context
   conflicts with the PRD or the code, treat `.agents/` as stale and update it
   as part of the session.
4. Preserve the current service boundary: MPIPS is a reusable Madeena image
   processing execution service, not an MHCS-member-only application.
5. Do not write application code when the task is documentation/bootstrap-only.

## End-of-session

Before ending a task that changes project state:

1. Append a short entry to `.agents/history.md`.
2. Update `.agents/memory/state.md` when goals, milestones, health status, or
   known issues changed.
3. Report verification commands run and any commands that could not be run.
