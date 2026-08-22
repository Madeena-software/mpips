# ImageJ/Fiji reference environment

This directory contains only the tracked adapter. Third-party Java sources,
JARs, compiled classes, and the JDK remain in the retained temporary workspace
`/tmp/mpips-imagej-reference-LyDbYJ` and are not repository dependencies.

## Pinned inputs

### Eclipse Temurin

- Vendor/runtime: Eclipse Temurin 17.0.19+10 HotSpot, Linux x86_64
- Release tag: `jdk-17.0.19+10`
- Archive: `OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz`
- Official archive: <https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.19%2B10/OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz>
- Official checksum: <https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.19%2B10/OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz.sha256.txt>
- SHA256: `d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331`
- Retained archive: `/tmp/mpips-imagej-reference-LyDbYJ/downloads/OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz`

### ImageJ core

- Project/tag: `imagej/ImageJ`, `v1.54p`
- Artifact: `ij-1.54p.jar`
- URL: <https://repo1.maven.org/maven2/net/imagej/ij/1.54p/ij-1.54p.jar>
- SHA256: `2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20`
- Used classes: `ij.plugin.ContrastEnhancer` and
  `ij.plugin.filter.RankFilters`.
- Retained artifact: `/tmp/mpips-imagej-reference-LyDbYJ/imagej/ij-1.54p.jar`

### Fiji CLAHE

- Project/commit: `axtimwalde/mpicbg@0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0`
- Repository: <https://github.com/axtimwalde/mpicbg>
- Source root in the pinned checkout:
  `mpicbg/mpicbg/src/main/java/`
- Sources compiled, with SHA256:

| Source path | SHA256 |
|---|---|
| `mpicbg/ij/clahe/Apply.java` | `2dbbecd5dc2355004b10998f3a32dc40b037f226d98001c2aa8a34daf27c8c7a` |
| `mpicbg/ij/clahe/ByteApply.java` | `adb4bd88aa68af148374b6fd3e97f8bdc3fdaa27421496fe67149c36d5b37428` |
| `mpicbg/ij/clahe/FastByteApply.java` | `3744374e2846305cf28579382467df0ceedaa2132cf0345701832a566a250abc` |
| `mpicbg/ij/clahe/FastFlat.java` | `09fa2048f80d258a2ce02b8940373e2a9e9b8176e5b86e0a4c5ae6710114b3fd` |
| `mpicbg/ij/clahe/Flat.java` | `112ba574034acb2c740dfcc5365fb9489305d62e9527df71665cac8971dedee2` |
| `mpicbg/ij/clahe/FloatApply.java` | `7d66d1c71ab282aa00a7645545924a568f08ec222ca6306c7f27e7ce8891a891` |
| `mpicbg/ij/clahe/RGBApply.java` | `e08de2b9054709e8926ae00a0098547019f7559287e82b5c285fc4559bbf561b` |
| `mpicbg/ij/clahe/ShortApply.java` | `c7394768b9d3821d8813b5c556edebf3cec5d1382d8c84af19ce0b6289f521e9` |
| `mpicbg/ij/clahe/Util.java` | `4dbe118c08eaa36a5f87c78930169383a602a84f25ca7b975284cb089bdd1689` |
| `mpicbg/util/Util.java` | `c1310ea802c965f6c69ca520455d6fef5ab69df71f3791d13531b59b6274d26c` |

The first nine sources are required by `Flat`/`FastFlat`; the final utility is
their external dependency. The compiled output directory is
`<REFERENCE_CLASSES>`.

### Hybrid Median

- Authoritative source: Christopher Philip Mauer,
  `Hybrid_2D_Median_Filter.java`
- URL: <https://wsr.imagej.net/ij/plugins/download/Hybrid_2D_Median_Filter.java>
- SHA256: `494cc92747ba8e01e9ad19f16d735ffe8faf0b65eba00f02fda691bc5529af03`
- Compiled output: `<REFERENCE_CLASSES>/Hybrid_2D_Median_Filter.class`

## Build

From a clean reconstruction directory, define `<IMAGEJ_JAR>` as the pinned
JAR, `<REFERENCE_CLASSES>` as its empty compiled-class output directory,
`<CLAHE_SOURCES>` as the nine `mpicbg/ij/clahe/*.java` paths above, and
`<MPICBG_UTIL_SOURCE>` as `mpicbg/util/Util.java`:

```sh
javac -cp <IMAGEJ_JAR> -d <REFERENCE_CLASSES> <CLAHE_SOURCES> <MPICBG_UTIL_SOURCE>
javac -cp <IMAGEJ_JAR>:<REFERENCE_CLASSES> -d <REFERENCE_CLASSES> <HYBRID_SOURCE>
javac -cp <IMAGEJ_JAR>:<REFERENCE_CLASSES> -d <HARNESS_CLASSES> scripts/imagej_reference/ReferenceHarness.java
```

The accepted run retained its original output directories as
`/tmp/mpips-imagej-reference-LyDbYJ/imagej/classes2` and
`/tmp/mpips-imagej-reference-LyDbYJ/harness-remediation`. The independent
reproduction used fresh output directories at
`/tmp/mpips-imagej-reference-LyDbYJ/repro-check-20260822/imagej/classes` and
`.../harness`; it did not reuse the original compiled classes.

`ReferenceHarness.java` is compiled from this repository revision. Its exact
source SHA256 is recorded below after the tracked adapter correction.

The Hybrid adapter accepts the MPIPS kernel size as its `hybrid` argument and
maps it to the plugin's internal selector as follows:

| MPIPS kernel | plugin selector | plugin `nsize` |
|---|---:|---:|
| 3x3 | 1 | 0 |
| 5x5 | 3 | 1 |
| 7x7 | 5 | 2 |

The pinned plugin source defines the choice order as `3x3`, `5x5`, `7x7`,
stores the selected choice index in `nsize`, and branches on `nsize == 0`,
`1`, and `2`. The adapter therefore sets the plugin's private `nsize` field
before invoking the private method; the method argument is set to the same
`nsize` value. This reflection is limited to invocation state and does not
implement or copy the filtering algorithm.

The corrected tracked adapter source SHA256 is
`4dd097ff92002f6d3d6a52ef6d2231e31aa3b32610c8af9e0c9e300559f2bcd5`.

## Execution

The reference classpath passed to the Python harness is exactly:

```text
<IMAGEJ_JAR>:<REFERENCE_CLASSES>:<HARNESS_CLASSES>
```

The JDK executable is the retained Temurin binary, for example
`/tmp/mpips-imagej-reference-LyDbYJ/jdk/jdk-17.0.19+10/bin/java`.

Representative complete command:

```sh
.venv/bin/python scripts/imagej_fidelity_characterization.py \
  --reference-java /tmp/mpips-imagej-reference-LyDbYJ/jdk/jdk-17.0.19+10/bin/java \
  --reference-classpath /tmp/mpips-imagej-reference-LyDbYJ/repro-check-20260822/external/ij-1.54p.jar:/tmp/mpips-imagej-reference-LyDbYJ/repro-check-20260822/imagej/classes:/tmp/mpips-imagej-reference-LyDbYJ/repro-check-20260822/harness \
  --runtime-root /tmp/mpips-imagej-reference-LyDbYJ \
  --jdk-archive OpenJDK17U-jdk_x64_linux_hotspot_17.0.19_10.tar.gz \
  --jdk-sha256 d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331 \
  --adapter-source scripts/imagej_reference/ReferenceHarness.java \
  --output-json .agents/evidence/imagej-fidelity-characterization.json \
  --output-md .agents/evidence/imagej-fidelity-characterization.md
```

The run emits 120 deterministic cases. The corrected independent run matched
the accepted run's case inventory, classifications, mismatch counts, and
authoritative runtime exceptions; only temporary filesystem paths are
normalized in machine-readable exception text.
