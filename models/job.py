"""
Job model and state management for the Karaoke Backend.
Handles job creation, status tracking, progress monitoring, and persistence.
"""

import uuid
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from database.redis_client import redis_client
from utils.logger import get_logger
from config import settings

logger = get_logger("job_model")


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SPLITTING_STEMS = "SPLITTING_STEMS"
    TRANSCRIBING_VOCALS = "TRANSCRIBING_VOCALS"
    ANALYZING_BEATS = "ANALYZING_BEATS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ProcessingStep(str, Enum):
    """Processing step enumeration."""
    UPLOAD = "UPLOAD"
    VALIDATION = "VALIDATION"
    PROCESSING = "PROCESSING"
    STEM_SEPARATION = "STEM_SEPARATION"
    VOCAL_TRANSCRIPTION = "VOCAL_TRANSCRIPTION"
    BEAT_ANALYSIS = "BEAT_ANALYSIS"
    FINALIZATION = "FINALIZATION"
    COMPLETED = "COMPLETED"


class JobData(BaseModel):
    """Job data model."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Current job status")
    progress: int = Field(default=0, description="Progress percentage (0-100)")
    current_step: Optional[ProcessingStep] = Field(default=None, description="Current processing step")
    
    # File information
    original_filename: Optional[str] = Field(default=None, description="Original uploaded filename")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    file_path: Optional[str] = Field(default=None, description="Path to uploaded file")
    
    # Processing results
    stems: Dict[str, str] = Field(default_factory=dict, description="Paths to stem files")
    lyrics: Optional[Dict[str, Any]] = Field(default=None, description="Lyrics with timestamps")
    beats: Optional[Dict[str, Any]] = Field(default=None, description="Beat analysis data")
    
    # Metadata
    created_at: float = Field(default_factory=time.time, description="Job creation timestamp")
    updated_at: float = Field(default_factory=time.time, description="Last update timestamp")
    started_at: Optional[float] = Field(default=None, description="Processing start timestamp")
    completed_at: Optional[float] = Field(default=None, description="Processing completion timestamp")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_step: Optional[ProcessingStep] = Field(default=None, description="Step where error occurred")
    
    # Configuration
    processing_config: Dict[str, Any] = Field(default_factory=dict, description="Processing configuration")
    
    # Task tracking
    task_id: Optional[str] = Field(default=None, description="Celery task ID for background processing")


class JobManager:
    """Job management class for handling job lifecycle and persistence."""
    
    def __init__(self):
        self.redis = redis_client
    
    def generate_job_id(self) -> str:
        """Generate a unique job ID."""
        return str(uuid.uuid4())
    
    def create_job(self, 
                   original_filename: str,
                   file_size: int,
                   file_path: str,
                   processing_config: Optional[Dict[str, Any]] = None) -> JobData:
        """Create a new job."""
        job_id = self.generate_job_id()
        
        job_data = JobData(
            job_id=job_id,
            original_filename=original_filename,
            file_size=file_size,
            file_path=file_path,
            processing_config=processing_config or {}
        )
        
        # Save to Redis
        if self.save_job(job_data):
            logger.info("Job created successfully", job_id=job_id, filename=original_filename)
            return job_data
        else:
            logger.error("Failed to save job to Redis", job_id=job_id)
            raise RuntimeError(f"Failed to create job {job_id}")
    
    def save_job(self, job_data: JobData) -> bool:
        """Save job data to Redis."""
        try:
            job_data.updated_at = time.time()
            
            # Convert to dict for storage
            job_dict = job_data.model_dump()
            
            # Store job data as hash
            job_key = f"job:{job_data.job_id}"
            success = self.redis.hset(job_key, job_dict)
            
            # Set expiration (cleanup after job timeout + buffer)
            expiry_seconds = settings.job_timeout + settings.cleanup_interval
            self.redis.expire(job_key, expiry_seconds)
            
            # Only add to indices if this is a new job (not already in the index)
            # Use a simpler approach - check if job exists in a set instead
            job_exists_key = "jobs:exists"
            if not self.redis.client.sismember(job_exists_key, job_data.job_id):
                self.redis.lpush("jobs:all", job_data.job_id)
                self.redis.client.sadd(job_exists_key, job_data.job_id)
            
            # Always add to status index (remove duplicates later if needed)
            # Handle case where status might be None
            if job_data.status is not None and hasattr(job_data.status, 'value'):
                status_key = f"jobs:status:{job_data.status.value}"
                self.redis.lpush(status_key, job_data.job_id)
            else:
                logger.warning("Job status is None or invalid, skipping status index", job_id=job_data.job_id)
            
            # Check if job exists in Redis to determine success
            # hset returns 0 when updating existing fields with same values
            job_exists = self.redis.exists(job_key)
            return job_exists
            
        except Exception as e:
            logger.error("Failed to save job", job_id=job_data.job_id, error=str(e), exc_info=True)
            return False
    
    def get_job(self, job_id: str) -> Optional[JobData]:
        """Get job data by ID."""
        try:
            job_key = f"job:{job_id}"
            job_dict = self.redis.hgetall(job_key)
            
            if not job_dict:
                return None
            
            # Convert Redis string values to appropriate types
            # Handle numeric fields
            for field in ['progress', 'file_size', 'created_at', 'updated_at', 'started_at', 'completed_at']:
                if field in job_dict and job_dict[field] is not None and job_dict[field] != 'None':
                    if field in ['progress', 'file_size']:
                        job_dict[field] = int(job_dict[field])
                    else:
                        job_dict[field] = float(job_dict[field])
                elif field in job_dict and job_dict[field] == 'None':
                    job_dict[field] = None
            
            # Handle JSON fields
            import json
            for field in ['stems', 'lyrics', 'beats', 'processing_config']:
                if field in job_dict and job_dict[field] is not None and job_dict[field] != 'None':
                    try:
                        job_dict[field] = json.loads(job_dict[field])
                    except (json.JSONDecodeError, TypeError):
                        job_dict[field] = {} if field in ['stems', 'processing_config'] else None
                elif field in job_dict and job_dict[field] == 'None':
                    job_dict[field] = {} if field in ['stems', 'processing_config'] else None
            
            # Handle enum fields - convert string values back to enums
            if 'status' in job_dict and job_dict['status'] and job_dict['status'] != 'None' and job_dict['status'] is not None:
                try:
                    job_dict['status'] = JobStatus(job_dict['status'])
                except ValueError:
                    # Fallback to QUEUED if invalid status
                    job_dict['status'] = JobStatus.QUEUED
            else:
                # Default to QUEUED if status is None, "None", or missing
                job_dict['status'] = JobStatus.QUEUED
            
            if 'current_step' in job_dict and job_dict['current_step'] and job_dict['current_step'] != 'None' and job_dict['current_step'] is not None:
                try:
                    job_dict['current_step'] = ProcessingStep(job_dict['current_step'])
                except ValueError:
                    job_dict['current_step'] = None
            else:
                job_dict['current_step'] = None
            
            if 'error_step' in job_dict and job_dict['error_step'] and job_dict['error_step'] != 'None' and job_dict['error_step'] is not None:
                try:
                    job_dict['error_step'] = ProcessingStep(job_dict['error_step'])
                except ValueError:
                    job_dict['error_step'] = None
            else:
                job_dict['error_step'] = None
            
            # Convert back to JobData model
            return JobData(**job_dict)
            
        except Exception as e:
            logger.error("Failed to get job", job_id=job_id, error=str(e), exc_info=True)
            return None
    
    def update_job_status(self, job_id: str, status: JobStatus, 
                          progress: Optional[int] = None,
                          current_step: Optional[ProcessingStep] = None,
                          error_message: Optional[str] = None) -> bool:
        """Update job status and progress."""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                logger.warning("Job not found for status update", job_id=job_id)
                return False
            
            # Remove from old status index (if status is changing)
            if job_data.status != status and job_data.status is not None:
                old_status_key = f"jobs:status:{job_data.status.value}"
                self.redis.client.lrem(old_status_key, 1, job_id)
            
            # Update job data
            job_data.status = status
            job_data.updated_at = time.time()
            
            if progress is not None:
                job_data.progress = min(100, max(0, progress))
            
            if current_step is not None:
                job_data.current_step = current_step
            
            if error_message is not None:
                job_data.error_message = error_message
                if current_step is not None:
                    job_data.error_step = current_step
            
            # Set timestamps based on status
            if status == JobStatus.PROCESSING and job_data.started_at is None:
                job_data.started_at = time.time()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job_data.completed_at = time.time()
                if status == JobStatus.COMPLETED:
                    job_data.progress = 100
            
            # Save updated job data
            if self.save_job(job_data):
                status_value = status.value if status and hasattr(status, 'value') else str(status)
                logger.log_job_event(job_id, "status_updated", 
                                    status=status_value, progress=job_data.progress)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to update job status", job_id=job_id, error=str(e), exc_info=True)
            return False
    
    def update_job_progress(self, job_id: str, progress: int, 
                           current_step: Optional[ProcessingStep] = None) -> bool:
        """Update job progress."""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                return False
            
            job_data.progress = min(100, max(0, progress))
            job_data.updated_at = time.time()
            
            if current_step is not None:
                job_data.current_step = current_step
            
            # Update status based on progress
            if job_data.status == JobStatus.QUEUED and progress > 0:
                job_data.status = JobStatus.PROCESSING
                if job_data.started_at is None:
                    job_data.started_at = time.time()
            
            return self.save_job(job_data)
            
        except Exception as e:
            logger.error("Failed to update job progress", job_id=job_id, error=str(e))
            return False
    
    def update_task_status(self, job_id: str, task_name: str, status: str, 
                          progress: int = 0, error: Optional[str] = None, 
                          **kwargs) -> bool:
        """Update individual task status within a job."""
        try:
            job_key = f"job:{job_id}"
            
            # Update task-specific fields
            task_fields = {
                f"{task_name}_status": status,
                f"{task_name}_progress": str(progress),
                f"{task_name}_updated_at": str(time.time())
            }
            
            if error:
                task_fields[f"{task_name}_error"] = error
            
            # Add any additional task-specific fields
            for key, value in kwargs.items():
                task_fields[f"{task_name}_{key}"] = str(value) if value is not None else None
            
            # Update Redis hash
            success = self.redis.hset(job_key, task_fields)
            
            if success:
                logger.info("Task status updated", job_id=job_id, task=task_name, status=status, progress=progress)
            else:
                logger.error("Failed to update task status", job_id=job_id, task=task_name)
            
            return bool(success)
            
        except Exception as e:
            logger.error("Failed to update task status", job_id=job_id, task=task_name, error=str(e), exc_info=True)
            return False
    
    def set_job_results(self, job_id: str, 
                       stems: Optional[Dict[str, str]] = None,
                       lyrics: Optional[Dict[str, Any]] = None,
                       beats: Optional[Dict[str, Any]] = None) -> bool:
        """Set job processing results."""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                return False
            
            if stems is not None:
                job_data.stems = stems
            
            if lyrics is not None:
                job_data.lyrics = lyrics
            
            if beats is not None:
                job_data.beats = beats
            
            job_data.updated_at = time.time()
            
            return self.save_job(job_data)
            
        except Exception as e:
            logger.error("Failed to set job results", job_id=job_id, error=str(e))
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job and all associated data."""
        try:
            job_data = self.get_job(job_id)
            if not job_data:
                return True  # Already deleted
            
            # Remove from indices
            self.redis.client.lrem("jobs:all", 1, job_id)
            if job_data.status is not None:
                status_key = f"jobs:status:{job_data.status.value}"
                self.redis.client.lrem(status_key, 1, job_id)
            
            # Remove from exists set
            self.redis.client.srem("jobs:exists", job_id)
            
            # Delete job data
            job_key = f"job:{job_id}"
            self.redis.delete(job_key)
            
            logger.info("Job deleted", job_id=job_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete job", job_id=job_id, error=str(e))
            return False
    
    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[JobData]:
        """List jobs, optionally filtered by status."""
        try:
            if status:
                job_ids = self.redis.client.lrange(f"jobs:status:{status.value}", 0, limit - 1)
            else:
                job_ids = self.redis.client.lrange("jobs:all", 0, limit - 1)
            
            jobs = []
            for job_id in job_ids:
                job_data = self.get_job(job_id)
                if job_data:
                    jobs.append(job_data)
            
            return jobs
            
        except Exception as e:
            logger.error("Failed to list jobs", error=str(e))
            return []
    
    def cleanup_expired_jobs(self) -> int:
        """Clean up expired jobs."""
        try:
            cutoff_time = time.time() - settings.cleanup_interval
            all_job_ids = self.redis.client.lrange("jobs:all", 0, -1)
            
            cleaned_count = 0
            for job_id in all_job_ids:
                job_data = self.get_job(job_id)
                if job_data and job_data.updated_at < cutoff_time:
                    if job_data.status not in [JobStatus.PROCESSING]:
                        self.delete_job(job_id)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info("Cleaned up expired jobs", count=cleaned_count)
            
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup expired jobs", error=str(e))
            return 0
    
    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics."""
        try:
            stats = {
                "total_jobs": self.redis.llen("jobs:all"),
                "by_status": {}
            }
            
            for status in JobStatus:
                count = self.redis.llen(f"jobs:status:{status.value}")
                stats["by_status"][status.value] = count
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get job stats", error=str(e))
            return {"error": str(e)}


# Global job manager instance
job_manager = JobManager() 