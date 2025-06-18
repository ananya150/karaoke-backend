"""
Librosa Audio Analysis Handler

This module provides comprehensive audio analysis capabilities using Librosa,
specifically optimized for karaoke applications including beat detection,
tempo analysis, and rhythm extraction.
"""

import os
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

import librosa
from scipy import signal

from utils.logger import get_logger


logger = get_logger("librosa_handler")


class LibrosaConfig:
    """Configuration class for Librosa audio analysis."""
    
    def __init__(self):
        # Audio loading parameters
        self.sample_rate = 22050  # Standard sample rate for music analysis
        self.mono = True  # Convert to mono for analysis
        self.offset = 0.0  # Start time offset
        self.duration = None  # Duration to analyze (None = full file)
        
        # Beat tracking parameters
        self.hop_length = 512  # Number of samples between frames
        self.n_fft = 2048  # FFT window size
        self.win_length = None  # Window length (None = n_fft)
        
        # Tempo detection parameters
        self.tempo_min = 60.0  # Minimum BPM
        self.tempo_max = 200.0  # Maximum BPM
        self.tempo_prior = None  # Prior tempo distribution
        self.tempo_units = 'bpm'  # Units for tempo
        
        # Beat tracking algorithm settings
        self.beat_tracker = 'ellis'  # 'ellis', 'degara', or 'crf'
        self.trim_silence = True  # Remove leading/trailing silence
        self.aggregate_beats = True  # Aggregate beat estimates
        
        # Analysis precision
        self.onset_detection = True  # Enable onset detection
        self.onset_units = 'time'  # 'time' or 'frames'
        self.onset_threshold = 0.5  # Onset detection threshold
        
        # Output format
        self.time_precision = 3  # Decimal places for timestamps
        self.include_confidence = True  # Include confidence scores
        
        logger.info("Librosa configuration initialized", 
                   sample_rate=self.sample_rate,
                   beat_tracker=self.beat_tracker,
                   tempo_range=f"{self.tempo_min}-{self.tempo_max}")


class LibrosaHandler:
    """Handler for Librosa-based audio analysis."""
    
    def __init__(self, config: Optional[LibrosaConfig] = None):
        self.config = config or LibrosaConfig()
        self.audio_data = None
        self.sample_rate = None
        self._analysis_cache = {}
        
    def analyze_audio(self, 
                     audio_path: str, 
                     output_dir: str,
                     progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive audio analysis including beat detection and tempo analysis.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save analysis results
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing analysis results and metadata
        """
        try:
            start_time = time.time()
            logger.info("Starting audio analysis", audio_path=audio_path, output_dir=output_dir)
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            if progress_callback:
                progress_callback(5)
            
            # Load audio
            logger.info("Loading audio for analysis")
            self.audio_data, self.sample_rate = librosa.load(
                audio_path,
                sr=self.config.sample_rate,
                mono=self.config.mono,
                offset=self.config.offset,
                duration=self.config.duration
            )
            
            if progress_callback:
                progress_callback(15)
            
            # Get audio properties
            audio_properties = self._get_audio_properties()
            logger.info("Audio properties extracted", 
                       duration=f"{audio_properties['duration']:.2f}s",
                       sample_rate=self.sample_rate)
            
            if progress_callback:
                progress_callback(25)
            
            # Tempo and beat analysis
            logger.info("Performing tempo and beat analysis")
            tempo_results = self._analyze_tempo_and_beats()
            
            if progress_callback:
                progress_callback(50)
            
            # Onset detection
            logger.info("Detecting onsets")
            onset_results = self._detect_onsets()
            
            if progress_callback:
                progress_callback(70)
            
            # Rhythm analysis
            logger.info("Analyzing rhythm patterns")
            rhythm_results = self._analyze_rhythm(tempo_results.get('beat_times', []))
            
            if progress_callback:
                progress_callback(85)
            
            # Combine all results
            analysis_results = {
                'audio_properties': audio_properties,
                'tempo_analysis': tempo_results,
                'onset_analysis': onset_results,
                'rhythm_analysis': rhythm_results
            }
            
            # Save results
            output_files = self._save_analysis_results(analysis_results, output_dir, audio_path)
            
            if progress_callback:
                progress_callback(95)
            
            # Generate metadata
            processing_time = time.time() - start_time
            metadata = {
                'processing_time': processing_time,
                'sample_rate': self.sample_rate,
                'audio_duration': audio_properties['duration'],
                'tempo_bpm': tempo_results.get('tempo_bpm', 0),
                'beat_count': len(tempo_results.get('beats', [])),
                'onset_count': len(onset_results.get('onsets', [])),
                'time_signature': rhythm_results.get('time_signature', '4/4')
            }
            
            logger.info("Audio analysis completed successfully",
                       processing_time=f"{processing_time:.2f}s",
                       tempo_bpm=metadata['tempo_bpm'],
                       beat_count=metadata['beat_count'])
            
            if progress_callback:
                progress_callback(100)
            
            return {
                'success': True,
                'analysis': analysis_results,
                'output_files': output_files,
                'metadata': metadata,
                'tempo_bpm': tempo_results.get('tempo_bpm', 0),
                'beats': tempo_results.get('beats', []),
                'beat_times': tempo_results.get('beat_times', []),
                'onsets': onset_results.get('onsets', [])
            }
            
        except Exception as e:
            error_msg = f"Audio analysis failed: {str(e)}"
            logger.error("Audio analysis failed", error=str(e), exc_info=True)
            
            return {
                'success': False,
                'error': error_msg,
                'analysis': {},
                'output_files': {},
                'metadata': {}
            }
    
    def _get_audio_properties(self) -> Dict[str, Any]:
        """Extract basic audio properties."""
        duration = librosa.get_duration(y=self.audio_data, sr=self.sample_rate)
        
        # RMS energy
        rms = librosa.feature.rms(y=self.audio_data, hop_length=self.config.hop_length)[0]
        
        # Spectral properties
        spectral_centroids = librosa.feature.spectral_centroid(
            y=self.audio_data, sr=self.sample_rate, hop_length=self.config.hop_length
        )[0]
        
        return {
            'duration': round(duration, self.config.time_precision),
            'sample_rate': self.sample_rate,
            'samples': len(self.audio_data),
            'channels': 1 if self.config.mono else 2,
            'rms_energy': {
                'mean': float(np.mean(rms)),
                'std': float(np.std(rms)),
                'max': float(np.max(rms))
            },
            'spectral_centroid': {
                'mean': float(np.mean(spectral_centroids)),
                'std': float(np.std(spectral_centroids))
            }
        }
    
    def _analyze_tempo_and_beats(self) -> Dict[str, Any]:
        """Perform tempo estimation and beat tracking."""
        try:
            # Tempo estimation
            tempo, beats = librosa.beat.beat_track(
                y=self.audio_data,
                sr=self.sample_rate,
                hop_length=self.config.hop_length,
                start_bpm=120.0,  # Initial BPM guess
                tightness=100,  # Tempo tracking tightness
                trim=self.config.trim_silence,
                units='time'
            )
            
            # Convert tempo to scalar if it's an array
            if hasattr(tempo, '__len__') and len(tempo) == 1:
                tempo = float(tempo[0])
            else:
                tempo = float(tempo)
            
            # Convert beats to timestamps
            beat_times = beats.tolist()
            
            # Use the primary tempo estimate (it's already working well)
            final_tempo = float(tempo)
            
            # Beat grid generation
            beat_grid = self._generate_beat_grid(final_tempo, beat_times)
            
            # Beat confidence estimation
            beat_confidence = self._estimate_beat_confidence(beat_times)
            
            return {
                'tempo_bpm': round(final_tempo, 1),
                'tempo_confidence': 1.0,  # Simplified confidence
                'beats': [round(beat, self.config.time_precision) for beat in beat_times],
                'beat_times': beat_times,
                'beat_count': len(beat_times),
                'beat_grid': beat_grid,
                'beat_confidence': beat_confidence,
                'tempo_estimates': [final_tempo],
                'beat_interval': round(60.0 / final_tempo, self.config.time_precision) if final_tempo > 0 else 0
            }
            
        except Exception as e:
            logger.error("Tempo and beat analysis failed", error=str(e))
            return {
                'tempo_bpm': 0,
                'tempo_confidence': 0.0,
                'beats': [],
                'beat_times': [],
                'beat_count': 0,
                'beat_grid': [],
                'beat_confidence': 0.0,
                'tempo_estimates': [],
                'beat_interval': 0
            }
    
    def _detect_onsets(self) -> Dict[str, Any]:
        """Detect onset times in the audio."""
        try:
            # Onset detection
            onsets = librosa.onset.onset_detect(
                y=self.audio_data,
                sr=self.sample_rate,
                hop_length=self.config.hop_length,
                units=self.config.onset_units,
                pre_max=0.03,
                post_max=0.03,  # Must be positive
                pre_avg=0.10,
                post_avg=0.10,
                delta=self.config.onset_threshold,
                wait=0.03
            )
            
            # Convert to time if needed
            if self.config.onset_units == 'frames':
                onset_times = librosa.frames_to_time(
                    onsets, sr=self.sample_rate, hop_length=self.config.hop_length
                )
            else:
                onset_times = onsets
            
            # Onset strength
            onset_strength = librosa.onset.onset_strength(
                y=self.audio_data,
                sr=self.sample_rate,
                hop_length=self.config.hop_length
            )
            
            return {
                'onsets': [round(onset, self.config.time_precision) for onset in onset_times],
                'onset_count': len(onset_times),
                'onset_strength_mean': float(np.mean(onset_strength)),
                'onset_strength_max': float(np.max(onset_strength)),
                'onset_density': len(onset_times) / self._get_audio_properties()['duration']
            }
            
        except Exception as e:
            logger.error("Onset detection failed", error=str(e))
            return {
                'onsets': [],
                'onset_count': 0,
                'onset_strength_mean': 0.0,
                'onset_strength_max': 0.0,
                'onset_density': 0.0
            }
    
    def _analyze_rhythm(self, beat_times: List[float] = None) -> Dict[str, Any]:
        """Analyze rhythm patterns and time signature."""
        try:
            # Tempogram for rhythm analysis
            tempogram = librosa.feature.tempogram(
                y=self.audio_data,
                sr=self.sample_rate,
                hop_length=self.config.hop_length
            )
            
            # Estimate time signature (simplified)
            # This is a basic implementation - more sophisticated methods exist
            tempo_bpm = self._analysis_cache.get('tempo_bpm', 120)
            
            # Common time signatures and their beat patterns
            time_signatures = ['4/4', '3/4', '2/4', '6/8', '12/8']
            
            # For now, default to 4/4 (most common in popular music)
            # In a more advanced implementation, you would analyze beat strength patterns
            estimated_time_signature = '4/4'
            
            # Rhythm regularity (beat tracking consistency)
            if beat_times and len(beat_times) > 2:
                beat_intervals = np.diff(beat_times)
                if np.mean(beat_intervals) > 0:
                    rhythm_regularity = 1.0 - (np.std(beat_intervals) / np.mean(beat_intervals))
                    rhythm_regularity = max(0.0, min(1.0, rhythm_regularity))
                else:
                    rhythm_regularity = 0.0
            else:
                rhythm_regularity = 0.0
            
            return {
                'time_signature': estimated_time_signature,
                'rhythm_regularity': round(rhythm_regularity, 3),
                'tempogram_shape': tempogram.shape,
                'rhythm_complexity': 'simple' if rhythm_regularity > 0.8 else 'complex'
            }
            
        except Exception as e:
            logger.error("Rhythm analysis failed", error=str(e))
            return {
                'time_signature': '4/4',
                'rhythm_regularity': 0.0,
                'tempogram_shape': (0, 0),
                'rhythm_complexity': 'unknown'
            }
    
    def _generate_beat_grid(self, tempo_bpm: float, beat_times: List[float]) -> List[Dict[str, Any]]:
        """Generate a regular beat grid based on tempo."""
        if tempo_bpm <= 0 or not beat_times:
            return []
        
        beat_interval = 60.0 / tempo_bpm
        duration = self._get_audio_properties()['duration']
        
        # Generate regular grid
        grid = []
        current_time = 0.0
        beat_number = 1
        
        while current_time < duration:
            # Find closest actual beat
            if beat_times:
                closest_beat = min(beat_times, key=lambda x: abs(x - current_time))
                deviation = abs(closest_beat - current_time)
            else:
                closest_beat = current_time
                deviation = 0.0
            
            grid.append({
                'beat_number': beat_number,
                'grid_time': round(current_time, self.config.time_precision),
                'actual_beat_time': round(closest_beat, self.config.time_precision),
                'deviation': round(deviation, self.config.time_precision),
                'confidence': max(0.0, 1.0 - (deviation / beat_interval))
            })
            
            current_time += beat_interval
            beat_number += 1
        
        return grid
    
    def _estimate_beat_confidence(self, beat_times: List[float]) -> float:
        """Estimate overall confidence in beat detection."""
        if len(beat_times) < 3:
            return 0.0
        
        # Calculate beat interval consistency
        intervals = np.diff(beat_times)
        if len(intervals) == 0:
            return 0.0
        
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Confidence based on regularity
        if mean_interval > 0:
            confidence = 1.0 - (std_interval / mean_interval)
            return max(0.0, min(1.0, confidence))
        
        return 0.0
    
    def _save_analysis_results(self, analysis_data: Dict[str, Any], 
                              output_dir: str, audio_path: str) -> Dict[str, str]:
        """Save analysis results in multiple formats."""
        try:
            output_files = {}
            input_filename = Path(audio_path).stem
            
            # Save complete analysis JSON
            analysis_path = os.path.join(output_dir, f"{input_filename}_analysis.json")
            with open(analysis_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            output_files['analysis_json'] = analysis_path
            
            # Save beat data for karaoke applications
            beat_data = {
                'tempo_bpm': analysis_data['tempo_analysis'].get('tempo_bpm', 0),
                'beats': analysis_data['tempo_analysis'].get('beats', []),
                'beat_grid': analysis_data['tempo_analysis'].get('beat_grid', []),
                'time_signature': analysis_data['rhythm_analysis'].get('time_signature', '4/4'),
                'duration': analysis_data['audio_properties'].get('duration', 0)
            }
            
            beat_path = os.path.join(output_dir, f"{input_filename}_beats.json")
            with open(beat_path, 'w', encoding='utf-8') as f:
                json.dump(beat_data, f, indent=2, ensure_ascii=False)
            output_files['beats_json'] = beat_path
            
            # Save onset data
            onset_data = {
                'onsets': analysis_data['onset_analysis'].get('onsets', []),
                'onset_count': analysis_data['onset_analysis'].get('onset_count', 0),
                'onset_density': analysis_data['onset_analysis'].get('onset_density', 0)
            }
            
            onset_path = os.path.join(output_dir, f"{input_filename}_onsets.json")
            with open(onset_path, 'w', encoding='utf-8') as f:
                json.dump(onset_data, f, indent=2, ensure_ascii=False)
            output_files['onsets_json'] = onset_path
            
            logger.info("Analysis results saved", 
                       formats=list(output_files.keys()),
                       output_dir=output_dir)
            
            return output_files
            
        except Exception as e:
            logger.error("Failed to save analysis results", error=str(e))
            return {}
    
    def get_analysis_info(self) -> Dict[str, Any]:
        """Get information about the analysis configuration."""
        return {
            'sample_rate': self.config.sample_rate,
            'hop_length': self.config.hop_length,
            'beat_tracker': self.config.beat_tracker,
            'tempo_range': f"{self.config.tempo_min}-{self.config.tempo_max}",
            'onset_detection': self.config.onset_detection
        }
    
    def cleanup(self):
        """Clean up audio data and cache."""
        self.audio_data = None
        self.sample_rate = None
        self._analysis_cache.clear()
        logger.info("Librosa handler cleaned up")


# Global handler instance for reuse
_librosa_handler = None

def get_librosa_handler(config: Optional[LibrosaConfig] = None) -> LibrosaHandler:
    """Get a global instance of the Librosa handler."""
    global _librosa_handler
    
    if _librosa_handler is None:
        _librosa_handler = LibrosaHandler(config)
    
    return _librosa_handler 