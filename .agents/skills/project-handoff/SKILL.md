---
name: project-handoff
description: Use this skill when the user asks to save unfinished progress, prepare a sanitized handoff, pause complex work, or resume it in a later conversation.
license: MIT
---

<!-- antigravity-code-agent-template:managed -->
# Project Handoff

Persist only the minimum state another conversation needs.

## Process

1. Inspect the actual working tree or available file state, repository checkpoint, active task, completed changes, verification output, blockers, and next action.
2. Copy `.agents/memory/state.template.md` to `.agents/memory/state.md` when the state file does not exist.
3. Replace stale state with a concise current handoff. Link an active immutable task instead of duplicating or modifying it, and record the selected model only when verified.
4. Include only verified file, command, and status information with provenance and timestamps. Record superseded facts and unknowns explicitly.
5. Re-read the result and remove secrets, tokens, credentials, personal data, private prompts, hidden reasoning, and transcript-like detail.

## Output contract

Write `.agents/memory/state.md` and report its path.

## Boundaries

- Do not create commits, branches, or Git metadata.
- Do not mark work complete when required implementation or verification remains.
- Do not use the handoff as a substitute for durable project context or an immutable task assignment.
- Never transfer permissions, approvals, or authority; the receiving session must reverify them and all saved claims.
