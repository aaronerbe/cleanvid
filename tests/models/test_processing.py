"""
Unit tests for processing models.

Tests ProcessingStatus, VideoMetadata, ProcessingResult, and ProcessingStats.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from cleanvid.models.processing import (
    ProcessingStatus,
    VideoMetadata,
    ProcessingResult,
    ProcessingStats,
)


class TestProcessingStatus:
    """Test ProcessingStatus enum."""
    
    def test_status_values(self):
        """Test all status enum values."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.SUCCESS.value == "success"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.SKIPPED.value == "skipped"


class TestVideoMetadata:
    """Test VideoMetadata model."""
    
    def test_create_metadata(self):
        """Test creating video metadata."""
        metadata = VideoMetadata(
            path=Path("/movies/test.mkv"),
            size_bytes=1024 * 1024 * 1024,  # 1GB
            duration_seconds=7200.0,  # 2 hours
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert metadata.path == Path("/movies/test.mkv")
        assert metadata.size_bytes == 1024 * 1024 * 1024
        assert metadata.duration_seconds == 7200.0
        assert metadata.width == 1920
        assert metadata.height == 1080
    
    def test_size_mb_property(self):
        """Test size in megabytes."""
        metadata = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1024 * 1024 * 100,  # 100MB
            duration_seconds=3600.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert metadata.size_mb == 100.0
    
    def test_size_gb_property(self):
        """Test size in gigabytes."""
        metadata = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1024 * 1024 * 1024 * 2,  # 2GB
            duration_seconds=3600.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert metadata.size_gb == 2.0
    
    def test_resolution_property(self):
        """Test resolution string."""
        metadata = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1000,
            duration_seconds=3600.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert metadata.resolution == "1920x1080"
    
    def test_is_hd_property(self):
        """Test HD detection."""
        hd_metadata = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1000,
            duration_seconds=3600.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac"
        )
        
        sd_metadata = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1000,
            duration_seconds=3600.0,
            width=640,
            height=480,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert hd_metadata.is_hd is True
        assert sd_metadata.is_hd is False
    
    def test_is_4k_property(self):
        """Test 4K detection."""
        metadata_4k = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1000,
            duration_seconds=3600.0,
            width=3840,
            height=2160,
            video_codec="h265",
            audio_codec="aac"
        )
        
        metadata_hd = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1000,
            duration_seconds=3600.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac"
        )
        
        assert metadata_4k.is_4k is True
        assert metadata_hd.is_4k is False
    
    def test_subtitle_fields(self):
        """Test subtitle-related fields."""
        metadata = VideoMetadata(
            path=Path("/test.mkv"),
            size_bytes=1000,
            duration_seconds=3600.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac",
            has_subtitles=True,
            subtitle_path=Path("/test.srt")
        )
        
        assert metadata.has_subtitles is True
        assert metadata.subtitle_path == Path("/test.srt")


class TestProcessingResult:
    """Test ProcessingResult model."""
    
    def test_create_result(self):
        """Test creating processing result."""
        start = datetime.now()
        result = ProcessingResult(
            video_path=Path("/movies/test.mkv"),
            status=ProcessingStatus.PROCESSING,
            start_time=start
        )
        
        assert result.video_path == Path("/movies/test.mkv")
        assert result.status == ProcessingStatus.PROCESSING
        assert result.start_time == start
        assert result.end_time is None
    
    def test_duration_properties(self):
        """Test duration calculations."""
        start = datetime.now()
        end = start + timedelta(minutes=10)
        
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.SUCCESS,
            start_time=start,
            end_time=end
        )
        
        assert result.duration_seconds == pytest.approx(600.0, abs=1.0)
        assert result.duration_minutes == pytest.approx(10.0, abs=0.1)
    
    def test_duration_no_end_time(self):
        """Test duration when not complete."""
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.PROCESSING,
            start_time=datetime.now()
        )
        
        assert result.duration_seconds == 0.0
        assert result.duration_minutes == 0.0
    
    def test_success_property(self):
        """Test success flag."""
        success_result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.SUCCESS,
            start_time=datetime.now()
        )
        
        failed_result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.FAILED,
            start_time=datetime.now()
        )
        
        assert success_result.success is True
        assert failed_result.success is False
    
    def test_failed_property(self):
        """Test failed flag."""
        success_result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.SUCCESS,
            start_time=datetime.now()
        )
        
        failed_result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.FAILED,
            start_time=datetime.now()
        )
        
        assert success_result.failed is False
        assert failed_result.failed is True
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.PROCESSING,
            start_time=datetime.now()
        )
        
        result.add_warning("Subtitle quality low")
        result.add_warning("Audio sync issue")
        
        assert len(result.warnings) == 2
        assert "Subtitle quality low" in result.warnings
    
    def test_mark_complete_success(self):
        """Test marking as successfully complete."""
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.PROCESSING,
            start_time=datetime.now()
        )
        
        result.mark_complete(success=True)
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.end_time is not None
        assert result.error_message is None
    
    def test_mark_complete_failure(self):
        """Test marking as failed."""
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.PROCESSING,
            start_time=datetime.now()
        )
        
        result.mark_complete(success=False, error="FFmpeg failed")
        
        assert result.status == ProcessingStatus.FAILED
        assert result.end_time is not None
        assert result.error_message == "FFmpeg failed"
    
    def test_to_dict(self):
        """Test JSON serialization."""
        start = datetime.now()
        result = ProcessingResult(
            video_path=Path("/movies/test.mkv"),
            status=ProcessingStatus.SUCCESS,
            start_time=start,
            output_path=Path("/filtered/test.mkv"),
            segments_muted=5,
            subtitle_downloaded=True
        )
        result.mark_complete(success=True)
        
        data = result.to_dict()
        
        assert data["video_path"] == "/movies/test.mkv"
        assert data["status"] == "success"
        assert data["segments_muted"] == 5
        assert data["subtitle_downloaded"] is True
        assert "start_time" in data
        assert "end_time" in data
    
    def test_str_representation(self):
        """Test string representation."""
        result = ProcessingResult(
            video_path=Path("/movies/test.mkv"),
            status=ProcessingStatus.SUCCESS,
            start_time=datetime.now()
        )
        
        str_rep = str(result)
        assert "test.mkv" in str_rep
        assert "✓" in str_rep  # Success symbol


class TestProcessingStats:
    """Test ProcessingStats model."""
    
    def test_default_stats(self):
        """Test default statistics."""
        stats = ProcessingStats()
        
        assert stats.total_videos == 0
        assert stats.successful == 0
        assert stats.failed == 0
        assert stats.skipped == 0
        assert stats.total_segments_muted == 0
        assert stats.subtitles_downloaded == 0
    
    def test_processed_property(self):
        """Test processed count."""
        stats = ProcessingStats()
        stats.successful = 8
        stats.failed = 2
        
        assert stats.processed == 10
    
    def test_success_rate(self):
        """Test success rate calculation."""
        stats = ProcessingStats()
        stats.successful = 8
        stats.failed = 2
        
        assert stats.success_rate == 80.0
    
    def test_success_rate_no_processing(self):
        """Test success rate when nothing processed."""
        stats = ProcessingStats()
        assert stats.success_rate == 0.0
    
    def test_duration_properties(self):
        """Test duration calculations."""
        start = datetime.now()
        end = start + timedelta(minutes=30)
        
        stats = ProcessingStats(start_time=start, end_time=end)
        
        assert stats.duration_seconds == pytest.approx(1800.0, abs=1.0)
        assert stats.duration_minutes == pytest.approx(30.0, abs=0.1)
    
    def test_average_time_per_video(self):
        """Test average processing time."""
        start = datetime.now()
        end = start + timedelta(minutes=30)
        
        stats = ProcessingStats(start_time=start, end_time=end)
        stats.successful = 3
        
        avg = stats.average_time_per_video
        assert avg == pytest.approx(600.0, abs=1.0)  # 30min / 3 = 10min = 600s
    
    def test_average_time_no_processing(self):
        """Test average time when nothing processed."""
        stats = ProcessingStats()
        assert stats.average_time_per_video == 0.0
    
    def test_add_result_success(self):
        """Test adding successful result."""
        stats = ProcessingStats()
        
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.SUCCESS,
            start_time=datetime.now(),
            segments_muted=5,
            subtitle_downloaded=True
        )
        
        stats.add_result(result)
        
        assert stats.successful == 1
        assert stats.total_segments_muted == 5
        assert stats.subtitles_downloaded == 1
    
    def test_add_result_failed(self):
        """Test adding failed result."""
        stats = ProcessingStats()
        
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.FAILED,
            start_time=datetime.now()
        )
        
        stats.add_result(result)
        
        assert stats.failed == 1
        assert stats.successful == 0
    
    def test_add_result_skipped(self):
        """Test adding skipped result."""
        stats = ProcessingStats()
        
        result = ProcessingResult(
            video_path=Path("/test.mkv"),
            status=ProcessingStatus.SKIPPED,
            start_time=datetime.now()
        )
        
        stats.add_result(result)
        
        assert stats.skipped == 1
    
    def test_add_multiple_results(self):
        """Test adding multiple results."""
        stats = ProcessingStats(total_videos=10)
        
        # Add 8 successes
        for i in range(8):
            result = ProcessingResult(
                video_path=Path(f"/test{i}.mkv"),
                status=ProcessingStatus.SUCCESS,
                start_time=datetime.now(),
                segments_muted=3,
                subtitle_downloaded=True
            )
            stats.add_result(result)
        
        # Add 2 failures
        for i in range(2):
            result = ProcessingResult(
                video_path=Path(f"/fail{i}.mkv"),
                status=ProcessingStatus.FAILED,
                start_time=datetime.now()
            )
            stats.add_result(result)
        
        assert stats.successful == 8
        assert stats.failed == 2
        assert stats.total_segments_muted == 24  # 8 * 3
        assert stats.subtitles_downloaded == 8
        assert stats.success_rate == 80.0
    
    def test_mark_complete(self):
        """Test marking batch as complete."""
        stats = ProcessingStats()
        stats.mark_complete()
        
        assert stats.end_time is not None
    
    def test_to_summary_string(self):
        """Test summary generation."""
        stats = ProcessingStats(total_videos=10)
        stats.successful = 8
        stats.failed = 2
        stats.total_segments_muted = 40
        stats.subtitles_downloaded = 7
        stats.mark_complete()
        
        summary = stats.to_summary_string()
        
        assert "Total videos found: 10" in summary
        assert "Successfully processed: 8" in summary
        assert "Failed: 2" in summary
        assert "Success rate: 80.0%" in summary
        assert "Total segments muted: 40" in summary
        assert "Subtitles downloaded: 7" in summary
    
    def test_to_dict(self):
        """Test JSON serialization."""
        start = datetime.now()
        stats = ProcessingStats(
            total_videos=10,
            start_time=start
        )
        stats.successful = 8
        stats.failed = 2
        stats.mark_complete()
        
        data = stats.to_dict()
        
        assert data["total_videos"] == 10
        assert data["successful"] == 8
        assert data["failed"] == 2
        assert data["processed"] == 10
        assert data["success_rate"] == 80.0
        assert "start_time" in data
        assert "end_time" in data
    
    def test_str_representation(self):
        """Test string representation."""
        stats = ProcessingStats(total_videos=10)
        stats.successful = 8
        
        str_rep = str(stats)
        assert "8/10 successful" in str_rep
