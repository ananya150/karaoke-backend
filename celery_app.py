"""
Celery application configuration for the Karaoke Backend.
Handles background audio processing tasks.
"""

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from utils.logger import get_logger

logger = get_logger("celery_app")

# Create Celery application
celery_app = Celery(
    'karaoke_backend',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'tasks.audio_processing',
        'tasks.stem_separation',
        'tasks.transcription',
        'tasks.beat_analysis'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'tasks.audio_processing.*': {'queue': 'audio_processing'},
        'tasks.stem_separation.*': {'queue': 'stem_separation'},
        'tasks.transcription.*': {'queue': 'transcription'},
        'tasks.beat_analysis.*': {'queue': 'beat_analysis'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Process one task at a time for memory efficiency
    task_acks_late=True,  # Acknowledge tasks after completion
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    
    # Task time limits
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'retry_on_timeout': True,
        'visibility_timeout': 3600,
    },
    
    # Task retry configuration
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Maximum 3 retries
    
    # Queue configuration
    task_create_missing_queues=True,
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'exchange_type': 'direct',
            'routing_key': 'default',
        },
        'audio_processing': {
            'exchange': 'audio_processing',
            'exchange_type': 'direct',
            'routing_key': 'audio_processing',
        },
        'stem_separation': {
            'exchange': 'stem_separation',
            'exchange_type': 'direct',
            'routing_key': 'stem_separation',
        },
        'transcription': {
            'exchange': 'transcription',
            'exchange_type': 'direct',
            'routing_key': 'transcription',
        },
        'beat_analysis': {
            'exchange': 'beat_analysis',
            'exchange_type': 'direct',
            'routing_key': 'beat_analysis',
        },
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
)

# Configure logging for Celery
celery_app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
celery_app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready event."""
    logger.info("Celery worker is ready", worker=sender.hostname)


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown event."""
    logger.info("Celery worker is shutting down", worker=sender.hostname)


# Task decorators and utilities
def get_task_logger(task_name: str):
    """Get a logger for a specific task."""
    return get_logger(f"task.{task_name}")


def update_job_progress(job_id: str, progress: int, status: str = None, current_step: str = None, error_message: str = None):
    """Update job progress in Redis."""
    try:
        from models.job import job_manager, JobStatus, ProcessingStep
        
        if status:
            # Convert string to enum if needed
            if isinstance(status, str):
                status = JobStatus(status)
            if isinstance(current_step, str):
                current_step = ProcessingStep(current_step)
        
        job_manager.update_job_status(
            job_id=job_id,
            status=status,
            progress=progress,
            current_step=current_step,
            error_message=error_message
        )
        
    except Exception as e:
        logger.error("Failed to update job progress", job_id=job_id, error=str(e))


# Health check task
@celery_app.task(bind=True, name='tasks.health_check')
def health_check_task(self):
    """Simple health check task to verify Celery is working."""
    task_logger = get_task_logger("health_check")
    task_logger.info("Health check task started", task_id=self.request.id)
    
    import time
    time.sleep(1)  # Simulate some work
    
    result = {
        'status': 'healthy',
        'task_id': self.request.id,
        'timestamp': time.time(),
        'worker': self.request.hostname
    }
    
    task_logger.info("Health check task completed", task_id=self.request.id, result=result)
    return result


if __name__ == '__main__':
    # Allow running celery app directly for testing
    celery_app.start() 