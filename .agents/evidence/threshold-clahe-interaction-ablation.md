# I-5B Threshold × CLAHE interaction ablation

Task: `.agents/tasks/real-radiograph-threshold-clahe-interaction-ablation.md @ 82cf2187b2efd6146de790021c1ba5e4e307b9d7`
Implementation baseline: `fe164f7c39697765f1c34b876c080efb34ffe36f`
Evidence revision: `be726db2fd66906b9f51bb90f9a24b921009ccce`

Primary cohort: exactly six identities: 3 `Kepala` (`I-1-1`, `I-1-2`, `I-1-4`) and 3 `Tulang Belakang` (`I-1-1`, `I-1-2`, `I-1-3`). Phase A completed 42 requested method × image characterizations. `T_ALT1=otsu` and `T_ALT2=knee` were selected by threshold-stage mask disagreement only; no reference IQA or candidate score was used.

## Matrix and reuse

The Phase-B matrix contains exactly 4 × 3 × 6 = 72 logical rows: 72 COMPARABLE, 0 NON-COMPARABLE, 0 ERROR. `18` accepted I-5A rows were individually reused; `newly_computed_rows = 72 - reused_rows = 54`.

## Corrected interpretation

Otsu collapses all governed outputs to zero. Knee produces near-total sparsity. Low Pearson is candidate degradation, not geometry failure. CLAHE provides measurable structural value under NONE/AUTO. M06 vs M15 remains a parameter trade-off.

Threshold classification: **THRESHOLD VALUE NOT SUPPORTED**. CLAHE classification: **CLAHE VALUE SUPPORTED**. Interaction classification: **INTERACTION SIGNAL PRESENT — STAGE-ORDER FOLLOW-UP JUSTIFIED**. This interaction classification does NOT authorize stage reordering.

Determinism: **VERIFIED / PASS** using the four exported cases.

## Production HOLD

Production HOLD remains true. No production/default/config/code change, no stage-order experiment, no full-corpus expansion, and converter unchanged. Protected converter SHA256: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
