# Antigravity Prompt — MPIPS API Hardening & Debugging

Repository:

https://github.com/Madeena-software/mpips

## Primary Objective

Harden and debug the existing MPIPS DICOM API until its functional contract, failure behavior, security boundaries, DICOM conformance, idempotency semantics, worker isolation, cleanup behavior, and diagnostic quality are production-ready for the current internal-beta architecture.

This task is **not** a performance benchmark task and **not** an MHCS integration-documentation task.

Do not optimize throughput merely to improve benchmark numbers.
Do not write the final local/production integration guide yet.
Do not redesign deployment unless a proven API-hardening blocker requires a minimal runtime change.

---

## Current Verified Baseline

Start by independently confirming the current repository state.

Expected starting HEAD at task creation:

`fa7357d145a1738d064ec6665fa16d47778ab7d2`

Expected latest commit message:

`fix(concurrency): align max concurrent conversions to 2 and harden verification contract`

Known successful functional verification evidence:

- Verify MPIPS Internal Beta #6
  - Run ID: `31563098884`
  - Trigger: `workflow_run`
  - Result: SUCCESS
- Verify MPIPS Internal Beta #7
  - Run ID: `31563105098`
  - Trigger: `workflow_dispatch`
  - Result: SUCCESS

Observed functional behavior:

```text
health                         -> 200
valid DICOM conversion         -> 200
valid DICOM                    -> explicit VR little endian
output dimensions              -> 3053 x 4059
pixel type                     -> uint16
private tags                   -> none

missing API key                -> 401 INVALID_API_KEY
wrong API key                  -> 401 INVALID_API_KEY
bearer without API key         -> 401 INVALID_API_KEY

malformed manifest             -> 422 MANIFEST_SCHEMA_INVALID
malformed radiograph           -> 422 NPZ_VALIDATION_ERROR

idempotency first claim        -> 200
idempotency replay             -> 200
idempotency conflict           -> 409 IDEMPOTENCY_CONFLICT

bounded concurrency            -> [200, 200, 429, 429, 429, 429, 429, 429]
unexpected 5xx in concurrency  -> 0
health after concurrency       -> 200

launcher malformed JSON        -> rejected
launcher path traversal        -> rejected
launcher missing args          -> rejected

workspace cleanup              -> 0 job directories
burn-in                        -> 19 HTTP cases passed
```

Current production API endpoint on the host:

`http://127.0.0.1:8014`

Current private Docker network:

`madeena-software-network`

Current container-to-container MPIPS endpoint:

`http://mpips-api:8000`

Current configured conversion concurrency:

`MPIPS_DICOM_MAX_CONCURRENT_CONVERSIONS=2`

Do not regress this baseline.

---

## Repository Authority

Before modifying anything, read and follow:

```text
.agents/AGENTS.md
.agents/software-workflow.md
.agents/context/project.md
```

Also inspect the relevant current task files under:

```text
.agents/tasks/
```

Create or update a focused task record for this work if repository workflow requires one.

Record:

```text
STARTING_HEAD=<sha>
CURRENT_DEPLOY_RUN=<run id if relevant>
CURRENT_VERIFY_RUN=<run id>
```

Do not trust an old Antigravity summary if GitHub evidence differs.

---

# Scope

The scope is the API and the execution path used by:

```text
POST /v1/radiographs/dicom
```

Primary files to inspect include, but are not limited to:

```text
mpips/api/api_key.py
mpips/api/application.py
mpips/api/idempotency.py
mpips/api/routes/v1/dicom.py
mpips/api/schemas/dicom.py

mpips/conversion/service.py
mpips/conversion/validation.py
mpips/conversion/worker.py

docker/host-launcher/mpips-launcher.py
docker-compose.prod.yml

scripts/local_dicom_burn_in.py

tests/api/
tests/test_host_launcher.py

.github/workflows/verify-internal-beta.yml
```

Inspect other files only when evidence requires it.

---

# Explicit Non-Goals

Do NOT turn this task into:

- performance benchmarking;
- p50/p95/p99 measurement;
- capacity planning beyond what is required to validate correctness;
- broad MHCS integration work;
- MHCS repository changes;
- public API exposure;
- API gateway design;
- Kubernetes migration;
- reverse proxy redesign;
- distributed queue redesign;
- Redis architecture redesign;
- broad refactoring;
- unrelated formatting or generated-cache commits.

Performance measurement will be a separate task after this hardening task is complete.

Integration documentation will be a separate task after the API contract and performance envelope are stable.

---

# Phase 1 — Baseline Reproduction

Before editing code, reproduce the current verified behavior locally where possible.

Run focused tests first.

At minimum:

```bash
MPIPS_ENVIRONMENT=development uv run pytest \
  tests/api/test_api_surface.py \
  tests/api/test_dicom_authentication.py \
  tests/api/test_dicom_conversion.py \
  tests/test_host_launcher.py \
  -q
```

Also inspect the latest successful verification log.

Confirm:

```text
valid conversion = 200
DICOM validation = PASS
concurrency = only 200 and 429
unexpected 5xx = 0
health after concurrency = 200
```

Do not edit until the baseline is understood.

---

# Phase 2 — Authentication and Secret Hardening

Audit authentication before touching unrelated code.

The current implementation must not rely on a production API credential committed as a source-code literal.

Investigate:

```text
mpips/api/api_key.py
scripts/local_dicom_burn_in.py
tests
docker-compose.prod.yml
.env examples
GitHub Actions workflow secret handling
```

Determine whether any credential currently used by production or verification is embedded in tracked source.

Requirements:

1. Production API key material must come from runtime configuration or an appropriate secret source.
2. Fail closed if production authentication configuration is absent or invalid.
3. Do not print API keys.
4. Do not include API keys in exception text.
5. Do not include API keys in workflow logs.
6. Continue using constant-time comparison or an equivalently safe mechanism.
7. Verification must obtain its credential without reintroducing a committed secret.
8. Development/test defaults must not silently become production credentials.
9. Update tests for missing configuration and invalid keys.
10. Preserve the existing `401 INVALID_API_KEY` external contract unless there is a documented reason to change it.

Do not rotate or expose real credentials in the repository.

If a production secret must be created or changed outside the repository and you do not have the required authority, stop and report:

```text
SECRET_CONFIGURATION_REQUIRED=true
REQUIRED_SECRET_NAME=<name>
```

Do not invent a real secret value.

---

# Phase 3 — HTTP Contract Hardening

Audit the actual API behavior against the declared contract.

The route currently advertises responses in the general classes:

```text
200
400
401
409
413
422
429
503
504
```

Verify actual behavior for:

- missing multipart fields;
- duplicate multipart fields;
- wrong content type;
- empty manifest;
- invalid UTF-8 manifest;
- invalid JSON;
- schema-invalid manifest;
- missing radiograph NPZ;
- missing gain NPZ;
- empty NPZ files;
- byte-size mismatch;
- SHA-256 mismatch;
- oversized manifest;
- oversized radiograph;
- oversized gain;
- oversized combined upload;
- malformed NPZ;
- detector mismatch;
- camera mismatch;
- calibration mismatch;
- Redis unavailable;
- worker timeout;
- worker failure;
- capacity exhausted.

Do not force a status code merely because the OpenAPI decorator currently lists it.

First determine the intended contract from:

- code;
- tests;
- project documentation;
- existing consumers.

Then either:

- make implementation match the intended contract; or
- make documentation/tests match proven intentional behavior.

Every externally visible failure must return:

- a stable HTTP status;
- a sanitized machine-readable `detail`;
- no stack trace;
- no local filesystem path;
- no Docker command;
- no API key;
- no patient data beyond what is explicitly required by the API contract.

---

# Phase 4 — Idempotency + Concurrency Interaction

This is a mandatory investigation.

The current request flow should be inspected carefully around:

```text
IdempotencyService.claim_job(...)
        ↓
CapacityLimiter.acquire_nowait()
```

At the current baseline, the idempotency claim occurs before concurrency admission.

Prove whether this can create a stranded idempotency lease.

Mandatory reproduction:

1. Saturate the conversion limiter in a controlled test.
2. Send a valid request with a new `conversion_job_id`.
3. Confirm the request receives:
   `429 CONCURRENCY_LIMIT_EXCEEDED`.
4. Allow capacity to become available.
5. Retry the **same exact request with the same conversion_job_id**.
6. Observe whether it succeeds normally or incorrectly returns:
   `409 IDEMPOTENCY_IN_PROGRESS`.

Expected semantic property:

> A request rejected before conversion because capacity is unavailable must not leave an idempotency state that prevents a legitimate retry.

Do not assume this bug exists. Prove it with a deterministic test.

If proven, fix the transaction/order/state handling with the smallest correct change.

Possible strategies must be evaluated rather than blindly chosen:

- acquire capacity before creating a processing claim;
- explicitly release/fail the claim on 429;
- use a different admission-state model.

Preserve race safety.

Add a regression test proving that a 429 does not poison the idempotency key.

Also verify:

- simultaneous duplicate same-job requests;
- replay after success;
- retry after worker failure;
- retry after timeout;
- conflict with same job ID but different fingerprint;
- Redis failure during claim;
- Redis failure during mark-success.

Do not weaken atomic Redis semantics.

---

# Phase 5 — Idempotency Replay Semantics

Inspect what `SUCCEEDED_SAME` actually means end-to-end.

Determine whether an exact successful replay:

- returns a cached result;
- reruns conversion;
- reacquires worker capacity;
- mutates the idempotency state back to processing;
- produces exactly the same SOP Instance UID;
- behaves safely if the second conversion fails.

Do not change semantics merely because caching sounds preferable.

First identify the intended contract from current documentation/tests.

Then ensure the implementation is internally consistent and covered by tests.

The final report must explicitly state:

```text
IDEMPOTENCY_REPLAY_MODE=<cached|recomputed|other>
```

and explain why.

---

# Phase 6 — DICOM Conformance Hardening

The current successful verification still emits this warning:

```text
pydicom UserWarning:
The value length (18) exceeds the maximum length of 16 allowed for VR SH.
```

Do not suppress the warning.

Identify exactly:

```text
DICOM tag
keyword
VR
source manifest field
actual generated value
maximum permitted representation
```

Trace the value through:

```text
manifest
  -> adapter/converter metadata
  -> DICOM writer
  -> enrichment
  -> final dataset
```

Fix the source of the invalid SH value in the narrowest standards-correct layer.

Do not arbitrarily truncate clinically meaningful identifiers unless the DICOM mapping explicitly permits a deterministic compliant representation.

Add a regression test that fails when generated test DICOM emits known VR-length conformance warnings.

Also audit the final DICOM for at least:

```text
Transfer Syntax
SOP Class UID
SOP Instance UID
Study Instance UID
Series Instance UID
Rows
Columns
Bits Allocated
Bits Stored
High Bit
Pixel Representation
Photometric Interpretation
Samples per Pixel
Pixel Data length
Burned In Annotation
Lossy Image Compression
Patient ID mapping
Accession Number
Study Description
Series Description
Protocol Name
date/time validity
VR length validity for populated textual elements
private tags
```

Do not redesign clinical metadata mapping without evidence.

---

# Protected Converter Boundary

Treat:

```text
mpips/engine/imager_pipeline/tiff_json_to_dcm.py
```

as protected.

Record its SHA before work.

Do not modify it by default.

If the SH warning or another defect appears to originate there:

1. prove the exact source;
2. determine whether the correct fix belongs upstream in metadata preparation or downstream enrichment;
3. prefer a non-invasive standards-correct fix outside the protected converter when appropriate.

If modifying the protected converter is truly required, STOP before editing and report:

```text
PROTECTED_CONVERTER_CHANGE_REQUIRED=true
EXACT_REASON=<evidence>
PROPOSED_CHANGE=<minimal change>
```

Do not edit it automatically.

---

# Phase 7 — NPZ Input Hardening

Audit NPZ parsing and validation as untrusted input.

Check for:

- unsafe pickle/object deserialization;
- compressed-data expansion risk;
- unexpected arrays;
- missing arrays;
- unexpected dtypes;
- object arrays;
- invalid dimensions;
- zero-sized arrays;
- negative/NaN/Inf where meaningful;
- excessive dimensions;
- shape mismatch;
- gain/radiograph mismatch;
- detector mismatch;
- camera mismatch;
- array byte-size limits after decompression;
- pixel-count limits;
- integer overflow in dimension calculations;
- malformed ZIP/NPZ containers.

Do not rely only on HTTP compressed byte size.

Preserve compatibility with the actual detector NPZ structure required by MPIPS.

If `allow_pickle=True` or equivalent unsafe behavior is required because existing detector NPZ metadata uses object arrays, document the precise trust boundary and implement the strongest practical validation around it rather than silently breaking compatibility.

Add focused adversarial tests without creating huge files or resource-exhaustion tests.

Do not run destructive stress tests.

---

# Phase 8 — Worker and Launcher Failure Hardening

Audit the full boundary:

```text
API
 -> Unix socket
 -> host launcher
 -> docker run
 -> NPZ worker
 -> worker result JSON
 -> parent conversion
```

Test controlled failure modes:

- launcher socket missing;
- launcher connection refused;
- malformed launcher response;
- empty launcher response;
- worker nonzero exit;
- worker timeout;
- missing worker result JSON;
- malformed worker result JSON;
- worker result says failure;
- output TIFF missing;
- output TIFF malformed;
- output DICOM validation failure;
- cleanup after every failure.

Ensure:

```text
timeout       -> controlled 504 where contract requires
dependency    -> controlled 503 where contract requires
validation    -> controlled 4xx where contract requires
internal fault-> sanitized 5xx
```

No failure may leak:

- host paths;
- Docker internals;
- command arguments;
- environment secrets;
- patient data.

Keep useful detailed diagnostics in server-side logs with PHI-safe sanitization.

---

# Phase 9 — Resource and Cleanup Correctness

This is correctness hardening, not performance benchmarking.

Verify temporary resources are released for every path:

```text
/tmp/mpips-dicom-stage-*
/tmp/mpips-workspaces/job-*
temporary TIFF
temporary JSON
output DICOM
launcher worker containers
CapacityLimiter tokens
Redis processing leases
```

Test cleanup after:

- 401;
- malformed multipart;
- 413;
- 422;
- 409;
- 429;
- worker failure;
- timeout;
- successful FileResponse completion;
- client disconnect if feasible without disproportionate complexity.

Ensure limiter tokens cannot leak.

Ensure a failed request cannot permanently reduce available capacity.

Ensure worker containers do not remain after bounded failures.

Do not implement broad host-cleanup scripts that might delete unrelated files.

---

# Phase 10 — Realistic Fixture Validation

The current `local_dicom_burn_in.py` uses a synthetic flat radiograph rather than a real radiographic image.

Synthetic burn-in must remain because it is deterministic and safe for CI.

Additionally, look for an existing **de-identified, non-PHI representative radiograph NPZ + matching gain NPZ** that is already authorized for test use.

Rules:

- Do not commit real patient PHI.
- Do not print patient PHI.
- Do not copy production patient data into the repository.
- Do not invent a de-identification process and assume it is sufficient.
- Do not block the entire hardening task if no safe real fixture is available.

If an approved de-identified fixture exists, add a separate optional/manual verification path that proves the real image shape and pipeline behavior without making CI depend on private patient data.

If none exists, report:

```text
REAL_DEIDENTIFIED_FIXTURE_AVAILABLE=false
```

and continue using synthetic tests.

---

# Phase 11 — Observability and Diagnostics

Improve diagnostics only where needed to debug API behavior.

Every request should be attributable using safe identifiers such as:

```text
correlation_id
conversion_job_id
sanitized error code
duration
worker outcome
```

Do not log:

```text
API key
patient name
raw NPZ content
Pixel Data
complete manifest
secrets
authorization headers
```

Review whether `X-Correlation-ID` and `X-Conversion-Job-ID` are returned consistently for successful and appropriate error responses.

Do not create a full telemetry platform in this task.

Metrics benchmarking belongs to Prompt 2.

---

# Phase 12 — Verification Contract Hardening

Strengthen `scripts/local_dicom_burn_in.py` only where needed.

It should continue to reject unexpected 5xx.

Add high-value regression cases discovered during this task, especially:

- 429 must not poison idempotency;
- authentication secret configuration behavior;
- DICOM SH/VR conformance warning;
- cleanup after failure;
- retry behavior after worker failure/timeout where deterministic;
- documented error-contract edge cases.

Avoid turning the burn-in into an enormous test suite.

Keep detailed unit/integration coverage in `tests/`.

Burn-in should remain a concise server-level acceptance check.

---

# Phase 13 — Testing Requirements

Before any production deployment:

Run the focused suite.

Then run the full repository test suite if practical:

```bash
uv run pytest -q
```

Run static checks already used by the repository, for example:

```bash
uv run mypy mpips tests
uv run black --check .
uv run flake8 mpips
```

Use the repository's actual configured commands if they differ.

Do not claim success from unexecuted commands.

Record exact counts:

```text
focused tests: X passed, Y failed
full tests: X passed, Y failed
mypy: result
format: result
lint: result
```

---

# Phase 14 — Change Discipline

Keep changes focused.

Maximum implementation commits:

```text
2
```

Prefer:

```text
1. API hardening/security correctness
2. DICOM/verification hardening
```

only if separation is useful.

Do not create generated AST/cache commits.

Do not include unrelated formatting across the repository.

Do not modify MHCS.

Do not modify `madeena-software-network`.

Do not expose MPIPS publicly.

Do not bind port 8014 to `0.0.0.0`.

Do not expose Redis host ports.

Do not change host sysctl.

Do not weaken container isolation.

---

# Phase 15 — Deployment Boundary

The current deployment is already functionally healthy.

Treat deployment as a prerequisite, not the default debugging target.

Do not modify:

```text
.github/workflows/deploy-internal-beta.yml
```

unless direct evidence proves a deployment-owned requirement is blocking a correct API hardening fix.

Before any deploy-workflow modification, print:

```text
DEPLOYMENT_CHANGE_REQUIRED=true
EXACT_BLOCKER=<evidence>
WHY_API_CODE_ALONE_CANNOT_FIX_IT=<reason>
```

Then make only the minimal required change.

Runtime configuration changes required for secret injection or corrected API behavior are allowed only when they are directly justified by this task.

---

# Phase 16 — Production Validation

After local tests pass and the implementation is committed:

1. Push the focused commit(s) to `main` if repository authority permits.
2. If runtime code/config changed, dispatch **one** Deploy MPIPS Internal Beta run.
3. Require deploy success before functional verification.
4. Dispatch or use the automatic **one** Verify MPIPS Internal Beta run.
5. Inspect the actual job log, not just the green badge.

Do not deploy repeatedly as a debugging loop.

Do not run Verify repeatedly merely for confidence.

One successful functional verification on the exact deployed SHA is sufficient unless a previous run was invalid for a proven reason.

---

# CRITICAL POLLING RULE

Maximum workflow status checks per run:

```text
3
```

After the third status check:

- if completed, inspect result;
- if still running, STOP IMMEDIATELY;
- output `still-in-progress`.

Do NOT:

- schedule another timer;
- call `gh run list` again;
- call `gh run view` again;
- create another polling loop;
- wait indefinitely.

The GitHub workflow may continue independently after Antigravity stops.

---

# Success Criteria

This task is `succeeded` only if all applicable criteria are observed:

```text
valid /v1/radiographs/dicom            -> 200
health                                  -> 200
valid DICOM structural validation       -> PASS

auth failures                           -> controlled 401
schema/NPZ failures                     -> controlled validation response
upload-limit failures                   -> controlled response
idempotency conflicts                   -> controlled 409
capacity rejection                      -> controlled 429
dependency failure                      -> controlled response
timeout                                 -> controlled 504 where applicable

unexpected 5xx in defined burn-in       -> 0
health after failures/concurrency        -> 200

429 retry with same job ID               -> not poisoned by stale IN_PROGRESS lease
limiter token leak                       -> none
workspace leak                           -> none
worker-container leak                    -> none

committed production credential literal  -> none
secret leakage in logs                   -> none

known DICOM SH>16 warning                 -> resolved or explicitly blocked with evidence

focused tests                             -> PASS
full tests                                -> PASS
static checks                             -> PASS

Deploy on tested SHA                      -> SUCCESS if deployment required
Verify on deployed SHA                    -> SUCCESS
```

Do not report `succeeded` merely because tests are green if a known security or state-corruption defect discovered during this task remains unresolved.

---

# Final Report

Return a concise but evidence-based final report with exactly these sections:

```text
1. Starting HEAD
2. Final HEAD
3. Baseline Verify Evidence
4. Hardening Findings
5. Security Findings
6. Idempotency + Concurrency Result
7. DICOM Conformance Result
8. NPZ Validation Result
9. Worker/Launcher Failure Result
10. Cleanup/Resource Result
11. Files Changed
12. Tests Added/Changed
13. Focused Test Results
14. Full Test Results
15. Static Check Results
16. Deployment Changes
17. Deploy Run
18. Verify Run
19. Residual Risks
20. Final Outcome
```

For each finding use:

```text
PROVEN
NOT REPRODUCED
FIXED
BLOCKED
OUT OF SCOPE
```

Do not use speculative wording as a substitute for evidence.

Use exactly one final terminal state:

```text
succeeded
failed
blocked
awaiting-approval
still-in-progress
```

---

# Priority Order

If time or context becomes constrained, prioritize in this exact order:

```text
1. committed credential / authentication hardening
2. idempotency + 429 state correctness
3. DICOM SH/VR conformance warning
4. unexpected 5xx and worker error semantics
5. cleanup and limiter/lease correctness
6. NPZ adversarial validation
7. observability improvements
8. optional de-identified real fixture path
```

Do not skip a higher-priority proven defect to work on a lower-priority cleanup item.
