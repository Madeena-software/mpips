# Madeena Python Image Processing Services (MPIPS)

The scientific computation microservice of the **Madeena Image Platform (MIP)**. Built with Python 3.12, FastAPI, and Celery, `mpips` (MPIPS) interprets and executes Directed Acyclic Graphs (DAGs) in topological order on image files retrieved from and saved back to S3-compatible storage. It calculates Image Quality Assessment (IQA) metrics and sends secure, signed status callbacks to the `mipc` (MIPC) control plane.

---

## 🛠️ Technology Stack

- **Runtime**: Python 3.12+
- **API Gateway**: FastAPI & Uvicorn
- **Distributed Task Queue**: Celery & Redis
- **Scientific Image Processing**: OpenCV, NumPy, SciPy, scikit-image, PyWavelets
- **Image Quality Assessment (IQA)**: CII (Contrast Improvement Index), ENT (Entropy), EME (Measure of Enhancement), and BRISQUE (No-Reference Image Quality Assessment)
- **Dependency Management**: `uv` or standard virtualenv

---

## 📂 Directory Structure

```
mpips/
├── mpips/
│   ├── api/             # FastAPI app, routes, schemas, and security
│   ├── asgi.py          # ASGI entrypoint for installed deployments
│   ├── cli.py           # Console scripts installed by pip
│   ├── engine/          # Importable DAG, catalog, registry, nodes, IQA, calibration helpers
│   ├── storage.py       # S3/presigned URL and local-file storage backends
│   ├── tenant_paths.py  # Tenant storage boundary validation
│   └── worker/          # Celery app and task definitions
├── research/
│   ├── camera-calibration-dotgrid/
│   └── imager-pipeline/
├── tests/               # Pytest integration/unit tests
├── pyproject.toml       # Python package configuration and dependencies
└── uv.lock              # Lockfile for locked dependencies
```

---

## 🎛️ Image Processing Node Catalog

`mpips` features **25 custom processing nodes** classified into 6 distinct categories:

### 1. Input / Output (`io`)
- `input`: Downloads the source image from S3 and maps it into the DAG execution workspace.
- `output`: Uploads the final processed image back to the target S3 path.

### 2. Geometry (`geometry`)
- `resize`: Resizes images using standard interpolation algorithms (NEAREST, BILINEAR, BICUBIC, LANCZOS4).
- `crop`: Extracts a sub-region of the image relative to a bounding box.
- `rotate`: Rotates the image by an arbitrary angle (supports boundary expansion).
- `flip`: Flips the image horizontally, vertically, or both.

### 3. Adjustments (`adjustments`)
- `grayscale`: Converts multi-channel RGB/RGBA images into a single-channel luminance array.
- `brightness_contrast`: Adjusts image contrast (scaling gain) and brightness (bias offset).
- `thresholding`: Converts images to binary using a static threshold or dynamic Otsu's thresholding.
- `gamma_correction`: Applies non-linear luminance correction using power-law transformations.

### 4. Filtering (`filtering`)
- `gaussian_blur`: Blurs the image to reduce noise using a Gaussian filter kernel.
- `median_blur`: Non-linear blur using median filter (highly effective for salt-and-pepper noise).
- `canny`: Detects edges using multi-stage hysteresis thresholding.
- `sobel`: Computes horizontal/vertical derivatives to extract gradients.

### 5. Advanced (`advanced`)
- `nlm_denoising`: Patch-similarity-based Non-Local Means (NLM) denoising (ideal for low-light sensor noise).
- `homomorphic_filter`: Frequency-domain filter correcting non-uniform lighting by separating illumination and reflectance.
- `wavelet_denoising`: Multiscale denoising using discrete wavelet transforms (DWT).
- `flat_field_correction`: Corrects uneven sensor sensitivity using flat and dark calibration frames.
- `camera_calibration`: Corrects lens distortions using pre-calculated camera matrix `.npz` files.
- `camera_calibration_warp`: Applies promoted calibration remap coordinates from reusable engine logic.
- `fabemd`: Fast Adaptive Bi-dimensional Empirical Mode Decomposition.

### 6. Image Quality Assessment (`iqa`)
- `cii`: Evaluates Contrast Improvement Index on processed results.
- `ent`: Evaluates image information content based on pixel probability distribution (Entropy).
- `eme`: Evaluates local blocks to measure enhancement using the Weber-Fechner law.
- `brisque`: No-reference natural image quality evaluator (lower score indicates higher perceptual quality).

---

## ⚙️ Environment Configuration (`.env`)

Configure the execution plane by setting the following keys in your `.env` file:

### API Configuration
* `API_HOST`: Host to bind the FastAPI app (`0.0.0.0`).
* `API_PORT`: Port to listen on (`8000`).

### Redis & Celery
* `REDIS_URL`: Redis database URL for state storage.
* `CELERY_BROKER_URL`: Celery Redis broker connection string.
* `CELERY_RESULT_BACKEND`: Celery Redis backend connection string.

### Object Storage (S3 / MinIO)
* `AWS_ACCESS_KEY_ID`: AWS / MinIO Access Key.
* `AWS_SECRET_ACCESS_KEY`: AWS / MinIO Secret Key.
* `AWS_DEFAULT_REGION`: Default region name.
* `AWS_ENDPOINT_URL`: Object storage connection endpoint (use `http://localhost:9000` for MinIO).

### Webhook Signatures
* `WEBHOOK_SECRET`: HMAC key matching `mipc`'s webhook secret to sign outgoing callbacks.

### Token Verification (SSO)
* `MADEENA_IDP_JWKS_URL`: JWKS endpoint used to fetch public keys for OAuth2 JWT token verification.
* `MADEENA_REQUIRED_SCOPES`: OAuth scopes required to access job submission/catalog (`image:process,nodes:read`).

### Developer Auth Bypass
* `DEV_AUTH_BYPASS`: Set to `true` to skip central OAuth verification in local dev.
* `DEV_BEARER_TOKEN`: Hardcoded mock token matching `mipc`'s configured bypass token.

---

## 💻 Local Development Setup

We recommend using `uv` to manage Python versions and virtualenvs.

1. **Install Dependencies**:
   ```bash
   uv sync --extra service
   ```
   *Alternatively, using traditional virtualenv:*
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Setup Local Environment**:
   ```bash
   cp .env.production.example .env
   ```

3. **Run Services**:
   Start both the FastAPI API server and the Celery worker daemon.
   ```bash
   # Start FastAPI Server (running on port 8000)
   uv run uvicorn mpips.asgi:app --reload
   # or, after pip install:
   mpips-api
   
   # Start Celery Worker
   uv run celery -A mpips.worker worker --loglevel=info
   # or, after pip install:
   mpips-worker
   ```

---

## 📦 Installing as a Python Module

`mpips` can be installed as a lightweight engine package or as the full backend
service package.

```bash
pip install /path/to/mpips
# or for editable local development:
pip install -e /path/to/mpips
# full API/worker/S3 service dependencies:
pip install -e "/path/to/mpips[service]"
```

For a private GitHub repo in Google Colab, install with a GitHub token or SSH
credential supplied through the notebook environment. Do not commit tokens into
the notebook or repository.

```bash
pip install "git+ssh://git@github.com/<org>/<private-repo>.git"
# or:
pip install "git+https://${GITHUB_TOKEN}@github.com/<org>/<private-repo>.git"
```

Installed import paths:

```python
import mpips
from mpips.engine import DAGExecutor, NODE_CATALOG, get_node_class
from mpips.storage import LocalFileStorageBackend

app = mpips.create_app()
executor = DAGExecutor(storage=LocalFileStorageBackend("/content/data"))
resize_node = get_node_class("resize")
```

Installed service entrypoints:

```bash
uvicorn mpips.asgi:app --host 0.0.0.0 --port 8000
mpips-api
mpips-worker
```

The root repository is also named `mpips`, but the inner `mpips/` directory is
the Python package required for `import mpips` after pip or Colab install.

### Promotion Flow

Prototype code starts in `research/<topic>/`. Once stable, move the reusable
logic into `mpips.engine` as pure Python/Numpy/OpenCV code. If backend execution
is needed, wrap that logic in a node under `mpips.engine.nodes`, register it in
`mpips.engine.registry`, and add catalog metadata in `mpips.engine.catalog`.
Only promoted code under `mpips/` may be imported by the backend.

---

## 🧪 Testing & Code Quality

Verify the codebase with pytest and standard linting/formatting checks.

- **Run Pytest Suite**:
  ```bash
  uv run pytest
  ```
- **Check Formatting (Black)**:
  ```bash
  uv run black --check .
  ```
- **Lint Code (Flake8)**:
  ```bash
  uv run flake8 .
  ```
- **Check Static Typing (Mypy)**:
  ```bash
  uv run mypy .
  ```

---

## 🐳 Production Deployment & Worker Tuning

`mpips` is packaged in a single Docker image that can be run under two distinct roles:

- **API Role** (FastAPI Web API):
  ```bash
  docker run --env-file .env.production -p 8000:8000 mpips:latest api
  ```
- **Worker Role** (Celery Task Worker):
  ```bash
  docker run --env-file .env.production mpips:latest worker
  ```

### Performance & Scaling Controls
When running the `worker` role, tune the following environment variables to optimize throughput:
- `MPIPS_WORKER_CONCURRENCY`: Number of concurrent task processes (default: `2`).
- `MPIPS_WORKER_PREFETCH_MULTIPLIER`: Tasks to pre-fetch per worker process (default: `1` to avoid head-of-line blocking on long jobs).
- `MPIPS_WORKER_TASK_TIME_LIMIT`: Hard time limit for pipeline tasks in seconds (default: `300`).
- `MPIPS_WORKER_TASK_SOFT_TIME_LIMIT`: Soft time limit for pipeline tasks (default: `240`).
- `MPIPS_WORKER_MAX_TASKS_PER_CHILD`: Maximum tasks a worker child process runs before restarting to avoid memory leaks (default: `50`).

---

## 🔌 API Integration Guide

This guide details how external applications (such as client portals, mobile/web apps, or other backend microservices) can connect to and consume `mpips`.

### 🔐 Authentication

All REST endpoints require an OAuth2 Bearer token (JWT) in the `Authorization` header:

```http
Authorization: Bearer <YOUR_ACCESS_TOKEN>
```

#### Production Authentication
In production, your application must authenticate against the central Madeena Identity Provider (IdP) via OAuth2 Client Credentials flow. The token returned must contain the following scopes:
- `image:process` (Required to submit or cancel jobs)
- `nodes:read` (Required to fetch the processor catalog)

#### Local Development Bypass
For rapid development, `mpips` supports a local authentication bypass. To use this mode:
1. Ensure the following variables are set in your `.env` file:
   ```env
   DEV_AUTH_BYPASS=true
   DEV_BEARER_TOKEN=mock_developer_token_xyz
   ```
2. Pass the developer token directly in your request headers:
   ```http
   Authorization: Bearer mock_developer_token_xyz
   ```

---

### 🗃️ 1. Fetching the Node Catalog

To discover available image processing capabilities (dynamic node definitions, parameters, ranges, and types), query the node catalog endpoint.

* **Endpoint**: `GET /v1/nodes`
* **Headers**:
  * `Authorization: Bearer <TOKEN>`

#### Example Request (cURL)
```bash
curl -X GET "http://localhost:8000/v1/nodes" \
  -H "Authorization: Bearer mock_developer_token_xyz"
```

#### Example Response (JSON)
```json
{
  "nodes": [
    {
      "id": "resize",
      "name": "Resize Image",
      "category": "geometry",
      "description": "Resize an image to specific dimensions.",
      "inputs": [{"name": "input_image", "type": "image"}],
      "outputs": [{"name": "output_image", "type": "image"}],
      "parameters": [
        {
          "name": "width",
          "type": "integer",
          "default": 800,
          "description": "Target width in pixels",
          "min": 1,
          "max": null,
          "options": null
        }
      ],
      "version": "1.0.0"
    }
  ]
}
```

---

### 🚀 2. Submitting an Image Processing Job

Submit an image processing Directed Acyclic Graph (DAG) for asynchronous execution.

* **Endpoint**: `POST /v1/jobs`
* **Status Code**: `202 Accepted`
* **Headers**:
  * `Authorization: Bearer <TOKEN>`
  * `Content-Type: application/json`

#### Payload Structure
* `tenant_id` (UUID, Required): Strict tenant identifier boundary. All referenced storage keys/prefixes must belong to this tenant's directory.
* `external_execution_id` (UUID, Required): Unique ID generated by your client application to track this run.
* `pipeline` (Object, Required):
  * `nodes` (Array): Nodes representing processing steps (must include an `input` and `output` node).
  * `edges` (Array): Connections between nodes mapping upstream output handles to downstream input handles.
* `inputs` (Object, Required): Configuration mapping input node IDs to their source storage (e.g. S3).
* `output` (Object, Required): Configuration mapping output node IDs to destination storage.
* `callback_url` (String, Optional): An HTTP endpoint in your application that receives progress updates and the final execution payload.

> [!IMPORTANT]
> **Tenant Key Verification**: For security and isolation, any S3 storage keys in `inputs` or `output` *must* be prefixed with `{tenant_id}/`. For example, if your `tenant_id` is `11111111-1111-4111-8111-111111111111`, input keys must match `11111111-1111-4111-8111-111111111111/path/to/image.png`. Crossing tenant boundaries will result in a `422 Unprocessable Entity` error.

#### Example Request Payload (JSON)
```json
{
  "tenant_id": "11111111-1111-4111-8111-111111111111",
  "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
  "pipeline": {
    "nodes": [
      { "id": "input_1", "type": "input" },
      { "id": "grayscale_1", "type": "grayscale" },
      { "id": "output_1", "type": "output" }
    ],
    "edges": [
      {
        "source": "input_1",
        "target": "grayscale_1",
        "source_handle": "output_image",
        "target_handle": "input_image"
      },
      {
        "source": "grayscale_1",
        "target": "output_1",
        "source_handle": "output_image",
        "target_handle": "input_image"
      }
    ]
  },
  "inputs": {
    "input_1": {
      "source_type": "s3",
      "bucket": "madeena-media",
      "key": "11111111-1111-4111-8111-111111111111/uploads/raw_image.png"
    }
  },
  "output": {
    "destination_type": "s3",
    "bucket": "madeena-media",
    "prefix": "11111111-1111-4111-8111-111111111111/outputs/8fa3b7e4/"
  },
  "callback_url": "https://your-app.com/api/v1/callbacks/jobs"
}
```

#### Example Request (cURL)
```bash
curl -X POST "http://localhost:8000/v1/jobs" \
  -H "Authorization: Bearer mock_developer_token_xyz" \
  -H "Content-Type: application/json" \
  -d @job_payload.json
```

#### Example Response (JSON)
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "queued",
  "submitted_at": "2026-06-12T14:30:00Z"
}
```

---

### 📊 3. Tracking Job Status

For real-time polling of execution status, progress percentage, and outputs.

* **Endpoint**: `GET /v1/jobs/{job_id}`
* **Headers**:
  * `Authorization: Bearer <TOKEN>`

#### Example Request (cURL)
```bash
curl -X GET "http://localhost:8000/v1/jobs/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d" \
  -H "Authorization: Bearer mock_developer_token_xyz"
```

#### Example Response (JSON - Running)
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "tenant_id": "11111111-1111-4111-8111-111111111111",
  "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
  "status": "running",
  "progress": 33.3,
  "current_node": "grayscale_1",
  "started_at": "2026-06-12T14:30:02Z",
  "finished_at": null,
  "outputs": {},
  "error": null
}
```

#### Example Response (JSON - Completed)
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "tenant_id": "11111111-1111-4111-8111-111111111111",
  "external_execution_id": "8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851",
  "status": "completed",
  "progress": 100.0,
  "current_node": null,
  "started_at": "2026-06-12T14:30:02Z",
  "finished_at": "2026-06-12T14:30:05Z",
  "outputs": {
    "output_1": {
      "storage_disk": "s3",
      "bucket": "madeena-media",
      "key": "11111111-1111-4111-8111-111111111111/outputs/8fa3b7e4/output_1.png",
      "mime_type": "image/png",
      "size_bytes": 102450,
      "width": 800,
      "height": 600,
      "checksum": "d41d8cd98f00b204e9800998ecf8427e"
    }
  },
  "error": null
}
```

---

### 🛑 4. Cancelling a Job

Abort an active or queued job. Celery will immediately revoke the worker process execution, and a final status callback will be sent.

* **Endpoint**: `DELETE /v1/jobs/{job_id}`
* **Headers**:
  * `Authorization: Bearer <TOKEN>`

#### Example Request (cURL)
```bash
curl -X DELETE "http://localhost:8000/v1/jobs/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d" \
  -H "Authorization: Bearer mock_developer_token_xyz"
```

#### Example Response (JSON)
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "cancelled",
  "cancelled_at": "2026-06-12T14:31:00Z"
}
```

---

### 🔔 5. Webhooks & Signature Verification

If `callback_url` was specified during job submission, `mpips` will POST JSON updates to your server when:
1. A job transitions to `running`
2. A job finishes successfully (`completed`)
3. A job encounters an error (`failed`)
4. A job is aborted (`cancelled`)

To secure your callback URL, you must verify the signature headers sent in each webhook request.

#### Webhook Headers
* `X-Madeena-Timestamp`: UNIX timestamp of when the webhook was generated.
* `X-Madeena-Signature`: HMAC SHA-256 signature generated using your shared `WEBHOOK_SECRET`.

#### Signature Construction
The signature is calculated by hashing the concatenation of the timestamp, a dot separator (`.`), and the raw JSON payload body:
```
signature = HMAC-SHA256(timestamp + "." + raw_payload_bytes, WEBHOOK_SECRET)
```

#### Verification Snippet (PHP / Laravel Middleware)
```php
<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class VerifyWebhookSignature
{
    public function handle(Request $request, Closure $next): Response
    {
        $signature = $request->header('X-Madeena-Signature');
        $timestamp = $request->header('X-Madeena-Timestamp');
        
        if (!$signature || !$timestamp) {
            abort(401, 'Missing webhook signature or timestamp.');
        }

        // 1. Verify timestamp age (prevent replay attacks - e.g., 5-minute window)
        if (abs(time() - (int)$timestamp) > 300) {
            abort(401, 'Expired webhook signature.');
        }

        $secret = config('services.mpips.webhook_secret'); // Loaded from env('WEBHOOK_SECRET')
        $content = $request->getContent(); // Raw request body string

        // 2. Validate using raw content
        $computed = hash_hmac('sha256', $timestamp . '.' . $content, $secret);
        
        if (hash_equals($signature, $computed)) {
            return $next($request);
        }

        // 3. Fallback: Validate using canonical JSON format (in case of proxy re-serialization)
        $decodedPayload = json_decode($content, true);
        if (json_last_error() === JSON_ERROR_NONE) {
            $canonicalContent = json_encode($decodedPayload, JSON_UNESCAPED_SLASHES);
            if (is_string($canonicalContent)) {
                $computedCanonical = hash_hmac('sha256', $timestamp . '.' . $canonicalContent, $secret);
                if (hash_equals($signature, $computedCanonical)) {
                    return $next($request);
                }
            }
        }

        abort(401, 'Invalid webhook signature.');
    }
}
```

#### Verification Snippet (Node.js / Express Middleware)
```javascript
const crypto = require('crypto');

function verifyMpipsWebhook(req, res, next) {
  const signature = req.headers['x-madeena-signature'];
  const timestamp = req.headers['x-madeena-timestamp'];
  const secret = process.env.WEBHOOK_SECRET;

  if (!signature || !timestamp) {
    return res.status(401).send('Missing webhook headers');
  }

  // Prevent replay attacks (5-minute tolerance)
  const age = Math.abs(Math.floor(Date.now() / 1000) - parseInt(timestamp, 10));
  if (age > 300) {
    return res.status(401).send('Expired webhook signature');
  }

  // Re-verify signature using the raw request body buffer
  // Note: Ensure your Express setup uses bodyParser.raw() or preserves req.rawBody
  const rawBody = req.rawBody ? req.rawBody.toString('utf8') : JSON.stringify(req.body);
  const computedSignature = crypto
    .createHmac('sha256', secret)
    .update(`${timestamp}.${rawBody}`)
    .digest('hex');

  if (crypto.timingSafeEqual(Buffer.from(signature, 'hex'), Buffer.from(computedSignature, 'hex'))) {
    return next();
  }

  return res.status(401).send('Invalid webhook signature');
}
```
