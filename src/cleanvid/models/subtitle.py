"""
Subtitle data models.

Defines structures for representing subtitle files and entries.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SubtitleEntry:
    """Represents a single subtitle entry with timing and text."""
    
    index: int
    start_time: float  # seconds
    end_time: float    # seconds
    text: str
    
    def __post_init__(self):
        """Validate subtitle entry."""
        if self.start_time < 0:
            raise ValueError(f"Start time cannot be negative: {self.start_time}")
        if self.end_time < self.start_time:
            raise ValueError(
                f"End time ({self.end_time}) must be >= start time ({self.start_time})"
            )
        if not self.text.strip():
            raise ValueError("Subtitle text cannot be empty")
    
    @property
    def duration(self) -> float:
        """Get duration of subtitle in seconds."""
        return self.end_time - self.start_time
    
    def contains_time(self, time: float) -> bool:
        """Check if a given time falls within this subtitle's timespan."""
        return self.start_time <= time <= self.end_time
    
    def overlaps_with(self, other: 'SubtitleEntry') -> bool:
        """Check if this subtitle overlaps with another."""
        return (
            self.contains_time(other.start_time) or
            self.contains_time(other.end_time) or
            other.contains_time(self.start_time) or
            other.contains_time(self.end_time)
        )
    
    def __str__(self) -> str:
        """String representation."""
        return f"SubtitleEntry({self.index}: {self.start_time:.2f}s-{self.end_time:.2f}s)"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"SubtitleEntry(index={self.index}, "
            f"start_time={self.start_time:.3f}, "
            f"end_time={self.end_time:.3f}, "
            f"text='{self.text[:30]}...')"
        )


@dataclass
class SubtitleFile:
    """Represents a subtitle file with all its entries."""
    
    path: Path
    entries: List[SubtitleEntry] = field(default_factory=list)
    encoding: str = "utf-8"
    language: Optional[str] = None
    
    def __post_init__(self):
        """Validate subtitle file."""
        if not self.path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {self.path}")
    
    @property
    def duration(self) -> float:
        """Get total duration of subtitle file."""
        if not self.entries:
            return 0.0
        return max(entry.end_time for entry in self.entries)
    
    @property
    def entry_count(self) -> int:
        """Get number of subtitle entries."""
        return len(self.entries)
    
    def get_entries_in_range(
        self, 
        start_time: float, 
        end_time: float
    ) -> List[SubtitleEntry]:
        """Get all subtitle entries within a time range."""
        return [
            entry for entry in self.entries
            if entry.start_time < end_time and entry.end_time > start_time
        ]
    
    def search_text(self, query: str, case_sensitive: bool = False) -> List[SubtitleEntry]:
        """Search for text in subtitle entries."""
        if not case_sensitive:
            query = query.lower()
        
        matches = []
        for entry in self.entries:
            text = entry.text if case_sensitive else entry.text.lower()
            if query in text:
                matches.append(entry)
        
        return matches
    
    def get_entry_by_index(self, index: int) -> Optional[SubtitleEntry]:
        """Get subtitle entry by its index number."""
        for entry in self.entries:
            if entry.index == index:
                return entry
        return None
    
    def get_entry_at_time(self, time: float) -> Optional[SubtitleEntry]:
        """Get subtitle entry active at a specific time."""
        for entry in self.entries:
            if entry.contains_time(time):
                return entry
        return None
    
    def __len__(self) -> int:
        """Return number of entries."""
        return len(self.entries)
    
    def __iter__(self):
        """Iterate over entries."""
        return iter(self.entries)
    
    def __getitem__(self, index: int) -> SubtitleEntry:
        """Get entry by list index (not subtitle index)."""
        return self.entries[index]
    
    def __str__(self) -> str:
        """String representation."""
        return f"SubtitleFile({self.path.name}, {self.entry_count} entries)"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"SubtitleFile(path={self.path}, "
            f"entries={self.entry_count}, "
            f"encoding={self.encoding}, "
            f"language={self.language})"
        )
