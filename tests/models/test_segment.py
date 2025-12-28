"""
Unit tests for segment models.

Tests MuteSegment class and helper functions.
"""

import pytest
from cleanvid.models.segment import (
    MuteSegment,
    merge_overlapping_segments,
    add_padding_to_segments,
    create_ffmpeg_filter_chain,
)


class TestMuteSegment:
    """Test MuteSegment model."""
    
    def test_create_valid_segment(self):
        """Test creating a valid mute segment."""
        segment = MuteSegment(
            start_time=10.5,
            end_time=15.2,
            word="damn",
            confidence=0.95
        )
        assert segment.start_time == 10.5
        assert segment.end_time == 15.2
        assert segment.word == "damn"
        assert segment.confidence == 0.95
    
    def test_default_confidence(self):
        """Test default confidence is 1.0."""
        segment = MuteSegment(
            start_time=10.0,
            end_time=15.0,
            word="test"
        )
        assert segment.confidence == 1.0
    
    def test_duration_property(self):
        """Test duration calculation."""
        segment = MuteSegment(
            start_time=10.0,
            end_time=15.0,
            word="test"
        )
        assert segment.duration == 5.0
    
    def test_validates_positive_start_time(self):
        """Test start time must be non-negative."""
        with pytest.raises(ValueError, match="cannot be negative"):
            MuteSegment(
                start_time=-1.0,
                end_time=10.0,
                word="test"
            )
    
    def test_validates_end_time_after_start(self):
        """Test end time must be > start time."""
        with pytest.raises(ValueError, match="must be > start time"):
            MuteSegment(
                start_time=15.0,
                end_time=10.0,
                word="test"
            )
        
        with pytest.raises(ValueError, match="must be > start time"):
            MuteSegment(
                start_time=10.0,
                end_time=10.0,
                word="test"
            )
    
    def test_validates_confidence_range(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            MuteSegment(
                start_time=10.0,
                end_time=15.0,
                word="test",
                confidence=-0.1
            )
        
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            MuteSegment(
                start_time=10.0,
                end_time=15.0,
                word="test",
                confidence=1.1
            )
    
    def test_validates_non_empty_word(self):
        """Test word cannot be empty."""
        with pytest.raises(ValueError, match="cannot be empty"):
            MuteSegment(
                start_time=10.0,
                end_time=15.0,
                word=""
            )
        
        with pytest.raises(ValueError, match="cannot be empty"):
            MuteSegment(
                start_time=10.0,
                end_time=15.0,
                word="   "
            )
    
    def test_overlaps_with(self):
        """Test overlap detection."""
        seg1 = MuteSegment(10.0, 20.0, "first")
        seg2 = MuteSegment(15.0, 25.0, "second")
        seg3 = MuteSegment(25.0, 30.0, "third")
        
        assert seg1.overlaps_with(seg2) is True
        assert seg2.overlaps_with(seg1) is True
        assert seg1.overlaps_with(seg3) is False
        assert seg2.overlaps_with(seg3) is False
    
    def test_overlaps_with_touching_boundaries(self):
        """Test overlap with touching boundaries."""
        seg1 = MuteSegment(10.0, 20.0, "first")
        seg2 = MuteSegment(20.0, 30.0, "second")
        
        # Touching at boundary does not overlap
        assert seg1.overlaps_with(seg2) is False
    
    def test_contains_time(self):
        """Test time containment."""
        segment = MuteSegment(10.0, 20.0, "test")
        
        assert segment.contains_time(10.0) is True
        assert segment.contains_time(15.0) is True
        assert segment.contains_time(20.0) is True
        assert segment.contains_time(9.9) is False
        assert segment.contains_time(20.1) is False
    
    def test_is_adjacent_to(self):
        """Test adjacency detection."""
        seg1 = MuteSegment(10.0, 20.0, "first")
        seg2 = MuteSegment(20.0, 30.0, "second")
        seg3 = MuteSegment(20.05, 30.0, "third")
        seg4 = MuteSegment(25.0, 35.0, "fourth")
        
        # Exactly touching
        assert seg1.is_adjacent_to(seg2) is True
        assert seg2.is_adjacent_to(seg1) is True
        
        # Within tolerance
        assert seg1.is_adjacent_to(seg3, tolerance=0.1) is True
        
        # Beyond tolerance
        assert seg1.is_adjacent_to(seg3, tolerance=0.01) is False
        
        # Not adjacent
        assert seg1.is_adjacent_to(seg4) is False
    
    def test_merge_with(self):
        """Test merging segments."""
        seg1 = MuteSegment(10.0, 20.0, "first", confidence=0.9)
        seg2 = MuteSegment(15.0, 25.0, "second", confidence=0.8)
        
        merged = seg1.merge_with(seg2)
        
        assert merged.start_time == 10.0
        assert merged.end_time == 25.0
        assert merged.word == "first+second"
        assert merged.confidence == 0.8  # Min of the two
    
    def test_add_padding(self):
        """Test adding padding."""
        segment = MuteSegment(10.0, 15.0, "test")
        
        padded = segment.add_padding(before=0.5, after=1.0)
        
        assert padded.start_time == 9.5
        assert padded.end_time == 16.0
        assert padded.word == "test"
        assert padded.confidence == segment.confidence
    
    def test_add_padding_prevents_negative_start(self):
        """Test padding doesn't create negative start time."""
        segment = MuteSegment(0.2, 1.0, "test")
        
        padded = segment.add_padding(before=0.5, after=0.0)
        
        assert padded.start_time == 0.0  # Clamped to 0
        assert padded.end_time == 1.0
    
    def test_to_ffmpeg_filter(self):
        """Test FFmpeg filter generation."""
        segment = MuteSegment(10.5, 15.2, "test")
        
        filter_str = segment.to_ffmpeg_filter()
        
        assert filter_str == "volume=enable='between(t,10.500,15.200)':volume=0"
    
    def test_str_representation(self):
        """Test string representation."""
        segment = MuteSegment(10.5, 15.2, "damn")
        assert "10.50s-15.20s: 'damn'" in str(segment)
    
    def test_repr_representation(self):
        """Test detailed representation."""
        segment = MuteSegment(10.5, 15.2, "damn", confidence=0.95)
        repr_str = repr(segment)
        assert "start_time=10.500" in repr_str
        assert "end_time=15.200" in repr_str
        assert "word='damn'" in repr_str
        assert "confidence=0.95" in repr_str
    
    def test_equality(self):
        """Test equality comparison."""
        seg1 = MuteSegment(10.0, 15.0, "test")
        seg2 = MuteSegment(10.0, 15.0, "different")
        seg3 = MuteSegment(10.001, 15.0, "test")
        
        assert seg1 == seg2  # Same timing
        assert seg1 != seg3  # Different timing
        assert seg1 != "not a segment"
    
    def test_sorting(self):
        """Test segment sorting by start time."""
        seg1 = MuteSegment(20.0, 25.0, "third")
        seg2 = MuteSegment(10.0, 15.0, "first")
        seg3 = MuteSegment(15.0, 20.0, "second")
        
        sorted_segs = sorted([seg1, seg2, seg3])
        
        assert sorted_segs[0].word == "first"
        assert sorted_segs[1].word == "second"
        assert sorted_segs[2].word == "third"


class TestMergeOverlappingSegments:
    """Test merge_overlapping_segments function."""
    
    def test_empty_list(self):
        """Test merging empty list."""
        result = merge_overlapping_segments([])
        assert result == []
    
    def test_single_segment(self):
        """Test with single segment."""
        segment = MuteSegment(10.0, 15.0, "test")
        result = merge_overlapping_segments([segment])
        assert len(result) == 1
        assert result[0] == segment
    
    def test_non_overlapping_segments(self):
        """Test non-overlapping segments remain separate."""
        seg1 = MuteSegment(10.0, 15.0, "first")
        seg2 = MuteSegment(20.0, 25.0, "second")
        seg3 = MuteSegment(30.0, 35.0, "third")
        
        result = merge_overlapping_segments([seg3, seg1, seg2])  # Unsorted
        
        assert len(result) == 3
        assert result[0].word == "first"
        assert result[1].word == "second"
        assert result[2].word == "third"
    
    def test_overlapping_segments(self):
        """Test overlapping segments get merged."""
        seg1 = MuteSegment(10.0, 20.0, "first")
        seg2 = MuteSegment(15.0, 25.0, "second")
        seg3 = MuteSegment(22.0, 30.0, "third")
        
        result = merge_overlapping_segments([seg1, seg2, seg3])
        
        assert len(result) == 1
        assert result[0].start_time == 10.0
        assert result[0].end_time == 30.0
    
    def test_adjacent_segments(self):
        """Test adjacent segments get merged."""
        seg1 = MuteSegment(10.0, 20.0, "first")
        seg2 = MuteSegment(20.0, 30.0, "second")
        
        result = merge_overlapping_segments([seg1, seg2])
        
        assert len(result) == 1
        assert result[0].start_time == 10.0
        assert result[0].end_time == 30.0
    
    def test_mixed_segments(self):
        """Test mix of overlapping and separate segments."""
        seg1 = MuteSegment(10.0, 20.0, "first")
        seg2 = MuteSegment(15.0, 25.0, "second")
        seg3 = MuteSegment(40.0, 45.0, "third")
        seg4 = MuteSegment(50.0, 55.0, "fourth")
        seg5 = MuteSegment(52.0, 60.0, "fifth")
        
        result = merge_overlapping_segments([seg1, seg2, seg3, seg4, seg5])
        
        assert len(result) == 3
        assert result[0].start_time == 10.0  # Merged 1+2
        assert result[0].end_time == 25.0
        assert result[1].start_time == 40.0  # Separate
        assert result[1].end_time == 45.0
        assert result[2].start_time == 50.0  # Merged 4+5
        assert result[2].end_time == 60.0


class TestAddPaddingToSegments:
    """Test add_padding_to_segments function."""
    
    def test_empty_list(self):
        """Test adding padding to empty list."""
        result = add_padding_to_segments([])
        assert result == []
    
    def test_add_padding_single_segment(self):
        """Test adding padding to single segment."""
        segment = MuteSegment(10.0, 15.0, "test")
        
        result = add_padding_to_segments([segment], before_ms=500, after_ms=1000)
        
        assert len(result) == 1
        assert result[0].start_time == 9.5
        assert result[0].end_time == 16.0
    
    def test_add_padding_merges_overlapping(self):
        """Test padding that causes overlap triggers merge."""
        seg1 = MuteSegment(10.0, 11.0, "first")
        seg2 = MuteSegment(11.5, 12.5, "second")
        
        # With 500ms padding, these will overlap
        result = add_padding_to_segments([seg1, seg2], before_ms=500, after_ms=500)
        
        assert len(result) == 1  # Merged
        assert result[0].start_time == 9.5
        assert result[0].end_time == 13.0
    
    def test_add_padding_separate_segments(self):
        """Test padding that doesn't cause overlap."""
        seg1 = MuteSegment(10.0, 11.0, "first")
        seg2 = MuteSegment(20.0, 21.0, "second")
        
        result = add_padding_to_segments([seg1, seg2], before_ms=500, after_ms=500)
        
        assert len(result) == 2  # Remain separate
        assert result[0].start_time == 9.5
        assert result[0].end_time == 11.5
        assert result[1].start_time == 19.5
        assert result[1].end_time == 21.5
    
    def test_zero_padding(self):
        """Test with zero padding."""
        segment = MuteSegment(10.0, 15.0, "test")
        
        result = add_padding_to_segments([segment], before_ms=0, after_ms=0)
        
        assert len(result) == 1
        assert result[0].start_time == 10.0
        assert result[0].end_time == 15.0


class TestCreateFfmpegFilterChain:
    """Test create_ffmpeg_filter_chain function."""
    
    def test_empty_list(self):
        """Test with empty segment list."""
        result = create_ffmpeg_filter_chain([])
        assert result == ""
    
    def test_single_segment(self):
        """Test with single segment."""
        segment = MuteSegment(10.0, 15.0, "test")
        
        result = create_ffmpeg_filter_chain([segment])
        
        assert result == "volume=enable='between(t,10.000,15.000)':volume=0"
    
    def test_multiple_segments(self):
        """Test with multiple segments."""
        seg1 = MuteSegment(10.0, 15.0, "first")
        seg2 = MuteSegment(20.0, 25.0, "second")
        seg3 = MuteSegment(30.0, 35.0, "third")
        
        result = create_ffmpeg_filter_chain([seg1, seg2, seg3])
        
        filters = result.split(",")
        assert len(filters) == 3
        assert "between(t,10.000,15.000)" in filters[0]
        assert "between(t,20.000,25.000)" in filters[1]
        assert "between(t,30.000,35.000)" in filters[2]
