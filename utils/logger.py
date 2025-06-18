"""
Logging configuration for the Karaoke Backend application.
Provides structured logging with JSON format support.
"""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.stdlib import LoggerFactory

from config import settings


def setup_logging():
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    

class Logger:
    """Custom logger wrapper with structured logging."""
    
    def __init__(self, name: str = "karaoke-backend"):
        self._logger = structlog.get_logger(name)
    
    def debug(self, message: str, **kwargs: Any):
        """Log debug message."""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs: Any):
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any):
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs: Any):
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any):
        """Log critical message."""
        self._logger.critical(message, **kwargs)
    
    def log_job_event(self, job_id: str, event: str, **kwargs: Any):
        """Log job-specific events."""
        self.info(f"Job {event}", job_id=job_id, **kwargs)
    
    def log_api_request(self, method: str, path: str, status_code: int, **kwargs: Any):
        """Log API request details."""
        self.info(
            "API request",
            method=method,
            path=path,
            status_code=status_code,
            **kwargs
        )
    
    def log_processing_step(self, job_id: str, step: str, progress: int = None, **kwargs: Any):
        """Log processing step with progress."""
        log_data = {
            "job_id": job_id,
            "step": step,
            **kwargs
        }
        if progress is not None:
            log_data["progress"] = progress
        
        self.info(f"Processing step: {step}", **log_data)


# Global logger instance
logger = Logger()


def get_logger(name: str = None) -> Logger:
    """Get a logger instance with optional name."""
    if name:
        return Logger(name)
    return logger 