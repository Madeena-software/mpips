---
title: Linux Standalone .bin Feasibility and Embedded Calibration Prototype
version: 1.0
status: Validated/Published
language: en-US
---

# Executable Task

## Task identity

**Task title:** Linux Standalone .bin Feasibility and Embedded Calibration Prototype (Milestone 5 Prototype)

**Task path:** `.agents/tasks/mpips-standalone-bin-prototype.md`

**Task contract state:** Validated/Published.

**Delivery objective:** Build and qualify an experimental self-contained Linux ELF executable named `mpips-runtime.bin` for Ubuntu 24.04 x86_64. The executable must run without a separately installed Python interpreter or packages, preserve offline NPZ-to-DICOM conversion, expose a Grabber-facing `convert` command without `--calibration` (resolving calibration assets internally from embedded profiles), preserve deterministic JSON status and failure handling, and support synthetic BED/TRX workflows. If single-file ELF executable is blocked, preserve standalone-directory results and report exact blockers. Protected converter immutability and existing TAR package qualification must be preserved. Development-only feasibility experiment; G10 remains NOT RELEASED.

**Owner / designated planning authority:** Designated user instruction ("MPIPS — Linux Standalone .bin Feasibility and Embedded Calibration Prototype").

## Delivery context

1. Assess calibration contract: separate algorithms (in source), detector-specific assets (`metadata.json`, `remap.npz`), and per-acquisition `gain.npz` (remains external).
2. Generate explicitly labeled synthetic calibration profiles for BED and TRX test fixtures and embed them into the bundle.
3. Expose experimental CLI interface: `--version` and `convert --radiograph ... --gain ... --manifest ... --output ...` without `--calibration`. Document interface distinction (`interface_version: "2-experimental"` or equivalent) while keeping existing `mpips.runtime` CLI interface 1 intact.
4. Evaluate PyInstaller in an isolated build environment without global/unapproved persistent modifications.
5. Stage A: Build a working standalone directory bundle.
6. Stage B: Build single-file Linux ELF executable `mpips-runtime.bin`.
7. Solve worker subprocess dispatch in frozen environment, native C extensions (NumPy, SciPy, OpenCV), process isolation/timeout, and clean extraction.
8. Qualify in isolated environment against BED and TRX synthetic workflows and negative cases, comparing DICOM output and performance against the accepted TAR baseline.

## Baseline and task revision

**Implementation baseline:**
`8dd42a7106d13ff602f41a57b726668066791bec` (verified `main` HEAD).

**Task revision:**
The governing identity is `<task path> @ <full SHA of the commit publishing this task>`.

## Requirements, ownership, and verification

| ID | Obligation | Owner | Verification |
|---|---|---|---|
| REQ-CALIB-CONTRACT | Distinguish algorithms, detector assets, and per-exam gain; build and embed labeled synthetic calibration profiles | MPIPS | Profile inspection & verification test |
| REQ-CLI-SURFACE | Expose `--version` and `convert` without `--calibration`; reject mismatches; keep existing `mpips.runtime` interface 1 intact | MPIPS | CLI unit and integration tests |
| REQ-FREEZE-STAGE-A | Produce working standalone directory distribution via PyInstaller in isolated build env | MPIPS | Build script execution and directory run check |
| REQ-FREEZE-STAGE-B | Produce self-contained single-file ELF `mpips-runtime.bin` with worker process isolation | MPIPS | ELF binary inspection (`file`, `ldd`) & execution |
| REQ-E2E-QUALIFY | Synthetic BED/TRX conversion, negative failure cases, pixel/DICOM regression vs TAR baseline | MPIPS | Automated qualification test suite |
| REQ-SAFETY-GOV | Converter immutability (`mpips/conversion/tiff_json_to_dcm.py`), candidate non-distribution status, G10 NOT RELEASED | MPIPS | Hash verification and clean isolation |

## Scope and constraints

- **In Scope:** Build script/spec for freezing, embedded synthetic calibration assets, runtime entrypoint adapter supporting no-calibration CLI, qualification tests, and evidence report.
- **Out of Scope:** Clinical deployment, production releases, modifying `mpips/conversion/tiff_json_to_dcm.py`, removing subprocess worker isolation.
