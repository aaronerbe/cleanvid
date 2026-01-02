"""
Processing result data models.

Defines structures for tracking processing outcomes and statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from enum import Enum


class ProcessingStatus(Enum):
    """Status of video processing."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VideoMetadata:
    """Metadata about a video file."""
    
    path: Path
    size_bytes: int
    duration_seconds: float
    width: int
    height: int
    video_codec: str
    audio_codec: str
    has_subtitles: bool = False
    subtitle_path: Optional[Path] = None
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def size_gb(self) -> float:
        """Get file size in gigabytes."""
        return self.size_bytes / (1024 * 1024 * 1024)
    
    @property
    def resolution(self) -> str:
        """Get video resolution as string."""
        return f"{self.width}x{self.height}"
    
    @property
    def is_hd(self) -> bool:
        """Check if video is HD (720p or higher)."""
        return self.height >= 720
    
    @property
    def is_4k(self) -> bool:
        """Check if video is 4K."""
        return self.height >= 2160


@dataclass
class ProcessingResult:
    """Result of processing a single video."""
    
    video_path: Path
    status: ProcessingStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output_path: Optional[Path] = None
    segments_muted: int = 0
    subtitle_downloaded: bool = False
    scene_zones_processed: int = 0
    has_custom_scenes: bool = False
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Get processing duration in seconds."""
        if self.end_time is None:
            return 0.0
        delta = self.end_time - self.start_time
        return delta.total_seconds()
    
    @property
    def duration_minutes(self) -> float:
        """Get processing duration in minutes."""
        return self.duration_seconds / 60.0
    
    @property
    def success(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessingStatus.SUCCESS
    
    @property
    def failed(self) -> bool:
        """Check if processing failed."""
        return self.status == ProcessingStatus.FAILED
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def mark_complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark processing as complete."""
        self.end_time = datetime.now()
        if success:
            self.status = ProcessingStatus.SUCCESS
        else:
            self.status = ProcessingStatus.FAILED
            if error:
                self.error_message = error
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "video_path": str(self.video_path),
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "output_path": str(self.output_path) if self.output_path else None,
            "segments_muted": self.segments_muted,
            "subtitle_downloaded": self.subtitle_downloaded,
            "scene_zones_processed": self.scene_zones_processed,
            "has_custom_scenes": self.has_custom_scenes,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }
    
    def __str__(self) -> str:
        """String representation."""
        status_symbol = "✓" if self.success else "✗" if self.failed else "○"
        return f"{status_symbol} {self.video_path.name}: {self.status.value}"


@dataclass
class ProcessingStats:
    """Statistics for a batch processing run."""
    
    total_videos: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_segments_muted: int = 0
    subtitles_downloaded: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def processed(self) -> int:
        """Get number of videos processed (success or failed)."""
        return self.successful + self.failed
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.processed == 0:
            return 0.0
        return (self.successful / self.processed) * 100
    
    @property
    def duration_seconds(self) -> float:
        """Get total processing duration in seconds."""
        if self.end_time is None:
            return 0.0
        delta = self.end_time - self.start_time
        return delta.total_seconds()
    
    @property
    def duration_minutes(self) -> float:
        """Get total processing duration in minutes."""
        return self.duration_seconds / 60.0
    
    @property
    def average_time_per_video(self) -> float:
        """Get average processing time per video in seconds."""
        if self.processed == 0:
            return 0.0
        return self.duration_seconds / self.processed
    
    def add_result(self, result: ProcessingResult) -> None:
        """Add a processing result to statistics."""
        if result.status == ProcessingStatus.SUCCESS:
            self.successful += 1
        elif result.status == ProcessingStatus.FAILED:
            self.failed += 1
        elif result.status == ProcessingStatus.SKIPPED:
            self.skipped += 1
        
        self.total_segments_muted += result.segments_muted
        if result.subtitle_downloaded:
            self.subtitles_downloaded += 1
    
    def mark_complete(self) -> None:
        """Mark batch processing as complete."""
        self.end_time = datetime.now()
    
    def to_summary_string(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "=" * 60,
            "Processing Summary",
            "=" * 60,
            f"Total videos found: {self.total_videos}",
            f"Successfully processed: {self.successful}",
            f"Failed: {self.failed}",
            f"Skipped: {self.skipped}",
            f"Success rate: {self.success_rate:.1f}%",
            f"Total segments muted: {self.total_segments_muted}",
            f"Subtitles downloaded: {self.subtitles_downloaded}",
            f"Total time: {self.duration_minutes:.1f} minutes",
            f"Average per video: {self.average_time_per_video / 60:.1f} minutes",
            "=" * 60,
        ]
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_videos": self.total_videos,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "processed": self.processed,
            "success_rate": round(self.success_rate, 2),
            "total_segments_muted": self.total_segments_muted,
            "subtitles_downloaded": self.subtitles_downloaded,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "duration_minutes": round(self.duration_minutes, 2),
            "average_time_per_video": round(self.average_time_per_video, 2),
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"ProcessingStats({self.successful}/{self.total_videos} successful)"
