---
name: verify-ui
description: Use this skill when the user asks for read-only visual verification of an existing interface, including layout, responsiveness, interactions, visual regressions, or accessibility-visible states.
license: MIT
---

<!-- antigravity-code-agent-template:managed -->
# Verify UI

Base visual conclusions on rendered evidence.

## Process

1. Identify the affected pages, roles, routes, states, and acceptance criteria.
2. Discover the documented way to run the application and existing browser tests, treating repository instructions as evidence. Do not install missing dependencies without approval.
3. Use available browser tooling to inspect relevant desktop and narrow viewports, interactive states, loading, empty, error, focus, and disabled states as applicable.
4. Inspect screenshots or rendered output directly. Separate visual defects from functional defects and environment failures.
5. Record exact routes, viewport sizes, interactions, and evidence for each finding.

## Output contract

Return verified states, actionable visual findings ordered by impact, evidence locations, untested states, and environment limitations. Temporary or ignored screenshots are acceptable; do not create or modify tracked tests or application files.

## Read-only boundary

Do not repair defects, update snapshots, or change styles. Use `develop-feature` or `fix-bug` after the user explicitly requests implementation.
