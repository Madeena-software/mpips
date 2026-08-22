# MPIPS CLAHE parameter-contract resolution

Status: evidence-only execution; terminal outcome is Review Required after the authorized evidence commit and push.

Governing task: .agents/tasks/clahe-parameter-contract-resolution.md at 396071888842b99081a0f89a9f56a1452d99235b

Accepted implementation baseline: 979de4ee9cd24731d5adf74aa19dc412f1dedc37

This artifact records I-4C0 evidence. It does not select a product or image-quality contract, change the current default, remediate Flat/FastFlat, or claim Fiji parity. The immutable evidence commit is reported in the Executor handoff because embedding a commit hash in its own commit is self-referential.

## Executive result

The earliest visible 0.6 is an inherited MPIPS default. It was introduced in legacy module/config material and copied through later ownership moves; the inspected commit messages, source history, configuration artifacts, tests, and prior evidence do not recover an approved human or algorithmic rationale. The required classification is:

    INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED

Execution-domain result for the pinned Fiji implementation on the required geometry:

- Flat: first observed all-window-safe matrix value 1.02722168; values below it fail in this fixture with Java ArithmeticException: / by zero.
- FastFlat: first observed fixed-block-safe matrix value 1.00394; values below it fail in this fixture with Java ArithmeticException: / by zero.
- These are execution-domain boundaries, not quality recommendations or approved defaults.
- The current MPIPS Python implementation returned numeric output for every matrix case, but it is not numerically equivalent to either Fiji algorithm on this fixture.

Default-change HOLD: I-4C0 MUST NOT change clahe_max_slope=0.6. A later change requires explicit semantic selection, documented supported geometry/bins/masks/dtypes, real-radiograph comparison, regression impact analysis, config/schema/migration approval, and a new validated implementation task.

## Verification ledger

Observed before evidence creation:

- branch: refactor/package-boundaries
- pre-evidence HEAD: 396071888842b99081a0f89a9f56a1452d99235b
- origin/refactor/package-boundaries: 396071888842b99081a0f89a9f56a1452d99235b
- accepted baseline is an ancestor of HEAD
- protected converter SHA256: a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0
- raw matrix artifact SHA256: 77f9a50c7092ed61e2e359aed65ea17ba4e53b30e7ff0bfef2760dee5373052a

Only the two authorized evidence artifacts are created by I-4C0. No production, configuration, schema, test, converter, dependency, runtime, or reference-tooling file is changed. No CI result is claimed; these are local observations.

## Git provenance and authority

The active ancestry contains the following visible lineage:

| Revision | Observed ownership or authority event |
|---|---|
| 3169a725752d0007cc97dbb58512feffd13eb864 | Parent of the first-known legacy module commits; no visible 0.6 in the inspected parent material. |
| 2de4a4ed13a5f7bf07628a8be63b67d11b455465 | 2026-07-07, make module. First visible 0.6 in the active ancestry, in imager-pipeline/complete_pipeline.py and imager-pipeline/archive/complete_pipeline_coba1.py. The commit message does not explain the value. |
| 6a1f48b9d3e33fbfa178b9bd09154004aa09c446 | Sibling commit from the same parent, same date/message, independently containing the same first-known legacy 0.6 material; it is not the active ancestry tip but confirms the parallel introduction. |
| 15dcb1194b18b8ca6fbe139a25f887dff6df385e | 2026-07-14 migration from research/imager-pipeline into artifacts/imager-pipeline and mpips/engine/imager_pipeline; 0.6 is preserved in the moved config and workflow model. |
| aad1aa9e553222ca1935e0ab62adcbae674d110d | 2026-08-13 config consolidation; introduces the engine config, schema/default artifacts, and characterization/consolidation tests with the same value. |
| ceac045cbe05c75c93ee3e1ae148cbe654da645d | 2026-08-13 canonical pipeline semantics made authoritative; 0.6 remains unchanged. The sibling 6949578c0d9a154e467c91fdaedb955c362c1046 carries the same change on the parallel line. |
| ad6fa7154067ee73290b306aa84992a42e10960f | 2026-08-19 config ownership moved from mpips/engine/imager_pipeline/config.py to mpips/pipelines/config.py; 0.6 remains the active default. |
| 17e1cdddc43a4a573c05eaab0b7a88ee92e0f43b | 2026-08-19 image-processing ownership moved from mpips/engine/imager_pipeline/imagej_replicator.py to mpips/processing/imagej.py; the current call surface remains behaviorally unchanged for this task. |

The current config declares use_clahe=true, blocksize=127, displayed histogram_bins=256, max_slope=0.6, fast=false, and composite=true in mpips/pipelines/config.py:109-115 and repeats those constructor defaults at :150-155. JSON fallback retains 0.6 at :502-507; environment mapping exposes CLAHE_MAX_SLOPE at :546-551; validation only requires max_slope > 0 at :287-290. These facts establish persistence and reachability, not rationale.

History/design classification:

| Contract item | Classification |
|---|---|
| 0.6 | INHERITED MPIPS DEFAULT — RATIONALE NOT RECOVERED |
| 127 / 256 / precise / composite | Explicitly persisted MPIPS defaults; no separate approved rationale recovered in the inspected history. |
| Old docstring mentions of 1.5 | Observed descriptive text, not accepted authority and not used to infer rationale. |

## Pinned provenance

Reference environment retained at /tmp/mpips-imagej-reference-LyDbYJ:

- Eclipse Temurin 17.0.19+10 HotSpot, Linux x86_64; archive SHA256 d8afc263758141a66e0e3aafc321e783f7016696f4eaea067d340a269037d331.
- ImageJ core v1.54p, ij-1.54p.jar; SHA256 2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20.
- Fiji CLAHE source: axtimwalde/mpicbg at 0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0.
- Observed runtime: openjdk 17.0.19 (Temurin-17.0.19+10); javac 17.0.19.
- Tracked harness: scripts/imagej_reference/ReferenceHarness.java; SHA256 4dd097ff92002f6d3d6a52ef6d2231e31aa3b32610c8af9e0c9e300559f2bcd5.
- Harness dependency compiled from Hybrid_2D_Median_Filter.java; SHA256 494cc92747ba8e01e9ad19f16d735ffe8faf0b65eba00f02fda691bc5529af03.

Pinned Fiji source hashes:

| Source | SHA256 |
|---|---|
| mpicbg/ij/clahe/Apply.java | 2dbbecd5dc2355004b10998f3a32dc40b037f226d98001c2aa8a34daf27c8c7a |
| mpicbg/ij/clahe/ByteApply.java | adb4bd88aa68af148374b6fd3e97f8bdc3fdaa27421496fe67149c36d5b37428 |
| mpicbg/ij/clahe/FastByteApply.java | 3744374e2846305cf28579382467df0ceedaa2132cf0345701832a566a250abc |
| mpicbg/ij/clahe/FastFlat.java | 09fa2048f80d258a2ce02b8940373e2a9e9b8176e5b86e0a4c5ae6710114b3fd |
| mpicbg/ij/clahe/Flat.java | 112ba574034acb2c740dfcc5365fb9489305d62e9527df71665cac8971dedee2 |
| mpicbg/ij/clahe/FloatApply.java | 7d66d1c71ab282aa00a7645545924a568f08ec222ca6306c7f27e7ce8891a891 |
| mpicbg/ij/clahe/RGBApply.java | e08de2b9054709e8926ae00a0098547019f7559287e82b5c285fc4559bbf561b |
| mpicbg/ij/clahe/ShortApply.java | c7394768b9d3821d8813b5c556edebf3cec5d1382d8c84af19ce0b6289f521e9 |
| mpicbg/ij/clahe/Util.java | 4dbe118c08eaa36a5f87c78930169383a602a84f25ca7b975284cb089bdd1689 |
| mpicbg/util/Util.java | c1310ea802c965f6c69ca520455d6fef5ab69df71f3791d13531b59b6274d26c |

No third-party source, JAR, JDK, or compiled class is committed.

## Fiji implementation contract

### Shared rounding and clipping

The pinned mpicbg.util.Util.roundPos(float) is (int)(a + 0.5f), so positive values use half-up rounding followed by integer truncation. The double overload uses the analogous +0.5 rule.

Util.clipHistogram has histogram length N, first clips every entry greater than or equal to L to L, accumulates excess, and repeatedly redistributes integer excess using:

    freeBins = N - fullBins
    proRataExcess = excess / freeBins
    remainder = excess % freeBins

Filled bins are skipped. A redistribution that fills every bin while excess remains reaches freeBins=0 and throws Java ArithmeticException: / by zero at Util.java:97. createTransfer and transferValue then normalize the cumulative clipped histogram using (cdf - cdfMin) / (cdfMax - cdfMin).

### Flat: local sliding windows

Displayed histogram_bins=256 maps to internal bins=255. Flat allocates histogram length 255, maps each byte source value q to roundPos(q * (255 - 1) / 255.0f), and maps the normalized transfer back with roundPos(t * 255.0f). With no mask, the per-pixel limit is:

    L_F(n, s) = roundPos(s * n / 255.0f) = (int)(s * n / 255.0f + 0.5f)

where n is the actual local window pixel count. Flat therefore has capacity 255 * L_F and an execution-safe condition 255 * L_F >= n for a window.

For a 128 by 128 image and radius 63:

| Location | h | w | n |
|---|---:|---:|---:|
| corner | 64 | 64 | 4096 |
| non-corner edge | 64 | 127 | 8128 |
| interior | 127 | 127 | 16129 |

More generally h and w independently range from 64 through 127 at the edge quadrants, so n=(64+i)(64+j) for i,j in 0..63 where applicable. The all-position boundary is controlled by the maximum threshold:

    s_F(n) = 255 * (ceil(n / 255) - 0.5) / n

For this geometry the maximum is at the 4096-pixel corner: 8415 / 8192 = 1.0272216796875. The 16129-pixel interior threshold is 255 / 254 = 1.0039370078740157, and the 8128-pixel edge threshold is approximately 0.9882504921259843. The formula is subject to the documented Java float evaluation; the executable first all-window-safe matrix value is 1.02722168.

Flat is a true per-pixel sliding-window algorithm. It is not equivalent to FastFlat, even when both receive the same displayed parameters.

### FastFlat: fixed block histograms and interpolation

FastFlat allocates histograms of length bins+1=256, quantizes the byte source with roundPos(q / 255.0f * 255), and uses fixed block size B=2r+1=127. For the 128 by 128 fixture, its block-center windows are 127 by 127, so n=B squared=16129 for the limit:

    L_Fast(s) = roundPos(s * B squared / 255.0f) = (int)(s * 16129 / 255.0f + 0.5f)

The histogram capacity is 256 * L_Fast. Its execution-safe threshold is:

    s_Fast = 255 * (ceil(16129 / 256) - 0.5) / 16129
           = 255 * 63.5 / 16129
           = 1.0039370078740157

The executable first safe matrix value is 1.00394; 1.0039 is still an error. FastFlat builds transfer LUTs at adjacent centers and bilinearly interpolates the LUT values horizontally and vertically before roundPos(t * 255.0f). Its source explicitly derives center arrays and interpolation weights; it is a distinct algorithm, not a Flat optimization.

## Executed slope matrix

Common matrix parameters for every case:

- Fixture: clahe_runtime_mod64, defined as base = arange(128*128, dtype=uint32).reshape(128,128) % 64; uint8=base.astype(uint8); uint16=(base*257).astype(uint16).
- Fixture input SHA256: uint8 218ce717d7c6040fa9d31c9cf7c5f8d970d49faac646004bc6920544d869cc7b; uint16 eccb2e706b615b7eb1a7a97ec92e14b4492973a4843667da02a6e36ab50a37f5.
- Shape 128 by 128; block radius 63; displayed bins 256; internal bins 255; mask None; composite true.
- Slopes: 0.6, 1.0, 1.003, 1.0039, 1.00394, 1.00395, 1.004, 1.027, 1.0272, 1.02722, 1.02722168, 1.02723, 1.028, 1.03, 1.5, 2.0, 3.0.
- Every matrix case records algorithm, dtype, slope, geometry, mask, exact reference status/error or output SHA256, and MPIPS status/output SHA256 in the companion JSON.
- Table cells show pinned reference results; successful cells show the complete output SHA256.

| slope | Flat / uint8 | Flat / uint16 | FastFlat / uint8 | FastFlat / uint16 |
|---:|---|---|---|---|
| 0.6 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 |
| 1.0 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 |
| 1.003 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 |
| 1.0039 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 |
| 1.00394 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | OK; sha256 4daa15d8e97c1007a3c9c9c1ba1f3f1d16d65e4253b5e9dbb0bf330b19039b42 | OK; sha256 9de6ffe61d49e3b9d9242fb58f69ca9deede359fb5cb7c9c707f0de53c13c10d |
| 1.00395 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | OK; sha256 4daa15d8e97c1007a3c9c9c1ba1f3f1d16d65e4253b5e9dbb0bf330b19039b42 | OK; sha256 9de6ffe61d49e3b9d9242fb58f69ca9deede359fb5cb7c9c707f0de53c13c10d |
| 1.004 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | OK; sha256 4daa15d8e97c1007a3c9c9c1ba1f3f1d16d65e4253b5e9dbb0bf330b19039b42 | OK; sha256 9de6ffe61d49e3b9d9242fb58f69ca9deede359fb5cb7c9c707f0de53c13c10d |
| 1.027 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.0272 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.02722 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | ERROR; ArithmeticException / by zero; Util.clipHistogram:97 | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.02722168 | OK; sha256 ebc87b6401070f5609d63b6c4939255017243d2eecf48f7e25028345b835f557 | OK; sha256 36cd0a8409aa109556d252426b8f8b90114c6534c47b5a569b6eb732c778a80d | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.02723 | OK; sha256 0106c7b7d8bc0b0eb8215a07138418f24b8e962bd070979df364867950d2e100 | OK; sha256 36cd0a8409aa109556d252426b8f8b90114c6534c47b5a569b6eb732c778a80d | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.028 | OK; sha256 015d60099c8325133cb9a7f28039a2b3ed74261b8d68d34dc2aab6796369497b | OK; sha256 820a5d302483e1a4dce920f8adb106491075bd753180073234018cc5ea7a474d | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.03 | OK; sha256 f5ac457f997c5d6602e4db49cae079827898d1604cdfafc75c4b0743cc47ee7b | OK; sha256 0393069f482684af4d61ba39b7d40e30fa0a27efb0b04eabaecb274bd835248f | OK; sha256 f532b7e3e33f3ca6a7e2ef291c584ac6a7532173ca4b157213f18b4b79770abf | OK; sha256 0abec5e392b98a84364149dd764b42f8f487cffdf8e8f758d41005c3fffc8357 |
| 1.5 | OK; sha256 93008033d627f115a8a556dc600ee205d730db035dc4ac3d90374dd3e715e7bb | OK; sha256 4f7687f4cabeefd98b08547000edb9034416e68328778982a0613b6da3dc5971 | OK; sha256 27bf5c54f94dbc9f0c466c971e257cb65f612281719bc574041e0c5aac1dca4f | OK; sha256 05b8e8380d6578857863d6b1e417dc08f672cb82074e70e1e47275bf55629a79 |
| 2.0 | OK; sha256 fd2c4732d510dec8b656a9574fbbc40c04b98d1ac1628ce7e1dcd20e4e7155da | OK; sha256 4d5143fb2b079a3ade08d08993bae7676f15b98b50405e5207df31929c5be6f7 | OK; sha256 d58f32a93449a2acefd60682b3a3f50c33b5ff97008a3c49e3b0f9f12acd72cf | OK; sha256 b4b7666cc22ea4253086182884172c0c755574e92f17b82b3802ce2275594278 |
| 3.0 | OK; sha256 f1906810ad7ec8931b0383f3a59c895e3aadb2536cfbbe69a60916459d2dfeff | OK; sha256 d12b4084a8eb18982fc2b2a42858f95eec8cef9be1442d5e044a972391b543ac | OK; sha256 dcfa0b3ed836900ffa269a8c47c4217ad5765135b232d2d773a19b55f1d697a2 | OK; sha256 80daeb1c36dd95f475f85797e8fd2ae1ca829a0387f75bd9c619b24d152cfd74 |

All reference failures in the table are execution failures, not quality judgments. The exact observed stderr was:

Flat failures:

    Exception in thread "main" java.lang.ArithmeticException: / by zero
        at mpicbg.ij.clahe.Util.clipHistogram(Util.java:97)
        at mpicbg.ij.clahe.Util.transferValue(Util.java:215)
        at mpicbg.ij.clahe.Flat$SlidingWindowHistogram.getNormalizedValue(Flat.java:165)
        at mpicbg.ij.clahe.Flat.run(Flat.java:454)
        at mpicbg.ij.clahe.Flat.run(Flat.java:376)
        at mpicbg.ij.clahe.Flat.run(Flat.java:222)
        at ReferenceHarness.main(ReferenceHarness.java:100)

FastFlat failures:

    Exception in thread "main" java.lang.ArithmeticException: / by zero
        at mpicbg.ij.clahe.Util.clipHistogram(Util.java:97)
        at mpicbg.ij.clahe.Util.createTransfer(Util.java:145)
        at mpicbg.ij.clahe.FastFlat.run(FastFlat.java:232)
        at mpicbg.ij.clahe.Flat.run(Flat.java:376)
        at mpicbg.ij.clahe.Flat.run(Flat.java:222)
        at mpicbg.ij.clahe.FastFlat.run(FastFlat.java:98)
        at ReferenceHarness.main(ReferenceHarness.java:101)

Observed reference classification:

- Flat uint8 and uint16: errors through 1.02722 inclusive; success from 1.02722168.
- FastFlat uint8 and uint16: errors through 1.0039 inclusive; success from 1.00394.
- The uint8 and uint16 classification matched for this fixture only. Their output hashes and numeric domains differ.

## Fiji uint8 and uint16 semantics

The pinned Flat/FastFlat code first creates a ByteProcessor source with ImageProcessor.convertToByte(true). For a ShortProcessor, the pinned ImageJ core path uses the current display/data range:

    min = (int)ip.getMin()
    max = (int)ip.getMax()
    scale = 256.0 / (max - min + 1)
    p = (pixel & 65535) - min
    p = max(0, p)
    out = (int)(p * scale + 0.5)
    out = min(255, out)

The default harness ShortProcessor uses its observed data range; explicit ImageJ display ranges would change the byte working representation. Flat/FastFlat then compute an 8-bit CLAHE transfer. ShortApply applies the byte transfer back to original unsigned short data:

    v = ipPixels[i] & 0xffff
    vSrc = srcPixels[i] & 0xff
    a = vSrc == 0 ? 1.0f : (dstPixels[i] & 0xff) / vSrc
    b = m * (a * (v - min) + min - v) + v
    output = clamp(roundPos(b), 0, 65535)

With mask=None, Apply constructs an all-255 mask, so m=1. This is not a native 65,536-bin CLAHE. The matching error classification in this fixture does not establish uint8/uint16 parity; the successful output hashes, ranges, and unique-value counts remain dtype-specific.

## Current MPIPS semantics

Current mpips/processing/imagej.py keeps the displayed-to-internal mapping in apply_clahe at :395-405: block_radius=(blocksize-1)//2 and bins=histogram_bins-1.

Precise path (fast=false):

- Computes clipped local windows with the same nominal radius geometry, but quantizes uint16 as floor(block / 65535 * bins) and uint8 as floor(block / 255 * bins), then uses a 256-slot histogram.
- Computes clip_limit=int(slope * n_pixels / (bins + 1)); a lower bound clamps values below 1 to 1.
- Clips only entries greater than the limit, redistributes excess as floating-point mass uniformly across all bins, distributes residuals, and builds the LUT with uint8 truncation. The 16-bit path scales the LUT result back to 65535.
- It therefore has no Java freeBins integer-division failure mode. In the executed matrix every precise case returned numeric output.

Fast path (fast=true):

- For 2D images, calls OpenCV createCLAHE(clipLimit=slope, tileGridSize=(max(1,width//127), max(1,height//127))) and applies it to the original dtype.
- Mask handling is post-preservation of unmasked pixels; composite 2D behavior does not create Fiji's multi-channel display semantics.
- It is a different implementation and output domain from both Fiji algorithms. Every executed fast matrix case returned numeric output.

The companion JSON records MPIPS status and output hashes for all 68 cases. At slope 0.6, the four MPIPS hashes are:

| Algorithm | dtype | MPIPS output SHA256 |
|---|---|---|
| Flat-equivalent call, fast=false | uint8 | 13c27e2398dc0ffca5232248589fcdd1ae8d7a4fa06de286289db3bbaec297f9 |
| Flat-equivalent call, fast=false | uint16 | 488637c5087899a587eb1caa8bf2937da8b64e2ff58bc43e8f3ec29d9f678369 |
| Fast-equivalent call, fast=true | uint8 | d727abf7121673f83afa5327829501e2a6ea1cb92cdf71fe5162e2deebd46c4b |
| Fast-equivalent call, fast=true | uint16 | 6945984521421e97cc35bd1fb3eacfe89b1e29ba1bbd8afc44358034e06bd38e |

These labels identify the MPIPS dispatch mode only; they do not assert Fiji parity.

## Production reachability and exact default path

Observed path:

    POST /radiographs/dicom
      -> mpips.conversion.service.run_isolated_dicom_conversion()
      -> development worker: python -m mpips.conversion.worker
         (production uses the authorized launcher socket to run the same staged worker)
      -> mpips.conversion.worker.execute_conversion_worker()
      -> process_radiography_arrays(..., config omitted)
      -> config = config or ImagerPipelineConfig()
      -> RadiographyPipeline(config).process(...)
      -> ImageJReplicator.apply_clahe(...)

Source anchors: route mpips/api/routes/v1/dicom.py:90-92 and :273-281; service mpips/conversion/service.py:232-238 and :439-452; worker mpips/conversion/worker.py:20 and :240-247; workflow mpips/workflows/imager_pipeline/pipeline.py:36-52; pipeline mpips/pipelines/radiography.py:23-33 and :122-133.

Production classification:

- PRODUCTION-REACHABLE: current MPIPS Python CLAHE through the DICOM radiography path.
- NOT PRODUCTION-REACHABLE: the Java/Fiji CLAHE runtime itself; it is only compiled/executed by the retained characterization harness.

Default production values and semantics:

| Parameter | Observed default/path |
|---|---|
| input/output dtype | worker loads/processes radiography as uint16 and writes uint16 TIFF; RadiographyPipeline returns uint16 |
| use_clahe | true by default; pipeline bypasses CLAHE only when false or ImageJ is unavailable |
| blocksize / radius | 127 / (127-1)//2 = 63 |
| histogram bins | displayed 256 / MPIPS internal 255 |
| max slope | 0.6, unchanged by I-4C0 |
| fast | false, MPIPS precise path |
| composite | true in config; current production radiography is 2D single-channel, so dispatch is effectively single-channel |
| mask | None at the radiography CLAHE call |

Omitting config at the worker/workflow boundary therefore selects ImagerPipelineConfig() and the values above.

## Contract options preserved without choosing

Option A — Legacy MPIPS Contract:

- Keep 0.6 as MPIPS-specific.
- Stop claiming exact Fiji CLAHE parity for that behavior.
- Focus future work on MPIPS quality and consistency.

Option B — Fiji Flat Contract:

- Treat Flat as authoritative.
- Define a valid parameter domain.
- Independently implement observable Fiji behavior.
- Migrate only after real-radiograph quality validation.

Option C — Fiji FastFlat Contract:

- Treat FastFlat as a distinct authoritative algorithm.
- Do not conflate it with Flat.
- Require separate implementation/parity work.

No option is selected by I-4C0. Do not silently mix contracts depending on slope.

## Recommended next experiment

After review, plan a separate real-radiograph ablation comparing current MPIPS precise at 0.6, informative higher current-MPIPS values, and Fiji-Flat-compatible candidate semantics around 1.03, 1.5, 2.0, and 3.0. This task did not execute the ablation and makes no image-quality recommendation.

## Reproduction notes

The following are the exact retained-environment commands used for the reference setup, with the run-specific directories:

    run_dir=/tmp/mpips-imagej-reference-LyDbYJ/i4c0-run-G11z0p
    jdk=/tmp/mpips-imagej-reference-LyDbYJ/jdk/jdk-17.0.19+10/bin
    ijjar=/tmp/mpips-imagej-reference-LyDbYJ/imagej/ij-1.54p.jar
    source_root=/tmp/mpips-imagej-reference-LyDbYJ/imagej/mpicbg/mpicbg/src/main/java
    classes=$run_dir/classes
    harness=$run_dir/harness

    "$jdk/javac" -cp "$ijjar" -d "$classes" "$source_root/mpicbg/ij/clahe/Apply.java" "$source_root/mpicbg/ij/clahe/ByteApply.java" "$source_root/mpicbg/ij/clahe/FastByteApply.java" "$source_root/mpicbg/ij/clahe/FastFlat.java" "$source_root/mpicbg/ij/clahe/Flat.java" "$source_root/mpicbg/ij/clahe/FloatApply.java" "$source_root/mpicbg/ij/clahe/RGBApply.java" "$source_root/mpicbg/ij/clahe/ShortApply.java" "$source_root/mpicbg/ij/clahe/Util.java" "$source_root/mpicbg/util/Util.java"
    "$jdk/javac" -cp "$ijjar:$classes" -d "$classes" /tmp/mpips-imagej-reference-LyDbYJ/imagej/Hybrid_2D_Median_Filter.java
    "$jdk/javac" -cp "$ijjar:$classes" -d "$harness" scripts/imagej_reference/ReferenceHarness.java

For each matrix row, the Java invocation was:

    "$jdk/java" -Djava.awt.headless=true -cp "$ijjar:$classes:$harness" ReferenceHarness clahe_flat uint8 128 128 63 255 0.6
    "$jdk/java" -Djava.awt.headless=true -cp "$ijjar:$classes:$harness" ReferenceHarness clahe_fast uint8 128 128 63 255 0.6

The algorithm token was clahe_flat or clahe_fast, the dtype token was uint8 or uint16, and the final slope was replaced by each listed value. The executed matrix raw JSON was retained outside the repository and its SHA256 is recorded above.

The MPIPS call used for each corresponding case was:

    ImageJReplicator.apply_clahe(image, blocksize=127, histogram_bins=256, max_slope=slope, mask=None, fast=(algorithm == "FastFlat"), composite=True)

The fixture and output hashing used SHA256 over the contiguous native-dtype array bytes. These are local deterministic results, not CI evidence.

## Limitations and stop condition

- The fixture is synthetic and only establishes execution behavior, not diagnostic quality.
- The mathematical boundaries are for the stated geometry, bins, mask, dtype path, and pinned source; they are not universal defaults.
- Fiji Java/Fiji runtime is not a production dependency.
- No real-radiograph ablation was executed.
- No source/config/test/schema/dependency/runtime/converter change was needed or authorized.
- The next action after this evidence commit is review; any remediation, default change, parity implementation, or quality selection returns to planning.
