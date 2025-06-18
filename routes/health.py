"""
Health check endpoint for the Karaoke Backend API.
Provides system status and health monitoring.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import redis
import time
import os

from config import settings
from utils.logger import get_logger

logger = get_logger("health")
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str
    environment: str
    services: Dict[str, Any]
    storage: Dict[str, Any]


def check_redis_connection() -> Dict[str, Any]:
    """Check Redis connection health."""
    try:
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        
        # Test connection with ping
        r.ping()
        
        # Get Redis info
        info = r.info()
        
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown")
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_storage_health() -> Dict[str, Any]:
    """Check storage directories and disk space."""
    try:
        storage_info = {}
        
        # Check if directories exist and are writable
        directories = [
            settings.upload_folder,
            settings.jobs_folder,
            "logs",
            "models"
        ]
        
        for directory in directories:
            if os.path.exists(directory):
                storage_info[directory] = {
                    "exists": True,
                    "writable": os.access(directory, os.W_OK),
                    "files_count": len(os.listdir(directory)) if os.path.isdir(directory) else 0
                }
            else:
                storage_info[directory] = {
                    "exists": False,
                    "writable": False,
                    "files_count": 0
                }
        
        # Get disk space info for storage directory
        if os.path.exists("storage"):
            stat = os.statvfs("storage")
            total_space = stat.f_frsize * stat.f_blocks
            free_space = stat.f_frsize * stat.f_available
            used_space = total_space - free_space
            
            storage_info["disk_space"] = {
                "total_gb": round(total_space / (1024**3), 2),
                "used_gb": round(used_space / (1024**3), 2),
                "free_gb": round(free_space / (1024**3), 2),
                "usage_percent": round((used_space / total_space) * 100, 1)
            }
        
        return {
            "status": "healthy",
            "directories": storage_info
        }
        
    except Exception as e:
        logger.error("Storage health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the application and its dependencies.
    """
    logger.debug("Health check requested")
    
    # Check Redis connection
    redis_health = check_redis_connection()
    
    # Check storage
    storage_health = check_storage_health()
    
    # Determine overall status
    overall_status = "healthy"
    if redis_health["status"] != "healthy" or storage_health["status"] != "healthy":
        overall_status = "degraded"
    
    response = HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        version=settings.app_version,
        environment="development" if settings.debug else "production",
        services={
            "redis": redis_health,
            "api": {"status": "healthy"}
        },
        storage=storage_health
    )
    
    logger.info("Health check completed", status=overall_status)
    
    return response


@router.get("/health/simple")
async def simple_health_check():
    """
    Simple health check endpoint.
    
    Returns a basic OK response for load balancers.
    """
    return {"status": "ok", "timestamp": time.time()} 