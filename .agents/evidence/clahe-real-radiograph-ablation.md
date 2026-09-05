# I-5A CLAHE real-radiograph ablation evidence

Task: `.agents/tasks/real-radiograph-clahe-semantic-parameter-ablation.md @ a1585bbf1b1710d955595703f7821526b3073b23`  
Bounded-cohort addendum: `7e5d28c0a1cad2c70fec57d634bbdc72fd62a07e`
Baseline: `15305dd000538aaf3459e4124975ac17892c4d31`  

Status: **EXPLORATORY / DECISION-SUPPORT**. The bounded experiment reused six complete identity blocks from the preserved checkpoint (`26` identities / `260` rows); `0` new combinations were computed. `20` outside-cohort identities (`200` candidate rows) were excluded from primary analysis as `SUPPLEMENTAL / OUTSIDE PRIMARY BOUNDED COHORT`. The primary cohort is exactly 3 `Kepala` (`I-1-1`, `I-1-2`, `I-1-4`) and 3 `Tulang Belakang` (`I-1-1`, `I-1-2`, `I-1-3`). No supplemental candidate rows enter primary aggregates, and the remaining corpus was not processed. See `artifacts/real-data-regression/clahe-semantic-parameter-ablation.json` for the complete provenance, mapping inventory, candidate × case matrix, six-metric aggregates, paired deltas, intensity/clipping measurements, and exclusions.

Predeclared qualitative representatives `I-1-1` and `I-2-1` retained the same gross anatomy and hard separation across `C0`, `M06`, and `F15`; `F15` showed modestly stronger local contrast in faint peripheral/ear and weak rib/vertebral structures, without a decisive clipping difference. This observation is structural and non-clinical.

Terminal decision-support outcome: **NO DOMINANT CANDIDATE / TRADE-OFF UNRESOLVED**. Production HOLD: `clahe_max_slope=0.6` remains unchanged; acceptance/release authority remains with Planner/Reviewer.
