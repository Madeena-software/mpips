import os
import json
import httpx
import hmac
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any
from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.dag import DAGExecutor
from app.core.tenant_paths import validate_job_storage_paths
import redis

logger = get_task_logger(__name__)


def get_redis_client() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def dispatch_webhook(callback_url: str, payload: Dict[str, Any]) -> None:
    secret = os.getenv("WEBHOOK_SECRET", "your_hmac_webhook_secret_here")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = compute_signature(
        timestamp.encode("utf-8") + b"." + payload_bytes, secret
    )

    headers = {
        "Content-Type": "application/json",
        "X-Madeena-Signature": signature,
        "X-Madeena-Timestamp": timestamp,
    }

    try:
        with httpx.Client() as client:
            response = client.post(
                callback_url, content=payload_bytes, headers=headers, timeout=10.0
            )
            logger.info(
                f"Webhook sent to {callback_url}. Status: {response.status_code}"
            )
            if response.status_code >= 400:
                logger.error(
                    "Webhook delivery rejected. "
                    f"Status: {response.status_code}; "
                    f"signature_prefix: {signature[:12]}; "
                    f"timestamp: {timestamp}; "
                    f"content_sha256: {hashlib.sha256(payload_bytes).hexdigest()}; "
                    f"body: {response.text}"
                )
    except Exception as e:
        logger.error(f"Failed to dispatch webhook to {callback_url}: {str(e)}")


@shared_task(
    bind=True, name="celery_tasks.tasks.run_pipeline"
)  # type: ignore[untyped-decorator]
def run_pipeline(self: Any, job_data: Dict[str, Any]) -> Dict[str, Any]:
    job_id = self.request.id
    tenant_id = job_data["tenant_id"]
    external_execution_id = job_data["external_execution_id"]
    pipeline = job_data["pipeline"]
    inputs = job_data["inputs"]
    output = job_data["output"]
    callback_url = job_data.get("callback_url")

    r = get_redis_client()

    existing_state_str = r.get(f"mpips:job:{job_id}")
    if existing_state_str:
        job_state = json.loads(existing_state_str)
    else:
        job_state = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "external_execution_id": external_execution_id,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "outputs": {},
            "error": None,
            "callback_url": callback_url,
        }

    job_state.update({
        "job_id": job_id,
        "tenant_id": tenant_id,
        "external_execution_id": external_execution_id,
        "status": "running",
        "progress": 0.0,
        "current_node": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "callback_url": callback_url,
    })
    r.set(f"mpips:job:{job_id}", json.dumps(job_state))
    log_context = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "external_execution_id": external_execution_id,
    }
    logger.info("Job started.", extra=log_context)
    last_progress_webhook_at = 0.0

    def on_progress(node_id: str, progress_pct: float) -> None:
        nonlocal last_progress_webhook_at

        # Check if cancelled in Redis
        current_state_str = r.get(f"mpips:job:{job_id}")
        if current_state_str:
            state = json.loads(current_state_str)
            if state.get("status") == "cancelled":
                raise RuntimeError("Task execution cancelled by user request.")

        job_state["status"] = "running"
        job_state["progress"] = progress_pct
        job_state["current_node"] = node_id
        r.set(f"mpips:job:{job_id}", json.dumps(job_state))

        now = time.monotonic()
        if callback_url and now - last_progress_webhook_at >= 2.0:
            dispatch_webhook(callback_url, job_state)
            last_progress_webhook_at = now

    try:
        validate_job_storage_paths(tenant_id, inputs, output)
        executor = DAGExecutor()
        result = executor.execute(pipeline, inputs, output, on_progress=on_progress)

        job_state["status"] = "completed"
        job_state["progress"] = 100.0
        job_state["current_node"] = None
        job_state["finished_at"] = datetime.now(timezone.utc).isoformat()
        job_state["outputs"] = result.get("outputs", {})

        r.set(f"mpips:job:{job_id}", json.dumps(job_state))
        logger.info("Job completed.", extra=log_context)

        if callback_url:
            dispatch_webhook(callback_url, job_state)

        return job_state

    except Exception as e:
        # Check if already cancelled
        current_state_str = r.get(f"mpips:job:{job_id}")
        is_cancelled = False
        if current_state_str:
            state = json.loads(current_state_str)
            if state.get("status") == "cancelled":
                is_cancelled = True

        if is_cancelled:
            logger.info("Job was cancelled during execution.", extra=log_context)
            return job_state

        logger.error(
            f"Job failed: {str(e)}",
            exc_info=True,
            extra=log_context,
        )

        job_state["status"] = "failed"
        job_state["finished_at"] = datetime.now(timezone.utc).isoformat()
        job_state["error"] = str(e)

        r.set(f"mpips:job:{job_id}", json.dumps(job_state))

        if callback_url:
            dispatch_webhook(callback_url, job_state)

        raise e
