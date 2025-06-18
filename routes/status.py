"""
Status endpoint for the Karaoke Backend API.
Handles job status checking and progress monitoring.
"""

from fastapi import APIRouter, HTTPException
from utils.logger import get_logger

logger = get_logger("status")
router = APIRouter()


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get job status endpoint.
    
    This endpoint will be fully implemented in Step 9.
    For now, it returns a placeholder response.
    """
    logger.info("Status endpoint called (placeholder)", job_id=job_id)
    
    raise HTTPException(
        status_code=501,
        detail="Status functionality not yet implemented. Coming in Step 9!"
    ) 