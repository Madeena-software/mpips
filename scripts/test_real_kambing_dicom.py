#!/usr/bin/env python3
import json
from pathlib import Path
import httpx
import pydicom

import os

API_KEY = os.getenv("MPIPS_API_KEY", "")
if not API_KEY:
    raise RuntimeError("MPIPS_API_KEY environment variable is required")
PORT = os.getenv("MPIPS_LOCAL_PORT", "8014")
URL = f"http://127.0.0.1:{PORT}/v1/radiographs/dicom"

RAD_PATH = Path("research/kambing-260714/data/kambing/BED_1783222264263.npz")
GAIN_PATH = Path("research/kambing-260714/data/gain/BED_1783219207291.npz")
OUT_DIR = Path("research/kambing-260714/data/output/api-test-output")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DICOM_OUT_PATH = OUT_DIR / "kambing_output.dcm"

manifest_data = {
    "manifest_version": "1.0",
    "conversion_job_id": "11111111-2222-3333-4444-555555555555",
    "submission_id": "66666666-7777-8888-9999-000000000000",
    "correlation_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "examination": {
        "examination_id": "EXAM-KAMBING-001",
        "booking_id": "BKG-KAMBING-001",
        "service_request_id": "SR-KAMBING-001",
        "encounter_id": "ENC-KAMBING-001",
        "accession_number": "KAMBING260714",
        "study_id": "STUDYKAMBING001",
        "performed_at": "2026-07-14T17:00:00+07:00",
        "study_description": "Kambing Radiography Test",
        "protocol_name": "Kambing Protocol",
    },
    "patient": {
        "member_id": "11111111-1111-1111-1111-111111111111",
        "medical_record_number": "KAMBING-MRN-001",
        "name": {"full_name": "Kambing Test Patient", "family_name": "Patient"},
        "sex": "other",
        "birth_date": "2020-01-01",
    },
    "operator": {
        "operator_id": "22222222-2222-2222-2222-222222222222",
        "name": {"full_name": "Operator Kambing", "family_name": "Operator"},
    },
    "site": {
        "organization_id": "ORG-KAMBING-001",
        "site_id": "SITE-KAMBING-001",
        "institution_name": "Research Lab",
        "department_name": "Radiology",
        "station_name": "STATION-01",
        "timezone": "Asia/Jakarta",
    },
    "capture": {
        "capture_id": "1783222265244",
        "protocol_version": "KAMBING-V1",
        "body_part_examined": "CHEST",
        "laterality": "U",
        "projection": "PA",
        "captured_at": "2026-07-14T17:00:00+07:00",
        "radiograph": {
            "filename": "BED_1783222264263.npz",
            "byte_size": 69615538,
            "sha256": "1a1436b6aab20a2161e862617afe7f951e4483a35b869bb7df2539d16cdc64f0",
        },
        "gain": {
            "gain_id": "1783219207291",
            "filename": "BED_1783219207291.npz",
            "byte_size": 16371836,
            "sha256": "2467d0e0efd81f7441053fc8bfdc7d246db457cd31d9d56be44b4239c22719c0",
        },
        "image_spacing": {"row_um": 140.0, "column_um": 140.0},
    },
    "dicom": {
        "study_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.100",
        "series_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.101",
        "sop_instance_uid": "1.2.826.0.1.3680043.10.1356.1.1.102",
        "series_number": 1,
        "instance_number": 1,
        "series_description": "Kambing PA",
        "presentation_intent": "FOR PRESENTATION",
    },
}

headers = {"X-MPIPS-API-Key": API_KEY}
manifest_json_str = json.dumps(manifest_data)

print(f"POSTing real kambing NPZ files to {URL}...")
with httpx.Client(timeout=120.0) as client:
    with open(RAD_PATH, "rb") as rad_f, open(GAIN_PATH, "rb") as gain_f:
        files = {
            "manifest": ("manifest.json", manifest_json_str, "application/json"),
            "radiograph_npz": (
                "BED_1783222264263.npz",
                rad_f,
                "application/octet-stream",
            ),
            "gain_npz": ("BED_1783219207291.npz", gain_f, "application/octet-stream"),
        }
        response = client.post(URL, headers=headers, files=files)

print(f"Response Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Response byte size: {len(response.content)}")

if response.status_code != 200:
    print(f"Error response body: {response.text}")
    raise RuntimeError(f"API returned status code {response.status_code}")

# Write DICOM
DICOM_OUT_PATH.write_bytes(response.content)
print(f"Saved real DICOM output to {DICOM_OUT_PATH}")

# Validate with pydicom
ds = pydicom.dcmread(DICOM_OUT_PATH)

print(f"DICOM Rows: {ds.Rows}")
print(f"DICOM Columns: {ds.Columns}")
print(f"DICOM BitsAllocated: {ds.BitsAllocated}")
print(f"DICOM PixelRepresentation: {ds.PixelRepresentation}")

assert ds.Rows == 3053, f"Expected Rows == 3053, got {ds.Rows}"
assert ds.Columns == 4059, f"Expected Columns == 4059, got {ds.Columns}"
assert ds.BitsAllocated == 16, f"Expected BitsAllocated == 16, got {ds.BitsAllocated}"
assert (
    ds.PixelRepresentation == 0
), f"Expected PixelRepresentation == 0, got {ds.PixelRepresentation}"

private_tags = [elem for elem in ds if elem.tag.is_private]
print(f"Private tags count: {len(private_tags)}")
assert len(private_tags) == 0, f"Expected 0 private tags, found {len(private_tags)}"

print("ALL REAL-DATA DICOM ASSERTIONS PASSED SUCCESSFULLY!")
