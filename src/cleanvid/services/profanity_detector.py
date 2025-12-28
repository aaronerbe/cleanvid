"""
Profanity detection service.

Detects profane words in subtitle text and generates mute segments.
"""

import re
from pathlib import Path
from typing import List, Set, Optional

from cleanvid.models.subtitle import SubtitleFile, SubtitleEntry
from cleanvid.models.segment import MuteSegment


class ProfanityDetector:
    """
    Detects profanity in subtitle text.
    
    Loads a list of profane words and detects them in subtitle entries,
    creating mute segments for each detection.
    """
    
    def __init__(self, word_list_path: Path):
        """
        Initialize ProfanityDetector.
        
        Args:
            word_list_path: Path to text file containing profane words.
        
        Raises:
            FileNotFoundError: If word list file not found.
        """
        self.word_list_path = word_list_path
        self.profane_words: Set[str] = set()
        self.word_patterns: List[re.Pattern] = []
        self._load_word_list()
    
    def _load_word_list(self) -> None:
        """
        Load profane words from file.
        
        Raises:
            FileNotFoundError: If word list file not found.
        """
        if not self.word_list_path.exists():
            raise FileNotFoundError(
                f"Word list not found: {self.word_list_path}"
            )
        
        self.profane_words.clear()
        self.word_patterns.clear()
        
        with open(self.word_list_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip whitespace and skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Convert to lowercase for case-insensitive matching
                word = line.lower()
                self.profane_words.add(word)
                
                # Create regex pattern for word boundary matching
                # Handle wildcards (* becomes .*)
                pattern_str = re.escape(word).replace(r'\*', '.*')
                pattern = re.compile(
                    r'\b' + pattern_str + r'\b',
                    re.IGNORECASE
                )
                self.word_patterns.append(pattern)
    
    def reload_word_list(self) -> None:
        """Reload word list from disk."""
        self._load_word_list()
    
    def detect_in_text(self, text: str) -> List[str]:
        """
        Detect profane words in text.
        
        Args:
            text: Text to search for profanity.
        
        Returns:
            List of detected profane words (may contain duplicates).
        """
        detected = []
        
        for pattern in self.word_patterns:
            matches = pattern.findall(text)
            detected.extend(matches)
        
        return detected
    
    def detect_in_entry(
        self,
        entry: SubtitleEntry,
        confidence: float = 1.0
    ) -> List[MuteSegment]:
        """
        Detect profanity in a subtitle entry and create mute segments.
        
        Args:
            entry: Subtitle entry to analyze.
            confidence: Confidence level for detections (0.0-1.0).
        
        Returns:
            List of MuteSegment objects for detected profanity.
        """
        detected_words = self.detect_in_text(entry.text)
        
        if not detected_words:
            return []
        
        # For now, create one segment for the entire subtitle entry
        # In future, could try to estimate word timing within subtitle
        segments = []
        for word in detected_words:
            segment = MuteSegment(
                start_time=entry.start_time,
                end_time=entry.end_time,
                word=word.lower(),
                confidence=confidence
            )
            segments.append(segment)
        
        return segments
    
    def detect_in_subtitle_file(
        self,
        subtitle_file: SubtitleFile,
        confidence: float = 1.0
    ) -> List[MuteSegment]:
        """
        Detect profanity in all subtitle entries.
        
        Args:
            subtitle_file: SubtitleFile to analyze.
            confidence: Confidence level for all detections (0.0-1.0).
        
        Returns:
            List of all MuteSegment objects found.
        """
        all_segments = []
        
        for entry in subtitle_file.entries:
            segments = self.detect_in_entry(entry, confidence=confidence)
            all_segments.extend(segments)
        
        return all_segments
    
    def get_statistics(
        self,
        subtitle_file: SubtitleFile
    ) -> dict:
        """
        Get profanity detection statistics for a subtitle file.
        
        Args:
            subtitle_file: SubtitleFile to analyze.
        
        Returns:
            Dictionary containing detection statistics.
        """
        segments = self.detect_in_subtitle_file(subtitle_file)
        
        # Count occurrences of each word
        word_counts = {}
        for segment in segments:
            word_counts[segment.word] = word_counts.get(segment.word, 0) + 1
        
        # Calculate total muted duration
        total_duration = sum(s.duration for s in segments)
        
        # Get unique entries with profanity
        entries_with_profanity = set()
        for entry in subtitle_file.entries:
            if self.detect_in_text(entry.text):
                entries_with_profanity.add(entry.index)
        
        return {
            "total_detections": len(segments),
            "unique_words_detected": len(word_counts),
            "word_counts": word_counts,
            "total_muted_duration": total_duration,
            "entries_with_profanity": len(entries_with_profanity),
            "total_entries": len(subtitle_file.entries),
            "profanity_percentage": (
                len(entries_with_profanity) / len(subtitle_file.entries) * 100
                if len(subtitle_file.entries) > 0 else 0.0
            ),
        }
    
    def is_clean(self, subtitle_file: SubtitleFile) -> bool:
        """
        Check if subtitle file contains any profanity.
        
        Args:
            subtitle_file: SubtitleFile to check.
        
        Returns:
            True if no profanity detected, False otherwise.
        """
        for entry in subtitle_file.entries:
            if self.detect_in_text(entry.text):
                return False
        return True
    
    def add_word(self, word: str) -> None:
        """
        Add a word to the profanity list (in memory only).
        
        Args:
            word: Word to add.
        """
        word = word.lower().strip()
        if not word:
            return
        
        self.profane_words.add(word)
        
        # Create pattern
        pattern_str = re.escape(word).replace(r'\*', '.*')
        pattern = re.compile(
            r'\b' + pattern_str + r'\b',
            re.IGNORECASE
        )
        self.word_patterns.append(pattern)
    
    def remove_word(self, word: str) -> bool:
        """
        Remove a word from the profanity list (in memory only).
        
        Args:
            word: Word to remove.
        
        Returns:
            True if word was removed, False if not found.
        """
        word = word.lower().strip()
        
        if word in self.profane_words:
            self.profane_words.remove(word)
            # Rebuild patterns (simpler than finding and removing specific pattern)
            self._rebuild_patterns()
            return True
        
        return False
    
    def _rebuild_patterns(self) -> None:
        """Rebuild regex patterns from current word list."""
        self.word_patterns.clear()
        
        for word in self.profane_words:
            pattern_str = re.escape(word).replace(r'\*', '.*')
            pattern = re.compile(
                r'\b' + pattern_str + r'\b',
                re.IGNORECASE
            )
            self.word_patterns.append(pattern)
    
    def get_word_count(self) -> int:
        """Get number of words in profanity list."""
        return len(self.profane_words)
    
    def get_words(self) -> List[str]:
        """Get sorted list of all profane words."""
        return sorted(self.profane_words)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ProfanityDetector(word_list={self.word_list_path}, "
            f"words={len(self.profane_words)})"
        )
    
    def __str__(self) -> str:
        """String representation."""
        return f"ProfanityDetector with {len(self.profane_words)} words"
