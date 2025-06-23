"""
Static file serving endpoint for the Karaoke Backend API.
Handles secure file downloads for processed audio and results.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Query
from fastapi.responses import FileResponse
from fastapi.security.utils import get_authorization_scheme_param

from database.redis_client import get_redis_client
from utils.logger import get_logger
from config import settings

logger = get_logger("static")
router = APIRouter()


def is_safe_path(basedir: str, path: str) -> bool:
    """
    Check if the requested path is safe (within the base directory).
    Prevents directory traversal attacks.
    """
    try:
        basedir = os.path.abspath(basedir)
        path = os.path.abspath(os.path.join(basedir, path))
        return path.startswith(basedir)
    except:
        return False


def get_file_mime_type(file_path: str) -> str:
    """Get the MIME type for a file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # Default MIME types for common audio formats
    if mime_type is None:
        ext = os.path.splitext(file_path)[1].lower()
        audio_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.srt': 'text/plain'
        }
        mime_type = audio_types.get(ext, 'application/octet-stream')
    
    return mime_type


@router.get("/files/{job_id}/{filename}")
async def download_file(
    job_id: str, 
    filename: str,
    inline: bool = Query(False, description="Whether to display file inline or as attachment")
):
    """
    Download a processed file for a specific job.
    """
    try:
        logger.info("File download request", job_id=job_id, filename=filename, inline=inline)
        with get_redis_client() as redis_client:
            job_exists = redis_client.exists(f"job:{job_id}")
            logger.info("Job exists check", job_id=job_id, exists=job_exists)
            
            if not job_exists:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            job_data = redis_client.hgetall(f"job:{job_id}")
            original_file_path = job_data.get('file_path')
            logger.info("Got job data", original_file_path=original_file_path)
            
            if original_file_path:
                job_dir = os.path.dirname(original_file_path)
            else:
                job_dir = None
            
            logger.info("Job directory", job_dir=job_dir, exists=os.path.exists(job_dir) if job_dir else False)
        
        if not job_dir or not os.path.exists(job_dir):
            raise HTTPException(status_code=404, detail="Job files not found")
        
        # Search in multiple directories
        search_directories = [
            ("stems", "stems"),
            ("beat_analysis", "beat_analysis"),
            ("transcription", "transcription"),
            ("results", "results"),
            ("", "root")  # Root job directory
        ]
        
        found_path = None
        found_mime_type = None
        
        for subdir, dir_name in search_directories:
            if subdir:
                search_path = os.path.join(job_dir, subdir, filename)
            else:
                search_path = os.path.join(job_dir, filename)
            
            logger.info(f"Checking {dir_name} directory", search_path=search_path, exists=os.path.exists(search_path))
            
            if os.path.exists(search_path):
                found_path = search_path
                found_mime_type = get_file_mime_type(search_path)
                logger.info(f"Found file in {dir_name} directory", path=found_path, mime_type=found_mime_type)
                break
        
        if found_path:
            # Determine content disposition
            disposition = "inline" if inline else "attachment"
            
            return FileResponse(
                path=found_path,
                filename=filename,
                media_type=found_mime_type,
                headers={
                    "Content-Disposition": f'{disposition}; filename="{filename}"',
                    "X-Job-ID": job_id
                }
            )
        
        # If not found, return 404
        logger.warning("File not found anywhere", job_id=job_id, filename=filename)
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in file serving", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/files/{job_id}")
async def list_job_files(job_id: str):
    """
    List all available files for a job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        List of available files with metadata
        
    Raises:
        HTTPException: 404 if job not found, 500 for internal errors
    """
    try:
        logger.info("Listing job files", job_id=job_id)
        
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
            file_path = job_data.get('file_path')
            
            # Extract job directory from file path
            if file_path:
                job_dir = os.path.dirname(file_path)
            else:
                job_dir = None
        
        if not job_dir or not os.path.exists(job_dir):
            raise HTTPException(
                status_code=404,
                detail="Job files not found"
            )
        
        # Collect all files
        files = []
        
        def add_files_from_dir(directory: str, category: str):
            """Helper function to add files from a directory."""
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            mime_type = get_file_mime_type(file_path)
                            
                            files.append({
                                "filename": file,
                                "category": category,
                                "size": file_size,
                                "mime_type": mime_type,
                                "download_url": f"/api/files/{job_id}/{file}",
                                "preview_url": f"/api/files/{job_id}/{file}?inline=true" if mime_type.startswith(('audio/', 'text/', 'application/json')) else None
                            })
                        except:
                            pass  # Skip files that can't be accessed
        
        # Add files from different categories
        add_files_from_dir(os.path.join(job_dir, "stems"), "stem_separation")
        add_files_from_dir(os.path.join(job_dir, "transcription"), "transcription")
        add_files_from_dir(os.path.join(job_dir, "beat_analysis"), "beat_analysis")
        add_files_from_dir(os.path.join(job_dir, "results"), "results")
        add_files_from_dir(job_dir, "general")  # Files directly in job directory
        
        # Sort files by category and filename
        files.sort(key=lambda x: (x['category'], x['filename']))
        
        logger.info("Job files listed", job_id=job_id, file_count=len(files))
        
        return {
            "job_id": job_id,
            "file_count": len(files),
            "files": files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list job files", 
                    job_id=job_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while listing files"
        )


@router.head("/files/{job_id}/{filename}")
async def check_file_exists(job_id: str, filename: str):
    """
    Check if a file exists without downloading it (HEAD request).
    
    Args:
        job_id: Unique job identifier
        filename: Name of the file to check
        
    Returns:
        Response with headers indicating file existence and metadata
    """
    try:
        with get_redis_client() as redis_client:
            # Check if job exists
            job_exists = redis_client.exists(f"job:{job_id}")
            if not job_exists:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Get job data
            job_data = redis_client.hgetall(f"job:{job_id}")
            job_dir = job_data.get('job_dir')
        
        if not job_dir or not os.path.exists(job_dir):
            raise HTTPException(status_code=404, detail="Job files not found")
        
        # Check file existence (same logic as download_file)
        file_path = os.path.join(job_dir, filename)
        
        if not is_safe_path(job_dir, filename):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not os.path.exists(file_path):
            # Try subdirectories
            possible_paths = [
                os.path.join(job_dir, "stems", filename),
                os.path.join(job_dir, "transcription", filename),
                os.path.join(job_dir, "beat_analysis", filename),
                os.path.join(job_dir, "results", filename)
            ]
            
            for possible_path in possible_paths:
                if os.path.exists(possible_path) and is_safe_path(job_dir, os.path.relpath(possible_path, job_dir)):
                    file_path = possible_path
                    break
            else:
                raise HTTPException(status_code=404, detail="File not found")
        
        # Get file metadata
        file_size = os.path.getsize(file_path)
        mime_type = get_file_mime_type(file_path)
        
        # Return response with headers but no body
        return Response(
            content="",
            headers={
                "Content-Type": mime_type,
                "Content-Length": str(file_size),
                "X-Job-ID": job_id,
                "X-File-Exists": "true"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check file existence", 
                    job_id=job_id, 
                    filename=filename, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") 