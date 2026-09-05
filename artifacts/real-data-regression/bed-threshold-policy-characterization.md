# BED Threshold Policy Characterization

Classification: **BED THRESHOLD POLICY UNRESOLVED**

Source: `https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8` (read-only). Inventory: 196 acquisition NPZ candidates, 6 gain NPZ files, 4 calibration or processed NPZ files, 96 folders visited.

Selection was frozen before processing: lexicographic session/subject groups, stable acquisition ordering, first/last distinct acquisitions, round-robin, maximum 12.

Selected and successfully paired cases: 12; excluded: 0.

Final AUTO-minus-NONE mean-intensity delta median: -12546.732126790364.

Reference comparability: **NON-COMPARABLE**. NONE is an identity control, not a ground-truth reference; classification therefore remains unresolved.

## Case-level evidence

| Case | Session / subject | AUTO threshold | AUTO edge recall | NONE edge recall | AUTO lost informative tiles | NONE lost informative tiles | AUTO final mean | NONE final mean |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Ambil Data 1 / kambing-1 | 0.010709 | 0.2614 | 1.0000 | 0.4967 | 0.0000 | 9808.14 | 21956.45 |
| 2 | Ambil Data 1 / kambing-2 | 0.010330 | 0.2211 | 1.0000 | 0.5394 | 0.0000 | 8444.17 | 23214.50 |
| 3 | Ambil Data 2 / kambing-1 | 0.010731 | 0.2501 | 1.0000 | 0.5270 | 0.0000 | 9395.65 | 21759.55 |
| 4 | Ambil Data 2 / kambing-2 | 0.010283 | 0.2419 | 1.0000 | 0.5500 | 0.0000 | 9056.60 | 22102.23 |
| 5 | Ambil Data 3 / kambing 1 | 0.010536 | 0.2363 | 1.0000 | 0.5326 | 0.0000 | 9061.81 | 21292.44 |
| 6 | Ambil Data 3 / kambing 2 | 0.010105 | 0.2356 | 1.0000 | 0.5570 | 0.0000 | 8916.38 | 21439.83 |
| 7 | Ambil Data 4 / kambing 1 | 0.010596 | 0.2350 | 1.0000 | 0.5261 | 0.0000 | 9004.52 | 21574.54 |
| 8 | Ambil Data 4 / kambing 2 | 0.010211 | 0.2327 | 1.0000 | 0.5632 | 0.0000 | 8859.98 | 21474.15 |
| 9 | Ambil Data 5 / kambing 1 | 0.009841 | 0.2225 | 1.0000 | 0.6360 | 0.0000 | 8490.22 | 21339.35 |
| 10 | Ambil Data 5 / kambing 2 | 0.010422 | 0.2339 | 1.0000 | 0.5368 | 0.0000 | 8929.27 | 21441.44 |
| 11 | Ambil Data 6 / kambing 1 | 0.010477 | 0.2360 | 1.0000 | 0.5316 | 0.0000 | 9009.31 | 21312.96 |
| 12 | Ambil Data 6 / kambing 2 | 0.010085 | 0.2160 | 1.0000 | 0.5488 | 0.0000 | 8261.22 | 20904.49 |

## Grouping and conflicts

The complete inventory and selection manifest are in the JSON artifact. Selected cases are distributed across all six sessions and the selection was frozen before either result was inspected. Case-level direction and outliers must be interpreted with the NON-COMPARABLE reference limitation above.

IQA compares each threshold-stage output with the same-geometry normalized pre-threshold image using `mpips.iqa.analyze_structural_preservation`. No clinical or diagnostic conclusion is made.

The classification is decision support only and does not change BED runtime policy.
