# I-5B Threshold × CLAHE interaction ablation

Task: `.agents/tasks/real-radiograph-threshold-clahe-interaction-ablation.md @ 82cf2187b2efd6146de790021c1ba5e4e307b9d7`
Implementation baseline: `fe164f7c39697765f1c34b876c080efb34ffe36f`

Primary cohort: exactly six identities: 3 `Kepala` (`I-1-1`, `I-1-2`, `I-1-4`) and 3 `Tulang Belakang` (`I-1-1`, `I-1-2`, `I-1-3`). Phase A completed 42 requested method × image characterizations. `T_ALT1=otsu` and `T_ALT2=knee` were selected by threshold-stage mask disagreement only; no reference IQA or candidate score was used.

## Matrix and reuse

The Phase-B matrix contains exactly 4 × 3 × 6 = 72 logical rows. `18` accepted I-5A rows were individually reused after identity, gain, calibration, pre-CLAHE hash, and shape proof; `newly_computed_rows = 72 - reused_rows = 54`.

## Results

Comparable/non-comparable/error counts: 36/36/0. Structural metrics, intensity/clipping values, paired deltas, interaction contrasts, hashes, and provenance are in the JSON and CSV. This is exploratory decision support only; no weighted score or clinical claim was used.

Threshold classification: **THRESHOLD RELEVANCE UNRESOLVED**. CLAHE classification: **CLAHE RELEVANCE UNRESOLVED**. Interaction classification: **INTERACTION / TRADE-OFF UNRESOLVED**.

## Production HOLD

Production defaults remain unchanged. No stage reordering, Fiji, full-corpus expansion, production code/configuration/schema/test/reference-tool change, or external-data mutation was performed. Protected converter SHA256: `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.
