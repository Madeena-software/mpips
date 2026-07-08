# MPIPS Agent Control Center

This directory stores the working context, rules, prompts, and state that AI
agents must use when operating in this repository. It is intended to reduce
context loss between sessions and keep future work aligned with the actual
Python/FastAPI/Celery service in this repo.

## Directory Index

- `AGENTS.md`: Root rules that apply to every agent session in this workspace.
- `README.md`: This index and operating guide.
- `history.md`: Append-only session log.
- `memory.json`: Machine-readable project snapshot.
- `memory/state.md`: Current session state, health status, issues, and next
  steps.
- `prompts/prompts.md`: Reusable CORE-framework session prompts.
- `prompts/prd-generator.md`: Prompt for regenerating `docs/PRD.md` from the
  MPIPS codebase.
- `prompts/verify-features-prd.md`: Prompt for auditing implementation against
  `docs/PRD.md`.
- `rules/project-context.md`: Human-readable project overview, setup, env
  config, structure, and conventions.
- `rules/python-fastapi-celery.md`: Stack-specific architecture, security,
  performance, and verification rules.
- `rules/server-access-constraints.md`: Deployment and infrastructure access
  constraints.
- `rules/testing-pyramid.md`: Testing strategy and required commands.

## Instructions For AI Agents

1. Start every session by reading `.agents/memory/state.md`.
2. Load the applicable files in `.agents/rules/` before changing code or docs.
3. Use `docs/PRD.md` as the product authority for MPIPS behavior.
4. Keep MPIPS documented as a reusable Madeena image-processing execution
   service. Do not narrow it to a single downstream product unless the PRD is
   explicitly revised.
5. Update `.agents/history.md` and `.agents/memory/state.md` when your work
   changes project state, verification status, known issues, or next steps.

## Instructions For Humans

- Keep product decisions in `docs/PRD.md`.
- Keep agent workflow and current state in `.agents/`.
- When a session produces a durable decision, add it to `history.md` and
  update `memory/state.md`.
- If old history grows beyond 15 to 20 entries, archive older sessions into a
  dated file such as `.agents/history/archive_2026_Q3.md`.
