# BED Threshold Policy Reference Grounding

Classification: **BED THRESHOLD POLICY UNRESOLVED**

Phase-5 evidence: `80d815c191766798bf0a6977f7abcbe24977cfbd`. The accepted 12-case Phase-5
cohort was used unchanged; no new cohort was selected.

## Inventory

The read-only Drive inventory found **196 processed/reference
TIFFs** across six sessions and their subject folders. Historical Phase-5 inventory records
196 acquisition NPZ candidates, 6 gain NPZ
files, 4 calibration/processed NPZ files, and no
generated outputs in scope. TIFF bytes were not materialized, so reference hashes and image
dimensions/dtypes are unavailable.

The refreshed normalized inventory digest is `99691cb7d676239c51bde7a6eab3cf230144ff0f8052de9713ee024f6320a18d`. It has
0 additions, 0 removals, and 0
changed metadata records versus the provisional inventory; it matches the provisional
inventory.

## Relationship results

All 84 same-session/subject reference candidates were classified
without treating folder proximity as proof. **0**
were exact lossless matches, **4** had
filename-level acquisition-number matches but insufficient provenance, and
**80** were same-subject/different-
or-unknown-acquisition candidates. No derived-unknown or non-comparable mappings were created.

Filename-level matches cannot be promoted to exact identity without a derivation log or
metadata. No allowed geometry transform was applied; no mapping is lossless-comparable.

## Short-circuit

Because no accepted Phase-5 case has an `EXACT_SAME_ACQUISITION_LOSSLESS` reference,
Phase 6 short-circuited. AUTO/NONE arrays were not regenerated, and reference-vs-AUTO/NONE
measurements were not run.

The result is engineering provenance evidence only, not clinical ground truth or a runtime-policy decision.
