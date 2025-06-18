"""
Configuration management for the Karaoke Backend application.
Handles environment variables and provides default values.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application Configuration
    app_name: str = Field(default="Karaoke Backend", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # File Storage Configuration
    upload_folder: str = Field(default="storage/uploads", env="UPLOAD_FOLDER")
    jobs_folder: str = Field(default="storage/jobs", env="JOBS_FOLDER")
    max_file_size: str = Field(default="100MB", env="MAX_FILE_SIZE")
    allowed_extensions: List[str] = Field(default=["mp3", "wav", "m4a", "flac"], env="ALLOWED_EXTENSIONS")
    
    # AI Models Configuration
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")
    demucs_model: str = Field(default="htdemucs", env="DEMUCS_MODEL")
    audio_sample_rate: int = Field(default=44100, env="AUDIO_SAMPLE_RATE")
    
    # Processing Configuration
    max_concurrent_jobs: int = Field(default=3, env="MAX_CONCURRENT_JOBS")
    job_timeout: int = Field(default=3600, env="JOB_TIMEOUT")  # 1 hour
    cleanup_interval: int = Field(default=86400, env="CLEANUP_INTERVAL")  # 24 hours
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    
    # Optional: Cloud Storage (AWS S3)
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_bucket_name: Optional[str] = Field(default=None, env="AWS_BUCKET_NAME")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size string to bytes."""
        size_str = self.max_file_size.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.upload_folder,
            self.jobs_folder,
            os.path.join(self.jobs_folder, "temp"),
            "logs",
            "models"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()

# Create directories on import
settings.create_directories() 