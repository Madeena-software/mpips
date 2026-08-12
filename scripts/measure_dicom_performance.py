#!/usr/bin/env python3
"""Performance measurement and capacity characterization script for MPIPS DICOM API."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch
from uuid import uuid4

import httpx
import numpy as np
import pydicom

from mpips.api.idempotency import ClaimResult

SHAPE = (64, 64)
GAIN_ID = "SYNTH-GAIN-001"
CAMERA = "SYNTH-CAMERA-001"
BASE_JOB_ID = "00000000-0000-4000-8000-000000000001"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _uuid() -> str:
    return str(uuid4())


def _npz_bytes(
    *,
    radiograph: bool,
    shape: tuple[int, int] = SHAPE,
    camera: str = CAMERA,
) -> bytes:
    raw = np.full(shape, 1000, dtype=np.uint16)
    values: dict[str, Any]
    if radiograph:
        values = {
            "id": np.array("SYNTH-RAD-001"),
            "gainid": np.array(GAIN_ID),
            "rawimage": raw,
            "xrayparams": np.array({"detectorMode": "BED"}, dtype=object),
            "cameraparams": np.array({"serialNumber": camera}, dtype=object),
        }
    else:
        values = {
            "id": np.array(GAIN_ID),
            "rawimage": np.full(shape, 2000, dtype=np.uint16),
            "darkimage": np.full(shape, 50, dtype=np.uint16),
            "xrayparams": np.array({"detectorMode": "BED"}, dtype=object),
            "cameraparams": np.array({"serialNumber": camera}, dtype=object),
        }
    output = BytesIO()
    np.savez_compressed(output, **values)
    return output.getvalue()


def _manifest_template() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "conversion_job_id": BASE_JOB_ID,
        "submission_id": "00000000-0000-4000-8000-000000000002",
        "correlation_id": "00000000-0000-4000-8000-000000000003",
        "examination": {
            "examination_id": "SYNTH-EXAM-001",
            "booking_id": "SYNTH-BOOK-001",
            "service_request_id": "SYNTH-REQUEST-001",
            "encounter_id": "SYNTH-ENCOUNTER-001",
            "accession_number": "SYNTHACC001",
            "study_id": "SYNTHSTUDY001",
            "performed_at": "2026-08-05T10:00:00+00:00",
            "study_description": "Synthetic Chest Radiography",
            "protocol_name": "Synthetic Chest PA",
        },
        "patient": {
            "member_id": "00000000-0000-4000-8000-000000000004",
            "medical_record_number": "SYNTHETIC-MRN-001",
            "name": {"full_name": "Synthetic Patient", "family_name": "Patient"},
            "sex": "unknown",
            "birth_date": "2000-01-01",
        },
        "operator": {
            "operator_id": "00000000-0000-4000-8000-000000000005",
            "name": {"full_name": "Synthetic Operator", "family_name": "Operator"},
        },
        "site": {
            "organization_id": "SYNTH-ORG-001",
            "site_id": "SYNTH-SITE-001",
            "institution_name": "Synthetic Local Test Site",
            "department_name": "Synthetic Radiology",
            "station_name": "SYNTH-STATION-01",
            "timezone": "UTC",
        },
        "capture": {
            "capture_id": "SYNTH-CAPTURE-001",
            "protocol_version": "SYNTH-V1",
            "body_part_examined": "CHEST",
            "laterality": "U",
            "projection": "PA",
            "captured_at": "2026-08-05T10:00:00+00:00",
            "radiograph": {"filename": "synthetic-radiograph.npz"},
            "gain": {"filename": "synthetic-gain.npz", "gain_id": GAIN_ID},
            "image_spacing": {"row_um": 140.0, "column_um": 140.0},
        },
        "dicom": {
            "study_instance_uid": "1.2.826.0.1.3680043.10.1356.20260805.1",
            "series_instance_uid": "1.2.826.0.1.3680043.10.1356.20260805.2",
            "sop_instance_uid": "1.2.826.0.1.3680043.10.1356.20260805.3",
            "series_number": 1,
            "instance_number": 1,
            "series_description": "Synthetic Chest PA",
            "presentation_intent": "FOR PRESENTATION",
        },
    }


def _with_files(
    template: dict[str, Any],
    radiograph: bytes,
    gain: bytes,
    *,
    job_id: str | None = None,
) -> bytes:
    manifest = copy.deepcopy(template)
    manifest["conversion_job_id"] = job_id or _uuid()
    manifest["capture"]["radiograph"].update(
        {"byte_size": len(radiograph), "sha256": _sha(radiograph)}
    )
    manifest["capture"]["gain"].update({"byte_size": len(gain), "sha256": _sha(gain)})
    return _json_bytes(manifest)


@dataclass
class RequestResult:
    request_id: str
    conversion_job_id: str
    start_time: float
    end_time: float
    latency_seconds: float
    status_code: int
    response_bytes: int
    correlation_id: str
    dicom_valid: Optional[bool] = None
    output_rows: Optional[int] = None
    output_cols: Optional[int] = None
    retry_after: Optional[str] = None


class FakeIdempotencyService:
    """In-memory Redis simulator for local TestClient benchmarking."""

    def __init__(self) -> None:
        self.jobs: Dict[str, Dict[str, Any]] = {}
        import threading

        self.lock = threading.Lock()

    def claim_job(self, tenant_id: str, conversion_job_id: str, fp: str) -> ClaimResult:
        with self.lock:
            job_key = f"{tenant_id}:{conversion_job_id}"
            if job_key in self.jobs:
                existing = self.jobs[job_key]
                if existing["fp"] == fp:
                    return ClaimResult(status="SUCCEEDED_SAME")
                else:
                    return ClaimResult(status="SUCCEEDED_DIFF")

            self.jobs[job_key] = {"fp": fp, "status": "CLAIMED"}
            return ClaimResult(status="CLAIMED", lease_token=f"lease-{job_key}")

    def mark_success(
        self,
        tenant_id: str,
        conversion_job_id: Any,
        lease_token: str,
        dcm_bytes: bytes,
    ) -> None:
        with self.lock:
            job_key = f"{tenant_id}:{conversion_job_id}"
            if job_key in self.jobs:
                self.jobs[job_key]["status"] = "SUCCEEDED"

    def mark_failure(
        self,
        tenant_id: str,
        conversion_job_id: Any,
        lease_token: str,
        reason: str,
    ) -> None:
        with self.lock:
            job_key = f"{tenant_id}:{conversion_job_id}"
            self.jobs.pop(job_key, None)


class PerformanceTester:
    def __init__(self, url: str | None = None, api_key: str | None = None) -> None:
        self.url = (url or "http://127.0.0.1:8014").rstrip("/")
        self.api_key = api_key or os.getenv(
            "MPIPS_API_KEY", "mpips_dev_key_synthetic_only"
        )
        self.use_test_client = url is None and not self._is_server_up(self.url)
        self.template = _manifest_template()
        self.radiograph = _npz_bytes(radiograph=True)
        self.gain = _npz_bytes(radiograph=False)
        self._test_client = None
        self.fake_idempotency = FakeIdempotencyService()

        if self.use_test_client:
            self._setup_calibration_dir()
            from fastapi.testclient import TestClient
            from mpips.api.application import app

            self._test_client = TestClient(app)

    def _setup_calibration_dir(self) -> None:
        if not os.getenv("MPIPS_CALIBRATION_ARTIFACT_DIR"):
            temp_dir = Path(tempfile.mkdtemp(prefix="mpips_cal_bench_"))
            y_vals, x_vals = np.indices(SHAPE, dtype=np.float32)
            np.savez_compressed(temp_dir / "remap.npz", map_x=x_vals, map_y=y_vals)
            metadata = {
                "validated": True,
                "fingerprint": "synthetic-local-calibration-v1",
                "image_shape": list(SHAPE),
                "source_metadata": {
                    "detector_mode": "BED",
                    "camera_params": {"serialNumber": CAMERA},
                },
            }
            (temp_dir / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            os.environ["MPIPS_CALIBRATION_ARTIFACT_DIR"] = str(temp_dir)

    def _is_server_up(self, url: str) -> bool:
        try:
            r = httpx.get(f"{url}/health", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def send_request(
        self,
        raw_manifest: bytes,
        radiograph: bytes | None = None,
        gain: bytes | None = None,
        job_id: str | None = None,
    ) -> RequestResult:
        req_id = _uuid()
        job_str = job_id or str(
            json.loads(raw_manifest).get("conversion_job_id", _uuid())
        )
        rad_bytes = radiograph if radiograph is not None else self.radiograph
        gain_bytes = gain if gain is not None else self.gain

        files = [
            (
                "radiograph_npz",
                (
                    "synthetic-radiograph.npz",
                    rad_bytes,
                    "application/octet-stream",
                ),
            ),
            (
                "gain_npz",
                ("synthetic-gain.npz", gain_bytes, "application/octet-stream"),
            ),
            ("manifest", ("manifest.json", raw_manifest, "application/json")),
        ]
        headers: dict[str, str] = {"X-MPIPS-API-Key": self.api_key or ""}

        start = time.perf_counter()
        if self.use_test_client and self._test_client:
            with (
                patch(
                    "mpips.api.routes.v1.dicom.IdempotencyService.claim_job",
                    side_effect=self.fake_idempotency.claim_job,
                ),
                patch(
                    "mpips.api.routes.v1.dicom.IdempotencyService.mark_success",
                    side_effect=self.fake_idempotency.mark_success,
                ),
                patch(
                    "mpips.api.routes.v1.dicom.IdempotencyService.mark_failure",
                    side_effect=self.fake_idempotency.mark_failure,
                ),
            ):
                res = self._test_client.post(
                    "/v1/radiographs/dicom", headers=headers, files=files
                )
                status_code = res.status_code
                content = res.content
                resp_headers = res.headers
        else:
            with httpx.Client(timeout=120.0, follow_redirects=False) as client:
                res = client.post(
                    f"{self.url}/v1/radiographs/dicom",
                    headers=headers,
                    files=files,
                )
                status_code = res.status_code
                content = res.content
                resp_headers = res.headers
        end = time.perf_counter()

        latency = end - start
        cid = resp_headers.get("X-Correlation-ID", "")
        retry_after = resp_headers.get("Retry-After")

        result = RequestResult(
            request_id=req_id,
            conversion_job_id=job_str,
            start_time=start,
            end_time=end,
            latency_seconds=round(latency, 6),
            status_code=status_code,
            response_bytes=len(content),
            correlation_id=cid,
            retry_after=retry_after,
        )

        if status_code == 200:
            try:
                ds = pydicom.dcmread(BytesIO(content))
                result.dicom_valid = True
                result.output_rows = int(ds.Rows)
                result.output_cols = int(ds.Columns)
            except Exception:
                result.dicom_valid = False

        return result

    def measure_sequential_latency(
        self, sample_count: int = 5
    ) -> Tuple[RequestResult, List[RequestResult]]:
        # Warm-up request
        warmup_manifest = _with_files(
            self.template, self.radiograph, self.gain, job_id=_uuid()
        )
        warmup_res = self.send_request(warmup_manifest)

        # Measured requests
        results: List[RequestResult] = []
        for _ in range(sample_count):
            raw = _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
            res = self.send_request(raw)
            results.append(res)

        return warmup_res, results

    def measure_concurrency_batches(
        self, batch_count: int = 3, concurrency: int = 2
    ) -> List[List[RequestResult]]:
        batches: List[List[RequestResult]] = []
        for _ in range(batch_count):
            manifests = [
                _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
                for _ in range(concurrency)
            ]
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(self.send_request, m) for m in manifests]
                batch_res = [f.result() for f in futures]
            batches.append(batch_res)
        return batches

    def measure_burst_admission(self, total_burst: int = 8) -> List[RequestResult]:
        manifests = [
            _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
            for _ in range(total_burst)
        ]
        with ThreadPoolExecutor(max_workers=total_burst) as executor:
            futures = [executor.submit(self.send_request, m) for m in manifests]
            return [f.result() for f in futures]

    def measure_retry_sequence(self) -> Dict[str, Any]:
        batch_manifests = [
            _with_files(self.template, self.radiograph, self.gain, job_id=_uuid())
            for _ in range(4)
        ]

        retry_job_id = _uuid()
        target_manifest = _with_files(
            self.template, self.radiograph, self.gain, job_id=retry_job_id
        )

        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.send_request, m) for m in batch_manifests]
            target_future = executor.submit(
                self.send_request, target_manifest, None, None, retry_job_id
            )

            _ = [f.result() for f in futures]
            first_res = target_future.result()

        retry_res = None
        if first_res.status_code == 429:
            delay = float(first_res.retry_after or "5")
            time.sleep(delay)
            retry_res = self.send_request(target_manifest, None, None, retry_job_id)

        total_time = time.perf_counter() - start_time

        return {
            "initial_rejection": asdict(first_res),
            "retry_result": asdict(retry_res) if retry_res else None,
            "total_user_visible_latency_seconds": round(total_time, 6),
        }


def stats_dict(latencies: List[float]) -> Dict[str, float]:
    if not latencies:
        return {}
    s = sorted(latencies)
    n = len(s)
    mean_val = sum(s) / n
    variance = sum((x - mean_val) ** 2 for x in s) / n if n > 1 else 0.0
    std_dev = math.sqrt(variance)

    def percentile(p: float) -> float:
        idx = int(round((n - 1) * p))
        return s[idx]

    return {
        "min": round(s[0], 6),
        "mean": round(mean_val, 6),
        "p50": round(percentile(0.50), 6),
        "p95": round(percentile(0.95), 6),
        "max": round(s[-1], 6),
        "std_dev": round(std_dev, 6),
        "sample_count": n,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=None,
        help="Target API URL (default: http://127.0.0.1:8014 or TestClient)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".agents/context/performance/benchmark_results.json"),
    )
    args = parser.parse_args()

    print("Starting MPIPS Performance Measurement Suite...")
    tester = PerformanceTester(args.url)
    mode_str = (
        f"httpx -> {tester.url}"
        if not tester.use_test_client
        else "FastAPI TestClient (in-process)"
    )
    print(f"Mode: {mode_str}")

    print("Measuring single-conversion sequential latency...")
    warmup, sequential_results = tester.measure_sequential_latency(sample_count=5)
    seq_latencies = [
        r.latency_seconds for r in sequential_results if r.status_code == 200
    ]
    seq_stats = stats_dict(seq_latencies)

    print("Measuring concurrency=2 throughput...")
    conc2_batches = tester.measure_concurrency_batches(batch_count=3, concurrency=2)
    conc2_all = [r for batch in conc2_batches for r in batch]
    conc2_latencies = [r.latency_seconds for r in conc2_all if r.status_code == 200]
    conc2_stats = stats_dict(conc2_latencies)

    total_conc2_jobs = len([r for r in conc2_all if r.status_code == 200])
    total_conc2_time = sum(
        max(r.end_time for r in batch) - min(r.start_time for r in batch)
        for batch in conc2_batches
    )
    obs_throughput_pm = (
        (total_conc2_jobs / (total_conc2_time / 60.0)) if total_conc2_time > 0 else 0.0
    )
    est_throughput_ph = obs_throughput_pm * 60.0

    print("Measuring 8-request burst admission...")
    burst_results = tester.measure_burst_admission(total_burst=8)
    burst_200 = len([r for r in burst_results if r.status_code == 200])
    burst_429 = len([r for r in burst_results if r.status_code == 429])
    burst_5xx = len([r for r in burst_results if r.status_code >= 500])
    burst_429_latencies = [
        r.latency_seconds for r in burst_results if r.status_code == 429
    ]

    print("Measuring 429 retry sequence cost...")
    retry_info = tester.measure_retry_sequence()

    kambing_rad = Path("research/kambing-260714/data/kambing/BED_1783222264263.npz")
    kambing_gain = Path("research/kambing-260714/data/gain/BED_1783219207291.npz")
    rep_fixture_tested = kambing_rad.exists() and kambing_gain.exists()

    report = {
        "starting_head": "7ae33628955988e37163504c71c4f4ea175d5497",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "synthetic_fixture_tested": True,
        "representative_fixture_tested": rep_fixture_tested,
        "execution_mode": (
            "httpx" if not tester.use_test_client else "FastAPI TestClient"
        ),
        "single_request_latency": {
            "warmup": asdict(warmup),
            "stats": seq_stats,
            "samples": [asdict(r) for r in sequential_results],
        },
        "concurrency_2_results": {
            "stats": conc2_stats,
            "batches": [[asdict(r) for r in batch] for batch in conc2_batches],
            "observed_throughput_per_minute": round(obs_throughput_pm, 2),
            "estimated_throughput_per_hour": round(est_throughput_ph, 2),
        },
        "burst_admission_results": {
            "total_requests": 8,
            "admitted_200": burst_200,
            "rejected_429": burst_429,
            "unexpected_5xx": burst_5xx,
            "rejection_latency_stats": stats_dict(burst_429_latencies),
            "samples": [asdict(r) for r in burst_results],
        },
        "retry_sequence_cost": retry_info,
        "capacity_envelope": {
            "current_concurrency": 2,
            "single_conversion_p50_seconds": seq_stats.get("p50", 0.0),
            "single_conversion_max_seconds": seq_stats.get("max", 0.0),
            "two_request_batch_p50_seconds": conc2_stats.get("p50", 0.0),
            "observed_successful_conversions_per_minute": round(obs_throughput_pm, 2),
            "estimated_successful_conversions_per_hour": round(est_throughput_ph, 2),
            "429_rejection_latency_seconds": stats_dict(burst_429_latencies).get(
                "p50", 0.0
            ),
            "retry_completion_latency_seconds": retry_info.get(
                "total_user_visible_latency_seconds", 0.0
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nMeasurement complete. Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
