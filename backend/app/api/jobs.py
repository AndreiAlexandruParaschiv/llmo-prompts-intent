"""Job status API endpoints."""

from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult

from app.core.celery_app import celery_app

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a background job."""
    result = AsyncResult(job_id, app=celery_app)
    
    response = {
        "job_id": job_id,
        "status": result.status,
        "ready": result.ready(),
    }
    
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    elif result.status == "PROGRESS":
        response["progress"] = result.info
    
    return response


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    result = AsyncResult(job_id, app=celery_app)
    result.revoke(terminate=True)
    
    return {"job_id": job_id, "status": "cancelled"}

