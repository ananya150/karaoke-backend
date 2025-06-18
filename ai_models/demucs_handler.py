"""
Demucs Audio Stem Separation Handler

This module provides a wrapper around the Demucs library for high-quality 
audio source separation, specifically optimized for karaoke applications.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import logging

import torch
import torchaudio
from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import convert_audio

from utils.logger import get_logger


logger = get_logger("demucs_handler")


class DemucsConfig:
    """Configuration class for Demucs stem separation."""
    
    def __init__(self):
        # Model selection - options: 'htdemucs', 'htdemucs_ft', 'htdemucs_6s', 'mdx_extra_q', 'mdx_q', 'mdx'
        self.model_name = "mdx_q"  # More stable model for various audio formats
        
        # Processing parameters
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.segment_length = None  # Process full track without segmentation
        self.overlap = 0.25  # Overlap between segments
        self.batch_size = 1  # Process one file at a time
        
        # Quality vs Speed settings
        self.shifts = 1  # Number of random shifts for better quality (1-10)
        self.split = True  # Split stereo channels for better separation
        self.normalize = True  # Normalize output audio
        
        # Output configuration
        self.output_format = "wav"  # Output format
        self.sample_rate = 44100  # Output sample rate
        self.bit_depth = 16  # Output bit depth
        
        # Memory management
        self.max_memory_gb = 4.0  # Maximum memory usage in GB
        
        logger.info(f"Demucs configuration initialized", 
                   model=self.model_name, device=self.device)


class DemucsHandler:
    """Handler for Demucs-based audio stem separation."""
    
    def __init__(self, config: Optional[DemucsConfig] = None):
        self.config = config or DemucsConfig()
        self.model = None
        self._model_loaded = False
        
    def _load_model(self) -> None:
        """Load the Demucs model if not already loaded."""
        if self._model_loaded:
            return
            
        try:
            logger.info("Loading Demucs model", model=self.config.model_name)
            start_time = time.time()
            
            # Load the pre-trained model
            self.model = get_model(self.config.model_name)
            self.model.to(self.config.device)
            self.model.eval()
            
            # Set segment length based on available memory
            if self.config.segment_length is None:
                self.config.segment_length = self._calculate_optimal_segment_length()
            
            load_time = time.time() - start_time
            logger.info("Demucs model loaded successfully", 
                       model=self.config.model_name, 
                       device=self.config.device,
                       load_time=f"{load_time:.2f}s")
            
            self._model_loaded = True
            
        except Exception as e:
            logger.error("Failed to load Demucs model", error=str(e))
            raise RuntimeError(f"Failed to load Demucs model: {str(e)}")
    
    def _calculate_optimal_segment_length(self) -> Optional[float]:
        """Calculate optimal segment length based on available memory."""
        try:
            if self.config.device == "cuda" and torch.cuda.is_available():
                # Get GPU memory info
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                optimal_length = min(30.0, gpu_memory * 2)  # Conservative estimate
                logger.info(f"GPU memory detected: {gpu_memory:.1f}GB, segment length: {optimal_length:.1f}s")
                return optimal_length
            else:
                # CPU processing - use smaller segments
                return 10.0
        except Exception as e:
            logger.warning("Could not determine optimal segment length", error=str(e))
            return 10.0
    
    def separate_stems(self, 
                      input_path: str, 
                      output_dir: str,
                      progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """
        Separate audio into stems (vocals, drums, bass, other).
        
        Args:
            input_path: Path to input audio file
            output_dir: Directory to save separated stems
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing paths to separated stems and metadata
        """
        try:
            start_time = time.time()
            logger.info("Starting stem separation", input_path=input_path, output_dir=output_dir)
            
            # Ensure model is loaded
            self._load_model()
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Load and preprocess audio
            if progress_callback:
                progress_callback(10)
                
            audio_info = self._load_audio(input_path)
            waveform = audio_info['waveform']
            sample_rate = audio_info['sample_rate']
            duration = audio_info['duration']
            
            logger.info("Audio loaded", 
                       sample_rate=sample_rate, 
                       duration=f"{duration:.2f}s",
                       channels=waveform.shape[0])
            
            if progress_callback:
                progress_callback(20)
            
            # Convert audio to model's expected format
            model_sample_rate = getattr(self.model, 'samplerate', getattr(self.model, 'sample_rate', 44100))
            model_audio_channels = getattr(self.model, 'audio_channels', 2)
            
            logger.info("Converting audio format",
                       original_sr=sample_rate,
                       target_sr=model_sample_rate,
                       original_channels=waveform.shape[0],
                       target_channels=model_audio_channels,
                       original_shape=waveform.shape)
            
            waveform = convert_audio(
                waveform, 
                sample_rate, 
                model_sample_rate, 
                model_audio_channels
            )
            
            logger.info("Audio conversion completed", 
                       final_shape=waveform.shape,
                       final_sr=model_sample_rate)
            
            if progress_callback:
                progress_callback(30)
            
            # Apply stem separation
            logger.info("Applying Demucs model for stem separation")
            
            with torch.no_grad():
                # Move to device
                waveform = waveform.to(self.config.device)
                
                # Apply the model
                separated = apply_model(
                    self.model,
                    waveform[None],  # Add batch dimension
                    segment=self.config.segment_length,
                    overlap=self.config.overlap,
                    split=self.config.split,
                    device=self.config.device,
                    shifts=self.config.shifts,
                    progress=True
                )
                
                # Remove batch dimension
                separated = separated[0]
            
            if progress_callback:
                progress_callback(70)
            
            # Save separated stems
            stem_paths = self._save_stems(separated, output_dir, input_path)
            
            if progress_callback:
                progress_callback(90)
            
            # Generate metadata
            processing_time = time.time() - start_time
            metadata = {
                'processing_time': processing_time,
                'model_name': self.config.model_name,
                'device': self.config.device,
                'input_duration': duration,
                'sample_rate': model_sample_rate,
                'stems_count': len(stem_paths)
            }
            
            logger.info("Stem separation completed successfully",
                       processing_time=f"{processing_time:.2f}s",
                       stems_count=len(stem_paths))
            
            if progress_callback:
                progress_callback(100)
            
            return {
                'success': 1,
                'stems': stem_paths,
                'metadata': metadata,
                'vocals_path': stem_paths.get('vocals'),
                'instrumental_path': stem_paths.get('other')  # "other" is typically instrumental
            }
            
        except Exception as e:
            error_msg = f"Stem separation failed: {str(e)}"
            logger.error("Stem separation failed", error=str(e), exc_info=True)
            
            return {
                'success': 0,
                'error': error_msg,
                'stems': {},
                'metadata': {}
            }
    
    def _load_audio(self, file_path: str) -> Dict[str, Any]:
        """Load audio file and return waveform with metadata."""
        try:
            waveform, sample_rate = torchaudio.load(file_path)
            duration = waveform.shape[1] / sample_rate
            
            return {
                'waveform': waveform,
                'sample_rate': sample_rate,
                'duration': duration
            }
            
        except Exception as e:
            raise ValueError(f"Failed to load audio file {file_path}: {str(e)}")
    
    def _save_stems(self, 
                   separated: torch.Tensor, 
                   output_dir: str, 
                   input_path: str) -> Dict[str, str]:
        """Save separated stems to files."""
        try:
            # Get stem names from model
            stem_names = ['drums', 'bass', 'other', 'vocals']
            if hasattr(self.model, 'sources'):
                stem_names = self.model.sources
            
            stem_paths = {}
            input_filename = Path(input_path).stem
            
            for i, stem_name in enumerate(stem_names):
                if i < separated.shape[0]:  # Ensure we don't exceed available stems
                    # Get the stem audio
                    stem_audio = separated[i]
                    
                    # Create output filename
                    output_filename = f"{input_filename}_{stem_name}.{self.config.output_format}"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Normalize if requested
                    if self.config.normalize:
                        stem_audio = stem_audio / (stem_audio.abs().max() + 1e-8)
                    
                    # Save to file
                    model_sample_rate = getattr(self.model, 'samplerate', getattr(self.model, 'sample_rate', 44100))
                    torchaudio.save(
                        output_path,
                        stem_audio.cpu(),
                        model_sample_rate,
                        bits_per_sample=self.config.bit_depth
                    )
                    
                    stem_paths[stem_name] = output_path
                    logger.info(f"Saved {stem_name} stem", path=output_path)
            
            return stem_paths
            
        except Exception as e:
            raise RuntimeError(f"Failed to save stems: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self._model_loaded:
            self._load_model()
            
        return {
            'model_name': self.config.model_name,
            'device': self.config.device,
            'sample_rate': getattr(self.model, 'samplerate', getattr(self.model, 'sample_rate', 44100)),
            'audio_channels': getattr(self.model, 'audio_channels', 2),
            'stems': getattr(self.model, 'sources', ['drums', 'bass', 'other', 'vocals'])
        }
    
    def cleanup(self):
        """Clean up model and free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self._model_loaded = False
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("Demucs model cleaned up")


# Global handler instance for reuse
_demucs_handler = None

def get_demucs_handler(config: Optional[DemucsConfig] = None) -> DemucsHandler:
    """Get a global instance of the Demucs handler."""
    global _demucs_handler
    
    if _demucs_handler is None:
        _demucs_handler = DemucsHandler(config)
    
    return _demucs_handler 