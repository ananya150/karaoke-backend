"""
Upload endpoint for the Karaoke Backend API.
Handles audio file uploads and initiates processing jobs.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time

from models.job import job_manager, JobStatus, ProcessingStep
from utils.file_handler import file_manager
from utils.logger import get_logger

logger = get_logger("upload")
router = APIRouter()


class ProcessResponse(BaseModel):
    """Response model for process endpoint."""
    job_id: str
    status: str
    message: str
    filename: str
    file_size: int
    estimated_time: str


class ProcessingConfig(BaseModel):
    """Processing configuration options."""
    whisper_model: Optional[str] = None
    demucs_model: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    enable_beat_tracking: bool = True
    enable_vocals_extraction: bool = True
    language: Optional[str] = None  # For Whisper transcription


async def validate_upload_requirements(file: UploadFile = File(...)):
    """Dependency to validate upload requirements."""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check if file is empty
    if file.size == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    return file


@router.post("/process", response_model=ProcessResponse)
async def process_audio(
    file: UploadFile = Depends(validate_upload_requirements),
    whisper_model: Optional[str] = Form(None),
    demucs_model: Optional[str] = Form(None),
    audio_sample_rate: Optional[int] = Form(None),
    enable_beat_tracking: bool = Form(True),
    enable_vocals_extraction: bool = Form(True),
    language: Optional[str] = Form(None)
):
    """
    Process audio file endpoint.
    
    Accepts an audio file upload and starts the processing pipeline:
    1. Validates and stores the uploaded file
    2. Creates a processing job
    3. Returns job information for status tracking
    
    Args:
        file: The audio file to process (mp3, wav, m4a, flac)
        whisper_model: Whisper model to use (tiny, base, small, medium, large)
        demucs_model: Demucs model to use for stem separation
        audio_sample_rate: Target sample rate for processing
        enable_beat_tracking: Whether to perform beat analysis
        enable_vocals_extraction: Whether to extract vocal transcription
        language: Language hint for Whisper transcription
    
    Returns:
        ProcessResponse with job_id and processing information
    """
    start_time = time.time()
    
    logger.info(
        "Processing request received",
        filename=file.filename,
        content_type=file.content_type,
        file_size=file.size
    )
    
    try:
        # Create processing configuration
        processing_config = ProcessingConfig(
            whisper_model=whisper_model,
            demucs_model=demucs_model,
            audio_sample_rate=audio_sample_rate,
            enable_beat_tracking=enable_beat_tracking,
            enable_vocals_extraction=enable_vocals_extraction,
            language=language
        ).model_dump(exclude_none=True)
        
        # Create job first to get job_id
        job_data = job_manager.create_job(
            original_filename=file.filename,
            file_size=file.size or 0,  # Will be updated after saving
            file_path="",  # Will be updated after saving
            processing_config=processing_config
        )
        
        job_id = job_data.job_id
        logger.info("Job created", job_id=job_id, filename=file.filename)
        
        try:
            # Update job status to indicate file upload is starting
            job_manager.update_job_status(
                job_id,
                JobStatus.PROCESSING,
                progress=5,
                current_step=ProcessingStep.UPLOAD
            )
            
            # Process file upload
            file_info = await file_manager.process_upload(file, job_id)
            
            # Update job with actual file information
            job_data = job_manager.get_job(job_id)
            job_data.file_path = file_info['file_path']
            job_data.file_size = file_info['file_size']
            job_manager.save_job(job_data)
            
            # Update job status to indicate file upload is complete
            job_manager.update_job_status(
                job_id,
                JobStatus.QUEUED,
                progress=10,
                current_step=ProcessingStep.VALIDATION
            )
            
            # Calculate estimated processing time based on file size
            estimated_minutes = max(1, file_info['file_size'] // (1024 * 1024))  # ~1 min per MB
            estimated_time = f"{estimated_minutes}-{estimated_minutes * 2} minutes"
            
            processing_time = time.time() - start_time
            
            logger.info(
                "File upload completed successfully",
                job_id=job_id,
                filename=file.filename,
                file_size=file_info['file_size'],
                file_hash=file_info['file_hash'],
                processing_time=f"{processing_time:.2f}s"
            )
            
            return ProcessResponse(
                job_id=job_id,
                status=job_data.status.value,
                message="File uploaded successfully. Processing will begin shortly.",
                filename=file.filename,
                file_size=file_info['file_size'],
                estimated_time=estimated_time
            )
            
        except HTTPException as e:
            # If file processing fails, clean up the job
            job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=e.detail,
                current_step=ProcessingStep.UPLOAD
            )
            raise e
        
        except Exception as e:
            # If any other error occurs, clean up the job
            error_msg = f"File processing failed: {str(e)}"
            job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=error_msg,
                current_step=ProcessingStep.UPLOAD
            )
            logger.error("File processing failed", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=error_msg)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("Unexpected error in process endpoint", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the request"
        )


@router.get("/upload-info")
async def get_upload_info():
    """
    Get information about upload requirements and limits.
    
    Returns supported formats, size limits, and processing options.
    """
    from utils.file_handler import FileValidator
    
    return {
        "supported_formats": FileValidator.get_allowed_extensions(),
        "max_file_size_mb": FileValidator.get_max_file_size() // (1024 * 1024),
        "max_file_size_bytes": FileValidator.get_max_file_size(),
        "processing_options": {
            "whisper_models": ["tiny", "base", "small", "medium", "large"],
            "demucs_models": ["htdemucs", "htdemucs_ft", "mdx", "mdx_extra"],
            "supported_languages": ["auto", "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            "sample_rates": [8000, 16000, 22050, 44100, 48000]
        },
        "estimated_processing_time": "1-5 minutes per MB of audio"
    }


@router.delete("/cleanup/{job_id}")
async def cleanup_job_files(job_id: str):
    """
    Clean up files for a specific job.
    
    This endpoint allows manual cleanup of job files.
    Normally, cleanup happens automatically after job completion.
    """
    try:
        # Check if job exists
        job_data = job_manager.get_job(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Clean up files
        success = file_manager.cleanup_job(job_id)
        
        if success:
            logger.info("Manual cleanup completed", job_id=job_id)
            return {"message": "Files cleaned up successfully", "job_id": job_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to clean up files")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cleanup failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Cleanup operation failed") 