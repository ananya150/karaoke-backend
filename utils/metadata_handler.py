"""
Audio metadata extraction utilities for the Karaoke Backend.
Handles extraction of audio metadata including cover art, title, artist, album, etc.
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from mutagen import File
from mutagen.id3 import ID3NoHeaderError, APIC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

from utils.logger import get_logger

logger = get_logger("metadata_handler")


class AudioMetadataExtractor:
    """Extract metadata and cover art from audio files."""

    SUPPORTED_COVER_FORMATS = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp']
    
    @classmethod
    def extract_metadata(cls, file_path: str, job_id: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from audio file including cover art.
        
        Args:
            file_path: Path to the audio file
            job_id: Job ID for organizing output files
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            logger.info("Extracting audio metadata", file_path=file_path, job_id=job_id)
            
            # Load audio file
            audio_file = File(file_path)
            if audio_file is None:
                logger.warning("Could not load audio file for metadata extraction", file_path=file_path)
                return cls._get_default_metadata()
            
            # Extract basic metadata
            metadata = {
                'title': cls._get_tag_value(audio_file, ['TIT2', 'TITLE', '\xa9nam']),
                'artist': cls._get_tag_value(audio_file, ['TPE1', 'ARTIST', '\xa9ART']),
                'album': cls._get_tag_value(audio_file, ['TALB', 'ALBUM', '\xa9alb']),
                'albumartist': cls._get_tag_value(audio_file, ['TPE2', 'ALBUMARTIST', 'aART']),
                'date': cls._get_tag_value(audio_file, ['TDRC', 'DATE', '\xa9day']),
                'year': cls._get_year(audio_file),
                'genre': cls._get_tag_value(audio_file, ['TCON', 'GENRE', '\xa9gen']),
                'track': cls._get_track_number(audio_file),
                'tracktotal': cls._get_track_total(audio_file),
                'disc': cls._get_disc_number(audio_file),
                'duration': cls._get_duration(audio_file),
                'bitrate': cls._get_bitrate(audio_file),
                'sample_rate': cls._get_sample_rate(audio_file),
                'channels': cls._get_channels(audio_file),
                'format': cls._get_format(file_path),
                'filesize': os.path.getsize(file_path)
            }
            
            # Extract cover art
            cover_info = cls._extract_cover_art(audio_file, file_path, job_id)
            metadata.update(cover_info)
            
            logger.info("Metadata extraction completed", 
                       job_id=job_id,
                       title=metadata.get('title', 'Unknown'),
                       artist=metadata.get('artist', 'Unknown'),
                       has_cover=bool(metadata.get('cover_image_path')))
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to extract metadata", 
                        file_path=file_path, 
                        job_id=job_id, 
                        error=str(e))
            return cls._get_default_metadata()
    
    @classmethod
    def _get_tag_value(cls, audio_file: File, tag_names: List[str]) -> Optional[str]:
        """Get tag value from audio file, trying multiple tag names."""
        if not audio_file.tags:
            return None
            
        for tag_name in tag_names:
            if tag_name in audio_file.tags:
                tag_value = audio_file.tags[tag_name]
                if isinstance(tag_value, list) and tag_value:
                    return str(tag_value[0])
                elif tag_value:
                    return str(tag_value)
        return None
    
    @classmethod
    def _get_year(cls, audio_file: File) -> Optional[int]:
        """Extract year from date fields."""
        date_str = cls._get_tag_value(audio_file, ['TDRC', 'DATE', '\xa9day', 'YEAR'])
        if date_str:
            try:
                # Extract year from various date formats
                year_str = date_str.split('-')[0].split('/')[0][:4]
                return int(year_str)
            except (ValueError, IndexError):
                pass
        return None
    
    @classmethod
    def _get_track_number(cls, audio_file: File) -> Optional[int]:
        """Extract track number."""
        track_str = cls._get_tag_value(audio_file, ['TRCK', 'TRACKNUMBER', 'trkn'])
        if track_str:
            try:
                # Handle "track/total" format
                track_num = track_str.split('/')[0]
                return int(track_num)
            except (ValueError, IndexError):
                pass
        return None
    
    @classmethod
    def _get_track_total(cls, audio_file: File) -> Optional[int]:
        """Extract total number of tracks."""
        track_str = cls._get_tag_value(audio_file, ['TRCK', 'TRACKTOTAL', 'trkn'])
        if track_str and '/' in track_str:
            try:
                return int(track_str.split('/')[1])
            except (ValueError, IndexError):
                pass
        return None
    
    @classmethod
    def _get_disc_number(cls, audio_file: File) -> Optional[int]:
        """Extract disc number."""
        disc_str = cls._get_tag_value(audio_file, ['TPOS', 'DISCNUMBER', 'disk'])
        if disc_str:
            try:
                # Handle "disc/total" format
                disc_num = disc_str.split('/')[0]
                return int(disc_num)
            except (ValueError, IndexError):
                pass
        return None
    
    @classmethod
    def _get_duration(cls, audio_file: File) -> Optional[float]:
        """Get audio duration in seconds."""
        if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
            return round(audio_file.info.length, 2)
        return None
    
    @classmethod
    def _get_bitrate(cls, audio_file: File) -> Optional[int]:
        """Get audio bitrate."""
        if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'bitrate'):
            return audio_file.info.bitrate
        return None
    
    @classmethod
    def _get_sample_rate(cls, audio_file: File) -> Optional[int]:
        """Get audio sample rate."""
        if hasattr(audio_file, 'info'):
            for attr in ['sample_rate', 'samplerate']:
                if hasattr(audio_file.info, attr):
                    return getattr(audio_file.info, attr)
        return None
    
    @classmethod
    def _get_channels(cls, audio_file: File) -> Optional[int]:
        """Get number of audio channels."""
        if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'channels'):
            return audio_file.info.channels
        return None
    
    @classmethod
    def _get_format(cls, file_path: str) -> str:
        """Get audio format from file extension."""
        return Path(file_path).suffix.lower().lstrip('.')
    
    @classmethod
    def _extract_cover_art(cls, audio_file: File, file_path: str, job_id: str) -> Dict[str, Any]:
        """Extract cover art from audio file."""
        cover_info = {
            'cover_image_path': None,
            'cover_image_format': None,
            'cover_image_size': None,
            'cover_image_width': None,
            'cover_image_height': None
        }
        
        try:
            cover_data = None
            cover_format = None
            
            # Try different methods based on file type
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.mp3':
                cover_data, cover_format = cls._extract_mp3_cover(audio_file)
            elif file_ext == '.mp4' or file_ext == '.m4a':
                cover_data, cover_format = cls._extract_mp4_cover(audio_file)
            elif file_ext == '.flac':
                cover_data, cover_format = cls._extract_flac_cover(audio_file)
            elif file_ext == '.ogg':
                cover_data, cover_format = cls._extract_ogg_cover(audio_file)
            
            if cover_data and cover_format:
                # Save cover art to file
                cover_path = cls._save_cover_art(cover_data, cover_format, job_id)
                if cover_path:
                    cover_info.update({
                        'cover_image_path': cover_path,
                        'cover_image_format': cover_format,
                        'cover_image_size': len(cover_data)
                    })
                    
                    # Try to get image dimensions
                    try:
                        from PIL import Image
                        import io
                        image = Image.open(io.BytesIO(cover_data))
                        cover_info.update({
                            'cover_image_width': image.width,
                            'cover_image_height': image.height
                        })
                    except ImportError:
                        logger.warning("PIL not available for image dimension extraction", job_id=job_id)
                    except Exception:
                        pass  # Ignore errors getting dimensions
            
        except Exception as e:
            logger.error("Failed to extract cover art", 
                        file_path=file_path, 
                        job_id=job_id, 
                        error=str(e))
        
        return cover_info
    
    @classmethod
    def _extract_mp3_cover(cls, audio_file: File) -> tuple:
        """Extract cover art from MP3 file."""
        if not audio_file.tags:
            return None, None
            
        for key in audio_file.tags:
            if key.startswith('APIC:'):
                apic = audio_file.tags[key]
                if hasattr(apic, 'data') and hasattr(apic, 'mime'):
                    return apic.data, apic.mime
        return None, None
    
    @classmethod
    def _extract_mp4_cover(cls, audio_file: File) -> tuple:
        """Extract cover art from MP4/M4A file."""
        if not audio_file.tags:
            return None, None
            
        if 'covr' in audio_file.tags:
            covers = audio_file.tags['covr']
            if covers:
                cover_data = covers[0]
                # MP4 cover format detection
                if cover_data[:4] == b'\xff\xd8\xff\xe0':
                    return cover_data, 'image/jpeg'
                elif cover_data[:8] == b'\x89PNG\r\n\x1a\n':
                    return cover_data, 'image/png'
                else:
                    return cover_data, 'image/jpeg'  # Default to JPEG
        return None, None
    
    @classmethod
    def _extract_flac_cover(cls, audio_file: File) -> tuple:
        """Extract cover art from FLAC file."""
        if hasattr(audio_file, 'pictures') and audio_file.pictures:
            picture = audio_file.pictures[0]
            return picture.data, picture.mime
        return None, None
    
    @classmethod
    def _extract_ogg_cover(cls, audio_file: File) -> tuple:
        """Extract cover art from OGG file."""
        # OGG Vorbis uses FLAC-style pictures
        return cls._extract_flac_cover(audio_file)
    
    @classmethod
    def _save_cover_art(cls, cover_data: bytes, cover_format: str, job_id: str) -> Optional[str]:
        """Save cover art data to file."""
        try:
            # Determine file extension from MIME type
            ext_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/bmp': '.bmp'
            }
            
            file_ext = ext_map.get(cover_format, '.jpg')
            
            # Create job directory if it doesn't exist
            from config import settings
            job_dir = Path(settings.jobs_folder) / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            
            # Save cover art
            cover_filename = f"cover{file_ext}"
            cover_path = job_dir / cover_filename
            
            with open(cover_path, 'wb') as f:
                f.write(cover_data)
            
            logger.info("Cover art saved", 
                       job_id=job_id, 
                       cover_path=str(cover_path),
                       size=len(cover_data))
            
            return str(cover_path)
            
        except Exception as e:
            logger.error("Failed to save cover art", 
                        job_id=job_id, 
                        error=str(e))
            return None
    
    @classmethod
    def _get_default_metadata(cls) -> Dict[str, Any]:
        """Return default metadata structure when extraction fails."""
        return {
            'title': None,
            'artist': None,
            'album': None,
            'albumartist': None,
            'date': None,
            'year': None,
            'genre': None,
            'track': None,
            'tracktotal': None,
            'disc': None,
            'duration': None,
            'bitrate': None,
            'sample_rate': None,
            'channels': None,
            'format': None,
            'filesize': None,
            'cover_image_path': None,
            'cover_image_format': None,
            'cover_image_size': None,
            'cover_image_width': None,
            'cover_image_height': None
        }


# Global instance
metadata_extractor = AudioMetadataExtractor() 