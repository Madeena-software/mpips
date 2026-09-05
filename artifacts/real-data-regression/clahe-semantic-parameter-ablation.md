# MPIPS real-radiograph CLAHE semantic/parameter ablation

Governing task: `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation.md @ a1585bbf1b1710d955595703f7821526b3073b23`  
Bounded-cohort addendum: `7e5d28c0a1cad2c70fec57d634bbdc72fd62a07e`
Accepted baseline: `15305dd000538aaf3459e4124975ac17892c4d31`  

Scope: **EXPLORATORY / DECISION-SUPPORT**; full-corpus processing is optional confirmatory work, not required. The bounded primary matrix contains `10` candidates and `6` selected image identities (`60` candidate × case combinations). The eligible inventory contains `38` mapped images; exclusions are recorded in the JSON inventory. The deterministic primary cohort is 3 `Kepala` (`I-1-1`, `I-1-2`, `I-1-4`) and 3 `Tulang Belakang` (`I-1-1`, `I-1-2`, `I-1-3`).

Checkpoint reuse: `26` identities and `260` rows existed before bounded extraction; all six selected identities already had complete ten-candidate blocks, so `0` new combinations were computed. `20` outside-cohort identities (`200` candidate rows) were intentionally excluded as `SUPPLEMENTAL / OUTSIDE PRIMARY BOUNDED COHORT`; no supplemental candidate rows enter the primary matrix, and the remaining corpus was not processed.

## Candidate matrix

| ID | Semantic contract | Slope |
|---|---|---:|
| C0 | CLAHE disabled | N/A |
| M06 | MPIPS precise | 0.6 |
| M103 | MPIPS precise | 1.03 |
| M15 | MPIPS precise | 1.5 |
| M20 | MPIPS precise | 2.0 |
| M30 | MPIPS precise | 3.0 |
| F103 | pinned Fiji Flat | 1.03 |
| F15 | pinned Fiji Flat | 1.5 |
| F20 | pinned Fiji Flat | 2.0 |
| F30 | pinned Fiji Flat | 3.0 |

## Feasibility and freeze

The tracked `ReferenceHarness.java` over the retained pinned Fiji environment was sufficient. The full-resolution F15 sentinel succeeded at 3053×4059 uint16 with no resize/downsampling; sentinel and deterministic rerun details are in the machine-readable artifact. All candidates share the same raw, gain, calibration fingerprint, detector mode, FFC, geometry, normalization, threshold, inversion, contrast, denoise, and corrected Hybrid Median state. The pre-CLAHE stage hash is held constant per mapped image.

## Results

All `60` matrix combinations were comparable; errors: `0`. Six structural metrics, Pearson alignment, valid overlap, required intensity/clipping fields, hashes, paired deltas against M06 and C0, aggregates, and worst cases are in the JSON/CSV artifacts.

Decision-support outcome: **NO DOMINANT CANDIDATE / TRADE-OFF UNRESOLVED**. This is not a weighted score, clinical conclusion, semantic selection, or production-default decision.

Predeclared visual review of `I-1-1` and `I-2-1` found the `C0`, `M06`, and `F15` views retained the same gross anatomy and hard foreground/background separation. `F15` showed modestly stronger local contrast in faint peripheral/ear and weak rib/vertebral structures, but `M06` and `F15` remained visually close and the reviewed representatives did not provide a decisive clipping difference. This is structural, non-clinical inspection only.

## Production HOLD

No production source, configuration, schema, test, converter, dependency, or reference tooling was changed. `clahe_max_slope=0.6` remains the production default. No radiograph, JAR, JDK, class, or thumbnail is included in the evidence commit.
