# IQA before-and-after comparison

Task contract state: Validated/Published
Owner and intended authority: Arif's request on 2026-10-16 to compare image metrics before and after processing, and explicit authorization to update both mipc and mpips.
Task path: .agents/tasks/iqa-before-after-comparison.md
Task revision: the full Git commit SHA containing this task publication, recorded by the executing session.

## Baselines and delivery state

- mipc implementation baseline: f30aa4ab75db7f0827714f79da373a6a27e53b9f.
- mpips implementation baseline: 8dd42a7106d13ff602f41a57b726668066791bec.
- Implementation baselines remain unchanged as of 2026-10-21. Preserve the unrelated untracked mipc docs/audits/ directory.
- This is a bounded UI and output-metadata enhancement. No existing task was found covering this comparison.
- Current mipc output metrics are persisted verbatim from each output's quality_assessment field; mpips currently calculates only processed-image metrics against its selected reference.

## Objective and traceability

IQA-COMPARE-1: Show original and processed BRISQUE-compatible proxy, CII, entropy, and EME values beside each other, with a signed numeric change. Source: user's screenshot and before/after request.
IQA-COMPARE-2: Calculate actual baseline values for future executions in mpips. Source: user's explicit approval to update both projects.
IQA-COMPARE-3: Preserve existing results and show unavailable baselines honestly. Source: compatibility constraint derived from existing stored output-only results.

Governing inputs: the user instructions above, each repository's .agents/AGENTS.md and .agents/software-workflow.md, mipc PRODUCT.md, DESIGN.md, and docs/PRD.md execution review and service-boundary requirements.

## Scope and preserved behavior

- mipc: update resources/views/filament/forms/components/iqa-metrics.blade.php and the IQA styles in public/css/mipc-filament-shell.css; add focused rendering tests.
- mpips: extend DAG output quality_assessment metadata with a nested before measurement map, retaining existing top-level processed scores; add focused executor contract tests.
- Use the actual original input selected for that output's reference. Verify input/output ancestry; do not pair unrelated images or invent a baseline when the original is unavailable.
- Preserve existing metric algorithms, precision, flat processed metric keys, output-node grouping, tenant boundaries, signed webhook validation, and existing image review/download controls.
- Keep computation in mpips and communication through the existing output metadata/webhook contract. No PHP/Python runtime coupling.
- Match the existing neutral light/dark interface; retain meaningful metric descriptions and explicitly describe the BRISQUE-compatible score as a proxy.
- No clinical quality claims or universal better/worse judgments from entropy/contrast changes.
- Exclude production API registration, DICOM processing, structural-safety policy, algorithm changes, migrations, historical backfills, dependency changes, deployments, pushes, and unrelated refactors.

## Acceptance and verification

- Each metric shows Before, After, and Change with two decimal places; signed changes are After minus Before.
- New output metadata includes real original measurements, where a valid original is available, without removing existing processed scores.
- Old output-only records continue to render their processed scores and show Not recorded for missing baselines; no change is calculated from absent values.
- Zero, missing/non-numeric values, unchanged scores, negative changes, and multiple outputs render correctly.
- Comparison remains legible and usable at desktop and narrow widths, with accessible column/metric labels and sufficient contrast in both themes.
- Run targeted PHP rendering/webhook tests with SQLite in an isolated test environment, and targeted Python IQA/executor tests. Report unavailable tools honestly.
- Inspect rendered desktop/mobile, light/dark comparison states. Run the design detector on changed UI files and review the final diffs in both projects.

## Dependencies, stop conditions, and approvals

Both repositories are independently versioned; publish this bounded contract in each before implementation. The mpips original-input selection must be verified before computing baseline values. Stop for unrelated changes, incompatible output/reference geometry semantics, required production-surface changes, or a materially broader requirement.

Publication authorization: Arif explicitly instructed implementation on 2026-10-21 after being asked to authorize task-only local commits in both projects. No implementation commit, push, deployment, dependency installation, secret access, or local database reset is authorized by that publication.

Return observed verification evidence and remaining limitations for review. Implementation acceptance is separate from release authorization.