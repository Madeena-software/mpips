# MPIPS ImageJ/Fiji Fidelity Characterization — I-4A

Governing task: `ae873d1d8ea04cb482a7896ca84088867e5524ec`; accepted implementation baseline: `dd13fc4dab512bbb59242bde7f5fb7cc6c5c370e`.

## Runtime and provenance

```json
{
  "clahe": {
    "commit": "0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0",
    "project": "axtimwalde/mpicbg",
    "retrieval": "https://github.com/axtimwalde/mpicbg",
    "source": "mpicbg.ij.clahe.Flat, FastFlat, Util",
    "source_sha256": {
      "FastFlat.java": "09fa2048f80d258a2ce02b8940373e2a9e9b8176e5b86e0a4c5ae6710114b3fd",
      "Flat.java": "112ba574034acb2c740dfcc5365fb9489305d62e9527df71665cac8971dedee2",
      "Util.java": "4dbe118c08eaa36a5f87c78930169383a602a84f25ca7b975284cb089bdd1689"
    }
  },
  "hybrid_median": {
    "project": "ImageJ plugin site",
    "retrieval": "https://wsr.imagej.net/ij/plugins/download/Hybrid_2D_Median_Filter.java",
    "sha256": "494cc92747ba8e01e9ad19f16d735ffe8faf0b65eba00f02fda691bc5529af03",
    "source": "Hybrid_2D_Median_Filter.java by Christopher Philip Mauer"
  },
  "imagej": {
    "artifact": "ij-1.54p.jar",
    "project": "imagej/ImageJ",
    "retrieval": "https://repo1.maven.org/maven2/net/imagej/ij/1.54p/ij-1.54p.jar",
    "sha256": "2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20",
    "source": "ij.plugin.ContrastEnhancer and ij.plugin.filter.RankFilters",
    "version": "1.54p"
  },
  "runtime": {
    "archive": "OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz",
    "archive_sha256_expected": "d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331",
    "archive_sha256_observed": "d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331",
    "build": "17.0.19+10",
    "checksum_verified": true,
    "java_version_output": "openjdk version \"17.0.19\" 2026-04-21\nOpenJDK Runtime Environment Temurin-17.0.19+10 (build 17.0.19+10)\nOpenJDK 64-Bit Server VM Temurin-17.0.19+10 (build 17.0.19+10, mixed mode, sharing)",
    "javac_version_output": "javac 17.0.19",
    "mpips_dependencies_changed": false,
    "persistent_environment_change": false,
    "release_tag": "jdk-17.0.19+10",
    "system_java_initially_available": false,
    "system_wide_installation": false,
    "temporary_location": "/tmp/mpips-imagej-reference-LyDbYJ",
    "vendor": "Eclipse Temurin / Eclipse Adoptium",
    "version": "17.0.19+10"
  }
}
```

## Production reachability

Temporal median is **NOT PRODUCTION-REACHABLE**: no pipeline caller or registered production API path was found. RGB/composite behavior was inspected secondarily; grayscale evidence does not establish RGB parity.

## Fixture matrix

`constant`, `two_level`, `ramp`, `sparse`, `narrow`, `full`, `impulse`, and `asymmetric_tail` cover uint8/uint16 stretch and equalization. `median_grid` covers hybrid, circular, and CLAHE boundary cases. The CLAHE fixture is a deterministic 128×128 ramp modulo 64 so the authoritative 256-bin implementation has non-full bins.

## Parameter mappings

MPIPS maps `blocksize=127` to `block_radius=63`; the Fiji call therefore uses `blockRadius=63`, `bins=256`, `slope=0.6`, and `composite=true`. Exact integer array equality is used for every executable case. Fiji Flat/FastFlat raise `ArithmeticException: / by zero` for this slope/data combination; those cases are recorded as `REFERENCE NOT RESOLVED`, not treated as parity.

## Final classification table

| Operation | Final classification |
|---|---|
| Contrast stretch uint8 | FIDELITY FAILURE |
| Contrast stretch uint16 | FIDELITY FAILURE |
| Equalize weighted uint8 | PARITY CONFIRMED |
| Equalize weighted uint16 | PARITY CONFIRMED |
| Equalize classic uint8 | PARITY CONFIRMED |
| Equalize classic uint16 | PARITY CONFIRMED |
| CLAHE Flat / precise | REFERENCE NOT RESOLVED |
| CLAHE FastFlat / fast | REFERENCE NOT RESOLVED |
| Hybrid Median 3x3 | FIDELITY FAILURE |
| Hybrid Median 5x5 | FIDELITY FAILURE |
| Hybrid Median 7x7 | FIDELITY FAILURE |
| Circular Median | PARITY CONFIRMED |
| Temporal Median | NOT PRODUCTION-REACHABLE |

## Aggregate results

| Operation | Cases | Mismatches |
|---|---:|---:|
| CLAHE FastFlat / fast | REFERENCE NOT RESOLVED | 2 | n/a |
| CLAHE Flat / precise | REFERENCE NOT RESOLVED | 2 | n/a |
| Circular Median | PARITY CONFIRMED | 6 | 0 |
| Contrast stretch | FIDELITY FAILURE | 48 | 438 |
| Equalize classic | PARITY CONFIRMED | 16 | 0 |
| Equalize weighted | PARITY CONFIRMED | 16 | 0 |
| Hybrid Median 3x3 | FIDELITY FAILURE | 2 | 28 |
| Hybrid Median 5x5 | FIDELITY FAILURE | 2 | 22 |
| Hybrid Median 7x7 | FIDELITY FAILURE | 2 | 20 |
| Temporal Median | NOT PRODUCTION-REACHABLE | — | — |

## Per-case measurements

| Operation | Fixture | Dtype | Parameters | Classification | Mismatch fraction | Max abs diff |
|---|---|---|---|---|---:|---:|
| Contrast stretch | constant | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | constant | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | constant | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | constant | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | constant | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | two_level | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | two_level | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | two_level | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | two_level | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | two_level | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | ramp | uint8 | `{"saturated_pixels": 0.0}` | FIDELITY FAILURE | 0.96 | 231 |
| Contrast stretch | ramp | uint8 | `{"saturated_pixels": 0.35}` | FIDELITY FAILURE | 0.96 | 231 |
| Contrast stretch | ramp | uint8 | `{"saturated_pixels": 5.0}` | FIDELITY FAILURE | 0.96 | 231 |
| Equalize weighted | ramp | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | ramp | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | sparse | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | sparse | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint8 | `{"saturated_pixels": 0.0}` | FIDELITY FAILURE | 1.0 | 153 |
| Contrast stretch | narrow | uint8 | `{"saturated_pixels": 0.35}` | FIDELITY FAILURE | 1.0 | 153 |
| Contrast stretch | narrow | uint8 | `{"saturated_pixels": 5.0}` | FIDELITY FAILURE | 1.0 | 153 |
| Equalize weighted | narrow | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | narrow | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | full | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | full | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | full | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | full | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | full | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | impulse | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | impulse | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | impulse | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | impulse | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | impulse | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | asymmetric_tail | uint8 | `{"saturated_pixels": 0.0}` | FIDELITY FAILURE | 0.96 | 10 |
| Contrast stretch | asymmetric_tail | uint8 | `{"saturated_pixels": 0.35}` | FIDELITY FAILURE | 0.96 | 10 |
| Contrast stretch | asymmetric_tail | uint8 | `{"saturated_pixels": 5.0}` | FIDELITY FAILURE | 0.96 | 10 |
| Equalize weighted | asymmetric_tail | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | asymmetric_tail | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Hybrid Median 3x3 | median_grid | uint8 | `{"kernel_size": 3}` | FIDELITY FAILURE | 0.56 | 3 |
| Hybrid Median 5x5 | median_grid | uint8 | `{"kernel_size": 5}` | FIDELITY FAILURE | 0.44 | 3 |
| Hybrid Median 7x7 | median_grid | uint8 | `{"kernel_size": 7}` | FIDELITY FAILURE | 0.4 | 5 |
| Circular Median | median_grid | uint8 | `{"radius": 1.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 2.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 3.0}` | PARITY CONFIRMED | 0.0 | 0 |
| CLAHE Flat / precise | clahe_128x128_full_bin_ramp | uint8 | `{"blocksize": 127, "composite": true, "histogram_bins": 256, "maximum_slope": 0.6}` | REFERENCE NOT RESOLVED | n/a | n/a |
| CLAHE FastFlat / fast | clahe_128x128_full_bin_ramp | uint8 | `{"blocksize": 127, "composite": true, "histogram_bins": 256, "maximum_slope": 0.6}` | REFERENCE NOT RESOLVED | n/a | n/a |
| Contrast stretch | constant | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | constant | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | constant | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | constant | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | constant | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | two_level | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | two_level | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | two_level | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | two_level | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | two_level | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | ramp | uint16 | `{"saturated_pixels": 0.0}` | FIDELITY FAILURE | 0.96 | 59367 |
| Contrast stretch | ramp | uint16 | `{"saturated_pixels": 0.35}` | FIDELITY FAILURE | 0.96 | 59367 |
| Contrast stretch | ramp | uint16 | `{"saturated_pixels": 5.0}` | FIDELITY FAILURE | 0.96 | 59367 |
| Equalize weighted | ramp | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | ramp | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | sparse | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | sparse | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint16 | `{"saturated_pixels": 0.0}` | FIDELITY FAILURE | 1.0 | 39321 |
| Contrast stretch | narrow | uint16 | `{"saturated_pixels": 0.35}` | FIDELITY FAILURE | 1.0 | 39321 |
| Contrast stretch | narrow | uint16 | `{"saturated_pixels": 5.0}` | FIDELITY FAILURE | 1.0 | 39321 |
| Equalize weighted | narrow | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | narrow | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | full | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | full | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | full | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | full | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | full | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | impulse | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | impulse | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | impulse | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | impulse | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | impulse | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | asymmetric_tail | uint16 | `{"saturated_pixels": 0.0}` | FIDELITY FAILURE | 0.96 | 2570 |
| Contrast stretch | asymmetric_tail | uint16 | `{"saturated_pixels": 0.35}` | FIDELITY FAILURE | 0.96 | 2570 |
| Contrast stretch | asymmetric_tail | uint16 | `{"saturated_pixels": 5.0}` | FIDELITY FAILURE | 0.96 | 2570 |
| Equalize weighted | asymmetric_tail | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | asymmetric_tail | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Hybrid Median 3x3 | median_grid | uint16 | `{"kernel_size": 3}` | FIDELITY FAILURE | 0.56 | 771 |
| Hybrid Median 5x5 | median_grid | uint16 | `{"kernel_size": 5}` | FIDELITY FAILURE | 0.44 | 771 |
| Hybrid Median 7x7 | median_grid | uint16 | `{"kernel_size": 7}` | FIDELITY FAILURE | 0.4 | 1285 |
| Circular Median | median_grid | uint16 | `{"radius": 1.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 2.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 3.0}` | PARITY CONFIRMED | 0.0 | 0 |
| CLAHE Flat / precise | clahe_128x128_full_bin_ramp | uint16 | `{"blocksize": 127, "composite": true, "histogram_bins": 256, "maximum_slope": 0.6}` | REFERENCE NOT RESOLVED | n/a | n/a |
| CLAHE FastFlat / fast | clahe_128x128_full_bin_ramp | uint16 | `{"blocksize": 127, "composite": true, "histogram_bins": 256, "maximum_slope": 0.6}` | REFERENCE NOT RESOLVED | n/a | n/a |

## Existing test gaps

`tests/test_imagej_migration.py` locks accepted MPIPS outputs but does not compare them with executable ImageJ/Fiji references. Its expected arrays and hashes were not modified.

## Representative deviations

The JSON records mismatch count, mismatch fraction, maximum absolute difference, output/reference SHA256, and the first differing coordinate/value for every case. A mismatch is diagnostic evidence; no production behavior was changed.

## Later remediation ordering

Use the measured operation families in this order: circular/Hybrid median edge semantics, ContrastEnhancer rounding/statistics, CLAHE Flat versus FastFlat parameter mapping, then any secondary RGB/composite work. This is diagnostic ordering only; remediation is out of scope for I-4A.

## Licensing and unresolved constraints

ImageJ core is public domain; the Fiji CLAHE implementation is GPL-2-era source and the Hybrid Median source carries its own non-commercial restriction. No third-party source or JAR is committed. Temporal median has an upstream plugin page but is not production-reachable, so no executable comparison was required.
