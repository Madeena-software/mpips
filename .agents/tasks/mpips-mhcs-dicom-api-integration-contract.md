---
title: MHCS Integration Contract & Implementation Guide
document_id: AGENT-TASK-MPIPS-MHCS-CONTRACT-001
version: 1.0
status: approved-reference
language: en-US
last_updated: 2026-08-12
scope:
  - MHCS DICOM API integration contract documentation
  - synthetic JSON manifest example
  - documentation schema validation test
authority_note: This task governs the creation of authoritative integration documentation for MHCS consumption of the MPIPS DICOM API without runtime or deployment changes.
---

# Task: MHCS Integration Contract & Implementation Guide

## Delivery Context

MHCS (Madeena Health Care Services) requires an authoritative integration contract to safely and correctly consume the current MPIPS DICOM conversion API (`POST /v1/radiographs/dicom`). This task produces comprehensive integration documentation, an example synthetic manifest, and a schema validation test without modifying MPIPS production runtime code or deployment configuration.

## Task Baseline

- **Starting HEAD:** `7acf893cf98ba6be89e371aaf3c023dcfae831ff`
- **Target Files:**
  - `docs/integration/mhcs-dicom-api.md`
  - `docs/integration/examples/mhcs-dicom-manifest.example.json`
  - `tests/api/test_mhcs_integration_docs.py`

## Primary Objectives

1. Produce `docs/integration/mhcs-dicom-api.md` covering all 24 required contract sections.
2. Produce `docs/integration/examples/mhcs-dicom-manifest.example.json` validating cleanly against `MHCSManifest`.
3. Add `tests/api/test_mhcs_integration_docs.py` to continuously validate example manifest against `MHCSManifest`.
4. Maintain 0 runtime modifications and 0 production deployment actions.
