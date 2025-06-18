"""
Status endpoint for the Karaoke Backend API.
Handles job status checking and progress monitoring.
"""

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from datetime import datetime

from database.redis_client import get_redis_client
from models.job import JobStatus, ProcessingStep
from utils.logger import get_logger

logger = get_logger("status")
router = APIRouter()


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: int
    current_step: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    estimated_completion: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    
    # Stage-specific status
    stem_separation: Optional[Dict[str, Any]] = None
    transcription: Optional[Dict[str, Any]] = None
    beat_analysis: Optional[Dict[str, Any]] = None
    
    # Summary information
    audio_duration: Optional[float] = None
    tempo_bpm: Optional[float] = None
    beat_count: Optional[int] = None
    file_size: Optional[int] = None


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get comprehensive job status and progress information.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Detailed job status including progress, current step, and stage-specific information
        
    Raises:
        HTTPException: 404 if job not found, 500 for internal errors
    """
    try:
        logger.info("Getting job status", job_id=job_id)
        
        with get_redis_client() as redis_client:
            # Check if job exists
            job_exists = redis_client.exists(f"job:{job_id}")
            if not job_exists:
                logger.warning("Job not found", job_id=job_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found"
                )
            
            # Get all job data
            job_data = redis_client.hgetall(f"job:{job_id}")
            
            if not job_data:
                logger.error("Job data is empty", job_id=job_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} data not found"
                )
        
        # Parse basic job information
        status = job_data.get('status', 'unknown')
        if status == 'None' or status is None:
            status = 'unknown'
            
        progress = int(job_data.get('progress', 0))
        
        current_step = job_data.get('current_step', 'unknown')
        if current_step == 'None' or current_step is None:
            current_step = 'unknown'
            
        created_at = job_data.get('created_at')
        updated_at = job_data.get('updated_at')
        
        error_message = job_data.get('error_message')
        if error_message == 'None':
            error_message = None
        
        # Calculate processing time if available
        processing_time = None
        if created_at and updated_at and created_at != 'None' and updated_at != 'None':
            try:
                # Timestamps are stored as Unix timestamps (floats)
                created_timestamp = float(created_at)
                updated_timestamp = float(updated_at)
                processing_time = updated_timestamp - created_timestamp
                
                # Convert timestamps to ISO format strings for response
                created_at = datetime.fromtimestamp(created_timestamp).isoformat()
                updated_at = datetime.fromtimestamp(updated_timestamp).isoformat()
            except (ValueError, TypeError):
                # If conversion fails, keep original values
                processing_time = None
        
        # Estimate completion time for active jobs
        estimated_completion = None
        if status in ['processing', 'queued'] and progress > 0 and processing_time:
            try:
                remaining_progress = 100 - progress
                time_per_percent = processing_time / progress
                estimated_seconds = remaining_progress * time_per_percent
                estimated_completion = f"{estimated_seconds:.1f} seconds"
            except:
                pass
        
        # Get stage-specific information
        stem_separation_info = None
        if 'stem_separation_status' in job_data:
            stem_separation_info = {
                'status': job_data.get('stem_separation_status'),
                'progress': job_data.get('stem_separation_progress'),
                'vocals_path': job_data.get('vocals_path'),
                'drums_path': job_data.get('drums_path'),
                'bass_path': job_data.get('bass_path'),
                'other_path': job_data.get('other_path'),
                'processing_time': job_data.get('stem_separation_time'),
                'error': job_data.get('stem_separation_error')
            }
        
        transcription_info = None
        if 'transcription_status' in job_data:
            transcription_info = {
                'status': job_data.get('transcription_status'),
                'progress': job_data.get('transcription_progress'),
                'transcription_path': job_data.get('transcription_path'),
                'language': job_data.get('transcription_language'),
                'word_count': job_data.get('transcription_word_count'),
                'processing_time': job_data.get('transcription_time'),
                'error': job_data.get('transcription_error')
            }
        
        beat_analysis_info = None
        if 'beat_analysis_status' in job_data:
            beat_analysis_info = {
                'status': job_data.get('beat_analysis_status'),
                'progress': job_data.get('beat_analysis_progress'),
                'tempo_bpm': float(job_data.get('tempo_bpm', 0)) if job_data.get('tempo_bpm') else None,
                'beat_count': int(job_data.get('beat_count', 0)) if job_data.get('beat_count') else None,
                'time_signature': job_data.get('time_signature'),
                'beat_confidence': float(job_data.get('beat_confidence', 0)) if job_data.get('beat_confidence') else None,
                'rhythm_regularity': float(job_data.get('rhythm_regularity', 0)) if job_data.get('rhythm_regularity') else None,
                'processing_time': job_data.get('beat_analysis_time'),
                'error': job_data.get('beat_analysis_error')
            }
        
        # Get summary information
        audio_duration = float(job_data.get('audio_duration', 0)) if job_data.get('audio_duration') else None
        tempo_bpm = float(job_data.get('tempo_bpm', 0)) if job_data.get('tempo_bpm') else None
        beat_count = int(job_data.get('beat_count', 0)) if job_data.get('beat_count') else None
        file_size = int(job_data.get('file_size', 0)) if job_data.get('file_size') else None
        
        # Build response
        response = JobStatusResponse(
            job_id=job_id,
            status=status,
            progress=progress,
            current_step=current_step,
            created_at=created_at,
            updated_at=updated_at,
            estimated_completion=estimated_completion,
            processing_time=processing_time,
            error_message=error_message,
            stem_separation=stem_separation_info,
            transcription=transcription_info,
            beat_analysis=beat_analysis_info,
            audio_duration=audio_duration,
            tempo_bpm=tempo_bpm,
            beat_count=beat_count,
            file_size=file_size
        )
        
        logger.info("Job status retrieved successfully", 
                   job_id=job_id, 
                   status=status, 
                   progress=progress,
                   current_step=current_step)
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("Failed to get job status", 
                    job_id=job_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while retrieving job status"
        )


@router.get("/status/{job_id}/simple")
async def get_simple_job_status(job_id: str):
    """
    Get simplified job status for quick polling.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Basic status information without detailed stage data
    """
    try:
        logger.info("Getting simple job status", job_id=job_id)
        
        with get_redis_client() as redis_client:
            # Check if job exists
            job_exists = redis_client.exists(f"job:{job_id}")
            if not job_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found"
                )
            
            # Get basic status information
            status = redis_client.hget(f"job:{job_id}", 'status') or 'unknown'
            progress = int(redis_client.hget(f"job:{job_id}", 'progress') or 0)
            current_step = redis_client.hget(f"job:{job_id}", 'current_step') or 'unknown'
            error_message = redis_client.hget(f"job:{job_id}", 'error_message')
        
        return {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "error_message": error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get simple job status", 
                    job_id=job_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 