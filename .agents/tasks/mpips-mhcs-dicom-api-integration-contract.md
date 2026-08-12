---
title: MHCS Integration Contract & Implementation Guide
document_id: AGENT-TASK-MPIPS-MHCS-CONTRACT-001
version: 1.2
status: approved-reference
language: en-US
last_updated: 2026-08-12
scope:
  - MHCS DICOM API integration contract documentation
  - synthetic JSON manifest examples (full and minimal)
  - documentation schema validation tests
  - minimal manifest schema contract with resolution layer
  - detector_type calibration mode selection (BED / THORAX / TRX)
authority_note: This task governs the creation of authoritative integration documentation and schemas for MHCS consumption of the MPIPS DICOM API.
---

# Task: MHCS Integration Contract & Implementation Guide

## Delivery Context

MHCS (Madeena Health Care Services) requires an authoritative integration contract to safely and correctly consume the current MPIPS DICOM conversion API (`POST /v1/radiographs/dicom`). This task produces comprehensive integration documentation, example synthetic manifests (full and minimal), and schema validation tests for MPIPS API consumption.

## Task Baseline

- **Starting HEAD:** `ae5ef53f0eef89b0033e28f2329579e0cbc0e50e`
- **Target Files:**
  - `docs/integration/mhcs-dicom-api.md`
  - `docs/integration/examples/mhcs-dicom-manifest.example.json`
  - `docs/integration/examples/mhcs-dicom-manifest.minimal.example.json`
  - `tests/api/test_mhcs_integration_docs.py`

## Primary Objectives

1. Maintain `docs/integration/mhcs-dicom-api.md` covering all contract sections, including minimal client manifests and resolved internal manifests (`ResolvedMHCSManifest`).
2. Maintain `docs/integration/examples/mhcs-dicom-manifest.example.json` and `docs/integration/examples/mhcs-dicom-manifest.minimal.example.json` validating cleanly against `MHCSManifest`.
3. Document minimal manifest payloads with server-computed file metadata, deterministic identifiers, DICOM UIDs, timestamps, and technical defaults.
4. Support `detector_type` (`"BED"` / `"THORAX"` / `"TRX"`) under `capture` for automatic detector calibration selection.
5. Continuously validate example manifests against `MHCSManifest` via `tests/api/test_mhcs_integration_docs.py`.
