# MPIPS — Repository Entry Point

Before planning, reviewing, modifying files, generating code, or running commands:

1. Read `.agents/AGENTS.md` completely.
2. Follow it as the canonical repository-wide agent contract.
3. Inspect the current repository state before making claims about existing behavior.
4. Load only the context, skills, roles, tasks, and evidence relevant to the current request.
5. Stop and report the issue if a required instruction, context, skill, task, or evidence source cannot be read.
6. Do not guess missing image-processing, DICOM, calibration, security, authorization, deployment, or product requirements.

Explicit user instructions and higher-priority runtime instructions take precedence over repository files.

## MPIPS context routing

Read `.agents/context/project.md` for the approved repository-wide product scope, architecture, technology choices, API boundary, image-processing flow, DICOM conversion path, security constraints, deployment model, and external integration assumptions.

Use repository evidence to determine the affected area before loading additional context.

For API routing, request validation, authentication, authorization, idempotency, and HTTP behavior, inspect the applicable code under:

```text
mpips/api/
```

For NPZ handling, image-processing orchestration, calibration, TIFF generation, DICOM conversion, enrichment, and validation, inspect the applicable code under:

```text
mpips/conversion/
mpips/engine/imager_pipeline/
```

For worker isolation, host-launcher behavior, containers, runtime permissions, and production deployment, inspect the applicable files under:

```text
docker/
docker-compose.prod.yml
.github/workflows/
```

For tests and verification evidence, inspect the relevant files under:

```text
tests/
```

Load only the files required for the current change. For cross-cutting work, inspect every affected boundary before modifying behavior.

The current product scope must come from `.agents/context/project.md`, not from the mere presence of legacy or generic platform code.

Do not assume that generic DAG, Celery, S3, URL-processing, webhook, callback, or node-catalog code is part of the active production product unless the approved context and current task explicitly say so.

## Task routing

Files under `.agents/tasks/` are versioned execution contracts and are not executed automatically.

Execute a task only when the user explicitly identifies that task or explicitly requests execution of a specific published task.

Before task execution:

1. Read `.agents/skills/agent-task/SKILL.md` completely.
2. Follow its Execute procedure.
3. Validate the identified task using the validator required by that skill.
4. Stop if validation fails or the required validator is unavailable.
5. Follow the task's runtime inputs, scope, iteration limit, approval gates, acceptance criteria, verification requirements, and output contract.
6. Do not edit a published task file to store runtime values, progress, command output, or results.
7. Report success only when all required acceptance criteria and verification checks pass.
8. Do not continue to a subsequent task until the current task has been independently reviewed and accepted.

## Framework boundary

Do not modify files marked with:

```text
<!-- antigravity-code-agent-template:managed -->
```

during ordinary product implementation.

Modify managed framework files only when the user explicitly requests maintenance or customization of the Antigravity framework.

Project-specific context, task definitions, and other files intentionally created for MPIPS may be added or revised only through their applicable framework procedures.

## Evidence boundary

Files under `.agents/context/` describe approved requirements, constraints, and target behavior.

They are not proof that the corresponding behavior is already implemented.

Determine current behavior from repository evidence, including:

- source code;
- tests;
- configuration;
- dependency manifests;
- Docker and deployment files;
- command output;
- registered application routes;
- generated artifacts;
- version-control state.

Do not claim implementation or completion without relevant verification evidence.

Do not silently resolve material conflicts between approved context and repository behavior.

Report conflicts affecting:

- image-processing correctness;
- calibration integrity;
- DICOM conformance;
- request authentication or authorization;
- tenant isolation;
- replay or idempotency controls;
- unsafe deserialization;
- filesystem or container isolation;
- network access;
- deployment safety;
- patient or study metadata integrity.

## Protected conversion boundary

Treat the approved TIFF-to-DICOM converter as a protected implementation boundary.

Do not modify:

```text
mpips/engine/imager_pipeline/tiff_json_to_dcm.py
```

unless the user explicitly requests a converter replacement task and the applicable task contract authorizes that change.

When a task requires converter preservation, verify its expected SHA-256 before and after the work.

Do not change DICOM tag mappings, UID behavior, pixel encoding, calibration inputs, or image-processing behavior as an incidental refactor.

## Repository-state boundary

Before changing files:

1. Record `git rev-parse HEAD`.
2. Record `git status --short`.
3. Stop if the task requires a clean tree and the tree is not clean.
4. Preserve all pre-existing user changes.
5. Do not reset, clean, stash, amend, rebase, or discard work unless explicitly authorized.
6. Stage only task-owned files.
7. Do not use `git add -A` unless explicitly authorized.
8. Do not push, deploy, or modify production infrastructure unless the user and active task explicitly authorize it.

After changing files:

1. Run the smallest relevant focused verification first.
2. Run every verification command required by the active task.
3. Inspect the final diff and changed-file list.
4. Confirm protected files and unrelated areas were not modified.
5. Report exact commands, results, residual risks, and final repository state.
