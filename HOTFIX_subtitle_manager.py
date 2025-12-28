"""
Subtitle management service.

Handles subtitle file operations including parsing, downloading, and format handling.
"""

import pysrt
from pathlib import Path
from typing import Optional, List
from subliminal import Video, download_best_subtitles, save_subtitles
from subliminal.subtitle import Subtitle as SubliminalSubtitle
from babelfish import Language

from cleanvid.models.subtitle import SubtitleFile, SubtitleEntry
from cleanvid.models.config import OpenSubtitlesConfig


class SubtitleManager:
    """
    Manages subtitle file operations.
    
    Handles parsing SRT files, downloading subtitles from OpenSubtitles,
    and converting between formats.
    """
    
    def __init__(self, config: Optional[OpenSubtitlesConfig] = None):
        """
        Initialize SubtitleManager.
        
        Args:
            config: OpenSubtitles configuration. If None, downloading is disabled.
        """
        self.config = config or OpenSubtitlesConfig(enabled=False)
    
    def parse_srt(self, srt_path: Path) -> SubtitleFile:
        """
        Parse an SRT subtitle file with automatic encoding detection.
        
        Args:
            srt_path: Path to SRT file.
        
        Returns:
            SubtitleFile object with parsed entries.
        
        Raises:
            FileNotFoundError: If SRT file not found.
            ValueError: If SRT file is invalid or cannot be parsed.
        """
        if not srt_path.exists():
            raise FileNotFoundError(f"SRT file not found: {srt_path}")
        
        # Try multiple encodings in order of likelihood
        encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin-1']
        
        last_error = None
        for encoding in encodings:
            try:
                # Parse with pysrt using this encoding
                subs = pysrt.open(str(srt_path), encoding=encoding)
                
                # Convert to our SubtitleEntry format
                entries = []
                for sub in subs:
                    # Convert pysrt time to seconds
                    start_time = self._time_to_seconds(sub.start)
                    end_time = self._time_to_seconds(sub.end)
                    
                    entry = SubtitleEntry(
                        index=sub.index,
                        start_time=start_time,
                        end_time=end_time,
                        text=sub.text
                    )
                    entries.append(entry)
                
                # Successfully parsed!
                print(f"  Subtitle encoding: {encoding}")
                
                return SubtitleFile(
                    path=srt_path,
                    entries=entries,
                    encoding=encoding,
                    language=None  # Will be detected if needed
                )
            
            except UnicodeDecodeError as e:
                # This encoding didn't work, try next one
                last_error = e
                continue
            except Exception as e:
                # Some other error - might be valid for this encoding
                # Save it but try other encodings first
                if last_error is None:
                    last_error = e
                continue
        
        # If we get here, none of the encodings worked
        if last_error:
            raise ValueError(f"Failed to parse SRT file {srt_path}: {last_error}")
        else:
            raise ValueError(f"Failed to parse SRT file {srt_path}: Unknown error")
    
    def _time_to_seconds(self, time_obj) -> float:
        """
        Convert pysrt SubRipTime to seconds.
        
        Args:
            time_obj: pysrt SubRipTime object.
        
        Returns:
            Time in seconds as float.
        """
        return (
            time_obj.hours * 3600 +
            time_obj.minutes * 60 +
            time_obj.seconds +
            time_obj.milliseconds / 1000.0
        )
    
    def find_subtitle_for_video(self, video_path: Path) -> Optional[Path]:
        """
        Find subtitle file for a video.
        
        Searches for subtitle files with same base name as video.
        Supported extensions: .srt, .sub, .ssa, .ass
        
        Args:
            video_path: Path to video file.
        
        Returns:
            Path to subtitle file if found, None otherwise.
        """
        video_dir = video_path.parent
        video_stem = video_path.stem
        
        # Try common subtitle extensions
        for ext in ['.srt', '.sub', '.ssa', '.ass']:
            subtitle_path = video_dir / f"{video_stem}{ext}"
            if subtitle_path.exists():
                return subtitle_path
        
        return None
    
    def download_subtitles(
        self,
        video_path: Path,
        #language: str = 'en',
        language: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Download subtitles for a video from OpenSubtitles.
        
        Args:
            video_path: Path to video file.
            language: Language code (e.g., 'en', 'es').
            output_dir: Directory to save subtitles. If None, uses video directory.
        
        Returns:
            Path to downloaded subtitle file, or None if download failed.
        
        Raises:
            RuntimeError: If OpenSubtitles is disabled in config.
        """
        if not self.config.enabled:
            raise RuntimeError(
                "Subtitle downloading is disabled. Enable OpenSubtitles in configuration."
            )
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Use config language if not specified
        if language is None:
            language = self.config.language
        
        try:
            # Create Video object for subliminal
            video = Video.fromname(str(video_path))
            
            # Set language
            languages = {Language(language)}
            
            # Download best subtitles
            subtitles = download_best_subtitles(
                {video},
                languages,
                # Add providers based on config
                providers=['opensubtitles'] if self.config.enabled else []
            )
            
            if not subtitles or video not in subtitles or not subtitles[video]:
                return None
            
            # Save subtitles
            subtitle = list(subtitles[video])[0]
            
            # Determine output directory
            if output_dir is None:
                output_dir = video_path.parent
            
            # Save subtitle
            save_subtitles(video, subtitles[video], single=True, directory=str(output_dir))
            
            # Return path to saved subtitle
            subtitle_path = output_dir / f"{video_path.stem}.{language}.srt"
            if subtitle_path.exists():
                return subtitle_path
            
            # Try without language code
            subtitle_path = output_dir / f"{video_path.stem}.srt"
            if subtitle_path.exists():
                return subtitle_path
            
            return None
        
        except Exception as e:
            # Log error but don't crash
            print(f"Failed to download subtitles for {video_path}: {e}")
            return None
    
    def get_or_download_subtitle(
            self,
            video_path: Path,
            language: Optional[str] = None
        ) -> Optional[Path]:
        """
        Get subtitle for video, downloading if necessary.
        
        First searches for existing subtitle file. If not found and
        OpenSubtitles is enabled, attempts to download.
        
        Args:
            video_path: Path to video file.
            language: Language code for download.
        
        Returns:
            Path to subtitle file (existing or downloaded), or None if not available.
        """
        # Use config language if not specified
        if language is None:
            language = self.config.language
        
        # First try to find existing subtitle
        existing = self.find_subtitle_for_video(video_path)
        if existing:
            return existing
        
        # If OpenSubtitles enabled, try to download
        if self.config.enabled:
            return self.download_subtitles(video_path, language)
        
        return None
    
    def load_subtitle_file(
            self,
            video_path: Path,
            language: Optional[str] = None,
            auto_download: bool = True
        ) -> Optional[SubtitleFile]:
        """
        Load subtitle file for a video, downloading if needed.
        
        Args:
            video_path: Path to video file.
            language: Language code for download.
            auto_download: If True, downloads subtitle if not found.
        
        Returns:
            SubtitleFile object, or None if subtitle not available.
        """
        # Use config language if not specified
        if language is None:
            language = self.config.language
        
        # Get subtitle path
        if auto_download:
            subtitle_path = self.get_or_download_subtitle(video_path, language)
        else:
            subtitle_path = self.find_subtitle_for_video(video_path)
        
        if not subtitle_path:
            return None
        
        # Parse and return
        return self.parse_srt(subtitle_path)
    
    def validate_subtitle_file(self, subtitle_path: Path) -> tuple[bool, List[str]]:
        """
        Validate a subtitle file.
        
        Args:
            subtitle_path: Path to subtitle file.
        
        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []
        
        # Check file exists
        if not subtitle_path.exists():
            errors.append(f"File not found: {subtitle_path}")
            return (False, errors)
        
        # Check file extension
        if subtitle_path.suffix.lower() not in ['.srt', '.sub', '.ssa', '.ass']:
            errors.append(f"Unsupported subtitle format: {subtitle_path.suffix}")
        
        # Try to parse
        try:
            subtitle_file = self.parse_srt(subtitle_path)
            
            # Check has entries
            if len(subtitle_file.entries) == 0:
                errors.append("Subtitle file is empty")
            
            # Check for timing issues
            for i, entry in enumerate(subtitle_file.entries):
                if entry.start_time < 0:
                    errors.append(f"Entry {i+1} has negative start time")
                if entry.end_time <= entry.start_time:
                    errors.append(f"Entry {i+1} has invalid timing")
        
        except Exception as e:
            errors.append(f"Failed to parse subtitle file: {e}")
        
        return (len(errors) == 0, errors)
    
    def get_subtitle_stats(self, subtitle_file: SubtitleFile) -> dict:
        """
        Get statistics about a subtitle file.
        
        Args:
            subtitle_file: SubtitleFile to analyze.
        
        Returns:
            Dictionary with subtitle statistics.
        """
        if len(subtitle_file.entries) == 0:
            return {
                'total_entries': 0,
                'total_duration': 0.0,
                'average_entry_duration': 0.0,
                'total_text_length': 0,
                'average_text_length': 0.0,
            }
        
        total_text_length = sum(len(entry.text) for entry in subtitle_file.entries)
        total_entry_duration = sum(entry.duration for entry in subtitle_file.entries)
        
        return {
            'total_entries': len(subtitle_file.entries),
            'total_duration': subtitle_file.duration,
            'average_entry_duration': total_entry_duration / len(subtitle_file.entries),
            'total_text_length': total_text_length,
            'average_text_length': total_text_length / len(subtitle_file.entries),
            'first_entry_time': subtitle_file.entries[0].start_time,
            'last_entry_time': subtitle_file.entries[-1].end_time,
        }
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"SubtitleManager(opensubtitles_enabled={self.config.enabled}, "
            f"language={self.config.language})"
        )
    
    def __str__(self) -> str:
        """String representation."""
        status = "enabled" if self.config.enabled else "disabled"
        return f"SubtitleManager (OpenSubtitles: {status})"
