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
    "source_retrieval": "https://github.com/imagej/ImageJ/tree/v1.54p",
    "source_tag": "v1.54p",
    "version": "1.54p"
  },
  "repository": {
    "adapter_build_command": "javac -cp <IMAGEJ_JAR>:<REFERENCE_CLASSES> -d <HARNESS_CLASSES> scripts/imagej_reference/ReferenceHarness.java",
    "adapter_sha256": "86189871e94cc0d34f09976a8f61c1672fe05cc94c3226ecb51c137926d0ff56",
    "adapter_source": "scripts/imagej_reference/ReferenceHarness.java",
    "external_build_commands": [
      "javac -cp <IMAGEJ_JAR> -d <REFERENCE_CLASSES> <CLAHE_SOURCES> <MPICBG_UTIL_SOURCE>",
      "javac -cp <IMAGEJ_JAR>:<REFERENCE_CLASSES> -d <REFERENCE_CLASSES> <HYBRID_SOURCE>"
    ],
    "reference_classpath_structure": "<IMAGEJ_JAR>:<REFERENCE_CLASSES>:<HARNESS_CLASSES>"
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
    "official_checksum_url": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.19%2B10/OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz.sha256.txt",
    "official_download_url": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.19%2B10/OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz",
    "persistent_environment_change": false,
    "platform": "Linux x86_64",
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

Stretch and equalization use `constant`, `two_level`, `ramp`, `sparse`, `narrow`, `full`, `impulse`, and `asymmetric_tail` for both uint8 and uint16. Median fixtures are `median_grid` and `hybrid_9x9`; CLAHE fixtures are `clahe_runtime` and `clahe_small`. The CLAHE fixtures are deterministic modulo ramps so the mapped-bin implementation has non-full bins. Circular radii tested are 0.5, 1.0, 1.5, 1.74, 1.75, 2.0, 2.5, 2.84, 2.85, and 3.0, covering special-radius boundary groups.

## Parameter mappings

MPIPS maps displayed `histogram_bins=256` to Fiji internal `bins=255`; `blocksize=127` maps to `block_radius=63`. Exact integer array equality is used. Fiji Flat/FastFlat raise `ArithmeticException: / by zero` at the runtime slope/data case, while smaller mapped-bin fixtures execute; the runtime exception and MPIPS numeric output are classified as FIDELITY FAILURE.

## Final classification table

| Operation | Final classification |
|---|---|
| Contrast stretch uint8 | PARITY CONFIRMED |
| Contrast stretch uint16 | PARITY CONFIRMED |
| Equalize weighted uint8 | PARITY CONFIRMED |
| Equalize weighted uint16 | PARITY CONFIRMED |
| Equalize classic uint8 | PARITY CONFIRMED |
| Equalize classic uint16 | PARITY CONFIRMED |
| CLAHE Flat / precise | FIDELITY FAILURE |
| CLAHE FastFlat / fast | FIDELITY FAILURE |
| Hybrid Median 3x3 | FIDELITY FAILURE |
| Hybrid Median 5x5 | FIDELITY FAILURE |
| Hybrid Median 7x7 | FIDELITY FAILURE |
| Circular Median | FIDELITY FAILURE |
| Temporal Median | NOT PRODUCTION-REACHABLE |

## Aggregate results

| Operation | Classification | Cases | Mismatches |
|---|---|---:|---:|
| CLAHE FastFlat / fast | FIDELITY FAILURE | 4 | 512; 2 reference errors |
| CLAHE Flat / precise | FIDELITY FAILURE | 4 | 336; 2 reference errors |
| Circular Median | FIDELITY FAILURE | 20 | 38 |
| Contrast stretch | PARITY CONFIRMED | 48 | 0 |
| Equalize classic | PARITY CONFIRMED | 16 | 0 |
| Equalize weighted | PARITY CONFIRMED | 16 | 0 |
| Hybrid Median 3x3 | FIDELITY FAILURE | 4 | 100 |
| Hybrid Median 5x5 | FIDELITY FAILURE | 4 | 92 |
| Hybrid Median 7x7 | FIDELITY FAILURE | 4 | 86 |
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
| Contrast stretch | ramp | uint8 | `{"reference_not_unchanged": true, "saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | ramp | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | ramp | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | ramp | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | ramp | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | sparse | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | sparse | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
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
| Contrast stretch | asymmetric_tail | uint8 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | asymmetric_tail | uint8 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | asymmetric_tail | uint8 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | asymmetric_tail | uint8 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | asymmetric_tail | uint8 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Hybrid Median 3x3 | median_grid | uint8 | `{"kernel_size": 3, "repetitions": 1}` | FIDELITY FAILURE | 0.56 | 3 |
| Hybrid Median 5x5 | median_grid | uint8 | `{"kernel_size": 5, "repetitions": 1}` | FIDELITY FAILURE | 0.44 | 3 |
| Hybrid Median 7x7 | median_grid | uint8 | `{"kernel_size": 7, "repetitions": 1}` | FIDELITY FAILURE | 0.4 | 5 |
| Hybrid Median 3x3 | hybrid_9x9 | uint8 | `{"kernel_size": 3, "repetitions": 1}` | FIDELITY FAILURE | 0.4444444444444444 | 71 |
| Hybrid Median 5x5 | hybrid_9x9 | uint8 | `{"kernel_size": 5, "repetitions": 2}` | FIDELITY FAILURE | 0.43209876543209874 | 82 |
| Hybrid Median 7x7 | hybrid_9x9 | uint8 | `{"kernel_size": 7, "repetitions": 1}` | FIDELITY FAILURE | 0.4074074074074074 | 82 |
| Circular Median | median_grid | uint8 | `{"radius": 0.5}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 1.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 1.5}` | FIDELITY FAILURE | 0.44 | 3 |
| Circular Median | median_grid | uint8 | `{"radius": 1.74}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 1.75}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 2.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 2.5}` | FIDELITY FAILURE | 0.32 | 2 |
| Circular Median | median_grid | uint8 | `{"radius": 2.84}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 2.85}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint8 | `{"radius": 3.0}` | PARITY CONFIRMED | 0.0 | 0 |
| CLAHE Flat / precise | clahe_runtime | uint8 | `{"block_radius": 63, "blocksize": 127, "composite": true, "histogram_bins": 256, "internal_bins": 255, "maximum_slope": 0.6}` | FIDELITY FAILURE | n/a | n/a |
| CLAHE FastFlat / fast | clahe_runtime | uint8 | `{"block_radius": 63, "blocksize": 127, "composite": true, "histogram_bins": 256, "internal_bins": 255, "maximum_slope": 0.6}` | FIDELITY FAILURE | n/a | n/a |
| CLAHE Flat / precise | clahe_small | uint8 | `{"block_radius": 2, "blocksize": 5, "composite": true, "histogram_bins": 16, "internal_bins": 15, "maximum_slope": 3.0}` | FIDELITY FAILURE | 0.375 | 64 |
| CLAHE FastFlat / fast | clahe_small | uint8 | `{"block_radius": 2, "blocksize": 5, "composite": true, "histogram_bins": 16, "internal_bins": 15, "maximum_slope": 3.0}` | FIDELITY FAILURE | 1.0 | 39 |
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
| Contrast stretch | ramp | uint16 | `{"reference_not_unchanged": true, "saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | ramp | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | ramp | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | ramp | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | ramp | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | sparse | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | sparse | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | sparse | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | narrow | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
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
| Contrast stretch | asymmetric_tail | uint16 | `{"saturated_pixels": 0.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | asymmetric_tail | uint16 | `{"saturated_pixels": 0.35}` | PARITY CONFIRMED | 0.0 | 0 |
| Contrast stretch | asymmetric_tail | uint16 | `{"saturated_pixels": 5.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize weighted | asymmetric_tail | uint16 | `{"classic": false}` | PARITY CONFIRMED | 0.0 | 0 |
| Equalize classic | asymmetric_tail | uint16 | `{"classic": true}` | PARITY CONFIRMED | 0.0 | 0 |
| Hybrid Median 3x3 | median_grid | uint16 | `{"kernel_size": 3, "repetitions": 1}` | FIDELITY FAILURE | 0.56 | 771 |
| Hybrid Median 5x5 | median_grid | uint16 | `{"kernel_size": 5, "repetitions": 1}` | FIDELITY FAILURE | 0.44 | 771 |
| Hybrid Median 7x7 | median_grid | uint16 | `{"kernel_size": 7, "repetitions": 1}` | FIDELITY FAILURE | 0.4 | 1285 |
| Hybrid Median 3x3 | hybrid_9x9 | uint16 | `{"kernel_size": 3, "repetitions": 1}` | FIDELITY FAILURE | 0.4444444444444444 | 18247 |
| Hybrid Median 5x5 | hybrid_9x9 | uint16 | `{"kernel_size": 5, "repetitions": 2}` | FIDELITY FAILURE | 0.43209876543209874 | 21074 |
| Hybrid Median 7x7 | hybrid_9x9 | uint16 | `{"kernel_size": 7, "repetitions": 1}` | FIDELITY FAILURE | 0.4074074074074074 | 21074 |
| Circular Median | median_grid | uint16 | `{"radius": 0.5}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 1.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 1.5}` | FIDELITY FAILURE | 0.44 | 771 |
| Circular Median | median_grid | uint16 | `{"radius": 1.74}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 1.75}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 2.0}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 2.5}` | FIDELITY FAILURE | 0.32 | 514 |
| Circular Median | median_grid | uint16 | `{"radius": 2.84}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 2.85}` | PARITY CONFIRMED | 0.0 | 0 |
| Circular Median | median_grid | uint16 | `{"radius": 3.0}` | PARITY CONFIRMED | 0.0 | 0 |
| CLAHE Flat / precise | clahe_runtime | uint16 | `{"block_radius": 63, "blocksize": 127, "composite": true, "histogram_bins": 256, "internal_bins": 255, "maximum_slope": 0.6}` | FIDELITY FAILURE | n/a | n/a |
| CLAHE FastFlat / fast | clahe_runtime | uint16 | `{"block_radius": 63, "blocksize": 127, "composite": true, "histogram_bins": 256, "internal_bins": 255, "maximum_slope": 0.6}` | FIDELITY FAILURE | n/a | n/a |
| CLAHE Flat / precise | clahe_small | uint16 | `{"block_radius": 2, "blocksize": 5, "composite": true, "histogram_bins": 16, "internal_bins": 15, "maximum_slope": 3.0}` | FIDELITY FAILURE | 0.9375 | 3855 |
| CLAHE FastFlat / fast | clahe_small | uint16 | `{"block_radius": 2, "blocksize": 5, "composite": true, "histogram_bins": 16, "internal_bins": 15, "maximum_slope": 3.0}` | FIDELITY FAILURE | 1.0 | 9388 |

## Boundary and rounding findings

ContrastEnhancer normalized stretch and weighted/classic equalization show exact parity for all tested uint8/uint16 fixtures and parameters. No current evidence justifies ContrastEnhancer fidelity remediation.

Circular Median diverges for the tested special-radius cases 1.5 and 2.5, while the tested radii 0.5, 1.0, 1.74, 1.75, 2.0, 2.84, 2.85, and 3.0 remain exact. These observations are limited to pinned ImageJ 1.54p RankFilters circular-radius semantics; the characterization does not fix them.

Hybrid Median deviations occur in both boundary and interior pixels: across the uint8/uint16 cases, the 3×3 family has 38 edge and 62 interior mismatches, 5×5 has 44 edge and 48 interior mismatches, and 7×7 has 38 edge and 48 interior mismatches. Repeated-pass behavior is represented by the `hybrid_9x9` 5×5 case with `repetitions=2`. No causal claim is made beyond these region counts.

Smaller correctly mapped CLAHE cases execute and numerically diverge. The runtime `maximum_slope=0.6` cases produce authoritative Fiji `ArithmeticException: / by zero` while MPIPS returns numeric output. The pinned source identity is resolved, so these are FIDELITY FAILURE results, not REFERENCE NOT RESOLVED.

## Existing test gaps

`tests/test_imagej_migration.py` locks accepted MPIPS outputs but does not compare them with executable ImageJ/Fiji references. Its expected arrays and hashes were not modified.

## Representative deviations

The JSON records mismatch count, mismatch fraction, maximum absolute difference, output/reference SHA256, and the first differing coordinate/value for every case. A mismatch is diagnostic evidence; no production behavior was changed.

## Later remediation ordering

I-4B ContrastEnhancer fidelity remediation: NOT CURRENTLY REQUIRED BY I-4A EVIDENCE. Do not create I-4B. The remaining FIDELITY FAILURE families are CLAHE, Hybrid Median, and Circular Median. The active production median path is `hybrid_imagej` with default radius 2 (`mpips/pipelines/config.py` and `mpips/processing/filtering.py`); order later work as Hybrid Median first, CLAHE second, and Circular Median third by production reachability and measured evidence. Circular Median is an exposed alternative, not the active default path. This is diagnostic ordering only; remediation is out of scope for I-4A.

## Licensing and unresolved constraints

ImageJ core is public domain; the Fiji CLAHE implementation is GPL-2-era source and the Hybrid Median source carries its own non-commercial restriction. No third-party source or JAR is committed. Temporal median has an upstream plugin page but is not production-reachable, so no executable comparison was required.
