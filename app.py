"""
Main FastAPI application for the Karaoke Backend.
Handles API routing, middleware, and application startup.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager

from config import settings
from utils.logger import setup_logging, logger
from routes import health, upload, status, results, static


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Karaoke Backend API", version=settings.app_version)
    
    # Ensure storage directories exist
    settings.create_directories()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Karaoke Backend API")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A powerful backend for processing audio files into karaoke-ready content",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Set up logging
setup_logging()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in settings.cors_origins else settings.cors_origins_list,
    allow_credentials=False if "*" in settings.cors_origins else True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected error occurred",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(
        "Incoming request",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )
    
    response = await call_next(request)
    
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code
    )
    
    return response


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(status.router, prefix="/api", tags=["Status"])
app.include_router(results.router, prefix="/api", tags=["Results"])
app.include_router(static.router, prefix="/api", tags=["Files"])

# Static files (for serving processed audio files)
if os.path.exists("storage"):
    app.mount("/static", StaticFiles(directory="storage"), name="static")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
        "endpoints": {
            "health": "/health",
            "process": "/api/process",
            "status": "/api/status/{job_id}",
            "results": "/api/results/{job_id}",
            "files": "/api/files/{job_id}/{filename}",
            "static": "/static/{path}"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 