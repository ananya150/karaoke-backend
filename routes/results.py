"""
Results endpoint for the Karaoke Backend API.
Handles job results retrieval and file serving.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database.redis_client import get_redis_client
from models.job import JobStatus
from utils.logger import get_logger

logger = get_logger("results")
router = APIRouter()


class StemSeparationResults(BaseModel):
    """Results for stem separation."""
    vocals_path: Optional[str] = None
    drums_path: Optional[str] = None
    bass_path: Optional[str] = None
    other_path: Optional[str] = None
    processing_time: Optional[float] = None
    separation_model: Optional[str] = None


class TranscriptionResults(BaseModel):
    """Results for vocal transcription."""
    transcription_path: Optional[str] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    processing_time: Optional[float] = None
    confidence: Optional[float] = None


class BeatAnalysisResults(BaseModel):
    """Results for beat analysis."""
    tempo_bpm: Optional[float] = None
    beat_count: Optional[int] = None
    time_signature: Optional[str] = None
    beat_confidence: Optional[float] = None
    rhythm_regularity: Optional[float] = None
    analysis_json: Optional[str] = None
    beats_json: Optional[str] = None
    onsets_json: Optional[str] = None
    processing_time: Optional[float] = None


class JobResults(BaseModel):
    """Complete job results."""
    job_id: str
    status: str
    progress: int
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_processing_time: Optional[float] = None
    
    # Original file information
    original_filename: Optional[str] = None
    audio_duration: Optional[float] = None
    file_size: Optional[int] = None
    
    # Processing results
    stem_separation: Optional[StemSeparationResults] = None
    transcription: Optional[TranscriptionResults] = None
    beat_analysis: Optional[BeatAnalysisResults] = None
    
    # Output files
    output_files: Optional[List[str]] = None
    download_links: Optional[Dict[str, str]] = None


@router.get("/results/{job_id}", response_model=JobResults)
async def get_job_results(job_id: str):
    """
    Get comprehensive job results and processed files.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Complete job results including all processed files and metadata
        
    Raises:
        HTTPException: 404 if job not found, 409 if job not completed, 500 for internal errors
    """
    try:
        logger.info("Getting job results", job_id=job_id)
        
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
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} data not found"
                )
        
        # Check if job is completed
        status = job_data.get('status', 'unknown')
        if status not in ['COMPLETED', 'completed', 'completed_with_errors']:
            logger.warning("Job not completed", job_id=job_id, status=status)
            raise HTTPException(
                status_code=409,
                detail=f"Job {job_id} is not completed yet. Current status: {status}"
            )
        
        # Parse basic information
        progress = int(job_data.get('progress', 0))
        
        # Convert timestamps to ISO format strings
        created_at = None
        completed_at = None
        
        if job_data.get('created_at'):
            try:
                from datetime import datetime
                created_timestamp = float(job_data.get('created_at'))
                created_at = datetime.fromtimestamp(created_timestamp).isoformat()
            except (ValueError, TypeError):
                pass
                
        if job_data.get('updated_at'):
            try:
                from datetime import datetime
                completed_timestamp = float(job_data.get('updated_at'))
                completed_at = datetime.fromtimestamp(completed_timestamp).isoformat()
            except (ValueError, TypeError):
                pass
        
        # Calculate total processing time
        total_processing_time = None
        if created_at and completed_at:
            try:
                from datetime import datetime
                created_dt = datetime.fromisoformat(created_at)
                completed_dt = datetime.fromisoformat(completed_at)
                total_processing_time = (completed_dt - created_dt).total_seconds()
            except:
                pass
        
        # Get original file information
        original_filename = job_data.get('original_filename')
        audio_duration = float(job_data.get('audio_duration', 0)) if job_data.get('audio_duration') else None
        file_size = int(job_data.get('file_size', 0)) if job_data.get('file_size') else None
        
        # Build stem separation results
        stem_separation = None
        if job_data.get('stem_separation_status') == 'completed':
            stem_separation = StemSeparationResults(
                vocals_path=job_data.get('vocals_path'),
                drums_path=job_data.get('drums_path'),
                bass_path=job_data.get('bass_path'),
                other_path=job_data.get('other_path'),
                processing_time=float(job_data.get('stem_separation_time', 0)) if job_data.get('stem_separation_time') else None,
                separation_model=job_data.get('stem_separation_model', 'htdemucs')
            )
        
        # Build transcription results
        transcription = None
        if job_data.get('transcription_status') == 'completed':
            transcription = TranscriptionResults(
                transcription_path=job_data.get('transcription_path'),
                language=job_data.get('transcription_language'),
                word_count=int(job_data.get('transcription_word_count', 0)) if job_data.get('transcription_word_count') else None,
                processing_time=float(job_data.get('transcription_time', 0)) if job_data.get('transcription_time') else None,
                confidence=float(job_data.get('transcription_confidence', 0)) if job_data.get('transcription_confidence') else None
            )
        
        # Build beat analysis results
        beat_analysis = None
        if job_data.get('beat_analysis_status') == 'completed':
            beat_analysis = BeatAnalysisResults(
                tempo_bpm=float(job_data.get('tempo_bpm', 0)) if job_data.get('tempo_bpm') else None,
                beat_count=int(job_data.get('beat_count', 0)) if job_data.get('beat_count') else None,
                time_signature=job_data.get('time_signature'),
                beat_confidence=float(job_data.get('beat_confidence', 0)) if job_data.get('beat_confidence') else None,
                rhythm_regularity=float(job_data.get('rhythm_regularity', 0)) if job_data.get('rhythm_regularity') else None,
                analysis_json=job_data.get('beat_analysis_json'),
                beats_json=job_data.get('beats_json'),
                onsets_json=job_data.get('onsets_json'),
                processing_time=float(job_data.get('beat_analysis_time', 0)) if job_data.get('beat_analysis_time') else None
            )
        
        # Collect all output files
        output_files = []
        download_links = {}
        
        # Add stem files
        if stem_separation:
            for stem_type, path in [
                ('vocals', stem_separation.vocals_path),
                ('drums', stem_separation.drums_path),
                ('bass', stem_separation.bass_path),
                ('other', stem_separation.other_path)
            ]:
                if path and os.path.exists(path):
                    output_files.append(path)
                    download_links[f"{stem_type}_stem"] = f"/files/{job_id}/{os.path.basename(path)}"
        
        # Add transcription files
        if transcription and transcription.transcription_path and os.path.exists(transcription.transcription_path):
            output_files.append(transcription.transcription_path)
            download_links["transcription"] = f"/files/{job_id}/{os.path.basename(transcription.transcription_path)}"
        
        # Add beat analysis files
        if beat_analysis:
            for analysis_type, path in [
                ('analysis', beat_analysis.analysis_json),
                ('beats', beat_analysis.beats_json),
                ('onsets', beat_analysis.onsets_json)
            ]:
                if path and os.path.exists(path):
                    output_files.append(path)
                    download_links[f"beat_{analysis_type}"] = f"/files/{job_id}/{os.path.basename(path)}"
        
        # Build response
        results = JobResults(
            job_id=job_id,
            status=status,
            progress=progress,
            created_at=created_at,
            completed_at=completed_at,
            total_processing_time=total_processing_time,
            original_filename=original_filename,
            audio_duration=audio_duration,
            file_size=file_size,
            stem_separation=stem_separation,
            transcription=transcription,
            beat_analysis=beat_analysis,
            output_files=output_files,
            download_links=download_links
        )
        
        logger.info("Job results retrieved successfully", 
                   job_id=job_id, 
                   status=status,
                   output_files_count=len(output_files),
                   total_processing_time=total_processing_time)
        
        return results
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("Failed to get job results", 
                    job_id=job_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while retrieving job results"
        )


@router.get("/results/{job_id}/summary")
async def get_job_results_summary(job_id: str):
    """
    Get a summary of job results without file paths.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Summary of processing results and key metrics
    """
    try:
        logger.info("Getting job results summary", job_id=job_id)
        
        with get_redis_client() as redis_client:
            # Check if job exists
            job_exists = redis_client.exists(f"job:{job_id}")
            if not job_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found"
                )
            
            # Get job data
            job_data = redis_client.hgetall(f"job:{job_id}")
        
        # Build summary
        summary = {
            "job_id": job_id,
            "status": job_data.get('status', 'unknown'),
            "progress": int(job_data.get('progress', 0)),
            "audio_duration": float(job_data.get('audio_duration', 0)) if job_data.get('audio_duration') else None,
            "processing_completed": {
                "stem_separation": job_data.get('stem_separation_status') == 'completed',
                "transcription": job_data.get('transcription_status') == 'completed',
                "beat_analysis": job_data.get('beat_analysis_status') == 'completed'
            },
            "key_metrics": {
                "tempo_bpm": float(job_data.get('tempo_bpm', 0)) if job_data.get('tempo_bpm') else None,
                "beat_count": int(job_data.get('beat_count', 0)) if job_data.get('beat_count') else None,
                "time_signature": job_data.get('time_signature'),
                "transcription_language": job_data.get('transcription_language')
            }
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job results summary", 
                    job_id=job_id, 
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 