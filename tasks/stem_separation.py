"""
Stem separation task for the Karaoke Backend.
Separates audio into stems (vocals, instruments, etc.) using Demucs AI models.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from celery_app import celery_app, get_task_logger
from models.job import job_manager, JobStatus, ProcessingStep
from ai_models.demucs_handler import get_demucs_handler, DemucsConfig


@celery_app.task(bind=True, name='tasks.stem_separation.separate_stems_task')
def separate_stems_task(self, job_id: str, audio_file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Separate audio into stems (vocals, drums, bass, other) using Demucs.
    
    This task uses the Demucs AI model to separate an audio file
    into individual stems for karaoke processing.
    
    Args:
        job_id: Unique job identifier
        audio_file_path: Path to the input audio file
        config: Configuration options for stem separation
        
    Returns:
        Dict containing separated stem file paths and metadata
    """
    task_logger = get_task_logger("stem_separation")
    task_logger.info("Starting Demucs stem separation", job_id=job_id, audio_file=audio_file_path)
    
    try:
        # Update job progress
        job_manager.update_job_progress(
            job_id=job_id,
            progress=5,
            current_step=ProcessingStep.STEM_SEPARATION
        )
        
        # Validate input file
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Get job data for output directory
        job_data = job_manager.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job {job_id} not found")
        
        # Create output directory for stems
        job_dir = Path(job_data.file_path).parent
        stems_dir = job_dir / "stems"
        stems_dir.mkdir(exist_ok=True)
        
        # Setup Demucs configuration
        demucs_config = DemucsConfig()
        
        # Apply config overrides if provided
        if config:
            if 'model_name' in config:
                demucs_config.model_name = config['model_name']
            if 'device' in config:
                demucs_config.device = config['device']
            if 'shifts' in config:
                demucs_config.shifts = config['shifts']
            if 'segment_length' in config:
                demucs_config.segment_length = config['segment_length']
        
        task_logger.info("Demucs configuration", 
                        model=demucs_config.model_name, 
                        device=demucs_config.device,
                        shifts=demucs_config.shifts)
        
        # Get Demucs handler
        demucs_handler = get_demucs_handler(demucs_config)
        
        # Progress tracking callback
        def progress_callback(progress: int):
            # Map Demucs progress (0-100) to our task progress (10-90)
            task_progress = 10 + int(progress * 0.8)
            job_manager.update_job_progress(
                job_id=job_id,
                progress=task_progress,
                current_step=ProcessingStep.STEM_SEPARATION
            )
            task_logger.info(f"Stem separation progress: {progress}%", job_id=job_id)
        
        # Perform stem separation
        task_logger.info("Running Demucs stem separation", job_id=job_id)
        result = demucs_handler.separate_stems(
            input_path=audio_file_path,
            output_dir=str(stems_dir),
            progress_callback=progress_callback
        )
        
        # Update final progress
        job_manager.update_job_progress(
            job_id=job_id,
            progress=100,
            current_step=ProcessingStep.STEM_SEPARATION
        )
        
        if result['success']:
            task_logger.info("Stem separation completed successfully", 
                           job_id=job_id, 
                           stems_count=result['metadata'].get('stems_count', 0),
                           processing_time=f"{result['metadata'].get('processing_time', 0):.2f}s")
        else:
            task_logger.error("Stem separation failed", job_id=job_id, error=result.get('error'))
        
        return result
        
    except Exception as e:
        error_msg = f"Stem separation failed: {str(e)}"
        task_logger.error("Stem separation failed", job_id=job_id, error=str(e), exc_info=True)
        
        return {
            'success': 0,
            'error': error_msg,
            'stems': {},
            'metadata': {}
        }


@celery_app.task(bind=True, name='tasks.stem_separation.optimize_stems_task')
def optimize_stems_task(self, job_id: str, stems_paths: Dict[str, str], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Optimize separated stems for karaoke use (normalize, enhance, etc.).
    
    Args:
        job_id: Unique job identifier
        stems_paths: Dictionary of stem names to file paths
        config: Configuration options for optimization
        
    Returns:
        Dict containing optimized stem file paths and metadata
    """
    task_logger = get_task_logger("stem_optimization")
    task_logger.info("Starting stem optimization", job_id=job_id, stems_count=len(stems_paths))
    
    try:
        optimized_paths = {}
        
        # TODO: Implement stem optimization
        # - Normalize audio levels
        # - Apply noise reduction
        # - Enhance vocal clarity
        # - Optimize instrumental balance
        
        # For now, just return the original paths
        optimized_paths = stems_paths.copy()
        
        task_logger.info("Stem optimization completed", job_id=job_id)
        
        return {
            'success': 1,
            'optimized_stems': optimized_paths,
            'metadata': {
                'optimization_applied': 0,  # Change to 1 when implemented
                'techniques': []  # List of applied optimization techniques
            }
        }
        
    except Exception as e:
        error_msg = f"Stem optimization failed: {str(e)}"
        task_logger.error("Stem optimization failed", job_id=job_id, error=str(e))
        
        return {
            'success': 0,
            'error': error_msg,
            'optimized_stems': {},
            'metadata': {}
        } 