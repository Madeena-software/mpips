# MPIPS repository size reduction — Phase 1 evidence

Governing task: `.agents/tasks/repository-size-reduction.md` @
`a7704a1a3a0fddc929c984b11d232bddd82c9e70`
Accepted baseline: `b14625ab01fe031cb3a9258b9fc5ff2227b032b3`
Branch: `refactor/package-boundaries`
History rewrite: prohibited and not performed.

## Before

Measured at HEAD `a7704a1a3a0fddc929c984b11d232bddd82c9e70` before cleanup:

| Metric | Value |
|---|---:|
| tracked files | 275 |
| tracked-tree bytes | 330,095,989 |
| tracked-tree MiB | 314.8041 |
| files > 1 MiB | 16 |
| files > 5 MiB | 11 |
| files > 10 MiB | 10 |
| files > 20 MiB | 10 |
| loose objects | 725 / 3.29 MiB |
| packed objects | 1,569 |
| pack size | 274.69 MiB |

Largest active files were the 74,446,788-byte runtime `remap.npz`, nine
24–27 MiB calibration TIFFs, and the 8,419,601-byte 2026 paper PDF.

## Cleanup decisions

- **Retained, runtime-required:**
  `research/kambing-260714/data/output/calibration-cache/4832df384f0539643af026fbfc5f29cd2d44e380143e1e67b4118b42bdf1555b/{metadata.json,remap.npz}`.
  `.github/workflows/setup-runtime-dirs.yml` copies these exact files into the
  deployed calibration directory.
- **Removed, generated/reproducible:** all tracked files under
  `artifacts/camera-calibration-dotgrid/output/` (49 files), including neural,
  OpenCV, radiography, plots, masks, TIFFs, CSVs, and reports.
- **Removed, replaceable source data:** the two tracked TIFF inputs under
  `artifacts/camera-calibration-dotgrid/data/` (2 files). Calibration CLI
  defaults remain unchanged; no runtime or test path reads these files.
- **Removed, replaceable references:** six bundled paper PDFs under
  `artifacts/camera-calibration-dotgrid/references/` (6 files). Their titles
  remain recoverable from the deleted paths and Git history; no external URL
  was invented.
- **Removed, obsolete exploratory material:**
  `artifacts/imager-pipeline/archive/try.ipynb` and the two
  `research/kambing-260714/*.ipynb` notebooks (3 files). No runtime/test
  references were found.
- **Retained:** accepted real-data characterization files, source, tests,
  configuration, lightweight JSON/CSV, and the runtime calibration cache.

Exact deleted paths are the staged `git diff --cached --name-status` output;
the groups above are intentionally narrow and match the new ignore rules.

## After active-tree measurement

Measured after cleanup and the Phase-1 commit:

| Metric | Value |
|---|---:|
| tracked files | 224 |
| tracked-tree bytes | 76,629,279 |
| tracked-tree MiB | 73.0794 |
| files > 1 MiB | 1 |
| files > 5 MiB | 1 |
| files > 10 MiB | 1 |
| files > 20 MiB | 1 |
| active-tree bytes removed | 253,466,710 |
| active-tree MiB removed | 241.7247 |
| active-tree reduction | 76.7858% |

The one remaining file above 20 MiB is the retained 74,446,788-byte runtime
`remap.npz`. Git object/pack size is expected to remain history-heavy until a
separate approved Phase-2 rewrite; it must not be described as clone savings
from this active-tree deletion.

## Reachable-history inventory

Generated deterministically from `git rev-list --objects --all` and
`git cat-file`. The following are the 50 largest unique reachable blobs by
uncompressed blob size; repeated historical `uv.lock` and source revisions are
shown because they remain reachable objects.

| bytes | blob | known path |
|---:|---|---|
| 74,446,788 | `bbc4faaad27b39d09bea413aff10d18d7aa7581d` | `research/kambing-260714/data/output/calibration-cache/.../remap.npz` |
| 27,281,686 | `74a2f1eebe762de261f158d7acf6ec58c0ab5397` | `artifacts/camera-calibration-dotgrid/output/opencv_baseline/undistorted_image.tiff` |
| 27,277,396 | `83ee9590494d4c34f6f5c46606868910a74e002f` | `artifacts/camera-calibration-dotgrid/output/neural_model/calibrated_image_expanded.tiff` |
| 26,216,464 | `83a54b2a72c0179a9eb6da2be2242a3acc98a22c` | `artifacts/camera-calibration-dotgrid/output/neural_model/calibrated_image_cropped.tiff` |
| 25,958,934 | `def0e20d4afd36edd9b93315e54d859bb22fb0f7` | `artifacts/camera-calibration-dotgrid/output/neural_model/calibrated_image.tiff` |
| 24,576,256 | `b8126af7171ab9247283c0c45e50f403f3157104` | `artifacts/camera-calibration-dotgrid/data/BED_1783222981898_processedimage.tiff` |
| 24,576,256 | `7fdebe2acb9e95f40ebf50543a342efeb1786980` | `artifacts/camera-calibration-dotgrid/data/lowanu-bed-kalibrasi.tiff` |
| 23,923,148 | `5e530dc805d6714eab20e09815dec94a1f852ef4` | `artifacts/camera-calibration-dotgrid/output/radiography/...expanded.tiff` |
| 22,802,428 | `19f355e4cf41ab235e63c20a59cb332b1c5f3c8a` | `artifacts/camera-calibration-dotgrid/output/radiography/...calibrated.tiff` |
| 22,492,134 | `9374177a6696bf4d525c41b4abad57a10` | `artifacts/camera-calibration-dotgrid/output/radiography/...cropped.tiff` |
| 8,419,601 | `4f4dcc51413db863c029016e29d73ac5cd37a65a` | `artifacts/camera-calibration-dotgrid/references/2026-Kelei Wang-...pdf` |
| 4,969,777 | `a869b66ff7c8fa4fc5eccc16d42cad191f4c7677` | `artifacts/camera-calibration-dotgrid/references/2025-Kelei Wang-...pdf` |
| 4,521,125 | `4f8a61f515072e581b032f2ea5cffdb0be396f95` | `artifacts/camera-calibration-dotgrid/references/2025-N.L.S. Maharani-...pdf` |
| 4,511,451 | `328f613267fd4f259f29ffd019fc1450b2a144f6` | `artifacts/camera-calibration-dotgrid/output/kalibrasi_overlay.jpg` |
| 1,711,342 | `2be57beac602ab10a1ce39796bb337d20b904ddd` | `artifacts/camera-calibration-dotgrid/references/2015-Bogdan Khomutenko-...pdf` |
| 1,433,312 | `abc33e42c35f4b177f303faa4404b6701f37344e` | `artifacts/imager-pipeline/archive/try.ipynb` |
| 1,265,043 | `688db8db9d7e340af8f1a83655130cdde4e640ec` | `research/kambing-260714/imager_pipeline_tweak_local.ipynb` |
| 571,009 | `c174e14b838b00088db273c10cbfe2305199b069` | `artifacts/camera-calibration-dotgrid/references/2009-Dong-Min Woo-...pdf` |
| 524,025 | `ff2c0b4dfd0e805f2ee28e05e8cdfcf118fe1651` | `artifacts/camera-calibration-dotgrid/output/3d_flat_mesh_plot.png` |
| 423,560 | `081f9d6654bc0ec5ca14e477bf2befc6763638e1` | `artifacts/camera-calibration-dotgrid/references/2006-Juho Kannala-...pdf` |
| 397,388 | `175a66610b4f01db949014d6d542ea7e883097c` | `artifacts/camera-calibration-dotgrid/output/3d_horizontal_euclidean.png` |
| 393,393 | `37ec41583e7231a4ef6ab4ba6d77b5862225d4d3` | `uv.lock` |
| 392,897 | `9833ca09a899ccd0e6b03b7f20d3a8ace46ede3b` | `uv.lock` |
| 392,773 | `4d360c5a08e6f15fc9d0c149ea1eba9394f2ef35` | `uv.lock` |
| 391,884 | `d92ae1a5676ebc1e34cceb62de1164234f42c3e9` | `uv.lock` |
| 286,707 | `00f3e390901479eac5274f0ea8c902cecfa43bec` | `uv.lock` |
| 284,238 | `a771a2d368517216a172efdeb65ec863aabf2151` | `uv.lock` |
| 283,578 | `15d734ff10676b07ec2f0754e22e4e9ff791a943` | `uv.lock` |
| 197,140 | `eb2846d79331a5f3d8926eada86b328ca736c3c5` | `uv.lock` |
| 136,201 | `8e5df174dbe6818e60da7574a5baff4dbae1a6f2` | `uv.lock` |
| 105,516 | `e3fd04119bd4fe4ec6084d3ec49ab23b199a5e2b` | `uv.lock` |
| 84,886 | `0330ca7e8a9319fb3efebedf74254b44ed62a87b` | `artifacts/camera-calibration-dotgrid/output/actual_y_coordinates_plot.png` |
| 83,006 | `53dd02e5ecc40bfefde9f567b17a0c5cae0032a2` | `artifacts/camera-calibration-dotgrid/output/actual_x_coordinates_plot.png` |
| 73,595 | `8bbe80191e34b766118f92184d4b87947a2fa6d5` | `artifacts/camera-calibration-dotgrid/output/neural_model/compensated_x_plot.png` |
| 67,040 | `c5a0479b2ad236ad91003a6c1b22c27272c42870` | `artifacts/camera-calibration-dotgrid/output/horizontal_distortion_plot.png` |
| 65,994 | `3bc069865a91929a84163b2f1d722139e93515a0` | `artifacts/real-data-regression/radiograph-structural-characterization.json` |
| 63,771 | `006d594569791f72d45752e0cd10c18a63abef40` | `artifacts/camera-calibration-dotgrid/output/neural_model/compensated_y_plot.png` |
| 61,757 | `b97e8d786b89e54cfdd4fb4cda67a3e4d32d8c07` | `.agents/software-workflow.md` |
| 60,529 | `d739743cba6cdd1fb0ed47f7689009f93dcbcaac` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 60,389 | `4296cb90b86ba0285df0afb9d477475a25176abd` | `artifacts/camera-calibration-dotgrid/output/vertical_distortion_plot.png` |
| 59,826 | `84ef856ea486eb1d39f986aa526a5415dc243cd5` | `research/imager-pipeline/complete_pipeline.py` |
| 57,928 | `bd93947587ec784299b8e1dba85c6317616df1d4` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 57,406 | `db32d72039493dcb1a003fee6dd118d42e762949` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 56,936 | `18f28a1f29e75fed2e1049f6c9888863f665a56b` | `tests/api/test_dicom_conversion.py` |
| 55,548 | `4e81dba2eeac6c92f81eb2708913418a936c6c17` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 55,366 | `9ffed66d6e3291ab40e9e4f114c46f3a57a6783c` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 55,288 | `4c725b6580975a2d9fd24a6e055c9a0e10bbed72` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 55,277 | `7a9c48f77691dbbe8cdcb9882e74931fbdeb167e` | `mpips/engine/imager_pipeline/complete_pipeline.py` |
| 52,746 | `e16b6821dc33ba2105f41de81f0a98ac526c13a3` | `tests/api/test_dicom_conversion.py` |
| 52,722 | `0c5fbfa4bbde4a084b52d5fd27d8436cf53b0d9f` | `tests/api/test_dicom_conversion.py` |

The remaining entries are historical source, test, and documentation blobs;
the command above remains the deterministic source for refreshing this table.

## Phase 2 candidate set

For unique reachable blobs in the removed classes, excluding the retained
runtime calibration cache, the projected uncompressed candidate total is
**254,730,118 bytes (242.9296 MiB)** across 55 blobs:

| class | unique reachable bytes |
|---|---:|
| generated output | 182,201,940 |
| source TIFF data | 49,152,512 |
| bundled papers | 20,616,414 |
| notebooks | 2,759,252 |

53 of the candidate blobs are present in the current HEAD tree before this
cleanup; 2 are historical-only. A history rewrite would change every commit
and descendant SHA that references these blobs, requiring coordinated ref
migration and force-push authorization. Fresh-clone verification must compare
the rewritten refs, run `git fsck --full --no-reflogs`, verify the retained
runtime cache checksum, clone without local unreachable objects, and rerun the
repository test/static checks. Summed blob bytes are not final packed-clone
savings because Git delta compression, duplicate blobs, and pack layout affect
the result.

## Prevention and verification

`.gitignore` now narrowly excludes calibration TIFF inputs, calibration output,
bundled paper PDFs, and the named exploratory notebooks. `artifacts/README.md`
records the retention and approval policy. No production source, defaults,
dependencies, lockfiles, or external systems were changed.

Protected converter before cleanup:
`a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`.

Observed checks: `tests/test_converter_protection.py` passed (1 test), Black
passed, Flake8 passed, `git diff --check` passed, and the protected converter
hash remained exact. The broader focused/full pytest commands were attempted
but the local process was terminated during collection/execution before a
result was emitted; no pass is claimed for those suites. Mypy was likewise not
completed after the local process termination. No Python source changed in
this phase.
