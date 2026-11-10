# MPIPS — Standalone Binary Review and Real TRX Calibration Integration Qualification Report

**Document ID:** EV-STANDALONE-REAL-TRX-001  
**Status:** Independent Review Remediation & Offline Integrated Acceptance (Review Pending)  
**Date:** 2026-11-10  
**Target Environment:** Ubuntu 24.04 LTS (`noble`) x86_64 (`glibc 2.39`, Linux 5.15/6.x)  
**Accepted Main Baseline:** `8dd42a7106d13ff602f41a57b726668066791bec`  
**Standalone Qualification Baseline:** `cbf2b24ba4fb8f2b5fc25b6a86f381ba7cf5f4b1`  
**Staging Hardening Baseline:** `b7d0a10a600ccc1215e529c5a6bbc05036ab2998`  
**Integration Merge Commit (`feat/offline-integrated-elf-acceptance`):** `90fa785b1607d6d63fe39e3e2557468e64da4717`  
**Governing Task:** `.agents/tasks/mpips-standalone-bin-real-trx-integration.md` (Revision 1.2)  
**Result:** **OFFLINE_INTEGRATED_ELF_PASS (Container & Local Env-Isolated Qualification) — Independent Review in Progress**

---

## 1. Executive Summary

This qualification report records the review, remediation, Ubuntu 24.04 container qualification, and offline integrated update-server acceptance of the self-contained Linux ELF executable **`mpips-runtime.bin`** embedded with the designated **real TRX detector geometric calibration profile**.

- **Executable:** `dist-experimental/mpips-runtime.bin` (local build candidate only; not distributed or released on GitHub)
- **Format:** ELF 64-bit LSB executable, x86-64, dynamically linked, stripped.
- **File Size:** `241,288,024` bytes (~230.1 MiB).
- **Verified Candidate SHA-256 Digest:**
  ```text
  189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937
  ```
  *(Recorded in `dist-experimental/mpips-runtime.bin.sha256`; supersedes the earlier `236,532,616`-byte candidate `8ef48229d72adaa4eb9df832a5315e2ecf42abb448f78c2674c330d964004669`).*
- **GLIBC Symbol Version Requirements (`objdump -T` / `readelf -V`):**
  1. **ELF Bootloader (`dist-experimental/mpips-runtime.bin`):** Requires `GLIBC_2.2.5`, `GLIBC_2.3`, `GLIBC_2.3.4`, `GLIBC_2.4`, `GLIBC_2.7`, `GLIBC_2.14` (maximum bootloader symbol version: `GLIBC_2.14`).
  2. **Bundled Shared Libraries (`152` `.so` libraries in PyInstaller archive):** Require symbol versions `GLIBC_2.2.5` through `GLIBC_2.38` (maximum bundled shared-library symbol version: **`GLIBC_2.38`**, observed in `libstdc++.so.6`).
  3. **Execution on Ubuntu 24.04 LTS (`noble`, `glibc 2.39`):** Confirmed compatible on Ubuntu 24.04.2 LTS (`Ubuntu GLIBC 2.39-0ubuntu8.4`), which satisfies both the outer bootloader (`<= GLIBC_2.14`) and all bundled native libraries (`<= GLIBC_2.38`).
- **Ubuntu 24.04 Container & Clean-Environment Qualification:**
  - **Container Image Identity:** Qualified against `ubuntu:24.04` (Ubuntu 24.04 LTS `noble` x86_64, `glibc 2.39`). An immutable Docker image digest (`sha256:...`) was not recorded in the original qualification log and is not claimed here because the local Docker daemon was offline during evidence reconciliation.
  - **No External Python Runtime Required:** Confirmed inside a clean container and via scrubbed environment invocation (`/usr/bin/env -i PATH=/usr/bin:/bin ./mpips-runtime.bin --version` returning `{"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}` and `convert` from `/tmp` with zero `PYTHON*` or `.venv` variables and no system `python3` invoked by the binary).
  - **Physical Hardware Qualification:** **NOT CLAIMED / PENDING.** Qualification was performed in container and WSL 2 environments only, not on physical bare-metal hospital Grabber hardware.
- **Designated Real TRX Asset Provenance:**
  - Archive: `trx-calibration-606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d.tar.gz`
  - Archive SHA-256: `2871e78f61676d36a03e8c06c172b49eed42d140c79e4b1970e141b70d557556` (exact match verified by pre-build gate)
  - Remap SHA-256: `32796276833f7c6a8acb1ecc82aebe5f6dac1147073e6c49b4feaf34146da893`
  - Fingerprint: `606db560c391764b24fa6257a01a8afb38380b83bf83ea7bd6a30b299861547d`
  - Profile ID: `GOTRI-TRX-001`, Detector Mode: `TRX`, Camera Serial: `DA5234480`, Camera Model: `MV-CH120-10UM`, Image Shape: `3000 x 4096`
  - Embedded BED Profile: `SYNTHETIC-EMBEDDED-BED-CALIBRATION-V1` (`48 x 64`, `SYNTHETIC_DEVELOPMENT_ONLY`, remap SHA-256 `57749f83ba9bd0704347a0c41cd4e454ed87829c00314f4948b3e9f03d2a7ddc`)
  - Scope: `LOCAL_REAL_TRX_ACCEPTANCE`
- **Protected Converter:** `mpips/conversion/tiff_json_to_dcm.py` verified unmodified (SHA-256 `a4a308661ebe8e418bbecd6f30af1b59eae3ee019fc4256b03b323be3c6706e0`).
- **Release Status:** Gate **G10 remains NOT RELEASED**. No external distribution or PR merge is authorized.

---

## 2. Separate Acceptance Verdicts

| Dimension | Verdict | Evidence / Observed Result |
|---|---|---|
| **One-file Standalone ELF Build** | **PASS** | Dynamic PyInstaller specs (`SPECPATH`-relative) preceded by `prepare_calibration_bundle.py` validation gate successfully built `241,288,024`-byte (~230.1 MiB) stripped ELF binary into `dist-experimental/mpips-runtime.bin`. |
| **Embedded Real TRX Calibration Provenance** | **PASS** | Source archive hash verified against `2871e78f...`. Embedded metadata and remap array validated with SHA-256 integrity checks directly by worker child process. Large assets excluded from Git. |
| **Full-Resolution Synthetic TRX Conversion** | **PASS** | 3000 x 4096 synthetic inputs processed through real TRX geometry into valid DICOM with 4096 x 3000 rotated uint16 pixel array in ~53s (~24.5 MiB DICOM). |
| **Synthetic BED Regression** | **PASS** | Small synthetic BED test fixtures continue to convert without `--calibration` and pass regression invariants. Deterministic synthetic BED coordinate grid generated cleanly. |
| **Grabber Adapter Compatibility** | **PASS** | `MPIPSSubprocessAdapter` enforces contract differences: interface negotiation verifies version; interface 1 requires calibration; interface 2-experimental uses embedded calibration and strictly rejects external `--calibration`. 27/27 adapter unit tests passed. |
| **Clean-Host Environment Isolation** | **PASS (Env-Isolated) / PENDING (Physical Clean Host)** | Subprocess execution verified under environment isolation (`env -i PATH=/usr/bin:/bin` from `/tmp`) with all Python/repo environment variables scrubbed. Physical or containerized execution without Python installed remains pending. |
| **Negative & Security Cases** | **PASS** | Strict fail-closed verification of camera serial identity, detector mode, remap hash, and fingerprint. Negative tests for wrong/missing serial, bad fingerprint, altered remap, missing remap, substitute TRX profile bypass attempts, external calibration override rejection in interface 2, and unhandled Linux RLIMIT_CPU failure all pass. File mode `0600` enforced. |
| **Repository Regression & CI** | **PASS (CI Suite) / LOCAL ONLY (.bin Execution)** | Standard CI suite passes completely on GitHub Actions (Black, Flake8, Mypy regression gate, pytest, Docker builds, smoke tests). Standalone binary execution is qualified strictly locally with `MPIPS_STRICT_QUALIFICATION=1`. |

---

## 3. Calibration Contract & Selection Safety

1. **Deterministic Matching & Fail-Closed Behavior:**
   - Radiograph metadata must match detector mode (`TRX`) and camera serial (`DA5234480`).
   - If radiograph specifies an incompatible serial (e.g., `WRONG-SERIAL-9999`), the internal worker raises `NPZ_VALIDATION_ERROR` and the top-level `mpips-runtime.bin` CLI exits with code `2` (`INVALID_INPUT`).
   - Top-level `mpips-runtime.bin` CLI exit and JSON `code` contract:
     - `0` -> `OK`
     - `2` -> `INVALID_INPUT`
     - `3` -> `INPUT_NOT_FOUND`
     - `4` -> `OUTPUT_EXISTS`
     - `5` -> `CONVERSION_TIMEOUT`
     - `6` -> `IO_ERROR`
     - `7` -> `CONVERSION_FAILED`
   - If radiograph input array dimensions do not match the calibration image shape (`3000 x 4096`), conversion fails immediately before processing.
   - Ambiguous profiles (multiple candidates with conflicting serials) fail closed.
   - Any attempt to supply a substitute TRX profile with altered profile ID, wrong fingerprint, absent camera serial, or altered remap payload fails before image processing.
2. **Gain Separation:**
   - Per-acquisition `gain.npz` remains an external requirement; its dark/flat shapes and detector mode are verified against the radiograph.
3. **No External Fallback:**
   - The frozen executable bundle checks `sys._MEIPASS` and does not fall back to local disk paths or identity remapping. Interface 2-experimental strictly rejects explicit external `--calibration` arguments.

---

## 4. Grabber Adapter Version-Aware Integration

`scripts/grabber_subprocess_adapter.py` defines:
```python
SUPPORTED_INTERFACE_VERSION = "1"
EXPERIMENTAL_INTERFACE_VERSION = "2-experimental"
SUPPORTED_INTERFACE_VERSIONS = {SUPPORTED_INTERFACE_VERSION, EXPERIMENTAL_INTERFACE_VERSION}
```
When invoking `convert`, interface negotiation occurs via `negotiate_interface()` or explicit `expected_interface_version`. Interface 1 requires an explicit external calibration directory. Interface 2-experimental requires embedded calibration and rejects external `--calibration`. Sanitized JSON responses and error translations are fully preserved.

---

## 5. Performance and Resource Metrics

- **Binary Cold Startup:** ~2.68s (self-extraction of bundle to `/tmp/_MEIxxxxxx`).
- **Full-Resolution (3000 x 4096) Conversion Duration:** ~53.1s.
- **Output DICOM File Size:** 24,577,268 bytes.
- **Output File Permissions:** `0600` (read/write by owner only).
- **Runtime Host Libraries (`ldd`):** `libdl.so.2`, `libz.so.1`, `libpthread.so.0`, `libc.so.6`, `ld-linux-x86-64.so.2` (standard Ubuntu 24.04).

---

## 6. Test Suite Evidence

### Standalone Qualification Suite
Command: `MPIPS_STRICT_QUALIFICATION=1 .venv/bin/pytest tests/test_standalone_bin_qualification.py -v`
```text
tests/test_standalone_bin_qualification.py::test_bin_version PASSED                      [  8%]
tests/test_standalone_bin_qualification.py::test_bin_convert_bed_synthetic_no_calibration PASSED [ 16%]
tests/test_standalone_bin_qualification.py::test_bin_convert_trx_full_resolution_no_calibration PASSED [ 25%]
tests/test_standalone_bin_qualification.py::test_bin_via_adapter_no_calibration PASSED [ 33%]
tests/test_standalone_bin_qualification.py::test_bin_negative_camera_serial_mismatch PASSED [ 41%]
tests/test_standalone_bin_qualification.py::test_bin_negative_input_not_found PASSED       [ 50%]
tests/test_standalone_bin_qualification.py::test_bin_negative_invalid_manifest PASSED      [ 58%]
tests/test_standalone_bin_qualification.py::test_bin_negative_output_exists PASSED        [ 66%]
tests/test_standalone_bin_qualification.py::test_bin_negative_dangling_symlink PASSED     [ 75%]
tests/test_standalone_bin_qualification.py::test_bin_negative_detector_mode_mismatch PASSED [ 83%]
tests/test_standalone_bin_qualification.py::test_worker_negative_real_trx_validation_cases PASSED [ 91%]
tests/test_standalone_bin_qualification.py::test_bin_rejects_explicit_calibration_override_in_interface_2 PASSED [100%]
======================== 12 passed in 114.54s ========================
```

### Subprocess Adapter Suite
Command: `.venv/bin/pytest tests/test_grabber_subprocess_adapter.py -v`
```text
============================= 27 passed in 10.82s ==============================
```

### Packaged Grabber E2E Regression
Command: `.venv/bin/pytest tests/test_packaged_grabber_e2e.py -v`
```text
============================= 11 passed in 31.42s ==============================
```

### Full Local Test Suite
Command: `.venv/bin/pytest -q`
```text
1076 passed, 315 warnings in 442.57s
```

### Canonical Converter Immutability
Command: `.venv/bin/pytest tests/test_converter_protection.py -v`
```text
============================== 1 passed in 0.03s ===============================
```

### Offline Integrated Update-Server & Real ELF Acceptance
Command: `MPIPS_STRICT_QUALIFICATION=1 .venv/bin/pytest tests/test_grabber_update_flow_simulation.py -v`
```text
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_successful_update_and_conversion PASSED [  9%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_unauthenticated_request PASSED [ 18%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_invalid_token PASSED [ 27%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_older_or_equal_sequence PASSED [ 36%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_invalid_signature_before_download PASSED [ 45%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_corrupted_sha256_preserves_runtime PASSED [ 54%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_incompatible_platform PASSED [ 63%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_failed_self_check_preserves_runtime PASSED [ 72%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_rejects_failed_synthetic_conversion_preserves_runtime PASSED [ 81%]
tests/test_grabber_update_flow_simulation.py::test_protocol_simulation_network_isolation_no_live_egress PASSED [ 90%]
tests/test_grabber_update_flow_simulation.py::test_real_update_server_and_real_elf_offline_integrated_acceptance PASSED [100%]
======================== 11 passed in 95.52s (0:01:35) =========================
```
- **Distinction Between Mock Protocol Simulation Tests (1–10) and Genuine ELF + Real Server Acceptance Test (11):**
  - **Mock Protocol Tests (`test_protocol_simulation_*`, 10 tests):** Use `MockUpdateServerFixture` and lightweight mock executable scripts (`_create_mock_runtime_script`) to test protocol edge cases: successful mock promotion, unauthenticated request rejection (`401`), invalid token rejection (`401`), older/equal sequence rejection, invalid Ed25519 signature rejection prior to download, corrupted SHA-256 download rejection, incompatible platform rejection (`422`), failed `--version` self-check rejection, failed synthetic conversion rejection, and Python-level `socket.create_connection` loopback egress blocking.
  - **Genuine ELF + Real Update-Server Test (`test_real_update_server_and_real_elf_offline_integrated_acceptance`, 1 test):**
    1. Hosted the real `mpips.update_server.app:create_update_server_app` (`ReleaseRegistry`, `ClientAuthenticator`, `MinIOArtifactStore`) backed by `LocalIsolatedS3Client` (simulated local loopback S3 storage, not a live MinIO instance) with a disposable Ed25519 keypair and synthetic `staging-reader` bearer token.
    2. Verified initial `status: "no_release"` (`run_checks(..., mode="infra") is True`, `mode="distribution"` is `False`, and first-bootstrap rejection when no valid runtime is installed).
    3. Registered, authorized, and promoted the genuine `241,288,024`-byte `dist-experimental/mpips-runtime.bin` (`189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) as `release_id: "0.1.0-real-elf-staging-r11"` (`sequence: 11`), and verified `run_checks(..., mode="distribution") is True`.
    4. Executed `simulate_grabber_update_flow` to discover `/mpips/staging/latest.json`, verify the 64-byte Ed25519 signature over `signed_metadata_b64` and all 12 `SIGNED_METADATA_KEYS`, call `/mpips/staging/releases/0.1.0-real-elf-staging-r11/download`, validate the loopback storage host and `StrictNoRedirectHandler`, stream all `241,288,024` bytes, verify exact byte length and SHA-256, run `--version` and synthetic BED smoke conversion, and atomically replace `installed_bin` (`os.replace`).
    5. Executed the downloaded ELF `--version` in a scrubbed environment (`/usr/bin/env -i PATH=/usr/bin:/bin`), confirming exact JSON output `{"code": "OK", "interface_version": "2-experimental", "runtime_version": "0.1.0", "status": "ok"}`.
    6. Parsed a synthetic SIMRS response (`visit_id = "SYNTHETIC-VISIT-2026-0777"`, `no_rkm_medis = "SYNTHETIC-MRN-0777"`), verified `SIMRSConfirmationRequiredError` when `confirmed=False`, and generated confirmed BED (`48 x 64`) and full-resolution TRX (`3000 x 4096`, `DA5234480`, `MV-CH120-10UM`) manifests and NPZ inputs.
    7. Invoked the downloaded real ELF without `--calibration` to produce both BED DICOM (`(48, 64)` `uint16`, mode `0600`) and full-resolution TRX DICOM (`(4096, 3000)` `uint16`, mode `0600`, `Modality = "DX"`, `PatientID = "SYNTHETIC-MRN-0777"`).
    8. Verified deterministic CLI failure codes on the downloaded real ELF: external `--calibration` override rejected with exit code `2` (`INVALID_INPUT`), existing output path rejected with exit code `4` (`OUTPUT_EXISTS`), and missing input file rejected with exit code `3` (`INPUT_NOT_FOUND`).
    9. Registered a subsequent `release_id: "0.1.0-real-elf-staging-r12"` (`sequence: 12`), injected stream corruption (`srv.corrupt_storage_stream = True`), confirmed `GrabberUpdateError` (`SHA-256 mismatch`), verified cleanup of `candidate_runtime.tmp`, and confirmed the installed `sequence: 11` real ELF remained intact (`241,288,024` bytes, SHA-256 `189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) and passed `adapter.check_version()`.
  - **Explicit Simulation Boundaries & Live Infrastructure Evidence:**
    1. **Network Isolation Scope:** `test_protocol_simulation_network_isolation_no_live_egress` monkeypatches Python's `socket.create_connection` to allow only loopback addresses (`127.0.0.1`, `localhost`, `::1`), verifies that non-loopback connection attempts (`198.51.100.1:443`) raise `RuntimeError`, and confirms that `simulate_grabber_update_flow` targets only the requested loopback endpoint. Other tests in `test_grabber_update_flow_simulation.py` configure loopback URLs (`http://127.0.0.1:<port>`) without a global socket monkeypatch, and none of these tests enforce kernel-level network namespace isolation (`unshare -rn`).
    2. **MinIO S3 Storage Scope:** The offline acceptance test uses `LocalIsolatedS3Client` rather than a live MinIO server. Read-only unauthenticated `HEAD https://s3.mhcsgo.cloud/mpips-dev-bucket/` returns HTTP `403 Forbidden` (`AccessDenied`), which is an access-denied result confirming that the S3 endpoint is reachable over HTTPS and does not allow anonymous public access; HTTP `403` is **not** independent proof that `mpips-dev-bucket` exists or contains no artifacts.
    3. **Live Deployment Identity:** GitHub Actions history (`deploy-staging-update-server.yml` Run #4 on `feat/mpips-staging-binary-distribution` @ `6976961e9bf6a3e1631180bc56a6e9de1da4840b`) indicates the last workflow-deployed staging image, but deployment identity inferred from GitHub Actions history remains **provisional** until confirmed against the live running container and image digest (`docker inspect`) on the staging host.
    4. **Grabber Updater Scope:** The test harness does not implement durable `state.json` persistence with `fsync` or post-activation rollback (because activation only occurs after pre-promotion `--version` and synthetic smoke conversion succeed).

---

## 7. Controlled Staging Deployment & MinIO Publication Runbook (Requires Separate Owner Authorizations)

> **CRITICAL GATE SEPARATION:**
> - **Gate A (Staging Hardening Deployment Authorization):** Required before updating `feat/mpips-staging-binary-distribution` or dispatching `.github/workflows/deploy-staging-update-server.yml` (remember: pushing to `feat/mpips-staging-binary-distribution` automatically triggers a GitHub Actions deployment on the self-hosted `[self-hosted, production]` runner).
> - **Gate B (Controlled Staging Publication Authorization):** Required separately *after* Gate A succeeds and live container/key/sequence state is confirmed before uploading `mpips-runtime.bin` to private MinIO or promoting a staging release.
> - **Gate G10 (Clinical / External Release Gate):** Remains **NOT RELEASED**.

### 7.1 Gate A: Provision Dedicated Secret & Deploy Hardened Staging Update Server (Port `8015` Only)

1. **Provision Dedicated GitHub Actions Secret (Owner Action):**
   - Create repository secret `MPIPS_UPDATE_STAGING_READER_TOKEN` in `Madeena-software/mpips` with a high-entropy bearer token dedicated strictly to staging update discovery/download (distinct from clinical `MPIPS_API_KEY`).
   - `.github/workflows/deploy-staging-update-server.yml` has zero fallback to `secrets.MPIPS_API_KEY` and fails in `Validate dedicated staging credentials and environment` before writing `/var/www/mpips-runtime/update-server/.env.staging` or touching Docker services if `MPIPS_UPDATE_STAGING_READER_TOKEN` is absent.
2. **Deploy Hardened Update Server (Only After Gate A Approval):**
   - Promote the approved commit to `feat/mpips-staging-binary-distribution` (or run `deploy-staging-update-server.yml`).
   - Confirm on the staging host that the running container identity matches the expected commit image (resolving the provisional GitHub Actions inference):
     ```bash
     docker inspect mpips-update-staging-mpips-update-server-1 \
       --format 'Image={{.Config.Image}} ImageID={{.Image}} Status={{.State.Status}}'
     ```
   - Confirm that `/var/www/mpips-runtime/update-server/release-public.pem`, `/var/www/mpips-runtime/update-server/staging-signing-private.pem`, and `/var/www/mpips-runtime/update-server/state/.bootstrapped` are intact and consistent, and that clinical API `http://127.0.0.1:8014/health` returns `200 OK`.

### 7.2 Gate B Step 1: Safe Environment Loading & Live Registry / Sequence Inspection

Do **not** blindly `source /var/www/mpips-runtime/update-server/.env.staging` as a shell script, and do **not** assume a host `.venv/bin/python` exists on the staging host. Execute administrative registry operations inside a one-off container using the deployed `mpips-api:${MPIPS_VERSION}` image (which has `/app/.venv/bin/python` and `mpips.update_server` preinstalled) with `--env-file /var/www/mpips-runtime/update-server/.env.staging`.

Inspect the live channel sequence, highest allocated sequence, and any registered (including unpromoted or revoked) releases:

```bash
set -Eeuo pipefail
BASE_DIR="/var/www/mpips-runtime/update-server"
ENV_FILE="$BASE_DIR/.env.staging"
IMAGE_TAG="$(grep -E '^MPIPS_VERSION=' "$ENV_FILE" | cut -d= -f2-)"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file "$ENV_FILE" \
  -v "$BASE_DIR/state:/var/lib/mpips-update-server/state:ro" \
  -v "$BASE_DIR/release-public.pem:/etc/mpips-update-server/release-public.pem:ro" \
  --entrypoint python \
  "mpips-api:${IMAGE_TAG}" -c '
import json
from pathlib import Path
from mpips.update_server.minio_adapter import MinIOArtifactStore
from mpips.update_server.registry import ReleaseRegistry

pub_pem = Path("/etc/mpips-update-server/release-public.pem").read_bytes()
reg = ReleaseRegistry(
    state_dir=Path("/var/lib/mpips-update-server/state"),
    public_key_pem=pub_pem,
    artifact_store=MinIOArtifactStore(),
)
current_seq = reg.get_current_sequence()
highest_seq = reg.get_highest_allocated_sequence()
releases = [
    {
        "release_id": r.release_id,
        "sequence": r.sequence,
        "authorization_state": r.authorization_state,
        "sha256": r.sha256,
        "size_bytes": r.size_bytes,
    }
    for r in reg.list_releases()
]
print(json.dumps({
    "current_promoted_sequence": current_seq,
    "highest_allocated_sequence": highest_seq,
    "next_safe_sequence": highest_seq + 1,
    "registered_releases": releases,
}, indent=2, sort_keys=True))
'
```

### 7.3 Gate B Step 2: Fix Publication Transaction Parameters & Verify Local Candidate ELF

Fix the exact transaction variables for the approved publication so that registration, verification, and promotion reference the exact same `TARGET_RELEASE_ID`, `EXPECTED_CURRENT_SEQ`, and `TARGET_SEQ`:

```bash
set -Eeuo pipefail
CANDIDATE_BIN="/tmp/mpips-staging-candidate/mpips-runtime.bin"
test "$(stat -c '%s' "$CANDIDATE_BIN")" = "241288024"
echo "189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937  $CANDIDATE_BIN" | sha256sum -c -

# Set from Step 1 inspection output:
EXPECTED_CURRENT_SEQ=0          # Must match current_promoted_sequence from Step 1
TARGET_SEQ=1                    # Must equal highest_allocated_sequence + 1 from Step 1
TARGET_RELEASE_ID="0.1.0-20261110-seq${TARGET_SEQ}"
SOURCE_COMMIT="cbf2b24ba4fb8f2b5fc25b6a86f381ba7cf5f4b1"
```

### 7.4 Gate B Step 3: Stage & Upload Release Bundle with Full Stored Binary SHA-256 Verification (`promote=False`)

`ReleaseRegistry.register_and_upload_release(..., authorize=True, promote=False)` uploads `release.json`, `release.sig`, and `mpips-runtime.bin` to `s3://mpips-dev-bucket/staging/ubuntu-24.04-x86_64/releases/${TARGET_RELEASE_ID}/`, immediately streams back the stored MinIO binary via `MinIOArtifactStore.verify_release_objects(..., verify_binary_sha256=True)` to verify both exact byte length (`241,288,024`) and SHA-256 (`189baaeff2dd6f5eb96e7dac984a63ea1e2cc47e54158539cc77d7d5d0fae937`) against the signed metadata, and records the release as `authorized` without advancing the channel pointer:

```bash
set -Eeuo pipefail
BASE_DIR="/var/www/mpips-runtime/update-server"
ENV_FILE="$BASE_DIR/.env.staging"
IMAGE_TAG="$(grep -E '^MPIPS_VERSION=' "$ENV_FILE" | cut -d= -f2-)"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file "$ENV_FILE" \
  -e TARGET_RELEASE_ID="$TARGET_RELEASE_ID" \
  -e TARGET_SEQ="$TARGET_SEQ" \
  -e SOURCE_COMMIT="$SOURCE_COMMIT" \
  -v "$BASE_DIR/state:/var/lib/mpips-update-server/state:rw" \
  -v "$BASE_DIR/release-public.pem:/etc/mpips-update-server/release-public.pem:ro" \
  -v "$BASE_DIR/staging-signing-private.pem:/etc/mpips-update-server/staging-signing-private.pem:ro" \
  -v "/tmp/mpips-staging-candidate/mpips-runtime.bin:/tmp/mpips-runtime.bin:ro" \
  --entrypoint python \
  "mpips-api:${IMAGE_TAG}" -c '
import hashlib, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from mpips.update_server.minio_adapter import MinIOArtifactStore
from mpips.update_server.registry import ReleaseRegistry
from mpips.update_server.release_metadata import (
    canonical_metadata_bytes,
    create_elf_release_metadata,
    sign_metadata_bytes,
)

bin_path = Path("/tmp/mpips-runtime.bin")
pub_pem = Path("/etc/mpips-update-server/release-public.pem").read_bytes()
priv_pem = Path("/etc/mpips-update-server/staging-signing-private.pem").read_bytes()

store = MinIOArtifactStore()
reg = ReleaseRegistry(
    state_dir=Path("/var/lib/mpips-update-server/state"),
    public_key_pem=pub_pem,
    artifact_store=store,
)

release_id = os.environ["TARGET_RELEASE_ID"]
target_seq = int(os.environ["TARGET_SEQ"])
source_commit = os.environ["SOURCE_COMMIT"]

metadata = create_elf_release_metadata(
    binary_path=bin_path,
    release_id=release_id,
    version="0.1.0",
    sequence=target_seq,
    source_commit=source_commit,
    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
)
meta_bytes = canonical_metadata_bytes(metadata)
sig_bytes = sign_metadata_bytes(meta_bytes, priv_pem)

record = reg.register_and_upload_release(
    binary_path=bin_path,
    metadata_bytes=meta_bytes,
    signature_bytes=sig_bytes,
    authorize=True,
    promote=False,
)
print(json.dumps({
    "action": "registered_and_uploaded",
    "release_id": record.release_id,
    "sequence": record.sequence,
    "sha256": record.sha256,
    "size_bytes": record.size_bytes,
    "object_key": record.artifact_object_key,
    "authorization_state": record.authorization_state,
    "pubkey_sha256": hashlib.sha256(pub_pem).hexdigest(),
}, sort_keys=True))
'
```

### 7.5 Gate B Step 4: Pre-Promotion Checksum Verification & Atomic Channel Promotion

`ReleaseRegistry.promote_release()` re-verifies the Ed25519 signature, compares `expected_current_sequence`, and runs `MinIOArtifactStore.verify_release_objects(..., verify_binary_sha256=True)` to confirm the complete stored ELF SHA-256 in MinIO before updating the `staging/ubuntu-24.04-x86_64` channel pointer:

```bash
set -Eeuo pipefail
BASE_DIR="/var/www/mpips-runtime/update-server"
ENV_FILE="$BASE_DIR/.env.staging"
IMAGE_TAG="$(grep -E '^MPIPS_VERSION=' "$ENV_FILE" | cut -d= -f2-)"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env-file "$ENV_FILE" \
  -e TARGET_RELEASE_ID="$TARGET_RELEASE_ID" \
  -e EXPECTED_CURRENT_SEQ="$EXPECTED_CURRENT_SEQ" \
  -v "$BASE_DIR/state:/var/lib/mpips-update-server/state:rw" \
  -v "$BASE_DIR/release-public.pem:/etc/mpips-update-server/release-public.pem:ro" \
  --entrypoint python \
  "mpips-api:${IMAGE_TAG}" -c '
import json, os
from pathlib import Path
from mpips.update_server.minio_adapter import MinIOArtifactStore
from mpips.update_server.registry import ReleaseRegistry

pub_pem = Path("/etc/mpips-update-server/release-public.pem").read_bytes()
reg = ReleaseRegistry(
    state_dir=Path("/var/lib/mpips-update-server/state"),
    public_key_pem=pub_pem,
    artifact_store=MinIOArtifactStore(),
)
promoted = reg.promote_release(
    release_id=os.environ["TARGET_RELEASE_ID"],
    expected_current_sequence=int(os.environ["EXPECTED_CURRENT_SEQ"]),
    channel="staging",
    platform_name="ubuntu-24.04-x86_64",
)
print(json.dumps({
    "action": "promoted",
    "release_id": promoted.release_id,
    "sequence": promoted.sequence,
    "sha256": promoted.sha256,
    "size_bytes": promoted.size_bytes,
    "authorization_state": promoted.authorization_state,
}, sort_keys=True))
'
```

### 7.6 Gate B Step 5: Post-Promotion Distribution Verification

```bash
set -Eeuo pipefail
BASE_DIR="/var/www/mpips-runtime/update-server"
ENV_FILE="$BASE_DIR/.env.staging"
READER_TOKEN="$(grep -E '^MPIPS_UPDATE_STAGING_READER_TOKEN=' "$ENV_FILE" | cut -d= -f2-)"

MPIPS_UPDATE_STAGING_READER_TOKEN="$READER_TOKEN" \
MPIPS_UPDATE_PUBLIC_KEY_PATH="$BASE_DIR/release-public.pem" \
python3 scripts/verify_staging_update_server.py \
  --base-url http://127.0.0.1:8015 \
  --mode distribution \
  --download-timeout 180

MPIPS_UPDATE_STAGING_READER_TOKEN="$READER_TOKEN" \
MPIPS_UPDATE_PUBLIC_KEY_PATH="$BASE_DIR/release-public.pem" \
python3 scripts/verify_staging_update_server.py \
  --base-url https://ip.mhcsgo.cloud \
  --mode distribution \
  --download-timeout 180
```

### 7.7 Safe Recovery & Revocation Procedures (No Manual `registry.json` Editing or Backup Restoration)

Never hand-edit `registry.json`, never restore stale `registry.json` backups (which would roll back monotonic sequence history), and never delete MinIO objects without separate destructive-cleanup authorization. Use the tested `ReleaseRegistry` APIs across all four failure classes:

1. **Case 1 — Pre-Registration Upload Failure (Failure during `upload_release_bundle` or `verify_release_objects` before `registry.json` is written):**
   - **State Impact:** `registry.json` is untouched (`release_id` is not registered, `current_sequence` is unchanged). However, partial immutable objects (`release.json`, `release.sig`, or a partial `mpips-runtime.bin`) may remain orphaned under `staging/ubuntu-24.04-x86_64/releases/<failed_release_id>/` in MinIO, causing `ensure_release_not_present` to raise `ReleaseConflictError` if the same `release_id` is retried.
   - **Safe Recovery:** Do **not** delete objects from MinIO without separate authorization. Leave the orphaned prefix untouched and start a new registration using a fresh `release_id` (and `sequence = highest_allocated_sequence + 1`).
2. **Case 2 — Registered but Unpromoted Release (`register_and_upload_release(..., promote=False)` succeeded, but operator aborts before promotion):**
   - **State Impact:** The release is in `registry.json` with `authorization_state = "authorized"` (or `"staged"`), and its `sequence` is allocated, while the channel pointer remains at the previous `current_sequence`. Because `/download` permits downloading `authorized` releases with `sequence >= current_sequence`, an unpromoted `authorized` release must be revoked if it is abandoned.
   - **Safe Recovery:** Call `reg.revoke_release("<release_id>")`. This atomically transitions `authorization_state` to `"revoked"` (blocking both `promote_release` and `/download` with HTTP `403 release_unauthorized`) while preserving the allocated sequence in `registry.json` so it can never be reused.
3. **Case 3 — Failed Promotion (`promote_release` raises `ArtifactIntegrityError`, `ChannelSequenceConflictError`, or `ReleaseValidationError`):**
   - **State Impact:** Channel pointer in `registry.json` is unchanged. The candidate release remains registered at its allocated sequence.
   - **Safe Recovery:** Immediately call `reg.revoke_release("<release_id>")` so the failed candidate cannot be downloaded or promoted later. Allocate `sequence = reg.get_highest_allocated_sequence() + 1` with a new `release_id` for any subsequent corrective release.
4. **Case 4 — Post-Promotion Verification Failure (Step 5 `verify_staging_update_server.py --mode distribution` fails after `promote_release` succeeded):**
   - **State Impact:** The channel pointer points to `<release_id>` at `sequence`.
   - **Safe Recovery:**
     1. Immediately execute `reg.revoke_release("<release_id>")` via the container command below:
        ```bash
        docker run --rm \
          --user "$(id -u):$(id -g)" \
          --env-file "$ENV_FILE" \
          -e REVOKE_RELEASE_ID="$TARGET_RELEASE_ID" \
          -v "$BASE_DIR/state:/var/lib/mpips-update-server/state:rw" \
          -v "$BASE_DIR/release-public.pem:/etc/mpips-update-server/release-public.pem:ro" \
          --entrypoint python \
          "mpips-api:${IMAGE_TAG}" -c '
        import json, os
        from pathlib import Path
        from mpips.update_server.minio_adapter import MinIOArtifactStore
        from mpips.update_server.registry import ReleaseRegistry

        pub_pem = Path("/etc/mpips-update-server/release-public.pem").read_bytes()
        reg = ReleaseRegistry(
            state_dir=Path("/var/lib/mpips-update-server/state"),
            public_key_pem=pub_pem,
            artifact_store=MinIOArtifactStore(),
        )
        revoked = reg.revoke_release(os.environ["REVOKE_RELEASE_ID"])
        print(json.dumps({
            "action": "revoked",
            "release_id": revoked.release_id,
            "sequence": revoked.sequence,
            "authorization_state": revoked.authorization_state,
            "current_sequence": reg.get_current_sequence(),
            "highest_allocated_sequence": reg.get_highest_allocated_sequence(),
        }, sort_keys=True))
        '
        ```
     2. Once revoked, `GET /mpips/staging/latest.json` and `GET /mpips/staging/releases/<release_id>/download` immediately fail closed with HTTP `403` (`release_unauthorized`), preventing any Grabber client from trusting or downloading the revoked release, while keeping `current_sequence` and audit history monotonic.
     3. To restore service with a known-good binary, register and promote a newly signed release using a new `release_id` and `sequence = reg.get_highest_allocated_sequence() + 1`.
