"""
Vocal transcription task for the Karaoke Backend using OpenAI Whisper.
Provides high-quality speech-to-text with word-level timestamps for karaoke applications.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from celery_app import celery_app, get_task_logger
from database.redis_client import get_redis_client
from ai_models.whisper_handler import get_whisper_handler, WhisperConfig


@celery_app.task(bind=True, name='tasks.transcription.transcribe_audio_task')
def transcribe_audio_task(self, job_id: str, vocal_stem_path: str, job_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transcribe vocals from separated stem to text with word-level timestamps.
    
    Args:
        job_id: Unique job identifier
        vocal_stem_path: Path to the separated vocal audio file
        job_dir: Job output directory for storing results
        config: Configuration dictionary with transcription settings
        
    Returns:
        Dictionary with transcription results and metadata
    """
    task_logger = get_task_logger("transcription")
    redis_client = get_redis_client()
    
    try:
        task_logger.info("Starting vocal transcription", 
                        job_id=job_id, 
                        task_id=self.request.id,
                        vocal_stem_path=vocal_stem_path)
        
        # Update job status
        redis_client.hset(f"job:{job_id}", 
                         "transcription_status", "processing",
                         "transcription_progress", "0")
        
        # Validate inputs
        if not os.path.exists(vocal_stem_path):
            raise FileNotFoundError(f"Vocal stem file not found: {vocal_stem_path}")
        
        if not os.path.exists(job_dir):
            os.makedirs(job_dir, exist_ok=True)
        
        # Progress callback for Redis updates
        def progress_callback(progress: int):
            redis_client.hset(f"job:{job_id}", 
                             "transcription_progress", str(progress))
            task_logger.info("Transcription progress", 
                           job_id=job_id, 
                           progress=f"{progress}%")
        
        # Configure Whisper based on user preferences
        whisper_config = WhisperConfig()
        
        # Apply user configuration if provided
        if config:
            if 'model_name' in config:
                whisper_config.model_name = config['model_name']
            if 'language' in config:
                whisper_config.language = config['language']
            if 'device' in config:
                whisper_config.device = config['device']
            if 'temperature' in config:
                whisper_config.temperature = config['temperature']
        
        task_logger.info("Whisper configuration", 
                        model=whisper_config.model_name,
                        device=whisper_config.device,
                        language=whisper_config.language or "auto-detect")
        
        # Get Whisper handler and perform transcription
        whisper_handler = get_whisper_handler(whisper_config)
        
        # Create transcription output directory
        transcription_dir = os.path.join(job_dir, "transcription")
        
        # Perform transcription
        transcription_result = whisper_handler.transcribe_audio(
            audio_path=vocal_stem_path,
            output_dir=transcription_dir,
            progress_callback=progress_callback
        )
        
        if not transcription_result['success']:
            raise RuntimeError(transcription_result.get('error', 'Transcription failed'))
        
        # Extract key results
        transcription_data = transcription_result['transcription']
        output_files = transcription_result['output_files']
        metadata = transcription_result['metadata']
        
        # Build final result
        result = {
            'success': True,
            'transcript_text': transcription_data.get('text', ''),
            'language': transcription_result.get('language', 'unknown'),
            'duration': transcription_data.get('duration', 0.0),
            'word_count': metadata.get('word_count', 0),
            'processing_time': metadata.get('processing_time', 0.0),
            'model_name': metadata.get('model_name'),
            'device': metadata.get('device'),
            'confidence': metadata.get('language_confidence', 0.0),
            
            # File paths
            'output_files': output_files,
            'transcription_json': output_files.get('json'),
            'lyrics_txt': output_files.get('txt'),
            'subtitles_srt': output_files.get('srt'),
            'karaoke_json': output_files.get('karaoke'),
            
            # Detailed data for karaoke applications
            'segments': transcription_data.get('segments', []),
            'words_with_timestamps': transcription_data.get('words', []),
            
            # Statistics
            'segment_count': len(transcription_data.get('segments', [])),
            'has_word_timestamps': len(transcription_data.get('words', [])) > 0,
        }
        
        # Update job status with results
        redis_client.hset(f"job:{job_id}", 
                         "transcription_status", "completed",
                         "transcription_progress", "100",
                         "transcript_text", result['transcript_text'],
                         "transcription_language", result['language'],
                         "transcription_duration", str(result['duration']),
                         "word_count", str(result['word_count']))
        
        task_logger.info("Transcription completed successfully", 
                        job_id=job_id,
                        language=result['language'],
                        duration=f"{result['duration']:.2f}s",
                        word_count=result['word_count'],
                        processing_time=f"{result['processing_time']:.2f}s",
                        transcript_preview=result['transcript_text'][:100] + "..." if len(result['transcript_text']) > 100 else result['transcript_text'])
        
        return result
        
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        task_logger.error("Transcription task failed", 
                         job_id=job_id, 
                         error=error_msg,
                         exc_info=True)
        
        # Update job status with error
        redis_client.hset(f"job:{job_id}", 
                         "transcription_status", "error",
                         "transcription_error", error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'transcript_text': '',
            'language': 'unknown',
            'duration': 0.0,
            'word_count': 0,
            'processing_time': 0.0,
            'output_files': {},
            'segments': [],
            'words_with_timestamps': []
        } 