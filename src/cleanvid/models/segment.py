"""
Mute segment data models.

Defines structures for representing time segments where audio should be muted.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MuteSegment:
    """Represents a time segment where audio should be muted."""
    
    start_time: float  # seconds
    end_time: float    # seconds
    word: str          # The profanity word that triggered this mute
    confidence: float = 1.0  # Confidence level (0.0 - 1.0)
    
    def __post_init__(self):
        """Validate mute segment."""
        if self.start_time < 0:
            raise ValueError(f"Start time cannot be negative: {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"End time ({self.end_time}) must be > start time ({self.start_time})"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1: {self.confidence}")
        if not self.word.strip():
            raise ValueError("Word cannot be empty")
    
    @property
    def duration(self) -> float:
        """Get duration of mute segment in seconds."""
        return self.end_time - self.start_time
    
    def overlaps_with(self, other: 'MuteSegment') -> bool:
        """Check if this segment overlaps with another."""
        return (
            self.start_time < other.end_time and
            self.end_time > other.start_time
        )
    
    def contains_time(self, time: float) -> bool:
        """Check if a time falls within this segment."""
        return self.start_time <= time <= self.end_time
    
    def is_adjacent_to(self, other: 'MuteSegment', tolerance: float = 0.1) -> bool:
        """
        Check if this segment is adjacent to another within tolerance.
        
        Args:
            other: Another mute segment
            tolerance: Maximum gap in seconds to consider adjacent
        
        Returns:
            True if segments are adjacent within tolerance
        """
        gap = min(
            abs(self.end_time - other.start_time),
            abs(other.end_time - self.start_time)
        )
        return gap <= tolerance
    
    def merge_with(self, other: 'MuteSegment') -> 'MuteSegment':
        """
        Merge this segment with another, creating a new segment spanning both.
        
        Args:
            other: Another mute segment to merge with
        
        Returns:
            New MuteSegment covering both original segments
        """
        return MuteSegment(
            start_time=min(self.start_time, other.start_time),
            end_time=max(self.end_time, other.end_time),
            word=f"{self.word}+{other.word}",
            confidence=min(self.confidence, other.confidence)
        )
    
    def add_padding(self, before: float = 0.0, after: float = 0.0) -> 'MuteSegment':
        """
        Create a new segment with padding added before and after.
        
        Args:
            before: Seconds to add before start
            after: Seconds to add after end
        
        Returns:
            New MuteSegment with padding applied
        """
        new_start = max(0.0, self.start_time - before)
        new_end = self.end_time + after
        
        return MuteSegment(
            start_time=new_start,
            end_time=new_end,
            word=self.word,
            confidence=self.confidence
        )
    
    def to_ffmpeg_filter(self) -> str:
        """
        Convert segment to FFmpeg volume filter format.
        
        Returns:
            FFmpeg filter string for muting this segment
        """
        return f"volume=enable='between(t,{self.start_time:.3f},{self.end_time:.3f})':volume=0"
    
    def __str__(self) -> str:
        """String representation."""
        return f"MuteSegment({self.start_time:.2f}s-{self.end_time:.2f}s: '{self.word}')"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"MuteSegment(start_time={self.start_time:.3f}, "
            f"end_time={self.end_time:.3f}, "
            f"word='{self.word}', "
            f"confidence={self.confidence:.2f})"
        )
    
    def __eq__(self, other) -> bool:
        """Check equality based on timing."""
        if not isinstance(other, MuteSegment):
            return False
        return (
            abs(self.start_time - other.start_time) < 0.001 and
            abs(self.end_time - other.end_time) < 0.001
        )
    
    def __lt__(self, other) -> bool:
        """Compare segments by start time for sorting."""
        if not isinstance(other, MuteSegment):
            return NotImplemented
        return self.start_time < other.start_time


def merge_overlapping_segments(segments: List[MuteSegment]) -> List[MuteSegment]:
    """
    Merge overlapping or adjacent mute segments.
    
    Args:
        segments: List of MuteSegment objects
    
    Returns:
        New list with overlapping segments merged
    """
    if not segments:
        return []
    
    # Sort by start time
    sorted_segments = sorted(segments)
    merged = [sorted_segments[0]]
    
    for current in sorted_segments[1:]:
        previous = merged[-1]
        
        # If segments overlap or are adjacent, merge them
        if current.overlaps_with(previous) or current.is_adjacent_to(previous):
            merged[-1] = previous.merge_with(current)
        else:
            merged.append(current)
    
    return merged


def add_padding_to_segments(
    segments: List[MuteSegment],
    before_ms: int = 500,
    after_ms: int = 500
) -> List[MuteSegment]:
    """
    Add padding to all segments.
    
    Args:
        segments: List of MuteSegment objects
        before_ms: Milliseconds to add before each segment
        after_ms: Milliseconds to add after each segment
    
    Returns:
        New list with padding applied to all segments
    """
    before_sec = before_ms / 1000.0
    after_sec = after_ms / 1000.0
    
    padded = [
        segment.add_padding(before=before_sec, after=after_sec)
        for segment in segments
    ]
    
    # Merge any newly overlapping segments after padding
    return merge_overlapping_segments(padded)


def create_ffmpeg_filter_chain(segments: List[MuteSegment]) -> str:
    """
    Create FFmpeg audio filter chain for muting multiple segments.
    
    Args:
        segments: List of MuteSegment objects
    
    Returns:
        FFmpeg filter string for muting all segments
    """
    if not segments:
        return ""
    
    filters = [segment.to_ffmpeg_filter() for segment in segments]
    return ",".join(filters)
