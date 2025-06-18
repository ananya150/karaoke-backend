"""
Whisper Audio Transcription Handler

This module provides a wrapper around OpenAI's Whisper model for high-quality 
speech-to-text transcription with word-level timestamps, specifically optimized 
for karaoke and music applications.
"""

import os
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import logging

import torch
import whisper
import numpy as np
from whisper.utils import get_writer

from utils.logger import get_logger


logger = get_logger("whisper_handler")


class WhisperConfig:
    """Configuration class for Whisper transcription."""
    
    def __init__(self):
        # Model selection - options: 'tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'
        self.model_name = "small"  # Good balance of speed/accuracy for music transcription
        
        # Processing parameters
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.language = None  # Auto-detect language
        self.task = "transcribe"  # transcribe or translate
        
        # Quality settings
        self.temperature = 0.1  # Slightly higher for music transcription
        self.best_of = 5  # Number of candidates when temperature > 0
        self.beam_size = 5  # Beam search size
        self.patience = None  # Patience for beam search
        
        # Timing parameters
        self.word_timestamps = True  # Enable word-level timestamps
        self.prepend_punctuations = "\"'([{-"
        self.append_punctuations = "\"'.,:!?)]}"
        
        # Audio preprocessing
        self.condition_on_previous_text = False  # Don't use context for music
        self.initial_prompt = "♪ Song lyrics: "  # Music-specific prompt
        self.suppress_tokens = [-1]  # Tokens to suppress
        
        # Output format
        self.output_format = "json"  # json, txt, vtt, srt
        self.max_line_width = None
        self.max_line_count = None
        self.highlight_words = False
        
        logger.info("Whisper configuration initialized", 
                   model=self.model_name, device=self.device)


class WhisperHandler:
    """Handler for Whisper-based audio transcription."""
    
    def __init__(self, config: Optional[WhisperConfig] = None):
        self.config = config or WhisperConfig()
        self.model = None
        self._model_loaded = False
        
    def _load_model(self) -> None:
        """Load the Whisper model if not already loaded."""
        if self._model_loaded:
            return
            
        try:
            logger.info("Loading Whisper model", model=self.config.model_name)
            start_time = time.time()
            
            # Load the pre-trained model
            self.model = whisper.load_model(
                self.config.model_name, 
                device=self.config.device
            )
            
            load_time = time.time() - start_time
            logger.info("Whisper model loaded successfully", 
                       model=self.config.model_name, 
                       device=self.config.device,
                       load_time=f"{load_time:.2f}s")
            
            self._model_loaded = True
            
        except Exception as e:
            logger.error("Failed to load Whisper model", error=str(e))
            raise RuntimeError(f"Failed to load Whisper model: {str(e)}")
    
    def transcribe_audio(self, 
                        audio_path: str, 
                        output_dir: str,
                        progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """
        Transcribe audio to text with word-level timestamps.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save transcription results
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing transcription results and metadata
        """
        try:
            start_time = time.time()
            logger.info("Starting audio transcription", audio_path=audio_path, output_dir=output_dir)
            
            # Ensure model is loaded
            self._load_model()
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            if progress_callback:
                progress_callback(10)
            
            # Load and preprocess audio
            logger.info("Loading audio for transcription")
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            
            if progress_callback:
                progress_callback(20)
            
            # Make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            
            if progress_callback:
                progress_callback(30)
            
            # Detect language if not specified
            if self.config.language is None:
                logger.info("Detecting language")
                _, probs = self.model.detect_language(mel)
                detected_language = max(probs, key=probs.get)
                language_confidence = probs[detected_language]
                logger.info("Language detected", 
                           language=detected_language, 
                           confidence=f"{language_confidence:.2f}")
            else:
                detected_language = self.config.language
                language_confidence = 1.0
            
            if progress_callback:
                progress_callback(40)
            
            # Perform transcription
            logger.info("Running Whisper transcription")
            
            options = {
                "language": detected_language,
                "task": self.config.task,
                "temperature": self.config.temperature,
                "best_of": self.config.best_of,
                "beam_size": self.config.beam_size,
                "patience": self.config.patience,
                "condition_on_previous_text": self.config.condition_on_previous_text,
                "initial_prompt": self.config.initial_prompt,
                "suppress_tokens": self.config.suppress_tokens,
                "word_timestamps": self.config.word_timestamps,
                "prepend_punctuations": self.config.prepend_punctuations,
                "append_punctuations": self.config.append_punctuations,
            }
            
            result = self.model.transcribe(audio_path, **options)
            
            if progress_callback:
                progress_callback(70)
            
            # Process results
            transcription_data = self._process_transcription_result(result, audio_path)
            
            if progress_callback:
                progress_callback(80)
            
            # Save results in various formats
            output_files = self._save_transcription_results(
                transcription_data, output_dir, audio_path
            )
            
            if progress_callback:
                progress_callback(90)
            
            # Generate metadata
            processing_time = time.time() - start_time
            metadata = {
                'processing_time': processing_time,
                'model_name': self.config.model_name,
                'device': self.config.device,
                'language': detected_language,
                'language_confidence': language_confidence,
                'word_count': len(transcription_data.get('words', [])),
                'segment_count': len(transcription_data.get('segments', [])),
                'total_duration': transcription_data.get('duration', 0.0)
            }
            
            logger.info("Transcription completed successfully",
                       processing_time=f"{processing_time:.2f}s",
                       language=detected_language,
                       word_count=metadata['word_count'])
            
            if progress_callback:
                progress_callback(100)
            
            return {
                'success': True,
                'transcription': transcription_data,
                'output_files': output_files,
                'metadata': metadata,
                'language': detected_language,
                'transcript_text': transcription_data.get('text', ''),
                'words_with_timestamps': transcription_data.get('words', [])
            }
            
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error("Audio transcription failed", error=str(e), exc_info=True)
            
            return {
                'success': False,
                'error': error_msg,
                'transcription': {},
                'output_files': {},
                'metadata': {}
            }
    
    def _process_transcription_result(self, result: Dict[str, Any], audio_path: str) -> Dict[str, Any]:
        """Process the raw Whisper result into our structured format."""
        try:
            # Extract basic information
            text = result.get('text', '').strip()
            language = result.get('language', 'unknown')
            
            # Process segments
            segments = []
            words = []
            
            for segment in result.get('segments', []):
                segment_data = {
                    'id': segment.get('id'),
                    'start': segment.get('start'),
                    'end': segment.get('end'),
                    'text': segment.get('text', '').strip(),
                    'temperature': segment.get('temperature'),
                    'avg_logprob': segment.get('avg_logprob'),
                    'compression_ratio': segment.get('compression_ratio'),
                    'no_speech_prob': segment.get('no_speech_prob')
                }
                segments.append(segment_data)
                
                # Extract word-level timestamps if available
                if 'words' in segment:
                    for word in segment['words']:
                        word_data = {
                            'word': word.get('word', '').strip(),
                            'start': word.get('start'),
                            'end': word.get('end'),
                            'probability': word.get('probability')
                        }
                        words.append(word_data)
            
            # Calculate duration
            duration = 0.0
            if segments:
                duration = max(seg.get('end', 0) for seg in segments)
            
            return {
                'text': text,
                'language': language,
                'duration': duration,
                'segments': segments,
                'words': words
            }
            
        except Exception as e:
            logger.error("Failed to process transcription result", error=str(e))
            return {
                'text': result.get('text', ''),
                'language': result.get('language', 'unknown'),
                'duration': 0.0,
                'segments': [],
                'words': []
            }
    
    def _save_transcription_results(self, transcription_data: Dict[str, Any], 
                                   output_dir: str, audio_path: str) -> Dict[str, str]:
        """Save transcription results in multiple formats."""
        try:
            output_files = {}
            input_filename = Path(audio_path).stem
            
            # Save JSON format (detailed with timestamps)
            json_path = os.path.join(output_dir, f"{input_filename}_transcription.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(transcription_data, f, indent=2, ensure_ascii=False)
            output_files['json'] = json_path
            
            # Save plain text format
            txt_path = os.path.join(output_dir, f"{input_filename}_lyrics.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(transcription_data.get('text', ''))
            output_files['txt'] = txt_path
            
            # Save SRT subtitle format (if segments available)
            if transcription_data.get('segments'):
                srt_path = os.path.join(output_dir, f"{input_filename}_subtitles.srt")
                self._save_srt_format(transcription_data['segments'], srt_path)
                output_files['srt'] = srt_path
            
            # Save word-level timing format (for karaoke)
            if transcription_data.get('words'):
                karaoke_path = os.path.join(output_dir, f"{input_filename}_karaoke.json")
                karaoke_data = {
                    'lyrics': transcription_data.get('text', ''),
                    'words': transcription_data['words'],
                    'language': transcription_data.get('language'),
                    'duration': transcription_data.get('duration', 0.0)
                }
                with open(karaoke_path, 'w', encoding='utf-8') as f:
                    json.dump(karaoke_data, f, indent=2, ensure_ascii=False)
                output_files['karaoke'] = karaoke_path
            
            logger.info("Transcription results saved", 
                       formats=list(output_files.keys()),
                       output_dir=output_dir)
            
            return output_files
            
        except Exception as e:
            logger.error("Failed to save transcription results", error=str(e))
            return {}
    
    def _save_srt_format(self, segments: List[Dict], output_path: str) -> None:
        """Save segments in SRT subtitle format."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_timestamp(segment.get('start', 0))
                    end_time = self._format_timestamp(segment.get('end', 0))
                    text = segment.get('text', '').strip()
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
                    
        except Exception as e:
            logger.error("Failed to save SRT format", error=str(e))
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self._model_loaded:
            self._load_model()
            
        return {
            'model_name': self.config.model_name,
            'device': self.config.device,
            'language': self.config.language or 'auto-detect',
            'word_timestamps': self.config.word_timestamps,
            'task': self.config.task
        }
    
    def cleanup(self):
        """Clean up model and free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self._model_loaded = False
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("Whisper model cleaned up")


# Global handler instance for reuse
_whisper_handler = None

def get_whisper_handler(config: Optional[WhisperConfig] = None) -> WhisperHandler:
    """Get a global instance of the Whisper handler."""
    global _whisper_handler
    
    if _whisper_handler is None:
        _whisper_handler = WhisperHandler(config)
    
    return _whisper_handler 