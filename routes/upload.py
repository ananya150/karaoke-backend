"""
Upload endpoint for the Karaoke Backend API.
Handles audio file uploads and initiates processing jobs.
"""

from fastapi import APIRouter, HTTPException
from utils.logger import get_logger

logger = get_logger("upload")
router = APIRouter()


@router.post("/process")
async def process_audio():
    """
    Process audio file endpoint.
    
    This endpoint will be fully implemented in Step 4.
    For now, it returns a placeholder response.
    """
    logger.info("Process endpoint called (placeholder)")
    
    raise HTTPException(
        status_code=501,
        detail="Upload functionality not yet implemented. Coming in Step 4!"
    ) 