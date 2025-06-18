"""
Beat analysis task for the Karaoke Backend using Librosa.
Provides comprehensive beat detection, tempo analysis, and rhythm extraction for karaoke applications.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from celery_app import celery_app, get_task_logger
from database.redis_client import get_redis_client
from ai_models.librosa_handler import get_librosa_handler, LibrosaConfig


@celery_app.task(bind=True, name='tasks.beat_analysis.analyze_beats_task')
def analyze_beats_task(self, job_id: str, audio_file_path: str, job_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze beats, tempo, and rhythm patterns in audio using Librosa.
    
    Args:
        job_id: Unique job identifier
        audio_file_path: Path to the audio file for analysis
        job_dir: Job output directory for storing results
        config: Configuration dictionary with analysis settings
        
    Returns:
        Dictionary with beat analysis results and metadata
    """
    task_logger = get_task_logger("beat_analysis")
    redis_client = get_redis_client()
    
    try:
        task_logger.info("Starting beat analysis", 
                        job_id=job_id, 
                        task_id=self.request.id,
                        audio_file_path=audio_file_path)
        
        # Update job status
        redis_client.hset(f"job:{job_id}", 
                         "beat_analysis_status", "processing",
                         "beat_analysis_progress", "0")
        
        # Validate inputs
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        if not os.path.exists(job_dir):
            os.makedirs(job_dir, exist_ok=True)
        
        # Progress callback for Redis updates
        def progress_callback(progress: int):
            redis_client.hset(f"job:{job_id}", 
                             "beat_analysis_progress", str(progress))
            task_logger.info("Beat analysis progress", 
                           job_id=job_id, 
                           progress=f"{progress}%")
        
        # Configure Librosa based on user preferences
        librosa_config = LibrosaConfig()
        
        # Apply user configuration if provided
        if config:
            if 'sample_rate' in config:
                librosa_config.sample_rate = config['sample_rate']
            if 'hop_length' in config:
                librosa_config.hop_length = config['hop_length']
            if 'tempo_min' in config:
                librosa_config.tempo_min = config['tempo_min']
            if 'tempo_max' in config:
                librosa_config.tempo_max = config['tempo_max']
            if 'beat_tracker' in config:
                librosa_config.beat_tracker = config['beat_tracker']
            if 'onset_detection' in config:
                librosa_config.onset_detection = config['onset_detection']
        
        task_logger.info("Librosa configuration", 
                        sample_rate=librosa_config.sample_rate,
                        beat_tracker=librosa_config.beat_tracker,
                        tempo_range=f"{librosa_config.tempo_min}-{librosa_config.tempo_max}")
        
        # Get Librosa handler and perform analysis
        librosa_handler = get_librosa_handler(librosa_config)
        
        # Create beat analysis output directory
        analysis_dir = os.path.join(job_dir, "beat_analysis")
        
        # Perform beat and tempo analysis
        analysis_result = librosa_handler.analyze_audio(
            audio_path=audio_file_path,
            output_dir=analysis_dir,
            progress_callback=progress_callback
        )
        
        if not analysis_result['success']:
            raise RuntimeError(analysis_result.get('error', 'Beat analysis failed'))
        
        # Extract key results
        analysis_data = analysis_result['analysis']
        output_files = analysis_result['output_files']
        metadata = analysis_result['metadata']
        
        # Build final result
        result = {
            'success': True,
            'tempo_bpm': analysis_result.get('tempo_bpm', 0),
            'beat_timestamps': analysis_result.get('beats', []),
            'beat_times': analysis_result.get('beat_times', []),
            'beat_count': metadata.get('beat_count', 0),
            'processing_time': metadata.get('processing_time', 0.0),
            'audio_duration': metadata.get('audio_duration', 0.0),
            'time_signature': metadata.get('time_signature', '4/4'),
            
            # File paths
            'output_files': output_files,
            'analysis_json': output_files.get('analysis_json'),
            'beats_json': output_files.get('beats_json'),
            'onsets_json': output_files.get('onsets_json'),
            
            # Detailed analysis data
            'audio_properties': analysis_data.get('audio_properties', {}),
            'tempo_analysis': analysis_data.get('tempo_analysis', {}),
            'onset_analysis': analysis_data.get('onset_analysis', {}),
            'rhythm_analysis': analysis_data.get('rhythm_analysis', {}),
            
            # Beat grid for karaoke synchronization
            'beat_grid': analysis_data.get('tempo_analysis', {}).get('beat_grid', []),
            'beat_confidence': analysis_data.get('tempo_analysis', {}).get('beat_confidence', 0.0),
            'beat_interval': analysis_data.get('tempo_analysis', {}).get('beat_interval', 0.0),
            
            # Onset information
            'onsets': analysis_result.get('onsets', []),
            'onset_count': analysis_data.get('onset_analysis', {}).get('onset_count', 0),
            'onset_density': analysis_data.get('onset_analysis', {}).get('onset_density', 0.0),
            
            # Rhythm characteristics
            'rhythm_regularity': analysis_data.get('rhythm_analysis', {}).get('rhythm_regularity', 0.0),
            'rhythm_complexity': analysis_data.get('rhythm_analysis', {}).get('rhythm_complexity', 'unknown'),
            
            # Quality metrics
            'tempo_confidence': analysis_data.get('tempo_analysis', {}).get('tempo_confidence', 0.0),
            'has_strong_beat': metadata.get('beat_count', 0) > 10 and analysis_data.get('tempo_analysis', {}).get('beat_confidence', 0) > 0.5
        }
        
        # Update job status with results
        redis_client.hset(f"job:{job_id}", 
                         "beat_analysis_status", "completed",
                         "beat_analysis_progress", "100",
                         "tempo_bpm", str(result['tempo_bpm']),
                         "beat_count", str(result['beat_count']),
                         "time_signature", result['time_signature'],
                         "beat_confidence", str(result['beat_confidence']),
                         "rhythm_regularity", str(result['rhythm_regularity']))
        
        task_logger.info("Beat analysis completed successfully", 
                        job_id=job_id,
                        tempo_bpm=result['tempo_bpm'],
                        beat_count=result['beat_count'],
                        time_signature=result['time_signature'],
                        processing_time=f"{result['processing_time']:.2f}s",
                        beat_confidence=f"{result['beat_confidence']:.2f}",
                        rhythm_regularity=f"{result['rhythm_regularity']:.2f}")
        
        return result
        
    except Exception as e:
        error_msg = f"Beat analysis failed: {str(e)}"
        task_logger.error("Beat analysis task failed", 
                         job_id=job_id, 
                         error=error_msg,
                         exc_info=True)
        
        # Update job status with error
        redis_client.hset(f"job:{job_id}", 
                         "beat_analysis_status", "error",
                         "beat_analysis_error", error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'tempo_bpm': 0,
            'beat_timestamps': [],
            'beat_times': [],
            'beat_count': 0,
            'processing_time': 0.0,
            'audio_duration': 0.0,
            'time_signature': '4/4',
            'output_files': {},
            'audio_properties': {},
            'tempo_analysis': {},
            'onset_analysis': {},
            'rhythm_analysis': {},
            'beat_grid': [],
            'beat_confidence': 0.0,
            'beat_interval': 0.0,
            'onsets': [],
            'onset_count': 0,
            'onset_density': 0.0,
            'rhythm_regularity': 0.0,
            'rhythm_complexity': 'unknown',
            'tempo_confidence': 0.0,
            'has_strong_beat': False
        } 