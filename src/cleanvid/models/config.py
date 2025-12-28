"""
Configuration models for cleanvid application.

Defines settings and configuration structures using Pydantic for validation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ProcessingConfig(BaseModel):
    """Configuration for video processing behavior."""
    
    max_daily_processing: int = Field(
        default=5,
        ge=1,
        description="Maximum number of videos to process per run"
    )
    max_processing_time_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum processing time in minutes (None = no limit)"
    )
    video_extensions: List[str] = Field(
        default=[".mkv", ".mp4", ".avi", ".mov", ".m4v"],
        description="Supported video file extensions"
    )
    mute_padding_before_ms: int = Field(
        default=500,
        ge=0,
        description="Milliseconds to start muting before detected word"
    )
    mute_padding_after_ms: int = Field(
        default=500,
        ge=0,
        description="Milliseconds to continue muting after detected word"
    )
    
    @validator('video_extensions')
    def validate_extensions(cls, v):
        """Ensure all extensions start with a dot."""
        return [ext if ext.startswith('.') else f'.{ext}' for ext in v]


class PathConfig(BaseModel):
    """Configuration for file paths."""
    
    input_dir: Path = Field(
        default=Path("/input"),
        description="Directory containing original movies"
    )
    output_dir: Path = Field(
        default=Path("/output"),
        description="Directory for filtered movies"
    )
    config_dir: Path = Field(
        default=Path("/config"),
        description="Directory for configuration files"
    )
    logs_dir: Path = Field(
        default=Path("/logs"),
        description="Directory for log files"
    )
    
    @validator('input_dir', 'output_dir', 'config_dir', 'logs_dir')
    def validate_path(cls, v):
        """Ensure paths are absolute."""
        if not v.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return v


class OpenSubtitlesConfig(BaseModel):
    """Configuration for OpenSubtitles integration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether to download subtitles from OpenSubtitles"
    )
    language: str = Field(
        default="en",
        description="Preferred subtitle language (ISO 639-1 code)"
    )
    username: Optional[str] = Field(
        default=None,
        description="OpenSubtitles username"
    )
    password: Optional[str] = Field(
        default=None,
        description="OpenSubtitles password"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="OpenSubtitles API key"
    )


class FFmpegConfig(BaseModel):
    """Configuration for FFmpeg processing."""
    
    threads: int = Field(
        default=2,
        ge=1,
        le=16,
        description="Number of threads for FFmpeg processing"
    )
    audio_codec: str = Field(
        default="aac",
        description="Audio codec for output"
    )
    audio_bitrate: str = Field(
        default="192k",
        description="Audio bitrate for output"
    )
    re_encode_video: bool = Field(
        default=False,
        description="Whether to re-encode video (slower but smaller)"
    )
    video_codec: Optional[str] = Field(
        default=None,
        description="Video codec if re-encoding (e.g., 'libx264')"
    )
    video_crf: Optional[int] = Field(
        default=23,
        ge=0,
        le=51,
        description="CRF value for video encoding (lower = higher quality)"
    )


class Settings(BaseModel):
    """Main application settings."""
    
    processing: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing configuration"
    )
    paths: PathConfig = Field(
        default_factory=PathConfig,
        description="Path configuration"
    )
    opensubtitles: OpenSubtitlesConfig = Field(
        default_factory=OpenSubtitlesConfig,
        description="OpenSubtitles configuration"
    )
    ffmpeg: FFmpegConfig = Field(
        default_factory=FFmpegConfig,
        description="FFmpeg configuration"
    )
    
    class Config:
        """Pydantic config."""
        validate_assignment = True
        extra = "forbid"  # Raise error on unknown fields
    
    def get_word_list_path(self) -> Path:
        """Get path to profanity word list file."""
        return self.paths.config_dir / "profanity_words.txt"
    
    def get_processed_log_path(self) -> Path:
        """Get path to processed videos log file."""
        return self.paths.config_dir / "processed_log.json"
    
    def get_log_file_path(self) -> Path:
        """Get path to main log file."""
        return self.paths.logs_dir / "cleanvid.log"


@dataclass
class Credentials:
    """OpenSubtitles API credentials."""
    
    username: str
    password: str
    api_key: Optional[str] = None
