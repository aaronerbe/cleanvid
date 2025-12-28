"""
Unit tests for SubtitleManager service.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cleanvid.services.subtitle_manager import SubtitleManager
from cleanvid.models.config import OpenSubtitlesConfig
from cleanvid.models.subtitle import SubtitleFile, SubtitleEntry


class TestSubtitleManager:
    """Test SubtitleManager service."""
    
    def test_init_default(self):
        """Test initialization with defaults."""
        manager = SubtitleManager()
        
        assert manager.config is not None
        assert manager.config.enabled is False
    
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = OpenSubtitlesConfig(
            enabled=True,
            language='es',
            username='testuser'
        )
        manager = SubtitleManager(config=config)
        
        assert manager.config.enabled is True
        assert manager.config.language == 'es'
        assert manager.config.username == 'testuser'
    
    def test_time_to_seconds(self):
        """Test time conversion."""
        manager = SubtitleManager()
        
        # Mock pysrt time object
        time_obj = Mock()
        time_obj.hours = 1
        time_obj.minutes = 30
        time_obj.seconds = 45
        time_obj.milliseconds = 500
        
        seconds = manager._time_to_seconds(time_obj)
        
        # 1h + 30m + 45s + 0.5s = 5445.5s
        assert seconds == 5445.5
    
    def test_time_to_seconds_zero(self):
        """Test zero time conversion."""
        manager = SubtitleManager()
        
        time_obj = Mock()
        time_obj.hours = 0
        time_obj.minutes = 0
        time_obj.seconds = 0
        time_obj.milliseconds = 0
        
        seconds = manager._time_to_seconds(time_obj)
        assert seconds == 0.0


class TestSubtitleManagerParsing:
    """Test SRT parsing functionality."""
    
    def test_parse_srt_success(self, tmp_path):
        """Test successful SRT parsing."""
        srt_content = """1
00:00:10,500 --> 00:00:15,200
First subtitle

2
00:00:20,000 --> 00:00:25,500
Second subtitle with profanity

3
00:00:30,100 --> 00:00:35,800
Third subtitle
"""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        
        manager = SubtitleManager()
        subtitle_file = manager.parse_srt(srt_file)
        
        assert isinstance(subtitle_file, SubtitleFile)
        assert len(subtitle_file.entries) == 3
        assert subtitle_file.path == srt_file
        assert subtitle_file.encoding == 'utf-8'
    
    def test_parse_srt_timing_accuracy(self, tmp_path):
        """Test SRT timing is converted accurately."""
        srt_content = """1
00:00:10,500 --> 00:00:15,200
Test subtitle
"""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        
        manager = SubtitleManager()
        subtitle_file = manager.parse_srt(srt_file)
        
        entry = subtitle_file.entries[0]
        assert entry.start_time == 10.5
        assert entry.end_time == 15.2
        assert entry.text == "Test subtitle"
        assert entry.index == 1
    
    def test_parse_srt_missing_file(self):
        """Test parsing non-existent file raises error."""
        manager = SubtitleManager()
        
        with pytest.raises(FileNotFoundError):
            manager.parse_srt(Path("/nonexistent/file.srt"))
    
    def test_parse_srt_invalid_format(self, tmp_path):
        """Test parsing invalid SRT raises error."""
        invalid_srt = tmp_path / "invalid.srt"
        invalid_srt.write_text("This is not a valid SRT file")
        
        manager = SubtitleManager()
        
        with pytest.raises(ValueError, match="Failed to parse"):
            manager.parse_srt(invalid_srt)
    
    def test_parse_srt_empty_file(self, tmp_path):
        """Test parsing empty SRT file."""
        empty_srt = tmp_path / "empty.srt"
        empty_srt.write_text("")
        
        manager = SubtitleManager()
        subtitle_file = manager.parse_srt(empty_srt)
        
        assert len(subtitle_file.entries) == 0
    
    def test_parse_srt_multiple_lines(self, tmp_path):
        """Test parsing subtitle with multiple text lines."""
        srt_content = """1
00:00:10,000 --> 00:00:15,000
Line 1
Line 2
Line 3
"""
        srt_file = tmp_path / "multiline.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        
        manager = SubtitleManager()
        subtitle_file = manager.parse_srt(srt_file)
        
        assert len(subtitle_file.entries) == 1
        # pysrt joins lines with \n
        assert "Line 1" in subtitle_file.entries[0].text
        assert "Line 2" in subtitle_file.entries[0].text


class TestSubtitleManagerDiscovery:
    """Test subtitle file discovery."""
    
    def test_find_subtitle_for_video_srt(self, tmp_path):
        """Test finding .srt subtitle."""
        video_file = tmp_path / "movie.mkv"
        subtitle_file = tmp_path / "movie.srt"
        
        video_file.write_text("fake video")
        subtitle_file.write_text("fake subtitle")
        
        manager = SubtitleManager()
        found = manager.find_subtitle_for_video(video_file)
        
        assert found == subtitle_file
    
    def test_find_subtitle_for_video_multiple_formats(self, tmp_path):
        """Test finding subtitle with different extension."""
        video_file = tmp_path / "movie.mp4"
        subtitle_file = tmp_path / "movie.sub"
        
        video_file.write_text("fake video")
        subtitle_file.write_text("fake subtitle")
        
        manager = SubtitleManager()
        found = manager.find_subtitle_for_video(video_file)
        
        assert found == subtitle_file
    
    def test_find_subtitle_for_video_priority(self, tmp_path):
        """Test .srt is preferred over other formats."""
        video_file = tmp_path / "movie.mkv"
        srt_file = tmp_path / "movie.srt"
        sub_file = tmp_path / "movie.sub"
        
        video_file.write_text("fake video")
        srt_file.write_text("srt subtitle")
        sub_file.write_text("sub subtitle")
        
        manager = SubtitleManager()
        found = manager.find_subtitle_for_video(video_file)
        
        # .srt should be found first (higher priority)
        assert found == srt_file
    
    def test_find_subtitle_for_video_not_found(self, tmp_path):
        """Test returns None when subtitle not found."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        manager = SubtitleManager()
        found = manager.find_subtitle_for_video(video_file)
        
        assert found is None


class TestSubtitleManagerDownload:
    """Test subtitle downloading."""
    
    def test_download_disabled_raises_error(self, tmp_path):
        """Test downloading raises error when disabled."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        config = OpenSubtitlesConfig(enabled=False)
        manager = SubtitleManager(config=config)
        
        with pytest.raises(RuntimeError, match="disabled"):
            manager.download_subtitles(video_file)
    
    def test_download_missing_video_raises_error(self):
        """Test downloading raises error for missing video."""
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        with pytest.raises(FileNotFoundError):
            manager.download_subtitles(Path("/nonexistent/movie.mkv"))
    
    @patch('cleanvid.services.subtitle_manager.download_best_subtitles')
    @patch('cleanvid.services.subtitle_manager.save_subtitles')
    @patch('cleanvid.services.subtitle_manager.Video')
    def test_download_success(self, mock_video, mock_save, mock_download, tmp_path):
        """Test successful subtitle download."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        # Mock subliminal components
        mock_video_obj = Mock()
        mock_video.fromname.return_value = mock_video_obj
        
        mock_subtitle = Mock()
        mock_download.return_value = {mock_video_obj: {mock_subtitle}}
        
        # Create the subtitle file that save_subtitles would create
        subtitle_file = tmp_path / "movie.srt"
        
        def create_subtitle(*args, **kwargs):
            subtitle_file.write_text("Downloaded subtitle")
        
        mock_save.side_effect = create_subtitle
        
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        result = manager.download_subtitles(video_file)
        
        assert result == subtitle_file
        mock_download.assert_called_once()
        mock_save.assert_called_once()
    
    @patch('cleanvid.services.subtitle_manager.download_best_subtitles')
    @patch('cleanvid.services.subtitle_manager.Video')
    def test_download_no_subtitles_found(self, mock_video, mock_download, tmp_path):
        """Test when no subtitles are found."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        mock_video_obj = Mock()
        mock_video.fromname.return_value = mock_video_obj
        
        # Return empty subtitles
        mock_download.return_value = {}
        
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        result = manager.download_subtitles(video_file)
        
        assert result is None


class TestSubtitleManagerGetOrDownload:
    """Test get_or_download_subtitle method."""
    
    def test_get_or_download_existing(self, tmp_path):
        """Test returns existing subtitle without downloading."""
        video_file = tmp_path / "movie.mkv"
        subtitle_file = tmp_path / "movie.srt"
        
        video_file.write_text("fake video")
        subtitle_file.write_text("existing subtitle")
        
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        result = manager.get_or_download_subtitle(video_file)
        
        assert result == subtitle_file
    
    @patch('cleanvid.services.subtitle_manager.SubtitleManager.download_subtitles')
    def test_get_or_download_downloads_when_missing(self, mock_download, tmp_path):
        """Test downloads when subtitle missing and enabled."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        downloaded_sub = tmp_path / "movie.srt"
        mock_download.return_value = downloaded_sub
        
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        result = manager.get_or_download_subtitle(video_file)
        
        mock_download.assert_called_once_with(video_file, 'en')
        assert result == downloaded_sub
    
    def test_get_or_download_disabled_returns_none(self, tmp_path):
        """Test returns None when subtitle missing and download disabled."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        config = OpenSubtitlesConfig(enabled=False)
        manager = SubtitleManager(config=config)
        
        result = manager.get_or_download_subtitle(video_file)
        
        assert result is None


class TestSubtitleManagerLoadSubtitleFile:
    """Test load_subtitle_file method."""
    
    def test_load_existing_subtitle(self, tmp_path):
        """Test loading existing subtitle file."""
        video_file = tmp_path / "movie.mkv"
        subtitle_file = tmp_path / "movie.srt"
        
        video_file.write_text("fake video")
        srt_content = """1
00:00:10,000 --> 00:00:15,000
Test subtitle
"""
        subtitle_file.write_text(srt_content)
        
        manager = SubtitleManager()
        result = manager.load_subtitle_file(video_file, auto_download=False)
        
        assert result is not None
        assert isinstance(result, SubtitleFile)
        assert len(result.entries) == 1
    
    def test_load_no_subtitle_auto_download_false(self, tmp_path):
        """Test returns None when subtitle missing and auto_download=False."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        manager = SubtitleManager()
        result = manager.load_subtitle_file(video_file, auto_download=False)
        
        assert result is None
    
    @patch('cleanvid.services.subtitle_manager.SubtitleManager.download_subtitles')
    def test_load_with_auto_download(self, mock_download, tmp_path):
        """Test auto-downloads when subtitle missing."""
        video_file = tmp_path / "movie.mkv"
        video_file.write_text("fake video")
        
        # Create subtitle file that download will "create"
        subtitle_file = tmp_path / "movie.srt"
        srt_content = """1
00:00:10,000 --> 00:00:15,000
Downloaded subtitle
"""
        
        def create_subtitle(*args, **kwargs):
            subtitle_file.write_text(srt_content)
            return subtitle_file
        
        mock_download.side_effect = create_subtitle
        
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        result = manager.load_subtitle_file(video_file, auto_download=True)
        
        assert result is not None
        assert isinstance(result, SubtitleFile)
        mock_download.assert_called_once()


class TestSubtitleManagerValidation:
    """Test subtitle validation."""
    
    def test_validate_valid_file(self, tmp_path):
        """Test validating valid subtitle file."""
        srt_content = """1
00:00:10,000 --> 00:00:15,000
Valid subtitle
"""
        srt_file = tmp_path / "valid.srt"
        srt_file.write_text(srt_content)
        
        manager = SubtitleManager()
        is_valid, errors = manager.validate_subtitle_file(srt_file)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_file(self):
        """Test validating non-existent file."""
        manager = SubtitleManager()
        is_valid, errors = manager.validate_subtitle_file(Path("/nonexistent.srt"))
        
        assert is_valid is False
        assert len(errors) > 0
        assert "not found" in errors[0]
    
    def test_validate_empty_file(self, tmp_path):
        """Test validating empty subtitle file."""
        empty_srt = tmp_path / "empty.srt"
        empty_srt.write_text("")
        
        manager = SubtitleManager()
        is_valid, errors = manager.validate_subtitle_file(empty_srt)
        
        assert is_valid is False
        assert any("empty" in err.lower() for err in errors)
    
    def test_validate_unsupported_format(self, tmp_path):
        """Test validating unsupported format."""
        txt_file = tmp_path / "subtitle.txt"
        txt_file.write_text("Not a subtitle")
        
        manager = SubtitleManager()
        is_valid, errors = manager.validate_subtitle_file(txt_file)
        
        assert is_valid is False
        assert any("Unsupported" in err for err in errors)


class TestSubtitleManagerStatistics:
    """Test subtitle statistics."""
    
    def test_get_stats_normal_file(self, tmp_path):
        """Test statistics for normal subtitle file."""
        srt_content = """1
00:00:10,000 --> 00:00:15,000
First subtitle here

2
00:00:20,000 --> 00:00:25,000
Second subtitle text
"""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content)
        
        manager = SubtitleManager()
        subtitle_file = manager.parse_srt(srt_file)
        stats = manager.get_subtitle_stats(subtitle_file)
        
        assert stats['total_entries'] == 2
        assert stats['total_duration'] == 25.0
        assert stats['first_entry_time'] == 10.0
        assert stats['last_entry_time'] == 25.0
        assert stats['total_text_length'] > 0
    
    def test_get_stats_empty_file(self, tmp_path):
        """Test statistics for empty subtitle file."""
        empty_srt = tmp_path / "empty.srt"
        empty_srt.write_text("")
        
        manager = SubtitleManager()
        subtitle_file = manager.parse_srt(empty_srt)
        stats = manager.get_subtitle_stats(subtitle_file)
        
        assert stats['total_entries'] == 0
        assert stats['total_duration'] == 0.0
        assert stats['average_entry_duration'] == 0.0


class TestSubtitleManagerRepresentation:
    """Test string representations."""
    
    def test_str_disabled(self):
        """Test string representation when disabled."""
        config = OpenSubtitlesConfig(enabled=False)
        manager = SubtitleManager(config=config)
        
        str_rep = str(manager)
        
        assert "disabled" in str_rep
    
    def test_str_enabled(self):
        """Test string representation when enabled."""
        config = OpenSubtitlesConfig(enabled=True)
        manager = SubtitleManager(config=config)
        
        str_rep = str(manager)
        
        assert "enabled" in str_rep
    
    def test_repr(self):
        """Test detailed representation."""
        config = OpenSubtitlesConfig(enabled=True, language='es')
        manager = SubtitleManager(config=config)
        
        repr_str = repr(manager)
        
        assert "SubtitleManager" in repr_str
        assert "opensubtitles_enabled=True" in repr_str
        assert "language=es" in repr_str
