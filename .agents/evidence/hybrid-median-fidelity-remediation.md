# MPIPS Hybrid Median Fidelity Remediation — I-4D-Hybrid

Governing task: `.agents/tasks/hybrid-median-fidelity-remediation.md`.
Implementation baseline: `6c5e7772c93e8b498b47bedcaa2b4261f42e9420`.
Execution branch: `refactor/package-boundaries`.

## Reference provenance

The retained workspace `/tmp/mpips-imagej-reference-LyDbYJ` was present and
verified without downloading or installing anything:

| Artifact | Observed SHA256 |
|---|---|
| `Hybrid_2D_Median_Filter.java` | `494cc92747ba8e01e9ad19f16d735ffe8faf0b65eba00f02fda691bc5529af03` |
| `ij-1.54p.jar` | `2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20` |
| Temurin JDK archive | `d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331` |
| tracked `ReferenceHarness.java` | `86189871e94cc0d34f09976a8f61c1672fe05cc94c3226ecb51c137926d0ff56` |

The retained adapter has a tooling defect: it passes the requested size to a
private method parameter, while the plugin branches on its private `nsize`
field and never assigns that field. A temporary local copy of the adapter set
that field before invocation; its SHA256 was
`648d7d62ea56946d665db892cc84a40ebb02f8419214b1a5a8da46eefe14f9fa`. The
pinned plugin source, ImageJ jar, and JDK were unchanged. Corrected adapter
arguments `1`, `3`, and `5` exercise the plugin's 3x3, 5x5, and 7x7 branches.

Runtime verification:

```text
openjdk version "17.0.19" 2026-04-21
OpenJDK Runtime Environment Temurin-17.0.19+10
javac 17.0.19
```

## TDD evidence

The focused test file was copied into a detached baseline worktree at
`6c5e7772c93e8b498b47bedcaa2b4261f42e9420` before the production change.

```text
pytest -q tests/test_hybrid_median_fidelity.py
9 failed, 3 passed
```

The baseline mismatched the authoritative goldens at 14/121 pixels for 3x3,
34/121 for 5x5, 57/121 for 7x7, and 43/121 for the two-pass 5x5 case. The
wrapper case also mismatched 34/121 pixels.

## Implementation and authoritative parity

`ImageJReplicator.hybrid_median_filter_2d()` now builds flat-index candidate
arrays with the plugin's cascading fallbacks, computes PLUS/X/center
median-of-three values, and preserves the plugin's observable 7x7 fallback
behavior. NumPy padding was removed because it does not match ImageJ's flat
index semantics. The implementation remains Python-only and keeps the public
API, dtype, shape, channel-wise, repetition, and wrapper contracts.

Final direct comparisons against the corrected retained harness used an
asymmetric 11x11 fixture. It contains 4 corners, 36 non-corner edge pixels,
81 interior pixels, and 25 genuine 7x7 interior pixels:

```text
uint8 3x3: mismatch_count=0
uint8 5x5: mismatch_count=0
uint8 7x7: mismatch_count=0
uint8 5x5 repetitions=2: mismatch_count=0
uint16 3x3: mismatch_count=0
uint16 5x5: mismatch_count=0
uint16 7x7: mismatch_count=0
uint16 5x5 repetitions=2: mismatch_count=0
wrapper radius=2: mismatch_count=0
```

The focused suite also covers isolated PLUS/X/center selection cases. The
production default remains `filter_type="hybrid_imagej", radius=2`, which is
the verified 5x5 wrapper path.

## Verification

Observed after the implementation change:

```text
black --check .                         0
flake8 .                                0
mypy mpips                              Success: no issues found in 87 source files
pytest -q                               536 passed, 1 skipped, 72 warnings in 102.00s
```

The focused and downstream processing tests completed with `123 passed, 1
skipped` before the full-suite run. Warnings were existing dependency/runtime
deprecations and PyWavelets boundary warnings; no test failure occurred.

Performance sanity on a deterministic 256x256 uint16 grayscale array, 5x5,
one pass, three timed calls:

```text
baseline min: 0.0129s
remediated min: 0.0260s
```

The faithful flat-index implementation has a modest measured slowdown and no
strict performance threshold was specified.

Protected converter verification:

```text
a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0  mpips/conversion/tiff_json_to_dcm.py
```

Only Hybrid implementation, Hybrid/downstream expected outputs, focused tests,
and this evidence file changed. CLAHE, Circular Median, ContrastEnhancer,
defaults, configuration, and the protected converter implementation were not
remediated or altered.
