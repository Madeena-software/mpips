# MHCS INTEGRATION CONTRACT & IMPLEMENTATION GUIDE

**Repository:** [MPIPS](https://github.com/Madeena-software/mpips)  
**Target Consumer:** `mhcs-core` (Madeena Health Care Services)  
**API Surface:** Synchronous DICOM Conversion Endpoint (`POST /v1/radiographs/dicom`)  
**Contract Version:** 1.2  
**Baseline Commit SHA:** `ae5ef53f0eef89b0033e28f2329579e0cbc0e50e`  
**Document Status:** Authoritative Integration Contract  

---

## 1. Purpose

This document provides the authoritative integration contract for Madeena Health Care Services (MHCS) to safely, reliably, and correctly consume the MPIPS synchronous DICOM conversion API.

The objective is to provide complete, unambiguous technical specifications, schema definitions, failure handling logic, idempotency rules, and client pseudocode so that any developer or automated subagent working inside `mhcs-core` can implement the client library without reverse-engineering MPIPS source code.

> [!IMPORTANT]
> This contract applies strictly to the current synchronous v1 API surface (`POST /v1/radiographs/dicom`). MPIPS uses a **fail-fast admission control model** with concurrency bounded to 2. MPIPS does **not** maintain a server-side waiting queue. MHCS is responsible for client-side retry orchestration.

---

## 2. Architecture & Manifest Layers

```text
+-------------------------------------------------------------------------------+
|                                 MHCS SERVICE                                  |
|                                 (mhcs-core)                                   |
+-------------------------------------------------------------------------------+
                                       |
                                       | POST /v1/radiographs/dicom
                                       | Multipart: radiograph_npz, gain_npz, manifest
                                       | Header: X-MPIPS-API-Key
                                       v
+-------------------------------------------------------------------------------+
|                                 MPIPS API                                     |
|                        (Container: mpips-api:8000)                            |
|                                                                               |
|  1. Authenticate X-MPIPS-API-Key                                             |
|  2. Validate Upload Size Limits (Manifest < 100MB, Rad < 100MB, Gain < 100MB)  |
|  3. Parse Client Input Manifest (MHCSManifest)                                |
|  4. Materialize & Resolve Manifest (resolve_mhcs_manifest -> ResolvedMHCSManifest)|
|     - Stream/Compute file byte sizes & SHA-256 hashes if omitted              |
|     - Derive deterministic conversion_job_id, submission_id, correlation_id  |
|     - Derive deterministic DICOM UIDs (2.25.<decimal_uuid>) if omitted       |
|     - Default operator, site, capture, and study_id metadata                 |
|  5. Claim Redis Idempotency Lease (mpips:dicom_idempotency:...)               |
|  6. Acquire Process Concurrency Limiter (CapacityLimiter max=2)               |
+-------------------------------------------------------------------------------+
          |                                                       |
          | Capacity Available (Active < 2)                       | Capacity Exhausted (Active == 2)
          v                                                       v
+------------------------------------+                 +------------------------+
| ISOLATED WORKER PROCESS / CONTAINER|                 |  IMMEDIATE HTTP 429    |
| (mpips-npz-worker)                 |                 | CONCURRENCY_LIMIT_     |
|                                    |                 |       EXCEEDED         |
|  - Process arrays & calibration    |                 |  Header: Retry-After: 5 |
|  - Generate processed.tiff         |                 +------------------------+
|  - TOCTOU descriptor validation    |                            |
|  - Enrich DICOM & validate dataset |                            | Client-side bounded
|  - Return application/dicom (200)  |                            v retry (stable job_id)
+------------------------------------+                 +------------------------+
                                                       |   MHCS CLIENT RETRY    |
                                                       | Exponential Backoff    |
                                                       | + Full Jitter          |
                                                       +------------------------+
```

### Two Manifest Layers (Client vs. Internal Server)

MPIPS explicitly decouples client submission schemas from internal worker execution schemas:

1. **MINIMAL MANIFEST / CLIENT INPUT MANIFEST (`MHCSManifest`)**:
   - Pydantic model: `MHCSManifest`
   - This is what MHCS submits in the `manifest` form field.
   - Designed for developer ergonomics and payload minimization. All file metadata, identifiers, timestamps, operator details, site details, and DICOM UIDs may be omitted by MHCS.
2. **RESOLVED INTERNAL MANIFEST (`ResolvedMHCSManifest`)**:
   - Pydantic model: `ResolvedMHCSManifest`
   - Materialized internally by `resolve_mhcs_manifest()`.
   - **NOT required from MHCS.**
   - MPIPS resolves all optional/defaulted fields **BEFORE**:
     - Computing the Redis idempotency fingerprint
     - Initiating isolated worker conversion
     - Performing DICOM enrichment
     - Validating DICOM dataset completeness
     - Recording successful completion state

---

## 3. Authoritative Client Minimal Manifest

MHCS MAY submit a **MINIMAL MANIFEST** containing only basic patient and clinical capture parameters.

### Minimal Client JSON Payload (`mhcs-dicom-manifest.minimal.example.json`)

```json
{
  "examination": {
    "study_description": "CHEST RADIOGRAPH"
  },
  "patient": {
    "medical_record_number": "MRN-90214810",
    "name": "JANE DOE",
    "sex": "female",
    "birth_date": "1988-03-15"
  },
  "capture": {
    "detector_type": "THORAX",
    "body_part_examined": "CHEST",
    "laterality": "U",
    "projection": "PA"
  }
}
```

> [!NOTE]
> The minimal manifest JSON is sent as `multipart/form-data` alongside binary form fields `radiograph_npz` and `gain_npz`. Binary NPZ array data MUST NOT be embedded inside the JSON string.

---

## 4. Client Fields Classification & Requirements

To eliminate ambiguity, payload fields are classified using strict terminology:

- **`REQUIRED FROM CLIENT`**: Must be explicitly supplied by MHCS in `MHCSManifest`.
- **`OPTIONAL FROM CLIENT`**: May be supplied by MHCS or omitted.
- **`SERVER COMPUTED`**: Computed directly from streaming upload file bytes if omitted.
- **`SERVER DERIVED`**: Derived deterministically using cryptographic hashing (UUIDv5) if omitted.
- **`SERVER DEFAULTED`**: Materialized using safe technical fallback defaults if omitted.

### Field Requirements Matrix

| Field Path | Category | Default / Derivation Behavior | Description |
|---|---|---|---|
| `manifest_version` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"1.0"`) | Schema version. |
| `conversion_job_id` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (UUIDv5 from manifest + NPZs SHA-256) | Unique conversion job ID. |
| `submission_id` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (UUIDv5 from job ID + `"submission"`) | Submission tracking ID. |
| `correlation_id` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (UUIDv5 from job ID + `"correlation"`) | Distributed tracing correlation ID. |
| `examination` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (Section defaults applied) | Examination metadata block. |
| `examination.accession_number` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (`ACC-<job_hex[:10]>`) | **SERVER FALLBACK TECHNICAL VALUE.** RIS Accession Number. |
| `examination.study_id` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"STUDY01"`) | **SERVER FALLBACK TECHNICAL VALUE.** Study ID (defaults to `"STUDY01"`). |
| `examination.performed_at` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (Deterministic ISO timestamp) | **SERVER-GENERATED TECHNICAL FALLBACK TIMESTAMP.** |
| `examination.study_description` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"CHEST RADIOGRAPH"`) | Study description (DICOM `(0008,1030)`). |
| `examination.protocol_name` | `OPTIONAL FROM CLIENT` | Remains `None` if omitted | Imaging protocol name (no default string invented). |
| `patient` | `REQUIRED FROM CLIENT` | None | Patient demographic block. |
| `patient.member_id` | `OPTIONAL FROM CLIENT` | Remains `None` if omitted | System member UUID (never synthesized). |
| `patient.medical_record_number` | `REQUIRED FROM CLIENT` | None | Patient MRN / ID (DICOM `(0010,0020)`). **Required.** |
| `patient.name` | `REQUIRED FROM CLIENT` | None | Patient name (DICOM `(0010,0010)`). String or `PersonNameSchema`. **Required.** |
| `patient.sex` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"unknown"` -> DICOM `"O"`) | Enum `["male", "female", "other", "unknown"]`. |
| `patient.birth_date` | `OPTIONAL FROM CLIENT` | None | Format `YYYY-MM-DD` (DICOM `(0010,0030)` `YYYYMMDD`). |
| `operator` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`OP-SYSTEM` / `SYSTEM OPERATOR`) | Technologist metadata. |
| `site` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`ORG-MADEENA` / `SITE-DEFAULT` / `MADEENA MEDICAL CENTER` / `Asia/Jakarta`) | Imaging site metadata (`department_name` & `station_name` remain `None` if omitted). |
| `capture` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (Section defaults applied) | Image acquisition metadata block. |
| `capture.capture_id` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (`CAP-<conversion_job_id.hex[:12].upper()>`) | Capture identifier. |
| `capture.detector_type` | `OPTIONAL FROM CLIENT` | Auto-resolved from calibration / NPZ | Detector mode (`"BED"`, `"THORAX"`, `"TRX"`). |
| `capture.body_part_examined` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"CHEST"`) | Body part examined (DICOM `(0018,0015)`). |
| `capture.laterality` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"U"`) | Laterality (`"R"`, `"L"`, `"U"`, `"B"`). |
| `capture.projection` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"PA"`) | Projection view (`"PA"`, `"AP"`, etc.). |
| `capture.captured_at` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (Deterministic ISO timestamp) | **SERVER-GENERATED TECHNICAL FALLBACK TIMESTAMP.** |
| `capture.radiograph` | `OPTIONAL FROM CLIENT` | `SERVER COMPUTED` | Radiograph file metadata (`byte_size`, `sha256`). |
| `capture.gain` | `OPTIONAL FROM CLIENT` | `SERVER COMPUTED` | Gain file metadata (`byte_size`, `sha256`). |
| `capture.image_spacing` | `OPTIONAL FROM CLIENT` | Remains `None` in resolved manifest | `row_um` & `column_um`. If omitted, **DOWNSTREAM DICOM FALLBACK** applies `140 µm × 140 µm` (`0.140 mm × 0.140 mm`). |
| `dicom` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (Section defaults applied) | DICOM UIDs and instance sequence. |
| `dicom.study_instance_uid` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (`2.25.<decimal_uuid>`) | DICOM Study Instance UID `(0020,000D)`. |
| `dicom.series_instance_uid` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (`2.25.<decimal_uuid>`) | DICOM Series Instance UID `(0020,000E)`. |
| `dicom.sop_instance_uid` | `OPTIONAL FROM CLIENT` | `SERVER DERIVED` (`2.25.<decimal_uuid>`) | DICOM SOP Instance UID `(0008,0018)`. |
| `dicom.series_number` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`1`) | Series Number `(0020,0011)`. |
| `dicom.instance_number` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`1`) | Instance Number `(0020,0013)`. |
| `dicom.series_description` | `OPTIONAL FROM CLIENT` | Precedence fallback | `dicom.series_description` -> `examination.study_description` -> `"CHEST RADIOGRAPH"`. |
| `dicom.presentation_intent` | `OPTIONAL FROM CLIENT` | `SERVER DEFAULTED` (`"FOR PRESENTATION"`) | Must be `"FOR PRESENTATION"`. |

---

## 5. File Size / SHA-256 Contract

The file integrity verification behavior depends strictly on whether client file metadata is omitted or provided:

- **OMITTED = SERVER COMPUTED**:
  If `manifest.capture.radiograph` or `manifest.capture.gain` omits `byte_size` or `sha256`, MPIPS automatically measures the byte length and computes the lowercase SHA-256 hex digest while streaming the file uploads. **Server-computed file metadata is used for internal validation.**
- **PROVIDED = SERVER STRICTLY VERIFIES**:
  If MHCS explicitly supplies `byte_size` or `sha256`, MPIPS compares the supplied value against the actual uploaded binary stream. Any mismatch in size or hash immediately aborts conversion and returns `HTTP 422 Unprocessable Entity` with `{"detail": "NPZ_VALIDATION_ERROR"}`.

> [!IMPORTANT]
> File integrity verification is **NEVER disabled**. Omitting file sizes and hashes in minimal requests delegates computation to the server; providing them enforces strict verification.

---

## 6. Identifier Materialization & Deterministic Conversion Job ID Semantics

When MHCS omits identifiers, MPIPS deterministically derives them using UUIDv5 cryptographic hashing (`MPIPS_STABLE_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")`):

### Deterministic Derivation Formula

$$\text{digest} = \text{SHA256}(\text{canonical\_client\_json} + \text{radiograph\_sha256} + \text{gain\_sha256})$$
$$\text{conversion\_job\_id} = \text{UUIDv5}(\text{MPIPS\_STABLE\_NAMESPACE}, \text{"mpips:conversion:"} + \text{digest})$$

Where `canonical_client_json` is produced by parsing the client JSON and serializing with sorted keys and compact separators (`json.dumps(raw_dict, sort_keys=True, separators=(',', ':'))`).

### Derived Identifiers Summary

- **`conversion_job_id`**:
  - `IF SUPPLIED`: Preserved exactly as provided.
  - `IF OMITTED`: Derived deterministically via UUIDv5 from client JSON semantics + radiograph SHA-256 + gain SHA-256.
- **`submission_id`**:
  - `IF SUPPLIED`: Preserved.
  - `IF OMITTED`: Derived via UUIDv5 (`"mpips:submission:<conversion_job_id>"`).
- **`correlation_id`**:
  - `IF SUPPLIED`: Preserved.
  - `IF OMITTED`: Derived via UUIDv5 (`"mpips:correlation:<conversion_job_id>"`).
- **`capture_id`**:
  - `IF SUPPLIED`: Preserved.
  - `IF OMITTED`: Derived as `CAP-<conversion_job_id.hex[:12].upper()>`. Used to format the response filename (`CAP-XXXXXXXXXXXX.dcm`).

### Key Property of Deterministic Identifiers
- **JSON Formatting Independence:** Whitespace, key indentation, or property ordering in client JSON does NOT change the derived `conversion_job_id`.
- **Identity Equivalence:** Identical minimal JSON semantics + identical radiograph NPZ + identical gain NPZ = identical `conversion_job_id`.
- **Escape Hatch for Genuinely New Conversions:** If MHCS intentionally wants an otherwise identical request payload to be processed as a NEW logical conversion, MHCS MUST supply an explicit new `conversion_job_id`.

---

## 7. DICOM UID Ownership & Strategy

- **IF SUPPLIED**: MHCS retains full ownership of DICOM UIDs (`study_instance_uid`, `series_instance_uid`, `sop_instance_uid`). MPIPS preserves them unchanged.
- **IF OMITTED**: MPIPS derives valid, deterministic DICOM UIDs using the standard `2.25` root namespace:

$$\text{study\_instance\_uid} = \text{"2.25."} + \text{str}(\text{int}(\text{UUIDv5}(\text{MPIPS\_STABLE\_NAMESPACE}, \text{"mpips:study:"} + \text{conversion\_job\_id})))$$
$$\text{series\_instance\_uid} = \text{"2.25."} + \text{str}(\text{int}(\text{UUIDv5}(\text{MPIPS\_STABLE\_NAMESPACE}, \text{"mpips:series:"} + \text{conversion\_job\_id})))$$
$$\text{sop\_instance\_uid} = \text{"2.25."} + \text{str}(\text{int}(\text{UUIDv5}(\text{MPIPS\_STABLE\_NAMESPACE}, \text{"mpips:sop:"} + \text{conversion\_job\_id})))$$

> [!TIP]
> Generated DICOM UIDs are **valid DICOM UIDs**, **deterministic**, **$\le 64$ characters**, and **stable across retries**. They are resolved BEFORE DICOM conversion and enrichment.

---

## 8. Clinical Metadata Fallbacks & Open Integration Decisions

### Accession Number & Study ID
- `accession_number`:
  - `IF SUPPLIED`: Preserved.
  - `IF OMITTED`: Fallback technical value generated: `ACC-<job_hex[:10].upper()>`.
- `study_id`:
  - `IF SUPPLIED`: Preserved.
  - `IF OMITTED`: Resolved value is `"STUDY01"`.
- **Note:** `"STUDY01"` and `ACC-<job_hex[:10]>` are **SERVER FALLBACK TECHNICAL VALUES**, not authoritative RIS study identifiers.

### Protocol Name & Patient Member ID
- `examination.protocol_name`: Preserved if supplied; if omitted, remains `None` / absent (no protocol name string is invented).
- `patient.member_id`: Preserved if supplied; if omitted, remains `None`. MPIPS MUST NOT be documented as synthesizing patient or member identity.

### Timestamp Semantics & Residual Decision
- `IF SUPPLIED`: `capture.captured_at` and `examination.performed_at` are preserved as source clinical timestamps.
- `IF OMITTED`: Derived as a **SERVER-GENERATED TECHNICAL FALLBACK TIMESTAMP** (a deterministic ISO 8601 timestamp generated from job hash offset).

> [!WARNING]
> **SERVER-GENERATED TECHNICAL FALLBACK TIMESTAMPS MUST NOT BE INTERPRETED AS AUTHORITATIVE CLINICAL ACQUISITION TIMES.** MHCS SHOULD supply real source timestamps (`captured_at` / `performed_at`) when available.  
> **Residual Integration Decision:** `CLINICAL_TIMESTAMP_FALLBACK_POLICY=OPEN`.

### Patient Identity
- Patient MRN (`patient.medical_record_number`) and Name (`patient.name`) are **REQUIRED FROM CLIENT**. MPIPS will NOT synthesize fake MRNs or dummy patient names.
- `patient.sex` defaults to `"unknown"` (mapped to DICOM `"O"`).

### Operator & Site Defaults
- `operator`: Default fallback is `operator_id="OP-SYSTEM"`, `name="SYSTEM OPERATOR"`. (Technical fallback, not an actual technologist).
- `site`: Default fallback is `organization_id="ORG-MADEENA"`, `site_id="SITE-DEFAULT"`, `institution_name="MADEENA MEDICAL CENTER"`, `timezone="Asia/Jakarta"`. (`department_name` and `station_name` remain `None` if omitted).

---

## 9. Detector Type, Image Spacing & Gain ID

### Detector Type (`detector_type`)
- Allowed values: `"BED"`, `"THORAX"`, `"TRX"`. (`"THORAX"` and `"TRX"` normalize to thorax detector mode).
- `IF SUPPLIED`: Verified against NPZ/calibration metadata. If supplied mode contradicts NPZ detector parameters, conversion fails with `HTTP 422 NPZ_VALIDATION_ERROR`.
- `IF OMITTED`: Auto-resolved from calibration directory and NPZ header metadata.

### Image Spacing (`image_spacing`)
- Optional: `capture.image_spacing.row_um`, `capture.image_spacing.column_um`.
- `IF SUPPLIED`: Preserved in `ResolvedMHCSManifest`, converted to mm (`row_um / 1000.0`, `column_um / 1000.0`), and populated in DICOM `PixelSpacing`.
- `IF OMITTED`: `ResolvedMHCSManifest.capture.image_spacing` remains `None`. During metadata generation, DICOM enrichment, and validation, MPIPS applies a **DOWNSTREAM DICOM FALLBACK** of `140 µm × 140 µm` = `0.140 mm × 0.140 mm`.

### Gain ID (`gain_id`)
- Optional: `capture.gain.gain_id`.
- `IF OMITTED`: Resolved directly from `gain.npz` `gainid` array.
- `IF SUPPLIED`: Verified against `gain.npz`. Mismatch returns `HTTP 422 NPZ_VALIDATION_ERROR`.

---

## 10. Series Description Precedence & Retry Contract

### Series Description Fallback Precedence
When populating DICOM `SeriesDescription`, MPIPS evaluates fields in exact order of precedence:
1. Explicit `dicom.series_description` (if provided)
2. `examination.study_description` (if provided)
3. `"CHEST RADIOGRAPH"` (default fallback)

### Minimal Manifest Retry Contract
When retrying a transiently failed request (HTTP 429, 503, timeout, or network drop), MHCS MUST preserve:
1. Equivalent manifest JSON semantics
2. Exact `radiograph_npz` binary bytes
3. Exact `gain_npz` binary bytes

Because MPIPS derives identical deterministic identifiers, the retry maps to the exact same conversion job. MHCS does NOT need to precompute or reconstruct server-derived identifiers. On successful responses, MHCS SHOULD record `X-Conversion-Job-ID` and `X-Correlation-ID` headers for telemetry.

### Full Manifest Retry Contract
For requests explicitly supplying identifiers or DICOM UIDs, MHCS MUST preserve identical values across retries (`conversion_job_id`, `submission_id`, `correlation_id`, `capture_id`, DICOM UIDs, file hashes/sizes).

### Idempotency Fingerprint Formula
$$\text{fp} = \text{SHA256}(\text{tenant\_id} + \text{manifest\_version} + \text{conversion\_job\_id} + \text{canonical\_resolved\_manifest\_json} + \text{radiograph\_sha256} + \text{gain\_sha256})$$

---

## 11. Endpoint Specification & Responses

### Request Headers
- `X-MPIPS-API-Key`: Required pre-shared secret key. Missing/invalid key returns `HTTP 401 Unauthorized` (`{"detail": "INVALID_API_KEY"}`).

### Form Fields
- `radiograph_npz`: Binary file attachment (max `100 MiB`).
- `gain_npz`: Binary file attachment (max `100 MiB`).
- `manifest`: JSON file attachment (max `100 MiB`).

### HTTP Response Status Codes

| Status Code | Response Content-Type | Detail / Description | Action Required |
|---|---|---|---|
| `200 OK` | `application/dicom` | Conversion successful. Valid DICOM byte stream returned. | Save DICOM stream. Record headers `X-Conversion-Job-ID` and `X-Correlation-ID`. |
| `401 Unauthorized` | `application/json` | `INVALID_API_KEY`. Missing or invalid API key. | Verify `MPIPS_API_KEY` configuration. |
| `409 Conflict` | `application/json` | `IDEMPOTENCY_IN_PROGRESS` or `IDEMPOTENCY_CONFLICT`. Concurrent or completed duplicate job. | If `IN_PROGRESS`, retry with backoff. If `CONFLICT`, check parameters. |
| `413 Payload Too Large`| `application/json` | `UPLOAD_SIZE_EXCEEDED`. File or body limit exceeded. | Check NPZ file sizes. |
| `422 Unprocessable` | `application/json` | `NPZ_VALIDATION_ERROR` or schema validation error. | Check NPZ integrity, manifest format, detector compatibility. |
| `429 Too Many Requests`| `application/json` | `CONCURRENCY_LIMIT_EXCEEDED` (`Retry-After: 5`). Process capacity limit (2) reached. | Retry request using exponential backoff with full jitter. |
| `500 Internal Server Error`| `application/json` | `CONVERSION_FAILED`. Worker process error. | Log correlation ID and alert operator. |

### Success Response Headers
- `Content-Type`: `application/dicom`
- `Content-Disposition`: `attachment; filename="CAP-XXXXXXXXXXXX.dcm"`
- `X-Conversion-Job-ID`: `<conversion_job_id_string>`
- `X-Correlation-ID`: `<correlation_id_string>`

---

## 12. Proposed MHCS Retry Policy & Configuration

> [!IMPORTANT]
> **PROPOSED_MHCS_RETRY_POLICY**:
> - **Max Retries:** 5 attempts
> - **Base Backoff Delay:** 2.0 seconds
> - **Max Backoff Delay:** 30.0 seconds
> - **Jitter:** Full random jitter (`random.uniform(0, current_delay)`)
> - **Retryable Status Codes:** `HTTP 429`, `HTTP 502`, `HTTP 503`, `HTTP 504`, network drop/reset, `HTTP 409 IDEMPOTENCY_IN_PROGRESS`.
> - **Non-Retryable Status Codes:** `HTTP 401`, `HTTP 413`, `HTTP 422`, `HTTP 409 IDEMPOTENCY_CONFLICT`.

### Open Operational Configurations
- `MHCS_HTTP_TIMEOUT_UNKNOWN=true`: Proposed starting client timeout configuration is **330–360 seconds** to accommodate heavy CPU array calibration.
- `NPZ_UNTRUSTED_INPUT_SECURITY_POSTURE=OPEN`: Worker processes load NPZs (`allow_pickle=True`). Worker runs in isolated container without network access.

---

## 13. Conceptual Resolved Manifest Example (Internal Server Only)

> [!IMPORTANT]
> **INTERNAL MPIPS RESOLUTION EXAMPLE — NOT CLIENT REQUEST PAYLOAD**  
> This example illustrates the internal `ResolvedMHCSManifest` materialized by `resolve_mhcs_manifest()` after resolving defaults for a minimal client submission. MHCS MUST NOT submit this resolved model directly.

```json
{
  "manifest_version": "1.0",
  "conversion_job_id": "97eeb9ef-d93c-43e7-aebe-c9ada5cc29fa",
  "submission_id": "a46c3061-220a-4a1f-babe-a99f446439e5",
  "correlation_id": "29722404-a494-46ca-960b-537255d37982",
  "examination": {
    "examination_id": "EXAM-97EEB9EF",
    "booking_id": null,
    "service_request_id": null,
    "encounter_id": null,
    "accession_number": "ACC-97EEB9EFD9",
    "study_id": "STUDY01",
    "performed_at": "2026-08-12T00:00:00+00:00",
    "study_description": "CHEST RADIOGRAPH",
    "protocol_name": null
  },
  "patient": {
    "member_id": null,
    "medical_record_number": "MRN-90214810",
    "name": {
      "full_name": "JANE DOE",
      "family_name": null
    },
    "sex": "female",
    "birth_date": "1988-03-15"
  },
  "operator": {
    "operator_id": "OP-SYSTEM",
    "name": {
      "full_name": "SYSTEM OPERATOR",
      "family_name": null
    }
  },
  "site": {
    "organization_id": "ORG-MADEENA",
    "site_id": "SITE-DEFAULT",
    "institution_name": "MADEENA MEDICAL CENTER",
    "department_name": null,
    "station_name": null,
    "timezone": "Asia/Jakarta"
  },
  "capture": {
    "capture_id": "CAP-97EEB9EFD93C",
    "protocol_version": "1.0.0",
    "detector_type": "THORAX",
    "body_part_examined": "CHEST",
    "laterality": "U",
    "projection": "PA",
    "captured_at": "2026-08-12T00:00:00+00:00",
    "radiograph": {
      "filename": "radiograph.npz",
      "byte_size": 24785860,
      "sha256": "a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0",
      "gain_id": null
    },
    "gain": {
      "filename": "gain.npz",
      "byte_size": 24785860,
      "sha256": "b5b419772fcf9f529ccfde7g41be45b0fbf4ff120gd5367c14c434cf4d7817f1",
      "gain_id": null
    },
    "image_spacing": null
  },
  "dicom": {
    "study_instance_uid": "2.25.12345678901234567890123456789012345678",
    "series_instance_uid": "2.25.23456789012345678901234567890123456789",
    "sop_instance_uid": "2.25.34567890123456789012345678901234567890",
    "series_number": 1,
    "instance_number": 1,
    "series_description": "CHEST RADIOGRAPH",
    "presentation_intent": "FOR PRESENTATION"
  }
}
```

---

## 14. Minimal cURL Request Example

```bash
curl -s -i -X POST "http://127.0.0.1:8014/v1/radiographs/dicom" \
  -H "X-MPIPS-API-Key: ${MPIPS_API_KEY}" \
  -F "radiograph_npz=@radiograph.npz" \
  -F "gain_npz=@gain.npz" \
  -F "manifest=@mhcs-dicom-manifest.minimal.example.json" \
  --output "converted_radiograph.dcm"
```

---

## 15. Security Posture

1. **Private Network Exposure:** Production API binds strictly to internal container/mesh network (`http://mpips-api:8000`). Host binding is restricted to loopback `127.0.0.1:8014`.
2. **API Key Guard:** Evaluated in constant time (`hmac.compare_digest`). API keys are never logged.
3. **Upload Limits:** Enforced via streaming middleware (`300 MiB` total request cap).
4. **Execution Isolation:** Conversion runs in non-root worker process/container without egress network access.
5. **Residual Security Risk:** `NPZ_UNTRUSTED_INPUT_SECURITY_POSTURE=OPEN` (`allow_pickle=True` in NumPy loading). Untrusted input NPZs must be sanitized at ingress boundary before reaching storage.
