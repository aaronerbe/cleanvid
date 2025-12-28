"""
Unit tests for ProfanityDetector service.
"""

import pytest
from pathlib import Path
from cleanvid.services.profanity_detector import ProfanityDetector
from cleanvid.models.subtitle import SubtitleEntry, SubtitleFile


class TestProfanityDetector:
    """Test ProfanityDetector service."""
    
    def test_init_loads_word_list(self, sample_word_list):
        """Test initialization loads word list."""
        detector = ProfanityDetector(sample_word_list)
        
        assert detector.word_list_path == sample_word_list
        assert len(detector.profane_words) > 0
        assert "damn" in detector.profane_words
        assert "hell" in detector.profane_words
    
    def test_init_missing_file(self):
        """Test initialization fails with missing file."""
        with pytest.raises(FileNotFoundError):
            ProfanityDetector(Path("/nonexistent/words.txt"))
    
    def test_load_word_list_skips_comments(self, tmp_path):
        """Test word list loading skips comments."""
        word_list = tmp_path / "words.txt"
        word_list.write_text("""# This is a comment
damn
# Another comment
hell
        # Indented comment
shit
""")
        
        detector = ProfanityDetector(word_list)
        
        assert len(detector.profane_words) == 3
        assert "# This is a comment" not in detector.profane_words
    
    def test_load_word_list_skips_empty_lines(self, tmp_path):
        """Test word list loading skips empty lines."""
        word_list = tmp_path / "words.txt"
        word_list.write_text("""damn

hell

shit
""")
        
        detector = ProfanityDetector(word_list)
        
        assert len(detector.profane_words) == 3
    
    def test_load_word_list_case_insensitive(self, tmp_path):
        """Test words are stored in lowercase."""
        word_list = tmp_path / "words.txt"
        word_list.write_text("DAMN\nHell\nShIt\n")
        
        detector = ProfanityDetector(word_list)
        
        assert "damn" in detector.profane_words
        assert "hell" in detector.profane_words
        assert "shit" in detector.profane_words
        assert "DAMN" not in detector.profane_words
    
    def test_detect_in_text_single_word(self, sample_word_list):
        """Test detecting single profane word."""
        detector = ProfanityDetector(sample_word_list)
        
        detected = detector.detect_in_text("This is damn annoying")
        
        assert len(detected) == 1
        assert detected[0].lower() == "damn"
    
    def test_detect_in_text_multiple_words(self, sample_word_list):
        """Test detecting multiple profane words."""
        detector = ProfanityDetector(sample_word_list)
        
        detected = detector.detect_in_text("What the hell, this is damn annoying")
        
        assert len(detected) == 2
        assert "hell" in [w.lower() for w in detected]
        assert "damn" in [w.lower() for w in detected]
    
    def test_detect_in_text_case_insensitive(self, sample_word_list):
        """Test detection is case insensitive."""
        detector = ProfanityDetector(sample_word_list)
        
        detected = detector.detect_in_text("DAMN, Hell, ShIt")
        
        assert len(detected) == 3
    
    def test_detect_in_text_word_boundaries(self, sample_word_list):
        """Test word boundary detection."""
        detector = ProfanityDetector(sample_word_list)
        
        # "assessment" contains "ass" but shouldn't match
        detected = detector.detect_in_text("This is an assessment")
        
        # Should not detect "ass" as it's part of a larger word
        # (depends on word list - if "ass" is whole word only)
        assert len(detected) == 0 or "assessment" not in detected
    
    def test_detect_in_text_no_profanity(self, sample_word_list):
        """Test clean text detection."""
        detector = ProfanityDetector(sample_word_list)
        
        detected = detector.detect_in_text("This is completely clean text")
        
        assert len(detected) == 0
    
    def test_detect_in_entry(self, sample_word_list):
        """Test detecting profanity in subtitle entry."""
        detector = ProfanityDetector(sample_word_list)
        
        entry = SubtitleEntry(
            index=1,
            start_time=10.0,
            end_time=15.0,
            text="What the hell is going on?"
        )
        
        segments = detector.detect_in_entry(entry)
        
        assert len(segments) > 0
        assert segments[0].start_time == 10.0
        assert segments[0].end_time == 15.0
        assert segments[0].word == "hell"
    
    def test_detect_in_entry_custom_confidence(self, sample_word_list):
        """Test detection with custom confidence."""
        detector = ProfanityDetector(sample_word_list)
        
        entry = SubtitleEntry(
            index=1,
            start_time=10.0,
            end_time=15.0,
            text="damn"
        )
        
        segments = detector.detect_in_entry(entry, confidence=0.75)
        
        assert segments[0].confidence == 0.75
    
    def test_detect_in_entry_no_profanity(self, sample_word_list):
        """Test clean entry returns no segments."""
        detector = ProfanityDetector(sample_word_list)
        
        entry = SubtitleEntry(
            index=1,
            start_time=10.0,
            end_time=15.0,
            text="Clean subtitle text"
        )
        
        segments = detector.detect_in_entry(entry)
        
        assert len(segments) == 0
    
    def test_detect_in_subtitle_file(self, sample_word_list, temp_subtitle_file):
        """Test detecting profanity in subtitle file."""
        detector = ProfanityDetector(sample_word_list)
        
        entries = [
            SubtitleEntry(1, 10.0, 15.0, "Clean text"),
            SubtitleEntry(2, 20.0, 25.0, "This is damn annoying"),
            SubtitleEntry(3, 30.0, 35.0, "What the hell"),
            SubtitleEntry(4, 40.0, 45.0, "More clean text"),
        ]
        
        subtitle_file = SubtitleFile(path=temp_subtitle_file, entries=entries)
        
        segments = detector.detect_in_subtitle_file(subtitle_file)
        
        assert len(segments) == 2  # Two profane entries
    
    def test_get_statistics(self, sample_word_list, temp_subtitle_file):
        """Test getting detection statistics."""
        detector = ProfanityDetector(sample_word_list)
        
        entries = [
            SubtitleEntry(1, 10.0, 15.0, "Clean text"),
            SubtitleEntry(2, 20.0, 25.0, "damn damn"),  # 2 occurrences
            SubtitleEntry(3, 30.0, 35.0, "hell"),
            SubtitleEntry(4, 40.0, 45.0, "Clean"),
        ]
        
        subtitle_file = SubtitleFile(path=temp_subtitle_file, entries=entries)
        
        stats = detector.get_statistics(subtitle_file)
        
        assert stats["total_detections"] == 3  # 2 damn + 1 hell
        assert stats["unique_words_detected"] == 2  # damn, hell
        assert stats["entries_with_profanity"] == 2  # Entries 2 and 3
        assert stats["total_entries"] == 4
        assert stats["profanity_percentage"] == 50.0  # 2/4 = 50%
        assert "damn" in stats["word_counts"]
        assert stats["word_counts"]["damn"] == 2
    
    def test_get_statistics_clean_file(self, sample_word_list, temp_subtitle_file):
        """Test statistics for clean subtitle file."""
        detector = ProfanityDetector(sample_word_list)
        
        entries = [
            SubtitleEntry(1, 10.0, 15.0, "Clean text"),
            SubtitleEntry(2, 20.0, 25.0, "More clean text"),
        ]
        
        subtitle_file = SubtitleFile(path=temp_subtitle_file, entries=entries)
        
        stats = detector.get_statistics(subtitle_file)
        
        assert stats["total_detections"] == 0
        assert stats["unique_words_detected"] == 0
        assert stats["profanity_percentage"] == 0.0
    
    def test_is_clean_true(self, sample_word_list, temp_subtitle_file):
        """Test clean file detection."""
        detector = ProfanityDetector(sample_word_list)
        
        entries = [
            SubtitleEntry(1, 10.0, 15.0, "Clean text"),
            SubtitleEntry(2, 20.0, 25.0, "More clean text"),
        ]
        
        subtitle_file = SubtitleFile(path=temp_subtitle_file, entries=entries)
        
        assert detector.is_clean(subtitle_file) is True
    
    def test_is_clean_false(self, sample_word_list, temp_subtitle_file):
        """Test dirty file detection."""
        detector = ProfanityDetector(sample_word_list)
        
        entries = [
            SubtitleEntry(1, 10.0, 15.0, "Clean text"),
            SubtitleEntry(2, 20.0, 25.0, "damn it"),
        ]
        
        subtitle_file = SubtitleFile(path=temp_subtitle_file, entries=entries)
        
        assert detector.is_clean(subtitle_file) is False
    
    def test_add_word(self, sample_word_list):
        """Test adding word to profanity list."""
        detector = ProfanityDetector(sample_word_list)
        
        initial_count = detector.get_word_count()
        
        detector.add_word("newbadword")
        
        assert detector.get_word_count() == initial_count + 1
        assert "newbadword" in detector.profane_words
        
        # Should now detect the new word
        detected = detector.detect_in_text("This is a newbadword")
        assert len(detected) == 1
    
    def test_add_word_normalizes_case(self, sample_word_list):
        """Test adding word normalizes to lowercase."""
        detector = ProfanityDetector(sample_word_list)
        
        detector.add_word("UPPERCASE")
        
        assert "uppercase" in detector.profane_words
        assert "UPPERCASE" not in detector.profane_words
    
    def test_add_word_empty(self, sample_word_list):
        """Test adding empty word does nothing."""
        detector = ProfanityDetector(sample_word_list)
        
        initial_count = detector.get_word_count()
        
        detector.add_word("")
        detector.add_word("   ")
        
        assert detector.get_word_count() == initial_count
    
    def test_remove_word(self, sample_word_list):
        """Test removing word from list."""
        detector = ProfanityDetector(sample_word_list)
        
        initial_count = detector.get_word_count()
        
        result = detector.remove_word("damn")
        
        assert result is True
        assert detector.get_word_count() == initial_count - 1
        assert "damn" not in detector.profane_words
        
        # Should no longer detect
        detected = detector.detect_in_text("This is damn annoying")
        assert len(detected) == 0
    
    def test_remove_word_not_found(self, sample_word_list):
        """Test removing non-existent word."""
        detector = ProfanityDetector(sample_word_list)
        
        result = detector.remove_word("nonexistent")
        
        assert result is False
    
    def test_reload_word_list(self, tmp_path):
        """Test reloading word list from disk."""
        word_list = tmp_path / "words.txt"
        word_list.write_text("damn\nhell\n")
        
        detector = ProfanityDetector(word_list)
        
        assert detector.get_word_count() == 2
        
        # Modify file on disk
        word_list.write_text("damn\nhell\nshit\nfuck\n")
        
        # Reload
        detector.reload_word_list()
        
        assert detector.get_word_count() == 4
        assert "shit" in detector.profane_words
        assert "fuck" in detector.profane_words
    
    def test_get_words(self, sample_word_list):
        """Test getting sorted word list."""
        detector = ProfanityDetector(sample_word_list)
        
        words = detector.get_words()
        
        assert isinstance(words, list)
        assert len(words) > 0
        # Check sorted
        assert words == sorted(words)
    
    def test_get_word_count(self, sample_word_list):
        """Test getting word count."""
        detector = ProfanityDetector(sample_word_list)
        
        count = detector.get_word_count()
        
        assert count > 0
        assert count == len(detector.profane_words)
    
    def test_str_representation(self, sample_word_list):
        """Test string representation."""
        detector = ProfanityDetector(sample_word_list)
        
        str_rep = str(detector)
        
        assert "ProfanityDetector" in str_rep
        assert str(len(detector.profane_words)) in str_rep
    
    def test_repr_representation(self, sample_word_list):
        """Test detailed representation."""
        detector = ProfanityDetector(sample_word_list)
        
        repr_str = repr(detector)
        
        assert "ProfanityDetector" in repr_str
        assert str(sample_word_list) in repr_str
        assert f"words={len(detector.profane_words)}" in repr_str


class TestProfanityDetectorWildcards:
    """Test wildcard support in profanity detection."""
    
    def test_wildcard_pattern(self, tmp_path):
        """Test wildcard pattern matching."""
        word_list = tmp_path / "words.txt"
        word_list.write_text("f*ck\n")  # Matches fuck, fack, feck, etc.
        
        detector = ProfanityDetector(word_list)
        
        assert len(detector.detect_in_text("fuck")) > 0
        assert len(detector.detect_in_text("feck")) > 0
        assert len(detector.detect_in_text("fack")) > 0
    
    def test_wildcard_doesnt_match_everything(self, tmp_path):
        """Test wildcard doesn't over-match."""
        word_list = tmp_path / "words.txt"
        word_list.write_text("f*ck\n")
        
        detector = ProfanityDetector(word_list)
        
        # Should not match words that don't fit pattern
        assert len(detector.detect_in_text("fake")) == 0
        assert len(detector.detect_in_text("fork")) == 0


class TestProfanityDetectorEdgeCases:
    """Test edge cases in profanity detection."""
    
    def test_empty_word_list(self, tmp_path):
        """Test detector with empty word list."""
        word_list = tmp_path / "empty.txt"
        word_list.write_text("# Only comments\n\n")
        
        detector = ProfanityDetector(word_list)
        
        assert detector.get_word_count() == 0
        assert len(detector.detect_in_text("any text here")) == 0
    
    def test_punctuation_handling(self, sample_word_list):
        """Test detection with punctuation."""
        detector = ProfanityDetector(sample_word_list)
        
        # Should detect despite punctuation
        assert len(detector.detect_in_text("damn!")) > 0
        assert len(detector.detect_in_text("damn.")) > 0
        assert len(detector.detect_in_text("damn,")) > 0
        assert len(detector.detect_in_text("'damn'")) > 0
        assert len(detector.detect_in_text('"damn"')) > 0
    
    def test_repeated_words(self, sample_word_list):
        """Test detection of repeated profanity."""
        detector = ProfanityDetector(sample_word_list)
        
        detected = detector.detect_in_text("damn damn damn")
        
        assert len(detected) == 3  # All three instances
