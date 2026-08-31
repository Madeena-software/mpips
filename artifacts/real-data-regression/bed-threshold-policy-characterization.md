# BED Threshold Policy Characterization

Classification: **BED BYPASS SUPPORTED**

Source: `https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8` (read-only). Inventory: 200 acquisition NPZ candidates, 6 gain NPZ files, 96 folders visited.

Selection was frozen before processing: lexicographic session/subject groups, stable acquisition ordering, first/last distinct acquisitions, round-robin, maximum 9.

Selected and successfully paired cases: 9; excluded: 0.

## Case-level evidence

| Case | Session / subject | AUTO threshold | AUTO edge recall | NONE edge recall | AUTO lost informative tiles | NONE lost informative tiles | AUTO final mean | NONE final mean |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Ambil Data 1 / kambing-1 | 0.010709 | 0.2614 | 1.0000 | 0.4967 | 0.0000 | 9808.14 | 21956.45 |
| 2 | Ambil Data 1 / kambing-2 | 0.010330 | 0.2211 | 1.0000 | 0.5394 | 0.0000 | 8444.17 | 23214.50 |
| 3 | Ambil Data 1 / kambing-3 | 0.010082 | 0.2320 | 1.0000 | 0.5862 | 0.0000 | 8657.89 | 23282.87 |
| 4 | Ambil Data 2 / kambing-1 | 0.010731 | 0.2501 | 1.0000 | 0.5270 | 0.0000 | 9395.65 | 21759.55 |
| 5 | Ambil Data 2 / kambing-2 | 0.010283 | 0.2419 | 1.0000 | 0.5500 | 0.0000 | 9056.60 | 22102.23 |
| 6 | Ambil Data 2 / kambing-3 | 0.010182 | 0.2246 | 1.0000 | 0.5484 | 0.0000 | 8444.82 | 22311.62 |
| 7 | Ambil Data 3 / kambing 1 | 0.010536 | 0.2363 | 1.0000 | 0.5326 | 0.0000 | 9061.81 | 21292.44 |
| 8 | Ambil Data 3 / kambing 2 | 0.010105 | 0.2356 | 1.0000 | 0.5570 | 0.0000 | 8916.38 | 21439.83 |
| 9 | Ambil Data 3 / kambing 3 | 0.010015 | 0.2309 | 1.0000 | 0.5602 | 0.0000 | 8722.76 | 21356.19 |

## Grouping and conflicts

All three sessions and all three subject folders show the same direction:
AUTO has lower edge recall and higher lost-tile fraction than NONE in every
case. The final AUTO-minus-NONE mean-intensity delta median is -12633.43;
final hashes differ in all nine pairs. There is no case-level conflict or
outlier that favors configured thresholding. These are structural/intensity
comparisons, not clinical or diagnostic claims.

Final AUTO-minus-NONE mean-intensity delta median: -12633.432549560548.

IQA compares each threshold-stage output with the same-geometry normalized pre-threshold image using `mpips.iqa.analyze_structural_preservation`. No clinical or diagnostic conclusion is made.

The classification is decision support only and does not change BED runtime policy.
