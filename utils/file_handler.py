"""
File handling utilities for the Karaoke Backend.
Handles file validation, storage, cleanup, and security.
"""

import os
import shutil
import hashlib
import magic
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from fastapi import UploadFile, HTTPException
import aiofiles

from config import settings
from utils.logger import get_logger

logger = get_logger("file_handler")


class FileValidator:
    """File validation and security checks."""
    
    # Supported audio formats and their MIME types
    SUPPORTED_FORMATS = {
        'mp3': ['audio/mpeg', 'audio/mp3'],
        'wav': ['audio/wav', 'audio/wave', 'audio/x-wav'],
        'm4a': ['audio/mp4', 'audio/x-m4a'],
        'flac': ['audio/flac', 'audio/x-flac'],
        'ogg': ['audio/ogg', 'audio/x-vorbis+ogg'],
        'aac': ['audio/aac', 'audio/x-aac']
    }
    
    # Maximum file sizes (can be overridden by config)
    DEFAULT_MAX_SIZE = 200 * 1024 * 1024  # 200MB
    
    @classmethod
    def get_allowed_extensions(cls) -> List[str]:
        """Get list of allowed file extensions from config."""
        return settings.allowed_extensions_list
    
    @classmethod
    def get_max_file_size(cls) -> int:
        """Get maximum file size in bytes from config."""
        return settings.max_file_size_bytes
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """Validate filename for security."""
        if not filename:
            return False
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for null bytes
        if '\x00' in filename:
            return False
        
        # Check filename length
        if len(filename) > 255:
            return False
        
        # Check for valid extension
        extension = cls._get_file_extension(filename)
        return extension in cls.get_allowed_extensions()
    
    @classmethod
    def validate_file_size(cls, file_size: int) -> bool:
        """Validate file size."""
        max_size = cls.get_max_file_size()
        return 0 < file_size <= max_size
    
    @classmethod
    def validate_mime_type(cls, file_path: str, filename: str) -> bool:
        """Validate MIME type using python-magic."""
        try:
            # Get MIME type from file content
            mime_type = magic.from_file(file_path, mime=True)
            
            # Get expected MIME types for file extension
            extension = cls._get_file_extension(filename)
            expected_mimes = cls.SUPPORTED_FORMATS.get(extension, [])
            
            # Check if detected MIME type matches expected
            if mime_type in expected_mimes:
                return True
            
            logger.warning(
                "MIME type mismatch",
                filename=filename,
                detected_mime=mime_type,
                expected_mimes=expected_mimes
            )
            return False
            
        except Exception as e:
            logger.error("Failed to validate MIME type", filename=filename, error=str(e))
            return False
    
    @classmethod
    def _get_file_extension(cls, filename: str) -> str:
        """Get file extension in lowercase."""
        return Path(filename).suffix.lower().lstrip('.')


class FileStorage:
    """File storage management."""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_folder)
        self.jobs_dir = Path(settings.jobs_folder)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set proper permissions
        os.chmod(self.upload_dir, 0o755)
        os.chmod(self.jobs_dir, 0o755)
    
    def create_job_directory(self, job_id: str) -> Path:
        """Create directory structure for a job."""
        job_dir = self.jobs_dir / job_id
        
        # Create main job directory
        job_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        subdirs = ['stems', 'temp', 'output']
        for subdir in subdirs:
            (job_dir / subdir).mkdir(exist_ok=True)
        
        # Set permissions
        os.chmod(job_dir, 0o755)
        for subdir in subdirs:
            os.chmod(job_dir / subdir, 0o755)
        
        logger.info("Created job directory", job_id=job_id, path=str(job_dir))
        return job_dir
    
    async def save_upload_file(self, upload_file: UploadFile, job_id: str) -> Tuple[str, str]:
        """Save uploaded file and return file path and hash."""
        # Create job directory
        job_dir = self.create_job_directory(job_id)
        
        # Generate safe filename
        safe_filename = self._generate_safe_filename(upload_file.filename)
        file_path = job_dir / safe_filename
        
        # Save file with chunked writing for memory efficiency
        file_hash = hashlib.sha256()
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                while chunk := await upload_file.read(8192):  # 8KB chunks
                    file_hash.update(chunk)
                    await f.write(chunk)
            
            # Set file permissions
            os.chmod(file_path, 0o644)
            
            file_hash_hex = file_hash.hexdigest()
            logger.info(
                "File saved successfully",
                job_id=job_id,
                filename=safe_filename,
                file_hash=file_hash_hex,
                file_size=file_path.stat().st_size
            )
            
            return str(file_path), file_hash_hex
            
        except Exception as e:
            # Cleanup on failure
            if file_path.exists():
                file_path.unlink()
            logger.error("Failed to save file", job_id=job_id, error=str(e))
            raise
    
    def _generate_safe_filename(self, original_filename: str) -> str:
        """Generate a safe filename preserving extension."""
        if not original_filename:
            return "uploaded_file"
        
        # Get file extension
        path = Path(original_filename)
        extension = path.suffix.lower()
        
        # Use original name but sanitized
        base_name = path.stem
        # Remove potentially dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        safe_name = ''.join(c for c in base_name if c in safe_chars)
        
        # Ensure name is not empty
        if not safe_name:
            safe_name = "uploaded_file"
        
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name + extension
    
    def cleanup_job_files(self, job_id: str) -> bool:
        """Clean up all files for a job."""
        job_dir = self.jobs_dir / job_id
        
        if not job_dir.exists():
            return True
        
        try:
            shutil.rmtree(job_dir)
            logger.info("Cleaned up job files", job_id=job_id)
            return True
        except Exception as e:
            logger.error("Failed to cleanup job files", job_id=job_id, error=str(e))
            return False
    
    def get_job_file_info(self, job_id: str) -> Dict[str, any]:
        """Get information about files in a job directory."""
        job_dir = self.jobs_dir / job_id
        
        if not job_dir.exists():
            return {}
        
        info = {
            'job_dir': str(job_dir),
            'total_size': 0,
            'files': {}
        }
        
        try:
            for file_path in job_dir.rglob('*'):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    relative_path = file_path.relative_to(job_dir)
                    info['files'][str(relative_path)] = {
                        'size': size,
                        'path': str(file_path)
                    }
                    info['total_size'] += size
            
            return info
            
        except Exception as e:
            logger.error("Failed to get job file info", job_id=job_id, error=str(e))
            return {}
    
    def cleanup_orphaned_files(self, active_job_ids: List[str]) -> int:
        """Clean up files for jobs that no longer exist."""
        if not self.jobs_dir.exists():
            return 0
        
        cleaned_count = 0
        
        try:
            for job_dir in self.jobs_dir.iterdir():
                if job_dir.is_dir() and job_dir.name not in active_job_ids:
                    try:
                        shutil.rmtree(job_dir)
                        cleaned_count += 1
                        logger.info("Cleaned up orphaned job files", job_id=job_dir.name)
                    except Exception as e:
                        logger.error(
                            "Failed to cleanup orphaned files",
                            job_id=job_dir.name,
                            error=str(e)
                        )
            
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup orphaned files", error=str(e))
            return 0


class FileManager:
    """High-level file management interface."""
    
    def __init__(self):
        self.validator = FileValidator()
        self.storage = FileStorage()
    
    async def process_upload(self, upload_file: UploadFile, job_id: str) -> Dict[str, any]:
        """Process file upload with full validation and storage."""
        try:
            # Validate filename
            if not self.validator.validate_filename(upload_file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid filename: {upload_file.filename}"
                )
            
            # Validate file size
            if upload_file.size and not self.validator.validate_file_size(upload_file.size):
                max_size_mb = self.validator.get_max_file_size() // (1024 * 1024)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {max_size_mb}MB"
                )
            
            # Save file
            file_path, file_hash = await self.storage.save_upload_file(upload_file, job_id)
            
            # Get actual file size
            actual_size = Path(file_path).stat().st_size
            
            # Validate file size again (in case size wasn't provided)
            if not self.validator.validate_file_size(actual_size):
                # Cleanup and raise error
                Path(file_path).unlink()
                max_size_mb = self.validator.get_max_file_size() // (1024 * 1024)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {max_size_mb}MB"
                )
            
            # Validate MIME type
            if not self.validator.validate_mime_type(file_path, upload_file.filename):
                # Cleanup and raise error
                Path(file_path).unlink()
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file format. Supported formats: " + 
                           ", ".join(self.validator.get_allowed_extensions())
                )
            
            result = {
                'filename': upload_file.filename,
                'file_path': file_path,
                'file_size': actual_size,
                'file_hash': file_hash,
                'content_type': upload_file.content_type
            }
            
            logger.info(
                "File upload processed successfully",
                job_id=job_id,
                filename=upload_file.filename,
                file_size=actual_size
            )
            
            return result
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error("File upload processing failed", job_id=job_id, error=str(e))
            raise HTTPException(
                status_code=500,
                detail="Failed to process file upload"
            )
    
    def cleanup_job(self, job_id: str) -> bool:
        """Clean up all files for a job."""
        return self.storage.cleanup_job_files(job_id)
    
    def get_job_info(self, job_id: str) -> Dict[str, any]:
        """Get file information for a job."""
        return self.storage.get_job_file_info(job_id)


# Global file manager instance
file_manager = FileManager() 