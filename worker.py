#!/usr/bin/env python3
"""
Celery worker script for the Karaoke Backend.
Runs background audio processing tasks.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import the Celery app
from celery_app import celery_app
from utils.logger import get_logger

logger = get_logger("worker")

def main():
    """Main worker entry point."""
    logger.info("Starting Celery worker for Karaoke Backend")
    
    # Worker configuration
    worker_args = [
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Limit concurrent tasks for memory efficiency
        '--queues=default,audio_processing,stem_separation,transcription,beat_analysis',
        '--hostname=karaoke-worker@%h',
        '--without-gossip',  # Reduce network chatter
        '--without-mingle',  # Reduce startup time
        '--without-heartbeat',  # Reduce network overhead
    ]
    
    # Add max tasks per child to prevent memory leaks
    if '--max-tasks-per-child' not in worker_args:
        worker_args.extend(['--max-tasks-per-child=50'])
    
    # Start the worker
    try:
        celery_app.start(worker_args)
    except KeyboardInterrupt:
        logger.info("Celery worker stopped by user")
    except Exception as e:
        logger.error("Celery worker error", error=str(e))
        sys.exit(1)


if __name__ == '__main__':
    main() 