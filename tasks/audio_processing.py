"""
Main audio processing pipeline for the Karaoke Backend.
Orchestrates stem separation, transcription, and beat analysis.
"""

from celery import group, chain, chord
from celery.exceptions import Retry
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from celery_app import celery_app, get_task_logger, update_job_progress
from models.job import job_manager, JobStatus, ProcessingStep


@celery_app.task(bind=True, name='tasks.audio_processing.process_audio_file')
def process_audio_file(self, job_id: str, processing_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main audio processing pipeline task.
    
    This task orchestrates the entire karaoke processing workflow:
    1. Load and validate the audio file
    2. Perform stem separation (vocals, instruments, etc.)
    3. Transcribe vocals to text with timestamps
    4. Analyze beat and tempo
    5. Generate final results
    
    Args:
        job_id: Unique job identifier
        processing_config: Configuration options for processing
        
    Returns:
        Dict containing processing results and file paths
    """
    task_logger = get_task_logger("audio_processing")
    task_logger.info("Starting audio processing pipeline", job_id=job_id, task_id=self.request.id)
    
    try:
        # Update job status to indicate processing has started
        update_job_progress(
            job_id=job_id,
            progress=15,
            status=JobStatus.PROCESSING,
            current_step=ProcessingStep.PROCESSING
        )
        
        # Get job data
        job_data = job_manager.get_job(job_id)
        if not job_data:
            raise Exception(f"Job {job_id} not found")
        
        if not os.path.exists(job_data.file_path):
            raise Exception(f"Audio file not found: {job_data.file_path}")
        
        task_logger.info(
            "Job data loaded",
            job_id=job_id,
            filename=job_data.original_filename,
            file_size=job_data.file_size
        )
        
        # Initialize processing configuration
        config = processing_config or {}
        
        # Create results structure
        results = {
            'job_id': job_id,
            'original_filename': job_data.original_filename,
            'file_size': job_data.file_size,
            'processing_config': config,
            'started_at': time.time(),
            'stages': {}
        }
        
        # Stage 1: Audio Validation and Preprocessing
        task_logger.info("Stage 1: Audio validation", job_id=job_id)
        update_job_progress(job_id, 20, current_step=ProcessingStep.VALIDATION)
        
        validation_result = validate_audio_file(job_data.file_path)
        results['stages']['validation'] = validation_result
        
        if not validation_result['valid']:
            raise Exception(f"Audio validation failed: {validation_result['error']}")
        
        # Stage 2: Stem Separation (if enabled)
        if config.get('enable_vocals_extraction', True):
            task_logger.info("Stage 2: Stem separation", job_id=job_id)
            update_job_progress(job_id, 30, current_step=ProcessingStep.STEM_SEPARATION)
            
            # Update task status
            job_manager.update_task_status(job_id, "stem_separation", "processing", 0)
            
            # Import and call stem separation task directly
            from tasks.stem_separation import separate_stems_task
            # Call the task function directly (not through Celery)
            stem_result = separate_stems_task.run(job_id, job_data.file_path, config)
            
            results['stages']['stem_separation'] = stem_result
            
            if stem_result['success']:
                # Update task status with results
                job_manager.update_task_status(
                    job_id, "stem_separation", "completed", 100,
                    vocals_path=stem_result.get('stems', {}).get('vocals'),
                    drums_path=stem_result.get('stems', {}).get('drums'),
                    bass_path=stem_result.get('stems', {}).get('bass'),
                    other_path=stem_result.get('stems', {}).get('other'),
                    processing_time=stem_result.get('metadata', {}).get('processing_time')
                )
            else:
                job_manager.update_task_status(
                    job_id, "stem_separation", "failed", 0, 
                    error=stem_result.get('error')
                )
                raise Exception(f"Stem separation failed: {stem_result['error']}")
        else:
            task_logger.info("Stem separation skipped (disabled)", job_id=job_id)
            job_manager.update_task_status(job_id, "stem_separation", "skipped", 100)
            results['stages']['stem_separation'] = {'success': 1, 'skipped': 1}  # Convert booleans to ints
        
        # Stage 3: Vocal Transcription (temporarily disabled)
        task_logger.info("Transcription skipped (temporarily disabled)", job_id=job_id)
        job_manager.update_task_status(job_id, "transcription", "skipped", 100)
        results['stages']['transcription'] = {'success': 1, 'skipped': 1}  # Convert booleans to ints
        
        # Stage 4: Beat Analysis (if enabled)
        if config.get('enable_beat_tracking', True):
            task_logger.info("Stage 4: Beat analysis", job_id=job_id)
            update_job_progress(job_id, 85, current_step=ProcessingStep.BEAT_ANALYSIS)
            
            # Update task status
            job_manager.update_task_status(job_id, "beat_analysis", "processing", 0)
            
            # Import and call beat analysis task directly
            from tasks.beat_analysis import analyze_beats_task
            # Calculate job directory from file path
            from pathlib import Path
            job_dir = str(Path(job_data.file_path).parent)
            # Call the task function directly (not through Celery)
            beat_result = analyze_beats_task.run(job_id, job_data.file_path, job_dir, config)
            
            results['stages']['beat_analysis'] = beat_result
            
            if beat_result['success']:
                # Update task status with results
                job_manager.update_task_status(
                    job_id, "beat_analysis", "completed", 100,
                    tempo_bpm=beat_result.get('tempo_bpm'),
                    beat_count=beat_result.get('beat_count'),
                    time_signature=beat_result.get('time_signature'),
                    beat_confidence=beat_result.get('beat_confidence'),
                    rhythm_regularity=beat_result.get('rhythm_regularity'),
                    processing_time=beat_result.get('processing_time')
                )
            else:
                job_manager.update_task_status(
                    job_id, "beat_analysis", "failed", 0,
                    error=beat_result.get('error')
                )
                task_logger.warning("Beat analysis failed but continuing", job_id=job_id, error=beat_result.get('error'))
        else:
            task_logger.info("Beat analysis skipped (disabled)", job_id=job_id)
            job_manager.update_task_status(job_id, "beat_analysis", "skipped", 100)
            results['stages']['beat_analysis'] = {'success': 1, 'skipped': 1}  # Convert booleans to ints
        
        # Stage 5: Finalization
        task_logger.info("Stage 5: Finalizing results", job_id=job_id)
        update_job_progress(job_id, 95, current_step=ProcessingStep.FINALIZATION)
        
        # Generate final output files and metadata
        finalization_result = finalize_processing(job_id, results)
        results['stages']['finalization'] = finalization_result
        
        # Complete processing
        results['completed_at'] = time.time()
        results['total_duration'] = results['completed_at'] - results['started_at']
        results['success'] = 1  # Convert boolean to int for JSON serialization
        
        # Store results in job data fields
        if 'stem_separation' in results['stages'] and results['stages']['stem_separation'].get('vocals_path'):
            job_data.stems = results['stages']['stem_separation']
        
        if 'transcription' in results['stages'] and results['stages']['transcription'].get('transcript_text'):
            job_data.lyrics = results['stages']['transcription']
        
        if 'beat_analysis' in results['stages'] and results['stages']['beat_analysis'].get('tempo_bpm'):
            job_data.beats = results['stages']['beat_analysis']
        
        job_manager.save_job(job_data)
        
        # Update final status
        update_job_progress(
            job_id=job_id,
            progress=100,
            status=JobStatus.COMPLETED,
            current_step=ProcessingStep.COMPLETED
        )
        
        task_logger.info(
            "Audio processing pipeline completed successfully",
            job_id=job_id,
            total_duration=f"{results['total_duration']:.2f}s"
        )
        
        return results
        
    except Exception as e:
        error_msg = f"Audio processing failed: {str(e)}"
        task_logger.error("Audio processing pipeline failed", job_id=job_id, error=str(e))
        
        # Update job status to failed
        update_job_progress(
            job_id=job_id,
            progress=0,
            status=JobStatus.FAILED,
            error_message=error_msg
        )
        
        # Store partial results if available
        if 'results' in locals():
            results['success'] = 0  # Convert boolean to int for JSON serialization
            results['error'] = error_msg
            results['completed_at'] = time.time()
            
            job_data = job_manager.get_job(job_id)
            if job_data:
                # Store any partial results that were completed
                if 'stem_separation' in results.get('stages', {}) and results['stages']['stem_separation'].get('vocals_path'):
                    job_data.stems = results['stages']['stem_separation']
                
                if 'transcription' in results.get('stages', {}) and results['stages']['transcription'].get('transcript_text'):
                    job_data.lyrics = results['stages']['transcription']
                
                if 'beat_analysis' in results.get('stages', {}) and results['stages']['beat_analysis'].get('tempo_bpm'):
                    job_data.beats = results['stages']['beat_analysis']
                
                job_manager.save_job(job_data)
        
        raise self.retry(exc=e, countdown=60, max_retries=2)


def validate_audio_file(file_path: str) -> Dict[str, Any]:
    """Validate audio file format and basic properties."""
    try:
        import librosa
        
        # Load audio metadata
        duration = librosa.get_duration(path=file_path)
        
        # Basic validation
        if duration < 1.0:
            return {'valid': 0, 'error': 'Audio file too short (< 1 second)'}  # Convert boolean to int
        
        if duration > 1800:  # 30 minutes
            return {'valid': 0, 'error': 'Audio file too long (> 30 minutes)'}  # Convert boolean to int
        
        # Try to load a small sample to verify format
        y, sr = librosa.load(file_path, duration=1.0)
        
        return {
            'valid': 1,  # Convert boolean to int
            'duration': duration,
            'sample_rate': sr,
            'samples': len(y)
        }
        
    except Exception as e:
        return {'valid': 0, 'error': f'Audio validation error: {str(e)}'}  # Convert boolean to int


def finalize_processing(job_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize processing and generate output files."""
    try:
        job_data = job_manager.get_job(job_id)
        job_dir = Path(job_data.file_path).parent
        output_dir = job_dir / 'output'
        
        # Generate metadata file
        metadata_file = output_dir / 'metadata.json'
        import json
        with open(metadata_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Create summary of available files
        available_files = []
        
        # Check for stem files
        stems_dir = job_dir / 'stems'
        if stems_dir.exists():
            for stem_file in stems_dir.glob('*.wav'):
                available_files.append({
                    'type': 'stem',
                    'name': stem_file.stem,
                    'path': str(stem_file),
                    'size': stem_file.stat().st_size
                })
        
        # Check for transcription files
        if 'transcription' in results['stages'] and results['stages']['transcription'].get('transcript_path'):
            transcript_path = Path(results['stages']['transcription']['transcript_path'])
            if transcript_path.exists():
                available_files.append({
                    'type': 'transcription',
                    'name': 'lyrics',
                    'path': str(transcript_path),
                    'size': transcript_path.stat().st_size
                })
        
        # Check for beat analysis files
        if 'beat_analysis' in results['stages'] and results['stages']['beat_analysis'].get('beats_path'):
            beats_path = Path(results['stages']['beat_analysis']['beats_path'])
            if beats_path.exists():
                available_files.append({
                    'type': 'beats',
                    'name': 'beat_map',
                    'path': str(beats_path),
                    'size': beats_path.stat().st_size
                })
        
        return {
            'success': 1,  # Convert boolean to int
            'metadata_file': str(metadata_file),
            'available_files': available_files,
            'output_directory': str(output_dir)
        }
        
    except Exception as e:
        return {'success': 0, 'error': f'Finalization error: {str(e)}'}  # Convert boolean to int


@celery_app.task(bind=True, name='tasks.audio_processing.cleanup_job')
def cleanup_job_task(self, job_id: str) -> Dict[str, Any]:
    """Clean up job files and data."""
    task_logger = get_task_logger("cleanup")
    task_logger.info("Starting job cleanup", job_id=job_id)
    
    try:
        from utils.file_handler import file_manager
        
        # Clean up files
        success = file_manager.cleanup_job(job_id)
        
        if success:
            task_logger.info("Job cleanup completed", job_id=job_id)
            return {'success': 1, 'job_id': job_id}  # Convert boolean to int
        else:
            return {'success': 0, 'error': 'Failed to clean up files'}  # Convert boolean to int
            
    except Exception as e:
        task_logger.error("Job cleanup failed", job_id=job_id, error=str(e))
        return {'success': 0, 'error': str(e)}  # Convert boolean to int 