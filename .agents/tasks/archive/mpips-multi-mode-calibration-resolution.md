---
name: mpips-multi-mode-calibration-resolution
description: Implement dynamic calibration artifact resolution to allow a single MPIPS API deployment to serve multiple radiograph modes concurrently based on NPZ detector metadata.
version: 1
---

<!-- antigravity-code-agent-template:managed -->
# Task: Dynamic multi-mode calibration resolution

## Objective

For `$TARGET`, update the API service and isolated worker to support dynamic, multi-mode calibration resolution. This allows the API to serve diverse radiograph types (e.g. BED and STAND) automatically based on the metadata contained within the uploaded radiograph NPZ file, without needing separate deployments.

## Context

Currently, the MPIPS DICOM-only API expects exactly one active calibration artifact (containing `metadata.json` and `remap.npz`) mapped directly into the `/opt/mpips/calibration` directory. The worker only checks if this exact calibration's `detector_mode` matches the radiograph. 

To support future Thorax/STAND images, the `/opt/mpips/calibration` root directory must be allowed to contain multiple subdirectories, each holding a different calibration artifact (e.g., `BED/` and `STAND/`). 

## Governing Authority

- Architecture: `project.md` and `worker.py` isolation boundary constraints.

## Scope

### In scope

1. **`mpips/conversion/service.py`**:
   - Update `resolve_calibration_artifact_dir()` to return the root calibration directory without enforcing that `metadata.json` exists directly in the root. 
   - Ensure backward compatibility: if `metadata.json` is at the root, it should still return the root. Otherwise, return the directory assuming it contains valid subdirectories.

2. **`mpips/conversion/worker.py`**:
   - Update the isolated worker logic to handle a `calibration_dir` containing multiple subdirectories.
   - After safely extracting `rad_info["detector_mode"]`, scan all subdirectories inside `calibration_dir`.
   - Read `metadata.json` in each subdirectory and select the one where `source_metadata.detector_mode` matches the radiograph.
   - Keep backward compatibility for single-mode setups (if `metadata.json` is at the root of `calibration_dir`).

3. **`tests/api/test_dicom_conversion.py`**:
   - Add a focused unit test covering multi-directory calibration resolution. Create two mock calibration subdirectories (e.g., one BED, one STAND) and verify the worker correctly selects the artifact matching the incoming radiograph's `detector_mode`.

### Out of scope

- Parsing the `radiograph_npz` file inside the `mpips-api` container (i.e. inside `service.py`). Parsing must remain strictly inside the isolated worker environment (`worker.py`) to preserve the security boundary.
- Making structural changes to how DICOM files are generated.

### Preserved behavior

- Cryptographic hashes of unaffected modules (like `tiff_json_to_dcm.py`) must remain unchanged.
- The single-mode calibration structure must remain supported.
- `map_x.shape != map_y.shape` validation must be preserved.

## Implementation Baseline

- Target Revision: `2b13a96` or later.

## Verification Plan

### Acceptance criteria

- [ ] `resolve_calibration_artifact_dir` allows a directory lacking an immediate `metadata.json` if it contains valid calibration subdirectories.
- [ ] `worker.py` dynamically scans subdirectories and matches `source_metadata.detector_mode` to `rad_info["detector_mode"]`.
- [ ] `worker.py` preserves single-mode backwards compatibility.
- [ ] The full test suite (`pytest -q`) passes cleanly.
- [ ] A new test explicitly validates that the correct subdirectory is chosen based on the `detector_mode` of the NPZ payload.
- [ ] Execute `scripts/test_real_kambing_dicom.py` (via `uv run`) against the local deployment to guarantee backward compatibility with the existing BED real-data workflow is 100% intact.

The Executor must implement these changes and report all observed test results.
