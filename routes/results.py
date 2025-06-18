"""
Results endpoint for the Karaoke Backend API.
Handles job results retrieval and file serving.
"""

from fastapi import APIRouter, HTTPException
from utils.logger import get_logger

logger = get_logger("results")
router = APIRouter()


@router.get("/results/{job_id}")
async def get_job_results(job_id: str):
    """
    Get job results endpoint.
    
    This endpoint will be fully implemented in Step 9.
    For now, it returns a placeholder response.
    """
    logger.info("Results endpoint called (placeholder)", job_id=job_id)
    
    raise HTTPException(
        status_code=501,
        detail="Results functionality not yet implemented. Coming in Step 9!"
    ) 