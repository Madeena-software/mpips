from fastapi import APIRouter, Depends, status, HTTPException
from uuid import UUID
from datetime import datetime, timezone
from typing import Dict, Any
import json

from app.core.security import verify_token
from app.schemas.nodes import NodeCatalogResponse
from app.schemas.jobs import (
    JobSubmitRequest,
    JobSubmitResponse,
    JobStatusResponse,
    JobCancelResponse,
)
from app.core.catalog import NODE_CATALOG

router = APIRouter(prefix="/v1", tags=["v1"])

_error_401 = {
    "description": "Missing or invalid Bearer token",
    "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
}
_error_403 = {
    "description": "Token lacks required scopes",
    "content": {
        "application/json": {
            "example": {"detail": ("Missing required scope: image:process")}
        }
    },
}
_error_404 = {
    "description": "Requested resource not found",
    "content": {"application/json": {"example": {"detail": "Job abc-123 not found."}}},
}


@router.get(
    "/nodes",
    response_model=NodeCatalogResponse,
    summary="List processing nodes",
    description=(
        "Returns the complete catalog of available "
        "image-processing nodes. Each node includes "
        "input/output slot definitions, configurable "
        "parameters with type constraints, and "
        "semantic versioning."
    ),
    response_description=("Full catalog of processor node schemas"),
    operation_id="listNodes",
    responses={401: _error_401, 403: _error_403},
    tags=["Nodes"],
)
def get_nodes(
    payload: Dict[str, Any] = Depends(verify_token),
) -> NodeCatalogResponse:
    """Returns the dynamic catalog of available image processing nodes."""
    return NodeCatalogResponse(nodes=NODE_CATALOG)


@router.post(
    "/jobs",
    response_model=JobSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a processing job",
    description=(
        "Queues an image-processing DAG execution "
        "job. The pipeline graph is validated, "
        "tenant S3 boundaries are enforced, and "
        "the job is dispatched to the Celery worker "
        "pool. Returns immediately with a job ID "
        "for status polling."
    ),
    response_description="Job acceptance confirmation",
    operation_id="submitJob",
    responses={
        401: _error_401,
        403: _error_403,
        422: {"description": ("Validation error in request body")},
    },
    tags=["Jobs"],
)
def submit_job(
    job_req: JobSubmitRequest,
    payload: Dict[str, Any] = Depends(verify_token),
) -> JobSubmitResponse:
    """Submits an image processing DAG execution job to the queue."""
    from celery_tasks.tasks import (
        run_pipeline,
        get_redis_client,
    )

    # 1. Trigger Celery task
    task = run_pipeline.apply_async(args=[job_req.model_dump(mode="json")])

    # 2. Store initial state in Redis
    r = get_redis_client()
    submitted_at = datetime.now(timezone.utc)
    job_state = {
        "job_id": task.id,
        "tenant_id": str(job_req.tenant_id),
        "external_execution_id": str(job_req.external_execution_id),
        "status": "queued",
        "progress": 0.0,
        "current_node": None,
        "submitted_at": submitted_at.isoformat(),
        "started_at": None,
        "finished_at": None,
        "outputs": {},
        "error": None,
        "callback_url": job_req.callback_url,
    }
    r.set(f"mpips:job:{task.id}", json.dumps(job_state))

    return JobSubmitResponse(
        job_id=task.id,
        status="queued",
        submitted_at=datetime.now(timezone.utc),
    )


@router.get(
    "/jobs/{id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description=(
        "Retrieves the current status, progress "
        "percentage, active node, timestamps, and "
        "output metadata for a specific execution "
        "job. Poll this endpoint to track "
        "asynchronous processing."
    ),
    response_description="Current job status snapshot",
    operation_id="getJobStatus",
    responses={
        401: _error_401,
        403: _error_403,
        404: _error_404,
    },
    tags=["Jobs"],
)
def get_job_status(
    id: str,
    payload: Dict[str, Any] = Depends(verify_token),
) -> JobStatusResponse:
    """Retrieves the status and progress of a specific execution job."""
    from celery_tasks.tasks import get_redis_client

    r = get_redis_client()
    job_key = f"mpips:job:{id}"
    job_state_str = r.get(job_key)

    if not job_state_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {id} not found.",
        )

    job_state = json.loads(job_state_str)

    return JobStatusResponse(
        job_id=job_state["job_id"],
        tenant_id=UUID(job_state["tenant_id"]),
        external_execution_id=UUID(job_state["external_execution_id"]),
        status=job_state["status"],
        progress=job_state["progress"],
        current_node=job_state.get("current_node"),
        submitted_at=(
            datetime.fromisoformat(job_state["submitted_at"])
            if job_state.get("submitted_at")
            else None
        ),
        started_at=(
            datetime.fromisoformat(job_state["started_at"])
            if job_state.get("started_at")
            else None
        ),
        finished_at=(
            datetime.fromisoformat(job_state["finished_at"])
            if job_state.get("finished_at")
            else None
        ),
        outputs=job_state.get("outputs", {}),
        error=job_state.get("error"),
    )


@router.delete(
    "/jobs/{id}",
    response_model=JobCancelResponse,
    summary="Cancel a job",
    description=(
        "Aborts a running or queued job by revoking "
        "the Celery task and updating the status in "
        "Redis. If the job has already reached a "
        "terminal state (completed, failed, "
        "cancelled), returns the existing state "
        "without modification."
    ),
    response_description="Cancellation result",
    operation_id="cancelJob",
    responses={
        401: _error_401,
        403: _error_403,
        404: _error_404,
    },
    tags=["Jobs"],
)
def cancel_job(
    id: str,
    payload: Dict[str, Any] = Depends(verify_token),
) -> JobCancelResponse:
    """Aborts a running or queued job."""
    from celery_tasks.tasks import (
        get_redis_client,
        dispatch_webhook,
    )
    from celery_tasks.worker import app as celery_app

    r = get_redis_client()
    job_key = f"mpips:job:{id}"
    job_state_str = r.get(job_key)

    if not job_state_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {id} not found.",
        )

    job_state = json.loads(job_state_str)

    if job_state.get("status") in (
        "completed",
        "failed",
        "cancelled",
    ):
        return JobCancelResponse(
            job_id=id,
            status=job_state["status"],
            cancelled_at=(
                datetime.fromisoformat(job_state["finished_at"])
                if job_state.get("finished_at")
                else datetime.now(timezone.utc)
            ),
        )

    job_state["status"] = "cancelled"
    job_state["finished_at"] = datetime.now(timezone.utc).isoformat()
    r.set(job_key, json.dumps(job_state))

    celery_app.control.revoke(id, terminate=True, signal="SIGTERM")

    callback_url = job_state.get("callback_url")
    if callback_url:
        dispatch_webhook(callback_url, job_state)

    return JobCancelResponse(
        job_id=id,
        status="cancelled",
        cancelled_at=datetime.now(timezone.utc),
    )


@router.get(
    "/jobs",
    response_model=list[JobStatusResponse],
    summary="List all jobs",
    description=(
        "Retrieves a list of all jobs currently stored in Redis. "
        "Each job contains its state, progress, and metadata."
    ),
    response_description="List of job status snapshots",
    operation_id="listJobs",
    responses={401: _error_401, 403: _error_403},
    tags=["Jobs"],
)
def list_jobs(
    payload: Dict[str, Any] = Depends(verify_token),
) -> list[JobStatusResponse]:
    """Retrieves all jobs stored in Redis."""
    from celery_tasks.tasks import get_redis_client

    r = get_redis_client()
    keys = r.keys("mpips:job:*")
    jobs = []
    for key in keys:
        try:
            job_state_str = r.get(key)
            if job_state_str:
                job_state = json.loads(job_state_str)
                jobs.append(
                    JobStatusResponse(
                        job_id=job_state["job_id"],
                        tenant_id=UUID(job_state["tenant_id"]),
                        external_execution_id=UUID(job_state["external_execution_id"]),
                        status=job_state["status"],
                        progress=job_state["progress"],
                        current_node=job_state.get("current_node"),
                        submitted_at=(
                            datetime.fromisoformat(job_state["submitted_at"])
                            if job_state.get("submitted_at")
                            else None
                        ),
                        started_at=(
                            datetime.fromisoformat(job_state["started_at"])
                            if job_state.get("started_at")
                            else None
                        ),
                        finished_at=(
                            datetime.fromisoformat(job_state["finished_at"])
                            if job_state.get("finished_at")
                            else None
                        ),
                        outputs=job_state.get("outputs", {}),
                        error=job_state.get("error"),
                    )
                )
        except Exception:
            pass

    # Sort jobs by submission time (newest first), then by start time.
    jobs.sort(
        key=lambda job: (
            job.submitted_at or job.started_at or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )
    return jobs
