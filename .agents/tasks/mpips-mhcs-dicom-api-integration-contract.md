---
title: MHCS Integration Contract & Implementation Guide
document_id: AGENT-TASK-MPIPS-MHCS-CONTRACT-001
version: 1.1
status: approved-reference
language: en-US
last_updated: 2026-08-12
scope:
  - MHCS DICOM API integration contract documentation
  - synthetic JSON manifest example
  - documentation schema validation test
  - simplified manifest schema contract with optional fields
  - detector_type calibration mode selection (BED / THORAX)
authority_note: This task governs the creation of authoritative integration documentation and schemas for MHCS consumption of the MPIPS DICOM API.
---

# Task: MHCS Integration Contract & Implementation Guide

## Delivery Context

MHCS (Madeena Health Care Services) requires an authoritative integration contract to safely and correctly consume the current MPIPS DICOM conversion API (`POST /v1/radiographs/dicom`). This task produces comprehensive integration documentation, an example synthetic manifest, and schema validation tests for MPIPS API consumption.

## Task Baseline

- **Starting HEAD:** `7acf893cf98ba6be89e371aaf3c023dcfae831ff`
- **Target Files:**
  - `docs/integration/mhcs-dicom-api.md`
  - `docs/integration/examples/mhcs-dicom-manifest.example.json`
  - `tests/api/test_mhcs_integration_docs.py`
  - `mpips/api/schemas/dicom.py`

## Primary Objectives

1. Maintain `docs/integration/mhcs-dicom-api.md` covering all contract sections, including optional fields and `detector_type`.
2. Maintain `docs/integration/examples/mhcs-dicom-manifest.example.json` validating cleanly against `MHCSManifest`.
3. Support simplified manifest payloads with optional DICOM UIDs, UUIDs, file hashes, and accession numbers.
4. Support `detector_type` (`"BED"` / `"THORAX"`) under `capture` for automatic detector calibration selection.
5. Continuously validate example manifests against `MHCSManifest` via `tests/api/test_mhcs_integration_docs.py`.
