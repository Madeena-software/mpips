from fastapi import APIRouter, Depends, status
from uuid import UUID
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

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


@router.get("/nodes", response_model=NodeCatalogResponse)
def get_nodes(payload: Dict[str, Any] = Depends(verify_token)) -> NodeCatalogResponse:
    """Returns the dynamic catalog of available image processing nodes."""
    return NodeCatalogResponse(nodes=NODE_CATALOG)


@router.post(
    "/jobs", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED
)
def submit_job(
    job_req: JobSubmitRequest, payload: Dict[str, Any] = Depends(verify_token)
) -> JobSubmitResponse:
    """Submits an image processing DAG execution job to the queue (Stub)."""
    # Return mock job response
    job_id = f"job_{uuid.uuid4()}"
    return JobSubmitResponse(
        job_id=job_id, status="queued", submitted_at=datetime.now(timezone.utc)
    )


@router.get("/jobs/{id}", response_model=JobStatusResponse)
def get_job_status(
    id: str, payload: Dict[str, Any] = Depends(verify_token)
) -> JobStatusResponse:
    """Retrieves the status and progress of a specific execution job (Stub)."""
    # Return mock status response
    return JobStatusResponse(
        job_id=id,
        external_execution_id=UUID("8fa3b7e4-0bb7-4b71-9252-c6c7b3be9851"),
        status="queued",
        progress=0.0,
        current_node=None,
        started_at=None,
        finished_at=None,
        outputs={},
        error=None,
    )


@router.delete("/jobs/{id}", response_model=JobCancelResponse)
def cancel_job(
    id: str, payload: Dict[str, Any] = Depends(verify_token)
) -> JobCancelResponse:
    """Aborts a running or queued job (Stub)."""
    return JobCancelResponse(
        job_id=id, status="cancelled", cancelled_at=datetime.now(timezone.utc)
    )
