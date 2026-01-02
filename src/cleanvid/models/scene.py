"""
Scene data models for custom skip zones.

Handles skip zone definitions for video processing with blur/black/skip modes.
"""

import uuid
from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class ProcessingMode(str, Enum):
    """Video processing mode for skip zones."""
    SKIP = "skip"  # No video modification
    BLUR = "blur"  # Blur video
    BLACK = "black"  # Black out video


class SkipZone(BaseModel):
    """
    Represents a skip zone in a video.
    
    Attributes:
        id: Unique identifier for the zone
        start_time: Start time in seconds
        end_time: End time in seconds
        start_display: Display format (HH:MM:SS or MM:SS)
        end_display: Display format (HH:MM:SS or MM:SS)
        description: User description of the scene
        mode: Processing mode (skip/blur/black)
        mute: Whether to mute audio during this zone
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = Field(gt=0, description="Start time in seconds")
    end_time: float = Field(gt=0, description="End time in seconds")
    start_display: str = Field(description="Display format HH:MM:SS or MM:SS")
    end_display: str = Field(description="Display format HH:MM:SS or MM:SS")
    description: str = Field(max_length=200, description="Scene description")
    mode: ProcessingMode = Field(default=ProcessingMode.SKIP)
    mute: bool = Field(default=False, description="Mute audio during zone")
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        """Ensure end time is after start time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be greater than start_time')
        return v
    
    @validator('mute')
    def validate_mute_with_mode(cls, v, values):
        """Mute only allowed with blur or black modes."""
        if 'mode' in values and v and values['mode'] == ProcessingMode.SKIP:
            raise ValueError('mute can only be enabled with blur or black modes')
        return v
    
    @property
    def duration(self) -> float:
        """Get duration of skip zone in seconds."""
        return self.end_time - self.start_time
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'start_display': self.start_display,
            'end_display': self.end_display,
            'description': self.description,
            'mode': self.mode.value,
            'mute': self.mute
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SkipZone':
        """Create from dictionary."""
        return cls(**data)


class VideoSceneFilters(BaseModel):
    """
    Scene filters for a video file.
    
    Attributes:
        video_path: Path to the video file
        title: Human-readable title
        skip_zones: List of skip zones
        last_modified: Last modification timestamp
    """
    video_path: str
    title: str
    skip_zones: List[SkipZone] = Field(default_factory=list)
    last_modified: datetime = Field(default_factory=datetime.now)
    
    def add_zone(self, zone: SkipZone) -> None:
        """Add a skip zone."""
        self.skip_zones.append(zone)
        self.last_modified = datetime.now()
    
    def remove_zone(self, zone_id: str) -> bool:
        """Remove a skip zone by ID. Returns True if removed."""
        initial_length = len(self.skip_zones)
        self.skip_zones = [z for z in self.skip_zones if z.id != zone_id]
        if len(self.skip_zones) < initial_length:
            self.last_modified = datetime.now()
            return True
        return False
    
    def get_zone(self, zone_id: str) -> Optional[SkipZone]:
        """Get a skip zone by ID."""
        for zone in self.skip_zones:
            if zone.id == zone_id:
                return zone
        return None
    
    def update_zone(self, zone_id: str, updated_zone: SkipZone) -> bool:
        """Update a skip zone. Returns True if updated."""
        for i, zone in enumerate(self.skip_zones):
            if zone.id == zone_id:
                self.skip_zones[i] = updated_zone
                self.last_modified = datetime.now()
                return True
        return False
    
    def get_zones_by_mode(self, mode: ProcessingMode) -> List[SkipZone]:
        """Get all zones with a specific processing mode."""
        return [z for z in self.skip_zones if z.mode == mode]
    
    def get_mute_zones(self) -> List[SkipZone]:
        """Get all zones that should be muted."""
        return [z for z in self.skip_zones if z.mute]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'video_path': self.video_path,
            'title': self.title,
            'skip_zones': [z.to_dict() for z in self.skip_zones],
            'last_modified': self.last_modified.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VideoSceneFilters':
        """Create from dictionary."""
        zones = [SkipZone.from_dict(z) for z in data.get('skip_zones', [])]
        return cls(
            video_path=data['video_path'],
            title=data['title'],
            skip_zones=zones,
            last_modified=datetime.fromisoformat(data['last_modified'])
        )


def parse_timestamp(timestamp: str) -> float:
    """
    Parse timestamp string to seconds.
    
    Supports formats:
    - HH:MM:SS
    - MM:SS
    - SS
    
    Args:
        timestamp: Timestamp string
    
    Returns:
        Time in seconds
    
    Raises:
        ValueError: If format is invalid
    """
    parts = timestamp.strip().split(':')
    
    try:
        if len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # MM:SS
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        elif len(parts) == 1:  # SS
            return float(parts[0])
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}")
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {timestamp}") from e


def format_timestamp(seconds: float) -> str:
    """
    Format seconds to HH:MM:SS or MM:SS.
    
    Args:
        seconds: Time in seconds
    
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def validate_skip_zone_timestamps(start: str, end: str) -> tuple[float, float, str, str]:
    """
    Validate and parse skip zone timestamps.
    
    Args:
        start: Start timestamp string
        end: End timestamp string
    
    Returns:
        Tuple of (start_seconds, end_seconds, start_display, end_display)
    
    Raises:
        ValueError: If timestamps are invalid or end <= start
    """
    start_seconds = parse_timestamp(start)
    end_seconds = parse_timestamp(end)
    
    if end_seconds <= start_seconds:
        raise ValueError("End timestamp must be after start timestamp")
    
    start_display = format_timestamp(start_seconds)
    end_display = format_timestamp(end_seconds)
    
    return start_seconds, end_seconds, start_display, end_display
