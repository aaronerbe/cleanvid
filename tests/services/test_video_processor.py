"""
Unit tests for VideoProcessor service.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from cleanvid.services.video_processor import VideoProcessor
from cleanvid.services.subtitle_manager import SubtitleManager
from cleanvid.services.profanity_detector import ProfanityDetector
from cleanvid.models.config import FFmpegConfig, OpenSubtitlesConfig
from cleanvid.models.processing import VideoMetadata, ProcessingResult, ProcessingStatus
from cleanvid.models.subtitle import SubtitleFile, SubtitleEntry
from cleanvid.models.segment import MuteSegment
from cleanvid.utils.ffmpeg_wrapper import FFmpegWrapper, FFprobeResult


@pytest.fixture
def mock_subtitle_manager():
    """Create mock SubtitleManager."""
    return Mock(spec=SubtitleManager)


@pytest.fixture
def mock_profanity_detector(sample_word_list):
    """Create real ProfanityDetector with sample word list."""
    return ProfanityDetector(sample_word_list)


@pytest.fixture
def mock_ffmpeg_wrapper():
    """Create mock FFmpegWrapper."""
    wrapper = Mock(spec=FFmpegWrapper)
    wrapper.check_available.return_value = (True, "ffmpeg version 4.4.1")
    return wrapper


@pytest.fixture
def video_processor(mock_subtitle_manager, mock_profanity_detector, mock_ffmpeg_wrapper):
    """Create VideoProcessor with mocks."""
    config = FFmpegConfig()
    return VideoProcessor(
        subtitle_manager=mock_subtitle_manager,
        profanity_detector=mock_profanity_detector,
        ffmpeg_config=config,
        ffmpeg_wrapper=mock_ffmpeg_wrapper
    )


class TestVideoProcessor:
    """Test VideoProcessor service."""
    
    def test_init(self, mock_subtitle_manager, mock_profanity_detector):
        """Test initialization."""
        config = FFmpegConfig()
        processor = VideoProcessor(
            subtitle_manager=mock_subtitle_manager,
            profanity_detector=mock_profanity_detector,
            ffmpeg_config=config
        )
        
        assert processor.subtitle_manager is mock_subtitle_manager
        assert processor.profanity_detector is mock_profanity_detector
        assert processor.ffmpeg_config is config
        assert processor.ffmpeg is not None
    
    def test_extract_metadata(self, video_processor, mock_ffmpeg_wrapper, tmp_path):
        """Test metadata extraction."""
        video_file = tmp_path / "test.mkv"
        video_file.write_text("fake video")
        
        # Mock ffprobe result
        probe_result = FFprobeResult(
            path=video_file,
            format="matroska",
            duration=7200.5,
            size=1073741824,
            bit_rate=1000000,
            video_codec="h264",
            audio_codec="aac",
            width=1920,
            height=1080
        )
        mock_ffmpeg_wrapper.probe.return_value = probe_result
        
        # Mock subtitle search
        video_processor.subtitle_manager.find_subtitle_for_video.return_value = None
        
        metadata = video_processor.extract_metadata(video_file)
        
        assert isinstance(metadata, VideoMetadata)
        assert metadata.path == video_file
        assert metadata.duration_seconds == 7200.5
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.has_subtitles is False
    
    def test_process_video_success(self, video_processor, tmp_path):
        """Test successful video processing."""
        video_file = tmp_path / "input.mkv"
        output_file = tmp_path / "output.mkv"
        video_file.write_text("fake video")
        
        # Mock subtitle file with profanity
        subtitle_file = SubtitleFile(
            path=video_file.with_suffix('.srt'),
            entries=[
                SubtitleEntry(1, 10.0, 15.0, "This has damn profanity"),
                SubtitleEntry(2, 20.0, 25.0, "Clean subtitle"),
            ]
        )
        video_processor.subtitle_manager.load_subtitle_file.return_value = subtitle_file
        video_processor.subtitle_manager.find_subtitle_for_video.return_value = subtitle_file.path
        
        # Mock FFmpeg success
        video_processor.ffmpeg.mute_audio.return_value = True
        
        result = video_processor.process_video(video_file, output_file)
        
        assert result.success is True
        assert result.status == ProcessingStatus.SUCCESS
        assert result.segments_muted > 0
        assert result.output_path == output_file
    
    def test_process_video_no_subtitle(self, video_processor, tmp_path):
        """Test processing fails when no subtitle found."""
        video_file = tmp_path / "input.mkv"
        output_file = tmp_path / "output.mkv"
        video_file.write_text("fake video")
        
        # Mock no subtitle found
        video_processor.subtitle_manager.load_subtitle_file.return_value = None
        
        result = video_processor.process_video(video_file, output_file)
        
        assert result.success is False
        assert "No subtitle" in result.error_message
    
    def test_process_video_clean(self, video_processor, tmp_path):
        """Test processing skips clean videos."""
        video_file = tmp_path / "input.mkv"
        output_file = tmp_path / "output.mkv"
        video_file.write_text("fake video")
        
        # Mock clean subtitle file (no profanity)
        subtitle_file = SubtitleFile(
            path=video_file.with_suffix('.srt'),
            entries=[
                SubtitleEntry(1, 10.0, 15.0, "Clean subtitle"),
                SubtitleEntry(2, 20.0, 25.0, "No profanity here"),
            ]
        )
        video_processor.subtitle_manager.load_subtitle_file.return_value = subtitle_file
        
        result = video_processor.process_video(video_file, output_file)
        
        assert result.status == ProcessingStatus.SKIPPED
        assert "No profanity detected" in result.error_message
    
    def test_can_process_success(self, video_processor, mock_ffmpeg_wrapper, tmp_path):
        """Test can_process returns True for valid video."""
        video_file = tmp_path / "test.mkv"
        video_file.write_text("fake video")
        
        # Mock valid probe result
        probe_result = FFprobeResult(
            path=video_file,
            format="matroska",
            duration=3600.0,
            size=1000000,
            bit_rate=1000,
            width=1920,
            height=1080
        )
        mock_ffmpeg_wrapper.probe.return_value = probe_result
        
        can_process, reason = video_processor.can_process(video_file)
        
        assert can_process is True
        assert reason is None
    
    def test_can_process_missing_file(self, video_processor):
        """Test can_process fails for missing file."""
        can_process, reason = video_processor.can_process(Path("/nonexistent.mkv"))
        
        assert can_process is False
        assert "not found" in reason
    
    def test_estimate_processing_time(self, video_processor, mock_ffmpeg_wrapper, tmp_path):
        """Test processing time estimation."""
        video_file = tmp_path / "test.mkv"
        video_file.write_text("fake video")
        
        # Mock 1-hour 1080p video
        probe_result = FFprobeResult(
            path=video_file,
            format="matroska",
            duration=3600.0,
            size=1000000,
            bit_rate=1000,
            width=1920,
            height=1080
        )
        mock_ffmpeg_wrapper.probe.return_value = probe_result
        
        # Copy mode (faster)
        video_processor.ffmpeg_config.re_encode_video = False
        estimate = video_processor.estimate_processing_time(video_file)
        
        assert estimate > 0
        assert estimate < 10000  # Should be reasonable
    
    def test_get_processing_summary(self, video_processor, tmp_path):
        """Test generating processing summary."""
        video_file = tmp_path / "test.mkv"
        output_file = tmp_path / "output.mkv"
        
        result = ProcessingResult(
            video_path=video_file,
            status=ProcessingStatus.SUCCESS,
            start_time=datetime.now(),
            output_path=output_file,
            segments_muted=5
        )
        result.mark_complete(success=True)
        
        summary = video_processor.get_processing_summary(result)
        
        assert "test.mkv" in summary
        assert "Successfully processed" in summary
        assert "5" in summary  # segments muted
    
    def test_repr(self, video_processor):
        """Test detailed representation."""
        repr_str = repr(video_processor)
        
        assert "VideoProcessor" in repr_str
    
    def test_str(self, video_processor, mock_ffmpeg_wrapper):
        """Test string representation."""
        str_rep = str(video_processor)
        
        assert "VideoProcessor" in str_rep
        assert "ready" in str_rep
