"""
Unit tests for subtitle models.

Tests SubtitleEntry and SubtitleFile classes.
"""

import pytest
from pathlib import Path
from cleanvid.models.subtitle import SubtitleEntry, SubtitleFile


class TestSubtitleEntry:
    """Test SubtitleEntry model."""
    
    def test_create_valid_entry(self):
        """Test creating a valid subtitle entry."""
        entry = SubtitleEntry(
            index=1,
            start_time=10.5,
            end_time=15.2,
            text="Hello world"
        )
        assert entry.index == 1
        assert entry.start_time == 10.5
        assert entry.end_time == 15.2
        assert entry.text == "Hello world"
    
    def test_duration_property(self):
        """Test duration calculation."""
        entry = SubtitleEntry(
            index=1,
            start_time=10.0,
            end_time=15.0,
            text="Test"
        )
        assert entry.duration == 5.0
    
    def test_validates_positive_start_time(self):
        """Test start time must be non-negative."""
        with pytest.raises(ValueError, match="cannot be negative"):
            SubtitleEntry(
                index=1,
                start_time=-1.0,
                end_time=10.0,
                text="Test"
            )
    
    def test_validates_end_time_after_start(self):
        """Test end time must be >= start time."""
        with pytest.raises(ValueError, match="must be >= start time"):
            SubtitleEntry(
                index=1,
                start_time=15.0,
                end_time=10.0,
                text="Test"
            )
    
    def test_allows_same_start_and_end_time(self):
        """Test start and end can be equal (instant subtitle)."""
        entry = SubtitleEntry(
            index=1,
            start_time=10.0,
            end_time=10.0,
            text="Flash"
        )
        assert entry.duration == 0.0
    
    def test_validates_non_empty_text(self):
        """Test text cannot be empty."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SubtitleEntry(
                index=1,
                start_time=10.0,
                end_time=15.0,
                text=""
            )
        
        with pytest.raises(ValueError, match="cannot be empty"):
            SubtitleEntry(
                index=1,
                start_time=10.0,
                end_time=15.0,
                text="   "
            )
    
    def test_contains_time(self):
        """Test time containment check."""
        entry = SubtitleEntry(
            index=1,
            start_time=10.0,
            end_time=20.0,
            text="Test"
        )
        
        assert entry.contains_time(10.0) is True
        assert entry.contains_time(15.0) is True
        assert entry.contains_time(20.0) is True
        assert entry.contains_time(9.9) is False
        assert entry.contains_time(20.1) is False
    
    def test_overlaps_with(self):
        """Test overlap detection."""
        entry1 = SubtitleEntry(1, 10.0, 20.0, "First")
        entry2 = SubtitleEntry(2, 15.0, 25.0, "Second")
        entry3 = SubtitleEntry(3, 25.0, 30.0, "Third")
        
        assert entry1.overlaps_with(entry2) is True
        assert entry2.overlaps_with(entry1) is True
        assert entry1.overlaps_with(entry3) is False
        assert entry2.overlaps_with(entry3) is False
    
    def test_overlaps_with_contained(self):
        """Test overlap when one entry is contained in another."""
        outer = SubtitleEntry(1, 10.0, 30.0, "Outer")
        inner = SubtitleEntry(2, 15.0, 20.0, "Inner")
        
        assert outer.overlaps_with(inner) is True
        assert inner.overlaps_with(outer) is True
    
    def test_str_representation(self):
        """Test string representation."""
        entry = SubtitleEntry(1, 10.5, 15.2, "Test")
        assert "SubtitleEntry(1: 10.50s-15.20s)" in str(entry)
    
    def test_repr_representation(self):
        """Test detailed representation."""
        entry = SubtitleEntry(1, 10.5, 15.2, "Hello world this is a long text")
        repr_str = repr(entry)
        assert "index=1" in repr_str
        assert "start_time=10.500" in repr_str
        assert "end_time=15.200" in repr_str
        assert "Hello world this is a long te..." in repr_str  # Truncated


class TestSubtitleFile:
    """Test SubtitleFile model."""
    
    @pytest.fixture
    def temp_subtitle_file(self, tmp_path):
        """Create a temporary subtitle file."""
        file_path = tmp_path / "test.srt"
        file_path.write_text("Dummy subtitle content")
        return file_path
    
    @pytest.fixture
    def sample_entries(self):
        """Create sample subtitle entries."""
        return [
            SubtitleEntry(1, 0.0, 5.0, "First subtitle"),
            SubtitleEntry(2, 5.0, 10.0, "Second subtitle"),
            SubtitleEntry(3, 10.0, 15.0, "Third subtitle with damn"),
            SubtitleEntry(4, 20.0, 25.0, "Fourth subtitle"),
        ]
    
    def test_create_subtitle_file(self, temp_subtitle_file):
        """Test creating a subtitle file."""
        sub_file = SubtitleFile(path=temp_subtitle_file)
        assert sub_file.path == temp_subtitle_file
        assert sub_file.entries == []
        assert sub_file.encoding == "utf-8"
        assert sub_file.language is None
    
    def test_validates_file_exists(self):
        """Test that file must exist."""
        with pytest.raises(FileNotFoundError):
            SubtitleFile(path=Path("/nonexistent/file.srt"))
    
    def test_with_entries(self, temp_subtitle_file, sample_entries):
        """Test subtitle file with entries."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        assert len(sub_file.entries) == 4
        assert sub_file.entry_count == 4
    
    def test_duration_property(self, temp_subtitle_file, sample_entries):
        """Test duration calculation."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        assert sub_file.duration == 25.0  # Max end time
    
    def test_duration_empty_file(self, temp_subtitle_file):
        """Test duration of empty file."""
        sub_file = SubtitleFile(path=temp_subtitle_file)
        assert sub_file.duration == 0.0
    
    def test_get_entries_in_range(self, temp_subtitle_file, sample_entries):
        """Test getting entries in time range."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        # Get entries from 3s to 12s
        entries = sub_file.get_entries_in_range(3.0, 12.0)
        assert len(entries) == 3  # Entries 1, 2, 3
        assert entries[0].index == 1
        assert entries[1].index == 2
        assert entries[2].index == 3
    
    def test_search_text_case_insensitive(self, temp_subtitle_file, sample_entries):
        """Test text search (case insensitive)."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        matches = sub_file.search_text("damn")
        assert len(matches) == 1
        assert matches[0].index == 3
        
        # Case insensitive
        matches = sub_file.search_text("DAMN")
        assert len(matches) == 1
    
    def test_search_text_case_sensitive(self, temp_subtitle_file, sample_entries):
        """Test text search (case sensitive)."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        matches = sub_file.search_text("damn", case_sensitive=True)
        assert len(matches) == 1
        
        matches = sub_file.search_text("DAMN", case_sensitive=True)
        assert len(matches) == 0
    
    def test_search_text_partial_match(self, temp_subtitle_file, sample_entries):
        """Test partial text matching."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        matches = sub_file.search_text("subtitle")
        assert len(matches) == 4  # All contain "subtitle"
    
    def test_get_entry_by_index(self, temp_subtitle_file, sample_entries):
        """Test getting entry by subtitle index."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        entry = sub_file.get_entry_by_index(3)
        assert entry is not None
        assert entry.index == 3
        assert "damn" in entry.text
        
        # Non-existent index
        entry = sub_file.get_entry_by_index(999)
        assert entry is None
    
    def test_get_entry_at_time(self, temp_subtitle_file, sample_entries):
        """Test getting entry at specific time."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        entry = sub_file.get_entry_at_time(7.5)
        assert entry is not None
        assert entry.index == 2
        
        # Time with no subtitle
        entry = sub_file.get_entry_at_time(17.5)
        assert entry is None
    
    def test_len(self, temp_subtitle_file, sample_entries):
        """Test __len__ method."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        assert len(sub_file) == 4
    
    def test_iter(self, temp_subtitle_file, sample_entries):
        """Test iteration over entries."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        indices = [entry.index for entry in sub_file]
        assert indices == [1, 2, 3, 4]
    
    def test_getitem(self, temp_subtitle_file, sample_entries):
        """Test indexing into entries."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        
        assert sub_file[0].index == 1
        assert sub_file[1].index == 2
        assert sub_file[-1].index == 4
    
    def test_str_representation(self, temp_subtitle_file, sample_entries):
        """Test string representation."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries
        )
        str_rep = str(sub_file)
        assert "test.srt" in str_rep
        assert "4 entries" in str_rep
    
    def test_repr_representation(self, temp_subtitle_file, sample_entries):
        """Test detailed representation."""
        sub_file = SubtitleFile(
            path=temp_subtitle_file,
            entries=sample_entries,
            language="en"
        )
        repr_str = repr(sub_file)
        assert "entries=4" in repr_str
        assert "encoding=utf-8" in repr_str
        assert "language=en" in repr_str
